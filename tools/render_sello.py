"""Genera las imágenes del sello de certificación a partir del PDF vectorial del certificador.

Uso (una vez, o cuando se renueve la certificación):
    pip install pymupdf
    python tools/render_sello.py <sello.pdf> <salida-sin-extension>

Ejemplo:
    python tools/render_sello.py "TR-Testmark_9000015845_ES_CMYK_with-QR-Code.pdf" \
        web/app/static/img/certificacion/tuv-rheinland-9000015845

Genera <salida>-1200.png y <salida>-2400.png (ancho en píxeles).

La marca del certificador no se modifica: se renderiza la página completa del PDF
(sin recortes), con sus proporciones, sobre fondo blanco y con conversión de color
gestionada por ICC (el original es CMYK). Se usa PNG y no SVG porque el sello tiene
degradés y biseles que la conversión a SVG no garantiza idénticos; el QR es vectorial
en el PDF y a estas resoluciones queda nítido y escaneable.
"""
import sys

import pymupdf

ANCHOS = (1200, 2400)


def main(pdf: str, salida: str) -> None:
    pymupdf.TOOLS.set_icc(True)  # CMYK → sRGB con perfiles de color, no con fórmula
    doc = pymupdf.open(pdf)
    if doc.page_count != 1:
        raise SystemExit(f"Se esperaba un PDF de una página y tiene {doc.page_count}")
    page = doc[0]
    for ancho in ANCHOS:
        escala = ancho / page.rect.width
        pix = page.get_pixmap(matrix=pymupdf.Matrix(escala, escala), colorspace=pymupdf.csRGB, alpha=False)
        destino = f"{salida}-{ancho}.png"
        pix.save(destino)
        print(f"{destino}: {pix.width}x{pix.height}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
