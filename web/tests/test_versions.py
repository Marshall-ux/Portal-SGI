"""Tests del módulo de versiones. Los nombres son reales, tomados del disco I."""
import pytest

from app.versions import (
    FileVersion,
    convention_issues,
    group_documents,
    has_rev_conflict,
    identity_key,
    natural_key,
    normalize,
    parse_name,
    pick_current,
    slugify,
    sort_versions,
)

# ── Revisión ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "name, rev",
    [
        ("F 8.4-01 - Autorización Generica de compra o contratación_Rev.07.pdf", 7),
        ("8.2.1K Proceso Venta de Unidades 0km KIA_ Rev.07.pdf", 7),
        ("F 7.2-05 -A25 - ANALISTA CONTABLE__Rev.00 (Act. 24052026).pdf", 0),
        ("F 7.2-01 - Programa anual de capacitación _Rev.04.xlsx", 4),
        ("8.2 Procesos relacionados con el cliente_Rev 14.pdf", 14),
        ("Autorización uso de imagen_ Rev01.pdf", 1),
        ("IN - SERV 01 CARGA DE ORDENES DE REPARACION_Rev0.pdf", 0),
        ("I-8.2-08 Entrega de unidades 0 km Honda_Rev02.pdf", 2),
        ("F 7.2-03 - Ficha Evaluación.Rev.01.doc", 1),
        ("F 7.2-04 - Matriz de Polivalencia del Personal. Rev.01.xls", 1),
        ("7.2-03 - Géstión e Investigación de Accidentes Laborales e In Itineres Rev.02.pdf", 2),
        ("F 6.1.2-03 - Control Operativo y Mantenimiento del Sistema de Tratamiento de Efluentes - Rev.02.pdf", 2),
        ("F 7.2-05 -C3 - REFERENTE DEL SISTEMA DE GESTIÓN INTEGRADO TRINORMA (SANTA FE) rev.04 act(24052026).pdf", 4),
        ("F.7.2 04 Matriz de Polivalencia de Personal _Rev.21.pdf", 21),
        ("I-8.4-01 Compra y pago de unidades 0km a la terminal KIA- Daseos S.A_Rev.00..pdf", 0),
    ],
)
def test_detecta_revision(name, rev):
    assert parse_name(name).rev == rev


@pytest.mark.parametrize(
    "name",
    [
        "F 7.2-15 Acta de Dirección.xlsx",
        "Encuestas Internas 2025.xlsx",
        "Control Operativo CALIDAD VTAS - 07102026.pdf",
        "Prevención 2023.pdf",  # "rev" pegado a una letra
        "Revisión de Proveedores 2024.pdf",  # "Revisión" sin número a continuación
        "PV & TALLER - 2018 - TABLERO INDICADOR  Y SEGUIMIENTO DE OBSERVACIONES.ods",
    ],
)
def test_sin_revision(name):
    assert parse_name(name).rev is None


