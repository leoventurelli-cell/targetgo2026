"""Thumbnail das aulas com a foto do Leo recortada (pasta fotos/), variando a cada vídeo:
cor da camisa, lado, tamanho e enquadramento da foto, cores do nível e o layout.

Fotos: coloque PNGs recortados (fundo transparente) em fotos/. Se houver um arquivo "<nome>.camisa.png"
(máscara branca da camisa), a camisa troca de cor. Sem máscara, a foto entra como está.
Desenhado com o Chromium (Playwright); se ele faltar, o vídeo usa a capa simples."""
import base64
import io
import random
from pathlib import Path

import config

PASTA_FOTOS = config.PASTA / "fotos"
CAMISAS = [(25, 45, 95), (190, 25, 35), (20, 120, 70), (40, 40, 45), (235, 180, 30), (245, 245, 245),
           (110, 40, 150), (0, 140, 160), (230, 100, 20)]


def _fotos() -> list[Path]:
    return sorted(p for p in PASTA_FOTOS.glob("*.png") if not p.name.endswith(".camisa.png"))


def _foto_com_camisa(foto: Path, cor) -> str:
    from PIL import Image
    import numpy as np
    img = Image.open(foto).convert("RGBA")
    mascara = foto.with_name(foto.stem + ".camisa.png")
    if mascara.exists() and cor:
        a = np.array(img).astype(float)
        m = np.array(Image.open(mascara).convert("L").resize(img.size)).astype(float)[..., None] / 255
        rgb = a[:, :, :3] / 255
        luz = rgb.mean(2)
        ref = max(float(luz[m[..., 0] > 0.5].max()) if (m > 0.5).any() else 1.0, 0.1)
        novo = np.clip(np.array(cor) / 255 * (0.35 + 0.9 * (luz / ref))[..., None], 0, 1)
        a[:, :, :3] = (rgb * (1 - m) + novo * m) * 255
        img = Image.fromarray(a.astype("uint8"))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _fontes_css() -> str:
    css = ""
    for arq, familia, peso in (("Anton.woff2", "Anton", 400), ("Montserrat-900.woff2", "Montserrat", 900),
                               ("Montserrat-700.woff2", "Montserrat", 700)):
        p = config.PASTA_FONTES / arq
        if p.exists():
            css += (f"@font-face{{font-family:{familia};font-weight:{peso};"
                    f"src:url(data:font/woff2;base64,{base64.b64encode(p.read_bytes()).decode()})}}")
    return css


def _velas(seed: int, c1: str, c2: str, tendencia: float, alpha: float) -> str:
    return f"""<script>
const c=document.querySelector('canvas');c.width=1280;c.height=720;const x=c.getContext('2d');
let s={seed};const r=()=>{{s=(s*9301+49297)%233280;return s/233280}};let p=420;
for(let i=0;i<40;i++){{const o=p;p+=(r()-0.5)*60+({tendencia});const cl=p;const hi=Math.min(o,cl)-r()*30,lo=Math.max(o,cl)+r()*30;
const X=20+i*32;x.globalAlpha={alpha};x.strokeStyle=x.fillStyle=cl<o?'{c1}':'{c2}';x.lineWidth=3;
x.beginPath();x.moveTo(X+9,hi);x.lineTo(X+9,lo);x.stroke();x.fillRect(X,Math.min(o,cl),18,Math.max(4,Math.abs(cl-o)));}}
</script>"""


