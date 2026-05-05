# stuff-fortnight

Local workspace bundling the platform MFE services and the IT asset
inventory feature.

## Layout

```
stuff-fortnight/
├── app-platform-registry-service/         (submodule, :8010)
├── app-platform-shell-bootstrap-api/      (submodule, :8000)
├── app-platform-shell/                    (submodule, :3000)
├── app-platform-feature-scaffold-tool/    (submodule, CLI)
├── feature-asset-inventory-backend/       (plain dir, :8200)
├── feature-asset-inventory-frontend/      (plain dir, :3200)
├── scripts/_run_lib.sh                    (shared launcher helpers)
├── run_platform.sh                        (registry + bootstrap + shell)
├── run_inventory.sh                       (inv-api + inv-web)
└── run_all.sh                             (everything in one terminal)
```

The 4 submodules pin to commits on
`github.com-work:highland-ventures/<name>.git`.
The 2 inventory dirs are plain folders versioned in this repo.

## First-time clone

```bash
git clone --recurse-submodules github.com-work:Julian-Cotto/stuff-fortnight.git
cd stuff-fortnight
```

If you forgot `--recurse-submodules`:

```bash
git submodule update --init --recursive
```

## Local prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL on `localhost:5432` with role + db `registry / portal_registry`
  (only required if running the registry service)
- ngrok / cloudflared (optional, for phone testing of the camera scanner)

## .env files

Each service uses a `.env` (gitignored). On first run the launcher copies
`.env.example` → `.env` for the registry, bootstrap-api, and shell. After
that you can edit them freely.

## Running

```bash
./run_platform.sh     # registry, bootstrap-api, shell
./run_inventory.sh    # inv-api, inv-web
```

Logs stream prefixed + colored. Per-service files in `./logs/<name>.log`.

For full-stack one-terminal mode:

```bash
./run_all.sh
```

Pass `--no-bootstrap` to skip pip/npm install. Pass `--skip name1,name2`
to omit services.

## Inventory feature setup

After the platform services are healthy, publish + activate the inventory
manifest in the registry:

```bash
curl -X POST http://localhost:8010/api/releases \
  -H 'Content-Type: application/json' \
  -d @feature-asset-inventory-backend/contracts/feature-manifest.local.json

curl -X POST 'http://localhost:8010/api/admin/features/asset-inventory/versions/0.1.1/activate?environment=local'
```

Refresh the shell at <http://localhost:3000> and "IT Inventory" appears
in the nav.

The Snowflake DDL for production tables lives at
`feature-asset-inventory-backend/infra/snowflake/schema.sql`.
