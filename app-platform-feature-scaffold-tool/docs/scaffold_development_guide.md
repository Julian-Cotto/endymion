# Feature Scaffold Tool — Development Guide

## Purpose

The **Feature Scaffold Tool** generates production-oriented feature repositories for the application platform. It enforces architecture consistency, manifest-driven design, deployment stubs, and the registry integration contract. It also supports **incremental updates** via `plan` / `apply` and **`scaffold.metadata.json`** so existing repos can be reconciled with the current template set.

**Example:** `create` with `examples/orders-feature.json` and `--output-dir ./out` produces `out/feature-orders/` with `frontend/`, `backend/`, `jobs/`, `workers/`, `listeners/` (as configured), `contracts/feature-manifest.json`, **`scaffold.metadata.json`**, CI, scripts, and infra templates.

**Operator-oriented docs:** the repository **[README.md](../README.md)** has install steps, CLI flags, exit codes, and a **minimal** and **rich** `feature.json` example. This guide focuses on implementation and contribution.

---

## Python and virtualenv

Use a **real CPython** from the OS (or a toolchain you trust) to create `.venv`. Some integrated terminals resolve `python3` to the **Cursor AppImage**; `python -m venv` then fails or leaves a broken tree (missing `bin/activate`, `pip`, or `python` symlinks pointing at the AppImage).

**Check the interpreter** (same shell you will use for `venv`):

```bash
type python3
python3 -c "import sys; print(sys.executable)"
```

`sys.executable` should be a normal binary under `/usr/bin/` (or similar), not `Cursor-*.AppImage`. If it is the AppImage, use an **external terminal** or fix `PATH` so `/usr/bin/python3` wins, then recreate the venv.

**Create the project venv** (from the repository root):

```bash
cd /path/to/feature-scaffold-tool
rm -rf .venv
/usr/bin/python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e ".[dev]"
```

On Fedora you can use `/usr/bin/python3.12` (or whatever `rpm -q python3` reports) if that is the interpreter you standardize on.

**Sanity checks** after `venv`:

```bash
test -f .venv/bin/activate && echo "venv OK"
ls -l .venv/bin/python3
```

`python3` inside `.venv/bin/` should resolve **inside** the virtualenv, not to a Cursor AppImage.

**Alternatives:** `uv venv` then `uv pip install -e ".[dev]"`, or a one-off `python3 -m pip install --user -e ".[dev]"` if you prefer not to use a venv (installs into your user site-packages).

### Python dependencies (this repo)

Install the package in editable mode so `python -m feature_scaffold.cli` resolves imports:

```bash
pip install -e ".[dev]"
```

**Authoritative list:** `pyproject.toml` `[project] dependencies` and `[project.optional-dependencies] dev`.

Runtime dependencies in `pyproject.toml` include **Jinja2**, **jsonschema**, **Pydantic**, **FastAPI**, **Uvicorn**, **PyJWT**, etc.; the **generator and CLI** primarily use the standard library plus **Jinja2** and **jsonschema** for templates and manifest validation. Generated app code (in output repos) uses the web stack according to those pins.

---

## High-Level Responsibilities

1. Parse and validate feature JSON → `ScaffoldConfig`
2. Normalize names and derived flags → `NormalizedScaffoldConfig`
3. Build a **`PlannedFile`** list (paths, templates, optional **`policy`**)
4. Render Jinja2 templates (`[[ ]]` / `{% %}` / `[# #]`)
5. **create:** write a new repo; emit **`scaffold.metadata.json`** from `build_scaffold_metadata()`
6. **plan:** compute **CREATE / REPLACE / MODIFIED / SKIP / ORPHAN** without writing
7. **apply:** update files with optional prompts, dry-run, and version-upgrade handling

---

## CLI (current)

Entry: `python -m feature_scaffold.cli` with positional **`command`**: `create` | `plan` | `apply`.

| Command | Requires | Notes |
|---------|----------|--------|
| `create` | `--config` | `--output-dir` (default `.`); optional `--templates-dir` (defaults to packaged `src/feature_scaffold/templates`) |
| `plan` | `--config`, `--repo` | Optional `--templates-dir`; `--json`, `--diff`, `--fail-on-modified`, `--fail-on-orphan`, `--fail-on-version-mismatch`, `--upgrade`, `--upgrade-preview` |
| `apply` | `--config`, `--repo` | Optional `--templates-dir`; `--interactive`, `--non-interactive`, `--dry-run`, `--upgrade`, `--fail-on-version-mismatch` |

