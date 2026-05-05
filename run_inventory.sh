#!/usr/bin/env bash
# Launch the asset-inventory feature locally:
#   inv-api        :8200   (FastAPI, SQLite stub)
#   inv-web        :3200   (Vite dev server)
#
# Platform services (registry/bootstrap/shell) are NOT started here —
# run ./run_platform.sh in another terminal first when working in shell.
#
# Usage:
#   ./run_inventory.sh                     # launch + bootstrap deps if missing
#   ./run_inventory.sh --no-bootstrap      # skip pip/npm install
#   ./run_inventory.sh --skip inv-web      # api only
#
# Logs: ./logs/{inv-api,inv-web}.log

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

SVC_NAMES=(inv-api inv-web)
declare -A SVC_DIR SVC_CMD SVC_HEALTH SVC_HEALTH_TIMEOUT SVC_BOOTSTRAP SVC_ENV_FROM_EXAMPLE

SVC_DIR[inv-api]="$ROOT/feature-asset-inventory-backend"
SVC_CMD[inv-api]='AUTH_MODE=mock APP_ENVIRONMENT=local .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8200'
SVC_HEALTH[inv-api]="http://localhost:8200/api/inventory/it/health"
SVC_HEALTH_TIMEOUT[inv-api]=30
SVC_BOOTSTRAP[inv-api]="python"

SVC_DIR[inv-web]="$ROOT/feature-asset-inventory-frontend"
SVC_CMD[inv-web]='npm run dev'
SVC_HEALTH[inv-web]="http://localhost:3200/"
SVC_HEALTH_TIMEOUT[inv-web]=60
SVC_BOOTSTRAP[inv-web]="node"

PORTS=(8200 3200)

source "$ROOT/scripts/_run_lib.sh"
parse_common_args "$@"
clear_ports "${PORTS[@]}"
launch_services
multiplex_logs
