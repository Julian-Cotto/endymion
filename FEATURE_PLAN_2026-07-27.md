# Feature plan — device hygiene reports + enroll enhancement (2026-07-27)

Five items. 1/2/5 are **read-only exception reports** (share a pattern: a
`report_service` function + endpoint + a Reports sub-tab). 3 is a
report + a small SoftwareDetail add. 4 is an **Enroll flow** change.

Status legend: `todo` / `in-progress` / `done`. Decision: `agree` / `revise` / `later`.

## Locked decisions (2026-07-27)

- **Placement:** items **1, 2, 5** ship as views under a **new "Compliance"
  sidebar group** (not Reports sub-tabs). New nav section between People and
  Logistics (or after Infrastructure) — TBD on exact position. Items get their
  own top-level view kinds + routes (`/compliance/...` or flat `/naming` etc.).
- **Build order:** **2 → 5 → 1 → 3 → 4.**
- Each item still resolves its own open decisions (below) when we start it.

---

## 1 — Flag "bad" devices (name ≠ primary user) — ✅ done

**Shipped 2026-07-27.** `report_service.naming_mismatches` +
`GET /reports/naming-mismatch?hard_only=&asset_type=&location_id=`. Compliance
→ **Naming** view (`/naming`). Defaults used: generic **strip-before-last-dash**
prefix handling; expected token from **UPN localpart AND** first-initial+surname
of the display name (either exact match = OK); **fuzzy** (one contains the other)
= review flag, **mismatch** (no relationship) = hard flag; scope
laptop/desktop/thin_client, assigned + named, non-archived, non-retired/lost.
Filters: severity (all/hard/fuzzy, client-side), type, location, search. Stat
tiles: flagged / hard / fuzzy. Tested: exact-OK, display-name fallback
(jsmith↔John Smith), hard mismatch, fuzzy (jd↔jdoe), out-of-scope skipped,
hard_only. **Persisted ignore/acknowledge list = fast follow (not built).**

**Goal.** Flag laptops/desktops where the Intune device name doesn't match
the assigned user. Convention: `<company>-<firstinitial><lastname>` e.g.
`hrg-jdoe` for user `jdoe@…`.

**Data (confirmed).** `Asset.intune_device_name`, `Asset.assigned_upn`,
`Asset.asset_type`, `Asset.status_code`; `IntuneUser.user_principal_name`,
`display_name`. ⚠️ No `given_name`/`surname` on IntuneUser — derive the
expected token from the **UPN localpart** (`jdoe`) with `display_name`
(first-initial + surname) as a fallback.

**Logic.**
- Scope: `asset_type in (laptop, desktop, thin_client)`, `assigned_upn` set,
  `intune_device_name` set, non-terminal status.
- `expected` = normalise(UPN localpart) e.g. `jdoe`.
- `actual` = device name lowercased, strip the company prefix (drop everything
  up to & incl. the last `-`, or a configured prefix list), strip non-alphanum.
- Flag when `actual != expected` (exact by default; optional fuzzy "contains").
- Reasons: `name_mismatch`, `named_but_unassigned` (device looks personal but
  no assigned_upn), `prefix_unknown`.

**Backend.** `report_service.naming_mismatches(db, *, prefixes, strict)` →
rows `{asset_id, device_name, assigned_upn, user_display, expected, actual, reason}`.
Endpoint `GET /reports/naming-mismatch`.

**Frontend.** New Reports sub-tab **"Naming"** (or standalone view): table of
flagged assets, row → AssetDetail; filter by reason; an **Acknowledge/ignore**
toggle to suppress known-good exceptions (shared devices, service accounts).

**Follow-up shipped 2026-07-27 — persisted acknowledge/ignore.** New
`naming_acks` table + `POST/DELETE /reports/naming-mismatch/{asset_id}/ack`.
Acks snapshot the device name + assigned user; report marks rows `acknowledged`
only while the snapshot still matches (a reassignment re-surfaces the mismatch —
tested). View: Acknowledge/Restore per row, "show acknowledged" toggle,
Acknowledged tile, acked rows dimmed. Counts reflect outstanding (unacked) only.

**Open decisions.** (a) Company prefixes list (`hrg`, …) — config vs inferred.
(b) Strict-equal vs fuzzy. (c) Which asset types.

---

## 2 — Check-in exceptions (stale Intune, configurable window) — ✅ done

**Shipped 2026-07-27.** `report_service.checkin_exceptions` +
`GET /reports/checkin-exceptions?days=&include_never=&asset_type=&location_id=`;
new **Compliance** sidebar group with the **Check-ins** view
(`/checkins`) — configurable day threshold, asset-type + location filters,
include-never toggle, stat tiles (exceptions / stale / never), row → AssetDetail.
Defaults applied: never-checked-in = its own flagged bucket (toggleable), 7-day
default, Intune-managed only (`intune_id` present).

