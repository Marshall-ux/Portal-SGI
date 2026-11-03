#!/usr/bin/env bash
# Tests de la sincronización. Corren dentro de la imagen del servicio sync:
#   docker build -t portal-sgi-sync sync
#   docker run --rm -v "$PWD/sync/tests:/tests:ro" --entrypoint bash portal-sgi-sync /tests/test_sincronizar.sh
set -uo pipefail

TMP=$(mktemp -d)
export SYNC_ORIGEN="$TMP/disco" SYNC_DATOS="$TMP/data" SYNC_CONSERVAR=3 SYNC_MIN_PROPORCION=0.9
FALLAS=0
OKS=0

ok() { OKS=$((OKS + 1)); echo "  ok  $1"; }
mal() { FALLAS=$((FALLAS + 1)); echo "  MAL $1"; }
check() { local desc="$1"; shift; if "$@"; then ok "$desc"; else mal "$desc"; fi; }
estado() { jq -r "$1" "$SYNC_DATOS/sync.json"; }
publicada() { readlink "$SYNC_DATOS/current"; }
snapshots() { find "$SYNC_DATOS/snapshots" -mindepth 1 -maxdepth 1 -type d | wc -l; }
sincronizar() { /usr/local/bin/sincronizar "$@" > "$TMP/salida.txt" 2>&1; }

# Disco de prueba con nombres como los reales (acentos, dobles espacios, rutas largas)
archivo() { mkdir -p "$(dirname "$SYNC_ORIGEN/$1")"; echo "${3:-contenido}" > "$SYNC_ORIGEN/$1"; touch -d "$2" "$SYNC_ORIGEN/$1"; }
LARGA="02. PUESTOS DE TRABAJO Y DOCUMENTACIÓN ASOCIADA/04. CICLOS DE VIDA - ASPECTOS E IMPACTOS AMBIENTALES/Analisis de Ciclo de Vida - (Ventas, Administración y Post Venta)/F 6.1.2-02 - Analisis de Ciclo de Vida (Ventas, Administración y Post Venta - GENERAL)_Rev.05.pdf"
archivo "00. Mapa de Proceso.pdf" "2026-04-17 11:49:10"
archivo "01. MANUALES  Y DOCUMENTACIÓN NEOSTAR/F 7.2-01 - Programa anual de capacitación_Rev.04.xlsx" "2025-03-10 08:15:42"
archivo "01. MANUALES  Y DOCUMENTACIÓN NEOSTAR/Thumbs.db" "2020-01-01 00:00:00"
archivo "01. MANUALES  Y DOCUMENTACIÓN NEOSTAR/~\$7.2-06 - Evaluación.doc" "2020-01-01 00:00:00"
archivo "aspnet_client/system_web/x.js" "2020-09-06 10:17:00"
archivo "web.config" "2023-03-27 20:48:00"
archivo "$LARGA" "2026-11-02 17:28:48"
for i in $(seq 1 20); do archivo "03. CAPACITACIONES NEOSTAR/doc $i.pdf" "2024-01-0$((i % 9 + 1)) 10:00:00"; done

echo "1. Primera sincronización"
sincronizar
check "termina bien" grep -q "OK: 23 archivos" "$TMP/salida.txt"
check "current apunta a una copia" test -d "$SYNC_DATOS/current/03. CAPACITACIONES NEOSTAR"
check "el enlace es relativo (funciona dentro de cualquier contenedor)" bash -c "[[ $(publicada) == snapshots/* ]]"
check "conserva la fecha de modificación original" \
  test "$(stat -c %Y "$SYNC_DATOS/current/00. Mapa de Proceso.pdf")" = "$(stat -c %Y "$SYNC_ORIGEN/00. Mapa de Proceso.pdf")"
check "copia rutas largas con acentos" test -f "$SYNC_DATOS/current/$LARGA"
check "excluye Thumbs.db, temporales de Office, aspnet_client y web.config" bash -c \
  "! find '$SYNC_DATOS/current/' \( -name Thumbs.db -o -name '~\$*' -o -name aspnet_client -o -name web.config \) | grep -q ."
check "sync.json: estado ok y cantidad de archivos" test "$(estado '.ultimo_estado + " " + (.archivos|tostring)')" = "ok 23"
check "sync.json: sin error" test "$(estado .ultimo_error)" = "null"
PRIMERA=$(publicada)

