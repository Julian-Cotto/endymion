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

## Reports Layering Endpoints (data plane)

The generic `/me` / `/items` endpoints above are scaffold defaults. The feature's
real surface lives under:

```text
/api/reports/reports-layering
```

### Permissions

| Action | Permission |
|---|---|
| View reports / rows / CSV export | `reports-layering.view` |
| Create/edit definitions, upload files, preview | `reports-layering.create` |
| Manage access groups | `reports-layering.manage` (admin) |

`platform.admin` grants all.

### Viewer surface

| Method / Path | Permission | Description |
|---|---|---|
| `GET /reports` | view | List report cards visible to the caller's groups. |
| `GET /reports/{slug}` | view | Report metadata + latest cached snapshot rows. |
| `GET /reports/{slug}/export.csv` | view | CSV of the latest snapshot. |

### Author surface

| Method / Path | Permission | Description |
|---|---|---|
| `GET /definitions` | create | All definitions (incl. archived). |
| `GET /definitions/{slug}` | create | Full definition (incl. SQL/sources) for editing. |
| `POST /definitions` | create | Create a definition; takes an immediate snapshot. |
| `PUT /definitions/{slug}` | create | Update a definition; re-snapshots. |
| `POST /definitions/{slug}/refresh` | create | Re-run and refresh the snapshot. |
| `POST /definitions/preview` | create | **Dry-run**: compute real columns + sample rows for an unsaved definition. Persists nothing. |
| `POST /uploads` | create | **Multipart** CSV/XLSX upload → `file_ref` + inferred columns. |

### Definition shape (`POST`/`PUT /definitions`, and `/preview`)

A report draws data one of two ways — a legacy single `sql_text`, or one-or-more
`sources` blended by `combine`:

```jsonc
{
  "title": "Blended Book",
  "description": "",
  // Option A — legacy single source:
  "sql_text": "SELECT region, COUNT(*) AS n FROM policies GROUP BY region",
  // Option B — multiple sources (omit sql_text):
  "sources": [
    { "name": "policies", "type": "sql", "sql": "SELECT k, prem FROM policies" },
    { "name": "claims",   "type": "file", "file_ref": "<from /uploads>" }
  ],
  "combine": {
    "op": "join",                 // "join" | "union"
    "joins": [                    // required for op "join"
      { "left": "policies", "right": "claims",
        "on": [["k", "k"]], "how": "inner" }  // how: "inner" | "left"
    ],
    "distinct": false             // union only
  },
  // Display metadata:
  "columns": { "region": { "label": "Region", "format": "int" } },
  "params":  { "status": { "type": "string", "default": "active" } },
  "chart":   { "type": "bar", "x": "region", "y": "n" },
  "output_types": ["table", "chart", "kpi"],
  "layout": null,
  "access_groups": ["underwriting"],
  "status": "active"
}
```

Rules (enforced backend-side, `422` on violation):

- Provide **either** `sql_text` **or** `sources`, never both.
- `combine` is **required** when there is more than one source.
- `sources[].name` must be unique; `combine` join refs must name known sources.
- SQL (single or per-source) must be a single read-only `SELECT`/`WITH`; declared
  `:params` must cover all referenced params.
- `type: "file"` sources must reference an existing upload `file_ref`.

### `POST /uploads` response

```json
{
  "file_ref": "d5e18de8e6fe4930b8789966ef28be1f",
  "filename": "book.csv",
  "row_count": 3,
  "columns": { "region": { "label": "region", "format": "text" } },
  "sample_rows": [ { "region": "West", "premium": 1200 } ]
}
```

Limits: `.csv`/`.xlsx` only, ≤ 10 MB, ≤ 50k rows, ≤ 200 columns.

### `POST /definitions/preview` response

```json
{
  "result_columns": ["k", "a_value", "b_value"],
  "rows": [ { "k": 0, "a_value": 10, "b_value": 10 } ],
  "row_count": 8
}
```

### Group administration (admin)

| Method / Path | Description |
|---|---|
| `GET /groups` | List access groups + member counts. |
| `POST /groups` | Create a group. |
| `POST /groups/{slug}/members` | Add a member (by user key). |
| `DELETE /groups/{slug}/members/{user_key}` | Remove a member. |

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