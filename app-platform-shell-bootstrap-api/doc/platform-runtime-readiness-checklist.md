# Platform runtime readiness checklist

What to run and verify when wiring the **shell**, **shell-bootstrap-api**, and **registry** together locally.

---

## Data flow

```text
Shell
  -> shell-bootstrap-api (/api/runtime/features | /api/shell/bootstrap)
  -> (registry mode) REGISTRY_BASE_URL/api/runtime/features?environment=APP_ENV
  -> manifest list + JWT-derived permissions + flag resolution
  -> filtered features back to shell
```

---

## Typical local ports (examples)

| Component | Example port | Notes |
|-----------|--------------|--------|
| Shell (Vite) | 3000 | Browser app |
| shell-bootstrap-api | 8000 or 8001 | Match `VITE_*` URLs |
| Registry service | 8010 | Must match `REGISTRY_BASE_URL` |
| Feature UIs / APIs | varies | Defined in manifests / `MOCK_FEATURES_JSON` |

---

## Startup order

1. Feature services (optional for empty registry).
2. **Registry** — e.g. `http://localhost:8010`.
3. Smoke registry:

```bash
curl -s "http://localhost:8010/api/runtime/features?environment=local" | jq
```

4. **shell-bootstrap-api** with `BOOTSTRAP_MODE=registry`, `REGISTRY_BASE_URL`, and auth settings below.
5. Smoke bootstrap API (use a real JWT when `REQUIRE_AUTH=true`):

```bash
curl -s "http://localhost:8000/api/runtime/features" \
  -H "Authorization: Bearer <local-or-entra-jwt>" | jq
```

6. **Shell** with correct `VITE_BOOTSTRAP_URL` and `VITE_REGISTRY_RUNTIME_URL`.

---

## shell-bootstrap-api `.env` checklist

| Variable | Purpose |
|----------|---------|
| `APP_ENV` | Passed as `environment` to the registry client |
| `BOOTSTRAP_MODE` | `mock` or `registry` |
| `REGISTRY_BASE_URL` | Required for `registry` (e.g. `http://localhost:8010`) |
| `REGISTRY_READ_TOKEN` | Optional `Authorization: Bearer` for registry HTTP |
| `APP_CONFIGURATION_ENDPOINT` | If empty, `NoopFlagService` (all flags true). If set, `AppConfigFlagService` is constructed |
| `APP_CONFIGURATION_LABEL` | App Configuration label (passed into `AppConfigFlagService`) |
| `AUTH_MODE` | `local` or `entra` |
| `REQUIRE_AUTH` | `true` / `false` |
| `LOCAL_JWT_SECRET` | Required when `AUTH_MODE=local` |
| `AUTH_ISSUER`, `AUTH_AUDIENCE`, `AUTH_ALLOWED_ALGS_CSV`, `AUTH_JWKS_URL` | See `doc/entra-jwks-auth.md` |
| `INCLUDE_FLAG_PREFIXES_CSV` | Filters which flag keys appear in mock payloads |
| `MOCK_FEATURES_JSON` | Mock mode feature JSON (maps to `mock_features_json`) |

---

## Shell `.env` / `.env.local` (Vite) checklist

```env
VITE_RUNTIME_SOURCE_MODE=registry
VITE_REGISTRY_RUNTIME_URL=http://localhost:8000/api/runtime/features
VITE_BOOTSTRAP_URL=http://localhost:8000/api/shell/bootstrap
```

Use the **same host/port** as Uvicorn. **`VITE_BOOTSTRAP_URL`** must be the **bootstrap** path, not the runtime path.

---

## Dev-only shortcuts (do not use in production)

- `AUTH_MODE=local` + HS256 + shared `LOCAL_JWT_SECRET`
- `REQUIRE_AUTH=false` for quick UI work
- `BOOTSTRAP_MODE=mock` + `MOCK_FEATURES_JSON` without registry
- `NoopFlagService` whenever `APP_CONFIGURATION_ENDPOINT` is unset (all flags **true**)
- `X-Debug-*` headers for persona switching

---

## Before production

- `AUTH_MODE=entra`, JWKS URL, RS256 only.
- `REQUIRE_AUTH=true`.
- Real App Configuration endpoint + managed identity / secrets as appropriate.
- Remove debug headers from any public path.
- `REGISTRY_READ_TOKEN` or network rules aligned with platform security.

---

## Automated tests

From repo root (with dev deps installed):

```bash
python -m pytest -q
```

`pyproject.toml` sets **`pythonpath = ["."]`** so `import app` works without editable install.

---

## Definition of done (local)

- Registry lists active manifests for `APP_ENV`.
- Bootstrap API returns filtered `features` consistent with permissions + flags.
- Shell loads bootstrap + runtime URLs without CORS errors (`CORS_ALLOW_ORIGINS_CSV`).
- `pytest` passes.
