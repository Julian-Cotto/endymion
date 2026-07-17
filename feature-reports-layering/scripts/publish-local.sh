#!/usr/bin/env bash

set -euo pipefail

FEATURE_KEY="reports-layering"

# Manifest scripts need jsonschema — prefer the backend venv interpreter,
# fall back to python3/python on PATH.
PYTHON="${PYTHON:-}"
if [ -z "$PYTHON" ]; then
  if [ -x "backend/.venv/bin/python" ]; then
    PYTHON="backend/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
  else
    PYTHON="python"
  fi
fi

# ---- PORT RESOLUTION (SAME AS run-local) ----
FRONTEND_PORT="${FRONTEND_PORT:-3500}"
BACKEND_PORT="${BACKEND_PORT:-8500}"

API_BASE_PATH="/api/reports"

REGISTRY_URL="${REGISTRY_URL:-http://localhost:8010}"
FEATURE_ENVIRONMENT="${FEATURE_ENVIRONMENT:-local}"

FEATURE_FRONTEND_ENTRY_URL="${FEATURE_FRONTEND_ENTRY_URL:-http://localhost:${FRONTEND_PORT}/src/bootstrap-entry.tsx}"
FEATURE_BACKEND_BASE_URL="${FEATURE_BACKEND_BASE_URL:-http://localhost:${BACKEND_PORT}${API_BASE_PATH}}"

export FEATURE_ENVIRONMENT
export FEATURE_FRONTEND_ENTRY_URL
export FEATURE_BACKEND_BASE_URL

echo "----------------------------------------"
echo "Publishing feature to local registry"
echo "Feature: $FEATURE_KEY"
echo "Environment: $FEATURE_ENVIRONMENT"
echo "Registry: $REGISTRY_URL"
echo "Frontend: $FEATURE_FRONTEND_ENTRY_URL"
echo "Backend:  $FEATURE_BACKEND_BASE_URL"
echo "----------------------------------------"

echo "→ Rendering manifest..."
"$PYTHON" scripts/render-manifest.py

echo "→ Validating manifest..."
"$PYTHON" scripts/validate-manifest.py

echo "→ Publishing manifest..."

curl -f -sS \
  -X POST "${REGISTRY_URL}/api/releases" \
  -H "Content-Type: application/json" \
  --data-binary @build/feature-manifest.resolved.json

echo "→ Activating feature..."
curl -i \
  -X POST "${REGISTRY_URL}/api/admin/features/${FEATURE_KEY}/versions/0.1.0/activate?environment=${FEATURE_ENVIRONMENT}"

echo ""
echo "✔ Publish complete"