**Goal.** Devices whose last Intune check-in is older than **N** days
(default 7), N configurable up/down.

**Data (confirmed).** `Asset.intune_last_check_in`, `intune_compliance`,
`assigned_upn`, `location_id`. (Dashboard already surfaces a fixed "stale >7d".)

**Backend.** `GET /reports/checkin-exceptions?days=7&asset_type=&location_id=&include_never=true`
→ assets where `intune_last_check_in < now - days` (and optionally `is null`),
with `days_since`, device, user, location, compliance.

**Frontend.** New Reports sub-tab **"Check-ins"**: a **number input for days**
(+ ≥/≤ toggle), asset-type and location filters, sortable by days-since.
Export button (reuse export pattern).

**Open decisions.** (a) Treat "never checked in" (null) as an exception or a
separate bucket. (b) Default window (7). (c) Only Intune-managed assets
(`intune_id` present).

---

## 3 — Users per software per company (vertical) — ✅ done

**Shipped 2026-07-27.** `GET /software/{id}/users-by-company` (direct
`principal_type='user'` assignments joined to `IntuneUser.company_name`,
grouped, count-desc). SoftwareDetail gains a **"Users by company"** section —
per-company subheader + count, each user → UserDetail; unknown company bucketed
as "— No company —". Company already shows on UserDetail. Global
software×company matrix not built.

**Follow-up shipped 2026-07-30 — group-membership expansion.**
`GET /software/{id}/users-by-company?include_groups=true` now expands each
group assignment's members live via `groups_service.list_group_members`, maps
each member to `IntuneUser.company_name` (uncached → "— No company —"), and
merges into the buckets deduped by user (**direct wins**; nested groups
skipped). Response is now an object `{groups, groups_expanded,
group_assignment_count}`; each user carries `via: "direct"|"group"`. Graph
unavailable → skipped gracefully (`groups_expanded=false`, direct only).
SoftwareDetail gets an **Include group members (N)** toggle, a `group` badge on
inherited users, and status copy reflecting expansion state. Tested: direct
grouping, graceful skip, and dedup/company-resolution via monkeypatched Graph
(Alice deduped, Eve→Acme via group, uncached Zed→No company, nested ignored).

**Follow-up shipped 2026-07-30 — global software×company matrix.**
`report_service.software_by_company_matrix(db, *, source)` +
`GET /reports/software-by-company?source=`. Cross-tab of distinct
directly-assigned users per (software × company); companies ordered by seat
count desc ("— No company —" last), per-row `counts` + `total`, plus a
`company_totals` footer row. New Inventory → Virtual nav item **By company**
(`/software-by-company`, `SoftwareByCompany.tsx`): sticky first column, source
filter, tiles (titles / companies / seats), row → SoftwareDetail. Tested
roundtrip (Acme 2 / Globex 1 / No-company 1; group assignment excluded; source
filter). Group expansion still per-software only (matrix stays direct).

**Goal.** For a Microsoft/Intune software item, see assigned users grouped by
**company** (vertical), and drill into the user. Company already shows on
UserDetail (`UserDetail.tsx:372`) ✔ — so this is the reporting piece.

**Data (confirmed).** `Software`, `SoftwareAssignment` (principal_type user),
`IntuneUser.company_name`. Direct (per-user) assignments join cleanly to a
company. Group-assigned software would need member expansion (heavier — phase 2).

**Backend.** `GET /software/{id}/users-by-company` →
`[{company, count, users:[{id, display_name, upn, department}]}]` (direct
assignments, `principal_type='user'`, joined to `IntuneUser.company_name`).
Optional cross-tab `GET /reports/software-by-company` (software × company matrix).

**Frontend.** SoftwareDetail: a **"By company"** grouped breakdown of assigned
users (collapsible per company), each user → UserDetail. Optionally a Reports
sub-tab with the matrix.

**Open decisions.** (a) Direct assignments only (v1) vs expand group membership.
(b) Per-software drill-in vs a global software×company matrix (or both).
(c) "Microsoft software section" = source `intune` filter — confirm.

---

## 4 — Enroll: pick location first + location-scoped free devices — ✅ done

