"""Desenha as imagens das cenas do curso e das notícias (matplotlib), no tamanho do vídeo.

Cenas que o roteiro pode pedir:
  ativo:EURUSD=X            gráfico real de candles (6 meses, diário)
  ativo:GC=F|1h             gráfico real de 5 dias, velas de 1 hora (bom para notícia)
  ativo:EURUSD=X|mm         com médias móveis 20/50/200      |sr  com suporte e resistência marcados
  comparar:GC=F,DX-Y.NYB    dois ou três ativos na mesma escala (variação em %)
  padrao:topo duplo         exemplo didático desenhado (ver PADROES)
  card:Título|linha|linha   quadro com conceito, fórmula ou números da aula
  serie:selic,ipca          séries oficiais do Banco Central (selic, ipca, cdi, dolar)
  juros:1000|1|120          juros compostos x simples (capital | % ao mês | meses), conta exata
"""
import random
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.dates  # noqa: E402,F401
import matplotlib.ticker  # noqa: E402,F401
import numpy as np  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

import config  # noqa: E402
import mercado  # noqa: E402

FUNDO, GRADE, TEXTO, SUAVE = "#0b1020", "#1c2540", "#f2f5ff", "#8a96b8"
ALTA, BAIXA, AMARELO, AZUL, LARANJA = "#26d07c", "#ff4d5e", "#ffd23f", "#4da3ff", "#ff8c1a"

PADROES = ["tendencia de alta", "tendencia de baixa", "lateral", "suporte", "resistencia", "troca de polaridade",
           "rompimento e reteste", "falso rompimento", "topo duplo", "fundo duplo", "oco", "triangulo",
           "martelo", "engolfo de alta", "doji", "estrela cadente", "candle de alta", "candle de baixa",
           "stop e alvo", "fibonacci", "medias moveis"]
NOMES_PADRAO = {"tendencia de alta": "Tendência de alta", "tendencia de baixa": "Tendência de baixa",
                "resistencia": "Resistência", "troca de polaridade": "Troca de polaridade",
                "oco": "Ombro-cabeça-ombro", "triangulo": "Triângulo", "medias moveis": "Médias móveis",
                "lateral": "Mercado lateral"}


def _fonte():
    arq = config.PASTA_FONTES / "Poppins-Bold.ttf"
    if arq.exists():
        try:
            font_manager.fontManager.addfont(str(arq))
            return font_manager.FontProperties(fname=str(arq)).get_name()
        except Exception:
            pass
    return "DejaVu Sans"


FONTE = _fonte()
plt.rcParams.update({"font.family": FONTE, "text.color": TEXTO, "axes.labelcolor": SUAVE,
                     "xtick.color": SUAVE, "ytick.color": SUAVE})


def _figura(w: int, h: int):
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100, facecolor=FUNDO)
    vertical = h > w
    # área livre embaixo para a legenda (no Short a legenda fica no meio-baixo)
    ax = fig.add_axes([0.07, 0.37, 0.86, 0.33] if vertical else [0.05, 0.22, 0.88, 0.62], facecolor=FUNDO)
    for lado in ax.spines.values():
        lado.set_visible(False)
    ax.grid(True, color=GRADE, linewidth=1)
    ax.tick_params(labelsize=22 if vertical else 16, length=0)
    ax.yaxis.tick_right()
    return fig, ax, vertical


def _titulo(fig, texto: str, sub: str, vertical: bool, cor=AMARELO):
    y = 0.745 if vertical else 0.93
    fig.text(0.07 if vertical else 0.05, y, texto, fontsize=56 if vertical else 40, color=TEXTO, weight="bold",
             va="bottom")
    if sub:
        fig.text(0.07 if vertical else 0.05, y - (0.025 if vertical else 0.045), sub, fontsize=28 if vertical else 22,
                 color=cor, va="bottom")


def _rodape(fig, texto: str, vertical: bool):
    fig.text(0.93 if vertical else 0.95, 0.345 if vertical else 0.155, texto, fontsize=18 if vertical else 14,
             color=SUAVE, ha="right")


