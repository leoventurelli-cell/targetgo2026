"""Roteiros do Target Go: aulas do curso (vídeo longo) e notícias de mercado (Short).
Usa a mesma IA do roteiro (Groq ou Gemini) e faz uma segunda passada de revisão técnica."""
import json

import config
import graficos
from roteiro import _pedir_ao_gemini, _pedir_ao_groq, limpar_narracao

AVISO = ("⚠️ Conteúdo educativo. Não é recomendação de investimento nem promessa de lucro. "
         "Operar no mercado envolve risco de perda, inclusive de todo o capital.")

ESTILO = """Jeito de falar (muito importante, a narração tem que soar humana, como um professor gravando):
- Fale direto com quem assiste ("você"), como numa conversa. Pode usar "pra", "tá", "olha só", "repara",
  "sabe aquela situação...". Frases curtas, ritmo variado, perguntas que a pessoa faria ("mas e se o preço voltar?").
- Use exemplos do dia a dia e mini-histórias ("imagina que você tem mil reais na conta...").
- Nada de listas lidas como robô, nada de "primeiramente/em segundo lugar". Sem emojis, sem indicações de cena.
- Números só se forem exatos (contas que você mesmo fez no roteiro) ou regras conhecidas; nunca invente estatística,
  cotação ou data. Se citar regra que pode mudar (imposto, limite do FGC), diga "pela regra atual, confira antes".
- Nunca prometa lucro, nunca diga "compre" ou "venda" um ativo específico, nunca dê sinal de entrada.
  Ensine critérios e riscos. Mostre o lado ruim também."""

CENAS = f"""IMAGENS FIÉIS À FALA (o mais importante do vídeo): cada parte tem "cenas", uma lista de 5 a 9 itens
{{"frase": "...", "cena": "..."}}, na ordem da narração. "frase" = 3 a 8 palavras copiadas EXATAMENTE da narração
daquela parte, no ponto em que a imagem deve entrar; a imagem fica na tela até a próxima frase. A 1ª frase é o
começo da parte. A imagem tem que mostrar EXATAMENTE o que está sendo dito naquele momento: falou de pip → card
do pip com a conta; falou de suporte → padrao:suporte; falou do Ibovespa → ativo:^BVSP; falou da Selic → serie:selic.
Troque de imagem a cada 10 a 25 segundos de fala (umas 25 a 60 palavras). Não repita a mesma cena seguida.
Use SÓ estes formatos em "cena":
- "padrao:NOME" desenho didático. NOME é um destes: {", ".join(graficos.PADROES)}
- "ativo:TICKER" gráfico real de candles (6 meses). Tickers: EURUSD=X, GBPUSD=X, USDJPY=X, BRL=X, GC=F (ouro),
  CL=F (petróleo), ^GSPC (S&P 500), ^IXIC (Nasdaq), ^BVSP (Ibovespa), DX-Y.NYB (índice do dólar), BTC-USD.
  Acrescente "|mm" para médias móveis 20/50/200, "|sr" para suporte e resistência, "|1h" para os últimos 5 dias.
- "comparar:TICKER,TICKER" dois ou três ativos na mesma escala, em %.
- "serie:selic" / "serie:ipca" / "serie:cdi" / "serie:dolar" ou duas juntas "serie:selic,ipca" (dados oficiais do Banco Central).
- "juros:CAPITAL|TAXA_AO_MES|MESES" curva de juros compostos x simples (ex: "juros:1000|1|120").
- "card:TÍTULO|linha|linha" quadro com o conceito, a fórmula ou a conta da aula (até 4 linhas curtas,
  ex: "card:Tamanho do lote|Risco: R$ 50|Stop: 25 pips|Lote: 0,20"). Use cards com frequência para fixar a ideia.
- Termo EM INGLÊS para vídeo de banco de imagens (1 ou 2 por parte, quando a fala for sobre pessoas, dinheiro,
  bancos, empresas ou o dia a dia): "trader looking at charts", "stock exchange screens", "person counting money",
  "calculator and notebook", "bank building", "currency exchange office", "oil refinery", "gold bars".
NUNCA escreva na narração os códigos (EURUSD=X, ^BVSP, GC=F, BTC-USD) nem as marcações de cena: na fala use o nome
normal (euro-dólar, Ibovespa, ouro, bitcoin, índice do dólar).
"""