`--repo` must point at the generated feature repository root (`feature-<kebab(feature_name)>` alongside the parent implied by the config), or **plan** / **apply** behavior will not match expectations.

**plan** builds expected content for **`scaffold.metadata.json`** with `build_scaffold_metadata()` (not the small `.j2` stub alone) so diffs match **apply**.

Exit codes (`src/feature_scaffold/exit_codes.py`):

| Constant | Value | Typical use |
|----------|------:|-------------|
| `SUCCESS` | 0 | Normal completion |
| `MODIFIED_FILES` | 2 | e.g. apply aborted in `--non-interactive` when managed files differ |
| `VERSION_MISMATCH` | 3 | Scaffold version / migration expectations |
| `INVALID_CONFIG` | 4 | Defined; reserved for invalid configuration paths |
| `ORPHAN_FILES` | 5 | Unexpected tracked files vs plan |
| `INTERNAL_ERROR` | 10 | Defined; reserved for unexpected failures |

---

## Project structure

```text
src/feature_scaffold/
├── cli.py                  → create / plan / apply
├── generator.py            → create: render + write; metadata at end
├── planners.py             → PlannedFile plan (policies where needed)
├── planner_diff.py         → compute_plan_diff
├── metadata.py             → build_scaffold_metadata
├── migrations.py           → migration registry + helpers
├── version.py              → SCAFFOLD_VERSION (repo metadata + mismatch checks)
├── exit_codes.py           → process exit codes
├── file_writer.py
├── template_engine.py      → Jinja: [[ ]], [# #]; blocks {% %}
├── manifest_builder.py
├── manifest_validator.py
├── models.py               → ScaffoldConfig, PlannedFile, FilePolicy, …
├── normalizers.py
├── validators.py
└── templates/
    ├── common/
    ├── contracts/
    ├── frontend/
    ├── backend/            # includes app/, platform/{database,storage,cache,…}, tests/, …
    ├── jobs/
    ├── workers/
    ├── listeners/
    ├── scripts/
    ├── github/
    ├── infra/
    └── docs/
```

Optional capability scaffolding (when enabled in feature JSON under `capabilities`) adds paths such as `backend/app/platform/database/`, `…/storage/`, `…/cache/`, Alembic files, infra variables, and extra docs (e.g. `docs/database-capability.md`). See **`planners.py`** for the exact `PlannedFile` list.

---

## Feature JSON (overview)

Authoritative shapes live in **`src/feature_scaffold/models.py`** (`ScaffoldConfig`) and **`cli.py`** (`_load_config` normalizes nested JSON). See **[README.md](../README.md)** for field tables and copy-paste examples.

| Area | Notes |
|------|--------|
| **`frontend` / `backend`** | Enable flags, `api_base_path`, shell integration. |
| **`auth`** | `mode`, `shell_auth_required`, `token_forwarding`, `allowed_dev_modes`, `roles`, `backend_token_strategy`. |
| **`registry`** | `mode` (`rest` / `file` / `none`), manifest publish. |
| **`scheduled_jobs`**, **`event_driven_jobs`**, **`event_listeners`** | Arrays; names unique across all three. |
| **`events`** | `publishes` / `consumes` contract lists. |
| **`capabilities`** | **`database`** (PostgreSQL / Snowflake, `targets`, ORM, migrations), **`blob_storage`**, **`cache`** (memory / Redis). |
| **`deployment`** | **`api`** (container app, port, …), **`jobs`** and **`listeners`** arrays for multi-target Azure / workflow hints. |
| **`developer_experience`** | `include_docs`, `include_tests`, `include_scripts`. |

`normalize_config()` flattens capabilities and other flags into **`NormalizedScaffoldConfig`** (e.g. `database_enabled`, `postgres_migrations_enabled`, `blob_storage_enabled`, `redis_enabled`) for templates and **`planners.py`**.

---

## Execution flows

### create

```text
Load JSON → validate → normalize → build_file_plan
  → for each PlannedFile (skip scaffold.metadata.json in loop):
      render / literal / manifest → write (respect create_if_missing)
  → write scaffold.metadata.json via build_scaffold_metadata(plan)
```

