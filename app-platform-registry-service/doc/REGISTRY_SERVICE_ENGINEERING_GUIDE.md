# Portal Platform — Registry Service Engineering & Development Guide

This file lives at **`doc/REGISTRY_SERVICE_ENGINEERING_GUIDE.md`**. For day-to-day commands (venv, Compose, pytest, env vars), start from the repository **[README.md](../README.md)**.

## 1. Purpose

This document defines the engineering, development, deployment, and operational standards for the **Registry Service** in the portal platform.

The registry service is a **platform-owned service** that answers one core question:

> Which feature versions are active and allowed to be loaded by the shell in a given environment?

This guide is intentionally detailed because the registry is a foundational part of the platform. It is the control point that enables independent feature deployment without requiring shell redeployment.

---

## 2. Scope

This guide covers:

- registry service purpose and boundaries
- runtime contract with the shell
- write/admin contract with CI/CD
- service architecture and code structure
- database schema and migrations
- deployment model on Azure Container Apps
- Terraform ownership boundaries
- security and Entra authentication model
- release, promotion, and rollback flow
- observability, testing, and operational guardrails

This guide does **not** define feature shell code or shared platform infrastructure in full. Shared platform artifacts belong in the common infrastructure repository.

---

## 3. Platform ownership boundaries

A critical design decision for this platform is the split between:

1. **Common platform infrastructure repository**
2. **Service or feature-specific repository**

### 3.1 Common platform repository owns shared artifacts

Examples:

- Azure Container Registry
- Azure Container Apps Environment
- Azure Database for PostgreSQL Flexible Server
- Log Analytics Workspace
- Key Vault
- shared networking
- shared DNS
- Front Door / WAF if used
- shared monitoring foundation
- shared Service Bus namespace if applicable

### 3.2 Registry repository owns only registry-specific artifacts

Examples:

- registry service source code
- registry Container App
- registry-specific role assignments
- registry configuration
- Alembic migrations for registry schema
- CI/CD workflow for registry release
- registry-specific Terraform that consumes shared outputs

### 3.3 Important rule

The registry repository must **not** create shared platform resources such as:

- ACR
- PostgreSQL server
- Container Apps Environment
- Log Analytics Workspace
- global Key Vault
- shared VNet or DNS

The registry repository may create service-scoped items if the platform governance model allows them, but the preferred model is:

- shared DB server created centrally
- registry schema/tables created by migrations in the registry service

---

## 4. Registry service purpose

The registry service stores and serves feature release metadata.

It is the source of truth for:

- feature identity
- deployed versions
- activation status
- runtime bundle URLs
- API base URLs
- shell compatibility metadata
- feature navigation metadata
- release audit trail

The registry service allows the shell to dynamically discover active features by environment.

---

## 5. What the registry does and does not do

### 5.1 What it does

- accepts release manifests from CI/CD
- validates release manifests
- stores feature and release records
- activates and deactivates releases
- returns active runtime manifests to the shell
- supports rollback by switching active release
- audits publish and activate operations

### 5.2 What it does not do

- host frontend bundles
- proxy feature APIs
- fully evaluate end-user permissions
- replace feature flags platform
- become a generic platform control plane
- own shared infrastructure foundations

---

## 6. Service boundaries and consumers

### 6.1 Shell runtime
The shell reads active manifests from the registry and then decides which features to show based on shell-owned rules such as permissions and flags.

### 6.2 Feature CI/CD pipelines
Feature pipelines publish candidate releases and may activate releases based on environment policy.

### 6.3 Platform administrators
Platform operations can activate, rollback, retire, or inspect releases.

---

## 7. High-level architecture

```text
Feature CI/CD
   |
   | publish / activate
   v
Registry Service API
   |
   +-- Manifest Validation
   +-- Release Persistence
   +-- Activation Logic
   +-- Audit Logging
   |
   v
PostgreSQL
   ^
   |
Shell Runtime
   |
   | read active manifests
   v
Dynamic feature loading
```

---

## 8. Runtime contract with the shell

