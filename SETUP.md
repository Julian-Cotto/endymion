# Endymion — fresh-clone setup

End-to-end instructions for getting the monorepo running from a clean
checkout on **WSL2 Ubuntu** or **Arch Linux**. Covers system prerequisites,
submodules, env files (every file, every path), Docker-backed databases,
and the dev-server launch scripts.

If anything below conflicts with the README in an individual submodule,
the submodule's README wins for that sub-project — this file is the
top-level glue.

---

## 1. What's in the repo

The monorepo wires a "shell" host UI together with multiple feature
front/back-ends. Each sub-project is a Git submodule (except
`document-compliance-*` which currently live as plain in-tree copies).

| Sub-project | Path | Runtime | Default port |
|---|---|---|---|
| Registry service | [app-platform-registry-service/](app-platform-registry-service/) | Python (FastAPI + Alembic) | 8010 |
| Shell bootstrap API | [app-platform-shell-bootstrap-api/](app-platform-shell-bootstrap-api/) | Python (FastAPI) | 8000 |
| Shell (host UI) | [app-platform-shell/](app-platform-shell/) | Node (Vite + React) | 3000 |
| Asset Inventory — API | [feature-asset-inventory-backend/](feature-asset-inventory-backend/) | Python (FastAPI, SQLite) | 8200 |
| Asset Inventory — Web | [feature-asset-inventory-frontend/](feature-asset-inventory-frontend/) | Node (Vite + React) | 3200 |
| Continued Education — API | [feature-continued-education-backend/](feature-continued-education-backend/) | Python (FastAPI, Snowflake/Postgres) | 8300 |
| Continued Education — Web | [feature-continued-education-frontend/](feature-continued-education-frontend/) | Node (Vite + React) | 3300 |
| Document Compliance — API | [document-compliance-backend/](document-compliance-backend/) | Python (FastAPI, Postgres) | 8400 |
| Document Compliance — Web | [document-compliance-frontend/](document-compliance-frontend/) | Node (Vite + React) | 3400 |
| Snowflake client (shared) | [app-platform-snowflake-client/](app-platform-snowflake-client/) | Python library | — |
| Feature scaffold tool | [app-platform-feature-scaffold-tool/](app-platform-feature-scaffold-tool/) | Python CLI | — |

Two Postgres databases run in Docker:

| DB | Image | Port | Used by |
|---|---|---|---|
| `portal_registry` | postgres:16 | 5433 | registry service |
| `document_compliance` | postgres:16 | 5434 | document compliance API |

The Asset Inventory API uses **SQLite on disk** (default
`app-platform.db` next to the service). No external DB needed.

---

## 2. Prerequisites by OS

You need Python 3.11+, Node.js 18+ (LTS), Docker + Compose, Git, and a few
build-time libs for psycopg / openssl.

### WSL2 Ubuntu (22.04 / 24.04)

```bash
# Update + base toolchain
sudo apt update && sudo apt -y upgrade
sudo apt -y install build-essential git curl ca-certificates \
                    pkg-config libssl-dev libffi-dev

# Python 3.11+ (Ubuntu 22.04 ships 3.10 — add deadsnakes if you need 3.11/3.12)
sudo apt -y install python3 python3-venv python3-pip python3-dev

# If on 22.04 and you need Python 3.12:
#   sudo add-apt-repository ppa:deadsnakes/ppa -y
#   sudo apt update
#   sudo apt -y install python3.12 python3.12-venv python3.12-dev

# Node.js 20 LTS (via NodeSource)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt -y install nodejs

# Docker Engine + Compose plugin (rootless-capable). Skip if you're using
# Docker Desktop on Windows with WSL integration enabled.
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo tee /etc/apt/keyrings/docker.asc > /dev/null
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt -y install docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER
# Log out + back in (or `newgrp docker`) so the group takes effect.

# Postgres client libs (only needed if you fall back from psycopg-binary)
sudo apt -y install libpq-dev
```

**WSL2 specifics**:

- Run *inside* the WSL distro, not from PowerShell. The repo should live
  on the **Linux filesystem** (e.g. `~/dev_projects/endymion`), not
  `/mnt/c/...` — Vite + npm I/O is orders of magnitude slower on the
  Windows-mounted side.
- If using Docker Desktop on Windows, enable "Use the WSL 2 based engine"
  + WSL integration for your distro under Settings → Resources → WSL.
  Skip the `apt install docker-ce` block above.
- Vite dev servers bind to `0.0.0.0`; access from Windows at
  `http://localhost:3000` etc. (WSL forwards automatically).

### Arch Linux

