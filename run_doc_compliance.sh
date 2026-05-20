#!/usr/bin/env bash
# Launch the document-compliance feature locally:
#   dc-api         :8400   (FastAPI, Postgres on :5434 + Snowflake reads)
#   dc-web         :3400   (Vite dev server)
#
# Postgres must be running — start it with:
#   (cd document-compliance-backend && docker compose up -d --wait)
#
# Platform services (registry/bootstrap/shell) are NOT started here —
# run ./run_platform.sh in another terminal first when working in shell.
#
# Usage:
#   ./run_doc_compliance.sh                  # launch + bootstrap deps if missing
#   ./run_doc_compliance.sh --no-bootstrap   # skip pip/npm install
#   ./run_doc_compliance.sh --skip dc-web    # api only
#
# Logs: ./logs/{dc-api,dc-web}.log

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

SVC_NAMES=(dc-api dc-web)
declare -A SVC_DIR SVC_CMD SVC_HEALTH SVC_HEALTH_TIMEOUT SVC_BOOTSTRAP SVC_ENV_FROM_EXAMPLE

SVC_DIR[dc-api]="$ROOT/document-compliance-backend"
SVC_CMD[dc-api]='AUTH_MODE=mock APP_ENVIRONMENT=local .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8400'
SVC_HEALTH[dc-api]="http://localhost:8400/api/document-compliance/health"
SVC_HEALTH_TIMEOUT[dc-api]=30
SVC_BOOTSTRAP[dc-api]="python"

SVC_DIR[dc-web]="$ROOT/document-compliance-frontend"
SVC_CMD[dc-web]='npm run dev'
SVC_HEALTH[dc-web]="http://localhost:3400/"
SVC_HEALTH_TIMEOUT[dc-web]=60
SVC_BOOTSTRAP[dc-web]="node"

PORTS=(8400 3400)

source "$ROOT/scripts/_run_lib.sh"
parse_common_args "$@"
clear_ports "${PORTS[@]}"
launch_services
multiplex_logs