The shell must never hardcode feature entry URLs.

Instead, the shell should:

1. determine current environment
2. call the runtime endpoint
3. receive all active manifests for that environment
4. filter them by shell-owned rules
5. dynamically load the feature frontend bundle

### 8.1 Runtime read endpoint

```http
GET /api/runtime/features?environment=prod
```

### 8.2 Example runtime response

```json
{
  "environment": "prod",
  "features": [
    {
      "manifestVersion": "1.0",
      "featureKey": "orders",
      "displayName": "Orders",
      "version": "1.4.2",
      "environment": "prod",
      "route": "/orders",
      "frontend": {
        "type": "module",
        "entryUrl": "https://portal-cdn.company.com/orders/1.4.2/entry.js",
        "integrity": "sha384-example",
        "basePath": "/orders/"
      },
      "backend": {
        "apiBaseUrl": "https://orders-api-prod.company.com"
      },
      "nav": {
        "label": "Orders",
        "icon": "shopping-cart",
        "group": "Operations",
        "order": 30
      },
      "authorization": {
        "requiredPermissions": ["orders.view"],
        "requiredFlags": ["orders.enabled"]
      },
      "auth": {
        "required": true,
        "mode": "entra",
        "shellAuthRequired": true,
        "tokenForwarding": true,
        "tokenStrategy": "forwarded-bearer",
        "allowedDevModes": ["mock"],
        "roles": []
      },
      "compatibility": {
        "shellContractMin": "1.0",
        "shellContractMax": "1.x"
      },
      "metadata": {
        "ownerTeam": "operations-platform",
        "commitSha": "abc123",
        "buildId": "20260320.7",
        "releaseDate": "2026-03-20T18:02:00Z"
      }
    }
  ]
}
```

---

## 9. Write/admin contract with CI/CD

Feature pipelines do not modify shell source code. Instead, they publish release metadata to the registry.

### 9.1 Publish release

```http
POST /api/releases
```

### 9.2 Activate release

```http
POST /api/admin/features/{featureKey}/versions/{version}/activate?environment=test
```

### 9.3 Expected release flow

1. feature pipeline builds frontend and backend
2. feature pipeline deploys feature infrastructure and services
3. pipeline runs verification
4. pipeline publishes release manifest as candidate
5. pipeline or approver activates release based on policy
6. shell sees newly active release on next registry fetch

---

## 10. Release lifecycle model

Recommended release states:

- `draft`
- `candidate`
- `active`
- `inactive`
- `retired`
- `failed`

### 10.1 Meanings

- **draft** — prepared but not yet publishable
- **candidate** — deployed and registered, but not active
- **active** — currently live for shell consumption
- **inactive** — previously active or published but not current
- **retired** — no longer allowed to become active
- **failed** — deployment or post-deploy validation failed

### 10.2 Important platform rules

- publish does not imply activate
- only one active release per feature per environment (the reference `ActivationService` marks the previous `active` release `inactive` before activating the target)
- active routes should be unique per environment across features (recommended; not enforced beyond activation per feature in the reference code — see §15)
- retired releases cannot be reactivated
- runtime endpoint must return only active releases

---

## 11. Repository structure

Layout of this repository (reference scaffold):

