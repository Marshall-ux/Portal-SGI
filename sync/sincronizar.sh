#!/usr/bin/env bash
# Copia el disco SGI a una carpeta nueva y la publica de forma atómica.
#
#   $SYNC_ORIGEN (/mnt/disco)   disco I de SGI, montado en solo lectura
#   $SYNC_DATOS  (/data)
#     snapshots/<fecha>/        copias; los archivos sin cambios son hardlinks a la anterior
#     current                   enlace a la copia publicada (es lo que lee el portal)
#     sync.json                 estado de la última sincronización (lo muestra el portal)
#     logs/sync.log             historial de sincronizaciones
#
# Uso: sincronizar [--forzar]
#   --forzar  publica aunque la copia nueva tenga muchos menos archivos que la
#             anterior (por ejemplo, si SGI borró una carpeta a propósito).
#
# Si algo falla, la copia publicada no cambia y el error queda en el log y en sync.json.
set -euo pipefail

ORIGEN="${SYNC_ORIGEN:-/mnt/disco}"
DATOS="${SYNC_DATOS:-/data}"
CONSERVAR="${SYNC_CONSERVAR:-3}"
MIN_PROPORCION="${SYNC_MIN_PROPORCION:-0.9}"
EXCLUSIONES="${PORTAL_EXCLUSIONES-aspnet_client/, web.config, Thumbs.db, desktop.ini, ~\$*, .~lock.*#, *.tmp, .*}"

FORZAR=0
case "${1:-}" in
  "") ;;
  --forzar) FORZAR=1 ;;
  *) echo "Uso: sincronizar [--forzar]" >&2; exit 2 ;;
esac

SNAPSHOTS="$DATOS/snapshots"
ACTUAL="$DATOS/current"
ESTADO="$DATOS/sync.json"
LOG="$DATOS/logs/sync.log"
mkdir -p "$SNAPSHOTS" "$DATOS/logs"
(( CONSERVAR >= 1 )) || CONSERVAR=1

log() {
  local linea
  linea="$(date '+%Y-%m-%d %H:%M:%S') $*"
  echo "$linea"
  echo "$linea" >> "$LOG"
}

# Una sola sincronización a la vez: la programada y una manual pueden coincidir.
exec 9> "$DATOS/.sync.lock"
if ! flock -n 9; then
  log "Ya hay una sincronización en curso; esta se omite."
  exit 1
fi

INICIO=$(date +%s)
# Con milisegundos: los nombres nunca se repiten y ordenarlos es ordenarlos en el tiempo.
NOMBRE=$(date '+%Y-%m-%d_%H%M%S.%3N')
while [[ -e "$SNAPSHOTS/$NOMBRE" ]]; do NOMBRE=$(date '+%Y-%m-%d_%H%M%S.%3N'); done
DESTINO="$SNAPSHOTS/$NOMBRE.parcial"
ARCHIVOS=null

# Guarda el resultado en sync.json sin perder los datos de la última sincronización correcta.
escribir_estado() {
  local estado="$1" mensaje="${2:-}" previo='{}'
  if [[ -s "$ESTADO" ]] && jq -e 'type == "object"' "$ESTADO" > /dev/null 2>&1; then
    previo=$(cat "$ESTADO")
  fi
  jq -n \
    --argjson previo "$previo" \
    --arg estado "$estado" \
    --arg mensaje "$mensaje" \
    --arg ahora "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
    --arg snapshot "$NOMBRE" \
    --argjson archivos "$ARCHIVOS" \
    --argjson duracion "$(( $(date +%s) - INICIO ))" \
    '$previo
     + {ultimo_intento: $ahora, ultimo_estado: $estado, duracion_s: $duracion,
        ultimo_error: (if $estado == "ok" then null else $mensaje end)}
     + (if $estado == "ok" then {ultima_ok: $ahora, snapshot: $snapshot, archivos: $archivos} else {} end)' \
    > "$ESTADO.tmp"
  mv -f "$ESTADO.tmp" "$ESTADO"
}

