"""Reporte del disco para SGI: qué revisar, agrupado por tipo y con qué hacer en cada caso.

Sale de los avisos que junta el indexador en cada escaneo, así que se actualiza solo
después de cada sincronización.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from .indexer import Index, Issue
from .versions import natural_key


@dataclass(frozen=True)
class TipoAviso:
    clave: str
    titulo: str
    que_hacer: str
    abierto: bool = True  # los de prioridad baja se muestran plegados


# En orden de prioridad
TIPOS = (
    TipoAviso("conflicto_revision", "La versión más nueva no es la de mayor revisión",
              "Revisar cuál es la vigente. El portal publica la de fecha más reciente: si alguien abrió y "
              "guardó una revisión vieja, quedó como vigente. Corregir el archivo o borrar el que sobra."),
    TipoAviso("versiones_anteriores", "Versiones anteriores en la misma carpeta",
              "Retirar del disco la versión anterior (el portal ya publica solo la vigente)."),
    TipoAviso("sin_revision", "Documentos con código y sin revisión",
              "Agregar la revisión al nombre: «CÓDIGO - Nombre_Rev.NN»."),
    TipoAviso("doble_extension", "Extensión repetida en el nombre",
              "Renombrar quitando la extensión repetida (por ejemplo «.pdf.pdf» → «.pdf»)."),
    TipoAviso("guion_bajo_inicial", "Nombres que empiezan con guion bajo",
              "Renombrar quitando el guion bajo inicial."),
    TipoAviso("carpeta_vacia", "Carpetas sin documentos",
              "Agregar documentos o eliminar la carpeta (el portal no la muestra mientras esté vacía)."),
    TipoAviso("enlace_ignorado", "Enlaces o accesos directos",
              "Reemplazar el enlace por el archivo real: el portal no publica enlaces."),
    TipoAviso("revision_no_estandar", "Revisión escrita distinto de «_Rev.NN»",
              "El portal las reconoce igual. Al publicar la próxima revisión, usar el formato «_Rev.NN» "
              "sin espacios ni datos agregados.", abierto=False),
    TipoAviso("excluido", "Archivos que el portal no publica",
              "Nada: el portal los oculta a propósito (Thumbs.db, temporales de Office, configuración del "
              "servidor y la Guía de Acceso del sitio anterior). Si alguno debería publicarse, avisar a I+D "
              "para ajustar las exclusiones.", abierto=False),
)

INFORMATIVOS = {"excluido"}  # no cuentan como avisos para corregir


@dataclass
class Grupo:
    tipo: TipoAviso
    avisos: list[Issue] = field(default_factory=list)


def agrupar(index: Index) -> list[Grupo]:
    """Avisos del índice agrupados por tipo, en orden de prioridad; solo los tipos con avisos."""
    por_tipo: dict[str, list[Issue]] = {t.clave: [] for t in TIPOS}
    for issue in index.issues:
        por_tipo.setdefault(issue.kind, []).append(issue)
    por_tipo["excluido"] = [Issue("excluido", ruta) for ruta in index.excluded]
    grupos = []
    for tipo in TIPOS:
        avisos = sorted(por_tipo[tipo.clave], key=lambda i: natural_key(i.relpath))
        if avisos:
            grupos.append(Grupo(tipo, avisos))
    return grupos


def a_corregir(grupos: list[Grupo]) -> int:
    return sum(len(g.avisos) for g in grupos if g.tipo.clave not in INFORMATIVOS)


def ruta_disco(relpath: str, prefijo: str) -> str:
    """Ruta como la ve SGI en el explorador de Windows: I:\\01. MANUALES…\\archivo.pdf"""
    return prefijo + relpath.rstrip("/").replace("/", "\\")


def a_csv(grupos: list[Grupo], prefijo: str) -> str:
    """CSV para abrir en Excel (separador «;», como usa Excel en castellano)."""
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";", lineterminator="\r\n")
    escritor.writerow(["Tipo", "Qué hacer", "Ruta en el disco", "Detalle"])
    for grupo in grupos:
        for aviso in grupo.avisos:
            escritor.writerow([grupo.tipo.titulo, grupo.tipo.que_hacer, ruta_disco(aviso.relpath, prefijo), aviso.detail])
    return salida.getvalue()
