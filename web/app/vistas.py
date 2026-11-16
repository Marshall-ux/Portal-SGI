"""Presentación: cómo se muestran secciones y documentos (títulos, íconos, formatos).

Solo cambia lo que se ve en pantalla; los nombres del disco no se tocan y el buscador
trabaja sin acentos ni mayúsculas, así que encuentra igual.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .indexer import Document, Index, Section

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

    seccion: Section | None  # None: sección con enlace cuya carpeta ya no está en el disco
    titulo: str
    descripcion: str
    icono: str
    enlace: str = ""  # dirección externa que reemplaza al contenido del disco
    enlace_nota: str = ""
    orden: int | None = None


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
        enlace=cfg.get("enlace", ""),
        enlace_nota=cfg.get("enlace_nota", ""),
        orden=section.info.order,
    )


def secciones_enlazadas(config: dict) -> dict[str, str]:
    """Secciones principales que llevan a otro sitio en vez de mostrar el disco: slug → dirección."""
    return {slug: cfg["enlace"] for slug, cfg in config.get("secciones", {}).items() if cfg.get("enlace")}


def secciones_home(index: Index, config: dict) -> list[SeccionVista]:
    """Tarjetas de Documentación de la home: las carpetas del disco más las secciones con
    enlace cuya carpeta ya no está (vacía o borrada), ubicadas por su "orden"."""
    vistas = [vista_seccion(s, config) for s in index.root.sections]
    presentes = {s.slug for s in index.root.sections}
    for slug, cfg in config.get("secciones", {}).items():
        if cfg.get("enlace") and slug not in presentes:
            vistas.append(SeccionVista(
                seccion=None,
                titulo=cfg.get("titulo") or slug,
                descripcion=cfg.get("descripcion", ""),
                icono=cfg.get("icono", "carpeta"),
                enlace=cfg["enlace"],
                enlace_nota=cfg.get("enlace_nota", ""),
                orden=cfg.get("orden"),
            ))
    # Orden estable: entre las del disco se conserva el del índice
    return sorted(vistas, key=lambda v: (v.orden is None, v.orden or 0))


def migas(section: Section, config: dict) -> list[SeccionVista]:
    """Ruta de navegación desde la sección principal hasta esta."""
    return [vista_seccion(s, config) for s in section.breadcrumb]


@dataclass(frozen=True)
class AccesoVista:
    """Un acceso rápido de la home, con el documento al que apunta (None si ya no está)."""

    ruta: str  # dirección configurada en portal.toml
    documento: Document | None
    titulo: str
    icono: str


def accesos_rapidos(index: Index, config: dict) -> list[AccesoVista]:
    """Accesos rápidos de config/portal.toml, en su orden. Si el documento se movió de carpeta
    y su nombre es único, se lo sigue encontrando."""
    accesos = []
    for cfg in config.get("accesos", []):
        ruta = cfg["documento"].strip("/")
        doc = index.document(ruta) or index.moved_document(ruta)
        accesos.append(AccesoVista(
            ruta=ruta,
            documento=doc,
            titulo=cfg.get("titulo") or (doc.info.label if doc else ruta),
            icono=cfg.get("icono", "documento"),
        ))
    return accesos


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
