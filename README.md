# Portal SGI

Portal web de la información documentada del Sistema de Gestión Integrado (SGI) de Neostar.
Reemplaza el listado de directorios de `http://192.168.41.5/` por una navegación con tarjetas,
buscador y acceso siempre a la versión vigente de cada documento.

**Fuente de datos:** el disco I de SGI (`\\192.168.41.5\iso`). Una vez por día se copia a una
carpeta local del servidor y el portal lee esa copia. No hay base de datos ni índice aparte:
las carpetas del disco definen la navegación.

> Documento en construcción: las secciones de despliegue, convención de nombres y cómo agregar
> documentos se completan en las próximas etapas.

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
