"""
Target Go: aulas do curso (vídeo longo + Short de chamada) e notícias de mercado (Short) → YouTube.

Uso:
    python main.py --modo aula               # próxima aula da grade (curso.json)
    python main.py --modo aula --aula 5      # aula específica (número na lista, começando em 1)
    python main.py --modo noticia            # radar: só gera se houver notícia de alto impacto
    python main.py --modo noticia --tema "Fed sobe juros para 5%"   # notícia pedida à mão
    python main.py ... --sem-publicar        # só gera (para testar)
"""
import argparse
import json
import os
import re
import subprocess
import traceback
import unicodedata
from datetime import datetime, timedelta, timezone

import config
import roteiro_trade
import video
import voz

BR = timezone(timedelta(hours=-3))
DOCS = config.PASTA / "docs"
ESTADO = DOCS / "curso_estado.json"
RADAR = DOCS / "radar.json"
PLAYLIST_NOTICIAS = "Notícias que mexem com o mercado"


# ───────────────────────── utilidades ─────────────────────────
def _slug(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", texto.lower())[:40].strip("-") or "video"


def _ler(arq, padrao):
    try:
        return json.loads(arq.read_text(encoding="utf-8"))
    except Exception:
        return padrao


def _gravar(arq, dados):
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")


def _automatico() -> bool:
    return os.getenv("GITHUB_EVENT_NAME") == "schedule" or os.getenv("AGENDADO") == "sim"


def _trilha() -> str:
    """Aula automática: de manhã educação financeira, no fim da tarde forex/trade.
    TRILHA vem do relógio; sem ela (reserva do agendamento) decide pelo horário."""
    t = (os.getenv("TRILHA") or "").strip().lower()
    if t in ("educacao", "trade"):
        return t
    return "educacao" if datetime.now(BR).hour < 14 else "trade"


def _legenda(r: dict) -> str:
    return f"{r.get('legenda_tiktok') or r['titulo']}\n\n{' '.join(r.get('hashtags_tiktok') or r.get('hashtags', []))}".strip()


def _textos(r: dict, formato: str) -> dict:
    import publicar_youtube
    return {"titulo_youtube": r["titulo"], "descricao_youtube": r.get("descricao_pronta") or publicar_youtube.descricao(r, formato),
            "legenda_tiktok": r.get("legenda_tiktok") or r["titulo"],
            "hashtags_tiktok": " ".join(r.get("hashtags_tiktok") or r.get("hashtags", [])),
            "tags_youtube": ", ".join(r.get("tags_youtube", []))}


def _release(r: dict, arquivos: list) -> str | None:
    """No GitHub, os arquivos viram um 'Release' público com link direto (o workflow faz o envio)."""
    repo = os.getenv("GITHUB_REPOSITORY")
    if not repo:
        return None
    tag = f"video-{datetime.now():%Y%m%d-%H%M}-{os.getenv('GITHUB_RUN_NUMBER', '0')}"
    r["_tag"] = tag
    _gravar(config.PASTA_SAIDA / "release.json", {"tag": tag, "arquivos": [str(a) for a in arquivos if a],
                                                  "titulo": r["titulo"][:120], "legenda": _legenda(r)})
    return f"{os.getenv('GITHUB_SERVER_URL', 'https://github.com')}/{repo}/releases/download/{tag}"


PASTA_CELULAR = DOCS / "tiktok"


def _copia_celular(arquivo, nome: str, manter: int = 6) -> str | None:
    """Cópia leve (720p) do vertical dentro do painel: o botão 'Mandar pro TikTok (celular)' usa este arquivo."""
    try:
        PASTA_CELULAR.mkdir(parents=True, exist_ok=True)
        destino = PASTA_CELULAR / f"{nome}.mp4"
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(arquivo), "-vf", "scale=720:-2",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-c:a", "aac", "-b:a", "128k",
                        "-movflags", "+faststart", str(destino)], check=True, timeout=600)
        for velho in sorted(PASTA_CELULAR.glob("*.mp4"), key=lambda p: p.stat().st_mtime)[:-manter]:
            velho.unlink()
        return f"tiktok/{destino.name}"
    except Exception as erro:
        print(f"   (sem cópia para o celular: {erro})")
        return None