@pytest.mark.parametrize(
    "name, title",
    [
        # Datos de la versión después de la revisión: se quitan
        ("F 7.2-05 -A11 - JEFE DE CONTADURIA E IMPUESTOS_ Rev.04 (Act. 24052026).pdf", "JEFE DE CONTADURIA E IMPUESTOS"),
        ("F 7.2-05 - E1 - AUDITOR INTERNO TRINORMA_ Rev.03 ( Act. 19092022).pdf", "AUDITOR INTERNO TRINORMA"),
        ("F 7.2-05 - E2 - ASESOR EXTERNO DE HIGIENE Y SEGURIDAD EN EL TRABAJO_Rev.03 (Act.. 19092022).pdf",
         "ASESOR EXTERNO DE HIGIENE Y SEGURIDAD EN EL TRABAJO"),
        ("F 7.2-05 -A22-ANALISTA FINANCIERO_ Rev.01 (Ult.Act. 24052026).pdf", "ANALISTA FINANCIERO"),
        ("F-4.0-01 Analisis de Contexto _Rev.07 - 2026.pdf", "Analisis de Contexto"),
        ("F 7.2-05 -A12 - RESPONSABLE ADMINISTRACION F_Rev.04 (Act. 24052026)..pdf", "RESPONSABLE ADMINISTRACION F"),
        # Texto después de la revisión que identifica a otro documento: se conserva
        ("F 7.1.3-01A - Análisis de Riesgo de Trabajo_Rev.03 (ADMINISTRATIVOS).pdf",
         "Análisis de Riesgo de Trabajo (ADMINISTRATIVOS)"),
        ("F 8.1-01 - Check List Control Operativo - Administración _Rev.04 - GUIA PARA AUDITORES.pdf",
         "Check List Control Operativo - Administración - GUIA PARA AUDITORES"),
        ("F 8.2-24 - Informe de Simulacro_Rev.01 KIA ROS 2025 (Mendoza 4631).pdf",
         "Informe de Simulacro KIA ROS 2025 (Mendoza 4631)"),
        ("PE - NISSAN_Rev.06 (Catamarca 2440).pdf", "PE - NISSAN (Catamarca 2440)"),
    ],
)
def test_titulo_sin_revision_ni_datos_de_version(name, title):
    assert parse_name(name).title == title


# ── Código, orden y limpieza ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "name, code, title",
    [
        ("F 7.2-01 - Programa anual de capacitación _Rev.04.xlsx", "F 7.2-01", "Programa anual de capacitación"),
        ("F.7.2 04 Matriz de Polivalencia de Personal _Rev.21.pdf", "F.7.2 04", "Matriz de Polivalencia de Personal"),
        ("F-4.0-01 Analisis de Contexto _Rev.07 - 2026.pdf", "F-4.0-01", "Analisis de Contexto"),
        ("F 1.0 01 - Organigrama_ Rev.33.pdf", "F 1.0 01", "Organigrama"),
        ("F 00-02 Matríz de riesgos y oportunidades_Rev 03.xlsx", "F 00-02", "Matríz de riesgos y oportunidades"),
        ("F 5.4-01- Integrantes del Comité Trinorma Vigente_ Rev.01.pdf", "F 5.4-01", "Integrantes del Comité Trinorma Vigente"),
        ("F 8.2-02.A2e - Declaración Jurada Sobre la titularidad de capital social (actualizado)_ Rev.08.pdf",
         "F 8.2-02.A2e", "Declaración Jurada Sobre la titularidad de capital social (actualizado)"),
        ("F 7.1.3-01A - Análisis de Riesgo de Trabajo_Rev.03 (MECÁNICO).pdf", "F 7.1.3-01A", "Análisis de Riesgo de Trabajo (MECÁNICO)"),
        ("F 7.2-05 -PV.10 - COORDINADOR OPERATIVO POST VENTA_ Rev.04 (Act. 24052026).pdf",
         "F 7.2-05 -PV.10", "COORDINADOR OPERATIVO POST VENTA"),
        ("F 7.2-05-PV.12 - GARANTISTA_Rev.04 (Act. 24052026).pdf", "F 7.2-05-PV.12", "GARANTISTA"),
        ("F 7.2-05 -C12- ANALISTA STOCK__Rev.00 (Act. 07072026).pdf", "F 7.2-05 -C12", "ANALISTA STOCK"),
        ("I-8.2-01 ANEXO 1 - Información adicional_ Rev.19.pdf", "I-8.2-01", "ANEXO 1 - Información adicional"),
        ("IN - SERV 01 CARGA DE ORDENES DE REPARACION_Rev0.pdf", "IN - SERV 01", "CARGA DE ORDENES DE REPARACION"),
        ("IN- ADM NEO 02 - Transatlantica - Cauciones Neostar S.A.pdf", "IN- ADM NEO 02", "Transatlantica - Cauciones Neostar S.A"),
        ("8.2.1BYD Proceso Venta de Unidades 0km BYD_ Rev.01.pdf", "8.2.1BYD", "Proceso Venta de Unidades 0km BYD"),
        ("8.4.5A. - Proceso Compras Librería Rosario_ Rev.00.pdf", "8.4.5A", "Proceso Compras Librería Rosario"),
        ("8.4.5- Compras Generales y Pago a Proveedores_ Rev.05.pdf", "8.4.5", "Compras Generales y Pago a Proveedores"),
        ("3.0 Procedimiento para la Elaboración y Gestión de Procedimientos Internos_ Rev.01.pdf",
         "3.0", "Procedimiento para la Elaboración y Gestión de Procedimientos Internos"),
    ],
)
def test_separa_codigo_y_titulo(name, code, title):
    p = parse_name(name)
    assert (p.code, p.title) == (code, title)