```bash
sudo pacman -Syu --needed base-devel git curl openssl libffi \
                          python python-pip \
                          nodejs npm \
                          docker docker-compose \
                          postgresql-libs
# Enable + start the Docker daemon
sudo systemctl enable --now docker.service
sudo usermod -aG docker $USER
# Log out + back in (or `newgrp docker`)
```

Arch ships current Python (3.12+) and Node (LTS-ish) — no extra repos
needed. If you want to pin Node LTS, use `nvm` or `pacman -S nodejs-lts-iron`.

---

## 3. Clone the repo and pull submodules

```bash
git clone <repo-url> endymion
cd endymion
git submodule update --init --recursive
```

If you already cloned without `--recursive`, run the second command after
the fact. Re-pull submodules anytime you switch branches:

```bash
git submodule update --init --recursive --remote
```

The two `document-compliance-*` directories aren't submodules — they
should be present in the parent repo's working tree as-is.

---

## 4. Env files — full cookbook

Every backend service ships a `.env.example` next to its code; copy it
to `.env` and edit the few required values. Frontends use Vite's
`VITE_*` convention and also ship `.env.example`s.

> **One-liner to bootstrap all `.env`s from their examples**
> (`run_all.sh` does this automatically for the platform services on
> first launch, but it doesn't touch the feature services):
>
> ```bash
> for d in app-platform-registry-service app-platform-shell-bootstrap-api app-platform-shell \
>          feature-asset-inventory-backend feature-asset-inventory-frontend \
>          feature-continued-education-backend feature-continued-education-frontend \
>          document-compliance-backend document-compliance-frontend; do
>   [ -f "$d/.env.example" ] && [ ! -f "$d/.env" ] && cp "$d/.env.example" "$d/.env" \
>     && echo "created $d/.env"
> done
> ```

### 4.1. Required env files (by path)

| File | Source | Required-to-edit keys | Notes |
|---|---|---|---|
| [`app-platform-registry-service/.env`](app-platform-registry-service/.env) | copy from `.env.example` | `DATABASE_URL`, `AUTH_DISABLED`, `ALLOWED_FRONTEND_HOSTS`, `ALLOWED_API_HOSTS` | DB URL should point at the Docker Postgres on `:5433`. Defaults in the example work for local dev. |
| [`app-platform-shell-bootstrap-api/.env`](app-platform-shell-bootstrap-api/.env) | copy from `.env.example` | `REGISTRY_BASE_URL=http://localhost:8010`, `AUTH_MODE=mock`, `CACHE_BACKEND=memory` (no Redis required) | `DEV_DEFAULT_ROLES_CSV` controls the default mock roles. |
| [`app-platform-shell/.env`](app-platform-shell/.env) | copy from `.env.example` | `VITE_BOOTSTRAP_URL=http://localhost:8000`, `VITE_AUTH_MODE=mock`, `VITE_MOCK_ACCESS_TOKEN` | Mock token is any string — has to match what the bootstrap-api accepts in mock mode. |
| [`feature-asset-inventory-backend/.env`](feature-asset-inventory-backend/.env) | copy from `.env.example` | `FEATURE_KEY=asset-inventory`, `AUTH_MODE=mock` | SQLite path defaults to a file next to the service; no DB setup needed. Optional integrations (Intune, Meraki, Defender, UPS, FedEx, Lenovo, Dell) all have their own env vars — see § 4.3. |
| [`feature-asset-inventory-frontend/.env`](feature-asset-inventory-frontend/.env) | copy from `.env.example` | `VITE_API_BASE_URL=http://localhost:8200/api/inventory/it`, `VITE_AUTH_MODE=mock` | |
| [`feature-continued-education-backend/.env`](feature-continued-education-backend/.env) | copy from `.env.example` | `APP_ENVIRONMENT=local`, `AUTH_MODE=mock`, `DATABASE_URL` (Snowflake or Postgres) | If you're not connecting to Snowflake, leave Snowflake vars blank and the service runs against SQLite or a local Postgres. |
| [`feature-continued-education-frontend/.env`](feature-continued-education-frontend/.env) | copy from `.env.example` | `VITE_API_BASE_URL=http://localhost:8300/api/education/continued-ed`, `VITE_AUTH_MODE=mock` | |
| [`document-compliance-backend/.env`](document-compliance-backend/.env) | copy from `.env.example` | `APP_ENVIRONMENT=local`, `AUTH_MODE=mock`, `DATABASE_URL=postgresql://compliance:compliance@localhost:5434/document_compliance`, `DB_CREATE_ALL_ON_STARTUP=true` | The Postgres `:5434` must be up (`./scripts/start_db.sh` or its own compose file). |
| [`document-compliance-frontend/.env`](document-compliance-frontend/.env) | copy from `.env.example` | `VITE_API_BASE_URL=http://localhost:8400/api/document-compliance`, `VITE_AUTH_MODE=mock` | |

### 4.2. Auth modes

All services support `AUTH_MODE=mock` (default for local dev — no Entra
ID needed). To switch to real Entra:

- Backend services: set `AUTH_MODE=entra`, plus `ENTRA_TENANT_ID`,
  `ENTRA_CLIENT_ID`, `ENTRA_JWKS_URL` (specific names vary slightly
  per service; see each `.env.example`).
- Shell + feature frontends: set `VITE_AUTH_MODE=entra`,
  `VITE_ENTRA_TENANT_ID`, `VITE_ENTRA_CLIENT_ID`, `VITE_ENTRA_REDIRECT_URI`.

Don't mix modes — every service in the stack should use the same auth
mode at the same time.

### 4.3. Asset Inventory optional integrations

The Inventory backend optionally talks to Intune, Defender, Meraki,
Snowflake, UPS / FedEx tracking, and Lenovo / Dell warranty APIs. **All
of these are off by default** — the service runs fine with just SQLite
and mock auth. To turn one on, set the corresponding env vars (see
`.env.example` for the full list, names start with the vendor prefix:
`INTUNE_*`, `DEFENDER_*`, `MERAKI_*`, `SNOWFLAKE_*`, `UPS_*`, `FEDEX_*`,
`LENOVO_*`, `DELL_*`).

### 4.4. `.env` is gitignored

Never commit `.env` files. The `.env.example` in each sub-project is
the source of truth for what keys exist; copy and edit locally only.

---

## 5. Install dependencies

Each sub-project owns its install step. The run scripts (§ 7) bootstrap
these automatically on first launch — but you can also do them by hand:

### Python backends

For every Python service (registry, bootstrap-api, asset-inventory-backend,
continued-education-backend, document-compliance-backend):

```bash
cd <service-dir>
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

The `feature-continued-education-backend/requirements.txt` includes an
editable install of `../app-platform-snowflake-client` — that resolves
automatically as long as both directories are present at the same parent
level (which is the default after `git submodule update --init`).

### Node frontends

For every frontend (shell, asset-inventory-frontend,
continued-education-frontend, document-compliance-frontend):

```bash
cd <service-dir>
npm install
```

---

## 6. Docker — start the databases

The registry and document-compliance services need Postgres. The Asset
Inventory service uses SQLite and needs nothing.

```bash
# Start both Postgres containers in one shot
./scripts/start_db.sh
```

That script wraps `docker compose up -d` for the two compose files at:

- [`app-platform-registry-service/docker-compose.yml`](app-platform-registry-service/docker-compose.yml) → `portal_registry` on **:5433**
- [`document-compliance-backend/docker-compose.yml`](document-compliance-backend/docker-compose.yml) → `document_compliance` on **:5434**

Verify both are listening:

```bash
docker compose -f app-platform-registry-service/docker-compose.yml ps
docker compose -f document-compliance-backend/docker-compose.yml ps
# Or just check the ports directly:
ss -tln | grep -E '543[34]'
```

To stop:

```bash
docker compose -f app-platform-registry-service/docker-compose.yml down
docker compose -f document-compliance-backend/docker-compose.yml down
```

Data persists in named Docker volumes — re-up gives you the same DB
contents. Wipe with `docker compose down -v` if you need a clean slate.

The registry service runs `alembic upgrade head` on startup, so schema
migrations apply automatically the first time it boots. Document
Compliance uses SQLAlchemy's `create_all` (enabled by
`DB_CREATE_ALL_ON_STARTUP=true` in its `.env`).

### Docker daemon permissions (one-time)

If `docker ps` says `permission denied`, add your user to the `docker`
group (both OSes):

```bash
sudo usermod -aG docker $USER
newgrp docker        # or: log out + log back in
```

---

## 7. Run the dev stack

Five launch scripts at the repo root. They share helpers in
[`scripts/_run_lib.sh`](scripts/_run_lib.sh) — auto-bootstrap deps,
clear stale port binds, tail combined logs in one terminal, and respect
`Ctrl+C` to tear everything down cleanly.

| Script | What it starts | Use when |
|---|---|---|
| `./run_platform.sh` | registry (8010) + bootstrap-api (8000) + shell (3000) | Working on the platform, not features |
| `./run_inventory.sh` | inv-api (8200) + inv-web (3200) | Working on the Asset Inventory feature only |
| `./run_continued_ed.sh` | ce-api (8300) + ce-web (3300) | Working on Continued Education only |
| `./run_doc_compliance.sh` | dc-api (8400) + dc-web (3400) | Working on Document Compliance only |
| `./run_all.sh` | Everything except Document Compliance | Demo-mode / "show me the whole thing" |

The feature scripts assume the platform is running (the shell loads
features via the bootstrap-api at `:8000`). Either run `./run_platform.sh`
first in another terminal, or use `./run_all.sh`.

**Common flags**:

```bash
./run_all.sh                       # full launch, auto-install missing deps
./run_all.sh --with-db             # also `./scripts/start_db.sh` first
./run_all.sh --no-bootstrap        # skip pip install / npm install (faster restarts)
./run_all.sh --skip shell,ce-web   # omit specific services
```

Logs are tailed to stdout *and* written to `./logs/<service-name>.log`
so you can grep historical output after the fact.

**Three-terminal flow** (recommended for active development — feature
restarts don't tear down the shell):

```bash
# Terminal 1
./scripts/start_db.sh && ./run_platform.sh

# Terminal 2
./run_inventory.sh

# Terminal 3
./run_continued_ed.sh    # or ./run_doc_compliance.sh
```

Open `http://localhost:3000` once everything is up. The shell loads the
feature MFEs from their dev servers via the bootstrap API.

---

## 8. Port map (cheat sheet)

| Service | Port | Health URL |
|---|---|---|
| Registry | 8010 | http://localhost:8010/health |
| Bootstrap API | 8000 | http://localhost:8000/api/shell/health |
| Shell | 3000 | http://localhost:3000/ |
| Inventory API | 8200 | http://localhost:8200/api/inventory/it/health |
| Inventory Web | 3200 | http://localhost:3200/ |
| Continued Ed API | 8300 | http://localhost:8300/api/education/continued-ed/health |
| Continued Ed Web | 3300 | http://localhost:3300/ |
| Doc Compliance API | 8400 | http://localhost:8400/api/document-compliance/health |
| Doc Compliance Web | 3400 | http://localhost:3400/ |
| Registry DB (Postgres) | 5433 | `psql -h localhost -p 5433 -U registry portal_registry` |
| Doc Compliance DB (Postgres) | 5434 | `psql -h localhost -p 5434 -U compliance document_compliance` |

---

## 9. Troubleshooting

**`address already in use` on launch**
The run scripts call `clear_ports` to kill stale processes on each
expected port, but if it failed mid-launch:
```bash
# Kill anything on the inventory ports
sudo fuser -k 8200/tcp 3200/tcp
```

**`docker: permission denied`**
You aren't in the `docker` group yet. See § 6.

**`could not connect to server: Connection refused` on port 5433/5434**
Postgres isn't up. Run `./scripts/start_db.sh`.

**Registry service exits with `alembic` errors**
The DB hasn't been initialised yet. Make sure Postgres on `:5433` is up
*before* registry starts — `run_platform.sh --with-db` does this for you.

**`No module named 'app_platform_snowflake_client'`** when starting
continued-education-backend
The editable install of the shared Snowflake client didn't resolve. Make
sure `app-platform-snowflake-client/` exists at the repo root (run
`git submodule update --init --recursive`), then re-install:
```bash
cd feature-continued-education-backend
.venv/bin/pip install -r requirements.txt
```

**SQLite "database is locked"** on the Asset Inventory API
Caused by a long-running write transaction holding the lock. The service
sets WAL mode + a 10-second busy timeout on every connection, so this
should be rare. If it persists, ensure no other process has the
`app-platform.db` file open (e.g. a stray uvicorn worker).

**Vite dev server unbearably slow on WSL2**
Repo is probably on `/mnt/c/...`. Move it to `~/` (the Linux filesystem).

**Stale `node_modules` / package install issues**
```bash
cd <frontend>
rm -rf node_modules package-lock.json
npm install
```

**Stale Python venv**
```bash
cd <backend>
rm -rf .venv
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

---

## 10. Quick-start (TL;DR)

```bash
# 1. Clone
git clone <repo-url> endymion && cd endymion
git submodule update --init --recursive

# 2. Env files
for d in app-platform-registry-service app-platform-shell-bootstrap-api app-platform-shell \
         feature-asset-inventory-backend feature-asset-inventory-frontend \
         feature-continued-education-backend feature-continued-education-frontend \
         document-compliance-backend document-compliance-frontend; do
  [ -f "$d/.env.example" ] && [ ! -f "$d/.env" ] && cp "$d/.env.example" "$d/.env"
done

# 3. Databases
./scripts/start_db.sh

# 4. Everything else
./run_all.sh

# 5. Open
xdg-open http://localhost:3000     # or just browse to it
```