```text
platform-registry-service/
├── README.md                          # quick start, env, tests, API summary
├── requirements.txt                   # runtime + pytest/httpx/coverage deps
├── pytest.ini                         # pytest pythonpath / testpaths
├── Dockerfile
├── docker-compose.yml                 # local Postgres (port 5433 on host)
├── alembic.ini
├── .env.example
├── app/
│   ├── api/                           # routes: runtime, releases, admin
│   ├── core/                          # config (pydantic-settings), security
│   ├── db/                            # SQLAlchemy models, session (lazy engine)
│   ├── schemas/                       # Pydantic: manifest, release, runtime DTOs
│   ├── services/                      # validator, release, activation, runtime, audit
│   ├── exceptions.py
│   └── main.py
├── tests/                             # pytest: conftest (Postgres fixtures), API + unit tests
├── doc/
│   └── REGISTRY_SERVICE_ENGINEERING_GUIDE.md
├── infra/
│   ├── providers.tf
│   ├── variables.tf
│   ├── data-platform.tf
│   ├── locals.tf
│   ├── container-app.tf
│   ├── role-assignments.tf
│   ├── outputs.tf
│   └── terraform.tfvars.example
├── migrations/
│   ├── env.py
│   └── versions/                      # e.g. 0001_init_registry, 0002_add_release_auth_json
├── scripts/
│   ├── run_local.sh                   # compose up, migrate, uvicorn :8010
│   ├── seed_local.py                  # optional local seed (active releases)
│   ├── build_image.sh
│   ├── deploy_registry.sh
│   ├── run_migrations.sh
│   └── smoke_test.sh                  # curls REGISTRY_BASE_URL/health
└── .github/
    └── workflows/
        └── registry-release.yml
```

---

## 12. Code architecture

### 12.1 `app/api`
Route definitions and dependency wiring.

### 12.2 `app/core`
Configuration, security, and cross-cutting concerns.

### 12.3 `app/db`
SQLAlchemy models and session setup.

### 12.4 `app/schemas`
Pydantic request and response models. The release manifest (`ReleaseManifestIn`) includes **`authorization`** (permission/flag hints) and **`auth`** (shell/API auth and token-forwarding policy); see §14.

### 12.5 `app/services`
Business logic:
- validation
- release persistence
- activation
- runtime projection
- auditing

### 12.6 `migrations`
Alembic migrations for schema lifecycle.

### 12.7 `infra`
Registry-specific Terraform only.

### 12.8 `scripts`
Deployment and operational helper scripts.

---

## 13. Data model

### 13.1 `features`
Stable feature identity.

Fields (see `app/db/models.py`):
- feature key (unique)
- display name
- owner team
- optional repository URL (`repo_url`)

### 13.2 `releases`
A feature version in an environment.

Fields (see `app/db/models.py`):
- feature ID (FK)
- manifest version string
- release version and environment
- status (`ReleaseStatus` enum: draft, candidate, active, inactive, retired, failed)
- route, frontend entry URL, backend API base URL (scalar columns for runtime projection)
- `nav_json`, `authorization_json`, **`auth_json`** (shell/token auth policy), `compatibility_json`, `metadata_json` (JSONB)
- soft delete flag `is_deleted`
- activation timestamp when made active

### 13.3 `audits`
Action history.

Fields:
- action
- feature key
- version
- environment
- actor
- details JSON
- timestamp

---

## 14. Manifest contract

### 14.1 Why the manifest matters

The release manifest is the interface between feature CI/CD and the registry. It must be versioned, validated, and stable.

### 14.2 Required fields

- `manifestVersion`
- `featureKey`
- `displayName`
- `version`
- `environment`
- `route`
- `frontend.entryUrl`
- `backend.apiBaseUrl`
- `nav`
- `authorization` (non-empty `requiredPermissions` and `requiredFlags`; see §15)
- `metadata.ownerTeam`

**Optional with defaults:** `auth` — if omitted, the API applies `AuthSchema` defaults (`mode` defaults to `mock`, etc.). Publish persists the resolved object to `releases.auth_json`.

### 14.3 Example manifest

```json
{
  "manifestVersion": "1.0",
  "featureKey": "orders",
  "displayName": "Orders",
  "version": "1.4.2",
  "environment": "test",
  "route": "/orders",
  "frontend": {
    "type": "module",
    "entryUrl": "https://portal-cdn.company.com/orders/1.4.2/entry.js",
    "integrity": "sha384-example",
    "basePath": "/orders/"
  },
  "backend": {
    "apiBaseUrl": "https://orders-api-test.company.com"
  },
  "nav": {
    "label": "Orders",
    "icon": "shopping-cart",
    "group": "Operations",
    "order": 30
  },
  "authorization": {
    "requiredPermissions": ["orders.view"],
    "requiredFlags": ["orders.enabled"]
  },
  "auth": {
    "required": true,
    "mode": "entra",
    "shellAuthRequired": true,
    "tokenForwarding": true,
    "tokenStrategy": "forwarded-bearer",
    "allowedDevModes": ["mock"],
    "roles": []
  },
  "compatibility": {
    "shellContractMin": "1.0",
    "shellContractMax": "1.x"
  },
  "metadata": {
    "ownerTeam": "operations-platform",
    "commitSha": "abc123",
    "buildId": "20260320.7",
    "releaseDate": "2026-03-20T18:02:00Z"
  }
}
```

