#!/bin/sh
set -e

export PYTHONPATH=/app

echo "Waiting for database..."
for i in $(seq 1 60); do
  if python -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('postgres',5432)); s.close()" 2>/dev/null; then
    echo "Database is reachable."
    break
  fi
  sleep 1
done

echo "Running Alembic migrations..."
alembic upgrade head
echo "Migrations complete."

echo "Starting: $@"
exec "$@"