PROMPT_AULA = """Você é o roteirista e professor do canal Target Go, o melhor curso gratuito de trade e
educação financeira do Brasil. Escreva a narração de UMA aula em {idioma}.

Curso: {curso}
Trilha/nível: {nivel}  ·  Aula {numero} de {total_nivel} deste nível
Tema da aula: {titulo}
O que a aula precisa cobrir: {pontos}
Aula anterior: {anterior}
Próxima aula: {proxima}
Ativos para usar nos exemplos: {ativos}
Imagens sugeridas (pode usar): {sugeridas}

Duração: cerca de {minutos} minutos de fala, NO MÍNIMO {palavras} palavras no total.

Estrutura:
- Parte 1 "Abertura": comece com um gancho forte (uma situação, um erro comum ou uma pergunta), diga em uma frase
  o que a pessoa vai saber fazer no fim da aula, e convide para se inscrever e seguir a playlist. Nada de "olá pessoal".
- {partes_meio} partes do meio, cada uma com subtítulo curto e ~{por_parte} palavras: explique do jeito mais simples
  possível, depois aprofunde, com exemplo prático (de preferência com conta feita passo a passo) e um erro comum.
- Parte "Na prática": um exercício simples para a pessoa fazer (na conta demo, no papel ou no app do banco).
- Última parte "Resumo": recapitule em 3 ideias, faça uma pergunta para comentarem, diga qual é a próxima aula
  e lembre que o conteúdo é educativo e que o mercado tem risco.

{estilo}

{cenas}

Responda SOMENTE com JSON:
{{
  "assunto": "assunto em poucas palavras",
  "titulo": "título do YouTube, até 70 caracteres, que desperte curiosidade sem prometer lucro",
  "descricao": "descrição de 4 a 6 frases com palavras-chave do tema",
  "texto_capa": "2 a 4 palavras de impacto para a thumbnail (diferente do título)",
  "apoio_capa": "até 5 palavras de apoio na thumbnail (ou vazio)",
  "titulo_short": "título do Short de chamada, até 60 caracteres",
  "legenda_tiktok": "legenda curta para TikTok com um gancho e uma pergunta",
  "hashtags": ["#trade", "#forex", "#educacaofinanceira"],
  "hashtags_tiktok": ["#trade", "#forex", "#fyp"],
  "tags_youtube": ["até 15 tags"],
  "partes": [{{"titulo": "Abertura", "texto": "narração completa",
              "cenas": [{{"frase": "primeiras palavras da parte", "cena": "card:..."}}, {{"frase": "trecho exato", "cena": "padrao:..."}}]}}]
}}"""

PROMPT_NOTICIA = """Você é o apresentador do canal Target Go e explica notícias que podem mexer com o mercado,
para quem está aprendendo. Escreva um Short (vídeo vertical de {segundos} segundos, ~{palavras} palavras) em {idioma}.

Notícia (use SÓ estes fatos, não acrescente nenhum dado que não esteja aqui):
{fatos}

Movimento real dos mercados agora (dados conferidos, pode citar):
{movimentos}

Estrutura:
1. Gancho em 1 frase: o que aconteceu e por que importa pra quem opera ou investe.
2. O que aconteceu, com a data/hora se estiver nos fatos.
3. POR QUE isso pode mexer no mercado: explique o mecanismo de forma simples (ex: juros mais altos nos EUA atraem
   dinheiro pro dólar, e o ouro, que não paga juros, costuma sofrer). Diga quais mercados podem ser afetados
   (dólar, ouro, índices, petróleo, real, cripto) e em que direção COSTUMA acontecer, sempre como possibilidade.
4. O que observar nas próximas horas/dias (próxima decisão, próximo dado, regiões de preço só se estiverem nos dados).
5. Feche com "isso não é recomendação" de forma natural e convide para seguir pra entender o mercado.

{estilo}

Cenas: 4 a 6, use "ativo:TICKER|1h" dos ativos afetados (Tickers: {tickers}), "card:TÍTULO|linha|linha" com o
resumo do porquê, e no máximo 1 termo em inglês de banco de vídeo (ex: "stock exchange screens").

Responda SOMENTE com JSON:
{{
  "assunto": "assunto em poucas palavras",
  "titulo": "título do Short, até 70 caracteres, factual e chamativo, sem sensacionalismo",
  "descricao": "2 a 4 frases com o resumo e as fontes citadas nos fatos",
  "texto_capa": "gancho de até 5 palavras escrito na tela no começo",
  "legenda_tiktok": "legenda curta com uma pergunta",
  "hashtags": ["#mercadofinanceiro", "#forex", "#noticias"],
  "hashtags_tiktok": ["#mercadofinanceiro", "#forex", "#fyp"],
  "tags_youtube": ["até 12 tags"],
  "roteiro": "narração completa",
  "cenas": ["ativo:GC=F|1h", "card:...", "..."]
}}"""

