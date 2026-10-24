#!/bin/sh
# Dump, upload to S3, delete the old ones. AWS credentials come from the
# instance IAM role, not from the environment.
set -eu

: "${BACKUP_BUCKET:?BACKUP_BUCKET is required}"
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

log "dumping: ${PGDATABASE:-?}"
# --clean --if-exists so a restore works over a non-empty database.
pg_dump --clean --if-exists --no-owner --no-privileges | gzip -9 >"$file"

size=$(wc -c <"$file" | tr -d ' ')
if [ "$size" -lt 1000 ]; then
    log "ERROR: dump size not plausible (${size} bytes), nothing uploaded"
    exit 1
fi

log "uploading: ${target} (${size} bytes)"
aws s3 cp "$file" "$target" --only-show-errors
log "uploaded"

cutoff=$(date -u -d "${KEEP_DAYS} days ago" +%s)
log "deleting backups older than ${KEEP_DAYS} days"

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
            log "deleted: ${key}"
        fi
    done

log "done"
