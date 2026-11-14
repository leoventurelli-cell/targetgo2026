"""Cotações reais (grátis) para os gráficos: Yahoo Finance (yfinance), com Stooq de reserva.
Se nenhum responder, devolve None e o gráfico vira exemplo ilustrativo (com aviso na tela)."""
import io

import requests

NOMES = {
    "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY", "AUDUSD=X": "AUD/USD",
    "USDCAD=X": "USD/CAD", "USDCHF=X": "USD/CHF", "BRL=X": "USD/BRL", "GC=F": "Ouro (XAU/USD)",
    "SI=F": "Prata", "CL=F": "Petróleo WTI", "BZ=F": "Petróleo Brent", "^GSPC": "S&P 500", "^IXIC": "Nasdaq",
    "^DJI": "Dow Jones", "^BVSP": "Ibovespa", "DX-Y.NYB": "Índice do dólar (DXY)", "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum", "^TNX": "Juros EUA 10 anos",
}
# Yahoo → Stooq (reserva)
STOOQ = {"EURUSD=X": "eurusd", "GBPUSD=X": "gbpusd", "USDJPY=X": "usdjpy", "AUDUSD=X": "audusd",
         "USDCAD=X": "usdcad", "USDCHF=X": "usdchf", "BRL=X": "usdbrl", "GC=F": "xauusd", "SI=F": "xagusd",
         "CL=F": "cl.f", "^GSPC": "^spx", "^IXIC": "^ndq", "^DJI": "^dji", "^BVSP": "^bvp",
         "BTC-USD": "btcusd", "DX-Y.NYB": "dx.f"}
APELIDOS = {"eurusd": "EURUSD=X", "eur/usd": "EURUSD=X", "gbpusd": "GBPUSD=X", "usdjpy": "USDJPY=X",
            "xauusd": "GC=F", "ouro": "GC=F", "gold": "GC=F", "usdbrl": "BRL=X", "dolar": "BRL=X",
            "dólar": "BRL=X", "dxy": "DX-Y.NYB", "petroleo": "CL=F", "petróleo": "CL=F", "sp500": "^GSPC",
            "s&p 500": "^GSPC", "nasdaq": "^IXIC", "ibovespa": "^BVSP", "bitcoin": "BTC-USD", "btc": "BTC-USD"}


def ticker(texto: str) -> str:
    t = str(texto or "").strip()
    return APELIDOS.get(t.lower(), t)


def nome(tk: str) -> str:
    return NOMES.get(tk, tk.replace("=X", "").replace("-USD", "/USD"))


def _yahoo(tk: str, periodo: str, intervalo: str):
    import yfinance as yf
    d = yf.download(tk, period=periodo, interval=intervalo, progress=False, auto_adjust=False, threads=False)
    if d is None or d.empty:
        return None
    if hasattr(d.columns, "levels"):  # colunas (Campo, Ticker)
        d.columns = [c[0] for c in d.columns]
    d = d[["Open", "High", "Low", "Close"]].dropna()
    return d if len(d) >= 10 else None


def _stooq(tk: str, periodo: str, intervalo: str):
    import pandas as pd
    codigo = STOOQ.get(tk)
    if not codigo or intervalo not in ("1d", "1wk"):
        return None
    r = requests.get(f"https://stooq.com/q/d/l/?s={codigo}&i={'d' if intervalo == '1d' else 'w'}", timeout=30)
    if not r.ok or "Date" not in r.text[:50]:
        return None
    d = pd.read_csv(io.StringIO(r.text), parse_dates=["Date"], index_col="Date")
    dias = {"1mo": 31, "3mo": 92, "6mo": 183, "1y": 365, "2y": 730, "5y": 1825}.get(periodo, 183)
    d = d[d.index >= d.index.max() - pd.Timedelta(days=dias)][["Open", "High", "Low", "Close"]].dropna()
    return d if len(d) >= 10 else None


def cotacoes(tk: str, periodo: str = "6mo", intervalo: str = "1d"):
    """DataFrame com Open/High/Low/Close (índice = data) ou None."""
    tk = ticker(tk)
    for fonte in (_yahoo, _stooq):
        try:
            d = fonte(tk, periodo, intervalo)
            if d is not None:
                return d
        except Exception as erro:
            print(f"   (cotação {tk} via {fonte.__name__[1:]} falhou: {str(erro)[:120]})")
    return None


def variacao(tk: str, periodo: str = "5d", intervalo: str = "60m") -> dict | None:
    """Resumo do movimento recente, para a IA não inventar número: último preço e variação no período."""
    d = cotacoes(tk, periodo, intervalo)
    if d is None:
        return None
    ini, fim = float(d["Close"].iloc[0]), float(d["Close"].iloc[-1])
    return {"ativo": nome(ticker(tk)), "ultimo": round(fim, 5 if fim < 20 else 2),
            "variacao_pct": round((fim / ini - 1) * 100, 2), "desde": str(d.index[0])[:16],
            "ate": str(d.index[-1])[:16]}
