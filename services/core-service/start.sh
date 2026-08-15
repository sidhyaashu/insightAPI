#!/bin/bash
# start.sh — Core Service Entrypoint
# Run Alembic migrations to head, then start uvicorn.
set -e

echo "[start.sh] Running Alembic database migrations..."
alembic upgrade head
echo "[start.sh] Migrations complete. Starting uvicorn..."

exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
