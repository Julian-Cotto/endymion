# App-Platform Sync Plan: Endymion ⇐ Hyperion

**Status:** Drafted 2026-05-13. Not yet executed.

## Context

Both workspaces hold the same four `app-platform-*` submodules, but they have diverged:

- **Endymion** submodules point to personal forks (`github.com-work:Julian-Cotto/endymion-*`). Endymion adds local theme/UI work on top of upstream — most visibly in `app-platform-shell`.
- **Hyperion** uses upstream remotes (`github.com-work:highland-ventures/app-platform-*`) and has received backend updates that endymion lacks (release auth schema, scaffold-tool overhaul, bootstrap-api auth changes).

The goal is to bring endymion's submodules up to date with upstream Hyperion changes **without losing** the endymion-only UI work in `app-platform-shell`.

`app-platform-snowflake-client` exists only in endymion — out of scope for this sync.

## Divergence summary

| Submodule | Direction | Common ancestor | Notes |
|---|---|---|---|
| `app-platform-feature-scaffold-tool` | Hyperion ahead by 2 commits | `e8098f6` | Adds `permissions.py.j2` template + auth/manifest overhaul. Endymion has no on-top commits beyond ancestor. |
| `app-platform-registry-service` | Hyperion ahead | (deeper than shown) | Adds release-auth feature: migration `0002_add_release_auth_json.py`, `AuthSchema`, updates to `release_service.py`, `runtime_service.py`, manifest schemas. |
| `app-platform-shell` | **Both diverged** | `19aefa3` | Hyperion added `aaf7a21` (FeatureHost props, role parsing, App refactor). Endymion added `3a0398e` (sidebar layout, bhacemp theme, custom Select/DatePicker, dashboard chrome). Real 3-way merge required. |
| `app-platform-shell-bootstrap-api` | Hyperion ahead | (deeper than shown) | Adds `dev_allow_debug_headers`, auth/runtime/config overhaul, every service file and test diverges. Endymion is unaware of these. |

## Pre-work (one-time, ~15 min)

1. **Clean working trees in endymion submodules.** Each currently carries untracked cruft that will confuse a merge:
   - Delete or git-ignore: `.env` (preserve copies elsewhere), `.venv/`, `node_modules/`, `dist/`, `__pycache__/` across all four submodules.
   - Confirm `git status` is clean inside each submodule before any sync work.
2. **Add upstream as a second remote** in each endymion submodule so we can fetch hyperion's history directly without depending on the hyperion working copy:
   ```bash
   cd app-platform-<name>
   git remote add upstream git@github.com-work:highland-ventures/app-platform-<name>.git
   git fetch upstream
   ```
3. **Decide on a sync branch naming convention** (suggested: `sync/upstream-2026-05`). Each submodule's sync work lives on that branch until merged to its `main`.
4. **Snapshot the workspace pointer.** From endymion repo root: note the current submodule SHAs (`git submodule status`) so we have a rollback target.

## Phase 1 — Backend submodules (fast path)

Order: scaffold-tool → registry-service → bootstrap-api. Each is roughly the same shape; the registry-service one has a DB migration so it carries the most risk.

For each backend submodule:

1. **Branch off endymion `main`:** `git checkout -b sync/upstream-2026-05`.
2. **Merge or rebase upstream onto your fork.** Prefer `git rebase upstream/main` if endymion's commits on top are purely local-config (e.g. `7d5bc21 Registry: untrack .venv`). Use `git merge upstream/main` if the local commits look semantically meaningful and we want to preserve them as a branch shape. Capture the choice in the PR description.
3. **Resolve conflicts.** Expected conflict surfaces:
   - **scaffold-tool:** `pyproject.toml`, `manifest.schema.json`, templates under `src/feature_scaffold/templates/backend/app/platform/` (new `permissions.py.j2`), every `.j2` template, all tests. Endymion has no semantic changes on top — most conflicts should resolve to upstream's version.
   - **registry-service:** `app/db/models.py`, `app/schemas/manifest.py`, `app/services/release_service.py`, `app/services/runtime_service.py`, `migrations/versions/0001_init_registry.py`. The new `0002_add_release_auth_json.py` should land cleanly. Local-only `scripts/run_local.sh` (underscore) vs upstream `scripts/run-local.sh` (hyphen) — adopt upstream's name and delete the duplicate.
   - **bootstrap-api:** every `app/api/`, `app/core/`, `app/services/` file plus every test. Local-only `.env.example` deltas need a careful look — keep environment-specific values, take new variables from upstream.
4. **Run the test suite** inside the submodule. Each has pytest. For registry-service also run the new migration against a scratch DB.
5. **For registry-service specifically:** verify migration chain. `alembic upgrade head` should apply `0001` → `0002` clean. If endymion has already applied a hand-modified `0001`, plan a one-time stamp.
6. **Push the sync branch to your fork** (`origin` = `Julian-Cotto/endymion-*`). Optionally open a PR on the fork for visibility, then merge to fork's `main`.
7. **Bump the submodule pointer in endymion workspace repo.**

