#!/usr/bin/env bash
# Launch the continued-education feature locally:
#   ce-api         :8300   (FastAPI, SQLite stub)
#   ce-web         :3300   (Vite dev server)
#
# Platform services (registry/bootstrap/shell) are NOT started here —
# run ./run_platform.sh in another terminal first when working in shell.
#
# Usage:
#   ./run_continued_ed.sh                  # launch + bootstrap deps if missing
#   ./run_continued_ed.sh --no-bootstrap   # skip pip/npm install
#   ./run_continued_ed.sh --skip ce-web    # api only
#
# Logs: ./logs/{ce-api,ce-web}.log

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

SVC_NAMES=(ce-api ce-web)
declare -A SVC_DIR SVC_CMD SVC_HEALTH SVC_HEALTH_TIMEOUT SVC_BOOTSTRAP SVC_ENV_FROM_EXAMPLE

SVC_DIR[ce-api]="$ROOT/feature-continued-education-backend"
SVC_CMD[ce-api]='AUTH_MODE=mock APP_ENVIRONMENT=local .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8300'
SVC_HEALTH[ce-api]="http://localhost:8300/api/education/continued-ed/health"
SVC_HEALTH_TIMEOUT[ce-api]=30
SVC_BOOTSTRAP[ce-api]="python"

SVC_DIR[ce-web]="$ROOT/feature-continued-education-frontend"
SVC_CMD[ce-web]='npm run dev'
SVC_HEALTH[ce-web]="http://localhost:3300/"
SVC_HEALTH_TIMEOUT[ce-web]=60
SVC_BOOTSTRAP[ce-web]="node"

PORTS=(8300 3300)

source "$ROOT/scripts/_run_lib.sh"
parse_common_args "$@"
clear_ports "${PORTS[@]}"
launch_services
multiplex_logs
