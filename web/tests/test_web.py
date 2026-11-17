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
        "01. MANUAL INTEGRADO": {
            "2.0 Politica de Calidad Medio Ambiente, Seguridad y Salud en el Trabajo_Rev.04.pdf": 50,
            "F 1.0 01 - Organigrama_Rev.33.pdf": 60,
        },
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


POLITICA = "manuales-y-documentacion-neostar/manual-integrado/2-0-politica-de-calidad-medio-ambiente-seguridad-y-salud-en-el-trabajo"


ORGANIGRAMA = "manuales-y-documentacion-neostar/manual-integrado/f-1-0-01-organigrama"


def bloque(page, id_titulo):
    return page.split(f'id="{id_titulo}"')[1].split("</section>")[0]


def test_home_accesos_rapidos_desde_la_configuracion(client):
    accesos = bloque(html(client.get("/")), "titulo-accesos")
    # En el orden de portal.toml, con el título configurado o el nombre del archivo
    assert accesos.index('href="/d/mapa-de-proceso"') < accesos.index(f'href="/d/{POLITICA}"')
    assert "Mapa de Proceso" in accesos
    assert "Política del Sistema de Gestión Integrado" in accesos
    assert accesos.index(f'href="/d/{POLITICA}"') < accesos.index(f'href="/d/{ORGANIGRAMA}"')
    assert ">Organigrama<" in accesos
    assert "ACUERDO" not in accesos


CANALES = ["Buzón de Sugerencias", "No Conformidades", "Oportunidades de Mejora",
           "Reporte de Incidentes", "Canal de Denuncias"]


def test_home_canales_de_participacion_y_reporte(client):
    page = html(client.get("/"))
    assert "Otros documentos" not in page
    canales = bloque(page, "titulo-canales")
    assert "Canales de Participación y Reporte" in canales
    assert "Tu voz cuenta. ¡Sé parte de la mejora!" in canales
    # Una tarjeta por canal, en el orden de portal.toml: nombre, público, pregunta corta y acciones
    posiciones = [canales.index(f'-nombre">{nombre}</h3>') for nombre in CANALES]
    assert posiciones == sorted(posiciones)
    tarjetas = canales.split('<div class="canal-panel"')[0]
    assert tarjetas.count('class="canal-abrir"') == 5
    assert tarjetas.count("<span>Público interno y externo</span>") == 1
    assert tarjetas.count("<span>Uso interno</span>") == 4
    assert "¿Tenés una idea o algo para sugerirnos?" in tarjetas
    assert "Ante una emergencia, avisá de inmediato." in tarjetas
    assert 'class="qr"' not in tarjetas  # el QR está en el cuadro que se despliega
    # NC y OM comparten el formulario, pero son dos tarjetas
    assert tarjetas.count('href="https://forms.gle/wLXx5mh5tNHD6tXKA" target="_blank" rel="noopener"') == 2


def test_home_canales_cuando_usarlo_despliega_el_detalle(client):
    canales = bloque(html(client.get("/")), "titulo-canales")
    # Cada «¿Cuándo usarlo?» controla su cuadro, cerrado al entrar
    for i in range(1, 6):
        assert f'aria-expanded="false" aria-controls="canal-{i}"' in canales
        assert f'id="canal-{i}" role="region" aria-labelledby="canal-{i}-titulo" tabindex="-1" hidden' in canales
    # El cuadro tiene la pregunta completa, la explicación, el ejemplo, el QR y el botón
    paneles = canales.split('<div class="canal-panel"', 1)[1]
    assert 'id="canal-2-titulo">No Conformidades (NC)</h3>' in paneles
    assert 'id="canal-5-titulo">Canal de Denuncias – Código de Ética</h3>' in paneles
    assert "¿Tenés una idea, sugerencia, inquietud o reclamo que quieras compartir?" in paneles
    assert paneles.count("¿Cuándo usar este canal?") == 5 and paneles.count(">Por ejemplo<") == 5
    assert paneles.count('class="canal-qr"') == 5 and paneles.count('class="qr"') == 5
    assert paneles.count("Abrir formulario") == 5
    assert "<strong>Importante:</strong>" in paneles
    assert "Este buzón no reemplaza esos canales de comunicación." in paneles
    r = client.get("/static/js/canales.js")
    assert r.status_code == 200
    r.close()