### 14.4 `authorization` vs `auth`

- **`authorization`** — Declares what the feature expects for **end-user / feature access** (permission and flag IDs). The shell uses this with its own authz model; the registry does not evaluate these claims.
- **`auth`** — Declares how the feature expects **tokens and shell authentication** to interact with the feature backend (e.g. Entra vs mock, whether to forward a bearer token, allowed dev modes). Persisted separately as `authorization_json` vs `auth_json` on `releases` so runtime responses carry both.

---

## 15. Validation rules

The registry must reject invalid manifests. The **reference code** in this repository implements the following (see `app/schemas/manifest.py` and `app/services/manifest_validator.py`):

**Enforced in code today**

- `version`: semver pattern (e.g. `1.0.0`, optional pre-release suffix).
- `route`: must start with `/`.
- `featureKey`: lowercase letters, digits, hyphens only.
- `environment`: one of `local`, `dev`, `test`, `uat`, `staging`, `prod`, `production`.
- `frontend.type`: must be `module` (only remote module loading is supported in the validator).
- `frontend.entryUrl` / `backend.apiBaseUrl`: hostnames must appear in `ALLOWED_FRONTEND_HOSTS` and `ALLOWED_API_HOSTS` respectively (comma-separated settings; defaults include `localhost` and `127.0.0.1`). URLs are parsed with Pydantic `HttpUrl` — **HTTP is allowed** for local hosts; production should still use HTTPS end-to-end.
- `authorization.requiredPermissions` / `requiredFlags`: non-empty; each entry matches `^[a-z0-9-]+\.[a-z0-9-]+$` after deduplication/trimming in the schema layer, with an additional permission/flag pattern check in the manifest validator.
- **`auth`** (Pydantic `AuthSchema`): validated on publish when present (defaults apply when omitted). In the reference code:
  - `mode`: one of `entra`, `mock`, `none` (case-insensitive input, stored normalized).
  - `tokenStrategy`: optional; if set, one of `forwarded-bearer`, `bearer`, `shell-session`, `none`, `forward_access_token`.
  - `allowedDevModes`: each entry one of `entra`, `mock`, `none`.
  - `roles`: deduped non-empty strings (no fixed pattern beyond normalization).
  - Other fields: `required`, `shellAuthRequired`, `tokenForwarding` (booleans).  
  The manifest validator (`ManifestValidator`) still focuses on semver, hosts, `frontend.type`, and authorization strings; **`auth` shape is enforced by Pydantic**, not duplicated there.
- Publish path checks **feature scope** when `AUTH_DISABLED` is false: JWT (or mock dev token) claims must allow the manifest’s `featureKey` unless the caller has a wildcard scope.

**Recommended platform rules (not all enforced in this scaffold)**

- Prefer HTTPS for all entry and API URLs in non-local environments.
- Prevent duplicate **active** routes across different features in the same environment (would require extra DB constraints or application checks; not implemented in the reference `ReleaseService` beyond idempotent publish by feature/version/environment).
- Optional stronger validation: URL reachability checks, nav naming standards, stricter compatibility parsing (HEAD/GET to entry URL, backend health probe, etc.).

---

## 16. Azure hosting model

The registry service is hosted on **Azure Container Apps**, not App Service.

### 16.1 Why Container Apps

- aligns with service-oriented platform direction
- fits containerized FastAPI deployment
- supports managed identity
- supports revisions and rollback
- supports low operational overhead
- fits early project phases where App Service is not planned

