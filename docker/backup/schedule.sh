#!/bin/sh
# Her gün BACKUP_AT saatinde (sunucu saat diliminde, TZ ile verilir)
# backup.sh çalıştırır. cron yerine basit bir bekleme döngüsü: ortam
# değişkenlerini bir dosyaya kopyalamak gerekmiyor, çıktı doğrudan
# docker log'una gidiyor.
set -eu

AT="${BACKUP_AT:-03:15}"
hour=${AT%%:*}
minute=${AT##*:}

case "$hour$minute" in
    *[!0-9]*) echo "BACKUP_AT 'SS:DD' biçiminde olmalı, verilen: $AT" >&2; exit 1 ;;
esac

target=$((10#$hour * 3600 + 10#$minute * 60))

echo "Yedek saati: ${AT} (${TZ:-UTC})"

while true; do
    now=$((10#$(date +%H) * 3600 + 10#$(date +%M) * 60 + 10#$(date +%S)))
    delay=$((target - now))
    [ "$delay" -gt 0 ] || delay=$((delay + 86400))

    echo "Sıradaki yedeğe ${delay} saniye"
    sleep "$delay"

    # Bir yedek başarısız olursa döngü durmaz; yarın tekrar denenir.
    sh /usr/local/bin/backup.sh || echo "yedek başarısız oldu, yarın tekrar denenecek"
done
