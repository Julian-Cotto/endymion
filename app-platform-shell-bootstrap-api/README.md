# Shell Bootstrap API

FastAPI service that composes **shell runtime** and **bootstrap** payloads: given the current user, environment, registry manifests, and feature flags, it returns which features the shell may load and with what URLs and auth metadata.

**Detailed behavior:** see [`doc/`](doc/) (especially [`doc/local-runtime-modes.md`](doc/local-runtime-modes.md), [`doc/auth-and-permissions.md`](doc/auth-and-permissions.md), and [`doc/Shell-Bootstrap-API-Engineering-Development-Guide.md`](doc/Shell-Bootstrap-API-Engineering-Development-Guide.md)).

---

## What it does

- **`BOOTSTRAP_MODE=registry`**: loads manifests from **`REGISTRY_BASE_URL`** (`GET …/api/runtime/features?environment={APP_ENV}`). Optional **`REGISTRY_READ_TOKEN`** sets `Authorization: Bearer` on that HTTP call.
- **`BOOTSTRAP_MODE=mock`**: builds from **`MOCK_FEATURES_JSON`** (env → `Settings.mock_features_json`).
- **Flags**: if **`APP_CONFIGURATION_ENDPOINT`** is unset, a **noop** resolver returns **all requested flags as `true`**. If set, **`AppConfigFlagService`** is used (see `app/services/appconfig_service.py` for current evaluation behavior).
- **Auth**: **`AUTH_MODE=local`** (HS256 + `LOCAL_JWT_SECRET`) or **`AUTH_MODE=entra`** (RS256 + JWKS). **`REQUIRE_AUTH`** and mock/local shortcuts control whether a JWT is required (`app/api/auth_runtime.py`).

---

## HTTP API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/shell/bootstrap` | Shell startup payload |
| GET | `/api/runtime/features` | Same visibility rules, runtime-oriented schema |
| GET | `/api/shell/health` | Liveness JSON |
| GET | `/api/shell/health/dependencies` | Mode / registry / App Config wiring |

Default Uvicorn port in examples below is **`8765`**; use any port and keep shell `VITE_*` URLs in sync.

---

## Quick start

### 1. Virtualenv and dependencies

Use a normal CPython (see [`scripts/bootstrap-venv.sh`](scripts/bootstrap-venv.sh) if your default `python3` is a tiny shim):

```bash
./scripts/bootstrap-venv.sh
# or: python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
source .venv/bin/activate
```

### 2. Environment

```bash
cp .env.example .env
# Edit .env — at minimum APP_ENV, BOOTSTRAP_MODE, REGISTRY_BASE_URL (for registry), AUTH_*, REQUIRE_AUTH
```

### 3. Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8765
```

### 4. Health

```bash
curl -s http://localhost:8765/api/shell/health | jq
```

### 5. Runtime (needs a JWT when `REQUIRE_AUTH=true` and no mock shortcut applies)

```bash
curl -s http://localhost:8765/api/runtime/features \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 6. Tests

```bash
python -m pytest -q
```

`pyproject.toml` sets **`pythonpath = ["."]`** so `import app` works without an editable install.

---

## Example local ports

These are **conventions**, not enforced by this repo:

| Service | Example port |
|---------|----------------|
| Registry | `8010` |
| This API | `8765` |
| Shell (Vite) | `3000` |
| Orders / Catalog UIs | `3200` / `3300` |
| Orders / Catalog APIs | `8100` / `8200` |

---

## Shell (Vite) URLs

Point the shell at **this** service (adjust host/port):

```env
VITE_RUNTIME_SOURCE_MODE=registry
VITE_REGISTRY_RUNTIME_URL=http://localhost:8765/api/runtime/features
VITE_BOOTSTRAP_URL=http://localhost:8765/api/shell/bootstrap
```

The shell should use the **bootstrap** URL for startup payloads and the **runtime** URL for the feature list endpoint exposed by this BFF—not the registry origin directly, unless you intentionally bypass this API.

---

## Environment variables (summary)

Copy from [`.env.example`](.env.example). Names map to `Settings` in [`app/core/config.py`](app/core/config.py).