def _candles(ax, o, hi, lo, c, largura=0.62):
    for i, (a, b, mn, mx) in enumerate(zip(o, c, lo, hi)):
        cor = ALTA if b >= a else BAIXA
        ax.plot([i, i], [mn, mx], color=cor, linewidth=1.6, zorder=2)
        ax.add_patch(Rectangle((i - largura / 2, min(a, b)), largura, max(abs(b - a), (mx - mn) * 0.02 + 1e-9),
                               color=cor, zorder=3))
    ax.set_xlim(-1, len(c) + 1)


def _ohlc_de(fechamentos, ruido=0.35, seed=1):
    rnd = random.Random(seed)
    o, hi, lo = [], [], []
    ant = fechamentos[0]
    for c in fechamentos:
        a = ant + (c - ant) * rnd.uniform(-0.15, 0.25)
        corpo = abs(c - a) + 0.2
        hi.append(max(a, c) + corpo * rnd.uniform(0.1, ruido * 3))
        lo.append(min(a, c) - corpo * rnd.uniform(0.1, ruido * 3))
        o.append(a)
        ant = c
    return o, hi, lo, list(fechamentos)


def _caminho(pontos, n=60, seed=2, ruido=0.6):
    """Liga os pontos (x de 0 a 1, y) com um caminho com ruído: base dos padrões didáticos."""
    rnd = random.Random(seed)
    xs = np.linspace(0, 1, n)
    px, py = zip(*pontos)
    ys = np.interp(xs, px, py)
    return [y + rnd.gauss(0, ruido) for y in ys]


def _seta(ax, x, y, texto, cor, dy):
    ax.annotate(texto, xy=(x, y), xytext=(x, y + dy), color=cor, fontsize=22, weight="bold", ha="center",
                arrowprops=dict(arrowstyle="->", color=cor, lw=3))


def _linha(ax, y, cor, texto, n, estilo="-"):
    ax.axhline(y, color=cor, linewidth=3.5, linestyle=estilo, zorder=4)
    ax.text(n * 0.01, y, f" {texto} ", color=FUNDO, fontsize=20, weight="bold", va="center", zorder=5,
            bbox=dict(facecolor=cor, edgecolor="none", boxstyle="round,pad=0.25"))


