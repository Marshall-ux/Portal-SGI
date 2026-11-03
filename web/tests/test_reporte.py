import csv
import io

import pytest

from app.indexer import build_index
from app.reporte import a_corregir, a_csv, agrupar, ruta_disco

DISCO = {
    "Thumbs.db": 1,
    "01. MANUALES  Y DOCUMENTACIÓN NEOSTAR": {
        "F 7.2-15 Acta de Dirección.xlsx": 1,                      # sin revisión
        "F 8.2-01 - Proceso_Rev.03.pdf": 10,                       # conflicto: la Rev.03 es más nueva
        "F 8.2-01 - Proceso_Rev.05.pdf": 5,
        "8.2.1K Proceso KIA_ Rev.07.pdf": 1,                       # revisión no estándar
        "VACÍA": {},
    },
    "02. PUESTOS": {
        "_F 7.2-05 -V1 - RECEPCIONISTA_Rev.04.pdf": 1,             # guion bajo inicial
        "F 7.2-05 -PV.9 - JEFE DE SERVICIOS_Rev.04.pdf.pdf": 1,    # doble extensión
    },
}


@pytest.fixture
def index(make_tree):
    return build_index(make_tree(DISCO))


def test_grupos_en_orden_de_prioridad(index):
    grupos = agrupar(index)
    assert [(g.tipo.clave, len(g.avisos)) for g in grupos] == [
        ("conflicto_revision", 1),
        ("versiones_anteriores", 1),
        ("sin_revision", 1),
        ("doble_extension", 1),
        ("guion_bajo_inicial", 1),
        ("carpeta_vacia", 1),
        ("revision_no_estandar", 1),
        ("excluido", 1),
    ]
    # Los de prioridad baja van plegados
    assert [g.tipo.clave for g in grupos if not g.tipo.abierto] == ["revision_no_estandar", "excluido"]
    # Los archivos no publicados son informativos: no cuentan como avisos para corregir
    assert a_corregir(grupos) == 7


def test_ruta_como_la_ve_sgi_en_windows():
    assert ruta_disco("01. MANUALES  Y DOCUMENTACIÓN NEOSTAR/F 7.2-15.xlsx", "I:\\") == \
        "I:\\01. MANUALES  Y DOCUMENTACIÓN NEOSTAR\\F 7.2-15.xlsx"
    assert ruta_disco("aspnet_client/", "I:\\") == "I:\\aspnet_client"


def test_csv_para_excel(index):
    filas = list(csv.reader(io.StringIO(a_csv(agrupar(index), "I:\\")), delimiter=";"))
    assert filas[0] == ["Tipo", "Qué hacer", "Ruta en el disco", "Detalle"]
    assert len(filas) == 1 + 8
    conflicto = filas[1]
    assert conflicto[0] == "La versión más nueva no es la de mayor revisión"
    assert conflicto[2] == "I:\\01. MANUALES  Y DOCUMENTACIÓN NEOSTAR\\F 8.2-01 - Proceso_Rev.03.pdf"
    assert conflicto[3] == "Revisión mayor: F 8.2-01 - Proceso_Rev.05.pdf"


def test_seccion_de_cada_aviso(index):
    manuales = index.section("manuales-y-documentacion-neostar")
    assert index.section_of("01. MANUALES  Y DOCUMENTACIÓN NEOSTAR/F 7.2-15 Acta de Dirección.xlsx") is manuales
    # La carpeta vacía no se publica: lleva a la carpeta que la contiene
    assert index.section_of("01. MANUALES  Y DOCUMENTACIÓN NEOSTAR/VACÍA") is manuales
    assert index.section_of("Thumbs.db") is index.root
