"""Genera las imágenes del avatar de SGI para el hero de la home a partir del original.

Uso:
    pip install pillow
    python tools/preparar_avatar.py <avatar-original.png> web/app/static/img/avatar

El original (1254×1254, escudo con check sobre un degradé con halo circular) no tiene
transparencia. El dibujo no se modifica: se encuadra en un círculo con borde suavizado,
así se integra con el fondo del portal en lugar de verse como un recuadro.

  avatar-sgi-320.webp / -640.webp   el escudo con su halo

El header y el favicon usan las siglas SGI, no el avatar.
"""
import os
import sys

from PIL import Image, ImageDraw

# Medidas sobre el original de 1254 px (se escalan si el original tiene otro tamaño)
HALO = (626, 607, 560)  # centro x, centro y, radio del encuadre (halo + brillo)
SUAVIZADO = 4           # la máscara se dibuja 4 veces más grande y se reduce: borde sin serrucho


def recorte_circular(img: Image.Image, cx: int, cy: int, r: int) -> Image.Image:
    cuadro = img.crop((cx - r, cy - r, cx + r, cy + r)).convert("RGBA")
    lado = cuadro.width
    mascara = Image.new("L", (lado * SUAVIZADO, lado * SUAVIZADO), 0)
    ImageDraw.Draw(mascara).ellipse((0, 0, lado * SUAVIZADO - 1, lado * SUAVIZADO - 1), fill=255)
    cuadro.putalpha(mascara.resize((lado, lado), Image.LANCZOS))
    return cuadro


def main(origen: str, destino: str) -> None:
    img = Image.open(origen).convert("RGB")
    escala = img.width / 1254
    os.makedirs(destino, exist_ok=True)

    def medir(m):
        return tuple(round(v * escala) for v in m)

    hero = recorte_circular(img, *medir(HALO))
    for lado in (320, 640):
        ruta = os.path.join(destino, f"avatar-sgi-{lado}.webp")
        hero.resize((lado, lado), Image.LANCZOS).save(ruta, "WEBP", quality=90, method=6)
        print(ruta)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
