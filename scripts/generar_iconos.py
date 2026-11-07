"""Genera el logo "Burbuja con duda" de ¿Le creo?: ui/web/icono-192.png, icono-512.png y logo.svg.

Uso: python scripts/generar_iconos.py
El fondo violeta llena todo el cuadrado (Android recorta el ícono con su propia forma) y la burbuja
queda dentro de la zona segura central, así nunca se corta.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WEB = Path(__file__).resolve().parent.parent / "ui" / "web"
VIOLETA = "#5A3FD0"
BLANCO = "#FFFFFF"
FUENTES = ("C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
           "/System/Library/Fonts/Supplemental/Arial Bold.ttf")

# Geometría en una cuadrícula de 100 × 100 (la misma del SVG)
CUERPO = (18, 24, 82, 66)            # x0, y0, x1, y1 de la burbuja
RADIO = 10
COLA = [(27, 62), (25, 80), (44, 64)]
TEXTO, TEXTO_CENTRO, TEXTO_TAMANO = "¿?", (50, 45.5), 30

SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" aria-label="¿Le creo?">
  <rect width="100" height="100" rx="22" fill="{VIOLETA}"/>
  <rect x="{CUERPO[0]}" y="{CUERPO[1]}" width="{CUERPO[2] - CUERPO[0]}" height="{CUERPO[3] - CUERPO[1]}" rx="{RADIO}" fill="{BLANCO}"/>
  <polygon points="{' '.join(f'{x},{y}' for x, y in COLA)}" fill="{BLANCO}"/>
  <text x="50" y="56" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-weight="700" font-size="{TEXTO_TAMANO}" fill="{VIOLETA}">{TEXTO}</text>
</svg>
"""


def fuente(tamano: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for ruta in FUENTES:
        if Path(ruta).exists():
            return ImageFont.truetype(ruta, tamano)
    return ImageFont.load_default(size=tamano)


def png(lado: int) -> Image.Image:
    escala = 4                                    # se dibuja grande y se reduce: bordes suaves
    s = lado * escala / 100
    img = Image.new("RGB", (lado * escala, lado * escala), VIOLETA)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([c * s for c in CUERPO], radius=RADIO * s, fill=BLANCO)
    d.polygon([(x * s, y * s) for x, y in COLA], fill=BLANCO)
    d.text((TEXTO_CENTRO[0] * s, TEXTO_CENTRO[1] * s), TEXTO, font=fuente(round(TEXTO_TAMANO * s)),
           fill=VIOLETA, anchor="mm")
    return img.resize((lado, lado), Image.LANCZOS)


def main() -> None:
    for lado in (192, 512):
        png(lado).save(WEB / f"icono-{lado}.png", optimize=True)
    (WEB / "logo.svg").write_text(SVG, encoding="utf-8")
    print("Listo: icono-192.png, icono-512.png y logo.svg en", WEB)


if __name__ == "__main__":
    main()
