"""Envia o vídeo para o YouTube pela YouTube Data API v3 (grátis, com cota diária).
curto → publica como Short;  longo → vídeo normal com capítulos e capa (thumbnail)."""
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

import config
import youtube_token

# "youtube" inclui enviar vídeos e organizar playlists (cada nível do curso tem a sua)
ESCOPOS = ["https://www.googleapis.com/auth/youtube"]


def _credenciais() -> Credentials:
    refresh = youtube_token.carregar()
    if not (config.YT_CLIENT_ID and config.YT_CLIENT_SECRET and refresh):
        raise RuntimeError("YouTube não conectado: use o botão 'Conectar YouTube' no painel.")
    cred = Credentials(
        token=None,
        refresh_token=refresh,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config.YT_CLIENT_ID,
        client_secret=config.YT_CLIENT_SECRET,
        scopes=ESCOPOS,
    )
    cred.refresh(Request())
    return cred


def _tempo(s: float) -> str:
    s = int(s)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def descricao(roteiro: dict, formato: str, capitulos: list[tuple[float, str]] | None = None) -> str:
    hashtags = list(roteiro.get("hashtags", []))
    if formato == "curto" and "#shorts" not in [h.lower() for h in hashtags]:
        hashtags.append("#shorts")
    texto = roteiro.get("descricao", "").strip()
    # sem lista de capítulos com minutos na descrição (preferência do canal)
    texto += "\n\n" + " ".join(hashtags)
    return texto.strip()[:4900]


def publicar(arquivo, roteiro: dict, formato: str = "curto", capitulos=None, capa=None) -> str:
    youtube = build("youtube", "v3", credentials=_credenciais(), cache_discovery=False)

    corpo = {
        "snippet": {
            "title": roteiro["titulo"][:100],
            "description": roteiro.get("descricao_pronta") or descricao(roteiro, formato, capitulos),
            "tags": (roteiro.get("tags_youtube") or [h.lstrip("#") for h in roteiro.get("hashtags", [])])[:15],
            "categoryId": config.YT_CATEGORIA,
            "defaultLanguage": "pt-BR",
            "defaultAudioLanguage": "pt-BR",
        },
        "status": {
            "privacyStatus": "private" if roteiro.get("publicar_em") else config.YT_PRIVACIDADE,
            **({"publishAt": roteiro["publicar_em"]} if roteiro.get("publicar_em") else {}),
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,  # declara conteúdo gerado por IA
        },
    }

    def enviar(c):
        media = MediaFileUpload(str(arquivo), mimetype="video/mp4", chunksize=16 * 1024 * 1024, resumable=True)
        pedido = youtube.videos().insert(part="snippet,status", body=c, media_body=media)
        resposta = None
        while resposta is None:
            status, resposta = pedido.next_chunk()
            if status:
                print(f"   YouTube: {int(status.progress() * 100)}%")
        return resposta

    try:
        resposta = enviar(corpo)
    except HttpError as e:
        if "containsSyntheticMedia" in str(e):
            corpo["status"].pop("containsSyntheticMedia")
            resposta = enviar(corpo)
        else:
            raise

    video_id = resposta["id"]
    if capa:
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(capa), mimetype="image/jpeg")).execute()
            print("   YouTube: capa enviada")
        except HttpError as e:
            print(f"::warning title=YouTube::Capa não enviada (verifique o canal por telefone em youtube.com/verify): {e}")

    privacidade = resposta.get("status", {}).get("privacyStatus")
    if roteiro.get("publicar_em"):
        print(f"   YouTube: agendado para {roteiro['publicar_em']} (UTC)")
    elif privacidade == "private" and config.YT_PRIVACIDADE != "private":
        print("::warning title=YouTube::O YouTube deixou o vídeo PRIVADO: o projeto ainda não passou na auditoria da API.")
    url = f"https://youtube.com/shorts/{video_id}" if formato == "curto" else f"https://youtu.be/{video_id}"
    print(f"::notice title=YouTube::{url} ({privacidade})")
    return url


ARQUIVO_PLAYLISTS = config.PASTA / "docs" / "playlists.json"


def adicionar_na_playlist(url_video: str, nome: str, descricao: str = "") -> str | None:
    """Põe o vídeo na playlist `nome` (cria a playlist na primeira vez). Devolve o link da playlist."""
    import json
    video_id = url_video.rstrip("/").split("/")[-1].split("?")[0]
    youtube = build("youtube", "v3", credentials=_credenciais(), cache_discovery=False)
    try:
        listas = json.loads(ARQUIVO_PLAYLISTS.read_text(encoding="utf-8"))
    except Exception:
        listas = {}
    pid = listas.get(nome)
    if not pid:  # já existe no canal com esse nome (criada à mão)? usa ela
        pedido = youtube.playlists().list(part="snippet", mine=True, maxResults=50)
        while pedido is not None and not pid:
            r = pedido.execute()
            pid = next((i["id"] for i in r.get("items", [])
                        if i["snippet"]["title"].strip().lower() == nome.strip().lower()), None)
            pedido = youtube.playlists().list_next(pedido, r)
        if pid:
            listas[nome] = pid
            ARQUIVO_PLAYLISTS.write_text(json.dumps(listas, ensure_ascii=False, indent=1), encoding="utf-8")
    if not pid:
        r = youtube.playlists().insert(part="snippet,status", body={
            "snippet": {"title": nome[:150], "description": descricao[:4900], "defaultLanguage": "pt-BR"},
            "status": {"privacyStatus": "public"}}).execute()
        pid = r["id"]
        listas[nome] = pid
        ARQUIVO_PLAYLISTS.write_text(json.dumps(listas, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"   📂 playlist criada: {nome}")
    youtube.playlistItems().insert(part="snippet", body={
        "snippet": {"playlistId": pid, "resourceId": {"kind": "youtube#video", "videoId": video_id}}}).execute()
    print(f"   📂 adicionado na playlist '{nome}'")
    return f"https://www.youtube.com/playlist?list={pid}"
