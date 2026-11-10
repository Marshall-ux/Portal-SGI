"""Rutas del portal: home, secciones, buscador, documentos y estado."""
from __future__ import annotations

from datetime import date

from flask import (Blueprint, Response, abort, current_app, jsonify, redirect, render_template, request,
                   send_file, url_for)

from . import reporte as rep
from .indexer import Document, Index, Section
from .search import buscar as buscar_en
from .store import IndexStore
from .vistas import accesos_rapidos, icono_documento, migas, vista_seccion

bp = Blueprint("portal", __name__)

# Formatos que el navegador muestra en una pestaña; el resto se descarga.
FORMATOS_EN_LINEA = {"pdf", "mp4", "png", "jpg", "jpeg"}


def _store() -> IndexStore:
    return current_app.extensions["store"]


def _index_o_preparando() -> Index:
    index = _store().get()
    if index is None:
        abort(503)
    return index


@bp.app_context_processor
def ayudantes():
    """Funciones disponibles en todas las plantillas."""
    config = current_app.config["PORTAL"]
    return {
        "vista": lambda section: vista_seccion(section, config),
        "migas": lambda section: migas(section, config),
        "icono_documento": icono_documento,
        "q": request.args.get("q", ""),
    }


@bp.get("/")
def home():
    index = _index_o_preparando()
    accesos = [a for a in accesos_rapidos(index, current_app.config["PORTAL"]) if a.documento]
    en_accesos = {id(a.documento) for a in accesos}
    return render_template(
        "home.html",
        estado=_store().status(),
        accesos=accesos,
        # Los archivos de la raíz del disco que no son accesos rápidos
        otros=[d for d in index.root.documents if id(d) not in en_accesos],
        secciones=index.root.sections,
        cert=current_app.config["PORTAL"].get("certificacion"),
    )


@bp.get("/s/<path:ruta>")
def seccion(ruta: str):
    section = _index_o_preparando().section(ruta)
    if section is None:
        abort(404)
    return render_template("seccion.html", seccion=section)


@bp.get("/buscar")
def buscar():
    index = _index_o_preparando()
    dentro: Section | None = index.section(request.args.get("en", "")) if request.args.get("en") else None
    resultados = buscar_en(index, request.args.get("q", ""), dentro)
    return render_template("buscar.html", resultados=resultados, dentro=dentro)


@bp.get("/d/<path:ruta>")
def documento(ruta: str):
    """Abre la versión vigente del documento. ?formato=xls elige otro formato."""
    index = _index_o_preparando()
    doc: Document | None = index.document(ruta)
    if doc is None:
        # Link viejo: si el documento cambió de carpeta y su nombre es único, se redirige
        movido = index.moved_document(ruta)
        if movido is None:
            abort(404)
        return redirect(url_for("portal.documento", ruta=movido.path, **request.args))
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


@bp.get("/reporte")
def reporte():
    """Qué revisar en el disco para que el portal quede ordenado (para el equipo de SGI)."""
    index = _index_o_preparando()
    grupos = rep.agrupar(index)
    # Accesos rápidos de portal.toml cuyo documento ya no se encuentra (se renombró o se borró)
    accesos_faltantes = [a for a in accesos_rapidos(index, current_app.config["PORTAL"]) if a.documento is None]
    return render_template(
        "reporte.html",
        index=index,
        estado=_store().status(),
        grupos=grupos,
        accesos_faltantes=accesos_faltantes,
        a_corregir=rep.a_corregir(grupos) + len(accesos_faltantes),
        ruta_disco=lambda relpath: rep.ruta_disco(relpath, current_app.config["RUTA_DISCO"]),
    )


@bp.get("/reporte.csv")
def reporte_csv():
    grupos = rep.agrupar(_index_o_preparando())
    # Con BOM: Excel lo abre con los acentos bien
    contenido = "﻿" + rep.a_csv(grupos, current_app.config["RUTA_DISCO"])
    nombre = f"reporte-disco-sgi-{date.today():%Y-%m-%d}.csv"
    return Response(contenido, mimetype="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


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
                           mensaje="Puede que el documento haya cambiado de lugar o de nombre. "
                                   "Probá con el buscador."), 404


@bp.app_errorhandler(503)
def preparando(_error):
    return render_template("preparando.html", estado=_store().status()), 503
