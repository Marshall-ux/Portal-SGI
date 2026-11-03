"""Índice vigente y estado de la sincronización.

La copia del disco vive en la carpeta de datos que comparte el servicio sync:
  current     enlace a la copia publicada (snapshots/<fecha>)
  sync.json   resultado de la última sincronización

En cada pedido se consulta a dónde apunta "current" (una lectura de enlace,
barata). Si cambió desde el último escaneo, se regenera el índice: así el
portal toma cada sincronización sin reiniciarse.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass
from datetime import datetime

from .indexer import Exclusions, Index, build_index

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SyncStatus:
    """Contenido de sync.json. Todos los campos son None si todavía no hubo sincronización."""

    ultima_ok: datetime | None = None
    snapshot: str | None = None
    archivos: int | None = None
    ultimo_intento: datetime | None = None
    ultimo_estado: str | None = None  # "ok" o "error"
    ultimo_error: str | None = None

    @property
    def fallo_el_ultimo_intento(self) -> bool:
        return self.ultimo_estado == "error"

    @classmethod
    def read(cls, path: str) -> SyncStatus:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            return cls()
        except (OSError, ValueError) as e:
            log.warning("No se pudo leer %s: %s", path, e)
            return cls()
        if not isinstance(data, dict):
            return cls()
        return cls(
            ultima_ok=_fecha(data.get("ultima_ok")),
            snapshot=data.get("snapshot"),
            archivos=data.get("archivos"),
            ultimo_intento=_fecha(data.get("ultimo_intento")),
            ultimo_estado=data.get("ultimo_estado"),
            ultimo_error=data.get("ultimo_error"),
        )


def _fecha(valor) -> datetime | None:
    """Fecha ISO de sync.json (en UTC) convertida a la hora local del servidor."""
    if not isinstance(valor, str):
        return None
    try:
        return datetime.fromisoformat(valor).astimezone()
    except ValueError:
        return None


class IndexStore:
    """Mantiene el índice de la copia publicada y lo regenera cuando cambia."""

    def __init__(self, data_dir: str, exclusions: Exclusions | None = None):
        self.current = os.path.join(data_dir, "current")
        self.status_path = os.path.join(data_dir, "sync.json")
        self.exclusions = exclusions
        self._index: Index | None = None
        self._lock = threading.Lock()

    def get(self) -> Index | None:
        """Índice de la copia publicada; None si todavía no hay ninguna."""
        target = self._target()
        if target is None:
            return self._index
        if self._index is not None and self._index.source == target:
            return self._index
        with self._lock:
            # Otro hilo pudo haberlo regenerado mientras esperábamos
            if self._index is None or self._index.source != target:
                try:
                    self._index = build_index(target, self.exclusions)
                    log.info("Índice regenerado: %s (%d documentos)", target, len(self._index.documents))
                except Exception:
                    # Mejor seguir mostrando la copia anterior que dejar el portal sin datos
                    log.exception("No se pudo escanear %s; se mantiene el índice anterior", target)
        return self._index

    def status(self) -> SyncStatus:
        return SyncStatus.read(self.status_path)

    def _target(self) -> str | None:
        if not os.path.isdir(self.current):
            return None
        return os.path.realpath(self.current)
