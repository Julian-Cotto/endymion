#!/usr/bin/env bash
# Launch ALL services (platform + inventory feature) in one terminal.
# Order:
#   1. registry            :8010
#   2. shell-bootstrap-api :8000
#   3. shell               :3000
#   4. inv-api             :8200
#   5. inv-web             :3200
#
# For development you usually want two terminals instead:
#   T1: ./run_platform.sh
#   T2: ./run_inventory.sh
# That way the inv-api/web restarts don't tear down the shell.
#
# Usage:
#   ./run_all.sh                       # full launch + bootstrap deps
#   ./run_all.sh --no-bootstrap        # skip pip/npm install
#   ./run_all.sh --skip shell,inv-web  # omit specific services
#
# Logs: ./logs/<name>.log

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

SVC_NAMES=(registry bootstrap shell inv-api inv-web)
declare -A SVC_DIR SVC_CMD SVC_HEALTH SVC_HEALTH_TIMEOUT SVC_BOOTSTRAP SVC_ENV_FROM_EXAMPLE

SVC_DIR[registry]="$ROOT/app-platform-registry-service"
SVC_CMD[registry]='PYTHONPATH=. .venv/bin/alembic upgrade head 2>&1; PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8010'
SVC_HEALTH[registry]="http://localhost:8010/health"
SVC_HEALTH_TIMEOUT[registry]=60
SVC_BOOTSTRAP[registry]="python"
SVC_ENV_FROM_EXAMPLE[registry]=1

SVC_DIR[bootstrap]="$ROOT/app-platform-shell-bootstrap-api"
SVC_CMD[bootstrap]='.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000'
SVC_HEALTH[bootstrap]="http://localhost:8000/api/shell/health"
SVC_HEALTH_TIMEOUT[bootstrap]=60
SVC_BOOTSTRAP[bootstrap]="python"
SVC_ENV_FROM_EXAMPLE[bootstrap]=1

SVC_DIR[shell]="$ROOT/app-platform-shell"
SVC_CMD[shell]='npm run dev'
SVC_HEALTH[shell]="http://localhost:3000/"
SVC_HEALTH_TIMEOUT[shell]=90
SVC_BOOTSTRAP[shell]="node"
SVC_ENV_FROM_EXAMPLE[shell]=1

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

PORTS=(8010 8000 3000 8200 3200)

source "$ROOT/scripts/_run_lib.sh"
parse_common_args "$@"
clear_ports "${PORTS[@]}"
launch_services
multiplex_logs
