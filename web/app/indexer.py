"""Escaneo de la copia del disco SGI y armado del índice navegable en memoria.

El índice refleja las carpetas del disco: cada carpeta es una sección y cada
grupo de archivos con la misma identidad es un documento (ver versions.py),
con su versión vigente en cada formato.

Se arma sobre una copia concreta: si la raíz es un enlace ("current"), se
resuelve antes de escanear, así una sincronización que cambie el enlace a
mitad de camino no mezcla dos copias.
"""
from __future__ import annotations

import fnmatch
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterator

from .versions import (
    FileVersion,
    ParsedName,
    convention_issues,
    group_documents,
    has_rev_conflict,
    natural_key,
    parse_name,
    slugify,
    sort_versions,
)

DEFAULT_EXCLUDES = "aspnet_client/, web.config, Thumbs.db, desktop.ini, ~$*, .~lock.*#, *.tmp, .*"

# El formato principal de un documento es el primero disponible de esta lista;
# los demás se ofrecen como descarga del editable.
FORMAT_PRIORITY = ("pdf", "docx", "doc", "xlsx", "xlsm", "xls", "ods", "odt", "pptx", "ppt")

ISSUE_KINDS = {
    "versiones_anteriores": "Versiones anteriores en la misma carpeta (se publica solo la vigente)",
    "conflicto_revision": "La versión más nueva por fecha no es la de mayor revisión",
    "doble_extension": "Extensión repetida en el nombre",
    "guion_bajo_inicial": "Nombre que empieza con guion bajo",
    "carpeta_vacia": "Carpeta sin documentos publicables",
    "enlace_ignorado": "Enlace simbólico (no se publica)",
    "sin_revision": "Documento con código y sin revisión en el nombre",
    "revision_no_estandar": "Revisión escrita distinto de _Rev.NN",
}


class Exclusions:
    """Patrones de archivos y carpetas que no se publican.

    Se comparan contra el nombre (no la ruta) sin distinguir mayúsculas, con
    comodines estilo shell. Un patrón que termina en "/" aplica solo a carpetas.
    """

    def __init__(self, patterns: list[str]):
        self.patterns = [p.strip() for p in patterns if p.strip()]
        self._dirs = [p[:-1].lower() for p in self.patterns if p.endswith("/")]
        self._any = [p.lower() for p in self.patterns if not p.endswith("/")]

    @classmethod
    def parse(cls, text: str) -> Exclusions:
        """Lista separada por comas, tal como viene del .env."""
        return cls(text.split(","))

    def excludes(self, name: str, is_dir: bool) -> bool:
        name = name.lower()
        patterns = self._any + self._dirs if is_dir else self._any
        return any(fnmatch.fnmatchcase(name, p) for p in patterns)


@dataclass(frozen=True)
class Issue:
    """Algo del disco que SGI debería revisar. Alimenta el reporte."""

    kind: str  # clave de ISSUE_KINDS
    relpath: str
    detail: str = ""


@dataclass(eq=False)
class Document:
    """Un documento: todas sus versiones, agrupadas por formato."""

    key: str
    versions: dict[str, list[FileVersion]]  # extensión → versiones, la vigente primero
    section: Section = field(repr=False)
    slug: str = ""

    @property
    def formats(self) -> dict[str, FileVersion]:
        """Versión vigente de cada formato."""
        return {ext: vs[0] for ext, vs in self.versions.items()}

    @property
    def primary(self) -> FileVersion:
        """Versión vigente del formato principal (PDF si existe)."""
        ext = next((e for e in FORMAT_PRIORITY if e in self.versions), min(self.versions))
        return self.versions[ext][0]

    @property
    def info(self) -> ParsedName:
        return self.primary.parsed

    @property
    def path(self) -> str:
        return f"{self.section.path}/{self.slug}" if self.section.path else self.slug

    @property
    def mtime(self) -> float:
        return max(v.mtime for v in self.formats.values())


