# Authentication: local HS256 vs Entra JWKS

This service does **not** hard-code Entra. It branches on **`AUTH_MODE`** (`local` or `entra`) in `app/core/config.py` and `app/core/jwt_auth.py`.

---

## `AUTH_MODE=local` (development)

- **`LOCAL_JWT_SECRET`** (required) and **`LOCAL_JWT_ALGORITHM=HS256`** (required; config rejects other algorithms for local mode).
- JWT header algorithm must be **HS256**.
- **`AUTH_ISSUER`** / **`AUTH_AUDIENCE`**: if non-empty, `iss` / `aud` are verified; if empty, those checks are disabled.
- **`AUTH_JWKS_URL`**: leave empty for local HS256.

Example `.env` fragment:

```env
AUTH_MODE=local
REQUIRE_AUTH=true
LOCAL_JWT_SECRET=local-dev-secret
LOCAL_JWT_ALGORITHM=HS256
AUTH_ISSUER=https://issuer.example.com
AUTH_AUDIENCE=api://shell-bootstrap
AUTH_ALLOWED_ALGS_CSV=HS256
AUTH_JWKS_URL=
```

### Local debug headers

When local/mock paths apply, or when decoding a local JWT, you can override display fields with:

- `X-Debug-User-Id`
- `X-Debug-User-Name`
- `X-Debug-Email`
- `X-Debug-Roles` (comma-separated)

See `app/api/auth_runtime.py`.

---

## `AUTH_MODE=entra` (production-shaped)

`Settings.validate_auth_config()` requires:

- **`AUTH_ISSUER`**
- **`AUTH_AUDIENCE`**
- **`AUTH_JWKS_URL`**
- **`AUTH_ALLOWED_ALGS_CSV`** resolving to exactly **`RS256`**

`decode_bearer_token` uses **`PyJWKClient`** against **`AUTH_JWKS_URL`** and decodes with **`RS256`**.

Example (commented in `.env.example`):

```env
AUTH_MODE=entra
AUTH_ISSUER=https://login.microsoftonline.com/<tenant-id>/v2.0
AUTH_AUDIENCE=api://<bootstrap-api-client-id>
AUTH_ALLOWED_ALGS_CSV=RS256
AUTH_JWKS_URL=https://login.microsoftonline.com/<tenant-id>/discovery/v2.0/keys
```

---

## Claim → role → permission

Same pipeline for both modes after decode:

1. **`roles_from_claims`** — `AUTH_*_CLAIM` names and JSON maps (`GROUP_ROLE_MAP_JSON`, `SCOPE_ROLE_MAP_JSON`, `WID_ROLE_MAP_JSON`, `DIRECT_ROLE_ALLOW_LIST_CSV`).
2. **`permissions_from_user`** — `ROLE_PERMISSION_MAP_JSON`, `DEFAULT_PERMISSIONS_CSV`, admin wildcard.

Details: **`doc/auth-and-permissions.md`**.

---

## Manual check (registry + JWT)

Start Uvicorn (port is arbitrary):

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

When **`REQUIRE_AUTH=true`** and neither mock shortcut applies:

```bash
curl -s "http://localhost:8000/api/runtime/features" \
  -H "Authorization: Bearer <valid-jwt>" | jq
```

Response shape is **`RuntimeFeaturesResponse`** (`environment`, `user`, `permissions`, `flags`, `features`, `metadata`, …) from `app/schemas/runtime_features.py` — not fixed to empty `features`; content depends on registry + visibility.

---

## Security reminders

- Do not ship **`AUTH_MODE=local`** or empty **`AUTH_JWKS_URL`** to production.
- **`REQUIRE_AUTH=false`** is only for controlled local testing.
- Entra mode must keep **`AUTH_ALLOWED_ALGS_CSV=RS256`** only (enforced in code).
