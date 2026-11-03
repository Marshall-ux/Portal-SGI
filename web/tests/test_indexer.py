import os

import pytest

from app.indexer import Exclusions, build_index

DISCO = {
    "00. Guia de Acceso Documentación SGI.pdf": 10,
    "00. Mapa de Proceso.pdf": 11,
    "4. ACUERDO CON SUSCRIPTOR.pdf": 12,
    "Rol Actualizado.pdf": 13,
    "web.config": 1,
    "aspnet_client": {"system_web": {"x.js": 1}},
    "01. MANUALES  Y DOCUMENTACIÓN NEOSTAR": {
        "Thumbs.db": 1,
        "~$7.2-06 - Evaluación de desempeño_Rev.02.doc": 1,
        "04. FORMULARIOS": {
            "F 7.2-01 - Programa anual de capacitación _Rev.03.xlsx": 100,
            "F 7.2-01 - Programa anual de capacitación_Rev.04.xlsx": 200,
            "F 8.4-01 - Autorización Generica_Rev.07.pdf": 100,
            "F 8.4-01 - Autorización Generica_Rev.07.xls": 300,
            "F 10.3-01 - Informe de No Conformidad_Rev.03.doc": 50,
            "F 9.1-01 - Programa anual de mediciones_Rev.03.xlsx": 60,
        },
        "01. MANUAL INTEGRADO": {
            "2.0 Política de Calidad_Rev.05.pdf": 20,
        },
    },
    "02. PUESTOS DE TRABAJO": {
        "Vacía": {},
        "Solo basura": {"Thumbs.db": 1, ".~lock.algo.ods#": 1},
        "03. PLANES": {"plan.pdf": 1},
        "01. PERFILES": {"_F 7.2-05 -V1 - RECEPCIONISTA_ Rev.04.pdf": 1},
    },
    "10. CONTROLES DE AÑOS ANTERIORES": {
        "2019": {"a.pdf": 1},
        "2018": {"b.pdf": 1},
        "01. VENTAS": {"c.pdf": 1},
        "02. VENTAS": {"d.pdf": 1},
    },
    "03. CAPACITACIONES NEOSTAR": {
        "EXTINTORES Y TIPOS DE FUEGO.mp4": 5,
        "Matriz_Rev.05.pdf": 10,
        "Matriz_Rev.03.pdf": 20,  # guardada después: vigente por fecha, con conflicto
    },
}


@pytest.fixture
def index(make_tree):
    return build_index(make_tree(DISCO))


def titles(items):
    return [i.title if hasattr(i, "title") else i.info.title for i in items]


def test_secciones_en_orden_numerico_sin_tecnicas(index):
    assert titles(index.root.sections) == [
        "MANUALES Y DOCUMENTACIÓN NEOSTAR",
        "PUESTOS DE TRABAJO",
        "CAPACITACIONES NEOSTAR",
        "CONTROLES DE AÑOS ANTERIORES",
    ]


def test_documentos_de_la_raiz(index):
    assert [d.info.title for d in index.root.documents] == [
        "Guia de Acceso Documentación SGI",
        "Mapa de Proceso",
        "ACUERDO CON SUSCRIPTOR",
        "Rol Actualizado",
    ]


def test_exclusiones(index):
    assert sorted(index.excluded) == sorted([
        "web.config",
        "aspnet_client/",
        "01. MANUALES  Y DOCUMENTACIÓN NEOSTAR/Thumbs.db",
        "01. MANUALES  Y DOCUMENTACIÓN NEOSTAR/~$7.2-06 - Evaluación de desempeño_Rev.02.doc",
        "02. PUESTOS DE TRABAJO/Solo basura/Thumbs.db",
        "02. PUESTOS DE TRABAJO/Solo basura/.~lock.algo.ods#",
    ])


def test_carpetas_vacias_se_ocultan_y_se_informan(index):
    puestos = index.section("puestos-de-trabajo")
    assert titles(puestos.sections) == ["PERFILES", "PLANES"]
    vacias = sorted(i.relpath for i in index.issues if i.kind == "carpeta_vacia")
    assert vacias == ["02. PUESTOS DE TRABAJO/Solo basura", "02. PUESTOS DE TRABAJO/Vacía"]


def test_subcarpetas_numeradas_primero_y_orden_natural(index):
    controles = index.section("controles-de-anos-anteriores")
    assert titles(controles.sections) == ["VENTAS", "VENTAS", "2018", "2019"]
    assert [s.slug for s in controles.sections] == ["ventas", "ventas-2", "2018", "2019"]


def test_codigos_ordenados_naturalmente(index):
    formularios = index.section("manuales-y-documentacion-neostar/formularios")
    assert [d.info.code for d in formularios.documents] == ["F 7.2-01", "F 8.4-01", "F 9.1-01", "F 10.3-01"]


