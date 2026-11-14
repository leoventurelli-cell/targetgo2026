"""Radar de notícias de mercado: olha as manchetes recentes (Google Notícias, grátis) e escolhe a que mais
pode mexer com dólar, ouro, índices, juros e petróleo. Só vira vídeo se o impacto for alto."""
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests

import config
from roteiro import _pedir_ao_gemini, _pedir_ao_groq

BUSCAS = [
    ("pt-BR", "BR", "BR:pt-419", ["Fed juros", "Copom Selic", "payroll Estados Unidos", "inflação Estados Unidos CPI",
                                   "dólar hoje mercado", "preço do ouro", "petróleo Opep", "Banco Central Europeu juros",
                                   "Powell", "Ibovespa hoje", "IPCA inflação", "Galípolo Banco Central"]),
    ("en-US", "US", "US:en", ["Federal Reserve rates", "CPI inflation report", "nonfarm payrolls", "ECB interest rate",
                              "gold price", "oil prices OPEC", "dollar index", "stock market today"]),
]
UA = {"User-Agent": "Mozilla/5.0 (TargetGoBot; +https://github.com)"}

PROMPT = """Você é editor de mercado financeiro de um canal educativo brasileiro (forex, ouro, índices, juros, dólar).
Abaixo estão manchetes das últimas horas (algumas em inglês). Agora são {agora} (Brasília).

Assuntos que JÁ viraram vídeo recentemente (não repita o mesmo fato): {feitos}

Manchetes:
{lista}

Escolha UMA manchete (a de maior potencial de mexer com os mercados HOJE): decisões ou falas de bancos centrais
(Fed, BCE, Copom), dados de inflação, emprego (payroll), PIB, tarifas e guerras comerciais, choques no petróleo,
crises que mexem com dólar, ouro, índices ou o real. Ignore notícias velhas, repetidas, só de empresa pequena,
opinião, previsão de "analista diz que vai subir", ou tragédias com vítimas.
Dê nota de impacto de 0 a 10 (10 = decisão de juros do Fed fora do esperado; 7 = dado relevante que mexeu com
vários mercados; abaixo de 7 = não vale vídeo).

Responda SOMENTE com JSON:
{{"indice": número da manchete escolhida, "impacto": 0-10, "assunto": "fato em poucas palavras, em português",
"motivo": "1 ou 2 frases: por que pode mexer e em quais mercados",
"ativos": ["até 3 tickers entre EURUSD=X, GBPUSD=X, USDJPY=X, BRL=X, GC=F, CL=F, ^GSPC, ^IXIC, ^BVSP, DX-Y.NYB, BTC-USD"],
"relacionadas": [índices de outras manchetes sobre o MESMO fato]}}"""


def _manchetes(horas: int = 8) -> list[dict]:
    limite = datetime.now(timezone.utc) - timedelta(hours=horas)
    vistas, itens = set(), []
    for hl, gl, ceid, termos in BUSCAS:
        for termo in termos:
            url = (f"https://news.google.com/rss/search?q={urllib.parse.quote(termo + ' when:1d')}"
                   f"&hl={hl}&gl={gl}&ceid={ceid}")
            try:
                raiz = ET.fromstring(requests.get(url, headers=UA, timeout=25).content)
            except Exception as erro:
                print(f"   (busca '{termo}' falhou: {erro})")
                continue
            for item in raiz.iter("item"):
                titulo = (item.findtext("title") or "").strip()
                try:
                    data = parsedate_to_datetime(item.findtext("pubDate") or "")
                except Exception:
                    continue
                if data < limite:
                    continue
                fonte = (item.findtext("source") or "").strip()
                titulo_limpo = re.sub(r"\s+-\s+[^-]+$", "", titulo)
                chave = re.sub(r"\W+", " ", titulo_limpo.lower())[:60]
                if not titulo_limpo or chave in vistas:
                    continue
                vistas.add(chave)
                itens.append({"titulo": titulo_limpo, "fonte": fonte, "link": item.findtext("link") or "",
                              "data": data.astimezone(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M")})
    itens.sort(key=lambda x: x["data"], reverse=True)
    return itens[:80]


def escolher(feitos: list[str], minimo: int | None = None) -> dict | None:
    """Devolve a notícia escolhida (com 'motivo', 'ativos', 'relacionadas') ou None se nada for forte o bastante."""
    minimo = int(minimo if minimo is not None else config.NOTICIA_IMPACTO_MINIMO)
    itens = _manchetes()
    print(f"📰 {len(itens)} manchetes recentes")
    if not itens:
        return None
    agora = datetime.now(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M")
    lista = "\n".join(f"{i}. [{x['data']}] {x['titulo']} ({x['fonte']})" for i, x in enumerate(itens))
    pedir = _pedir_ao_groq if config.GROQ_API_KEY else _pedir_ao_gemini
    r = pedir(PROMPT.format(agora=agora, feitos="; ".join(feitos[-15:]) or "nenhum", lista=lista))
    try:
        idx, nota = int(r.get("indice", -1)), float(r.get("impacto", 0))
    except (TypeError, ValueError):
        return None
    if not 0 <= idx < len(itens):
        return None
    escolhida = {**itens[idx], "impacto": nota, "assunto": str(r.get("assunto") or itens[idx]["titulo"]),
                 "motivo": str(r.get("motivo", "")), "ativos": [str(a) for a in r.get("ativos", [])][:3],
                 "relacionadas": [itens[int(j)]["titulo"] for j in r.get("relacionadas", [])
                                  if str(j).isdigit() and 0 <= int(j) < len(itens) and int(j) != idx]}
    print(f"   → impacto {nota:.0f}/10: {escolhida['titulo']} ({escolhida['fonte']})")
    if nota < minimo:
        print(f"   impacto abaixo de {minimo}: sem vídeo agora.")
        return None
    return escolhida


if __name__ == "__main__":
    print(json.dumps(escolher([], minimo=0), ensure_ascii=False, indent=1))