### plan

```text
Load JSON → normalize → plan → render expected bytes in memory
  → compute_plan_diff(repo, plan, rendered_by_path)
  → print or JSON; optional fail flags / upgrade-preview
```

### apply

```text
Load JSON → version check → normalize → plan → diff
  → optional non-interactive fail on MODIFIED
  → optional interactive prompts for MODIFIED
  → write files (create_if_missing, interactive skips)
```

---

## `scaffold.metadata.json`

Written on **create**; updated on **apply**. Fields include:

- **`scaffoldVersion`** — compared to `version.SCAFFOLD_VERSION`
- **`featureKey`**, **`repoName`**, **`manifestVersion`**
- **`managedFiles`** — map of `target_path` → **`replace`** | **`create_if_missing`** | **`manual`**
- **`appliedMigrations`** — keys from `migrations.MIGRATIONS`

**ORPHAN:** path listed in `managedFiles`, file still on disk, but path not in current plan.

---

## `PlannedFile.policy` (`FilePolicy`)

Default **`replace`**: scaffold output is authoritative; drift shows **MODIFIED** when disk ≠ rendered.

**`create_if_missing`**: write only if missing; if present, **SKIP** in diff. Used for selected frontend/backend files and some job/worker/listener handlers so teams can customize without constant drift.

When adding files, pick policy deliberately and add planner + diff tests if non-default.

---

## Migrations

`migrations.py` lists **`ScaffoldMigration`** entries (version, key, description). **`MIGRATION_TRANSFORMS`** can hold optional metadata transforms. Helpers: `get_migrations_since`, `get_pending_migrations`, `apply_migrations`. **`--upgrade`** / **`--upgrade-preview`** tie into version mismatch messaging.

---

## Template system

Templates under `src/feature_scaffold/templates/`. Expressions use **`[[ ... ]]`** (not `{{ }}`). **`{% ... %}`** remains standard for `if` / `for`. GitHub Actions `${{ ... }}` and JSX `{{ ... }}` in `.j2` files are **not** Jinja—leave them as-is.

`StrictUndefined` catches missing context keys.

**Render context (create):** `generator._build_template_context(normalized)` supplies, among other fields:

- **`names`** — `NormalizedNames` as a `dict` (`feature_key`, `base_path`, `api_base_path`, …).
- **`ports`** — `SimpleNamespace` from **`generator.local_dev_ports(feature_key)`**: local **backend / frontend / bootstrap** defaults (**8100 / 3200 / 3050** for most features; **8200 / 3300 / 3060** when `feature_key == "catalog"`). These must match the defaults embedded in **`templates/scripts/run-local.sh.j2`** (and friends) so two sample features can run together without port clashes.
- **Auth shortcuts** — `auth_mode`, `auth_shell_required`, `auth_token_forwarding`, `auth_allowed_dev_modes`, `auth_roles` (aliases for templates; the normalized config still holds the canonical fields).

Per-file overrides come from `PlannedFile.template_context` merged into the base context.

---

## Adding a new generated file

1. Add `templates/.../your-file.j2` (or `literal_content` in planner).
2. Register **`PlannedFile(...)`** in `planners.py` (and **`policy`** if not `replace`).
3. Add tests: planner path set + generator filesystem check (+ diff/apply if policy matters).

Example planner assertion:

```python
from feature_scaffold.models import ScaffoldConfig
from feature_scaffold.normalizers import normalize_config
from feature_scaffold.planners import build_file_plan

def test_plan_includes_script() -> None:
    cfg = ScaffoldConfig(feature_name="orders", display_name="Orders", base_path="/orders")
    paths = {p.target_path for p in build_file_plan(normalize_config(cfg))}
    assert "scripts/new-script.py" in paths
```

---

## Manifest layout (generated repo)

```text
contracts/feature-manifest.json
manifest.schema.json
scaffold.metadata.json
build/
  feature-manifest.resolved.json
  registry-payload.json
```

Lifecycle in repo: `scripts/render-manifest.py` → `validate-manifest.py` → `render-registry-payload.py`.

---

## Testing

Tests live in `tests/`. Besides generator/planner/validator/manifest/deploy/registry/render contracts, there are **incremental** tests, for example:

