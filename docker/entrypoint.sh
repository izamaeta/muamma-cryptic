#!/bin/sh
# Apply migrations, then hand over to the command.
set -e

echo "Applying migrations..."
flask db upgrade

exec "$@"
