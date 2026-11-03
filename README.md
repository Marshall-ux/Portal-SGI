# Portal SGI

Portal web de la información documentada del Sistema de Gestión Integrado (SGI) de Neostar.
Reemplaza el listado de directorios de `http://192.168.41.5/` por una navegación con tarjetas,
buscador y acceso siempre a la versión vigente de cada documento.

**Fuente de datos:** el disco I de SGI (`\\192.168.41.5\iso`). Una vez por día se copia a una
carpeta local del servidor y el portal lee esa copia. No hay base de datos ni índice aparte:
las carpetas del disco definen la navegación.

> Documento en construcción: las secciones de despliegue, convención de nombres y cómo agregar
> documentos se completan en las próximas etapas.

## Convención de nombres (para SGI)

El portal arma la navegación y elige la versión vigente a partir de los nombres de carpetas y
archivos del disco I. Siguiendo esta convención, todo aparece ordenado y sin sorpresas.

**Documentos**

```
CÓDIGO - Nombre del documento_Rev.NN.ext
```

| Parte | Ejemplo | Regla |
|---|---|---|
| Código | `F 7.2-01`, `I-8.2-08`, `IN - ADM 01` | El que ya usa SGI. Opcional para documentos sin código (capacitaciones, informes). |
| Separador | ` - ` | Espacio, guion, espacio. |
| Nombre | `Programa anual de capacitación` | Sin guion bajo al inicio. |
| Revisión | `_Rev.05` | Al final, con dos dígitos. |

Ejemplos correctos: `F 7.2-01 - Programa anual de capacitación_Rev.05.xlsx`,
`8.2.1K - Proceso Venta de Unidades 0km KIA_Rev.08.pdf`.

**Nueva versión de un documento:** se copia al disco con la revisión siguiente (`_Rev.06`).
Es la misma ficha en el portal: el link no cambia y abre siempre la versión vigente. La versión
anterior se puede borrar o dejar; si queda, el portal muestra solo la vigente y la lista en el
reporte para que SGI la retire.

**Cuál es la vigente:** la de fecha de modificación más reciente. Si dos tienen la misma fecha,
la de revisión más alta. Si alguien abre y guarda una revisión vieja, pasa a ser la más nueva:
el reporte avisa ese caso ("la más nueva por fecha no es la de mayor revisión").

**PDF y editable:** si un documento está en PDF y también en Excel/Word con el mismo nombre, el
portal muestra una sola ficha con los dos formatos.

**Carpetas:** el número inicial define el orden (`01. MANUALES…`, `02. PUESTOS…`) y no se
muestra en el portal. Las carpetas sin número van después, en orden alfabético.

**Qué tolera el portal** (funciona igual, pero conviene evitarlo): `_ Rev.04`, `Rev 04`,
`Rev04`, `. Rev.01`, datos de actualización como `(Act. 24052026)` o ` - 2026` después de la
revisión (la fecha ya la toma del archivo), dobles espacios y mayúsculas mezcladas.

**Qué marca el reporte para corregir:** nombres que empiezan con guion bajo, extensión
repetida (`.pdf.pdf`), versiones viejas en la misma carpeta y carpetas vacías.

## Estructura

```
portal-sgi/
├── web/                # App Flask (páginas, índice en memoria, entrega de archivos)
│   ├── app/
│   │   ├── versions.py # Nombres de archivo, identidad y versión vigente (módulo aislado)
│   │   └── indexer.py  # Escaneo del disco → árbol de secciones y documentos
│   └── tests/
└── sync/               # Sincronización diaria del disco (próxima etapa)
```

## Tests

Desde `web/`:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt   # Windows
.venv/Scripts/python -m pytest
```

Los tests usan árboles de prueba generados al vuelo. Además, si existe una copia real del disco
en `C:\Temp\DocumentacionISO` (o en la ruta de la variable `SGI_DISCO_PRUEBA`), se corre un test
extra contra esa copia.
