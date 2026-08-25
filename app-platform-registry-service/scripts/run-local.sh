#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Ensure .env exists
if [ ! -f ".env" ]; then
  cp .env.example .env
fi

echo "[registry] Starting Postgres container..."
docker compose up -d db

echo "[registry] Waiting for Postgres..."
until docker compose exec -T db pg_isready -U registry -d portal_registry >/dev/null 2>&1; do
  sleep 1
done

echo "[registry] Running migrations..."
PYTHONPATH="$ROOT_DIR" alembic upgrade head

# echo "[registry] Seeding local data..."
# PYTHONPATH="$ROOT_DIR" python scripts/seed_local.py

echo "[registry] Starting API on http://localhost:8010"
PYTHONPATH="$ROOT_DIR" uvicorn app.main:app --reload --host 0.0.0.0 --port 8010