def _padrao(ax, nome: str):
    n = nome.lower().replace("ê", "e").replace("é", "e").replace("á", "a").replace("ó", "o").replace("ã", "a")
    if "candle de" in n or n in ("martelo", "doji", "estrela cadente", "engolfo de alta"):
        return _velas_didaticas(ax, n)
    cfg = {
        "tendencia de alta": ([(0, 10), (.2, 16), (.3, 13), (.5, 21), (.6, 18), (.8, 27), (.9, 24), (1, 31)], []),
        "tendencia de baixa": ([(0, 31), (.2, 25), (.3, 28), (.5, 20), (.6, 23), (.8, 14), (.9, 17), (1, 10)], []),
        "lateral": ([(0, 20), (.15, 26), (.3, 14), (.45, 26), (.6, 14), (.75, 26), (.9, 14), (1, 20)],
                    [(26.5, BAIXA, "RESISTÊNCIA"), (13.5, ALTA, "SUPORTE")]),
        "suporte": ([(0, 28), (.25, 14), (.4, 22), (.55, 14.3), (.7, 21), (.85, 14.1), (1, 24)], [(13.6, ALTA, "SUPORTE")]),
        "resistencia": ([(0, 12), (.25, 26), (.4, 18), (.55, 25.7), (.7, 19), (.85, 25.9), (1, 16)],
                        [(26.4, BAIXA, "RESISTÊNCIA")]),
        "troca de polaridade": ([(0, 12), (.2, 22), (.3, 17), (.45, 22.3), (.6, 29), (.75, 22.6), (1, 33)],
                                [(22.4, AMARELO, "RESISTÊNCIA VIRA SUPORTE")]),
        "rompimento e reteste": ([(0, 14), (.15, 22), (.3, 16), (.45, 22.2), (.55, 28), (.7, 22.6), (1, 34)],
                                 [(22.4, AMARELO, "ROMPE → RETESTA → SEGUE")]),
        "falso rompimento": ([(0, 14), (.2, 22), (.35, 16), (.5, 22.1), (.58, 24.5), (.66, 21), (1, 12)],
                             [(22.4, BAIXA, "FALSO ROMPIMENTO")]),
        "topo duplo": ([(0, 10), (.25, 28), (.4, 19), (.55, 28.2), (.75, 17), (1, 9)], [(18.6, AMARELO, "LINHA DE PESCOÇO")]),
        "fundo duplo": ([(0, 30), (.25, 12), (.4, 21), (.55, 11.8), (.75, 23), (1, 31)], [(21.4, AMARELO, "LINHA DE PESCOÇO")]),
        "oco": ([(0, 10), (.15, 22), (.27, 16), (.42, 30), (.57, 16.3), (.72, 22.5), (.85, 15), (1, 8)],
                [(16, AMARELO, "PESCOÇO")]),
        "triangulo": ([(0, 10), (.15, 28), (.3, 13), (.45, 26), (.6, 15.5), (.72, 24), (.82, 17), (.9, 21), (1, 30)], []),
        "stop e alvo": ([(0, 14), (.3, 20), (.45, 17), (.6, 20.5), (1, 30)],
                        [(29, ALTA, "TAKE PROFIT (ALVO)"), (20.3, AZUL, "ENTRADA"), (15.5, BAIXA, "STOP LOSS")]),
        "fibonacci": ([(0, 10), (.45, 32), (.65, 22.5), (1, 36)], []),
        "medias moveis": ([(0, 10), (.3, 18), (.4, 15), (.6, 24), (.7, 21), (1, 32)], []),
    }
    pontos, linhas = cfg.get(n, cfg["tendencia de alta"])
    c = _caminho(pontos, n=64, seed=len(n))
    o, hi, lo, c = _ohlc_de(c, seed=len(n) + 3)
    _candles(ax, o, hi, lo, c)
    for y, cor, texto in linhas:
        _linha(ax, y, cor, texto, len(c), "--" if "PESCOÇO" in texto else "-")
    if n == "fibonacci":
        topo, fundo = 32, 10
        for nivel, cor in ((0.382, AZUL), (0.5, AMARELO), (0.618, LARANJA)):
            y = topo - (topo - fundo) * nivel
            _linha(ax, y, cor, f"{nivel * 100:.1f}%".replace(".", ","), len(c), "--")
    if n == "triangulo":
        ax.plot([2, 58], [28.5, 21.5], color=BAIXA, linewidth=3)
        ax.plot([12, 58], [12.5, 20.5], color=ALTA, linewidth=3)
    if n == "medias moveis":
        s = np.array(c)
        for p, cor in ((8, AMARELO), (20, AZUL)):
            m = np.convolve(s, np.ones(p) / p, mode="valid")
            ax.plot(range(p - 1, len(s)), m, color=cor, linewidth=3.5, label=f"média {p}")
        ax.legend(facecolor=FUNDO, edgecolor=GRADE, labelcolor=TEXTO, fontsize=18, loc="upper left")
    if "tendencia" in n:
        ref = [p for p in pontos]
        for i, (x, y) in enumerate(ref[1:-1], 1):
            alto = (y > ref[i - 1][1]) and (y > ref[i + 1][1])
            ax.text(x * 63, y + (2.2 if alto else -3.2), "TOPO" if alto else "FUNDO", color=AMARELO if alto else AZUL,
                    fontsize=18, weight="bold", ha="center")
    ax.set_yticklabels([])
    ax.set_xticklabels([])