@pytest.mark.parametrize(
    "name",
    [
        "20260507 - Informe de Simulacro Ambiental - CDG 2026 (Hipólito Yrigoyen 885).pdf",
        "KIA - 01072024.pdf",
        "HONDA - 2023.08.15.pdf",
        "CAPACITACIÓN 2023 - PREVENCION DE RIESGOS.pdf",
        "PE - FCA PV_Rev.06 (Av. Eva Perón 5380).pdf",
        "MGCMA. Manual Integrado de Calidad.pdf",
        "Rol Actualizado.pdf",
        "8 2 Procesos relacionados con el cliente.pdf",
    ],
)
def test_no_inventa_codigos(name):
    assert parse_name(name).code is None


@pytest.mark.parametrize(
    "name, is_dir, order, title",
    [
        ("01. MANUALES  Y DOCUMENTACIÓN NEOSTAR", True, 1, "MANUALES Y DOCUMENTACIÓN NEOSTAR"),
        ("10. CONTROLES DE AÑOS ANTERIORES", True, 10, "CONTROLES DE AÑOS ANTERIORES"),
        ("02. IN - ADMINISTRACIÓN - ALCO ROSARIO S.A", True, 2, "IN - ADMINISTRACIÓN - ALCO ROSARIO S.A"),
        ("2018", True, None, "2018"),
        ("00. Mapa de Proceso.pdf", False, 0, "Mapa de Proceso"),
        ("4. ACUERDO CON SUSCRIPTOR.pdf", False, 4, "ACUERDO CON SUSCRIPTOR"),
    ],
)
def test_numero_de_orden(name, is_dir, order, title):
    p = parse_name(name, is_dir=is_dir)
    assert (p.order, p.title) == (order, title)


def test_carpeta_no_separa_extension():
    p = parse_name("02. IN - ADMINISTRACIÓN - ALCO ROSARIO S.A", is_dir=True)
    assert p.ext == ""


def test_doble_extension():
    p = parse_name("F 7.2-05 -PV.9 - JEFE DE SERVICIOS_Rev.04 (Act. 24052026).pdf.pdf")
    assert (p.ext, p.title, p.rev) == ("pdf", "JEFE DE SERVICIOS", 4)
    assert "doble_extension" in p.notes


def test_guion_bajo_inicial():
    p = parse_name("_F 7.2-05 -V10 - GERENTE_DE_VENTAS_Rev.04 (Act. 24052026).pdf")
    assert (p.code, p.title) == ("F 7.2-05 -V10", "GERENTE DE VENTAS")
    assert "guion_bajo_inicial" in p.notes


