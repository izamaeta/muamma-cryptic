#!/bin/sh
# Restore a backup from S3. Runs inside the container; scripts/restore.sh
# is the wrapper.
#
#   restore.sh                 newest backup
#   restore.sh <key>           a specific backup (full S3 key)
set -eu

: "${BACKUP_BUCKET:?BACKUP_BUCKET is required}"
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
    echo "No backup found: s3://${BACKUP_BUCKET}/${PREFIX}/" >&2
    exit 1
fi

echo "Restoring: s3://${BACKUP_BUCKET}/${key}"
echo "Target: ${PGUSER}@${PGHOST}/${PGDATABASE}"

# The dump drops and recreates; ON_ERROR_STOP avoids a half-loaded database.
aws s3 cp "s3://${BACKUP_BUCKET}/${key}" - |
    gunzip |
    psql --quiet --no-psqlrc -v ON_ERROR_STOP=1

echo "Restore finished."
