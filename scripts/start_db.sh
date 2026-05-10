#!/usr/bin/env bash
# Start docker-compose postgres for registry-service.
# Standalone, idempotent. Used by run scripts via --with-db, or directly.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_DIR="$ROOT/app-platform-registry-service"

if [[ ! -f "$DB_DIR/docker-compose.yml" ]]; then
  echo "[start_db] missing $DB_DIR/docker-compose.yml" >&2
  exit 1
fi

echo "[start_db] docker compose up -d --wait ($DB_DIR)"
cd "$DB_DIR"
docker compose up -d --wait
echo "[start_db] postgres ready on localhost:5433"
