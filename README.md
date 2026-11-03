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

## Qué muestra la home

| Bloque | De dónde sale |
|---|---|
| Aclaración debajo del título | Variable `PORTAL_AVISO` del `.env` |
| Última actualización | Fecha y hora de la última sincronización correcta (`sync.json`) |
| Accesos rápidos | Documentos de la raíz del disco cuyo nombre empieza con `00.` (hoy: Guía de Acceso y Mapa de Proceso). Para sumar otro, SGI lo copia a la raíz como `00. Nombre.pdf`. |
| Certificación vigente | Sello e información de `web/config/portal.toml` |
| Documentación | Una tarjeta por carpeta principal del disco. Título, descripción e ícono en `web/config/portal.toml`; una carpeta nueva aparece igual, con su nombre y un ícono genérico. |
| Otros documentos | El resto de los archivos de la raíz del disco |

## Navegación

- **Secciones** (`/s/<carpeta>/<subcarpeta>`): una página por carpeta del disco, con ruta de navegación,
  sus subcarpetas y sus documentos como tarjetas. Los nombres de carpeta en mayúsculas se muestran con
  mayúsculas y minúsculas, conservando las siglas (`KIA SANTA FE - PV` → `KIA Santa Fe - PV`); los
  nombres de los documentos se muestran tal cual. Las carpetas por año van de la más reciente a la más vieja.
- **Documentos**: toda la tarjeta abre la versión vigente; si también hay un editable (Excel, Word), se
  descarga con su propio botón. La tarjeta muestra código, revisión, fecha de modificación y tamaño.
- **Buscador** (en el header de todas las páginas, y "Buscar en esta sección" en cada sección): por nombre,
  código o carpeta, sin acentos ni mayúsculas. Cada palabra busca comienzos de palabra ("capacit" encuentra
  "Capacitación") y primero aparecen los documentos cuyo nombre contiene la consulta tal cual.
- **Links viejos**: si un documento cambia de carpeta y su nombre es único, su link anterior redirige al nuevo.

### Renovación de la certificación

El sello se genera desde el PDF vectorial que entrega el certificador, sin modificar la marca
(página completa, sin recortes ni efectos, colores convertidos con perfil ICC):

```bash
pip install pymupdf
python tools/render_sello.py "<sello del certificador>.pdf" web/app/static/img/certificacion/<nombre>
```

Después se actualiza la sección `[certificacion]` de `web/config/portal.toml` (ID, normas,
nombre del sello y dirección de verificación, que es la misma del QR).

### Avatar de SGI

El avatar aparece en el hero de la home (el header y la pestaña del navegador usan las siglas SGI).
Sus imágenes se generan desde el original del departamento; el dibujo no se modifica: se encuadra
en un círculo para integrarlo con el fondo del portal.

```bash
pip install pillow
python tools/preparar_avatar.py "<avatar original>.png" web/app/static/img/avatar
```

## Estructura

```
portal-sgi/
├── docker-compose.yml      # Servicios y volúmenes (SMB del disco I + datos)
├── docker-compose.dev.yml  # Desarrollo: copia local del disco en lugar del SMB
├── .env.example            # Configuración (copiar a .env)
├── tools/
│   ├── render_sello.py     # PDF del certificador → imágenes del sello
│   └── preparar_avatar.py  # Avatar original de SGI → imágenes del hero
├── web/                    # App Flask (páginas, índice en memoria, entrega de archivos)
│   ├── config/portal.toml  # Presentación: secciones (títulos, descripciones, íconos) y certificación
│   ├── app/
│   │   ├── versions.py     # Nombres de archivo, identidad y versión vigente (módulo aislado)
│   │   ├── indexer.py      # Escaneo del disco → árbol de secciones y documentos
│   │   ├── store.py        # Índice vigente: se regenera solo después de cada sincronización
│   │   ├── routes.py       # Home, secciones (/s/…), buscador, documentos (/d/…) y estado (/salud)
│   │   ├── search.py       # Buscador sin acentos ni mayúsculas
│   │   ├── vistas.py       # Presentación: títulos legibles, íconos por formato
│   │   ├── templates/      # Plantillas Jinja2
│   │   └── static/         # CSS con la paleta SGI como variables, imágenes, sello
│   └── tests/
└── sync/                   # Sincronización diaria del disco
    ├── sincronizar.sh      # Copia → validación → publicación atómica
    ├── entrypoint.sh       # Programa el cron y hace la sincronización inicial
    └── tests/
```

