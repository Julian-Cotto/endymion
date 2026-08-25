# Auth and permissions

End-to-end behavior implemented in `app/api/auth_runtime.py`, `app/core/jwt_auth.py`, `app/services/claim_role_mapper.py`, and `app/services/permission_mapper.py`.

---

## Request flow

```text
Client
  -> (optional) Authorization: Bearer <JWT>
  -> (optional) X-Debug-User-Id / X-Debug-User-Name / X-Debug-Email / X-Debug-Roles
  -> GET /api/shell/bootstrap | GET /api/runtime/features
  -> runtime_authenticated_user
  -> decode_bearer_token (if token required)
  -> build_authenticated_user_from_claims
  -> roles_from_claims
  -> permissions_from_user
  -> bootstrap_service visibility (permissions + flags)
```

---

## `REQUIRE_AUTH`

Loaded from **`REQUIRE_AUTH`** (`Settings.require_auth`).

- **`false`**: no bearer token required; **`runtime_authenticated_user`** returns a **mock user** (optionally overridden by `X-Debug-*` headers).
- **`true`**: a bearer token is required **except** for the mock shortcut below.

---

## When no bearer token is accepted

`runtime_authenticated_user` returns a **mock local user** (with optional **`X-Debug-*`** header overrides) if **either**:

1. **`REQUIRE_AUTH=false`**, or  
2. **`BOOTSTRAP_MODE=mock`** and **`AUTH_MODE=local`**.

Otherwise **`Authorization: Bearer <token>`** is required and **`decode_bearer_token`** runs.

---

## JWT modes (`AUTH_MODE`)

Set **`AUTH_MODE=local`** or **`AUTH_MODE=entra`**. Validated at settings load via **`Settings.validate_auth_config()`** in `app/core/config.py`.

### Local (`AUTH_MODE=local`)

- Algorithm must be **HS256** (`LOCAL_JWT_ALGORITHM`, enforced).
- Secret: **`LOCAL_JWT_SECRET`** (required).
- **`AUTH_ISSUER`** / **`AUTH_AUDIENCE`**: if set, JWT **`iss`** / **`aud`** are verified; if empty, those checks are skipped (see `jwt.decode` options in `jwt_auth.py`).

### Entra (`AUTH_MODE=entra`)

- **`AUTH_ISSUER`**, **`AUTH_AUDIENCE`**, **`AUTH_JWKS_URL`** required.
- **`AUTH_ALLOWED_ALGS_CSV`** must resolve to exactly **`RS256`** (enforced).
- Tokens decoded with **`PyJWKClient`** (`jwt_auth.py`).

---

## Claims → roles (`roles_from_claims`)

Configured claim names (defaults shown):

| Setting | Default | Source |
|---------|---------|--------|
| `AUTH_ROLES_CLAIM` | `roles` | string or list → direct roles |
| `AUTH_GROUPS_CLAIM` | `groups` | mapped via `GROUP_ROLE_MAP_JSON` |
| `AUTH_SCOPE_CLAIM` | `scp` | space-separated scopes → `SCOPE_ROLE_MAP_JSON` |
| `AUTH_WIDS_CLAIM` | `wids` | mapped via `WID_ROLE_MAP_JSON` |

Direct roles are filtered with **`DIRECT_ROLE_ALLOW_LIST_CSV`**.

---

## Roles → permissions (`permissions_from_user`)

- JSON: **`ROLE_PERMISSION_MAP_JSON`** → `Settings.role_permission_map` (role → list of permission strings).
- **`DEFAULT_PERMISSIONS_CSV`**: extra permissions appended for every user (after role mapping).
- If **`admin`** is in **`user.roles`**, permissions return **`["*"]`** immediately (wildcard).

---

## Feature visibility (registry payloads)

A registry manifest is visible only if:

1. Every **`authorization.requiredPermissions`** is satisfied by the user’s permission set.
2. Every **`authorization.requiredFlags`** key is **true** in the resolved flag map from **`flag_service.resolve_flags`**.

Mock mode uses the same shape on coerced mock features.

---

## Cache key shapes (`bootstrap_service.py`)

- Bootstrap: `bootstrap:v2:{app_env}:{user_id}:{sorted_permissions_joined}`
- Runtime: `runtime:v2:{app_env}:{user_id}:{sorted_permissions_joined}`

TTL for the combined bootstrap/runtime cache factory is clamped between **1** and **15** seconds in code (see `get_or_set` calls).

---

## Required JWT claims (authenticated path)

`build_authenticated_user_from_claims` requires string claims:

- **`AUTH_USER_ID_CLAIM`** (default `sub`)
- **`AUTH_USER_NAME_CLAIM`** (default `name`)
- **`AUTH_EMAIL_CLAIM`** (default `email`)

Missing values → **401** with a clear message.
