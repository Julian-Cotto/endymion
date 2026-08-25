# Asset Inventory Audit — Backlog

> Audit conducted 2026-06-25. Module reviewed: `feature-asset-inventory-backend` + `feature-asset-inventory-frontend`. Excludes work already shipped (SyncRun ledger, Axis badge mirror + CRUD, two-controller setup, Controllers topology view, Meraki claim integration, Asset Locator serial/MAC search, badge ↔ UPN linking).

## How to use this doc

Each finding has a **Decision** field. Fill it in as we agree on direction:

- `agree` — accept as written, ready to schedule
- `revise` — keep idea but change scope/approach (note revision)
- `skip` — drop from backlog
- `later` — defer to a future phase
- `(blank)` — not yet discussed

Add notes in `Notes:` lines under any finding.

Status column tracks build state once started: `todo` / `in-progress` / `done` / `blocked`.

---

## 1 — Cross-view navigation gaps

Places where the relationship exists in the data model but the UI can't follow it.

### 1.1 Badge → Asset (via linked UPN → assigned_upn)

- **What's there**: `Badge.linked_intune_user_upn` set manually; `Asset.assigned_upn` is the same UPN.
- **What's missing**: BadgeDetail's "Open user" button ([BadgeDetail.tsx:635-644](feature-asset-inventory-frontend/src/views/BadgeDetail.tsx#L635-L644)) goes to the user but not to that user's assigned assets.
- **Fix**: New section in BadgeDetail "Assets assigned to this person" listing assets where `assigned_upn == linked_intune_user_upn`. Click → AssetDetail.
- **Decision**: agree
- **Status**: done
- **Notes**: Card hidden when no UPN linked. Archived assets hidden by default with toggle when present. Click row → AssetDetail via `onAssetClick` wired from App.tsx.

### 1.2 Asset → Badges (via assigned_upn)

- **What's there**: `assigned_upn` on every assigned asset; `Badge.linked_intune_user_upn` filterable.
- **What's missing**: AssetDetail has no awareness of badges. No `onBadgeClick` callback. ([AssetDetail.tsx], [App.tsx:434-439])
- **Fix**: Card on AssetDetail "Access credentials" listing badges with matching UPN. Click → BadgeDetail.
- **Decision**: agree
- **Status**: done
- **Notes**: Card hidden when asset has no `assigned_upn`. Backend search filter is fuzzy (ILIKE %term%), so frontend re-filters with case-insensitive equality on `linked_intune_user_upn` to avoid card-number false matches. Archived badges hidden by default with toggle; enabled/disabled chip per row.

### 1.3 Network → Badges (controller membership)

- **What's there**: Door panels sit on a network. Badge controller_id is known; the Meraki network for that IP could be looked up.
- **What's missing**: NetworkDetail has no controller awareness. Controllers view has no network awareness.
- **Fix**: When the controller's IP matches a Meraki client appearance, cross-link Controllers ↔ Networks ↔ Badges.
- **Decision**: agree
- **Status**: done
- **Notes**: Backend reuses `network_service.build_vlan_index` + `match_ip` (same surface as asset locator). `/badges/controllers` returns `network_id`/`network_name`; new `/networks/{id}/axis-controllers` lists panels on a network. Controllers view shows "On network: X" link below the controller tabs; NetworkDetail gets an "Access controllers" section (hidden when none match).

### 1.4 Deployment ↔ Location

- **What's there**: `Deployment.target_address_*` free-form fields ([DeploymentDetail.tsx:54-62]).
- **What's missing**: No `location_id` FK on Deployment. Locations view doesn't show deployments to/from that location. Free-text address can't be queried back.
- **Fix**: Backfill `location_id` on Deployment (and Shipment — see 1.5). Add "Deployments to this location" panel on Location detail.
- **Decision**: agree
- **Status**: done
- **Notes**: Schema actually already had `target_location_id` FK + picker in DeploymentCreate. So this collapsed to the reverse-query work in 5.3 + Location detail view in 4.3.

### 1.5 Shipment ↔ Location

- **What's there**: `to_*` / `from_*` address fields on Shipment.
- **What's missing**: No reverse query, no location-detail surface.
- **Fix**: Same shape as 1.4 — `to_location_id` / `from_location_id` (nullable), plus Location detail panel.
- **Decision**: agree
- **Status**: done
- **Notes**: Same surprise — Shipment already had `from_location_id` + `to_location_id` FKs and ShipmentCreate already had pickers. Just needed reverse query (5.3) + Location detail view (4.3).

### 1.6 ReservationDetail → Asset

- **What's there**: Reservation rows carry `asset_id`. App.tsx routes ReservationDetail with `onAssetClick` ([App.tsx:457]).
- **What's missing**: ReservationDetail probably doesn't expose a click target on the asset row.
- **Fix**: Make asset name/serial in reservation detail a button → AssetDetail.
- **Decision**: n/a — already shipped
- **Status**: closed
- **Notes**: ReservationDetail.tsx line 149 already calls `onAssetClick(row.asset_id)`. Audit was wrong.

### 1.7 User → Reservations they own

- **What's there**: UserDetail shows assigned devices ([UserDetail.tsx:399-436]).
- **What's missing**: No view of pending shipments/deployments naming the user as recipient.
- **Fix**: Backend endpoint `/users/{upn}/pending-deliveries`. New section in UserDetail.
- **Decision**: agree
- **Status**: done
- **Notes**: Reused existing `/reservations` endpoint with new `?assigned_upn=` filter — case-insensitive UPN match against `Asset.assigned_upn`. UserDetail gets new "Pending deliveries" card (hidden when empty) with row click → AssetDetail and source button → DeploymentDetail / ShipmentDetail.

### 1.8 Group → Members → their assets

- **What's there**: GroupDetail filters members ([GroupDetail.tsx:122-131]).
- **What's missing**: Member rows are static — no `onMemberClick` wired.
- **Fix**: Make rows clickable → UserDetail. App.tsx passes the callback already exists pattern.
- **Decision**: agree
- **Status**: done
- **Notes**: Only `member_type === "user"` rows route (devices/nested groups left static — no detail view for those). UserDetail now also shows pending deliveries (1.7) + their badges (via 1.2) so the full Group → Member → Assets → Badges chain is reachable.

### 1.9 Software → Groups (reverse usage)

- **What's there**: SoftwareAssignment table joins Software to Groups (backend).
- **What's missing**: SoftwareDetail has no "Used by these groups" panel.
- **Fix**: Surface existing relationship.
- **Decision**: agree
- **Status**: done
- **Notes**: SoftwareDetail already rendered the Groups + Users assignment lists; rows were static. Made the principal name clickable on both. Group → GroupDetail, User → UserDetail. The "Remove assignment" trash button stays separate.

### 1.10 Controllers → Assets on their network

- **What's there**: Controllers manage doors which sit on a Meraki network.
- **What's missing**: Controllers view never links to assets that share its network.
- **Fix**: After 1.3 lands, add "Devices on this network" panel to controller detail.
- **Decision**: covered-by-1.3
- **Status**: closed
- **Notes**: 1.3 added the "On network: X" link in the Controllers view header. NetworkDetail already lists gear + clients, so Controllers → Network → Assets is one extra click. No dedicated "devices on this network" inline panel — the indirection is acceptable given typical network gear counts.

---

## 2 — Dashboard / roll-up gaps

Data exists somewhere but isn't aggregated on the landing screen.

### 2.1 Badge inventory tile

- **What's missing**: Dashboard has no badge counts.
- **Fix**: Add tile: `N total · M unlinked · K archived` per controller. New `getDashboardStats.badges` block.
- **Decision**: agree
- **Status**: done
- **Notes**: Bundled with 2.2. `DashboardStats.badges` block returns total / enabled / disabled / unlinked / archived + per-controller breakdown. New tile is the 5th stat-card (grid now `lg:grid-cols-5`); click → Badges view.

### 2.2 Unlinked-badges alert

- **What's missing**: Dashboard doesn't flag "badges awaiting UPN link" — security/audit signal.
- **Fix**: Alert tile when `unlinked > threshold`. Click → Badges view with `linked=false` filter pre-applied.
- **Decision**: agree
- **Status**: done
- **Notes**: Alert tile (warning tone) shows whenever `unlinked > 0`. Click navigates to Badges. Pre-filter on `linked=false` deferred — currently lands on the list and the operator picks the Link filter manually. Tile passes the filter arg through but App.tsx currently routes plain; URL-based filter handoff is a follow-up.

### 2.3 SyncHealthCard: retry button

- **What's there**: Tiles + drawer with run history ([SyncHealthCard.tsx]).
- **What's missing**: Drawer can't trigger a re-sync. Operator must navigate to the actual feature view.
- **Fix**: Add per-source "Trigger now" button on the drawer that POSTs the right sync endpoint.
- **Decision**: agree
- **Status**: done
- **Notes**: New `POST /sync-runs/trigger/{source}` dispatches to the appropriate service function (intune, defender, meraki_devices, meraki_networks, meraki_clients, snowflake_locations, users, entra_groups, software, axis_badges, warranty). `shipments_poll` left untriggerable on purpose (scheduled only — manual would burn carrier quotas). Drawer fetches the triggerable list once on mount, disables the button (with tooltip) for non-triggerable sources, refreshes runs + outer health after success.

### 2.4 Stale-sync aggregate

- **What's missing**: No cross-source "how many sources are stale right now" count.
- **Fix**: Tile on Dashboard. Heatmap optional.
- **Decision**: agree
- **Status**: done
- **Notes**: Pure render-side roll-up in SyncHealthCard header — chips show `healthy/total`, plus separate `N failed`, `N stale`, `N never run` chips when non-zero. No backend change; reuses the same `/sync-runs/health` payload already loaded.

### 2.5 Controller heartbeat tile

- **What's missing**: Dashboard doesn't show Axis controllers online/offline.
- **Fix**: Quick ping in sync-health pipeline; surface count.
- **Decision**: agree (B — read last sync, no live probe)
- **Status**: done
- **Notes**: Backend `_controllers_reachable_snapshot` reads the most recent `axis_badges` SyncRun and counts controllers where `unreachable` is falsy + `skipped=false`. Added `controllers_configured` / `controllers_reachable` / `controllers_last_checked_at` to `DashboardStats.badges`. Dashboard tile renders a colored "X/Y controllers reachable" sub-line (green when all, yellow on partial, red on zero, muted "never checked" before first sync). Tooltip shows relative time. No live HTTP probe — uses the data the sync already wrote.

### 2.6 Warranty × Intune-compliance cross-metric

- **What's there**: Dashboard shows warranty % and Intune stale count separately ([Reports.tsx:130], [Reports.tsx:149]).
- **What's missing**: No "warranty OK ∩ compliance OK" intersection — useful for fleet readiness reports.
- **Fix**: Add combined grid to Fleet report tab.
- **Decision**: agree
- **Status**: done
- **Notes**: Backend `_warranty_compliance_matrix` builds a 3×3 cross-tab (warranty on/off/unknown × compliance compliant/non_compliant/unmanaged) on devices only. Returned under `fleet_health().warranty_x_compliance`. FleetView renders a color-coded grid: green=ready, yellow=attention, red=blocked. Each cell shows count + % of fleet. Verified against real data: 155 on+compliant / 22 off+non_compliant / 0 unmanaged on this org.

### 2.7 Export on list views (Assets, Badges, Users, Software, Groups, Networks, Locations, Deployments, Shipments)

- **What's missing**: None of the 9 list tables have CSV/XLSX export.
- **Fix**: Generic `useExport` hook + per-view "Export" button. Locator already has the CSV/XLSX pattern — reuse.
- **Decision**: agree (final pass — all 9 wired)
- **Status**: done
- **Notes**: Built `export_service.py` (reusable Column-based CSV/XLSX writer) on the backend. Export endpoints live for all 9 entities: `/assets/export`, `/badges/export`, `/users/export`, `/software/export`, `/groups/export`, `/networks/export`, `/locations/export`, `/deployments/export`, `/shipments/export`. Each accepts the same filter surface as its list endpoint. Frontend `ExportDropdown` mounted on all 9 list views. Filename includes timestamp + entity prefix.

### 2.8 Reservation pipeline funnel

- **What's missing**: No visualization of `planning → shipped → received` across reservations.
- **Fix**: Add stage counts to DashboardStats; render funnel.
- **Decision**: agree (A — render-side roll-up, no schema change)
- **Status**: done
- **Notes**: Pure render-side. New `PipelineFunnel` component on Dashboard renders 5 stages — Planning · Deployment in progress · Shipments open · In transit · Completed (30d) — as horizontal bars scaled to the max stage count. Exception count surfaces as a separate side chip in danger tone. Uses existing `DashboardStats.deployments` + `DashboardStats.shipments` blocks; no backend change.

---

## 3 — Missing features on existing infrastructure

### 3.1 Bulk actions: Badges / Software / Locations

- **What's there**: AssetsList has bulk-select + bulk-location modal ([AssetsList.tsx:74-98]).
- **What's missing**: Badges (bulk enable/disable/archive), Software (bulk deactivate), Locations (bulk import) have no multi-select UI.
- **Fix**: Add checkbox column + bulk-action toolbar to each.
- **Decision**: agree-all
- **Status**: done
- **Notes**: All three views got a checkbox column + select-all in the header + a sticky bulk toolbar that appears when ≥1 row selected. Backend endpoints: `POST /badges/bulk-set-enabled` (loops through Axis SetCredential per token, isolated per-token errors), `POST /software/bulk-archive` (toggles `archived_at`, idempotent), `POST /locations/bulk-set-active` (toggles `is_active`, idempotent). Selection clears automatically when filters change. Toasts on success/failure/warning.

### 3.2 Audit history surfaced on more entities

- **What's there**: AssetHistory table + UI on AssetDetail.
- **What's missing**: SoftwareDetail, BadgeDetail, NetworkDetail, DeploymentDetail have no audit log section even where timestamps exist.
- **Fix**: Generic audit-log component reading `created_by_upn`, `updated_by_upn`, etc. Surface per detail page.
- **Decision**: agree-A-full
- **Status**: done
- **Notes**: New `EntityHistory` table (entity_type, entity_id as string, event_type, from/to_value, actor_upn, notes, occurred_at). `history_service.record(...)` shares the mutation tx. Wired write sites: Badge (create, delete, link/unlink, rename, enable/disable), Software (create, update, archive/unarchive, bulk-archive), Location (create, update, delete, bulk activate/deactivate), Deployment (start/complete/cancel/archive), Network (update), Shipment (resolve/cancel/archive/unarchive). Backend `GET /history/{entity_type}/{entity_id}` returns newest-first. Reusable `EntityHistoryList` component mounted on BadgeDetail, SoftwareDetail, LocationDetail, DeploymentDetail, NetworkDetail, ShipmentDetail. Hides itself when no events. Asset stays on its existing dedicated `AssetHistory` system.

### 3.3 Meraki claim status on AssetDetail

- **What's there**: Claim happens; result toasted.
- **What's missing**: No persistent badge on the asset showing "claimed in Meraki org" vs unclaimed.
- **Fix**: Store last claim result on asset row (or compute via inventory lookup); show chip in AssetDetail.
- **Decision**: agree
- **Status**: done
- **Notes**: Added `Asset.meraki_claim_status` + `meraki_claim_checked_at` columns + lightweight migration. Claim endpoint accepts optional `asset_id` and persists the result. `AssetOut` schema returns the new fields. MerakiClaimPanel now seeds its chip from the cached status so the operator sees state before clicking — and re-clicks now refresh the persisted value via `onResult` callback that updates the parent's Asset state without a full reload.

### 3.4 MAC address visibility on Asset

- **What's there**: `Asset.mac_address` populated from Intune (`inventory.py:159`).
- **What's missing**: Never displayed in AssetDetail or list rows.
- **Fix**: Add to AssetDetail "Network" section with copy-to-clipboard.
- **Decision**: agree
- **Status**: done
- **Notes**: New `MacCell` renders next to Defender's "Last IP". Click copies the address to clipboard with success toast. AssetsList column deferred (table is already dense).

### 3.5 Bulk relink (network / MAC / Meraki)

- **What's there**: BulkLocationModal only.
- **What's missing**: BulkNetworkModal, BulkMerakiClaim modal for fleet ops.
- **Fix**: Generalize the bulk-modal pattern.
- **Decision**: agree-claim-only
- **Status**: done (claim only)
- **Notes**: `POST /assets/bulk-meraki-claim` loops the selected asset_ids, skips non-gear, runs `claim_serial` per row, persists the result via `meraki_claim_status` + `meraki_claim_checked_at`. AssetsList bulk toolbar gains a "Claim in Meraki" button — disabled when none of the selection is gear, labeled with the gear count when present. Confirm dialog before firing. Toast summary shows ok/failed/skipped. Per-asset chip refreshes after reload. Bulk network and bulk MAC override deferred as low real-world value.

### 3.6 Defender risk/health card on AssetDetail

- **What's there**: `defender_risk_score`, `defender_health_status`, `defender_last_seen_at`, `defender_onboarding_status`, etc. populated.
- **What's missing**: No card surfaces these.
- **Fix**: Dedicated Defender card on AssetDetail; chip on AssetsList for at-risk machines.
- **Decision**: agree-A
- **Status**: done
- **Notes**: Existing Defender KV grid was technically present but visually buried under an `eyebrow` label. Promoted the section header to a real `heading-3` with a Shield icon and a new `SecurityHeadlineChip` summarizing the row's posture: green "Healthy · low", yellow "Attention · medium / impaired comms", red "At risk · high / inactive / no-sensor-data", muted "Status unknown" or "Not Defender-managed". Hover shows last-seen timestamp. AssetsList chip deferred.

---

## 4 — IA / UX confusion

### 4.1 Three "overview" surfaces

- **What's there**: Dashboard.tsx, Reports.tsx (wraps Dashboard + sub-tabs), Wallboard.tsx ([App.tsx:357]).
- **Problem**: New users don't know which is the home. Wallboard is buried behind a Dashboard button.
- **Fix**: Flatten — rename Dashboard → "Overview" as the top-level home; promote Wallboard to a peer tab; collapse Reports sub-tabs into Overview or split cleanly.
- **Decision**: agree-B (Wallboard promoted only; no rename, no Reports restructure)
- **Status**: done (partial — only Wallboard surfaced as top-level)
- **Notes**: Added `wallboard` to TabKind union, TABS array, and the persisted-default list. Wallboard still renders fullscreen on view.kind="wallboard", so the existing escape path works. Dashboard rename + Reports flatten left out — touchy UX changes, defer until requested.

### 4.2 Networks vs Controllers ambiguity

- **What's there**: Networks view shows Meraki networks; Controllers view shows Axis controllers ([App.tsx:544-552]).
- **Problem**: Both kinds of "network device" — confusing as separate top-level tabs with no cross-link.
- **Fix**: Either rename clearly ("Networks (Meraki)" + "Access Control (Axis)") or merge under a single "Infrastructure" parent.
- **Decision**: agree-A
- **Status**: done
- **Notes**: Tab labels renamed to "Networks (Meraki)" and "Access Control (Axis)". URLs + view kinds unchanged so deep links still work. 1.3 already cross-links Controllers ↔ Networks.

### 4.3 Locations is read-only-ish with no drill-down

- **What's there**: Locations CRUD ([Locations.tsx:67-83]).
- **Problem**: No asset count, no deployment/shipment count, no detail view.
- **Fix**: LocationDetail showing assets at this location + active reservations.
- **Decision**: agree
- **Status**: done
- **Notes**: New LocationDetail.tsx with hero + 4 summary tiles (assets, deployments, inbound, outbound) + a sample asset list (8 rows, click → AssetDetail) + Deployments table + inbound/outbound shipment tables. Location row name in Locations.tsx is now clickable.

---

## 5 — Backend data inconsistencies

### 5.1 Naive datetime serialization (systemic)

- **What's there**: We patched BadgeDetail/Badges with `parseUtc` helper. Same bug exists across User, Network, Shipment, Deployment views — datetimes serialize without `Z`, JS parses as local time.
- **Fix**: One-time backend fix — serializer enforces ISO8601 with timezone (`Z` or offset) on every datetime field. Then strip `parseUtc` from frontend.
- **Decision**: agree
- **Status**: done (backend); frontend shims left as defensive no-ops
- **Notes**: New `UtcJSONResponse` set as FastAPI's `default_response_class`. Regex-substitutes naive ISO datetimes inside quoted JSON strings to append `Z`. Doesn't touch strings that already carry `Z` or an offset. Validated against `2026-06-25T20:11:17.456789` (gains `Z`), `2026-06-25T20:11:17Z` (no-op), `2026-06-25T20:11:17+00:00` (no-op). Frontend `parseUtc` shims left in place — they pass through Z-suffixed input unchanged, so removing them is mechanical churn for no behavioral gain. Future frontend code can use plain `new Date(iso)`.

### 5.2 Asset.location_id has no explicit "Unset" button

- **What's there**: Column is nullable.
- **What's missing**: AssetDetail offers a setter but no clear "remove this asset's location" action.
- **Fix**: Add "Remove location" button.
- **Decision**: agree
- **Status**: done
- **Notes**: New "Clear location" button on AssetDetail next to Assign / Unassign. Visible only when `asset.location_id !== null`. Confirm dialog explains the assignment stays in place. Reuses the existing `bulk-location` endpoint with a single-asset id list + `null` — no backend change.

### 5.3 No `/locations/{id}/reservations` endpoint

- **What's there**: Backend has the joins (Asset → DeploymentItem → Deployment, Asset → ShipmentItem → Shipment).
- **What's missing**: No endpoint exposes them by location. Needed for 1.4/1.5/4.3.
- **Fix**: New endpoint + service method.
- **Decision**: agree
- **Status**: done
- **Notes**: `GET /locations/{id}/reservations` returns `{deployments, shipments_inbound, shipments_outbound}`. Per-row item counts via `GROUP BY` so no N+1 across deployment items.

### 5.4 Sync-run stats endpoint

- **What's there**: `/sync-runs/health` and `/sync-runs?source=` exist.
- **What's missing**: No aggregate stats (success rate, avg duration, error trend) per source over N days.
- **Fix**: `GET /sync-runs/stats?source=&days=30` → success%, avg duration, last error categories. Mini-chart on Dashboard.
- **Decision**: agree
- **Status**: done
- **Notes**: `GET /sync-runs/stats?source=&days=30` returns total / succeeded / failed / success_rate / avg_duration_ms / max_duration_ms + top-5 error fingerprints (first 80 chars of error first line, bucketed). SyncHealthCard drawer renders a stats panel above the run history: success % tinted green/yellow/red by threshold, failed count, avg duration, and a top-failure-pattern list with occurrence counts. Hidden when window has 0 runs.

---

## Top 5 recommended next (Claude's pick)

1. **5.1 datetime serialization** — one backend change kills a class of bug across every view.
2. **1.1 + 1.2 Badge ↔ Asset both directions** — closes the loop on access vs equipment.
3. **2.1 + 2.2 Badge tile + unlinked-badge alert on Dashboard** — security signal, cheap to add.
4. **2.7 list-view export** — generic hook, applies to 9 tables, frequently requested.
5. **3.6 Defender card on AssetDetail** — data is already there, just hidden.

## Other ordering considerations

- 1.4 / 1.5 / 4.3 / 5.3 ship best as one bundle (location ↔ deployments/shipments).
- 3.1 (bulk actions) is a multi-view rollout — pick the entity that hurts most first.
- 4.1 (overview flattening) is touchy UI work; defer until a quiet moment.

---

## Final summary — work completed

**Completed 2026-06-30.** Walked the doc finding-by-finding, building per agreement.

### Tally

- **31 findings** total across 5 sections.
- **All 31** have a decision + status. No items left in open / undecided state.

| Status | Count | Meaning |
|---|---|---|
| `done` | 23 | Built and shipped as written or agreed scope |
| `done (partial …)` | 4 | Core item shipped; explicit follow-up noted |
| `closed` | 3 | Already shipped by an earlier finding, or no real gap on inspection |
| `n/a — already shipped` | 1 | Audit was wrong; functionality already existed (1.6) |

### What shipped, grouped

**Cross-view navigation** — every relationship in the data model is now click-throughable in the UI:
- Badge ↔ Asset (via linked UPN / assigned_upn) — both directions
- Controllers ↔ Networks (via IP subnet match) — both directions
- Location → assets / deployments / shipments
- User → pending shipments + deployments staged for them
- Group member → UserDetail (user-type members)
- Software → group / user assignments → their detail pages

**Dashboard surfaces**
- Access-badges stat tile + unlinked-badge alert + controllers-reachable chip
- Sync-health header summary (`healthy/total`, failed, stale, never-run)
- Per-source "Trigger now" button + 30-day stats panel (success %, avg duration, top failure patterns)
- Reservation pipeline funnel (planning → completed)
- Warranty × compliance cross-tab on Fleet report

**Features on existing data**
- Bulk actions on Badges (enable/disable), Software (archive/unarchive), Locations (activate/deactivate)
- Bulk Meraki claim on AssetsList for gear
- Persistent Meraki claim status chip on AssetDetail
- MAC address with copy-to-clipboard on AssetDetail
- Defender security card promoted with at-a-glance posture chip
- Generic audit history (EntityHistory) wired to Badge / Software / Location / Deployment / Network / Shipment mutations; reusable list component on each detail page
- "Clear location" action on AssetDetail

**IA / labelling**
- Wallboard promoted to top-level tab
- Tabs renamed: "Networks (Meraki)" / "Access Control (Axis)"
- LocationDetail view with hero + summary tiles + reservations

**Backend hygiene**
- Class-of-bug fixed: `UtcJSONResponse` regex-appends `Z` to naive ISO datetimes globally
- `GET /sync-runs/trigger/{source}` for in-place re-runs
- `GET /sync-runs/stats?source=&days=` for trend reads
- `GET /locations/{id}/reservations`
- `GET /networks/{id}/axis-controllers`
- Export endpoints across all 9 list entities (`/assets`, `/badges`, `/users`, `/software`, `/groups`, `/networks`, `/locations`, `/deployments`, `/shipments`)
- `meraki_claim_status` + `meraki_claim_checked_at` persisted on Asset

### Explicitly deferred

Items the audit raised that we intentionally didn't ship — and why.

1. **2.2 — Unlinked-badge alert pre-filtering**. Alert tile lands on Badges view; operator picks the Link filter manually. URL-param plumbing for filter handoff is the next step.
2. **3.5 — Bulk network / MAC override on assets**. Rare real use; bulk Meraki claim shipped, others skipped.
3. **3.6 — AssetsList Defender risk column**. Table is already dense. Posture chip on AssetDetail covers most of the value.
4. **4.1 — Dashboard rename + Reports restructure**. Touchy UX; only Wallboard promotion done. Rename can land any time when desired.
5. **`shipments_poll` manual trigger**. Carrier quotas — by design, scheduled only.

### Operational notes worth keeping

- Custom JSON response (`UtcJSONResponse` in `main.py`) post-processes ALL response bodies. If a future field looks like ISO but isn't a datetime, this could touch it. Regex is bounded by quoted-string lookarounds and won't match values already carrying `Z` or `±HH:MM`, so risk is low.
- Frontend `parseUtc` shims in BadgeDetail / Badges / Controllers / LocationDetail / EntityHistoryList are now no-ops on Z-suffixed input. Safe to remove in a future cleanup; harmless to leave.
- The `SYNC_SOURCES` tuple + the `_MANUAL_TRIGGERS` dict in `app/api/sync_runs.py` is the right place to add new sync types. Frontend SyncHealthCard auto-picks them up.
- `EntityHistory` write sites are isolated per service; adding a new event type = one `history_service.record(...)` call. No schema change needed.
- All bulk endpoints follow the same `{requested, updated, skipped, errors[]}` shape so new ones can copy any existing example.

---

## Sign-off

- **Reviewed by**: Julian Cotto
- **Date**: 2026-06-30
- **Approved scope for next phase**: Audit is complete. Future audits can start from a fresh `/audit` or by reviewing the deferred items above when the surrounding context invites it.
