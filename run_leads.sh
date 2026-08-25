#!/usr/bin/env bash
# Launch the Lead Locator feature locally:
#   ll-api         :8600   (FastAPI, PostGIS on :5435)
#   ll-web         :3600   (Vite dev server)
#
# Unlike run_reports.sh, this feature has NO zero-service local mode: the
# scoring engine stores POI/tract geometry and does distance + containment
# queries, so PostGIS is mandatory. The DB is started automatically here
# (idempotent); skip it with --no-db if you already have it up.
#
#   (cd feature-lead-locator && docker compose up -d --wait)   # manual equivalent
#
# Platform services (registry/bootstrap/shell) are NOT started here —
# run ./run_platform.sh in another terminal first when working in shell.
#
# Usage:
#   ./run_leads.sh                  # launch + bootstrap deps if missing
#   ./run_leads.sh --no-bootstrap   # skip pip/npm install
#   ./run_leads.sh --no-db          # assume PostGIS already running
#   ./run_leads.sh --skip ll-web    # api only
#
# Logs: ./logs/{ll-api,ll-web}.log

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

# --no-db is specific to this script; strip it before the shared lib parses
# the rest (it would reject an unknown arg).
START_DB=1
ARGS=()
for a in "$@"; do
  if [[ "$a" == "--no-db" ]]; then START_DB=0; else ARGS+=("$a"); fi
done

SVC_NAMES=(ll-api ll-web)
declare -A SVC_DIR SVC_CMD SVC_HEALTH SVC_HEALTH_TIMEOUT SVC_BOOTSTRAP SVC_ENV_FROM_EXAMPLE

SVC_DIR[ll-api]="$ROOT/feature-lead-locator/backend"
# The backend reads .env itself (pydantic-settings env_file), so it is NOT
# sourced here — values like SERVICE_NAME contain spaces and would break a
# shell `.` source. These exports just override for a local run.
SVC_CMD[ll-api]='export APP_ENVIRONMENT=local AUTH_MODE=mock AUTH_DEBUG_HEADERS_ENABLED=true AUTH_DEFAULT_DEV_ROLES_RAW=lead-locator.view,lead-locator.create,lead-locator.admin DATABASE_URL="postgresql://leads:leads@localhost:5435/lead_locator"; .venv/bin/alembic upgrade head && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8600'
SVC_HEALTH[ll-api]="http://localhost:8600/api/leads/health"
SVC_HEALTH_TIMEOUT[ll-api]=40
SVC_BOOTSTRAP[ll-api]="python"
SVC_ENV_FROM_EXAMPLE[ll-api]=1

SVC_DIR[ll-web]="$ROOT/feature-lead-locator/frontend"
SVC_CMD[ll-web]='npm run dev'
SVC_HEALTH[ll-web]="http://localhost:3600/"
SVC_HEALTH_TIMEOUT[ll-web]=60
SVC_BOOTSTRAP[ll-web]="node"
SVC_ENV_FROM_EXAMPLE[ll-web]=1

PORTS=(8600 3600)

source "$ROOT/scripts/_run_lib.sh"
parse_common_args "${ARGS[@]+"${ARGS[@]}"}"

if [[ "$START_DB" == "1" ]]; then
  echo "[run_leads] starting PostGIS (localhost:5435)"
  (cd "$ROOT/feature-lead-locator" && docker compose up -d --wait)
fi

clear_ports "${PORTS[@]}"
launch_services
multiplex_logs
