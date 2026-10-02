#!/bin/sh
# Migrationlar uygulamadan önce çalışır: yeni sürüm açılırken şema da
# güncellenmiş olur, elle bir adım kalmaz.
set -e

echo "Migrationlar uygulanıyor..."
flask db upgrade

exec "$@"
