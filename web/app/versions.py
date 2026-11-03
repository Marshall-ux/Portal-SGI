"""Nombres de archivo, identidad de documentos y versión vigente.

Módulo aislado (solo biblioteca estándar, sin acceso a disco): recibe nombres
y fechas de modificación, y decide qué archivo es la versión vigente de cada
documento.

Regla de versión vigente acordada con SGI:
  1. Gana la fecha de modificación original más reciente.
  2. Si dos versiones tienen la misma fecha (diferencia menor a
     MTIME_TOLERANCE), gana el número de revisión más alto del nombre.
  3. Si sigue el empate, decide el nombre del archivo, para que el resultado
     sea siempre el mismo.

Identidad: dos archivos son versiones del mismo documento si, dentro de la
misma carpeta y con la misma extensión, su nombre coincide después de quitar
el número de orden ("01. "), la revisión ("_Rev.04") con sus datos de versión
("(Act. 24052026)", " - 2026"), los acentos, las mayúsculas y la puntuación.
"""
from __future__ import annotations

import os
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Sequence

# Diferencia máxima, en segundos, para considerar que dos fechas son iguales.
# Absorbe redondeos de copia (HTTP y FAT redondean a 1-2 segundos).
MTIME_TOLERANCE = 2.0

# Número de orden al inicio: "01. MANUALES …", "4. ACUERDO …".
# Exige espacio después del punto para no confundirlo con códigos como "8.2.3-A".
_ORDER_RE = re.compile(r"^(\d{1,3})\s*[.)]\s+(?=\S)")

