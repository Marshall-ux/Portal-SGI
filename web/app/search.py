"""Buscador de documentos y secciones.

Busca por nombre, código o carpeta, sin acentos ni mayúsculas. Cada palabra de la
consulta tiene que ser el comienzo de alguna palabra del documento o de las carpetas
donde está ("capacit" encuentra "Capacitación"; "7.2-01" encuentra "F 7.2-01").
Primero aparecen los documentos cuyo nombre contiene la consulta tal cual.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .indexer import Document, Index, Section
from .versions import natural_key, normalize
from .vistas import titulo_legible

LIMITE = 200


@dataclass
class Resultados:
    consulta: str
    documentos: list[Document] = field(default_factory=list)
    secciones: list[Section] = field(default_factory=list)
    total_documentos: int = 0  # antes de aplicar el límite


def _palabras(texto: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalize(texto))


def _coincide(tokens: list[str], palabras: list[str]) -> bool:
    return all(any(p.startswith(t) for p in palabras) for t in tokens)


def _frase_en(frase: str, texto: str) -> bool:
    """La frase aparece en el texto empezando en un comienzo de palabra."""
    return f" {texto} ".find(f" {frase}") >= 0


def buscar(index: Index, consulta: str, dentro: Section | None = None, limite: int = LIMITE) -> Resultados:
    tokens = _palabras(consulta)
    resultados = Resultados(consulta=consulta.strip())
    if not tokens:
        return resultados
    frase = " ".join(tokens)
    raiz = dentro or index.root

    encontrados = []
    for section in raiz.walk():
        if section is not raiz and _coincide(tokens, _palabras(f"{section.title} {titulo_legible(section.title)}")):
            resultados.secciones.append(section)
        ruta = _palabras(" ".join(s.title for s in section.breadcrumb))
        for doc in section.documents:
            propias = doc.key.split()
            if not _coincide(tokens, propias + ruta):
                continue
            puntaje = 0
            if _frase_en(frase, doc.key):
                puntaje += 100 + (50 if doc.key.startswith(frase) else 0)
            if _coincide(tokens, propias):
                puntaje += 20  # coincide por su propio nombre, no solo por la carpeta
            encontrados.append((-puntaje, natural_key(doc.info.label), doc))

    encontrados.sort(key=lambda e: e[:2])
    resultados.total_documentos = len(encontrados)
    resultados.documentos = [doc for *_, doc in encontrados[:limite]]
    resultados.secciones.sort(key=lambda s: (len(s.breadcrumb), natural_key(s.title)))
    return resultados
