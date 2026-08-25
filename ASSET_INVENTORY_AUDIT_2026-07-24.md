# Asset Inventory — Audit & Improvement Backlog (2026-07-24)

_Second-pass audit. Prior audit (`ASSET_INVENTORY_AUDIT.md`, 2026-06-30) covered cross-view nav, dashboard roll-ups, bulk actions — all shipped. This pass looks at structural / platform gaps not in that scope. Scope: `feature-asset-inventory-backend` (FastAPI) + `feature-asset-inventory-frontend` (React MFE)._

## 🔴 Critical (correctness / risk)

1. **Tests near-zero, one is broken.**
   - Backend: only `test_health` + `test_feature`. ~150 endpoints, 26 services, 0 coverage. Vendor clients (Intune/Meraki/Defender/Axis/UPS/FedEx/Dell/Lenovo) unmocked.
   - Frontend: 1 test file, stale — asserts `"Test item — active"` listitem UI that no longer exists (`src/tests/App.test.tsx:63`). Fails against current code.
   - Cheap first wins: `pathToView`/`viewToPath` routing (pure), `apiClient` error mapping, `report_service.py` aggregations.

2. **Committed `.env` with real-looking secrets** at backend repo root. Rotate + purge from history + `.gitignore`. `.env.example` missing Axis/Snowflake/Entra keys.

3. **No Alembic. Migrations hand-rolled at every boot.** `_apply_lightweight_migrations` etc. in `app/main.py:130-361` — `ALTER TABLE ADD COLUMN` loops + 12-step SQLite CHECK rebuild, exceptions swallowed (`main.py:357`). Fragile, silent failures, won't translate to Snowflake prod. Adopt Alembic (pattern already exists in reports-layering).

## 🟠 High (missing function)

4. **No scheduler. Periodic syncs never fire.** Staleness thresholds imply nightly/periodic (`shipments_poll` 2h `sync_run_service.py:199`, `tracking_auto_refresh_minutes=15`) but nothing schedules them. `shipments_poll` has no manual entrypoint either (`sync_runs.py:49`). Add APScheduler/cron or wire external trigger.

5. **Events declared, stubbed.** Contract publishes `asset.onboarded/assigned/archived`, consumes `hr.user.offboarded`. Reality: `events/publisher.py` prints; offboarding job/listener/worker are no-ops. Offboarding automation is fake.

6. **Long syncs block HTTP request.** All syncs synchronous, request-driven. Big bulk-sync ties up a worker + risks client timeout. Move to background task queue.

## 🟡 Medium (UX / maintainability)

7. **Frontend list views have no loading state.** `AssetsList`, `Shipments`, `Deployments`, `Users`, `Groups`, `Networks`, `Software`, `Locations`, `Statuses` — blank flash during load. Empty states inconsistent. No `ErrorBoundary` anywhere — `apiClient` throws on missing token → white-screen.