# Revisión y, a continuación, datos de la versión que no forman parte de la
# identidad. Variantes reales del disco: "_Rev.04", "_ Rev.04", "__Rev.00",
# " Rev 14", "Rev01", "rev.04", ". Rev.01", " - Rev.02", "_Rev.04 - 2026",
# "_Rev.03 ( Act. 19092022)", "_Rev.01 (Ult.Act. 24052026)", "rev.04 act(24052026)".
_REV_RE = re.compile(
    r"""
    [\s_.\-]*                                   # separadores previos
    (?<![^\W\d_])                               # "rev" no pegado a una letra (Prev, Abrev)
    rev(?:isi[oó]n)?\s*\.{0,2}\s*
    (?P<rev>\d{1,3})(?!\d)
    (?P<meta>(?:
        \s*\.*\s*-\s*(?:19|20)\d{2}(?!\d)                    # " - 2026"
      | \s*\.*\s*\(\s*(?:ult\.?\s*)?act\.*\s*[\d./\-\s]*\)   # "(Act. 24052026)"
      | \s*act\s*\(\s*[\d./\-\s]*\)                          # "act(24052026)"
    )*)
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Código de documento al inicio del nombre (solo para mostrar, no para la
# identidad): "F 7.2-01", "F.7.2 04", "F-4.0-01", "I-8.2-08", "IN - ADM NEO 01",
# "8.2.1BYD", "8.4.5A", "F 8.2-02.A2e", "F 7.2-05 -PV.10", "F 7.2-05 - E1".
_CODE_RE = re.compile(
    r"""^(?P<code>
        (?:[A-Z]{1,3}(?:\s*-\s*[A-Z]{2,4}(?:\s+[A-Z]{2,4})*)?\s*[.\-]?\s*)?  # prefijo: F, I-, IN - ADM
        \d{1,2}(?:[.\-]\d{1,2})*(?:[\s.\-]\d{2}(?!\d))?                     # 7.2-05 · 1.0 01 · 00-02
        (?:\.?[A-Z]{1,3}\d{0,2}[a-z]?)?                                     # 01A · 8.2.1BYD · .A2e
        (?:\s*-\s*[A-Z]{1,2}\.?\d{1,2})?                                    # -A11 · -PV.10 · - E1
    )(?=[\s.\-])[\s.\-]+(?P<title>\S.*)$""",
    re.VERBOSE,
)


@dataclass(frozen=True)
class ParsedName:
    """Partes de un nombre de archivo o carpeta del disco SGI."""

    original: str
    ext: str  # en minúsculas y sin punto; "" si no tiene
    order: int | None  # número de orden inicial ("01. ") o None
    code: str | None  # código de documento ("F 7.2-01") o None
    title: str  # nombre para mostrar, sin orden, código, revisión ni extensión
    rev: int | None  # número de revisión o None
    rev_token: str | None  # texto de la revisión tal como aparece ("_ Rev.04 (Act. 24052026)")
    key: str  # identidad del documento (sin orden, revisión ni extensión)
    notes: tuple[str, ...] = ()  # rarezas del nombre, para el reporte

    @property
    def label(self) -> str:
        """Nombre completo para mostrar: código + título."""
        return f"{self.code} - {self.title}" if self.code else self.title


def normalize(text: str) -> str:
    """Texto comparable: sin acentos, en minúsculas y con espacios simples."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.casefold().replace("_", " ")
    return " ".join(text.split())


def identity_key(text: str) -> str:
    """Clave de identidad: solo letras y números, separados por un espacio."""
    return " ".join(re.findall(r"[a-z0-9]+", normalize(text)))


def slugify(text: str) -> str:
    """Fragmento de URL legible y estable a partir de un nombre."""
    return identity_key(text).replace(" ", "-") or "sin-nombre"


def natural_key(text: str) -> list:
    """Clave de orden natural ("2" antes que "10"), sin acentos ni mayúsculas."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", normalize(text))]


def _clean(text: str) -> str:
    """Guiones bajos como espacios, espacios simples y sin separadores en los bordes."""
    text = " ".join(text.replace("_", " ").split())
    return text.strip(" .-")


def parse_name(name: str, is_dir: bool = False) -> ParsedName:
    """Interpreta un nombre de archivo (o de carpeta, con is_dir=True)."""
    notes: list[str] = []
    stem, ext = (name, "") if is_dir else os.path.splitext(name)
    ext = ext[1:].lower()

    # "X.pdf.pdf": la extensión repetida queda dentro del nombre
    if ext and stem.lower().endswith("." + ext):
        stem = stem[: -len(ext) - 1]
        notes.append("doble_extension")

    if stem.startswith("_"):
        notes.append("guion_bajo_inicial")
    stem = stem.lstrip("_ ")

    order = None
    m = _ORDER_RE.match(stem)
    if m:
        order = int(m.group(1))
        stem = stem[m.end():]

    rev = rev_token = None
    matches = list(_REV_RE.finditer(stem))
    if matches:
        m = matches[-1]  # la revisión va al final; si hubiera dos, vale la última
        rev = int(m.group("rev"))
        rev_token = m.group(0).strip()
        stem = f"{stem[:m.start()]} {stem[m.end():]}"

    label = _clean(stem) or _clean(name)
    code, title = None, label
    m = _CODE_RE.match(label)
    # Un código válido empieza con letra ("F 7.2-01") o tiene números separados
    # ("3.0", "7.2-03"); así "8 Procesos" o "20260507 - Informe" no se parten.
    if m and (m.group("code")[0].isalpha() or re.search(r"\d[.\-\s]\d", m.group("code"))):
        code, title = _clean(m.group("code")), _clean(m.group("title"))

    return ParsedName(
        original=name,
        ext=ext,
        order=order,
        code=code,
        title=title,
        rev=rev,
        rev_token=rev_token,
        key=identity_key(label),
        notes=tuple(notes),
    )


@dataclass(frozen=True)
class FileVersion:
    """Un archivo concreto del disco: una versión (en un formato) de un documento."""

    name: str
    mtime: float  # fecha de modificación original (timestamp)
    size: int = 0
    relpath: str = ""  # ruta relativa a la raíz del disco, con "/"
    parsed: ParsedName = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "parsed", parse_name(self.name))

    @property
    def rev(self) -> int | None:
        return self.parsed.rev

    @property
    def ext(self) -> str:
        return self.parsed.ext

    @property
    def key(self) -> str:
        return self.parsed.key


def pick_current(versions: Sequence[FileVersion]) -> FileVersion:
    """Elige la versión vigente según la regla del módulo."""
    if not versions:
        raise ValueError("No hay versiones para elegir")
    newest = max(v.mtime for v in versions)
    tied = [v for v in versions if newest - v.mtime < MTIME_TOLERANCE]
    return max(tied, key=lambda v: (v.rev if v.rev is not None else -1, v.mtime, v.name))


def sort_versions(versions: Sequence[FileVersion]) -> list[FileVersion]:
    """La vigente primero; las anteriores, de la más nueva a la más vieja."""
    current = pick_current(versions)
    others = sorted((v for v in versions if v is not current), key=lambda v: v.mtime, reverse=True)
    return [current, *others]


def has_rev_conflict(versions: Sequence[FileVersion]) -> bool:
    """True si la vigente (por fecha) no es la de revisión más alta.

    Pasa, por ejemplo, si alguien abre y guarda una revisión vieja: queda con
    fecha más nueva y el portal la muestra como vigente. Se informa en el
    reporte para que SGI lo revise.
    """
    current = pick_current(versions)
    best_rev = max((v.rev for v in versions if v.rev is not None), default=None)
    return best_rev is not None and (current.rev is None or best_rev > current.rev)


def group_documents(files: Iterable[FileVersion]) -> dict[str, dict[str, list[FileVersion]]]:
    """Agrupa archivos de una misma carpeta: identidad → extensión → versiones."""
    groups: dict[str, dict[str, list[FileVersion]]] = defaultdict(lambda: defaultdict(list))
    for f in files:
        groups[f.key][f.ext].append(f)
    return {key: dict(by_ext) for key, by_ext in groups.items()}
