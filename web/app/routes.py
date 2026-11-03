"""Rutas del portal: home, documentos y estado."""
from __future__ import annotations

from dataclasses import dataclass

from flask import Blueprint, abort, current_app, jsonify, render_template, request, send_file

from .indexer import Document, Section
from .store import IndexStore

bp = Blueprint("portal", __name__)

# Formatos que el navegador muestra en una pestaña; el resto se descarga.
FORMATOS_EN_LINEA = {"pdf", "mp4", "png", "jpg", "jpeg"}


@dataclass(frozen=True)
class SeccionVista:
    """Datos de una sección listos para su tarjeta."""

    seccion: Section
    titulo: str
    descripcion: str
    icono: str


def _store() -> IndexStore:
    return current_app.extensions["store"]


def vista_seccion(section: Section) -> SeccionVista:
    """Título, descripción e ícono desde config/portal.toml; si no figura, lo que dice el disco."""
    cfg = current_app.config["PORTAL"].get("secciones", {}).get(section.slug, {})
    return SeccionVista(
        seccion=section,
        titulo=cfg.get("titulo", section.title),
        descripcion=cfg.get("descripcion", ""),
        icono=cfg.get("icono", "carpeta"),
    )


@bp.get("/")
def home():
    index = _store().get()
    estado = _store().status()
    if index is None:
        return render_template("preparando.html", estado=estado), 503

    raiz = index.root.documents
    return render_template(
        "home.html",
        estado=estado,
        # Los documentos "00." de la raíz son los accesos rápidos (Guía de Acceso, Mapa de Proceso)
        accesos=[d for d in raiz if d.info.order == 0],
        otros=[d for d in raiz if d.info.order != 0],
        secciones=[vista_seccion(s) for s in index.root.sections],
        cert=current_app.config["PORTAL"].get("certificacion"),
    )


@bp.get("/s/<path:ruta>")
def seccion(ruta: str):
    # La navegación por secciones llega en la próxima etapa.
    index = _store().get()
    if index is None or index.section(ruta) is None:
        abort(404)
    return render_template("en_construccion.html", seccion=vista_seccion(index.section(ruta))), 501


@bp.get("/d/<path:ruta>")
def documento(ruta: str):
    """Abre la versión vigente del documento. ?formato=xls elige otro formato."""
    index = _store().get()
    doc: Document | None = index.document(ruta) if index else None
    if doc is None:
        abort(404)
    formato = request.args.get("formato")
    version = doc.formats.get(formato.lower()) if formato else doc.primary
    if version is None:
        abort(404)
    return send_file(
        index.abspath(version),
        download_name=version.name,
        as_attachment=version.ext not in FORMATOS_EN_LINEA,
        conditional=True,
        max_age=0,  # siempre se revalida: después de una sincronización llega la versión nueva
    )


@bp.get("/salud")
def salud():
    """Estado para monitoreo: si hay índice, cuántos documentos y la última sincronización."""
    index = _store().get()
    estado = _store().status()
    return jsonify(
        estado="ok" if index else "sin_datos",
        documentos=len(index.documents) if index else 0,
        ultima_sincronizacion=estado.ultima_ok.isoformat() if estado.ultima_ok else None,
        ultimo_intento_fallido=estado.fallo_el_ultimo_intento,
    ), (200 if index else 503)


@bp.app_errorhandler(404)
def no_encontrado(_error):
    return render_template("error.html", titulo="No encontramos esa página",
                           mensaje="Puede que el documento haya cambiado de lugar o de nombre."), 404