def _html(texto: str, apoio: str, selo: str, cor: str, foto: str, layout: int, seed: int) -> str:
    palavras = texto.upper().split()
    meio = max(1, len(palavras) // 2)
    l1, l2 = " ".join(palavras[:meio]), " ".join(palavras[meio:])
    grande = 150 if len(texto) <= 14 else 128 if len(texto) <= 22 else 104
    fundos = ["radial-gradient(circle at 70% 45%,#1b4fd6,#06102e 70%)",
              "linear-gradient(90deg,#000 0%,#1a1400 45%,#3d2f00 100%)",
              "conic-gradient(from 200deg at 30% 60%,#1a0400,#4a0d00,#120200,#1a0400)",
              "radial-gradient(circle at 50% 60%,#0e3b2a,#04140e 70%)",
              "radial-gradient(circle at 30% 40%,#2a0a3a,#0a0412 70%)"]
    fundo = fundos[seed % len(fundos)]
    base = f"""<style>{_fontes_css()}
*{{margin:0;box-sizing:border-box}}body{{width:1280px;height:720px;overflow:hidden;position:relative;
font-family:Montserrat,sans-serif;background:{fundo}}}canvas{{position:absolute;inset:0}}
.leo{{position:absolute;bottom:0;filter:drop-shadow(0 0 30px rgba(0,0,0,.75))}}
.fade{{-webkit-mask-image:linear-gradient(to right,transparent 0%,#000 18%,#000 86%,transparent 100%),linear-gradient(#000,#000);
-webkit-mask-size:100% 45%,100% 55%;-webkit-mask-position:bottom,top;-webkit-mask-repeat:no-repeat}}
.big{{font-family:Anton,Impact,sans-serif;text-transform:uppercase;line-height:.95;position:absolute}}
.selo{{position:absolute;top:34px;padding:12px 26px;border-radius:12px;font-weight:900;font-size:30px;
letter-spacing:1px;background:{cor};color:#111}}
.apoio{{position:absolute;font-weight:900;font-size:34px;padding:8px 20px;background:#fff;color:#111;transform:rotate(-2deg)}}
.marca{{position:absolute;bottom:26px;font-weight:900;font-size:28px;letter-spacing:4px;color:#fff;opacity:.9}}
.marca b{{color:{cor}}}</style><canvas></canvas>{_velas(seed, '#ff4d5e', '#2fe38a', random.Random(seed).choice([-5, -2, 2, 5]), .38)}"""
    sombra = "0 8px 0 #000,0 0 40px #000"
    if layout == 0:  # texto à esquerda, foto à direita
        corpo = f"""<img class="leo fade" src="{foto}" style="right:20px;height:700px">
<div class="selo" style="left:40px">{selo}</div>
<div class="big" style="left:40px;top:120px;font-size:{grande}px;color:#fff;text-shadow:{sombra};max-width:720px">{l1}<br>
<span style="color:{cor}">{l2}</span></div>
{f'<div class="apoio" style="left:44px;bottom:110px">{apoio}</div>' if apoio else ''}
<div class="marca" style="left:44px">TARGET<b>GO</b></div>"""
    elif layout == 1:  # close no rosto à esquerda (espelhado), texto à direita
        corpo = f"""<img class="leo" src="{foto}" style="left:-170px;height:1150px;bottom:-470px;transform:scaleX(-1)">
<div class="selo" style="right:40px">{selo}</div>
<div class="big" style="right:40px;top:130px;text-align:right;font-size:{grande - 10}px;color:#fff;text-shadow:{sombra};max-width:640px">{l1}<br>
<span style="color:{cor}">{l2}</span></div>
{f'<div class="apoio" style="right:44px;bottom:110px">{apoio}</div>' if apoio else ''}
<div class="marca" style="left:44px">TARGET<b>GO</b></div>"""
    elif layout == 2:  # foto no canto esquerdo, palavra gigante à direita
        corpo = f"""<img class="leo" src="{foto}" style="left:-70px;height:650px">
<div class="selo" style="right:40px">{selo}</div>
<div class="big" style="right:40px;top:120px;text-align:right;font-size:{grande + 30}px;color:{cor};text-shadow:0 10px 0 #000,0 0 50px #000;max-width:760px">{l1}</div>
<div class="big" style="right:40px;bottom:120px;text-align:right;font-size:86px;color:#fff;text-shadow:{sombra};max-width:760px">{l2}</div>
{f'<div style="position:absolute;right:44px;bottom:60px;color:{cor};font-weight:900;font-size:28px">{apoio}</div>' if apoio else ''}
<div class="marca" style="left:44px;opacity:0">.</div>"""
    else:  # foto menor à direita, texto grande à esquerda com faixa
        corpo = f"""<img class="leo fade" src="{foto}" style="right:30px;height:640px">
<div class="selo" style="left:40px">{selo}</div>
<div class="big" style="left:40px;top:130px;font-size:{grande}px;color:#fff;text-shadow:{sombra};max-width:760px">{l1}</div>
<div class="big" style="left:40px;top:{130 + int(grande * 1.05) * max(1, len(l1) // 16 + 1)}px;font-size:{grande}px;color:#111;background:{cor};padding:0 18px;max-width:760px">{l2}</div>
{f'<div class="apoio" style="left:44px;bottom:110px;transform:rotate(1deg)">{apoio}</div>' if apoio else ''}
<div class="marca" style="left:44px">TARGET<b>GO</b></div>"""
    return f"<html><head><meta charset='utf-8'></head><body>{base}{corpo}</body></html>"


def criar(texto: str, destino: Path, selo: str, cor: str, numero: int, apoio: str = "") -> Path | None:
    """Cria a thumbnail (1280x720 JPG). Devolve None se não houver foto ou Chromium."""
    fotos = _fotos()
    if not fotos:
        print("   (sem fotos em fotos/: usando a capa simples)")
        return None
    rnd = random.Random(numero * 7919)
    foto = fotos[numero % len(fotos)]
    cor_camisa = CAMISAS[numero % len(CAMISAS)]
    layout = numero % 4
    html = _html(texto.strip()[:40] or "AULA", apoio.strip()[:40], selo, cor, _foto_com_camisa(foto, cor_camisa),
                 layout, rnd.randint(1, 9999))
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            nav = p.chromium.launch()
            pagina = nav.new_page(viewport={"width": 1280, "height": 720})
            pagina.set_content(html)
            pagina.wait_for_timeout(400)
            pagina.screenshot(path=str(destino), type="jpeg", quality=92)
            nav.close()
        print(f"   🖼️  thumbnail: layout {layout + 1}, foto {foto.name}, camisa {cor_camisa}")
        return destino
    except Exception as erro:
        print(f"   ⚠️  thumbnail com foto falhou ({str(erro)[:200]}); usando a capa simples")
        return None


if __name__ == "__main__":  # teste: python thumb.py
    for i, (t, a) in enumerate([("Leia o gráfico", "em 10 minutos"), ("O stop que salva", "e quase ninguém usa"),
                                ("Selic explicada", "o juro que manda em tudo"), ("Lote certo conta viva", "")]):
        criar(t, config.PASTA_SAIDA / f"thumb_{i}.jpg", f"🟢 INICIANTE · AULA {i + 1:02d}", "#2fe38a", i, a)
