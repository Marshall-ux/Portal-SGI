"""Filtros de plantillas: fechas, tamaños y formatos en castellano."""
from __future__ import annotations

from datetime import datetime

from flask import Flask

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre")

FORMATOS = {
    "pdf": "PDF",
    "doc": "Word", "docx": "Word", "odt": "Writer",
    "xls": "Excel", "xlsx": "Excel", "xlsm": "Excel", "ods": "Calc",
    "ppt": "PowerPoint", "pptx": "PowerPoint",
    "mp4": "Video",
    "jpg": "Imagen", "jpeg": "Imagen", "png": "Imagen",
}


def fecha_larga(valor: datetime | None) -> str:
    """3 de noviembre de 2026, 06:00 h"""
    if valor is None:
        return "sin datos"
    return f"{valor.day} de {MESES[valor.month - 1]} de {valor.year}, {valor:%H:%M} h"


def fecha_corta(valor: datetime | float | None) -> str:
    """16/04/2026 (acepta datetime o timestamp)."""
    if valor is None:
        return ""
    if not isinstance(valor, datetime):
        valor = datetime.fromtimestamp(valor)
    return f"{valor:%d/%m/%Y}"


def tamano(bytes_: int) -> str:
    """47,5 MB"""
    valor = float(bytes_)
    for unidad in ("bytes", "KB", "MB", "GB"):
        if valor < 1024 or unidad == "GB":
            break
        valor /= 1024
    texto = f"{valor:.0f}" if unidad in ("bytes", "KB") or valor >= 100 else f"{valor:.1f}"
    return f"{texto.replace('.', ',')} {unidad}"


def formato(ext: str) -> str:
    """Nombre amable de un formato de archivo: pdf → PDF, xlsx → Excel."""
    return FORMATOS.get(ext.lower(), ext.upper() or "Archivo")


def register(app: Flask) -> None:
    for f in (fecha_larga, fecha_corta, tamano, formato):
        app.add_template_filter(f)
