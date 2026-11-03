import json
import os
from datetime import timezone

import pytest

from app import store as store_module
from app.store import IndexStore, SyncStatus


@pytest.fixture
def data(tmp_path):
    """Carpeta de datos como la deja el servicio sync, con dos copias del disco."""
    for nombre, archivos in {"2026-11-03_060000.000": ["a.pdf"], "2026-11-04_060000.000": ["a.pdf", "b.pdf"]}.items():
        carpeta = tmp_path / "snapshots" / nombre / "01. SECCION"
        carpeta.mkdir(parents=True)
        for archivo in archivos:
            (carpeta / archivo).write_bytes(b"x")
    return tmp_path


def publicar(data, nombre):
    """Igual que el servicio sync: enlace nuevo y rename atómico sobre current."""
    nuevo = data / "current.nuevo"
    try:
        os.symlink(os.path.join("snapshots", nombre), nuevo, target_is_directory=True)
    except OSError:
        pytest.skip("Este sistema no permite crear enlaces simbólicos")
    os.replace(nuevo, data / "current")


def test_sin_copia_publicada_devuelve_none(data):
    assert IndexStore(str(data)).get() is None


def test_reutiliza_el_indice_mientras_no_cambie_la_copia(data):
    publicar(data, "2026-11-03_060000.000")
    store = IndexStore(str(data))
    assert store.get() is store.get()
    assert len(store.get().documents) == 1


def test_regenera_cuando_se_publica_otra_copia(data):
    publicar(data, "2026-11-03_060000.000")
    store = IndexStore(str(data))
    primero = store.get()
    publicar(data, "2026-11-04_060000.000")
    segundo = store.get()
    assert segundo is not primero
    assert len(segundo.documents) == 2
    assert segundo.source.endswith("2026-11-04_060000.000")


def test_si_falla_el_escaneo_mantiene_el_indice_anterior(data, monkeypatch):
    publicar(data, "2026-11-03_060000.000")
    store = IndexStore(str(data))
    primero = store.get()

    def falla(*args, **kwargs):
        raise OSError("disco ilegible")

    monkeypatch.setattr(store_module, "build_index", falla)
    publicar(data, "2026-11-04_060000.000")
    assert store.get() is primero


def test_carpeta_comun_como_current(tmp_path):
    """En desarrollo, current puede ser una carpeta común en lugar de un enlace."""
    (tmp_path / "current" / "01. SECCION").mkdir(parents=True)
    (tmp_path / "current" / "01. SECCION" / "a.pdf").write_bytes(b"x")
    assert len(IndexStore(str(tmp_path)).get().documents) == 1


def test_estado_de_sincronizacion(tmp_path):
    (tmp_path / "sync.json").write_text(json.dumps({
        "ultima_ok": "2026-11-04T09:00:03Z",
        "snapshot": "2026-11-04_060000.000",
        "archivos": 641,
        "ultimo_intento": "2026-11-05T09:00:01Z",
        "ultimo_estado": "error",
        "ultimo_error": "El origen /mnt/disco está vacío o no se puede leer.",
        "duracion_s": 2,
    }), encoding="utf-8")
    estado = IndexStore(str(tmp_path)).status()
    assert estado.ultima_ok.astimezone(timezone.utc).isoformat() == "2026-11-04T09:00:03+00:00"
    assert estado.ultima_ok.tzinfo is not None
    assert (estado.archivos, estado.snapshot) == (641, "2026-11-04_060000.000")
    assert estado.fallo_el_ultimo_intento
    assert "vacío" in estado.ultimo_error


@pytest.mark.parametrize("contenido", [None, "esto no es json", "[1, 2]", '{"ultima_ok": "ayer"}'])
def test_estado_ausente_o_invalido(tmp_path, contenido):
    if contenido is not None:
        (tmp_path / "sync.json").write_text(contenido, encoding="utf-8")
    estado = SyncStatus.read(str(tmp_path / "sync.json"))
    assert estado.ultima_ok is None
    assert not estado.fallo_el_ultimo_intento
