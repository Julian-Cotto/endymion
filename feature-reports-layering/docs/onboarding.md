# Reports Layering Developer Onboarding

## Purpose

This repository contains the `Reports Layering` feature.

It is generated as an independent feature repository for the modular application platform.

The feature may include:

```text
frontend/
backend/
jobs/
workers/
listeners/
contracts/
infra/
scripts/
docs/
```

---

## Platform Context

The platform runtime flow is:

```text
Shell
  → Bootstrap API
  → Registry Service
  → Feature Repository
```

Responsibilities:

| Component | Responsibility |
|---|---|
| Shell | Hosts and dynamically loads features |
| Bootstrap API | Resolves runtime config, user context, permissions, flags, and visible features |
| Registry Service | Stores feature releases and active versions |
| Feature Repo | Owns feature frontend, backend, workers, jobs, contracts, and feature-specific infrastructure |

---

## First-Time Setup

Run:

```bash
./scripts/bootstrap.sh
```

This prepares the repository for local development.

Expected actions:

```text
install backend dependencies
install frontend dependencies
prepare local env files
make scripts executable
```

---

## Run Locally

Run:

```bash
./scripts/run-local.sh
```

This starts the feature and registers it locally.

Expected actions:

```text
start backend
start frontend
render manifest
validate manifest
publish release to registry
activate local release
```

---

## Required Platform Services

Before starting this feature, the following platform services should be running:

```text
Registry Service
Bootstrap API
Shell
```

Typical local ports:

```text
Shell             :3000
Bootstrap API     :8001
Registry          :8010
```

Feature-specific local ports are defined in the generated environment files and manifest.

---

## Authentication Model

This feature follows the platform-wide authorization convention:

```text
Entra app role value = platform permission
```

Examples:

```text
reports-layering.view
reports-layering.create
reports-layering.edit
reports-layering.manage
platform.admin
```

The feature does not maintain role-permission mappings.

Do not add mappings such as:

```text
developer → reports-layering.view
admin → *
access_as_user → reports-layering.view
```

OAuth scopes are for API access, not feature business permissions.

---

## Local Auth

Local development uses mock auth by default.

```env
AUTH_MODE=mock
AUTH_DEFAULT_DEV_ROLES_RAW=reports-layering.view
AUTH_DEBUG_HEADERS_ENABLED=true
```

Optional debug header:

```http
X-Debug-Roles: reports-layering.view,reports-layering.edit
```

This allows local permission testing without Entra.

---

## Production Auth

Production must use Entra JWT validation.

```env
APP_ENVIRONMENT=production
AUTH_MODE=entra
AUTH_DEBUG_HEADERS_ENABLED=false
```

The token must contain permission-shaped roles:

```json
{
  "roles": [
    "reports-layering.view"
  ]
}
```

---

## Backend Permission Enforcement

Use the generated permission dependency:

```python
from fastapi import Depends
from app.platform.auth_context import AuthContext
from app.platform.permissions import require_permissions


@router.get("/items")
async def list_items(
    ctx: AuthContext = Depends(require_permissions(["reports-layering.view"])),
):
    return {"items": []}
```

For admin-style access, assign this Entra app role:

```text
platform.admin
```

`platform.admin` grants wildcard access.

---

## Manifest Authorization

The feature manifest should declare required permissions:

```json
{
  "authorization": {
    "requiredPermissions": ["reports-layering.view"],
    "requiredFlags": ["reports-layering.enabled"]
  }
}
```

Bootstrap uses this to decide whether the feature is visible to the user.

---

## Frontend Development

The feature frontend is loaded dynamically by the Shell.

The Shell provides:

```text
user context
permissions
access token
feature metadata
backend API base URL
```

Frontend permission checks are for UX only.

Examples:

```text
hide unavailable buttons
disable unavailable actions
show read-only state
```

Security must be enforced by the backend.

---

## Backend Development

The backend should enforce permissions on protected endpoints.

Common generated endpoints:

```text
GET /api/reports/health
GET /api/reports/me
GET /api/reports/items
```

`/health` is usually public.

`/me` and `/items` should be protected by permissions.

---

## Testing

Run backend tests:

```bash
cd backend
python -m pytest
```

Run frontend tests:

```bash
cd frontend
npm test
```

Expected authorization coverage:

```text
default mock permission allows access
debug permission override allows access
missing permission returns 403
platform.admin grants access
roles remain permission-shaped
```

---

## Local Troubleshooting

### Feature does not appear in Shell

Check:

```text
Registry service is running
Feature was published to registry
Feature release was activated
Bootstrap API can reach registry
User has required permission
Required feature flag is enabled
```

### Backend returns 403

Check:

```text
AUTH_DEFAULT_DEV_ROLES_RAW
X-Debug-Roles
AUTH_REQUIRED_PERMISSIONS_RAW
Manifest requiredPermissions
```

### Token works but user has no permissions

Check that the access token contains a `roles` claim.

Expected:

```json
{
  "roles": ["reports-layering.view"]
}
```

Do not rely on `scp` for feature permissions.

---

## Developer Rules

### Do

```text
Use permission-shaped roles
Declare required permissions in the manifest
Use require_permissions() for backend security
Keep frontend checks UX-only
Use registry publish + activate flow
Keep feature-specific infrastructure in this repo
```

### Do Not

```text
Do not hardcode feature visibility in the Shell
Do not create feature-local role mappings
Do not convert scopes into business permissions
Do not rely on frontend-only authorization
Do not bypass backend permission checks
```

---

## Definition of Done

A new developer should be able to:

```text
bootstrap the repo
run the feature locally
publish and activate the feature in registry
see the feature in Shell when authorized
receive 403 when missing permissions
run tests successfully
```