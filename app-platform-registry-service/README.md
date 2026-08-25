# Portal Registry Service

FastAPI service that stores feature release manifests, serves **active** manifests to the shell by environment, and records publish/activate **audits**. This repo is a reference implementation aligned with the platform registry model.

**Full design and governance:** [doc/REGISTRY_SERVICE_ENGINEERING_GUIDE.md](doc/REGISTRY_SERVICE_ENGINEERING_GUIDE.md)

## Requirements

- Python **3.11+** (3.12 used in CI-style setups)
- **Docker** (for local PostgreSQL via Compose)
- Dependencies in `requirements.txt` (includes `psycopg` for PostgreSQL)

## Quick start

```bash
cd platform-registry-service
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp -n .env.example .env      # optional; run_local.sh also copies if missing
./scripts/run_local.sh
```

This script:

1. Starts Postgres (`docker compose up -d db`) on host port **5433**
2. Waits for readiness, runs **`alembic upgrade head`**
3. Starts the API with **Uvicorn** at **http://localhost:8010**

Optional sample data: uncomment the seed lines in `scripts/run_local.sh`, or run:

```bash
PYTHONPATH=. python scripts/seed_local.py
```

(Use a DB that already has the schema from Alembic.)

## Configuration

Environment variables are loaded from `.env` (see [.env.example](.env.example)). Important fields:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLAlchemy URL, e.g. `postgresql+psycopg://registry:registry@localhost:5433/portal_registry` |
| `AUTH_DISABLED` | When `true`, all registry roles are granted (local dev only). |
| `ALLOWED_FRONTEND_HOSTS` / `ALLOWED_API_HOSTS` | Comma-separated hostnames allowed in manifest URLs (publish validation). |
| `SHELL_READ_AUDIENCES` / `PIPELINE_WRITE_AUDIENCES` | JWT audience allow lists when auth is enabled. |

The DB engine is created **lazily** on first use (`app/db/session.py`), so importing the app does not require a running database.

## HTTP API (summary)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness / build identity |
| GET | `/api/runtime/features?environment=…` | Active manifests for that environment (requires runtime read role). |
| POST | `/api/releases` | Publish a candidate release manifest (requires release write + feature scope). |
| POST | `/api/admin/features/{feature_key}/versions/{version}/activate?environment=…` | Activate a version (requires activate role). |

OpenAPI: **http://localhost:8010/docs** when the app is running.

### Manifest: `authorization` vs `auth`

- **`authorization`** — feature-level hints for the shell (required permissions and flags). Validated on publish; stored in `releases.authorization_json`.
- **`auth`** — how the feature expects the shell to handle **authentication / token forwarding** toward the feature API (mode, token strategy, dev modes, etc.). Optional on ingest: defaults come from `AuthSchema` in `app/schemas/manifest.py`. Stored in **`releases.auth_json`** (see migration `0002_add_release_auth_json`). The runtime response includes both blocks so the shell can apply the same policy for active features.

## Tests

Integration tests expect **PostgreSQL** with the migrated schema (same defaults as Compose: user/password/db `registry` / `portal_registry`, port **5433**).

```bash
docker compose up -d db
PYTHONPATH=. alembic upgrade head
PYTHONPATH=. pytest tests/ --cov=app --cov-report=term-missing
```

Override the DB URL for tests:

```bash
export TEST_DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
PYTHONPATH=. pytest tests/
```

If Postgres is unreachable, tests that need a database are **skipped**; pure unit tests (schemas, manifest validator, security with mocks) still run.

Use this repository’s virtualenv when running pytest so `psycopg` and other deps resolve correctly (avoid pointing `pytest` at another project’s `.venv`).

## Layout

| Path | Role |
|------|------|
| `app/` | FastAPI app: `main.py`, `api/`, `core/`, `db/`, `schemas/`, `services/` |
| `migrations/` | Alembic versions |
| `tests/` | Pytest suite (`conftest.py`, factories, API and service tests) |
| `doc/` | Engineering guide |
| `infra/` | Registry-scoped Terraform |
| `scripts/` | `run_local.sh`, `seed_local.py`, image build, deploy, migrations, smoke test |

Do **not** commit `.venv/`, `__pycache__/`, or `*.pyc` — they are listed in `.gitignore` and are recreated locally.
