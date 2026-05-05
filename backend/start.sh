#!/bin/sh
set -e
echo "Running database migrations..."
alembic upgrade head || echo "Migration failed or already up to date"
echo "Starting server..."
if [ "$RELOAD" = "true" ]; then
  exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-3001} --reload
else
  exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-3001}
fi
