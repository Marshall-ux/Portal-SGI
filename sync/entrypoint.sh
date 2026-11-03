#!/usr/bin/env bash
# Programa la sincronización diaria con cron y, si todavía no hay ninguna copia
# publicada (primer arranque), hace una sincronización inicial.
set -euo pipefail

SYNC_HORARIO="${SYNC_HORARIO:-0 6 * * *}"

# El crond de busybox no pasa el entorno del contenedor a las tareas: se guarda
# en un archivo que la tarea carga antes de ejecutar.
export -p | grep -E '^declare -x (SYNC_|PORTAL_|TZ=)' > /etc/sincronizar.env || true

echo "$SYNC_HORARIO /bin/bash -c '. /etc/sincronizar.env && /usr/local/bin/sincronizar' > /proc/1/fd/1 2>&1" \
  > /etc/crontabs/root
echo "Sincronización programada: '$SYNC_HORARIO' (zona horaria ${TZ:-UTC})."

if [[ ! -L "${SYNC_DATOS:-/data}/current" ]]; then
  echo "No hay copia publicada todavía: sincronización inicial."
  /usr/local/bin/sincronizar &
fi

exec crond -f -l 8