### 16.2 Registry hosting recommendation

- one dedicated Container App for the registry
- Container Apps Environment owned by common infrastructure repo
- minimum 1 replica
- external ingress only if shell reads directly from browser
- internal ingress preferred if shell uses BFF or gateway later

### 16.3 Revision mode

For initial phases:
- `revision_mode = "Single"`

Later:
- can move to `Multiple` for controlled canary rollout

---

## 17. Terraform ownership model

### 17.1 Shared infra repository creates

- ACR
- Container Apps Environment
- PostgreSQL Flexible Server
- Log Analytics
- Key Vault
- network, DNS, and other common platform resources

### 17.2 Registry repository Terraform creates

- registry Container App
- registry-specific role assignments
- registry service configuration wiring

### 17.3 Registry repository should consume shared outputs

Preferred options:
- `terraform_remote_state`
- pipeline-provided variables

### 17.4 Do not duplicate shared infra creation

The registry service Terraform must not independently create shared platform foundations.

---

## 18. Security and authentication model

### 18.1 Two auth surfaces

The registry exposes two logical surfaces:

#### Runtime read API
- used by shell
- read-only
- audience dedicated to runtime
- role: `registry.runtime.read`

#### Admin/write API
- used by CI/CD and platform admins
- write/activate operations
- audience dedicated to admin
- roles:
  - `registry.release.write`
  - `registry.release.activate`

### 18.2 Entra ID model

Recommended logical identity model:

- runtime audience: `api://portal-registry-runtime`
- admin audience: `api://portal-registry-admin`

### 18.3 Feature scope

The registry should validate that a pipeline can only publish for its own feature.

Example claim:
```json
{
  "feature_keys": ["orders"]
}
```

### 18.4 Important division of responsibility

Registry authorization decides:
- may caller read runtime manifests?
- may caller publish release?
- may caller activate release for target feature?

Shell authorization decides:
- should current user see the feature in nav?
- do feature flags or claims allow rendering?

Feature API authorization decides:
- may user perform the business action?

### 18.5 Local development authentication (`AUTH_DISABLED`)

When `AUTH_DISABLED=true` (default in `.env.example`), `get_principal_from_request` returns a synthetic principal with all registry roles and wildcard feature scope. **Do not use this mode outside local development.**

When `AUTH_DISABLED=false`, callers must send `Authorization: Bearer <token>`. The reference implementation includes **mock** JWT decoding for development only (`app/core/security.py`):

- `shell-read-token` — runtime read audience and `registry.runtime.read` role.
- `pipeline-write-token` — admin audience, write/activate roles, and `feature_keys` limited to `orders` (used to test pipeline scope without Entra).

Production should replace `_mock_decode_for_dev` with real Entra validation and JWKS.

---

## 19. CI/CD model

### 19.1 Registry service repository pipeline

Registry service pipeline should:

1. run lint and tests (this repo includes a **pytest** suite under `tests/`; the current `registry-release.yml` workflow runs a Python import check — extend it with `pytest tests/` and a Postgres **service** job or shared test database as you mature CI)
2. build container image
3. push image to shared ACR
4. deploy registry Container App
5. run database migrations
6. smoke test `/health` (see `scripts/smoke_test.sh` and `REGISTRY_BASE_URL`)
7. optionally smoke test runtime endpoint

### 19.2 Feature repository pipeline interaction with registry

Feature pipeline should:

1. build frontend and backend
2. deploy feature-specific artifacts
3. run feature smoke tests
4. create final manifest
5. publish candidate release to registry
6. activate release based on environment policy

---

## 20. Rollback strategy

### 20.1 Registry service rollback
Use Container Apps revisions to rollback registry application code.

### 20.2 Feature release rollback
Use registry activation to point shell back to a previous active feature release.

This is one of the biggest benefits of the registry.

---

## 21. Observability

The registry service must have:

- structured application logging
- request correlation
- audit logging for publish/activate operations
- health endpoint
- metrics if available
- revision visibility in deployment logs