echo "2. Segunda sincronización con un archivo modificado"
archivo "00. Mapa de Proceso.pdf" "2026-11-03 09:00:00" "versión nueva"
sincronizar
SEGUNDA=$(publicada)
check "publica una copia nueva" test "$PRIMERA" != "$SEGUNDA"
check "el archivo sin cambios es un hardlink (no ocupa lugar)" test \
  "$(stat -c %i "$SYNC_DATOS/$PRIMERA/03. CAPACITACIONES NEOSTAR/doc 1.pdf")" = \
  "$(stat -c %i "$SYNC_DATOS/$SEGUNDA/03. CAPACITACIONES NEOSTAR/doc 1.pdf")"
check "el archivo modificado tiene el contenido nuevo" grep -q "versión nueva" "$SYNC_DATOS/current/00. Mapa de Proceso.pdf"
check "la copia anterior queda intacta" grep -q "contenido" "$SYNC_DATOS/$PRIMERA/00. Mapa de Proceso.pdf"

echo "3. Origen vacío (montaje caído)"
mv "$SYNC_ORIGEN" "$TMP/disco.bak" && mkdir "$SYNC_ORIGEN"
sincronizar; codigo=$?
check "falla" test $codigo -ne 0
check "no cambia la copia publicada" test "$(publicada)" = "$SEGUNDA"
check "sync.json: error registrado" test "$(estado .ultimo_estado)" = "error"
check "sync.json: conserva la última correcta" test "$(estado .snapshot)" = "${SEGUNDA#snapshots/}"
check "el error queda en el log" grep -q "está vacío" "$SYNC_DATOS/logs/sync.log"
check "no deja copias a medias" bash -c "! ls -d '$SYNC_DATOS'/snapshots/*.parcial 2>/dev/null | grep -q ."
rmdir "$SYNC_ORIGEN" && mv "$TMP/disco.bak" "$SYNC_ORIGEN"

echo "4. Origen inexistente"
mv "$SYNC_ORIGEN" "$TMP/disco.bak"
sincronizar; codigo=$?
check "falla sin publicar" bash -c "[[ $codigo -ne 0 && $(publicada) == $SEGUNDA ]]"
mv "$TMP/disco.bak" "$SYNC_ORIGEN"

echo "5. Desaparece más del 10% de los archivos"
mkdir -p "$TMP/apartados" && mv "$SYNC_ORIGEN/03. CAPACITACIONES NEOSTAR" "$TMP/apartados/"
sincronizar; codigo=$?
check "no publica" bash -c "[[ $codigo -ne 0 && $(publicada) == $SEGUNDA ]]"
check "explica cómo forzar" grep -q "sincronizar --forzar" "$TMP/salida.txt"
sincronizar --forzar; codigo=$?
check "con --forzar publica" bash -c "[[ $codigo -eq 0 && $(publicada) != $SEGUNDA ]]"
check "la copia forzada tiene 3 archivos" test "$(estado .archivos)" = "3"
mv "$TMP/apartados/03. CAPACITACIONES NEOSTAR" "$SYNC_ORIGEN/"

echo "6. Conserva solo las últimas $SYNC_CONSERVAR copias (varias en el mismo segundo)"
for i in 1 2 3 4 5; do sincronizar; done
check "quedan $SYNC_CONSERVAR copias" test "$(snapshots)" -eq "$SYNC_CONSERVAR"
check "la publicada es la más nueva" test "$(publicada)" = "snapshots/$(ls "$SYNC_DATOS/snapshots" | sort | tail -n 1)"
check "la publicada existe" test -d "$SYNC_DATOS/current/03. CAPACITACIONES NEOSTAR"
check "los nombres de las copias no se repiten" test "$(grep -c 'OK:' "$SYNC_DATOS/logs/sync.log")" -eq \
  "$(grep 'OK:' "$SYNC_DATOS/logs/sync.log" | grep -o 'snapshots/[^ ]*' | sort -u | wc -l)"

echo "7. Dos sincronizaciones a la vez"
exec 8> "$SYNC_DATOS/.sync.lock"; flock 8
ANTES=$(publicada)
sincronizar; codigo=$?
check "la segunda se omite" bash -c "[[ $codigo -ne 0 ]] && grep -q 'en curso' '$TMP/salida.txt'"
check "no toca la publicada" test "$(publicada)" = "$ANTES"
exec 8>&-

echo "8. Argumento inválido"
sincronizar --otra; codigo=$?
check "muestra el uso" bash -c "[[ $codigo -eq 2 ]] && grep -q 'Uso:' '$TMP/salida.txt'"

rm -rf "$TMP"
echo
echo "Resultado: $OKS ok, $FALLAS con fallas"
[[ $FALLAS -eq 0 ]]