# ── Identidad ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "a, b",
    [
        # Distinta revisión
        ("F 7.2-01 - Programa anual de capacitación _Rev.03.xlsx", "F 7.2-01 - Programa anual de capacitación_Rev.04.xlsx"),
        # Distinta revisión y fecha de actualización
        ("F 7.2-05 -V5 - VENDEDOR PLAN DE AHORRO_ Rev.04 (Act.24052026).pdf",
         "F 7.2-05 -V5 - VENDEDOR PLAN DE AHORRO_Rev.05 (Act. 10012027).pdf"),
        # Año de la versión
        ("F-4.0-01 Analisis de Contexto _Rev.05 - 2023.pdf", "F-4.0-01 Analisis de Contexto _Rev.07 - 2026.pdf"),
        # Acentos, mayúsculas, dobles espacios y guiones bajos
        ("I-7.2-03 Reglamento Interno  de Trabajo_Rev.01.pdf", "I-7.2-03 reglamento interno de trabajo_Rev.02.pdf"),
        ("F 7.2-05 -V10 - GERENTE_DE_VENTAS_Rev.04.pdf", "_F 7.2-05 -V10 - GERENTE DE VENTAS_Rev.05.pdf"),
        ("Matríz de riesgos_Rev 03.xlsx", "Matriz de riesgos_Rev.04.xlsx"),
        # Distinto número de orden
        ("00. Mapa de Proceso.pdf", "01. Mapa de Proceso.pdf"),
    ],
)
def test_misma_identidad(a, b):
    assert parse_name(a).key == parse_name(b).key


@pytest.mark.parametrize(
    "a, b",
    [
        ("Encuestas Internas 2024.xlsx", "Encuestas Internas 2025.xlsx"),
        ("F 8.2-24 - Informe de Simulacro_Rev.01 KIA ROS 2025 (Mendoza 4631).pdf",
         "F 8.2-24 - Informe de Simulacro_Rev.01 KIA ROS 2026 (Mendoza 4631).pdf"),
        ("F 7.1.3-01A - Análisis de Riesgo de Trabajo_Rev.03 (ADMINISTRATIVOS).pdf",
         "F 7.1.3-01B - Análisis de Riesgo de Trabajo_Rev.03 (VENDEDOR CONVENCIONAL).pdf"),
        # Mismo código, distinto puesto
        ("F 7.2-05 -A18 - ADMINISTRATIVA AUXILIAR CONTABLE _ Rev.04 (Act. 24052026).pdf",
         "F 7.2-05 -A18 - RESPONSABLE ADMINISTRATIVO DE CONCESIONARIA _ Rev.04 (Act. 24052026).pdf"),
        ("Control Operativo CALIDAD VTAS - 07102026.pdf", "Control Operativo CALIDAD VTAS - 08092025.pdf"),
    ],
)
def test_distinta_identidad(a, b):
    assert parse_name(a).key != parse_name(b).key


def test_normaliza_unicode_compuesto_y_descompuesto():
    compuesto = "DOCUMENTACIÓN"  # Ó como un solo carácter (NFC)
    descompuesto = "DOCUMENTACIÓN"  # O + tilde combinable (NFD)
    assert normalize(compuesto) == normalize(descompuesto) == "documentacion"
    assert identity_key(compuesto) == identity_key(descompuesto)


def test_slug_y_orden_natural():
    assert slugify("01. MANUALES  Y DOCUMENTACIÓN NEOSTAR") == "01-manuales-y-documentacion-neostar"
    assert slugify("???") == "sin-nombre"
    assert sorted(["10. X", "2. X", "1. X"], key=natural_key) == ["1. X", "2. X", "10. X"]


# ── Convención de nombres ───────────────────────────────────────────────────


@pytest.mark.parametrize("name, issues", [
    ("F 7.2-01 - Programa anual de capacitación_Rev.04.xlsx", []),
    ("F 7.2-01 - Programa anual de capacitación _Rev.04.xlsx", []),  # el espacio antes de "_" se tolera
    ("EXTINTORES Y TIPOS DE FUEGO.mp4", []),  # sin código: la revisión no es obligatoria
    ("F 7.2-15 Acta de Dirección.xlsx", [("sin_revision", "")]),
    ("F 8.4-02 - Listado de Proveedores Aprobados - PS_ ev.03.pdf", [("sin_revision", "")]),  # "ev" en vez de "Rev"
    ("8.2.1K Proceso Venta de Unidades 0km KIA_ Rev.07.pdf", [("revision_no_estandar", "_ Rev.07")]),
    ("F 7.2-05 -V5 - VENDEDOR PLAN DE AHORRO_ Rev.04 (Act.24052026).pdf",
     [("revision_no_estandar", "_ Rev.04 (Act.24052026)")]),
    ("Autorización uso de imagen_ Rev01.pdf", [("revision_no_estandar", "_ Rev01")]),
])
def test_convencion_de_nombres(name, issues):
    assert convention_issues(parse_name(name)) == issues