def test_home_sin_canales_configurados(data_dir):
    app = create_app({"DATA_DIR": str(data_dir)})
    del app.config["PORTAL"]["canales"]
    page = html(app.test_client().get("/"))
    assert 'id="titulo-canales"' not in page and "Documentación" in page


def test_qr_de_los_canales():
    from app.filters import qr

    svg = qr("https://forms.gle/vrp97hmSJcEJTNYt6")
    assert svg.startswith('<svg viewBox="') and 'class="qr"' in svg
    assert "width=" not in svg.split(">")[0]  # sin tamaño fijo: lo da el CSS
    assert qr("https://forms.gle/16V1RJrpnqMJFW4v8") != svg


def test_documentos_de_la_raiz_siguen_en_el_buscador(client):
    """Ya no se listan en la home, pero se encuentran y se abren igual."""
    assert 'href="/d/acuerdo-con-suscriptor"' not in html(client.get("/"))
    assert 'href="/d/acuerdo-con-suscriptor"' in html(client.get("/buscar?q=acuerdo"))


def test_guia_de_acceso_no_se_publica(client):
    page = html(client.get("/"))
    assert "guia-de-acceso" not in page and "Guia de Acceso" not in page
    assert client.get("/d/guia-de-acceso-documentacion-sgi").status_code == 404
    assert "No encontramos documentos" in html(client.get("/buscar?q=guia acceso"))
    # Figura en el reporte entre los archivos que no se publican
    assert "00. Guia de Acceso Documentación SGI.pdf" in html(client.get("/reporte"))


def test_acceso_rapido_sigue_al_documento_movido(data_dir):
    manuales = data_dir / "current" / "01. MANUALES  Y DOCUMENTACIÓN NEOSTAR"
    os.rename(manuales / "01. MANUAL INTEGRADO", manuales / "01. MANUAL DEL SGI")
    accesos = bloque(html(create_app({"DATA_DIR": str(data_dir)}).test_client().get("/")), "titulo-accesos")
    assert 'href="/d/manuales-y-documentacion-neostar/manual-del-sgi/2-0-politica-de-calidad' in accesos


def test_acceso_rapido_sin_documento_se_avisa_en_el_reporte(data_dir):
    integrado = data_dir / "current" / "01. MANUALES  Y DOCUMENTACIÓN NEOSTAR" / "01. MANUAL INTEGRADO"
    os.rename(integrado / "2.0 Politica de Calidad Medio Ambiente, Seguridad y Salud en el Trabajo_Rev.04.pdf",
              integrado / "2.0 Politica del SGI_Rev.05.pdf")
    client = create_app({"DATA_DIR": str(data_dir)}).test_client()
    page = html(client.get("/"))
    assert "Política del Sistema de Gestión Integrado" not in page
    assert 'href="/d/mapa-de-proceso"' in page  # los demás accesos siguen
    reporte = html(client.get("/reporte"))
    assert "Accesos rápidos sin documento" in reporte
    assert f"/d/{POLITICA}" in reporte
    assert "Todo en orden" not in reporte


def test_home_certificacion(client):
    page = html(client.get("/"))
    assert "Certificación vigente" in page
    assert "tuv-rheinland-9000015845-1200.png" in page and "tuv-rheinland-9000015845-2400.png" in page
    for norma, nombre in [("ISO 9001:2015", "Calidad"), ("ISO 14001:2015", "Medio Ambiente"),
                          ("ISO 45001:2018", "Seguridad y Salud en el Trabajo")]:
        assert norma in page and nombre in page
    assert 'href="http://m.certipedia.com/?id=9000015845"' in page