PROMPT_REVISAO = """Você é revisor técnico de um curso de trade e educação financeira e também diretor de locução.
Abaixo está o JSON de um roteiro. Devolva o MESMO JSON (mesmas chaves e estrutura), corrigindo:
1. Erros técnicos ou de conta (pip, lote, alavancagem, margem, juros, risco/retorno, impostos, regras do FGC etc.).
   Refaça as contas. Se não tiver certeza de um número, troque por uma explicação sem o número.
2. Qualquer promessa de lucro, "compre/venda" de ativo específico, sinal de entrada ou garantia: reescreva como critério educativo.
3. Fatos inventados (estatísticas, datas, cotações, declarações) que não estejam nos dados fornecidos: remova.
4. Deixe a fala mais humana e natural (conversa de professor), sem mudar o tamanho de forma relevante.
5. Cenas fora dos formatos permitidos: troque por "card:..." equivalente. Formatos: padrao:, ativo:, comparar:, serie:, juros:, card:
   ou termo em inglês de banco de vídeo.
{extra}
JSON:
{dados}"""


def _pedir(prompt: str) -> dict:
    if not (config.GROQ_API_KEY or config.GEMINI_API_KEY):
        raise RuntimeError("Falta a IA do roteiro (GROQ_API_KEY ou GEMINI_API_KEY).")
    return (_pedir_ao_groq if config.GROQ_API_KEY else _pedir_ao_gemini)(prompt)


def _contar(d: dict) -> int:
    return sum(len(str(p.get("texto", "")).split()) for p in d.get("partes", []))


def _revisar(dados: dict, extra: str = "") -> dict:
    try:
        novo = _pedir(PROMPT_REVISAO.format(dados=json.dumps(dados, ensure_ascii=False), extra=extra))
        chave = "partes" if "partes" in dados else "roteiro"
        if novo.get(chave) and (chave == "roteiro" or len(novo["partes"]) >= len(dados["partes"]) - 1):
            if chave == "partes" and _contar(novo) < _contar(dados) * 0.8:
                print("   (revisão encurtou demais o roteiro; mantendo o original)")
                return dados
            print("   ✔️  roteiro revisado (contas, promessas e naturalidade)")
            return {**dados, **novo}
    except Exception as erro:
        print(f"   ⚠️  revisão falhou ({erro}); seguindo com o roteiro original")
    return dados


FALADOS = {"EURUSD=X": "euro-dólar", "GBPUSD=X": "libra-dólar", "USDJPY=X": "dólar-iene", "BRL=X": "dólar-real",
           "GC=F": "ouro", "CL=F": "petróleo", "^GSPC": "S&P 500", "^IXIC": "Nasdaq", "^BVSP": "Ibovespa",
           "DX-Y.NYB": "índice do dólar", "BTC-USD": "bitcoin", "ETH-USD": "ethereum", "^DJI": "Dow Jones"}


def _fala_limpa(t: str) -> str:
    """Tira da narração códigos de ticker e marcações de cena que a IA às vezes deixa escapar."""
    import re
    t = limpar_narracao(t)
    t = re.sub(r"\b(?:padrao|ativo|comparar|serie|juros|card)\s*:\s*", "", t, flags=re.I)
    for cod, nome in FALADOS.items():
        t = re.sub(r"(?<![\w^])" + re.escape(cod) + r"(?![\w])", nome, t)
    t = re.sub(r"\s*\(\s*(?:Ibovespa|ouro|bitcoin|euro-dólar|índice do dólar|petróleo)\s*\)", "", t)
    t = re.sub(r"\b(Ibovespa|bitcoin|ouro|euro-dólar)\s+\1\b", r"\1", t, flags=re.I)
    t = re.sub(r"\|\s*(?:mm|sr|1h)\b", "", t)
    return re.sub(r"[ \t]{2,}", " ", t).strip()


def _limpar_cenas(cenas, reserva: str, limite: int = 9) -> list[str]:
    boas = []
    for c in cenas or []:
        c = c.get("cena", "") if isinstance(c, dict) else c
        if str(c).strip():
            boas.append(str(c).strip())
    return boas[:limite] or [reserva]


def _ancoras(cenas) -> list[dict]:
    """[{'frase', 'cena'}] na ordem; cenas sem frase ficam com frase vazia (o vídeo distribui por tempo)."""
    saida = []
    for c in cenas or []:
        if isinstance(c, dict) and str(c.get("cena", "")).strip():
            saida.append({"frase": str(c.get("frase", "")).strip(), "cena": str(c["cena"]).strip()})
        elif isinstance(c, str) and c.strip():
            saida.append({"frase": "", "cena": c.strip()})
    tirar_repetida = [a for i, a in enumerate(saida) if i == 0 or a["cena"] != saida[i - 1]["cena"]]
    return tirar_repetida[:9]


