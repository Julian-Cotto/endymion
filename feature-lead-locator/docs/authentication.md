# Authentication and Authorization

## Overview

This feature follows the platform authorization convention:

Entra app role value = platform permission

The feature backend does not maintain its own role-permission mapping.

---

## Runtime Flow

Shell
→ obtains access token from Entra  
→ passes token to feature frontend  
→ feature frontend calls feature backend  
→ feature backend validates token  
→ feature backend reads roles claim  
→ feature backend enforces required permissions  

---

## Permission Naming

Use this format:

<feature-key>.<action>

Examples for this feature:

lead-locator.view  
lead-locator.create  
lead-locator.edit  
lead-locator.delete  
lead-locator.manage  

Platform-wide admin:

platform.admin

platform.admin grants wildcard access.

---

## Entra App Roles

Create app roles in Entra with values that match permissions directly.

Example:

Value: lead-locator.view  
Display name: Lead Locator View  
Allowed member types: Users/Groups  
Description: Can view Lead Locator  

---

## Local Development

Local development uses mock mode by default:

AUTH_MODE=mock  
AUTH_DEFAULT_DEV_ROLES_RAW=lead-locator.view  
AUTH_DEBUG_HEADERS_ENABLED=true  

Optional debug header:

X-Debug-Roles: lead-locator.view,lead-locator.edit  

Debug headers are only for local/mock development.

---

## Production

Production must use Entra mode:

APP_ENVIRONMENT=production  
AUTH_MODE=entra  
AUTH_DEBUG_HEADERS_ENABLED=false  

Required Entra settings:

ENTRA_TENANT_ID=<tenant-id>  
ENTRA_AUDIENCE=api://<bootstrap-api-client-id>  
ENTRA_ISSUER=https://login.microsoftonline.com/<tenant-id>/v2.0  
ENTRA_JWKS_URL=https://login.microsoftonline.com/<tenant-id>/discovery/v2.0/keys  

---

## Backend Enforcement

Example usage:

from fastapi import Depends  
from app.platform.auth_context import AuthContext  
from app.platform.permissions import require_permissions  

@router.get("/items")  
async def list_items(  
    ctx: AuthContext = Depends(require_permissions(["lead-locator.view"])),  
):  
    return {"items": []}  

For one-of-many permission checks:

from app.platform.permissions import require_any_permission  

@router.post("/items")  
async def save_item(  
    ctx: AuthContext = Depends(  
        require_any_permission([  
            "lead-locator.edit",  
            "lead-locator.manage",  
        ])  
    ),  
):  
    return {"status": "saved"}  

---

## Responsibility Split

Entra → Assign roles to users/groups  
Bootstrap API → Filter visible features  
Shell → Render accessible navigation  
Feature frontend → UX gating only  
Feature backend → Security enforcement  

---

## What Not To Do

Do not add feature-local mappings such as:

developer → lead-locator.view  
admin → *  
access_as_user → lead-locator.view  

Do not treat OAuth scopes as business permissions.

Scopes answer:

Can this client call this API?

Roles answer:

What can this user do?