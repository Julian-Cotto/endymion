# feature-scaffold-tool

Scaffolds a platform-integrated feature repository with:

- React + Vite microfrontend (optional)
- FastAPI backend (optional)
- Scheduled jobs, event-driven workers, event listeners
- **Platform capabilities (optional):** PostgreSQL and/or Snowflake, Azure Blob–style storage, memory/Redis cache; Alembic/migrations when Postgres + migrations are enabled
- Feature manifest, registry-oriented scripts, CI/CD, Terraform skeleton
- **Per-target deployment hints:** API plus separate **jobs** and **listeners** container targets (see `deployment` in feature JSON)
- **Incremental updates:** `plan` / `apply` against an existing repo, with `scaffold.metadata.json` tracking managed files and scaffold version

The CLI reads a **feature JSON** file, validates it, then **creates** a new repo or **plans** / **applies** changes to an existing one.

---

## Install

Python **3.11+** and a virtual environment:

```bash
cd feature-scaffold-tool
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

Run:

```bash
python -m feature_scaffold.cli create --config examples/orders-feature.json --output-dir ./out
```

For **pytest**, `[tool.pytest.ini_options] pythonpath = ["src", "."]` in `pyproject.toml` loads the package and `tests.helpers` without extra env vars. Use `PYTHONPATH=src` only if you run ad-hoc scripts without that config.

---

## Commands

| Command | Purpose |
|--------|---------|
| **create** | New repo under `--output-dir` (default `.`). |
| **plan** | Diff existing `--repo` vs current templates; no writes. |
| **apply** | Write updates into existing `--repo`. |

All commands require `--config` (feature JSON). **plan** and **apply** require `--repo` (path to the generated `feature-*` root).

Shared flags: `--templates-dir` (override template root).

### plan

- `--json` — machine-readable summary and change list
- `--diff` — unified diff for **MODIFIED** files
- `--fail-on-modified` — exit `2` if any managed file differs from rendered content
- `--fail-on-orphan` — exit `5` if a path in `managedFiles` still exists but is no longer in the plan
- `--fail-on-version-mismatch` — exit `3` if repo `scaffoldVersion` ≠ tool `SCAFFOLD_VERSION` (unless `--upgrade` / preview path applies)
- `--upgrade` — used with version handling
- `--upgrade-preview` — print migration preview when versions differ (returns after preview)

### apply

- `--interactive` — prompt before overwriting **MODIFIED** files (not `scaffold.metadata.json`)
- `--non-interactive` — exit `2` if **MODIFIED** files would be overwritten without approval
- `--fail-on-version-mismatch` — same idea as **plan**
- `--upgrade` — run upgrade/migration metadata path
- `--dry-run` — print intended writes only

### Exit codes

Defined in `src/feature_scaffold/exit_codes.py`:

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Modified managed files (CI / `--non-interactive`) |
| 3 | Scaffold version mismatch |
| 4 | Invalid configuration (reserved) |
| 5 | Orphan managed files |
| 10 | Internal error (reserved) |

---

## Usage examples

```bash
# New repo
python -m feature_scaffold.cli create \
  --config examples/orders-feature.json \
  --output-dir ./out

# Preview drift
python -m feature_scaffold.cli plan \
  --config examples/orders-feature.json \
  --repo ./out/feature-orders

python -m feature_scaffold.cli plan \
  --config examples/orders-feature.json \
  --repo ./out/feature-orders \
  --json

# CI: fail on local edits or orphans
python -m feature_scaffold.cli plan \
  --config examples/orders-feature.json \
  --repo ./out/feature-orders \
  --fail-on-modified --fail-on-orphan

# Apply updates (repo path must match config: .../feature-<kebab(feature_name)>)
python -m feature_scaffold.cli apply \
  --config examples/orders-feature.json \
  --repo ./out/feature-orders

python -m feature_scaffold.cli apply \
  --config examples/orders-feature.json \
  --repo ./out/feature-orders \
  --dry-run