def _registrar(item: dict):
    lista = _ler(DOCS / "videos.json", [])
    item = {"data": datetime.now(BR).isoformat(timespec="seconds"), **item}
    if not _automatico():
        item["manual"] = True
    if os.getenv("GITHUB_RUN_ID"):
        item["execucao"] = f"{os.getenv('GITHUB_SERVER_URL')}/{os.getenv('GITHUB_REPOSITORY')}/actions/runs/{os.getenv('GITHUB_RUN_ID')}"
    lista.append(item)
    _gravar(DOCS / "videos.json", lista[-500:])


def _youtube(arquivo, r: dict, formato: str, capa=None, playlist: str | list | None = None) -> str | None:
    import publicar_youtube
    import youtube_token
    if not (config.PUBLICAR_YOUTUBE and youtube_token.conectado()):
        print("⏭️  YouTube não conectado: o vídeo fica para download no painel.")
        return None
    try:
        url = publicar_youtube.publicar(arquivo, r, formato, None, capa)
    except Exception:
        traceback.print_exc()
        return "ERRO"
    for nome_pl in ([playlist] if isinstance(playlist, str) else playlist or []):
        if not nome_pl or url == "ERRO":
            continue
        try:
            publicar_youtube.adicionar_na_playlist(url, nome_pl, r.get("descricao_playlist", ""))
        except Exception as erro:
            print(f"::warning title=Playlist::Não consegui pôr na playlist '{nome_pl}': {erro}")
    return url


# ───────────────────────── aulas ─────────────────────────
def _proxima_aula(curso: dict, feitas: list[int], trilha: str | None = None) -> int | None:
    """Com trilha: a próxima aula daquela trilha (se ela acabou, a da outra).
    Sem trilha (pedido manual): 2 aulas de trade, 1 de educação financeira, e assim por diante."""
    aulas = curso["aulas"]
    trade = [i for i, a in enumerate(aulas) if a["nivel"] != "educacao" and i not in feitas]
    edu = [i for i, a in enumerate(aulas) if a["nivel"] == "educacao" and i not in feitas]
    if trilha == "educacao":
        return (edu or trade or [None])[0]
    if trilha == "trade":
        return (trade or edu or [None])[0]
    if len(feitas) % 3 == 2 and edu:
        return edu[0]
    return (trade or edu or [None])[0]


