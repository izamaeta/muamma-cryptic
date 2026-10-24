#!/bin/sh
# Run backup.sh daily at BACKUP_AT, in the TZ given to the container.
set -eu

AT="${BACKUP_AT:-03:15}"
hour=${AT%%:*}
minute=${AT##*:}

case "$hour$minute" in
    *[!0-9]*) echo "BACKUP_AT must look like HH:MM, got: $AT" >&2; exit 1 ;;
esac

target=$((10#$hour * 3600 + 10#$minute * 60))

echo "Backup time: ${AT} (${TZ:-UTC})"

while true; do
    now=$((10#$(date +%H) * 3600 + 10#$(date +%M) * 60 + 10#$(date +%S)))
    delay=$((target - now))
    [ "$delay" -gt 0 ] || delay=$((delay + 86400))

    echo "Next backup in ${delay}s"
    sleep "$delay"

    # A failed backup does not stop the loop.
    sh /usr/local/bin/backup.sh || echo "backup failed, retrying tomorrow"
done