**Shipped 2026-07-27.** EnrollEmployee's Assets step gains an **Employee's
location** searchable picker; choosing a location reveals a **"Free at
&lt;location&gt;"** table of unassigned assets there (`listAssets({location_id,
available_only})`), each with an **Assign** button that sets `assigned_upn` via
`POST /assets/{id}/assign` (inventory assignment — distinct from the Intune
staging-pool path, which stays as-is). Assigned rows drop off the free list.
No backend change (reused existing endpoints).

**Goal.** In Enroll, add a **Step 1 = pick location** where the employee will
sit; the assign-device step then also offers **free devices at that location**,
alongside the existing warehouse/staging pool.

**Data (confirmed).** `listAssets({ location_id, available_only })` returns free
assets at a location. Two assign paths already exist:
- Staging pool → `POST /users/{id}/devices/assign` (Intune primaryUser).
- Inventory asset → `POST /assets/{id}/assign` (sets `assigned_upn`).

**Logic / flow.** Enroll becomes: pick employee → **pick location (new)** →
Assign assets shows **two sources**: (a) "Staging pool" (existing, Intune) and
(b) "Available at `<location>`" (free inventory assets: `available_only`,
`location_id`). Picking from (b) assigns via the inventory endpoint
(`assigned_upn`); (a) stays the Intune primaryUser path.

**Backend.** Mostly reuse (`listAssets` + both assign endpoints). Possibly a
convenience `GET /assets?location_id&available_only` filter tweak if needed.

**Frontend.** EnrollEmployee: add a location `Select` (searchable) step; add a
second devices table "Available at `<location>`" driven by `listAssets`; wire
its assign button to the inventory-assign service; refresh on assign.

**Open decisions.** (a) "Free" = `assigned_upn is null` + active + not reserved —
confirm. (b) Location step before or after employee (default: after employee,
before assets). (c) Should the location also filter the software step? (likely no).

---

## 5 — Offsite devices (Defender IP not on a known in-house subnet) — ✅ done

**Shipped 2026-07-27.** `report_service.offsite_devices` (reuses
`network_service.build_vlan_index`/`match_ip`) +
`GET /reports/offsite-devices?seen_within_days=&asset_type=`. Compliance →
**Offsite** view (`/offsite`): stat tiles (offsite / on-public-IP / subnets
indexed), last-seen + type filters, table with a public/private IP badge,
row → AssetDetail. Guards the "no subnets indexed ⇒ can't determine" case
(returns empty + a warning banner rather than flagging everything). Chose the
simple definition (IP not in any known VLAN subnet); Meraki-sighting-mismatch
left as a possible phase 2.

**Goal.** Find devices whose **last Defender-reported IP** isn't within any
known in-house network subnet (i.e., remote/offsite).

**Data (confirmed).** `Asset.defender_last_ip`, `defender_last_seen_at`;
`network_service.build_vlan_index(db)` + `match_ip(ip, index)` (the same
matcher the asset-locator uses).

**Logic.** For assets with `defender_last_ip` set (and optionally seen within a
staleness window), if `match_ip(ip, index)` is `None` → **offsite**. Return
device, user, `defender_last_ip`, `defender_last_seen_at`, location. Public
(non-RFC1918) IPs are always offsite.

**Backend.** `report_service.offsite_devices(db, *, seen_within_days=None)`
reusing `build_vlan_index`/`match_ip`. Endpoint `GET /reports/offsite-devices`.

**Frontend.** New Reports sub-tab **"Offsite"**: table (device, user, last IP,
last seen, home location), row → AssetDetail.

**Follow-up shipped 2026-07-27 — Meraki mode.** `offsite_devices` now takes
`mode=subnet|meraki`. `meraki` compares Defender IP to the latest Meraki client
sighting for the device's MAC (in-house-seen IP) and flags divergence — the
user's literal "Defender IP ≠ what the in-house network last saw." View gets a
**Definition** toggle + a "Last in-house IP" column in Meraki mode. Tested both
modes. Response unified to `{mode, total, index_count, index_label, rows}` with
`inhouse_ip`/`inhouse_last_seen_at` per row.

**Follow-up shipped 2026-07-30 — tuning resolved.** (a) Private-non-corp ranges:
now a user lever, not a hardcode — `public_only` param (`?public_only=true`) on
both modes restricts to public (non-RFC1918) Defender IPs, dropping private
off-subnet IPs (unindexed corp subnets / home LANs → false positives). View gets
an **IP scope** toggle (Any off-network / Public only). (b) Staleness: already a
first-class filter (`seen_within_days`, 1–365, default any). Tested both modes.

---

## Shape & sequencing

- **1, 2, 5** share the exact same skeleton (report_service fn → `/reports/*`
  endpoint → a Reports sub-tab) → cheapest to batch together; ~1 backend fn +
  1 view each. Could add a **"Hygiene"/"Exceptions"** grouping of these tabs.
- **3** = 1 endpoint + a SoftwareDetail section (company already on UserDetail).
- **4** = Enroll UI change + reuse of existing endpoints (no new report).

Suggested order: **2 → 5 → 1 → 3 → 4** (2 & 5 are the most mechanical and highest
signal; 1 needs the naming-convention decisions; 4 is the biggest UI change).
