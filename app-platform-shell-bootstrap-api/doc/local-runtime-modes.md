# Local runtime modes

How `BOOTSTRAP_MODE` affects `GET /api/shell/bootstrap` and `GET /api/runtime/features`.

---

## Mode selection

Set in `.env` (see `.env.example`):

```env
BOOTSTRAP_MODE=mock
```

or:

```env
BOOTSTRAP_MODE=registry
```

---

## Mock mode (`BOOTSTRAP_MODE=mock`)

### Data source

- Feature lists come from **`MOCK_FEATURES_JSON`**, which maps to `Settings.mock_features_json` (JSON array of feature objects).
- If `mock_features_json` is empty or `[]`, mock responses still build but may have no features until you set JSON.

### Registry and flags (dependencies)

- **`registry_client_dependency()`** returns **`NoopRegistryClient`**: no HTTP to the registry.
- **`flag_service_dependency()`** returns **`NoopFlagService`** unless `APP_CONFIGURATION_ENDPOINT` is set; **`NoopFlagService`** resolves every requested flag key to **`true`** (local convenience).

### Auth shortcut

When **`AUTH_MODE=local`** and **`BOOTSTRAP_MODE=mock`**, **`runtime_authenticated_user`** returns a **mock user** without a bearer token (unless **`REQUIRE_AUTH=true`**, which forces real JWT flow). See `app/api/auth_runtime.py`.

### Typical use

- Shell integration without registry or App Config
- Tuning `MOCK_FEATURES_JSON` for URLs, nav, and auth blocks on manifests

---

## Registry mode (`BOOTSTRAP_MODE=registry`)

### Data source

- Manifests come from the **registry HTTP API**: `GET {REGISTRY_BASE_URL}/api/runtime/features?environment={APP_ENV}`.
- Optional header: **`Authorization: Bearer {REGISTRY_READ_TOKEN}`** when `REGISTRY_READ_TOKEN` is set (`RegistryClient`).

### Flags

- If **`APP_CONFIGURATION_ENDPOINT`** is empty: **`NoopFlagService`** (all requested flags **true**).
- If the endpoint is set: **`AppConfigFlagService`** is used (wired with label, cache, TTL). **`resolve_flags`** in the current implementation still returns **all keys true** (local override); production behavior can be extended to call Azure App Configuration / Feature Management as needed.

### Auth

- With **`REQUIRE_AUTH=true`**, callers must send **`Authorization: Bearer <JWT>`** unless the mock/local shortcut above applies.
- JWT validation is **`AUTH_MODE=local`** (HS256 + `LOCAL_JWT_SECRET`) or **`AUTH_MODE=entra`** (RS256 + JWKS); see `doc/entra-jwks-auth.md` and `doc/auth-and-permissions.md`.

### Required env

- **`REGISTRY_BASE_URL`** (non-empty), or startup raises when building the registry client.

---

## HTTP routes (this service)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/shell/bootstrap` | Shell startup payload |
| GET | `/api/runtime/features` | Same visibility rules, runtime-oriented shape |
| GET | `/api/shell/health` | Liveness |
| GET | `/api/shell/health/dependencies` | JSON summary of mode / registry / App Config wiring |

Port is whatever you pass to Uvicorn (e.g. `--port 8000` or `8001`).

---

## Example shell `.env` (Vite)

Point the shell at this API (adjust host/port to match Uvicorn):

```env
VITE_RUNTIME_SOURCE_MODE=registry
VITE_REGISTRY_RUNTIME_URL=http://localhost:8000/api/runtime/features
VITE_BOOTSTRAP_URL=http://localhost:8000/api/shell/bootstrap
```

---

## Suggested local order

1. Start feature backends/frontends as needed.
2. Start **registry** (e.g. on port `8010`) if using `BOOTSTRAP_MODE=registry`.
3. Start **shell-bootstrap-api** with matching `REGISTRY_BASE_URL` and `APP_ENV`.
4. Start **shell** with `VITE_*` URLs above.
5. Hit `/api/shell/health` then `/api/runtime/features` or `/api/shell/bootstrap` with a valid token when `REQUIRE_AUTH=true`.

---

## Reference ports (examples only)

Your `MOCK_FEATURES_JSON` or registry manifests define real URLs. Common local examples:

| Area | Example port |
|------|----------------|
| Orders backend | 8100 |
| Catalog backend | 8200 |
| Orders frontend | 3200 |
| Catalog frontend | 3300 |
| Registry service | 8010 |

These are not enforced by this repo; they are documentation conventions only.