def test_home_certificacion_descripcion_y_normas_desplegables(client):
    cert = bloque(html(client.get("/")), "titulo-certificacion")
    assert "¿Qué es nuestro Sistema de Gestión Integrado?" in cert
    assert "El SGI está presente en todas nuestras concesionarias" in cert
    # Cada norma es un botón que controla su cuadro, cerrado al entrar
    for clave, titulo in [("calidad", "ISO 9001:2015</span> – Gestión de la Calidad"),
                          ("ambiente", "ISO 14001:2015</span> – Gestión Ambiental"),
                          ("seguridad", "ISO 45001:2018</span> – Seguridad y Salud en el Trabajo")]:
        assert f'aria-expanded="false" aria-controls="norma-{clave}"' in cert
        assert f'id="norma-{clave}" role="region" aria-labelledby="norma-{clave}-titulo" hidden' in cert
        assert titulo in cert
    assert cert.count("¿Cómo la aplicamos en nuestras concesionarias?") == 3
    assert cert.count("Nuestro compromiso:") == 3
    assert "El SGI no es responsabilidad de una sola área." in cert
    assert "js/certificacion.js" in html(client.get("/"))
    r = client.get("/static/js/certificacion.js")
    assert r.status_code == 200
    r.close()


def test_home_certificacion_sin_textos_sigue_mostrando_las_normas(data_dir):
    app = create_app({"DATA_DIR": str(data_dir)})
    cert = app.config["PORTAL"]["certificacion"]
    app.config["PORTAL"]["certificacion"] = {
        **{k: v for k, v in cert.items() if k not in ("descripcion", "cierre")},
        "normas": [{k: n[k] for k in ("norma", "nombre", "icono")} for n in cert["normas"]],
    }
    page = bloque(html(app.test_client().get("/")), "titulo-certificacion")
    assert "ISO 14001:2015" in page and "Medio Ambiente" in page
    assert "<button" not in page and 'class="norma-panel' not in page and "cert-cierre" not in page


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
    # Carpeta que no está en la configuración: aparece igual, con su nombre del disco legible
    assert "Carpeta Nueva de SGI" in page
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


def test_seccion_con_enlace_abre_otro_sitio(data_dir):
    """Capacitaciones lleva al espacio de RRHH: no se muestra lo que quede en su carpeta."""
    carpeta = data_dir / "current" / "03. CAPACITACIONES NEOSTAR" / "01. CALIDAD"
    carpeta.mkdir(parents=True)
    (carpeta / "Capacitacion vieja de calidad.pdf").write_bytes(b"x")
    client = create_app({"DATA_DIR": str(data_dir)}).test_client()

    page = html(client.get("/"))
    assert 'href="https://multiversorrhh.com/mi-neoschool" target="_blank" rel="noopener"' in page
    assert 'href="/s/capacitaciones-neostar"' not in page
    assert "Sección 03" in page and "Capacitaciones de RRHH" in page
    # La sección y sus subcarpetas redirigen (enlaces guardados)
    for ruta in ("/s/capacitaciones-neostar", "/s/capacitaciones-neostar/calidad"):
        r = client.get(ruta)
        assert r.status_code == 302 and r.headers["Location"] == "https://multiversorrhh.com/mi-neoschool"
    # El material que quede en la carpeta no aparece en el buscador
    page = html(client.get("/buscar?q=calidad"))
    assert "Capacitacion vieja" not in page and 'href="/s/capacitaciones-neostar/calidad"' not in page


def test_seccion_con_enlace_sigue_en_la_home_sin_carpeta_en_el_disco(client):
    """Al retirar el material la carpeta queda vacía o se borra: la tarjeta sigue, en su lugar."""
    page = html(client.get("/"))
    assert 'href="https://multiversorrhh.com/mi-neoschool"' in page
    assert page.index("Sección 01") < page.index("Sección 03") < page.index("Sección 08")
    assert client.get("/s/capacitaciones-neostar").status_code == 302


# ── Secciones y buscador ────────────────────────────────────────────────────


