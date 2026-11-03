"""Portal SGI: aplicación web que publica la información documentada del disco SGI."""
from __future__ import annotations

import os
import tomllib

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .indexer import DEFAULT_EXCLUDES, Exclusions
from .store import IndexStore

AVISO_POR_DEFECTO = (
    "Información documentada del Sistema de Gestión Integrado. La versión vigente es la publicada "
    "en este portal; toda copia impresa o descargada se considera no controlada."
)


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        DATA_DIR=os.environ.get("PORTAL_DATOS", "/data"),
        EXCLUSIONES=os.environ.get("PORTAL_EXCLUSIONES", DEFAULT_EXCLUDES),
        AVISO=os.environ.get("PORTAL_AVISO") or AVISO_POR_DEFECTO,
        CONFIG_FILE=os.environ.get(
            "PORTAL_CONFIG", os.path.join(os.path.dirname(app.root_path), "config", "portal.toml")
        ),
    )
    if config:
        app.config.update(config)

    with open(app.config["CONFIG_FILE"], "rb") as f:
        app.config["PORTAL"] = tomllib.load(f)
    app.extensions["store"] = IndexStore(app.config["DATA_DIR"], Exclusions.parse(app.config["EXCLUSIONES"]))

    # Detrás del nginx de portal-interno, en /sgi/: X-Forwarded-Prefix hace que
    # url_for arme las rutas con el prefijo.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    from . import filters, routes

    filters.register(app)
    app.register_blueprint(routes.bp)
    return app
