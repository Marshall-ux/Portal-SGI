import pytest

from app.indexer import build_index
from app.search import buscar

DISCO = {
    "01. MANUALES  Y DOCUMENTACIÓN NEOSTAR": {
        "04. FORMULARIOS": {
            "01. FORMULARIOS GENERALES": {
                "F 7.2-01 - Programa anual de capacitación _Rev.04.xlsx": 1,
                "F 7.2-09 - Evaluación de desempeño _ Nuevos Colaboradores_Rev.02.pdf": 1,
                "F 10.3-04 - Buzón de Sugerencias_Rev.00.xls": 1,
                "F 2.7-01 - Otro formulario.pdf": 1,
            },
        },
        "02. MANUAL DE PROCEDIMIENTOS": {
            "7.2-04  Evaluación de Desempeño_Rev.00.pdf": 1,
        },
    },
    "03. CAPACITACIONES NEOSTAR": {
        "03. SEGURIDAD Y SALUD EN EL TRABAJO": {
            "EXTINTORES Y TIPOS DE FUEGO.mp4": 1,
            "Uso de matafuegos.pdf": 1,
        },
    },
    "05. CRONOGRAMAS": {
        "F 7.2-01 - Programa Anual de Capacitación _Rev.04 - 2026.pdf": 1,
    },
}


@pytest.fixture
def index(make_tree):
    return build_index(make_tree(DISCO))


def nombres(resultados):
    return [d.info.label for d in resultados.documentos]


def test_sin_acentos_ni_mayusculas(index):
    r = buscar(index, "EVALUACION desempeno")
    assert sorted(nombres(r)) == [
        "7.2-04 - Evaluación de Desempeño",
        "F 7.2-09 - Evaluación de desempeño Nuevos Colaboradores",
    ]


def test_por_codigo_primero_la_coincidencia_exacta(index):
    r = buscar(index, "F 7.2-01")
    assert nombres(r)[:2] == ["F 7.2-01 - Programa anual de capacitación", "F 7.2-01 - Programa Anual de Capacitación"]
    # "F 2.7-01" tiene los mismos números en otro orden: no aparece primero
    assert "F 2.7-01 - Otro formulario" not in nombres(r)[:2]


def test_comienzo_de_palabra(index):
    assert nombres(buscar(index, "capacit")) == [
        "F 7.2-01 - Programa anual de capacitación",
        "F 7.2-01 - Programa Anual de Capacitación",
        "EXTINTORES Y TIPOS DE FUEGO",  # por estar en la carpeta Capacitaciones
        "Uso de matafuegos",
    ]
    assert buscar(index, "acitacion").documentos == []  # no busca en el medio de las palabras


def test_por_carpeta(index):
    r = buscar(index, "seguridad matafuegos")
    assert nombres(r) == ["Uso de matafuegos"]
    assert [s.title for s in buscar(index, "formularios").secciones] == ["FORMULARIOS", "FORMULARIOS GENERALES"]


def test_dentro_de_una_seccion(index):
    cronogramas = index.section("cronogramas")
    r = buscar(index, "programa", dentro=cronogramas)
    assert nombres(r) == ["F 7.2-01 - Programa Anual de Capacitación"]


def test_consulta_vacia_o_sin_resultados(index):
    assert buscar(index, "   ").documentos == [] and buscar(index, "   ").total_documentos == 0
    assert buscar(index, "inexistente").documentos == []


def test_limite(index):
    r = buscar(index, "f", limite=2)
    assert len(r.documentos) == 2 and r.total_documentos > 2
