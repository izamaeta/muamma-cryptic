#!/usr/bin/env bash
# Restore from a backup. Run on the server, from the repository root.
#
#   scripts/restore.sh --list         list the backups
#   scripts/restore.sh                restore the newest backup
#   scripts/restore.sh muamma/muamma-20261001T031500Z.sql.gz
#   scripts/restore.sh --yes <key>    restore without asking
#
# The site is down for the duration: web is stopped, the database is
# replaced, web is started again.
set -euo pipefail

cd "$(dirname "$0")/.."

compose=(docker compose -f compose.prod.yaml --env-file .env.production)
run_in_backup=("${compose[@]}" run --rm --no-deps --entrypoint sh backup)

assume_yes=0
key=""
for argument in "$@"; do
    case "$argument" in
        --list)
            "${run_in_backup[@]}" -c 'aws s3 ls "s3://$BACKUP_BUCKET/$BACKUP_PREFIX/"'
            exit 0
            ;;
        --yes | -y)
            assume_yes=1
            ;;
        -*)
            echo "Unknown option: $argument" >&2
            exit 2
            ;;
        *)
            key="$argument"
            ;;
    esac
done

echo "Restoring: ${key:-newest backup}"
echo "This overwrites the current database."

if [ "$assume_yes" -eq 0 ]; then
    read -r -p "Continue? (type yes) " answer
    if [ "$answer" != "yes" ]; then
        echo "Cancelled."
        exit 1
    fi
fi

echo "--> stopping web"
"${compose[@]}" stop web

restore_status=0
echo "--> restoring"
"${run_in_backup[@]}" /usr/local/bin/restore.sh "$key" || restore_status=$?

echo "--> starting web"
"${compose[@]}" up -d web

if [ "$restore_status" -ne 0 ]; then
    echo "Restore failed (exit ${restore_status}); web was started again." >&2
    exit "$restore_status"
fi

echo "Done. Check the site."
