#!/bin/sh
# Bir yedeği S3'ten alıp veritabanına geri yükler. Konteynerin içinde
# çalışır; dışarıdan scripts/restore.sh çağırır.
#
#   restore.sh                 en yeni yedek
#   restore.sh <anahtar>       belirli bir yedek (tam S3 anahtarı)
set -eu

: "${BACKUP_BUCKET:?BACKUP_BUCKET gerekli}"
PREFIX="${BACKUP_PREFIX:-muamma}"

key="${1:-}"
if [ -z "$key" ]; then
    key=$(aws s3api list-objects-v2 \
        --bucket "$BACKUP_BUCKET" \
        --prefix "${PREFIX}/" \
        --query 'sort_by(Contents,&LastModified)[-1].Key' \
        --output text)
fi

if [ -z "$key" ] || [ "$key" = "None" ]; then
    echo "Yedek bulunamadı: s3://${BACKUP_BUCKET}/${PREFIX}/" >&2
    exit 1
fi

echo "Geri yüklenen yedek: s3://${BACKUP_BUCKET}/${key}"
echo "Hedef: ${PGUSER}@${PGHOST}/${PGDATABASE}"

# Döküm --clean --if-exists ile alındı: mevcut tabloları kendisi düşürüp
# yeniden kurar. ON_ERROR_STOP, yarı yüklenmiş bir veritabanıyla
# kalmamak için.
aws s3 cp "s3://${BACKUP_BUCKET}/${key}" - |
    gunzip |
    psql --quiet --no-psqlrc -v ON_ERROR_STOP=1

echo "Geri yükleme bitti."