@dataclass(eq=False)
class Section:
    """Una carpeta del disco con sus subcarpetas y documentos publicables."""

    name: str  # nombre real de la carpeta ("" para la raíz)
    relpath: str  # ruta relativa a la raíz del disco, con "/"
    parent: Section | None = field(default=None, repr=False)
    sections: list[Section] = field(default_factory=list, repr=False)
    documents: list[Document] = field(default_factory=list, repr=False)
    slug: str = ""
    path: str = ""  # ruta de URL: slugs desde la raíz, separados por "/"

    @property
    def info(self) -> ParsedName:
        return parse_name(self.name, is_dir=True)

    @property
    def title(self) -> str:
        return self.info.title if self.name else ""

    @property
    def breadcrumb(self) -> list[Section]:
        """Secciones desde la primera bajo la raíz hasta esta, inclusive."""
        chain, node = [], self
        while node is not None and node.parent is not None:
            chain.append(node)
            node = node.parent
        return chain[::-1]

    def walk(self) -> Iterator[Section]:
        """Esta sección y todas sus descendientes."""
        yield self
        for child in self.sections:
            yield from child.walk()

    @property
    def document_count(self) -> int:
        """Documentos en esta sección y sus subsecciones."""
        return sum(len(s.documents) for s in self.walk())


@dataclass(eq=False)
class Index:
    """Resultado del escaneo: árbol de secciones, búsqueda por ruta y avisos."""

    source: str  # carpeta escaneada, con enlaces ya resueltos
    root: Section
    built_at: datetime
    duration: float  # segundos que tardó el escaneo
    excluded: list[str]  # rutas relativas que no se publican
    issues: list[Issue]
    _fs_source: str = field(repr=False, default="")
    _sections: dict[str, Section] = field(repr=False, default_factory=dict)
    _documents: dict[str, Document] = field(repr=False, default_factory=dict)
    _by_relpath: dict[str, Section] = field(repr=False, default_factory=dict)

    def section(self, path: str) -> Section | None:
        return self._sections.get(path.strip("/"))

    def section_of(self, relpath: str) -> Section | None:
        """Sección publicada más cercana que contiene una ruta del disco (archivo o carpeta)."""
        partes = relpath.strip("/").split("/")
        while partes:
            partes.pop()
            section = self._by_relpath.get("/".join(partes))
            if section is not None:
                return section
        return None

    def document(self, path: str) -> Document | None:
        return self._documents.get(path.strip("/"))

    def moved_document(self, path: str) -> Document | None:
        """Documento que ya no está en esa ruta pero cuyo nombre es único en el disco: se movió de carpeta."""
        slug = path.strip("/").rsplit("/", 1)[-1]
        candidatos = [d for d in self._documents.values() if d.slug == slug]
        return candidatos[0] if len(candidatos) == 1 else None

    @property
    def documents(self) -> list[Document]:
        return list(self._documents.values())

    def abspath(self, version: FileVersion) -> str:
        """Ruta en disco de una versión, lista para abrir el archivo."""
        return os.path.join(self._fs_source, *version.relpath.split("/"))


def build_index(root: str, exclusions: Exclusions | None = None) -> Index:
    """Escanea la carpeta root y devuelve el índice navegable."""
    exclusions = exclusions or Exclusions.parse(DEFAULT_EXCLUDES)
    source = os.path.realpath(root)
    if not os.path.isdir(source):
        raise FileNotFoundError(f"No existe la carpeta del disco: {root}")

    started = time.monotonic()
    builder = _Builder(exclusions)
    fs_source = _fs_path(source)
    top = Section(name="", relpath="")
    builder.scan(top, fs_source)

    index = Index(
        source=source,
        root=top,
        built_at=datetime.now(),
        duration=0.0,
        excluded=builder.excluded,
        issues=builder.issues,
        _fs_source=fs_source,
    )
    _finalize(top, index)
    index.duration = time.monotonic() - started
    return index