## Sincronización del disco

El portal no lee el disco I en vivo. El servicio `sync` lo copia una vez por día (`SYNC_HORARIO`,
por defecto a las 6:00) a un volumen local, y el portal lee esa copia.

```
\\192.168.41.5\iso ──SMB, solo lectura──▶ sync ──▶ volumen sgi-data
                                                    ├── snapshots/<fecha>/   copias
                                                    ├── current → snapshots/<la publicada>
                                                    ├── sync.json            estado
                                                    └── logs/sync.log        historial
```

Cada sincronización:

1. Copia el disco con `rsync` a `snapshots/<fecha>.parcial`, **conservando la fecha de
   modificación original** de cada archivo (de eso depende la versión vigente). Los archivos
   que no cambiaron se enlazan a la copia anterior (hardlinks): cada copia nueva casi no ocupa lugar.
2. Valida: el origen no puede estar vacío (así se ve un montaje caído) y la copia nueva debe tener
   al menos el 90% de los archivos de la publicada (`SYNC_MIN_PROPORCION`).
3. Publica cambiando el enlace `current` con un rename atómico: el portal ve la copia anterior o
   la nueva, nunca una a medio copiar. El portal detecta el cambio y regenera su índice solo.
4. Conserva las últimas `SYNC_CONSERVAR` copias (3 por defecto) y borra las más viejas.

Si algo falla, **la copia publicada no cambia**: el error queda en `logs/sync.log` y en
`sync.json`, y el portal sigue mostrando la fecha de la última sincronización correcta.

Comandos útiles (desde la carpeta donde está el `docker-compose.yml`):

```bash
docker compose exec sync sincronizar            # sincronizar ahora
docker compose exec sync sincronizar --forzar   # publicar aunque falten muchos archivos (borrado intencional)
docker compose exec sync cat /data/sync.json    # estado de la última sincronización
docker compose exec sync tail -n 30 /data/logs/sync.log
docker compose logs --tail=50 sync
```

## Desarrollo local

Con una copia del disco en la PC (por defecto `C:/Temp/DocumentacionISO`, variable `SGI_DISCO_LOCAL`):

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

Solo la app web, sin Docker: `PORTAL_DATOS` apunta a una carpeta con `current` (la copia del
disco, o un enlace a ella) y opcionalmente `sync.json`.

```bash
cd web
PORTAL_DATOS=/ruta/a/datos .venv/Scripts/python -m flask --app "app:create_app" run --debug
```

## Tests

App web, desde `web/`:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt   # Windows
.venv/Scripts/python -m pytest
```

Los tests usan árboles de prueba generados al vuelo. Además, si existe una copia real del disco
en `C:\Temp\DocumentacionISO` (o en la ruta de la variable `SGI_DISCO_PRUEBA`), se corre un test
extra contra esa copia. En Windows se saltean los tests de enlaces simbólicos (requieren permisos
de administrador); para correrlos todos, en Linux:

```bash
docker run --rm -v "$PWD/web:/src:ro" python:3.12-slim \
  sh -c "cp -r /src /app && cd /app && pip install -q pytest && python -m pytest -q -p no:cacheprovider"
```

Sincronización (corre dentro de la imagen del servicio):

```bash
docker build -t portal-sgi-sync sync
docker run --rm -v "$PWD/sync/tests:/tests:ro" --entrypoint bash portal-sgi-sync /tests/test_sincronizar.sh
```