def fazer_aula(indice: int | None, publicar: bool):
    curso = _ler(config.ARQUIVO_CURSO, None)
    if not curso:
        raise SystemExit("::error::curso.json não encontrado ou inválido.")
    estado = _ler(ESTADO, {"feitas": []})
    hoje = datetime.now(BR).date().isoformat()
    trilha = _trilha() if _automatico() else None
    if trilha and estado.get(f"ultima_data_{trilha}") == hoje:
        print(f"⏭️  A aula de {'educação financeira' if trilha == 'educacao' else 'forex'} de hoje já saiu.")
        return
    i = indice if indice is not None else _proxima_aula(curso, estado["feitas"], trilha)
    if i is None:
        print("🎓 Todas as aulas da grade já saíram! Acrescente novas aulas em curso.json.")
        return
    aula = curso["aulas"][i]
    nivel = curso["niveis"][aula["nivel"]]
    mesmas = [j for j, a in enumerate(curso["aulas"]) if a["nivel"] == aula["nivel"]]
    pos = mesmas.index(i)
    numero = pos + 1
    anterior = curso["aulas"][mesmas[pos - 1]]["titulo"] if pos > 0 else ""
    proxima = curso["aulas"][mesmas[pos + 1]]["titulo"] if pos + 1 < len(mesmas) else ""
    print(f"📚 {nivel['emoji']} {nivel['nome']} · Aula {numero:02d}: {aula['titulo']}")

    r = roteiro_trade.gerar_aula(aula, curso, numero, len(mesmas), anterior, proxima)
    r["descricao_playlist"] = f"{curso.get('nome', '')} · nível {nivel['nome']}. Uma aula nova por dia, de graça."
    pasta = config.PASTA_SAIDA / f"{datetime.now():%Y-%m-%d_%H%M}_{_slug(aula['titulo'])}"
    pasta.mkdir(parents=True, exist_ok=True)
    _gravar(pasta / "roteiro.json", r)

    print("🎙️  Gravando a narração...")
    audio = pasta / "narracao.mp3"
    palavras, inicios = voz.gerar_partes([p["texto"] for p in r["partes"]], audio)
    final = video.montar(r, audio, palavras, pasta, formato="longo", inicios_partes=inicios)
    destino = pasta / f"{_slug(r['titulo'])}.mp4"
    final.rename(destino)
    segundos = video.duracao(destino)
    print(f"✅ Aula pronta ({segundos / 60:.1f} min)")

    import thumb
    selo = f"{nivel['emoji']} {nivel['nome'].upper()} · AULA {numero:02d}"
    capa = thumb.criar(r.get("texto_capa") or aula["titulo"], pasta / f"{_slug(r['titulo'])}-capa.jpg", selo,
                       nivel["cor"], i, r.get("apoio_capa", ""))
    if not capa:
        capa = video.criar_capa(destino, r.get("texto_capa") or r["titulo"], pasta / f"{_slug(r['titulo'])}-capa.jpg")
    chamada = None
    try:
        print("✂️  Criando o corte vertical (Short / TikTok)...")
        chamada = video.criar_chamada(destino, r.get("titulo_short") or r["titulo"], pasta / f"{_slug(r['titulo'])}-short.mp4",
                                      inicio=float(inicios[1]) if len(inicios) > 1 else 0.0)
    except Exception:
        traceback.print_exc()
    base = _release(r, [destino, capa, chamada])
    tag = r.get("_tag") or _slug(r["titulo"])
    mp4 = f"{base}/{destino.name}" if base else None
    for lixo in list(pasta.glob("clipe_*")) + list(pasta.glob("cena_*.mp4")) + list(pasta.glob("grafico_*")):
        lixo.unlink(missing_ok=True)

    if publicar and _automatico() and config.YT_PRIVACIDADE == "public":  # fica pública exatamente no horário
        hora = config.HORA_AULA_TARDE if trilha == "trade" else config.HORA_AULA
        h, mi = (int(x) for x in hora.split(":"))
        alvo = datetime.now(BR).replace(hour=h, minute=mi, second=0, microsecond=0)
        if alvo > datetime.now(BR) + timedelta(minutes=3):
            r["publicar_em"] = alvo.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    playlists = [curso.get("playlist_geral") if aula["nivel"] != "educacao" else None, nivel["playlist"]]
    url = _youtube(destino, r, "longo", capa, [p for p in playlists if p]) if publicar else None
    info_aula = {"indice": i, "nivel": aula["nivel"], "numero": numero, "titulo_aula": aula["titulo"]}
    _registrar({"titulo": r["titulo"], "assunto": r.get("assunto", ""), "legenda": _legenda(r), "segundos": round(segundos),
                "formato": "longo", "textos": _textos(r, "longo"), "aula": info_aula, "id": tag,
                **({"mp4": mp4} if mp4 else {}), **({"capa": f"{base}/{capa.name}"} if base and capa else {}),
                **({"youtube": url} if url else {})})
    if chamada:
        link = url if url and url.startswith("http") else "no canal"
        rc = {"titulo": (r.get("titulo_short") or r["titulo"])[:95], "assunto": r.get("assunto", ""),
              "descricao_pronta": f"{r['titulo']}\n\n▶ AULA COMPLETA: {link}\n\n{roteiro_trade.AVISO}\n\n"
                                  f"{' '.join(r.get('hashtags', []) + ['#shorts'])}",
              "legenda_tiktok": f"{r.get('legenda_tiktok') or r['titulo']}\nAula completa no YouTube: Target Go",
              "hashtags_tiktok": r.get("hashtags_tiktok", []), "hashtags": r.get("hashtags", []) + ["#shorts"],
              "tags_youtube": r.get("tags_youtube", []), "publicar_em": r.get("publicar_em")}
        url_c = _youtube(chamada, rc, "curto") if publicar and url and url != "ERRO" else None
        _registrar({"titulo": rc["titulo"], "assunto": rc["assunto"], "legenda": _legenda(rc),
                    "segundos": round(video.duracao(chamada)), "formato": "curto", "textos": _textos(rc, "curto"),
                    "chamada_de": tag, "id": f"{tag}-short", "aula": info_aula,
                    **({"mp4": f"{base}/{chamada.name}"} if base else {}),
                    **({"celular": c} if (c := _copia_celular(chamada, f"{tag}-short")) else {}),
                    **({"youtube": url_c} if url_c else {})})

    if publicar and url == "ERRO":
        raise SystemExit("::error::A aula foi gerada mas não subiu no YouTube (veja o log). Ela fica no painel para baixar.")
    if publicar:  # teste sem publicar não avança a grade
        if i not in estado["feitas"]:
            estado["feitas"].append(i)
        estado["ultima_data"] = hoje
        estado[f"ultima_data_{'educacao' if aula['nivel'] == 'educacao' else 'trade'}"] = hoje
        estado["ultima_aula"] = aula["titulo"]
        _gravar(ESTADO, estado)