```text
tests/test_incremental_scaffold.py
tests/test_plan_diff_output.py
tests/test_plan_json_output.py
tests/test_orphan_detection.py
tests/test_modified_detection.py
tests/test_fail_on_modified.py
tests/test_fail_on_orphan.py
tests/test_fail_on_version_mismatch.py
tests/test_upgrade_mode.py
tests/test_apply_command.py
tests/test_apply_non_interactive.py
tests/test_apply_interactive.py          # placeholder (TTY)
tests/test_apply_interactive_metadata.py # placeholder
```

**pytest** (`pyproject.toml`):

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src", "."]
norecursedirs = ["out", ".venv", "node_modules", "dist", "build", ".gitignore"]
addopts = ["--ignore=out"]
```

`pythonpath` puts `src` and the repo root on the import path so `import feature_scaffold` and `from tests.helpers import cli_python_executable` work without setting `PYTHONPATH`. `--ignore=out` avoids collecting tests inside generated trees under `out/`.

**CLI subprocess tests** use **`tests/helpers.py`** → `cli_python_executable()` (prefer `.venv/bin/python`, then `python3` on `PATH`) because embedded test runners may set `sys.executable` to a non-Python binary. Override with **`FEATURE_SCAFFOLD_TEST_PYTHON`**.

Run from the **repository root** with an editable install (recommended):

```bash
python -m pytest
python -m pytest tests/test_generator.py -q
```

---

## Common tasks

```bash
python -m feature_scaffold.cli create --config examples/orders-feature.json --output-dir ./out
python -m feature_scaffold.cli plan  --config examples/orders-feature.json --repo ./out/feature-orders
python -m feature_scaffold.cli apply --config examples/orders-feature.json --repo ./out/feature-orders
```

Generated repo: `./scripts/bootstrap.sh`, `validate.sh`, `run-local.sh`. **`run-local`** starts backend, frontend (if any), the **bootstrap mock**, then manifest render/validate and (unless `PUBLISH_LOCAL_ENABLED=false`) registry publish/activate against **`REGISTRY_BASE_URL`**.

Default ports are **feature-key–specific** in the generated script (e.g. **8100 / 3200 / 3050** vs **8200 / 3300 / 3060** for `catalog`); override when needed, e.g. `BACKEND_PORT=8001 ./scripts/run-local.sh`. The mock listens on **`BOOTSTRAP_PORT`** (see `serve-bootstrap-mock.py` template).

---

## Design principles

1. **Determinism** for `replace` outputs at a given tool + config version; `create_if_missing` allows intentional local drift.
2. **Scaffold owns layout** — extend `planners.py` + templates, not one-off repos.
3. **Templates encode behavior**; contracts live in schema + `docs/registry-contract.md`, `docs/shell-consumption-contract.md`, etc.
4. **Incremental flow is first-class** — metadata + diff + apply.

---

## Resolved manifest and registry payload

- **`build_feature_manifest()`** (`manifest_builder.py`) defines the JSON shape for **`contracts/feature-manifest.json`** (`featureKey`, `frontend`, `backend`, `auth`, `registry`, `events`, `workers` with `scheduledJobs` / `eventDrivenJobs` / `eventListeners` name lists).
- **`scripts/render-manifest.py`** (generated) produces **`build/feature-manifest.resolved.json`** (environment, URLs, `authorization`, etc.).
- **`scripts/render-registry-payload.py`** (generated) emits **`build/registry-payload.json`**: `{ featureKey, version, environment, manifest }` — the full resolved manifest is nested under **`manifest`** (no duplicate top-level `auth`). See **`docs/registry-contract.md`**.

---

## What not to add

Business logic, secrets, registry server, or shell runtime—only contracts, templates, and tooling scripts.

---

## Versioning

- **`pyproject.toml` `version`** — Python package release.
- **`version.SCAFFOLD_VERSION`** — stored in each repo’s `scaffold.metadata.json`; drives mismatch warnings and migration preview.

Bump and document when generated output or metadata contract changes in breaking ways.

---

## Future (outside this repo)

Hosted registry service, shell implementation, feature-flag orchestration, etc. The scaffold can keep emitting `build/registry-payload.json` for CI to call external systems.

---

## Summary

The tool is the **platform enforcer**, **architecture generator**, and **reconciliation engine** for feature repos. Trace any generated path from `examples/*.json` → `planners.py` → `templates/`; use **plan** / **apply** to evolve existing checkouts safely.