def _velas_didaticas(ax, n):
    """Uma ou duas velas grandes com as partes nomeadas."""
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.grid(False)

    def vela(x, a, c, mn, mx, larg=1.6):
        cor = ALTA if c >= a else BAIXA
        ax.plot([x, x], [mn, mx], color=cor, linewidth=6)
        ax.add_patch(Rectangle((x - larg / 2, min(a, c)), larg, max(abs(c - a), 0.12), color=cor))

    if n == "candle de alta" or n == "candle de baixa":
        alta = n == "candle de alta"
        a, c = (3.5, 7) if alta else (7, 3.5)
        vela(3, a, c, 1.5, 9)
        for y, t in ((9, "MÁXIMA"), (1.5, "MÍNIMA"), (c, "FECHAMENTO"), (a, "ABERTURA")):
            ax.annotate(t, xy=(3.9 if t in ("ABERTURA", "FECHAMENTO") else 3.1, y), xytext=(6, y), color=TEXTO,
                        fontsize=24, weight="bold", va="center", arrowprops=dict(arrowstyle="->", color=SUAVE, lw=2))
        ax.text(3, 0.3, "CANDLE DE ALTA" if alta else "CANDLE DE BAIXA", color=ALTA if alta else BAIXA,
                fontsize=26, weight="bold", ha="center")
    elif n == "martelo":
        vela(4, 6.8, 7.6, 2.2, 7.9)
        ax.text(6, 5, "PAVIO LONGO EMBAIXO:\nCOMPRADORES REAGIRAM", color=TEXTO, fontsize=22, weight="bold", va="center")
    elif n == "estrela cadente":
        vela(4, 3.2, 2.4, 2.1, 8)
        ax.text(6, 5, "PAVIO LONGO EM CIMA:\nVENDEDORES REAGIRAM", color=TEXTO, fontsize=22, weight="bold", va="center")
    elif n == "doji":
        vela(4, 5, 5.05, 2, 8)
        ax.text(6, 5, "ABRIU E FECHOU\nNO MESMO PREÇO:\nINDECISÃO", color=TEXTO, fontsize=22, weight="bold", va="center")
    else:  # engolfo de alta
        vela(3, 6, 4.5, 4, 6.4, 1.2)
        vela(5, 4.2, 7.4, 3.8, 7.8, 1.6)
        ax.text(6.6, 5.5, "A VELA VERDE\n\"ENGOLE\" A\nVERMELHA", color=TEXTO, fontsize=22, weight="bold", va="center")


def _ativo(ax, fig, spec: str, vertical: bool):
    partes = spec.split("|")
    tk = mercado.ticker(partes[0])
    opcoes = [p.strip().lower() for p in partes[1:]]
    intraday = any(o in ("1h", "60m", "intraday", "hora") for o in opcoes)
    d = mercado.cotacoes(tk, "5d" if intraday else "6mo", "60m" if intraday else "1d")
    if d is None:
        return False
    d = d.tail(90 if not vertical else 60)
    o, hi, lo, c = (d[k].tolist() for k in ("Open", "High", "Low", "Close"))
    _candles(ax, o, hi, lo, c)
    marcas = list(range(0, len(c), max(1, len(c) // 5)))
    ax.set_xticks(marcas)
    ax.set_xticklabels([d.index[i].strftime("%d/%m %Hh" if intraday else "%d/%m") for i in marcas])
    casas = 4 if c[-1] < 20 else 2
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.{casas}f}".replace(",", "X")
                                                                  .replace(".", ",").replace("X", ".")))
    if "mm" in opcoes:
        s = d["Close"]
        for p, cor in ((20, AMARELO), (50, AZUL), (200, LARANJA)):
            if len(s) > p:
                ax.plot(range(len(s)), s.rolling(p).mean(), color=cor, linewidth=3, label=f"média {p}")
        ax.legend(facecolor=FUNDO, edgecolor=GRADE, labelcolor=TEXTO, fontsize=16, loc="upper left")
    if "sr" in opcoes:
        topo, fundo = max(hi[-40:]), min(lo[-40:])
        _linha(ax, topo, BAIXA, "RESISTÊNCIA", len(c), "--")
        _linha(ax, fundo, ALTA, "SUPORTE", len(c), "--")
    var = (c[-1] / c[0] - 1) * 100
    _titulo(fig, mercado.nome(tk), f"{'últimos 5 dias' if intraday else 'últimos meses'} · "
                                   f"{'+' if var >= 0 else ''}{var:.2f}%".replace(".", ","), vertical,
            ALTA if var >= 0 else BAIXA)
    _rodape(fig, f"Fonte: dados de mercado até {d.index[-1]:%d/%m/%Y}", vertical)
    return True