def gerar_aula(aula: dict, curso: dict, numero: int, total_nivel: int, anterior: str, proxima: str) -> dict:
    nivel = curso["niveis"][aula["nivel"]]
    minutos = config.DURACAO_AULA_MINUTOS
    palavras = int(minutos * 60 * 2.4)
    partes_meio = max(3, min(7, minutos // 2))
    prompt = PROMPT_AULA.format(
        idioma=config.IDIOMA, curso=curso.get("nome", "Curso de Trade"), nivel=nivel["nome"], numero=numero,
        total_nivel=total_nivel, titulo=aula["titulo"], pontos=aula["pontos"], anterior=anterior or "esta é a primeira",
        proxima=proxima or "fim desta trilha", ativos=", ".join(aula.get("ativos") or ["EURUSD=X"]),
        sugeridas=", ".join(aula.get("cenas_sugeridas", []) + ["padrao:" + p for p in aula.get("padroes", [])]) or "nenhuma",
        minutos=minutos, palavras=palavras, partes_meio=partes_meio, por_parte=int(palavras * 0.75 / partes_meio),
        estilo=ESTILO, cenas=CENAS)
    dados = _pedir(prompt)
    for _ in range(2):
        if _contar(dados) >= palavras * 0.8 and len(dados.get("partes", [])) >= 4:
            break
        print(f"   aula com {_contar(dados)} palavras (meta {palavras}), pedindo versão maior...")
        dados = _pedir(prompt + f"\n\nATENÇÃO: a versão anterior tinha só {_contar(dados)} palavras. "
                                f"Escreva de novo com NO MÍNIMO {palavras} palavras, desenvolvendo cada parte com exemplos.")
    dados = _revisar(dados, f"Tema da aula: {aula['titulo']}. Nível: {nivel['nome']}.")
    partes = [p for p in dados.get("partes", []) if str(p.get("texto", "")).strip()]
    if len(partes) < 3:
        raise ValueError("A aula veio sem partes suficientes.")
    reserva = f"card:{aula['titulo'][:40]}"
    for p in partes:
        p["texto"] = _fala_limpa(p["texto"])
        p["titulo"] = str(p.get("titulo") or "Parte").strip()[:60]
        p["ancoras"] = _ancoras(p.get("cenas")) or [{"frase": "", "cena": reserva}]
        p["cenas"] = [a["cena"] for a in p["ancoras"]]
    dados["partes"] = partes
    dados["roteiro"] = "\n\n".join(p["texto"] for p in partes)
    dados["cenas"] = [c for p in partes for c in p["cenas"]]
    dados["titulo"] = str(dados.get("titulo") or aula["titulo"])[:95]
    dados.setdefault("assunto", aula["titulo"])
    dados["descricao"] = (f"{str(dados.get('descricao', '')).strip()}\n\n"
                          f"📚 {nivel['emoji']} {nivel['nome']} · Aula {numero:02d}: {aula['titulo']}\n"
                          f"▶ Próxima aula: {proxima or 'em breve'}\n\n{AVISO}")
    print(f"   aula: {len(partes)} partes, {_contar(dados)} palavras")
    return dados


def gerar_noticia(noticia: dict, movimentos: list[dict]) -> dict:
    segundos = 70
    palavras = int(segundos * 2.4)
    fatos = (f"Manchete: {noticia['titulo']}\nFonte: {noticia.get('fonte', '')}\nPublicada: {noticia.get('data', '')}\n"
             f"Outras manchetes sobre o mesmo assunto: {'; '.join(noticia.get('relacionadas', [])[:5]) or 'nenhuma'}\n"
             f"Por que pode mexer (análise preliminar): {noticia.get('motivo', '')}")
    mov = "\n".join(f"- {m['ativo']}: {m['variacao_pct']:+.2f}% de {m['desde']} até {m['ate']} (último {m['ultimo']})"
                    for m in movimentos) or "sem dados agora (não cite números de preço)"
    tickers = ", ".join(noticia.get("ativos") or ["EURUSD=X", "GC=F", "DX-Y.NYB"])
    dados = _pedir(PROMPT_NOTICIA.format(segundos=segundos, palavras=palavras, idioma=config.IDIOMA, fatos=fatos,
                                         movimentos=mov, estilo=ESTILO, tickers=tickers))
    dados = _revisar(dados, "É uma notícia: só valem os fatos e movimentos fornecidos abaixo.\n" + fatos + "\n" + mov)
    dados["roteiro"] = _fala_limpa(dados.get("roteiro", ""))
    if len(dados["roteiro"].split()) < 60:
        raise ValueError("Roteiro da notícia veio curto demais.")
    dados["cenas"] = _limpar_cenas(dados.get("cenas"), f"ativo:{(noticia.get('ativos') or ['GC=F'])[0]}|1h")
    dados["titulo"] = str(dados.get("titulo") or noticia["titulo"])[:95]
    dados.setdefault("assunto", noticia["titulo"][:80])
    fonte = f"\n\n📰 Fonte: {noticia.get('fonte', '')} – {noticia.get('link', '')}".rstrip(" –")
    dados["descricao"] = f"{str(dados.get('descricao', '')).strip()}{fonte}\n\n{AVISO}"
    return dados
