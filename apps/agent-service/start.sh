#!/bin/bash
# start.sh — Agent Service Entrypoint
# Run Alembic migrations to head, then start uvicorn.
# This script is used by the API container only. The Celery worker
# container overrides CMD in docker-compose.yml to launch celery worker.
set -e

echo "[start.sh] Running Alembic database migrations..."
alembic upgrade head
echo "[start.sh] Migrations complete. Starting uvicorn..."

exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8002