def test_pagina_de_seccion(client):
    r = client.get("/s/manuales-y-documentacion-neostar")
    page = html(r)
    assert r.status_code == 200
    # Breadcrumb y título desde config/portal.toml
    assert 'aria-label="Ruta de navegación"' in page and 'href="/"' in page
    assert '<h1 class="titulo-seccion">Manuales y Documentación</h1>' in page
    # Tarjeta de documento: enlace a la vigente, código, revisión y botón del otro formato
    assert 'href="/d/manuales-y-documentacion-neostar/f-8-4-01-autorizacion-generica"' in page
    assert "F 8.4-01" in page and "Rev. 07" in page
    assert 'href="/d/manuales-y-documentacion-neostar/f-8-4-01-autorizacion-generica?formato=xls"' in page
    # Buscador acotado a la sección
    assert 'name="en" value="manuales-y-documentacion-neostar"' in page


def test_seccion_inexistente(client):
    assert client.get("/s/no-existe").status_code == 404


def test_buscador(client):
    page = html(client.get("/buscar?q=autorizacion"))
    assert "Resultados para «autorizacion»" in page
    assert "1 documento" in page
    assert 'href="/d/manuales-y-documentacion-neostar/f-8-4-01-autorizacion-generica"' in page
    assert "Manuales y Documentación" in page  # muestra dónde está el documento


def test_buscador_dentro_de_una_seccion(client):
    page = html(client.get("/buscar?q=informe&en=carpeta-nueva-de-sgi"))
    assert "en <strong>Carpeta Nueva de SGI</strong>" in page
    assert 'href="/d/carpeta-nueva-de-sgi/informe"' in page
    assert "buscar en todo el portal" in page


def test_buscador_vacio_y_sin_resultados(client):
    assert "Buscar documentos" in html(client.get("/buscar?q="))
    assert "No encontramos documentos" in html(client.get("/buscar?q=zzzz"))


def test_busqueda_en_el_header_de_todas_las_paginas(client):
    for ruta in ("/", "/s/manuales-y-documentacion-neostar", "/buscar?q=x"):
        assert 'id="buscar-portal"' in html(client.get(ruta))


# ── Reporte del disco ───────────────────────────────────────────────────────


def test_reporte(client):
    r = client.get("/reporte")
    page = html(r)
    assert r.status_code == 200
    assert "Reporte del disco SGI" in page
    assert "Al día" in page  # sync.json sin error
    # "F 8.4-01 - Autorización Generica_Rev.07" está en PDF y XLS: no hay avisos de nombre
    assert "Todo en orden" in page
    assert 'href="/reporte"' in html(client.get("/"))  # enlace en el pie


def test_reporte_muestra_avisos_y_falla_de_sincronizacion(data_dir, make_tree):
    (data_dir / "current" / "F 7.2-15 Acta de Dirección.xlsx").write_bytes(b"x")
    (data_dir / "sync.json").write_text(json.dumps({**SYNC, "ultimo_estado": "error",
                                                    "ultimo_error": "El origen /mnt/disco está vacío."}), encoding="utf-8")
    page = html(create_app({"DATA_DIR": str(data_dir), "RUTA_DISCO": "I:\\"}).test_client().get("/reporte"))
    assert "Documentos con código y sin revisión" in page
    assert "I:\\F 7.2-15 Acta de Dirección.xlsx" in page
    assert "Falló el último intento" in page and "El origen /mnt/disco está vacío." in page


def test_reporte_csv(client):
    r = client.get("/reporte.csv")
    assert r.status_code == 200
    assert r.mimetype == "text/csv"
    assert r.headers["Content-Disposition"].startswith('attachment; filename="reporte-disco-sgi-')
    texto = r.get_data(as_text=True)
    assert texto.startswith("\ufeffTipo;Qué hacer;Ruta en el disco;Detalle")


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


def test_link_viejo_redirige_si_el_documento_cambio_de_carpeta(client):
    r = client.get("/d/carpeta-vieja/f-8-4-01-autorizacion-generica?formato=xls")
    assert r.status_code == 302
    assert r.headers["Location"] == "/d/manuales-y-documentacion-neostar/f-8-4-01-autorizacion-generica?formato=xls"


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
    # 7 archivos, 6 documentos: el PDF y el XLS de la Autorización son una sola ficha
    assert datos["estado"] == "ok" and datos["documentos"] == 6
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
