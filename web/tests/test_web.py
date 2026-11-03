import json
import os

import pytest

from app import AVISO_POR_DEFECTO, create_app
from app.filters import fecha_corta, fecha_larga, formato, tamano
from app.store import SyncStatus

DISCO = {
    "00. Guia de Acceso Documentación SGI.pdf": 10,
    "00. Mapa de Proceso.pdf": 11,
    "4. ACUERDO CON SUSCRIPTOR.pdf": 12,
    "01. MANUALES  Y DOCUMENTACIÓN NEOSTAR": {
        "F 8.4-01 - Autorización Generica_Rev.07.pdf": 100,
        "F 8.4-01 - Autorización Generica_Rev.07.xls": 300,
    },
    "08. CARPETA NUEVA DE SGI": {"informe.pdf": 1},
}

SYNC = {"ultima_ok": "2026-11-03T09:00:04Z", "snapshot": "2026-11-03_060000.000", "archivos": 6,
        "ultimo_intento": "2026-11-03T09:00:04Z", "ultimo_estado": "ok", "ultimo_error": None}


@pytest.fixture
def data_dir(tmp_path, make_tree):
    """Carpeta de datos como la deja sync; current es una carpeta común (sirve igual)."""
    disco = make_tree(DISCO)
    os.rename(disco, tmp_path / "current")
    (tmp_path / "sync.json").write_text(json.dumps(SYNC), encoding="utf-8")
    return tmp_path


@pytest.fixture
def client(data_dir):
    return create_app({"DATA_DIR": str(data_dir)}).test_client()


def html(response):
    return response.get_data(as_text=True)


# ── Home ────────────────────────────────────────────────────────────────────


def test_home_aclaracion_y_ultima_actualizacion(client, data_dir):
    r = client.get("/")
    assert r.status_code == 200
    assert AVISO_POR_DEFECTO in html(r)
    esperado = fecha_larga(SyncStatus.read(str(data_dir / "sync.json")).ultima_ok)
    assert f"Última actualización: {esperado}" in html(r)


def test_aclaracion_configurable(data_dir):
    app = create_app({"DATA_DIR": str(data_dir), "AVISO": "Texto de prueba de SGI."})
    assert "Texto de prueba de SGI." in html(app.test_client().get("/"))


def test_home_accesos_rapidos_son_los_documentos_00(client):
    page = html(client.get("/"))
    accesos = page.split('id="titulo-accesos"')[1].split("</section>")[0]
    assert 'href="/d/guia-de-acceso-documentacion-sgi"' in accesos
    assert 'href="/d/mapa-de-proceso"' in accesos
    assert "ACUERDO" not in accesos
    otros = page.split('id="titulo-otros"')[1]
    assert 'href="/d/acuerdo-con-suscriptor"' in otros


def test_home_certificacion(client):
    page = html(client.get("/"))
    assert "Certificación vigente" in page
    assert "tuv-rheinland-9000015845-1200.png" in page and "tuv-rheinland-9000015845-2400.png" in page
    for norma, nombre in [("ISO 9001:2015", "Calidad"), ("ISO 14001:2015", "Medio Ambiente"),
                          ("ISO 45001:2018", "Seguridad y Salud en el Trabajo")]:
        assert norma in page and nombre in page
    assert 'href="http://m.certipedia.com/?id=9000015845"' in page


def test_imagenes_del_sello_existen(client):
    for ancho in (1200, 2400):
        r = client.get(f"/static/img/certificacion/tuv-rheinland-9000015845-{ancho}.png")
        assert r.status_code == 200 and r.mimetype == "image/png"
        r.close()


def test_home_tarjetas_de_secciones(client):
    page = html(client.get("/"))
    # Título y descripción desde config/portal.toml
    assert "Manuales y Documentación" in page
    assert "Manual Integrado, procedimientos, instructivos y formularios." in page
    assert 'href="/s/manuales-y-documentacion-neostar"' in page
    # Carpeta que no está en la configuración: aparece igual, con su nombre del disco
    assert "CARPETA NUEVA DE SGI" in page
    assert 'href="/s/carpeta-nueva-de-sgi"' in page
    assert "Sección 08" in page


def test_rutas_con_prefijo_detras_de_nginx(client):
    page = html(client.get("/", headers={"X-Forwarded-Prefix": "/sgi"}))
    assert 'href="/sgi/d/mapa-de-proceso"' in page
    assert 'href="/sgi/static/css/portal.css"' in page


def test_sin_copia_publicada_muestra_preparando(tmp_path):
    client = create_app({"DATA_DIR": str(tmp_path)}).test_client()
    r = client.get("/")
    assert r.status_code == 503
    assert "Estamos preparando el portal" in html(r)


# ── Documentos ──────────────────────────────────────────────────────────────


def test_documento_pdf_se_abre_en_el_navegador(client):
    r = client.get("/d/manuales-y-documentacion-neostar/f-8-4-01-autorizacion-generica")
    assert r.status_code == 200
    assert r.mimetype == "application/pdf"
    assert r.headers["Content-Disposition"].startswith("inline")
    assert "Rev.07.pdf" in r.headers["Content-Disposition"]
    assert "max-age=0" in r.headers["Cache-Control"]
    r.close()


def test_documento_en_otro_formato_se_descarga(client):
    r = client.get("/d/manuales-y-documentacion-neostar/f-8-4-01-autorizacion-generica?formato=xls")
    assert r.status_code == 200
    assert r.headers["Content-Disposition"].startswith("attachment")
    assert "Rev.07.xls" in r.headers["Content-Disposition"]
    r.close()


@pytest.mark.parametrize("ruta", [
    "/d/no/existe",
    "/d/manuales-y-documentacion-neostar/f-8-4-01-autorizacion-generica?formato=docx",
    "/d/../../etc/passwd",
])
def test_documento_inexistente(client, ruta):
    r = client.get(ruta)
    assert r.status_code == 404
    assert "No encontramos esa página" in html(r)


def test_salud(client, tmp_path):
    datos = client.get("/salud").get_json()
    # 6 archivos, 5 documentos: el PDF y el XLS de la Autorización son una sola ficha
    assert datos["estado"] == "ok" and datos["documentos"] == 5
    assert datos["ultima_sincronizacion"] is not None
    vacio = create_app({"DATA_DIR": str(tmp_path / "vacio")}).test_client().get("/salud")
    assert vacio.status_code == 503 and vacio.get_json()["estado"] == "sin_datos"


# ── Filtros ─────────────────────────────────────────────────────────────────


def test_filtros():
    from datetime import datetime

    assert fecha_larga(datetime(2026, 11, 3, 6, 0)) == "3 de noviembre de 2026, 06:00 h"
    assert fecha_larga(None) == "sin datos"
    assert fecha_corta(datetime(2026, 4, 16, 15, 45)) == "16/04/2026"
    assert tamano(49_765_182) == "47,5 MB"
    assert tamano(2_093_820) == "2,0 MB"
    assert tamano(303_611) == "296 KB"
    assert tamano(512) == "512 bytes"
    assert (formato("pdf"), formato("XLSX"), formato("mp4"), formato("dwg")) == ("PDF", "Excel", "Video", "DWG")
