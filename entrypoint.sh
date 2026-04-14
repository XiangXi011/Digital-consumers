#!/bin/sh
set -e

echo "Waiting for database..."
while ! python -c "
import socket, sys
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    s.connect(('postgres', 5432))
    s.close()
    sys.exit(0)
except:
    sys.exit(1)
" 2>/dev/null; do
  sleep 1
done
echo "Database is reachable."

echo "Running Alembic migrations..."
alembic upgrade head
echo "Migrations complete."

echo "Starting: $@"
exec "$@"
