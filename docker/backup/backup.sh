#!/bin/sh
# Bir yedek al, S3'e koy, eskileri sil.
#
# S3 erişimi sunucunun IAM rolünden gelir: aws-cli kimlik bilgisini örnek
# meta verisinden (169.254.169.254) alır. Ortam değişkeninde anahtar yok,
# dolayısıyla diske de log'a da anahtar düşmez.
set -eu

: "${BACKUP_BUCKET:?BACKUP_BUCKET gerekli}"
PREFIX="${BACKUP_PREFIX:-muamma}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-30}"

stamp=$(date -u +%Y%m%dT%H%M%SZ)
name="muamma-${stamp}.sql.gz"
target="s3://${BACKUP_BUCKET}/${PREFIX}/${name}"
file="/tmp/${name}"

log() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"
}

cleanup() {
    rm -f "$file"
}
trap cleanup EXIT

log "yedek alınıyor: ${PGDATABASE:-?}"
# --clean --if-exists: geri yükleme boş olmayan bir veritabanının üstüne de
# çalışsın. Sahiplik ve yetkiler taşınmaz; hedefteki rol ne ise o kalır.
pg_dump --clean --if-exists --no-owner --no-privileges | gzip -9 >"$file"

size=$(wc -c <"$file" | tr -d ' ')
if [ "$size" -lt 1000 ]; then
    log "HATA: dökümün boyutu inandırıcı değil (${size} bayt), yükleme yapılmadı"
    exit 1
fi

log "yükleniyor: ${target} (${size} bayt)"
aws s3 cp "$file" "$target" --only-show-errors
log "yüklendi"

cutoff=$(date -u -d "${KEEP_DAYS} days ago" +%s)
log "${KEEP_DAYS} günden eski yedekler siliniyor"

aws s3api list-objects-v2 \
    --bucket "$BACKUP_BUCKET" \
    --prefix "${PREFIX}/" \
    --query 'Contents[].[Key,LastModified]' \
    --output text |
    while read -r key modified; do
        [ -n "${key:-}" ] || continue
        [ "$key" != "None" ] || continue
        age=$(date -u -d "$modified" +%s 2>/dev/null) || continue
        if [ "$age" -lt "$cutoff" ]; then
            aws s3api delete-object --bucket "$BACKUP_BUCKET" --key "$key" >/dev/null
            log "silindi: ${key}"
        fi
    done

log "bitti"
