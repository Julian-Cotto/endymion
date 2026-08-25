#!/usr/bin/env bash
set -euo pipefail

BOOTSTRAP_URL="${BOOTSTRAP_URL:-http://localhost:8001/api/runtime/features}"
ORDERS_API="${ORDERS_API:-http://localhost:8100/api/orders/items}"
CATALOG_API="${CATALOG_API:-http://localhost:8200/api/catalog/items}"

check_contains() {
  local name="$1"
  local body="$2"
  local expected="$3"

  if echo "$body" | grep -q "$expected"; then
    echo "✅ $name"
  else
    echo "❌ $name"
    echo "$body"
    exit 1
  fi
}

check_not_contains() {
  local name="$1"
  local body="$2"
  local unexpected="$3"

  if echo "$body" | grep -q "$unexpected"; then
    echo "❌ $name"
    echo "$body"
    exit 1
  else
    echo "✅ $name"
  fi
}

check_status() {
  local name="$1"
  local expected="$2"
  local url="$3"
  local roles="$4"

  status="$(curl -s -o /tmp/e2e-response.txt -w "%{http_code}" \
    -H "X-Debug-Roles: ${roles}" \
    "$url")"

  if [[ "$status" == "$expected" ]]; then
    echo "✅ $name"
  else
    echo "❌ $name expected $expected got $status"
    cat /tmp/e2e-response.txt
    exit 1
  fi
}

echo "== Bootstrap filtering =="

both="$(curl -s -H "X-Debug-Roles: orders.view,catalog.view" "$BOOTSTRAP_URL")"
check_contains "orders visible with orders.view" "$both" '"featureKey":"orders"'
check_contains "catalog visible with catalog.view" "$both" '"featureKey":"catalog"'

orders_only="$(curl -s -H "X-Debug-Roles: orders.view" "$BOOTSTRAP_URL")"
check_contains "orders visible with orders.view only" "$orders_only" '"featureKey":"orders"'
check_not_contains "catalog hidden without catalog.view" "$orders_only" '"featureKey":"catalog"'

none="$(curl -s -H "X-Debug-Roles: other.view" "$BOOTSTRAP_URL")"
check_not_contains "orders hidden without permission" "$none" '"featureKey":"orders"'
check_not_contains "catalog hidden without permission" "$none" '"featureKey":"catalog"'

admin="$(curl -s -H "X-Debug-Roles: platform.admin" "$BOOTSTRAP_URL")"
check_contains "orders visible with platform.admin" "$admin" '"featureKey":"orders"'
check_contains "catalog visible with platform.admin" "$admin" '"featureKey":"catalog"'

echo
echo "== Backend enforcement =="

check_status "orders API allows orders.view" "200" "$ORDERS_API" "orders.view"
check_status "orders API denies catalog.view" "403" "$ORDERS_API" "catalog.view"
check_status "orders API allows platform.admin" "200" "$ORDERS_API" "platform.admin"

check_status "catalog API allows catalog.view" "200" "$CATALOG_API" "catalog.view"
check_status "catalog API denies orders.view" "403" "$CATALOG_API" "orders.view"
check_status "catalog API allows platform.admin" "200" "$CATALOG_API" "platform.admin"

echo
echo "✅ E2E local auth check passed"