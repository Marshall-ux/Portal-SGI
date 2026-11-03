import os

import pytest

DIA = 86_400
BASE = 1_700_000_000  # 14/11/2023, fecha base para los archivos de prueba


def _make(base, spec):
    """Crea carpetas y archivos. spec: {nombre: días desde BASE | dict (subcarpeta)}."""
    for name, value in spec.items():
        path = os.path.join(base, name)
        if isinstance(value, dict):
            os.makedirs(path, exist_ok=True)
            _make(path, value)
        else:
            with open(path, "wb") as f:
                f.write(b"x")
            mtime = BASE + value * DIA
            os.utime(path, (mtime, mtime))


@pytest.fixture
def make_tree(tmp_path):
    """Arma un disco de prueba en una carpeta temporal y devuelve su ruta."""

    def factory(spec):
        root = tmp_path / "disco"
        root.mkdir()
        _make(str(root), spec)
        return str(root)

    return factory