# ───────────────────────── notícias ─────────────────────────
def fazer_noticia(tema: str | None, publicar: bool):
    import mercado
    import noticias
    hoje = datetime.now(BR).date().isoformat()
    radar = _ler(RADAR, {})
    if radar.get("data") != hoje:
        radar = {"data": hoje, "videos": 0, "feitos": radar.get("feitos", [])[-30:]}
    if not tema and radar["videos"] >= config.NOTICIAS_POR_DIA:
        print(f"⏭️  Já saíram {radar['videos']} notícias hoje (limite {config.NOTICIAS_POR_DIA}).")
        return
    if tema:
        n = {"titulo": tema, "fonte": "pedido manual", "data": datetime.now(BR).strftime("%d/%m/%Y %H:%M"),
             "motivo": "", "ativos": ["DX-Y.NYB", "GC=F", "EURUSD=X"], "assunto": tema[:80]}
    else:
        n = noticias.escolher(radar["feitos"])
        radar["checado"] = datetime.now(BR).strftime("%H:%M")
        if not n:
            _gravar(RADAR, radar)
            return
    movimentos = [m for m in (mercado.variacao(t) for t in (n.get("ativos") or [])[:3]) if m]
    r = roteiro_trade.gerar_noticia(n, movimentos)
    pasta = config.PASTA_SAIDA / f"{datetime.now():%Y-%m-%d_%H%M}_noticia_{_slug(r['assunto'])}"
    pasta.mkdir(parents=True, exist_ok=True)
    _gravar(pasta / "roteiro.json", r)
    audio = pasta / "narracao.mp3"
    palavras = voz.gerar(r["roteiro"], audio)
    r["musica"] = "noticia"
    final = video.montar(r, audio, palavras, pasta, formato="curto")
    destino = pasta / f"{_slug(r['titulo'])}.mp4"
    final.rename(destino)
    base = _release(r, [destino])
    tag = r.get("_tag") or _slug(r["titulo"])
    url = _youtube(destino, r, "curto", None, PLAYLIST_NOTICIAS) if publicar else None
    _registrar({"titulo": r["titulo"], "assunto": r.get("assunto", ""), "legenda": _legenda(r),
                "segundos": round(video.duracao(destino)), "formato": "curto", "textos": _textos(r, "curto"),
                "noticia": {"manchete": n["titulo"], "fonte": n.get("fonte", ""), "link": n.get("link", ""),
                            "impacto": n.get("impacto")}, "id": tag,
                **({"mp4": f"{base}/{destino.name}"} if base else {}),
                **({"celular": c} if (c := _copia_celular(destino, tag)) else {}),
                **({"youtube": url} if url else {})})
    radar["videos"] += 1
    radar["feitos"].append(n.get("assunto") or n["titulo"])
    _gravar(RADAR, radar)
    if publicar and url == "ERRO":
        raise SystemExit("::error::A notícia foi gerada mas não subiu no YouTube.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modo", choices=["aula", "noticia"], default=os.getenv("MODO") or "aula")
    ap.add_argument("--aula", type=int, help="número da aula na lista de curso.json (1 = primeira)")
    ap.add_argument("--tema", help="notícia pedida à mão")
    ap.add_argument("--sem-publicar", action="store_true")
    a = ap.parse_args()
    if a.modo == "aula":
        fazer_aula(a.aula - 1 if a.aula else None, not a.sem_publicar)
    else:
        fazer_noticia(a.tema, not a.sem_publicar)


if __name__ == "__main__":
    main()
