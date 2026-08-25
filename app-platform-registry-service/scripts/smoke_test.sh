#!/usr/bin/env bash
set -euo pipefail

: "${REGISTRY_BASE_URL:?REGISTRY_BASE_URL is required}"

curl -fsS "${REGISTRY_BASE_URL}/health"