fallar() {
  log "ERROR: $1 La copia publicada no cambia."
  rm -rf "$DESTINO"
  escribir_estado error "$1"
  exit 1
}

log "Inicio de sincronización: $ORIGEN → snapshots/$NOMBRE"

[[ -d "$ORIGEN" ]] || fallar "No se encuentra el origen $ORIGEN."
# Un montaje SMB caído suele verse como una carpeta vacía.
[[ -n "$(ls -A "$ORIGEN" 2> /dev/null)" ]] || fallar "El origen $ORIGEN está vacío o no se puede leer."

# Restos de corridas interrumpidas (reinicio del contenedor a mitad de copia).
rm -rf "$SNAPSHOTS"/*.parcial

# -r recursivo, -t conserva la fecha de modificación original (de eso depende la
# versión vigente). Sin -l: los enlaces simbólicos del origen no se copian.
args=(-rt --no-specials --no-devices --stats)
if [[ -L "$ACTUAL" ]]; then
  args+=("--link-dest=$(readlink -f "$ACTUAL")")
fi
IFS=',' read -ra patrones <<< "$EXCLUSIONES"
for p in "${patrones[@]}"; do
  p="${p#"${p%%[![:space:]]*}"}"   # recorta espacios
  p="${p%"${p##*[![:space:]]}"}"
  [[ -n "$p" ]] && args+=("--exclude=$p")
done

set +e
rsync "${args[@]}" "$ORIGEN/" "$DESTINO/" > "$DATOS/logs/rsync-ultimo.log" 2>&1
codigo=$?
set -e
case $codigo in
  0) ;;
  24) log "Aviso: algunos archivos desaparecieron durante la copia (alguien los movió o borró)." ;;
  *)
    tail -n 15 "$DATOS/logs/rsync-ultimo.log" >> "$LOG"
    fallar "rsync terminó con código $codigo (detalle en logs/rsync-ultimo.log)."
    ;;
esac

ARCHIVOS=$(find "$DESTINO" -type f | wc -l)
(( ARCHIVOS > 0 )) || fallar "La copia nueva no tiene archivos."

# Protección ante un disco que responde a medias: si desaparece una porción
# grande de archivos, no se publica salvo que se fuerce.
if [[ -L "$ACTUAL" && $FORZAR -eq 0 ]]; then
  ANTERIOR=$(find -L "$ACTUAL/" -type f | wc -l)
  MINIMO=$(awk -v a="$ANTERIOR" -v p="$MIN_PROPORCION" 'BEGIN { printf "%d", a * p }')
  if (( ARCHIVOS < MINIMO )); then
    fallar "La copia nueva tiene $ARCHIVOS archivos y la publicada $ANTERIOR (mínimo $MINIMO). Si la baja es intencional, ejecutar: sincronizar --forzar."
  fi
fi

mv "$DESTINO" "$SNAPSHOTS/$NOMBRE"
# rename(2) es atómico: el portal ve la copia anterior o la nueva, nunca un estado intermedio.
ln -s "snapshots/$NOMBRE" "$DATOS/current.nuevo"
mv -Tf "$DATOS/current.nuevo" "$ACTUAL"
escribir_estado ok

# Conserva la publicada y las CONSERVAR-1 anteriores más nuevas. La publicada se
# excluye explícitamente: nunca se borra, ordenen como ordenen los nombres.
find "$SNAPSHOTS" -mindepth 1 -maxdepth 1 -type d ! -name '*.parcial' ! -name "$NOMBRE" | sort -r |
  tail -n +"$CONSERVAR" |
  while IFS= read -r viejo; do
    rm -rf "$viejo"
    log "Copia anterior eliminada: $(basename "$viejo")"
  done

log "OK: $ARCHIVOS archivos publicados en snapshots/$NOMBRE ($(( $(date +%s) - INICIO )) s)."