```

---

## Feature JSON (`*-feature.json`)

Maps to `ScaffoldConfig` in `src/feature_scaffold/models.py`; validated by `validators.py`. The **rich example** below mirrors **`examples/orders-feature.json`**; additional samples are listed after it.

### Top-level

| Field | Required | Default | Notes |
|-------|----------|---------|--------|
| `feature_name` | yes | — | Drives `feature_key` (kebab) and folder `feature-<key>`. |
| `display_name` | yes | — | Human title. |
| `base_path` | yes | — | URL prefix; must start with `/`. |
| `description` | no | `""` | |
| `version` | no | `"0.1.0"` | Feature manifest version (in `contracts/feature-manifest.json`). |

### `frontend`

| Field | Default | Values |
|-------|---------|--------|
| `enabled` | `true` | |
| `framework` | `"react-vite"` | `"react-vite"` |
| `shell_integration` | `true` | |

### `backend`

| Field | Default | Values |
|-------|---------|--------|
| `enabled` | `true` | |
| `framework` | `"fastapi"` | `"fastapi"` |
| `api_base_path` | `"/api"` | |

### `auth`

Loaded feature JSON is normalized in `cli._load_config()` before `ScaffoldConfig` is built. If you construct `ScaffoldConfig` in Python without that path, see `AuthConfig` in `models.py` for dataclass defaults.

| Field | Default (JSON via CLI, field omitted) | Notes |
|-------|----------------------------------------|--------|
| `mode` | `"mock"` | `"entra"`, `"mock"`, `"none"` |
| `shell_auth_required` | `true` | Whether the shell must supply auth context. |
| `token_forwarding` | `true` if `mode == "entra"`, else `false` | Forward tokens toward the backend. |
| `allowed_dev_modes` | `["mock"]` | Dev-only auth modes allowed in local tooling. |
| `roles` | `[]` | Role names surfaced in generated docs/contracts; set explicitly in JSON when needed. |
| `backend_token_strategy` | `"forwarded-bearer"` if `mode == "entra"`, else `"none"` | e.g. `forwarded-bearer`, `shell-session`, `none` — align with your platform. |

### `registry`

| Field | Default | Values |
|-------|---------|--------|
| `enabled` | `true` | |
| `mode` | `"rest"` | `"rest"`, `"file"`, `"none"` |
| `manifest_publish` | `true` | |

### `capabilities`

Optional **database**, **blob storage**, and **cache** blocks. When enabled, the generator adds backend (and sometimes worker/listener) wiring, env examples, and docs. See `examples/orders-feature.json` for a full shape.

| Block | Role |
|-------|------|
| `database` | `enabled`, `targets` (`api`, `jobs`, `listeners`, …), `providers.postgresql` (`enabled`, `orm`, `migrations`), `providers.snowflake` (`enabled`). |
| `blob_storage` | `enabled`, `provider` (e.g. `azure_blob`), `targets`. |
| `cache` | `enabled`, `targets`, `providers.memory` / `providers.redis` (`enabled`). |

### `scheduled_jobs` (array)

Per job: `name` (required), `description`, `schedule` (required if job listed), `entrypoint`, `retry_policy` (`max_retries`, `backoff`). Names must be unique across jobs, workers, and listeners.

### `event_driven_jobs` (array)

`trigger`: `kind` (`topic-subscription` | `queue`), plus `topic`+`subscription` or `queue` as required. Unique `name`.

### `event_listeners` (array)

`name`, `event_name` (dotted lowercase pattern), `payload_schema`, etc. Unique `name`.

### `events`

`publishes` / `consumes`: arrays of `{ "name", "schema" }`. Same event name must not appear in both lists.

### `deployment`

Structured **API** and optional **jobs** / **listeners** targets (not legacy string enums only):

| Field | Role |
|-------|------|
| `api` | e.g. `container_app_name`, `port`, `runtime` — API/container app hints for Terraform and workflows. |
| `jobs` | Array of `{ "name", "container_app_name", … }` for job/worker deployments. |
| `listeners` | Array of listener deployment targets. |

Terraform and GitHub Actions templates consume these names. See `examples/orders-feature.json`.

### `developer_experience`

`include_docs`, `include_tests`, `include_scripts` (all default `true`).

### Validation summary

At least one of: `frontend.enabled`, `backend.enabled`, or non-empty `scheduled_jobs` / `event_driven_jobs` / `event_listeners`. See `validators.py` for full rules.

### Minimal example

Smallest valid shape (API-only, no UI):

```json
{
  "feature_name": "healthcheck",
  "display_name": "Healthcheck",
  "base_path": "/healthcheck",
  "frontend": { "enabled": false },
  "backend": { "enabled": true, "api_base_path": "/api/healthcheck" }
}
```

### Rich example (full stack)

This matches **`examples/orders-feature.json`**: frontend and backend, Entra-style auth, registry, a scheduled job, an event-driven worker, an event listener, published/consumed contracts, **capabilities** (Postgres + Snowflake, blob storage, Redis cache), and **deployment** hints for API, jobs, and listeners.

```json
{
  "feature_name": "orders",
  "display_name": "Orders",
  "description": "Orders management feature",
  "base_path": "/orders",
  "frontend": {
    "enabled": true,
    "framework": "react-vite",
    "shell_integration": true
  },
  "backend": {
    "enabled": true,
    "framework": "fastapi",
    "api_base_path": "/api/orders"
  },
  "auth": {
    "mode": "entra",
    "shell_auth_required": true,
    "token_forwarding": true,
    "allowed_dev_modes": ["mock"],
    "roles": ["admin", "developer", "reader", "operator"],
    "backend_token_strategy": "forwarded-bearer"
  },
  "registry": {
    "enabled": true,
    "mode": "rest",
    "manifest_publish": true
  },
  "scheduled_jobs": [
    {
      "name": "nightly-reconciliation",
      "description": "Reconcile orders nightly",
      "schedule": "0 2 * * *"
    }
  ],
  "event_driven_jobs": [
    {
      "name": "submit-order",
      "description": "Process submitted orders asynchronously",
      "trigger": {
        "kind": "topic-subscription",
        "topic": "orders",
        "subscription": "submit-order"
      },
      "payload_schema": "SubmitOrderRequested",
      "dead_letter": true,
      "max_concurrency": 4,
      "retry_policy": {
        "max_retries": 5,
        "backoff": "exponential"
      }
    }
  ],
  "event_listeners": [
    {
      "name": "inventory-reserved",
      "description": "Handle inventory reservation events",
      "event_name": "inventory.reserved",
      "payload_schema": "InventoryReserved"
    }
  ],
  "events": {
    "publishes": [
      { "name": "orders.created", "schema": "OrderCreated" }
    ],
    "consumes": [
      { "name": "inventory.reserved", "schema": "InventoryReserved" }
    ]
  },
  "capabilities": {
    "database": {
      "enabled": true,
      "targets": ["api", "jobs", "listeners"],
      "providers": {
        "postgresql": {
          "enabled": true,
          "orm": true,
          "migrations": true
        },
        "snowflake": {
          "enabled": true
        }
      }
    },
    "blob_storage": {
      "enabled": true,
      "provider": "azure_blob",
      "targets": ["api", "jobs"]
    },
    "cache": {
      "enabled": true,
      "targets": ["api", "jobs", "listeners"],
      "providers": {
        "memory": { "enabled": false },
        "redis": { "enabled": true }
      }
    }
  },
  "deployment": {
    "api": {
      "container_app_name": "orders-api",
      "port": 8000
    },
    "jobs": [
      {
        "name": "orders-jobs",
        "container_app_name": "orders-jobs"
      }
    ],
    "listeners": [
      {
        "name": "orders-listeners",
        "container_app_name": "orders-listeners"
      }
    ]
  },
  "developer_experience": {
    "include_docs": true,
    "include_tests": true,
    "include_scripts": true
  }
}
```

**Other samples** (narrower slices of the same schema):

| File | Highlights |
|------|------------|
| `examples/catalog-feature.json` | Catalog-style feature |
| `examples/billing-workers-feature.json` | Worker-heavy / billing-oriented |
| `examples/public-portal-feature.json` | Public portal pattern |

---

## After generation

```bash
cd out/feature-orders
./scripts/bootstrap.sh
./scripts/validate.sh
./scripts/run-local.sh
```

`run-local` starts the backend, frontend (if present), a **bootstrap mock** HTTP server, then renders/validates the manifest and (by default) **publishes** the registry payload to `REGISTRY_BASE_URL`. Override ports when colliding with other services:

| Variable | Default in generated `scripts/run-local.sh` |
|----------|---------------------------------------------|
| `BACKEND_PORT` | **8100** for most features; **8200** when the feature key is **`catalog`** (so orders + catalog dev stacks do not clash). |
| `FRONTEND_PORT` | **3200** (non-catalog) / **3300** (catalog). |
| `BOOTSTRAP_PORT` | **3050** / **3060** (catalog). Mock serves `http://localhost:<BOOTSTRAP_PORT>/bootstrap` (or `BOOTSTRAP_HEALTH_PATH`). |
| `REGISTRY_BASE_URL` | `http://localhost:8010` |
| `PUBLISH_LOCAL_ENABLED` | `true` — set to `false` to skip registry POST/activate when no registry is running. |

Example:

```bash
BACKEND_PORT=8001 BOOTSTRAP_PORT=3051 FRONTEND_PORT=3201 ./scripts/run-local.sh
```

Port defaults are baked in at generate time from `generator.local_dev_ports()` and must stay aligned with `templates/scripts/run-local.sh.j2`.

The shell application is **not** started by this repo. See the generated feature `README.md` for the full local workflow.

Manifest helpers:

```bash
python scripts/render-manifest.py
python scripts/validate-manifest.py
python scripts/render-registry-payload.py
```

---

## Documentation

- [Development guide](docs/scaffold_development_guide.md) — architecture, templates, plan/apply, tests
- [Registry contract](docs/registry-contract.md), [Shell consumption](docs/shell-consumption-contract.md)

---

## Tests

```bash
python -m pytest
```

Subprocess-based tests spawn the CLI with `tests.helpers.cli_python_executable()` (prefers `.venv/bin/python`) so runners where `sys.executable` is not a real interpreter (e.g. some IDE wrappers) still work. Override with `FEATURE_SCAFFOLD_TEST_PYTHON=/path/to/python` if needed.