| Area | Variables |
|------|-----------|
| Core | `APP_ENV`, `BOOTSTRAP_MODE` |
| Registry | `REGISTRY_BASE_URL`, `REGISTRY_READ_TOKEN` (optional) |
| App Configuration | `APP_CONFIGURATION_ENDPOINT`, `APP_CONFIGURATION_LABEL` |
| Auth | `AUTH_MODE` (`local` \| `entra`), `REQUIRE_AUTH`, `LOCAL_JWT_SECRET`, `LOCAL_JWT_ALGORITHM`, `AUTH_ISSUER`, `AUTH_AUDIENCE`, `AUTH_ALLOWED_ALGS_CSV`, `AUTH_JWKS_URL`, `AUTH_*_CLAIM` |
| Claims → roles | `GROUP_ROLE_MAP_JSON`, `SCOPE_ROLE_MAP_JSON`, `WID_ROLE_MAP_JSON`, `DIRECT_ROLE_ALLOW_LIST_CSV` |
| Roles → permissions | `ROLE_PERMISSION_MAP_JSON`, `DEFAULT_PERMISSIONS_CSV` |
| Mock data | `MOCK_FEATURES_JSON`, `INCLUDE_FLAG_PREFIXES_CSV` |
| CORS / cache | `CORS_ALLOW_ORIGINS_CSV`, `CACHE_BACKEND`, `CACHE_TTL_SECONDS`, `REDIS_URL` |

There are **no** `ENTRA_*` or `APP_ENVIRONMENT` variables in the current `Settings` model—use **`APP_ENV`** and the **`AUTH_*`** / **`AUTH_MODE`** fields above.

---

## Runtime flow (registry mode)

```text
Shell
  → GET /api/runtime/features (or /api/shell/bootstrap)
Bootstrap API
  → GET {REGISTRY_BASE_URL}/api/runtime/features?environment={APP_ENV}
Registry
  → manifests
Bootstrap API
  → JWT + claims → roles → permissions
  → resolve flags
  → filter by requiredPermissions + requiredFlags
  → JSON to shell
```

---

## Auth and visibility (short)

- **User resolution**: `runtime_authenticated_user` (`app/api/auth_runtime.py`).
- **JWT**: `decode_bearer_token` (`app/core/jwt_auth.py`) — HS256 local vs RS256 JWKS for Entra.
- **Roles from claims**: `roles_from_claims` (`app/services/claim_role_mapper.py`).
- **Permissions**: `permissions_from_user` (`app/services/permission_mapper.py`).
- **Visibility**: every `authorization.requiredPermissions` satisfied **and** every `authorization.requiredFlags` key **true** in the flag map.

Full rules: [`doc/auth-and-permissions.md`](doc/auth-and-permissions.md). Entra vs local JWT: [`doc/entra-jwks-auth.md`](doc/entra-jwks-auth.md).

---

## Registry vs this API

| | Registry service | Shell Bootstrap API |
|---|------------------|----------------------|
| **Role** | Source of active manifests per environment | Auth, flags, permissions, filtering |
| **Caller** | Often internal / CI | **Shell** (and tools) |

Smoke the registry directly:

```bash
curl -s "http://localhost:8010/api/runtime/features?environment=local" | jq
```

---

## Local end-to-end checklist

1. Start **registry** (e.g. port `8010`).
2. Start **shell-bootstrap-api** with `REGISTRY_BASE_URL` and matching `APP_ENV`.
3. Start **feature** frontends/backends as needed by manifests or `MOCK_FEATURES_JSON`.
4. Start **shell** with `VITE_*` URLs pointing at this API.

Platform-oriented checklist: [`doc/platform-runtime-readiness-checklist.md`](doc/platform-runtime-readiness-checklist.md).

---

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| **`No module named pytest`** / wrong interpreter | Recreate `.venv` with real CPython: `./scripts/bootstrap-venv.sh`. Use **`python -m pytest`**. |
| **`No module named app`** | Run pytest from repo root; `pythonpath` is set in `pyproject.toml`. |
| **401** | `REQUIRE_AUTH`, `BOOTSTRAP_MODE`, `AUTH_MODE`, bearer token, clock/skew for JWT. |
| **Feature in registry but not in API response** | Permissions, `requiredFlags`, `APP_ENV`, flag resolver output — compare registry JSON vs API JSON. |
| **Wrong URLs in payload** | Registry manifest or `MOCK_FEATURES_JSON` content, not this service’s routing. |

---

## Production direction

- **`AUTH_MODE=entra`**, JWKS URL, **`REQUIRE_AUTH=true`**, no local mock shortcuts.
- Managed identity / secrets for registry and Azure App Configuration as appropriate.
- Structured logging and observability (see `app/core/logging.py`).

---

## Developer contract

```text
Shell → Shell Bootstrap API → filtered features + flags + user context
Shell → feature frontend → feature backend (authoritative for business auth)
```

Feature backends should **not** depend on this API for authorization decisions; they enforce their own rules.

---

## Summary

```text
registry manifests
+ APP_ENV
+ user (JWT or mock)
+ permissions + flags
= /api/shell/bootstrap and /api/runtime/features responses
```