def _comparar(ax, fig, spec: str, vertical: bool):
    cores = [AMARELO, AZUL, LARANJA]
    ok = False
    for tk, cor in zip([mercado.ticker(t) for t in spec.split(",")][:3], cores):
        d = mercado.cotacoes(tk, "6mo", "1d")
        if d is None:
            continue
        s = d["Close"] / d["Close"].iloc[0] * 100 - 100
        ax.plot(range(len(s)), s.values, color=cor, linewidth=4, label=mercado.nome(tk))
        ok = True
    if not ok:
        return False
    ax.axhline(0, color=SUAVE, linewidth=1.5)
    ax.legend(facecolor=FUNDO, edgecolor=GRADE, labelcolor=TEXTO, fontsize=20, loc="upper left")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
    ax.set_xticklabels([])
    _titulo(fig, "Comparando os mercados", "variação nos últimos meses", vertical)
    _rodape(fig, "Fonte: dados de mercado", vertical)
    return True


def _card(destino: Path, spec: str, w: int, h: int):
    linhas = [x.strip() for x in spec.split("|") if x.strip()]
    titulo, resto = (linhas[0], linhas[1:]) if linhas else ("", [])
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100, facecolor=FUNDO)
    vertical = h > w
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    # papel com grade de gráfico ao fundo
    for x in np.linspace(0, 1, 25):
        ax.axvline(x, color=GRADE, linewidth=0.6, alpha=0.6)
    for y in np.linspace(0, 1, 15):
        ax.axhline(y, color=GRADE, linewidth=0.6, alpha=0.6)
    caixa = (0.08, 0.40, 0.84, 0.44) if vertical else (0.08, 0.20, 0.84, 0.61)
    ax.add_patch(FancyBboxPatch(caixa[:2], caixa[2], caixa[3], boxstyle="round,pad=0.01,rounding_size=0.03",
                                facecolor="#121a33", edgecolor=AMARELO, linewidth=4))
    topo = caixa[1] + caixa[3] - 0.06
    ax.text(0.5, topo, titulo.upper(), ha="center", va="top", fontsize=60 if vertical else 50, color=AMARELO,
            weight="bold", wrap=True)
    passo = (caixa[3] - 0.16) / max(len(resto), 1)
    tam = 44 if vertical else 36
    for i, linha in enumerate(resto[:6]):
        ax.text(0.5, topo - 0.12 - i * min(passo, 0.08 if vertical else 0.1), linha, ha="center", va="top",
                fontsize=tam, color=TEXTO, weight="bold")
    fig.savefig(destino, dpi=100, facecolor=FUNDO)
    plt.close(fig)
    return True


SERIES_BCB = {"selic": (432, "Taxa Selic (meta, % ao ano)"), "ipca": (13522, "Inflação IPCA (12 meses, %)"),
              "cdi": (4389, "CDI (% ao ano)"), "dolar": (1, "Dólar comercial (R$)")}


def _serie_bcb(codigo: int, anos: int = 10):
    """Séries oficiais do Banco Central (API SGS, grátis)."""
    import requests
    from datetime import date
    hoje = date.today()
    ini = date(hoje.year - anos, hoje.month, 1)
    r = requests.get(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados",
                     params={"formato": "json", "dataInicial": ini.strftime("%d/%m/%Y"),
                             "dataFinal": hoje.strftime("%d/%m/%Y")}, timeout=40)
    r.raise_for_status()
    dados = r.json()
    from datetime import datetime as dt
    return [dt.strptime(x["data"], "%d/%m/%Y") for x in dados], [float(str(x["valor"]).replace(",", ".")) for x in dados]


def _serie(ax, fig, valor: str, vertical: bool):
    nomes = [v.strip().lower() for v in valor.split(",") if v.strip()][:2]
    cores = [AMARELO, AZUL]
    ultimo = None
    for nome_s, cor in zip(nomes, cores):
        if nome_s not in SERIES_BCB:
            continue
        codigo, rotulo = SERIES_BCB[nome_s]
        datas, vals = _serie_bcb(codigo)
        if not vals:
            continue
        ax.plot(datas, vals, color=cor, linewidth=4, label=rotulo)
        ultimo = datas[-1]
    if ultimo is None:
        return False
    ax.legend(facecolor=FUNDO, edgecolor=GRADE, labelcolor=TEXTO, fontsize=20, loc="upper left")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y"))
    _titulo(fig, "Dados do Banco Central", "últimos 10 anos", vertical)
    _rodape(fig, f"Fonte: Banco Central do Brasil (SGS), até {ultimo:%m/%Y}", vertical)
    return True


