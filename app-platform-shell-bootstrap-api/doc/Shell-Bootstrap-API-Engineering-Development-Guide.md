# Shell Bootstrap API — engineering & development guide

## 1. Purpose

The Shell Bootstrap API is a **FastAPI** backend that aggregates data the browser shell needs at startup and for runtime feature lists:

- **Registry mode**: active feature manifests from **`REGISTRY_BASE_URL`** (`GET …/api/runtime/features?environment=…`).
- **Flags**: either a **noop** “all true” resolver, or **Azure App Configuration** wiring when `APP_CONFIGURATION_ENDPOINT` is set (implementation may still short-circuit to all-true for local dev — see `app/services/appconfig_service.py`).
- **Auth**: JWT validation for **`AUTH_MODE=local`** (HS256) or **`AUTH_MODE=entra`** (RS256 + JWKS), then **claims → roles → permissions** for visibility filtering.

It returns **frontend-safe** JSON for:

- `GET /api/shell/bootstrap`
- `GET /api/runtime/features`

This service does **not** replace:

- the registry as source of truth for **which** features are active and their manifests  
- Azure App Configuration as the long-term store for flag state (when fully wired)  
- feature backends for **business** authorization

---

## 2. Responsibilities

### This service owns

- Aggregating registry manifests + resolved flags + user permissions
- **Visibility rules** (required permissions + required flags)
- Response schemas (`app/schemas/*`)
- Short-lived caching (`app/services/cache.py`)

### Registry owns

- Active manifests, routes, frontend entry URLs, backend base URLs
- `authorization.requiredPermissions` / `requiredFlags` on each feature

### Feature services own

- API authorization and behavioral flags at runtime in the feature domain

---

## 3. High-level architecture

```text
Browser shell
    |  GET /api/shell/bootstrap  (or /api/runtime/features)
    v
shell-bootstrap-api
    |-- RegistryClient  -> REGISTRY_BASE_URL (optional bearer REGISTRY_READ_TOKEN)
    |-- Flag service    -> NoopFlagService | AppConfigFlagService
    |-- PermissionService -> roles_from_claims + role_permission_map
    v
BootstrapService -> filtered features + flags + user + permissions
```

### Visibility rule

A registry-backed feature is visible only if:

1. It appears in the registry response for `APP_ENV`.
2. The user has every **`authorization.requiredPermissions`** (via `ROLE_PERMISSION_MAP_JSON` / admin wildcard).
3. Every **`authorization.requiredFlags`** is **true** in the flag resolver output.

---

## 4. Runtime flow (registry + auth)

1. Shell calls **`GET /api/shell/bootstrap`** or **`GET /api/runtime/features`**.
2. **`runtime_authenticated_user`** resolves the user (mock shortcuts, or JWT via **`decode_bearer_token`**).
3. **`BootstrapService`** loads manifests from **`RegistryClient`** when `BOOTSTRAP_MODE=registry`.
4. Required flag keys are collected from manifests; **`flag_service.resolve_flags`** returns a `dict[str, bool]`.
5. **`PermissionService.get_permissions`** maps JWT roles to permission strings.
6. Features are filtered; response is built (`BootstrapResponse` / `RuntimeFeaturesResponse`).

---

## 5. HTTP API (current)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/shell/bootstrap` | Shell startup payload |
| GET | `/api/runtime/features` | Runtime list (same filtering, different schema) |
| GET | `/api/shell/health` | `{ "status": "ok", "generatedAtUtc": … }` |
| GET | `/api/shell/health/dependencies` | Mode / registry / App Config wiring summary |

There is **no** top-level `/health` route in code today — use **`/api/shell/health`**.

### Sample bootstrap shape (illustrative)

Field names follow **`BootstrapResponse`** in `app/schemas/bootstrap.py` (camelCase for JSON). `metadata` uses `source`, `generatedBy`, `generatedAtUtc` (not the older `degraded` / `cacheBackend` only shape):

```json
{
  "environment": "local",
  "user": {
    "id": "user-123",
    "displayName": "Example User",
    "email": "user@example.com"
  },
  "permissions": ["orders.view", "catalog.view"],
  "flags": {
    "orders.enabled": true,
    "shell.debug": true
  },
  "features": [
    {
      "featureKey": "orders",
      "displayName": "Orders",
      "route": "/orders",
      "version": "local",
      "frontend": { "enabled": true, "entryUrl": "https://example/entry.js" },
      "backend": { "enabled": true, "apiBaseUrl": "https://orders-api.example" },
      "authorization": {
        "requiredPermissions": ["orders.view"],
        "requiredFlags": ["orders.enabled"]
      },
      "auth": { "mode": "mock", "required": false }
    }
  ],
  "metadata": {
    "source": "bootstrap-service-registry",
    "generatedBy": "shell-bootstrap-api",
    "generatedAtUtc": "2026-04-27T12:00:00Z"
  }
}
```

---

## 6. Repository layout (current)

