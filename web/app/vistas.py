"""Presentación: cómo se muestran secciones y documentos (títulos, íconos, formatos).

Solo cambia lo que se ve en pantalla; los nombres del disco no se tocan y el buscador
trabaja sin acentos ni mayúsculas, así que encuentra igual.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .indexer import Document, Section

# Palabras que van en minúscula dentro de un título (salvo al principio)
_MINUSCULAS = {"a", "al", "con", "de", "del", "e", "el", "en", "la", "las", "los", "o", "para",
               "por", "sin", "u", "y"}
# Palabras cortas que no son siglas (las demás de hasta 3 letras se tratan como siglas: SGI, KIA, PV)
_CORTAS_COMUNES = {"fe", "san", "sur", "mes", "año", "uso", "red", "pie"}


def titulo_legible(texto: str) -> str:
    """Nombre de carpeta en mayúsculas → mayúsculas y minúsculas, conservando las siglas.

    "FORMULARIOS GENERALES" → "Formularios Generales"
    "KIA SANTA FE - PV" → "KIA Santa Fe - PV"
    "IN -ADMINISTRACIÓN" → "IN - Administración"
    Un nombre que ya tiene minúsculas se deja como está (salvo los guiones).
    """
    texto = re.sub(r"(?<=\S)\s+-\s*(?=\S)|(?<=\S)\s*-\s+(?=\S)", " - ", " ".join(texto.split()))
    if any(c.islower() for c in texto):
        return texto
    palabras = []
    for i, palabra in enumerate(texto.split(" ")):
        letras = "".join(c for c in palabra if c.isalpha())
        base = letras.lower()
        if i > 0 and base in _MINUSCULAS:
            palabras.append(palabra.lower())
        elif 0 < len(letras) <= 3 and base not in _MINUSCULAS | _CORTAS_COMUNES:
            palabras.append(palabra)  # sigla
        else:
            palabras.append(_capitalizar(palabra.lower()))
    return " ".join(palabras)


def _capitalizar(palabra: str) -> str:
    """Primera letra en mayúscula aunque la palabra empiece con un signo: "(norma)" → "(Norma)"."""
    for i, c in enumerate(palabra):
        if c.isalpha():
            return palabra[:i] + c.upper() + palabra[i + 1:]
    return palabra


@dataclass(frozen=True)
class SeccionVista:
    """Datos de una sección listos para mostrar."""

    seccion: Section
    titulo: str
    descripcion: str
    icono: str


def vista_seccion(section: Section, config: dict) -> SeccionVista:
    """Las secciones principales toman título, descripción e ícono de config/portal.toml."""
    cfg = {}
    if section.parent is not None and section.parent.parent is None:
        cfg = config.get("secciones", {}).get(section.slug, {})
    return SeccionVista(
        seccion=section,
        titulo=cfg.get("titulo") or titulo_legible(section.title),
        descripcion=cfg.get("descripcion", ""),
        icono=cfg.get("icono", "carpeta"),
    )


def migas(section: Section, config: dict) -> list[SeccionVista]:
    """Ruta de navegación desde la sección principal hasta esta."""
    return [vista_seccion(s, config) for s in section.breadcrumb]


_ICONO_FORMATO = {
    "pdf": "pdf",
    "xls": "planilla", "xlsx": "planilla", "xlsm": "planilla", "ods": "planilla",
    "doc": "documento", "docx": "documento", "odt": "documento",
    "ppt": "presentacion", "pptx": "presentacion",
    "mp4": "video",
    "jpg": "imagen", "jpeg": "imagen", "png": "imagen",
}


def icono_documento(doc: Document) -> str:
    return _ICONO_FORMATO.get(doc.primary.ext, "documento")