def test_version_vigente_y_anteriores(index):
    doc = index.document(
        "manuales-y-documentacion-neostar/formularios/f-7-2-01-programa-anual-de-capacitacion"
    )
    assert doc.primary.name == "F 7.2-01 - Programa anual de capacitación_Rev.04.xlsx"
    assert len(doc.versions["xlsx"]) == 2
    avisos = [i for i in index.issues if i.kind == "versiones_anteriores"]
    assert [(i.relpath.rsplit("/", 1)[1], i.detail) for i in avisos] == [
        ("F 7.2-01 - Programa anual de capacitación_Rev.04.xlsx",
         "F 7.2-01 - Programa anual de capacitación _Rev.03.xlsx"),
        ("Matriz_Rev.03.pdf", "Matriz_Rev.05.pdf"),
    ]


def test_pdf_y_editable_en_un_solo_documento(index):
    doc = index.document("manuales-y-documentacion-neostar/formularios/f-8-4-01-autorizacion-generica")
    assert sorted(doc.formats) == ["pdf", "xls"]
    assert doc.primary.ext == "pdf"  # el PDF es el principal aunque el xls sea más nuevo
    assert doc.mtime == doc.formats["xls"].mtime


def test_conflicto_de_revision(index):
    doc = index.document("capacitaciones-neostar/matriz")
    assert doc.primary.name == "Matriz_Rev.03.pdf"
    conflictos = [i for i in index.issues if i.kind == "conflicto_revision"]
    assert [(i.relpath, i.detail) for i in conflictos] == [
        ("03. CAPACITACIONES NEOSTAR/Matriz_Rev.03.pdf", "Revisión mayor: Matriz_Rev.05.pdf")
    ]


def test_avisos_de_nombre(index):
    kinds = {(i.kind, i.relpath.rsplit("/", 1)[1]) for i in index.issues}
    assert ("guion_bajo_inicial", "_F 7.2-05 -V1 - RECEPCIONISTA_ Rev.04.pdf") in kinds


def test_breadcrumb_y_rutas(index):
    seccion = index.section("manuales-y-documentacion-neostar/manual-integrado")
    assert [s.title for s in seccion.breadcrumb] == ["MANUALES Y DOCUMENTACIÓN NEOSTAR", "MANUAL INTEGRADO"]
    doc = seccion.documents[0]
    assert doc.path == "manuales-y-documentacion-neostar/manual-integrado/2-0-politica-de-calidad"
    assert index.document(doc.path) is doc
    assert index.section("/manuales-y-documentacion-neostar/") is seccion.parent
    assert index.section("no-existe") is None and index.document("no/existe") is None


def test_cantidades(index):
    # raíz 4 · formularios 4 · manual integrado 1 · perfiles 1 · planes 1 · controles 4 · capacitaciones 2
    assert index.root.document_count == len(index.documents) == 17
    assert index.section("manuales-y-documentacion-neostar").document_count == 5


def test_abspath_abre_el_archivo(index):
    doc = index.document("capacitaciones-neostar/extintores-y-tipos-de-fuego")
    with open(index.abspath(doc.primary), "rb") as f:
        assert f.read() == b"x"


def test_resuelve_enlace_current(make_tree, tmp_path):
    snapshot = make_tree({"01. SECCION": {"a.pdf": 1}})
    current = tmp_path / "current"
    try:
        os.symlink(snapshot, current, target_is_directory=True)
    except OSError:
        pytest.skip("Este sistema no permite crear enlaces simbólicos")
    index = build_index(str(current))
    assert index.source == os.path.realpath(snapshot)


def test_no_sigue_enlaces_dentro_del_disco(make_tree, tmp_path):
    fuera = tmp_path / "fuera"
    fuera.mkdir()
    (fuera / "secreto.pdf").write_bytes(b"x")
    root = make_tree({"01. SECCION": {"a.pdf": 1}})
    try:
        os.symlink(fuera, os.path.join(root, "01. SECCION", "atajo"), target_is_directory=True)
    except OSError:
        pytest.skip("Este sistema no permite crear enlaces simbólicos")
    index = build_index(root)
    assert len(index.documents) == 1
    assert [i.kind for i in index.issues] == ["enlace_ignorado"]


def test_exclusiones_configurables():
    ex = Exclusions.parse(" aspnet_client/ , *.TMP,borrador* ")
    assert ex.excludes("ASPNET_CLIENT", is_dir=True)
    assert not ex.excludes("aspnet_client", is_dir=False)
    assert ex.excludes("informe.tmp", is_dir=False)
    assert ex.excludes("Borrador final.pdf", is_dir=False)
    assert not ex.excludes("Informe final.pdf", is_dir=False)


def test_raiz_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError):
        build_index(str(tmp_path / "no-existe"))