def _juros(ax, fig, valor: str, vertical: bool):
    """juros:capital|taxa ao mês em %|meses  → juros compostos x juros simples (conta exata)."""
    partes = [p.strip().replace(",", ".") for p in valor.split("|")]
    capital = float(partes[0]) if partes and partes[0] else 1000.0
    taxa = (float(partes[1]) if len(partes) > 1 else 1.0) / 100
    meses = int(float(partes[2])) if len(partes) > 2 else 120
    m = np.arange(meses + 1)
    comp = capital * (1 + taxa) ** m
    simp = capital * (1 + taxa * m)
    ax.plot(m, comp, color=ALTA, linewidth=5, label="juros compostos")
    ax.plot(m, simp, color=SUAVE, linewidth=4, linestyle="--", label="juros simples")
    fmt = lambda v: "R$ " + f"{v:,.0f}".replace(",", ".")
    ax.text(meses, comp[-1], f" {fmt(comp[-1])}", color=ALTA, fontsize=24, weight="bold", va="center", ha="right")
    ax.text(meses, simp[-1] - (comp[-1] - capital) * 0.04, f"{fmt(simp[-1])}", color=SUAVE, fontsize=22,
            weight="bold", va="top", ha="right")
    ax.legend(facecolor=FUNDO, edgecolor=GRADE, labelcolor=TEXTO, fontsize=20, loc="upper left")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: fmt(v)))
    ax.set_xlabel("meses", fontsize=18)
    _titulo(fig, f"{fmt(capital)} a {f'{taxa * 100:.2f}'.rstrip('0').rstrip('.').replace('.', ',')}% ao mês",
            f"em {meses} meses", vertical, ALTA)
    _rodape(fig, "Simulação matemática, sem impostos e taxas", vertical)
    return True


def gerar(spec: str, destino: Path, w: int, h: int) -> bool:
    """Desenha a cena pedida em `destino` (PNG). Devolve False se não deu (ex.: cotação fora do ar)."""
    tipo, _, valor = spec.partition(":")
    tipo, valor = tipo.strip().lower(), valor.strip()
    try:
        if tipo == "card":
            return _card(destino, valor, w, h)
        fig, ax, vertical = _figura(w, h)
        if tipo == "ativo":
            ok = _ativo(ax, fig, valor, vertical)
            if not ok:  # sem cotação: mostra o mesmo tipo de movimento, como exemplo
                plt.close(fig)
                fig, ax, vertical = _figura(w, h)
                _padrao(ax, "tendencia de alta")
                _titulo(fig, mercado.nome(mercado.ticker(valor.split("|")[0])), "exemplo ilustrativo", vertical)
                _rodape(fig, "Exemplo ilustrativo (cotação indisponível agora)", vertical)
        elif tipo in ("serie", "juros"):
            if not (_serie if tipo == "serie" else _juros)(ax, fig, valor, vertical):
                plt.close(fig)
                return False
        elif tipo == "comparar":
            if not _comparar(ax, fig, valor, vertical):
                plt.close(fig)
                return False
        else:  # padrao
            chave = valor.lower().replace("ê", "e").replace("â", "a").replace("é", "e").replace("á", "a")
            _padrao(ax, valor)
            _titulo(fig, NOMES_PADRAO.get(chave, valor).upper(), "exemplo didático", vertical)
            _rodape(fig, "Exemplo didático, não é recomendação", vertical)
        fig.savefig(destino, dpi=100, facecolor=FUNDO)
        plt.close(fig)
        return True
    except Exception as erro:
        print(f"   ⚠️  gráfico '{spec}' falhou: {erro}")
        plt.close("all")
        return False


if __name__ == "__main__":  # teste rápido: python graficos.py
    pasta = Path("saida/teste_graficos")
    pasta.mkdir(parents=True, exist_ok=True)
    for i, s in enumerate(["padrao:" + p for p in PADROES] + ["card:Risco por operação|1% da conta|Stop de 20 pips|Lote 0,05",
                                                               "ativo:EURUSD=X|mm", "ativo:GC=F|1h"]):
        gerar(s, pasta / f"g{i:02d}.png", 1920, 1080)
    print("ok")
