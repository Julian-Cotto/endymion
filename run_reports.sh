#!/usr/bin/env bash
# Launch the Reports Layering feature locally:
#   rl-api         :8500   (FastAPI, SQLite metadata DB + Snowflake reads)
#   rl-web         :3500   (Vite dev server)
#
# Zero external services required for a local run:
#   * Metadata/roles/snapshots live in a local SQLite file
#     (feature-reports-layering/backend/reports_layering.db), auto-migrated
#     on start.
#   * Snowflake has no creds locally, so the client runs in mock mode and the
#     snapshot pipeline synthesizes rows from each report's declared columns.
#
# Snapshots normally refresh on a schedule; locally, creating/refreshing a
# report snapshots it immediately. To batch-refresh all reports manually:
#   (cd feature-reports-layering && PYTHONPATH=backend:. \
#      backend/.venv/bin/python -c \
#      'from jobs.refresh_report_snapshots.main import main; main()')
#
# Platform services (registry/bootstrap/shell) are NOT started here —
# run ./run_platform.sh in another terminal first when working in shell.
#
# Usage:
#   ./run_reports.sh                  # launch + bootstrap deps if missing
#   ./run_reports.sh --no-bootstrap   # skip pip/npm install
#   ./run_reports.sh --skip rl-web    # api only
#
# Logs: ./logs/{rl-api,rl-web}.log

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

SVC_NAMES=(rl-api rl-web)
declare -A SVC_DIR SVC_CMD SVC_HEALTH SVC_HEALTH_TIMEOUT SVC_BOOTSTRAP SVC_ENV_FROM_EXAMPLE

SVC_DIR[rl-api]="$ROOT/feature-reports-layering/backend"
SVC_CMD[rl-api]='export APP_ENVIRONMENT=local AUTH_MODE=mock AUTH_DEBUG_HEADERS_ENABLED=true AUTH_DEFAULT_DEV_ROLES_RAW=reports-layering.view,reports-layering.create,reports-layering.edit,reports-layering.admin DATABASE_URL="sqlite:///$PWD/reports_layering.db"; [ -f ../.env ] && { set -a; . ../.env; set +a; }; .venv/bin/alembic upgrade head && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8500'
SVC_HEALTH[rl-api]="http://localhost:8500/api/reports/health"
SVC_HEALTH_TIMEOUT[rl-api]=40
SVC_BOOTSTRAP[rl-api]="python"

SVC_DIR[rl-web]="$ROOT/feature-reports-layering/frontend"
SVC_CMD[rl-web]='npm run dev'
SVC_HEALTH[rl-web]="http://localhost:3500/"
SVC_HEALTH_TIMEOUT[rl-web]=60
SVC_BOOTSTRAP[rl-web]="node"

PORTS=(8500 3500)

source "$ROOT/scripts/_run_lib.sh"
parse_common_args "$@"
clear_ports "${PORTS[@]}"
launch_services
multiplex_logs
