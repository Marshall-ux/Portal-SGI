"""Test contra una copia real del disco SGI, si está disponible.

Ruta: variable SGI_DISCO_PRUEBA o, por defecto, C:\\Temp\\DocumentacionISO.
Comprueba invariantes, no cantidades exactas, porque el disco cambia.
"""
import os

import pytest

from app.indexer import build_index

RUTA = os.environ.get("SGI_DISCO_PRUEBA", r"C:\Temp\DocumentacionISO")

pytestmark = pytest.mark.skipif(not os.path.isdir(RUTA), reason=f"No hay copia del disco en {RUTA}")


@pytest.fixture(scope="module")
def index():
    return build_index(RUTA)


def test_secciones_principales(index):
    titulos = [s.title for s in index.root.sections]
    assert titulos[:7] == [
        "MANUALES Y DOCUMENTACIÓN NEOSTAR",
        "PUESTOS DE TRABAJO Y DOCUMENTACIÓN ASOCIADA",
        "CAPACITACIONES NEOSTAR",
        "CONTROLES OPERATIVOS NEOSTAR",
        "CRONOGRAMAS",
        "BUZONES DE PARTICIPACIÓN Y CONSULTA",
        "ENCUESTAS",
    ]
    assert not any("aspnet" in t.lower() for t in titulos)


def test_accesos_rapidos_en_la_raiz(index):
    raiz = [d.info.title for d in index.root.documents]
    assert raiz[:2] == ["Guia de Acceso Documentación SGI", "Mapa de Proceso"]


def test_nada_tecnico_publicado(index):
    nombres = [v.name.lower() for d in index.documents for vs in d.versions.values() for v in vs]
    assert "web.config" not in nombres
    assert not any(n == "thumbs.db" or n.startswith(("~$", ".~lock")) for n in nombres)


def test_todas_las_versiones_vigentes_se_pueden_abrir(index):
    for doc in index.documents:
        for version in doc.formats.values():
            assert os.path.isfile(index.abspath(version)), version.relpath


def test_rutas_unicas_y_navegables(index):
    for doc in index.documents:
        assert index.document(doc.path) is doc
    for section in index.root.walk():
        assert index.section(section.path) is section