class _Builder:
    def __init__(self, exclusions: Exclusions):
        self.exclusions = exclusions
        self.excluded: list[str] = []
        self.issues: list[Issue] = []

    def scan(self, section: Section, fs_dir: str) -> None:
        files: list[FileVersion] = []
        with os.scandir(fs_dir) as it:
            entries = sorted(it, key=lambda e: e.name)

        for entry in entries:
            rel = f"{section.relpath}/{entry.name}" if section.relpath else entry.name
            if entry.is_symlink():
                # Un enlace podría apuntar fuera del disco: nunca se sigue
                self.issues.append(Issue("enlace_ignorado", rel))
                continue
            is_dir = entry.is_dir(follow_symlinks=False)
            if self.exclusions.excludes(entry.name, is_dir):
                self.excluded.append(rel + "/" if is_dir else rel)
                continue
            if is_dir:
                child = Section(name=entry.name, relpath=rel, parent=section)
                self.scan(child, entry.path)
                if child.sections or child.documents:
                    section.sections.append(child)
                else:
                    self.issues.append(Issue("carpeta_vacia", rel))
            else:
                st = entry.stat(follow_symlinks=False)
                files.append(FileVersion(name=entry.name, mtime=st.st_mtime, size=st.st_size, relpath=rel))

        section.documents = self._documents(section, files)

    def _documents(self, section: Section, files: list[FileVersion]) -> list[Document]:
        docs = []
        for key, by_ext in group_documents(files).items():
            versions = {ext: sort_versions(vs) for ext, vs in sorted(by_ext.items())}
            docs.append(Document(key=key, versions=versions, section=section))
            for vs in versions.values():
                if len(vs) > 1:
                    older = ", ".join(v.name for v in vs[1:])
                    self.issues.append(Issue("versiones_anteriores", vs[0].relpath, older))
                if has_rev_conflict(vs):
                    top_rev = max((v for v in vs if v.rev is not None), key=lambda v: v.rev)
                    self.issues.append(Issue("conflicto_revision", vs[0].relpath, f"Revisión mayor: {top_rev.name}"))
        for f in files:
            self.issues.extend(Issue(note, f.relpath) for note in f.parsed.notes)
            self.issues.extend(Issue(kind, f.relpath, detail) for kind, detail in convention_issues(f.parsed))
        return docs


_ANIO = re.compile(r"(19|20)\d{2}")


def _sort_key(info: ParsedName) -> tuple:
    """Primero los numerados ("01.", "02."…) por número; después, por nombre."""
    return (info.order is None, info.order or 0, natural_key(info.label))


def _finalize(section: Section, index: Index) -> None:
    """Ordena, asigna slugs y rutas, y registra secciones y documentos en el índice."""
    index._sections[section.path] = section
    index._by_relpath[section.relpath] = section

    section.sections.sort(key=lambda s: _sort_key(s.info))
    # Carpetas por año ("2018", "2019"…): primero la más reciente
    if section.sections and all(_ANIO.fullmatch(s.title) for s in section.sections):
        section.sections.reverse()
    used: set[str] = set()
    for child in section.sections:
        child.slug = _unique(slugify(child.title), used)
        child.path = f"{section.path}/{child.slug}" if section.path else child.slug
        _finalize(child, index)

    section.documents.sort(key=lambda d: _sort_key(d.info))
    used = set()
    for doc in section.documents:
        doc.slug = _unique(slugify(doc.info.label), used)
        index._documents[doc.path] = doc


def _unique(slug: str, used: set[str]) -> str:
    candidate, n = slug, 2
    while candidate in used:
        candidate, n = f"{slug}-{n}", n + 1
    used.add(candidate)
    return candidate


def _fs_path(path: str) -> str:
    """En Windows, prefijo para rutas largas: el disco SGI tiene rutas de más de 260 caracteres."""
    if os.name != "nt" or path.startswith("\\\\?\\"):
        return path
    path = os.path.abspath(path)
    return "\\\\?\\UNC\\" + path[2:] if path.startswith("\\\\") else "\\\\?\\" + path