8. **No server-state layer.** All `useState`+`useEffect` fetch-on-mount per view. No cache/dedup/revalidate. Add react-query/SWR (also fixes #7).

9. **Type drift risk.** 140 endpoints hand-typed in `src/types/`, no OpenAPI codegen. Generate client from FastAPI OpenAPI.

10. **God files.** Backend `inventory_service.py` (2519), `models/inventory.py` (1087). Frontend `Wallboard.tsx` (3750), `AssetDetail`/`Controllers`/`Reports`/`EnrollEmployee` 1000+. Split.

## 🟢 Low (cleanup)

11. **Dead scaffold.** Backend: `platform_capabilities.py`, `cache_capabilities.py`, `snowflake.py` stub, broken `validate-manifest.py`, empty `domain/models.py`+`feature_service.py`, no-op jobs/listeners/workers. Frontend: `FeatureApp.tsx`, `FeatureHomePage.tsx`, `featureApi.ts`+`BackendHealthCard.tsx`, `registryClient.ts`, `featureConfig.ts` — 0 refs.

12. **Dep lists out of sync** — `pyproject.toml` vs `requirements.txt` (curl_cffi, snowflake-connector, openpyxl).

13. **Standalone `app` build renders unstyled** — CSS lives only in host shell.

14. **UPC lookup unimplemented** (`lookup_service.py:1198`).

## Feature ideas (net-new)

- **Warranty-expiry alerts** — warranty already synced; nothing surfaces "expires in 30d."
- **Auto-unassign on offboard** — the #5 event; HR feed → unassign + flag for collection.
- **Asset lifecycle cost / depreciation** — age / refresh-due reporting.
- **Reconciliation report** — Intune-seen vs inventory-known deltas (ghost/unmanaged devices).
- **Reservation deeplinks** — currently non-serializable (`App.tsx:160`).
- **SIM cards** — track SIMs as inventory, assign to a network (firewall) location, cross-check against Meraki cellular. _(BUILDING NOW — see below.)_

---

## SIM Card feature — design

**Goal.** SIMs are inventory items. A SIM can be assigned to a **network** (a Meraki network backed by a firewall/MX, which carries a location). Cross-reference against Meraki cellular data to show whether the SIM is *actually* present/active in a firewall at a network vs. only assigned on paper.

**Model decision.** Separate `Sim` model (not an `Asset` row). Rationale: SIMs share almost no fields with physical-device `Asset` (no warranty/model/Intune/Defender; instead ICCID/carrier/MSISDN/IMSI). Matches how `Badge`, `Network`, `Software` are all first-class non-Asset models in this codebase.

**`Sim` fields.**
- `iccid` (unique) — the SIM's serial, 19–20 digits.
- `carrier`, `phone_number` (MSISDN), `imsi` — identity.
- `status` — `active` / `spare` / `suspended` / `deactivated` (CHECK-constrained).
- `data_plan`, `notes`.
- `network_id` (FK → networks, nullable) — the assignment target (firewall + location).
- Meraki cross-check (written by sync): `meraki_seen` (bool), `meraki_serial` (firewall device serial reporting this ICCID), `meraki_network_id`, `meraki_status`, `meraki_checked_at`.
- Standard audit: `created_at/updated_at/created_by_upn/updated_by_upn/archived_at`.

**Assignment.** `network_id` ties the SIM to a network → firewall → location (network already carries `location_id` + `firewall_ip`). Location is derived, not stored twice.

**Meraki marriage.** New sync source `meraki_sims`. Pulls cellular SIM/uplink data from Meraki (MX cellular uplink + MG cellular gateways), keyed by ICCID. For each inventory SIM, sets:
- `meraki_seen` — ICCID found in any Meraki firewall.
- `meraki_serial` / `meraki_network_id` — where Meraki reports it.
- a derived **reconciliation state** surfaced in the UI: `matched` (assigned network == Meraki network), `mismatched` (assigned somewhere else than Meraki reports), `unassigned-but-live` (Meraki sees it, inventory has no network), `assigned-not-live` (inventory assigned, Meraki doesn't see it), `unknown` (not in Meraki).

**Endpoints** (`/sims` router): list (+filters +export), get, create, patch, assign/unassign to network, archive/unarchive, `POST /sims/sync` (Meraki reconcile). Wire into `SYNC_SOURCES` + sync-runs so it shows in SyncHealthCard.

**Frontend.** New `Sims` list view + `SimDetail`, nav tab, types, api module, reconciliation chip (reuse the meraki-claim chip pattern). Network detail gets a "SIMs on this network" panel.

### Build status — SHIPPED 2026-07-24
- [x] backend model `Sim` (`app/models/inventory.py`) + `SIM_STATUSES`/`SIM_CARRIERS` + `models/__init__` exports. New table auto-created by `create_all`; no hand migration needed (fresh table).
- [x] `meraki_sims` added to `SYNC_SOURCES` + `_MANUAL_TRIGGERS` + `_run_source` dispatcher (`sync_runs.py`) — shows in SyncHealthCard, triggerable from the drawer.
- [x] Meraki helper `lookup_service.list_meraki_cellular_sims()` — walks org appliance uplink statuses, extracts cellular ICCIDs (digits-normalised).
- [x] `sim_service.py` — list/get/create/update/assign/unassign/archive + `reconcile_with_meraki()`.
- [x] `api/sims.py` router (list/get/create/patch/assign/unassign/archive/unarchive/sync/export) wired in `main.py`.
- [x] `GET /networks/{id}/sims` for the NetworkDetail panel.
- [x] Frontend: `types/sim.ts`, `services/sims.ts`, `components/SimReconcileChip.tsx`, `views/Sims.tsx`, `views/SimDetail.tsx`, `exports.downloadSimsExport`, `entityHistory` "sim" type, App nav (tab + routes + render), NetworkDetail "SIMs on this firewall" panel.

**Reconcile state model** (derived, `Sim.reconcile_state`): `matched` / `mismatched` / `assigned_not_live` / `unassigned_but_live` / `unassigned`. Surfaced as a color chip everywhere + explanatory alerts on SimDetail.

**Verified:** backend boots, 9/9 tests pass, full CRUD+reconcile roundtrip against a temp DB, and the reconcile pulled **130 live cellular SIMs from the real Meraki org** (all `unknown_in_meraki` until onboarded). Frontend `tsc` clean (only pre-existing broken `App.test.tsx` errors remain) + both vite builds pass.

**Follow-ups (not built):** (1) dashboard tile for mismatched/not-live counts; (2) one-click "onboard from Meraki" for `unknown_in_meraki` ICCIDs; (3) tie SIM to the firewall *asset* row (not just network) if you later track MX appliances as assets; (4) auto-schedule `meraki_sims` once the scheduler gap (#4 above) is fixed.