Recommended metadata to include in logs:
- actor
- feature key
- version
- environment
- request ID
- operation name

---

## 22. Testing strategy

### 22.1 What exists in this repository

- **`tests/`** — Pytest layout: `conftest.py` provides a PostgreSQL engine (skips DB-backed tests if the server is unavailable), truncates app tables between tests, and overrides FastAPI `get_db` for HTTP tests.
- **Unit-style tests** — Pydantic manifest schema, `ManifestValidator`, security helpers (`Principal`, roles, feature scope), config helpers, `get_db` session close behavior.
- **Integration tests** — `ReleaseService` / `ActivationService` / `RuntimeService` / `AuditService` against a real Postgres; API tests for publish, activate, runtime features, validation HTTP status codes, and pipeline feature-scope denial.

Run locally (Postgres up, schema migrated):

```bash
PYTHONPATH=. alembic upgrade head
PYTHONPATH=. pytest tests/ --cov=app --cov-report=term-missing
```

Optional: `TEST_DATABASE_URL` overrides the default `postgresql+psycopg://registry:registry@127.0.0.1:5433/portal_registry`.

Use the **same virtualenv** as `pip install -r requirements.txt` so `psycopg` is available when integration tests connect.

### 22.2 Recommended additions

- Contract tests for stable runtime JSON shape vs shell consumers.
- CI job with a Postgres service container and `pytest` before image build.

### 22.3 Deployment smoke tests

- `/health` returns 200 (`scripts/smoke_test.sh`)
- publish candidate release in test environment
- activate test release
- runtime endpoint returns expected manifest

---

## 23. Operational guardrails

- do not activate before verification
- do not hardcode feature URLs in shell
- do not allow one feature pipeline to update another feature
- do not delete previous release metadata aggressively
- do not let runtime endpoint return candidate releases
- do not put shared infra creation in service repo Terraform

---

## 24. Local development guidance

### 24.1 Local app run

- **Postgres**: easiest path is `docker compose up -d db` (see `docker-compose.yml`: database `portal_registry`, user/password `registry`, host port **5433**).
- **`AUTH_DISABLED=true`**: only for local development (see §18.5).
- **Migrations**: run `alembic upgrade head` before first API use (included in `scripts/run_local.sh`).
- **Sample data**: optional `scripts/seed_local.py` (or uncomment the seed lines in `run_local.sh`) inserts active-style rows for local shell testing.

### 24.2 Local startup sequence (automated)

1. Create a Python virtual environment and `pip install -r requirements.txt`.
2. Ensure `.env` exists (`cp .env.example .env` or let `run_local.sh` copy it).
3. Run **`./scripts/run_local.sh`** — starts Compose Postgres, waits for `pg_isready`, runs Alembic, starts **Uvicorn** at **http://0.0.0.0:8010** (OpenAPI at `/docs`).

### 24.3 Manual sequence

1. `docker compose up -d db`
2. `PYTHONPATH=. alembic upgrade head`
3. `PYTHONPATH=. uvicorn app.main:app --reload --host 0.0.0.0 --port 8010`
4. `curl -s http://localhost:8010/health`

---

## 25. Production readiness checklist

- runtime/admin audience split defined
- feature scope enforcement implemented
- migration process automated
- registry app deployed on Container Apps
- ACR pull role assigned
- runtime endpoint smoke tested
- audit logging enabled
- rollback path documented
- Terraform boundary aligned to shared/common repo model

---

## 26. Summary

The registry service is the platform control point that makes independent feature deployment viable.

The most important design principles are:

1. the registry decides what is live
2. the shell discovers features dynamically through the registry
3. service repo Terraform must only own service-specific artifacts
4. shared infrastructure belongs in the common platform repo
5. publish and activate are separate actions
6. security is split between runtime reads and admin writes
7. rollback must be fast and mostly configuration-driven

This repository includes a reference FastAPI implementation and tests aligned to these principles. Operational commands and configuration tables are maintained in the root **README.md** alongside this guide.