# ── Versión vigente ─────────────────────────────────────────────────────────

DIA = 86_400


def fv(name, mtime):
    return FileVersion(name=name, mtime=mtime)


def test_gana_la_fecha_mas_reciente():
    vieja = fv("Programa_Rev.04.xlsx", 1_000 * DIA)
    nueva = fv("Programa_Rev.05.xlsx", 1_010 * DIA)
    assert pick_current([vieja, nueva]) is nueva


def test_la_fecha_gana_aunque_la_revision_sea_menor():
    rev5 = fv("Programa_Rev.05.xlsx", 1_000 * DIA)
    rev3_guardada_despues = fv("Programa_Rev.03.xlsx", 1_010 * DIA)
    versiones = [rev5, rev3_guardada_despues]
    assert pick_current(versiones) is rev3_guardada_despues
    assert has_rev_conflict(versiones)


def test_empate_de_fecha_desempata_por_revision():
    rev3 = fv("Programa_Rev.03.xlsx", 1_000 * DIA)
    rev4 = fv("Programa_Rev.04.xlsx", 1_000 * DIA + 0.5)  # medio segundo: cuenta como empate
    rev2 = fv("Programa_Rev.02.xlsx", 1_000 * DIA + 1.2)
    assert pick_current([rev3, rev4, rev2]) is rev4


def test_empate_sin_revision_es_determinista():
    a = fv("Programa A.pdf", 1_000 * DIA)
    b = fv("Programa B.pdf", 1_000 * DIA)
    assert pick_current([a, b]) is pick_current([b, a]) is b


def test_sin_revision_mas_nuevo_que_con_revision_es_conflicto():
    con_rev = fv("Programa_Rev.04.xlsx", 1_000 * DIA)
    sin_rev = fv("Programa.xlsx", 1_010 * DIA)
    assert pick_current([con_rev, sin_rev]) is sin_rev
    assert has_rev_conflict([con_rev, sin_rev])


def test_sin_conflicto_cuando_fecha_y_revision_coinciden():
    versiones = [fv("Programa_Rev.04.xlsx", 1_000 * DIA), fv("Programa_Rev.05.xlsx", 1_010 * DIA)]
    assert not has_rev_conflict(versiones)
    assert not has_rev_conflict([fv("Programa.xlsx", 1_000 * DIA)])


def test_sort_versions_vigente_primero():
    v3 = fv("Programa_Rev.03.xlsx", 1_000 * DIA)
    v4 = fv("Programa_Rev.04.xlsx", 1_005 * DIA)
    v5 = fv("Programa_Rev.05.xlsx", 1_010 * DIA)
    assert sort_versions([v3, v5, v4]) == [v5, v4, v3]


def test_pick_current_sin_versiones():
    with pytest.raises(ValueError):
        pick_current([])


def test_group_documents_por_identidad_y_formato():
    files = [
        fv("F 8.4-01 - Autorización Generica_Rev.07.pdf", 1),
        fv("F 8.4-01 - Autorización Generica_Rev.07.xls", 2),
        fv("F 8.4-01 - Autorización Generica_Rev.06.pdf", 0),
        fv("F 9.1.2-01 - RAC Interno.pdf", 1),
    ]
    groups = group_documents(files)
    assert len(groups) == 2
    autorizacion = groups[parse_name(files[0].name).key]
    assert sorted(autorizacion) == ["pdf", "xls"]
    assert len(autorizacion["pdf"]) == 2
