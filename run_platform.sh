#!/usr/bin/env bash
# Launch platform services only:
#   registry-service          :8010
#   shell-bootstrap-api       :8000
#   shell                     :3000
#
# Usage:
#   ./run_platform.sh                      # full launch + bootstrap deps if missing
#   ./run_platform.sh --no-bootstrap       # skip pip/npm install
#   ./run_platform.sh --skip shell         # omit services
#
# Logs: ./logs/{registry,bootstrap,shell}.log

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

SVC_NAMES=(registry bootstrap shell)
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

PORTS=(8010 8000 3000)

source "$ROOT/scripts/_run_lib.sh"
parse_common_args "$@"
clear_ports "${PORTS[@]}"
launch_services
multiplex_logs