## Phase 2 — `app-platform-shell` (real three-way merge)

This is the only submodule that needs careful manual work. Both sides have moved past the common ancestor `19aefa3`.

### What to preserve from endymion (`3a0398e`)

These files/dirs exist **only in endymion** and represent the bhacemp-theme work:
- `src/app/components/`
- `src/app/layouts/`
- `src/app/utils/`
- `src/styles/`
- `src/app/pages/HomePage.tsx`
- `src/app/providers/ThemeProvider.tsx`
- `tailwind.config.ts`
- `postcss.config.cjs`

### What to pull from hyperion (`aaf7a21`)

Hyperion's commit refactors how the shell loads/passes runtime + feature data:
- `src/app/App.tsx` — role parsing + session handling refactor
- `src/app/pages/FeatureHost.tsx` — accepts `runtime` and `feature` props
- `src/main.tsx` — global window auth/runtime properties
- All of `src/platform/bootstrap/` and `src/platform/runtime/` — bootstrap process streamlined
- `src/platform/auth/resolveShellFeatureAuth.test.ts`
- `src/test/setup.ts`, `src/vite-env.d.ts`
- New test scaffolding: `App.test.tsx`, `scripts/`, `user-event` dependency
- `vite.config.ts`, `package.json` + lock

### Strategy

1. **Branch from endymion `main`:** `sync/upstream-2026-05`.
2. **Merge `upstream/main` into the branch** (not rebase — we want to keep the `3a0398e` theme commit identifiable in history).
3. **Expected conflict files (manual resolution required):**
   - `src/app/App.tsx` — endymion wraps in `ThemeProvider` + sidebar layout; hyperion refactors role/session logic. Need both: keep theme wrapping, adopt new role/session flow.
   - `src/app/pages/FeatureHost.tsx` — endymion uses it inside layout; hyperion changes its prop signature. Adapt the layout's call site to the new signature.
   - `src/main.tsx` — endymion mounts theme + tailwind; hyperion adds window globals. Combine.
   - `package.json` + `package-lock.json` — merge dep lists; reinstall with `npm install` and commit the lock.
   - `vite.config.ts`, `src/test/setup.ts`, `src/vite-env.d.ts` — take upstream form, re-apply any local-only entries.
   - `.env.example` — diff manually, merge new keys.
4. **Bootstrap/runtime/auth platform layer** — endymion has not touched these since the common ancestor; resolve by taking upstream's version wholesale. Same for `resolveShellFeatureAuth.test.ts`.
5. **Verify in-browser before declaring done.** Per project preference: type-check + tests are not enough for UI. Start the dev server, log in, navigate to a feature, confirm:
   - bhacemp theme + sidebar still render
   - feature loading still works (both bootstrap and registry modes)
   - dashboard chrome and custom Select/DatePicker intact
   - no console errors from missing window globals
6. **Push to fork `main`, bump submodule pointer in workspace.**

## Phase 3 — Workspace commit

After all four submodule pointers are bumped:

1. From endymion workspace root: `git add` the four submodules, commit with a message describing the sync (which upstream SHAs were pulled, summary of what each contains).
2. Update `run_all.sh` / any local scripts that reference the renamed `scripts/run-local.sh` (was `run_local.sh` in registry-service).
3. Re-run `run_all.sh` end-to-end to confirm the workspace still boots: registry-service migrations apply, bootstrap-api comes up, shell loads, scaffold-tool CLI still works.

## Risk register

| Risk | Mitigation |
|---|---|
| Shell merge silently breaks the bhacemp theme in some route | Manual browser walkthrough of every top-level shell route post-merge. |
| Registry-service migration `0002` collides with a hand-applied schema in your local DB | Diff `0001_init_registry.py` between endymion and hyperion first — if they match, just upgrade; if not, plan a stamp or rebuild local DB. |
| Bootstrap-api `.env` keys drift — service starts but auth misbehaves | Diff `.env.example` carefully; add any new keys to local `.env` before first run. |
| New `permissions.py.j2` template in scaffold-tool breaks existing scaffolded features | Run `scaffold` against a throwaway target after merge and diff against an existing feature's `permissions.py`. |
| Endymion fork remote falls further behind during the merge work | Keep sync window short (<1 week); refetch upstream right before each phase. |

## Open questions

- Do we want endymion's forks to eventually re-converge with `highland-ventures/*` and use upstream directly, or stay forked indefinitely? If the latter, this sync exercise will repeat — consider a periodic `upstream-sync` cron.
- Is the bhacemp theme work eventually meant to land upstream? If yes, this merge would also be a chance to extract a clean PR back to `highland-ventures/app-platform-shell`.
- Does `app-platform-snowflake-client` need its own upstream eventually, or is it permanently endymion-local?

## Estimated effort

- Pre-work: ~15 min
- Phase 1 backend (3 submodules): ~1–2 hr each if conflicts are mechanical, more if migration surprises
- Phase 2 shell: half a day minimum — three-way semantic merge + manual browser verification
- Phase 3 workspace: ~30 min

Total realistic budget: **one full day of focused work**, ideally not split across sessions.
