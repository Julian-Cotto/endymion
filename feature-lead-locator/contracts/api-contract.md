# Lead Locator API Contract

## Overview

This document defines the backend API contract for the `Lead Locator` feature.

Base path:

```text
/api/leads
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
    "lead-locator.view",
    "lead-locator.edit"
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
lead-locator.view
lead-locator.create
lead-locator.edit
lead-locator.delete
lead-locator.manage
```

---

## Endpoint Security Rules

| Endpoint | Permission |
|--------|-----------|
| `GET /health` | public |
| `GET /me` | `lead-locator.view` |
| `GET /items` | `lead-locator.view` |

---

## Endpoints

### GET /health

Health check endpoint.

Response:

```json
{
  "status": "ok",
  "featureKey": "lead-locator"
}
```

---

### GET /me

Returns current user context.

Requires:

```text
lead-locator.view
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
lead-locator.view
```

Response:

```json
{
  "featureKey": "lead-locator",
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
      "lead-locator.view"
    ]
  }
}
```

---

## Local Development

Mock mode:

```env
AUTH_MODE=mock
AUTH_DEFAULT_DEV_ROLES_RAW=lead-locator.view
AUTH_DEBUG_HEADERS_ENABLED=true
```

Test via:

```bash
curl \
  -H "X-Debug-Roles: lead-locator.view" \
  http://localhost:<backend-port>/api/leads/items
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
  "roles": ["lead-locator.view"]
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