```text
shell-bootstrap-api/
├── app/
│   ├── api/
│   │   ├── routes_bootstrap.py
│   │   └── auth_runtime.py
│   ├── core/
│   │   ├── auth.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── jwt_auth.py
│   │   └── logging.py
│   ├── schemas/
│   │   ├── bootstrap.py
│   │   ├── registry_manifest.py
│   │   ├── runtime_features.py
│   │   └── …
│   ├── services/
│   │   ├── appconfig_service.py
│   │   ├── bootstrap_service.py
│   │   ├── cache.py
│   │   ├── claim_role_mapper.py
│   │   ├── permission_mapper.py
│   │   ├── permissions.py
│   │   ├── registry_client.py
│   │   └── registry_manifest_mapper.py
│   └── main.py
├── doc/
├── infra/
├── tests/
├── scripts/
│   └── bootstrap-venv.sh
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
└── .env.example
```

---

## 7. Configuration (environment variables)

Pydantic loads from **`.env`**; names are typically **UPPER_SNAKE** matching fields (see `Settings` in `app/core/config.py` and `.env.example`).

| Variable | Purpose |
|----------|---------|
| `APP_ENV` | Environment string sent to the registry client |
| `BOOTSTRAP_MODE` | `mock` or `registry` |
| `REGISTRY_BASE_URL` | Registry base URL (required when mode is `registry`) |
| `REGISTRY_READ_TOKEN` | Optional bearer token for registry HTTP |
| `APP_CONFIGURATION_ENDPOINT` | If set, construct `AppConfigFlagService`; else `NoopFlagService` |
| `APP_CONFIGURATION_LABEL` | App Configuration label |
| `AUTH_MODE` | `local` or `entra` |
| `REQUIRE_AUTH` | If `false`, mock user without JWT |
| `LOCAL_JWT_SECRET`, `LOCAL_JWT_ALGORITHM` | Local HS256 signing |
| `AUTH_ISSUER`, `AUTH_AUDIENCE`, `AUTH_ALLOWED_ALGS_CSV`, `AUTH_JWKS_URL` | JWT validation (see `doc/entra-jwks-auth.md`) |
| `AUTH_*_CLAIM` | Claim names for sub, name, email, roles, groups, scp, wids |
| `GROUP_ROLE_MAP_JSON`, `SCOPE_ROLE_MAP_JSON`, `WID_ROLE_MAP_JSON` | Claim → role |
| `DIRECT_ROLE_ALLOW_LIST_CSV` | Allow-list for direct `roles` claim values |
| `ROLE_PERMISSION_MAP_JSON`, `DEFAULT_PERMISSIONS_CSV` | Role → permission |
| `INCLUDE_FLAG_PREFIXES_CSV` | Prefix filter for flags exposed in payloads (mock + filtering helpers) |
| `MOCK_FEATURES_JSON` | JSON list for mock mode features |
| `CORS_ALLOW_ORIGINS_CSV` | Allowed CORS origins (comma-separated) |
| `CACHE_BACKEND` | `memory` or `redis` |
| `CACHE_TTL_SECONDS` | Cache TTL |
| `REDIS_URL` | Required when `CACHE_BACKEND=redis` |

---

## 8. Authentication & permissions (summary)

- **`doc/auth-and-permissions.md`** — full matrix (`REQUIRE_AUTH`, mock shortcuts, claims, permissions).
- **`doc/entra-jwks-auth.md`** — `AUTH_MODE=local` vs `entra` and JWKS.

---

## 9. Feature flags strategy

- **Noop** path: all requested flag keys resolve to **`true`** (fast local dev).
- **App Config path**: when endpoint is set, service is constructed with Azure credentials; extend `resolve_flags` when you need real feature evaluation instead of the current dev override.

Prefix filtering for which keys appear in responses is driven by **`INCLUDE_FLAG_PREFIXES_CSV`** (see `bootstrap_service` mock flag builders and registry flag filtering).

---

## 10. Caching

- **Backend**: in-memory by default, optional **Redis** (`CACHE_BACKEND=redis`, `REDIS_URL`).
- **Keys** (registry path): `bootstrap:v2:…` and `runtime:v2:…` (see `bootstrap_service.py`).
- TTL for combined user/env cache entries is clamped in code (see `get_or_set`).

---

## 11. Infrastructure boundary

This repo can hold **service-specific** Terraform under `infra/` (Container App, roles, etc.). Shared platform (ACR, ACA environment, shared App Configuration store) usually lives elsewhere — adjust to your org’s split.

---

## 12. CI/CD (reference)

- **CI**: install deps, **ruff** / **pytest** (see `requirements-dev.txt`, `.github/workflows/`).
- **CD**: build image, push, deploy revision (implementation in `cd.yml`).

---

## 13. Local development

### Prerequisites

- **Python 3.11+** (project targets 3.11 in `pyproject.toml` ruff target; Docker image uses 3.12-slim).
- **Redis** only if `CACHE_BACKEND=redis`.

### venv

Use a **real** CPython (not a mis-created venv pointing at an IDE AppImage):

```bash
./scripts/bootstrap-venv.sh
# or: python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
```

### Run

```bash
source .venv/bin/activate
cp .env.example .env   # then edit
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Tests

```bash
python -m pytest -q
```

---

## 14. Docker note

`Dockerfile` copies **`app/`** only today; if you add non-package assets, extend **`COPY`** accordingly before production builds.

---

## 15. Related docs

- `doc/local-runtime-modes.md` — mock vs registry behavior  
- `doc/auth-and-permissions.md` — JWT + permissions + visibility  
- `doc/entra-jwks-auth.md` — local HS256 vs Entra JWKS  
- `doc/platform-runtime-readiness-checklist.md` — shell + registry integration  
