#!/usr/bin/env bash
# Generate the Alembic baseline migration against a throwaway Postgres.
# Spins up an empty DB, autogenerates the baseline from the models, tears it down.
# The generated migration is left in alembic/versions/ for you to review.
#
# Usage:  cd backend && ./scripts/gen-baseline.sh
set -euo pipefail

CONTAINER=labz-baseline-scratch
PORT=5433
DB=scratch
USER=scratch
PASS=scratch

cleanup() { docker rm -f "$CONTAINER" >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo ">> starting throwaway Postgres ($CONTAINER on :$PORT)"
docker run -d --name "$CONTAINER" \
  -e POSTGRES_DB="$DB" -e POSTGRES_USER="$USER" -e POSTGRES_PASSWORD="$PASS" \
  -p "$PORT:5432" postgres:16-alpine >/dev/null

echo ">> waiting for it to accept connections"
for i in $(seq 1 30); do
  if docker exec "$CONTAINER" pg_isready -U "$USER" -d "$DB" >/dev/null 2>&1; then break; fi
  sleep 1
done

export DATABASE_URL="postgresql://$USER:$PASS@localhost:$PORT/$DB"
echo ">> autogenerating baseline against empty DB"
alembic revision --autogenerate -m "baseline schema"

echo ""
echo ">> Done. Review the new file in alembic/versions/ before committing."
echo "   Check: all tables/columns, server_defaults, JSONB types, indexes, FKs."
