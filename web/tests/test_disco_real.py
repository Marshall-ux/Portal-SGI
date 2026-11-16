"""Test contra una copia real del disco SGI, si está disponible.

Ruta: variable SGI_DISCO_PRUEBA o, por defecto, C:\\Temp\\DocumentacionISO.
Comprueba invariantes, no cantidades exactas, porque el disco cambia.
"""
import os
import tomllib

import pytest

from app.indexer import DEFAULT_EXCLUDES, Exclusions, build_index
from app.vistas import accesos_rapidos

RUTA = os.environ.get("SGI_DISCO_PRUEBA", r"C:\Temp\DocumentacionISO")
CONFIG = os.path.join(os.path.dirname(__file__), os.pardir, "config", "portal.toml")
with open(CONFIG, "rb") as f:
    PORTAL = tomllib.load(f)

pytestmark = pytest.mark.skipif(not os.path.isdir(RUTA), reason=f"No hay copia del disco en {RUTA}")


@pytest.fixture(scope="module")
def index():
    return build_index(RUTA)


@pytest.fixture(scope="module")
def index_portal():
    """El índice como lo arma el portal: con las exclusiones técnicas y las de portal.toml."""
    return build_index(RUTA, Exclusions(Exclusions.parse(DEFAULT_EXCLUDES).patterns + PORTAL.get("no_publicar", [])))


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


def test_accesos_rapidos_configurados_existen(index_portal):
    """Cada acceso de portal.toml encuentra su documento en el disco real."""
    accesos = accesos_rapidos(index_portal, PORTAL)
    assert accesos, "portal.toml no tiene accesos rápidos"
    assert [a.ruta for a in accesos if a.documento is None] == []


def test_guia_de_acceso_no_se_publica(index_portal):
    assert not any("guia de acceso" in d.key for d in index_portal.documents)
    assert any(r.startswith("00. Guia de Acceso") for r in index_portal.excluded)


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
