# Reports Layering API Contract

## Overview

This document defines the backend API contract for the `Reports Layering` feature.

Base path:

```text
/api/reports
```

---

## Authentication

All protected endpoints require a valid access token.

The platform uses:

```text
Entra app role value = platform permission
```

The backend does not maintain role-permission mappings.

---

## Authorization Model

Authorization is based on permission-shaped roles provided in the JWT:

```json
{
  "roles": [
    "reports-layering.view",
    "reports-layering.edit"
  ]
}
```

Special role:

```text
platform.admin
```

This grants full access (`*`).

---

## Permission Naming

Use:

```text
<feature-key>.<action>
```

Examples:

```text
reports-layering.view
reports-layering.create
reports-layering.edit
reports-layering.delete
reports-layering.manage
```

---

## Endpoint Security Rules

| Endpoint | Permission |
|--------|-----------|
| `GET /health` | public |
| `GET /me` | `reports-layering.view` |
| `GET /items` | `reports-layering.view` |

---

## Endpoints

### GET /health

Health check endpoint.

Response:

```json
{
  "status": "ok",
  "featureKey": "reports-layering"
}
```

---

### GET /me

Returns current user context.

Requires:

```text
reports-layering.view
```

Response:

```json
{
  "isAuthenticated": true,
  "userId": "string",
  "userName": "string",
  "email": "string",
  "roles": ["string"],
  "authMode": "mock | entra"
}
```

---

### GET /items

Returns feature data.

Requires:

```text
reports-layering.view
```

Response:

```json
{
  "featureKey": "reports-layering",
  "items": [
    {
      "id": "string",
      "name": "string"
    }
  ],
  "user": {
    "id": "string",
    "name": "string",
    "email": "string"
  }
}
```

---

## Error Responses

### 401 Unauthorized

Returned when token is missing or invalid.

```json
{
  "detail": "Authentication is required."
}
```

---

### 403 Forbidden

Returned when user lacks required permission.

```json
{
  "detail": {
    "message": "Insufficient permissions",
    "requiredPermissions": [
      "reports-layering.view"
    ]
  }
}
```

---

## Local Development

Mock mode:

```env
AUTH_MODE=mock
AUTH_DEFAULT_DEV_ROLES_RAW=reports-layering.view
AUTH_DEBUG_HEADERS_ENABLED=true
```

Test via:

```bash
curl \
  -H "X-Debug-Roles: reports-layering.view" \
  http://localhost:<backend-port>/api/reports/items
```

---

## Production Behavior

Production must use:

```env
AUTH_MODE=entra
```

Requirements:

```text
Valid JWT
Correct audience
Correct issuer
roles claim present
```

Example token:

```json
{
  "roles": ["reports-layering.view"]
}
```

---

## Important Rules

### Do

```text
Use permission-shaped roles
Enforce permissions at backend
Keep endpoints consistent with manifest permissions
```

### Do Not

```text
Do not map roles to permissions
Do not convert scopes into permissions
Do not trust frontend authorization
```

---

## Relationship to Platform

Authorization flow:

```text
Entra → roles
  → Bootstrap → filters features
  → Shell → renders UI
  → Feature backend → enforces permissions
```

The backend is the final authority for access control.