FROM alpine:3.20

# coreutils: "mv -T" para el cambio atómico de la copia publicada
# tzdata: la hora programada (SYNC_HORARIO) se interpreta en la zona de TZ
RUN apk add --no-cache bash coreutils jq rsync tzdata

COPY sincronizar.sh /usr/local/bin/sincronizar
COPY entrypoint.sh /usr/local/bin/entrypoint
RUN chmod +x /usr/local/bin/sincronizar /usr/local/bin/entrypoint

VOLUME ["/data"]
ENTRYPOINT ["/usr/local/bin/entrypoint"]
