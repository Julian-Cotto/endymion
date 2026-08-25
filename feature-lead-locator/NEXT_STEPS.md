# Lead Locator — remaining work

Status as of Phase 2 complete. Backend data layer + source adapters done and
verified against live data + real PostGIS. This file is the map of everything
left.

---

## Where things stand

**Done (Phase 1 + 2):**

- Feature scaffolded (`feature-lead-locator/`, backend :8600 / frontend :3600),
  wired into `SETUP.md`, `run_leads.sh`.
- PostGIS on :5435 (own `docker-compose.yml`), migration `0001_initial`
  verified up/down/up with zero drift.
- ORM models: `LeadSearch`, `HexCell`, `Poi`, `CensusTract`.
- Source adapters, all behind protocols in `app/infrastructure/sources/base.py`:
  - `TigerwebGeocoder` — zip/city → real polygon + FIPS (live-verified)
  - `OverpassPoiSource` — OSM POIs + category mapping, retry + mirror failover
  - `CensusAcsSource` + `TigerTractGeometrySource` — demographics + tract geometry
  - `ModeledTrafficSource` — free traffic proxy
- 87 tests passing (HTTP mocked). Two pre-existing scaffold bugs fixed.
- End-to-end chain proven: `90210` → 38 cells → 483 POIs → scored in ~6s.

**Done (Phase 3 — scoring engine):**

- `app/domain/tiling.py` — H3 tiling of the true boundary, cap-driven
  coarsening (down to res 5), `AreaTooLargeError` on overflow, centroid
  fallback for sub-cell areas.
- `app/domain/scoring.py` — the four-term opportunity model
  (`traffic + demand - saturation + anchor_pull`), each term min-max
  normalized within the search, full per-cell breakdown persisted.
  Resolved the two open questions: `anchor_pull` is non-overlapping with
  `traffic_proxy` (anchor-class POIs only, wider radius); `saturation` uses a
  configurable competitor category set (default retail/food/grocery).
- `app/infrastructure/geo.py` — the single place the (lat,lon)↔(lon,lat) flip
  happens; cell→tract assignment via STRtree.
- `app/infrastructure/repositories.py` — PostGIS read/write for all 4 models,
  bulk upserts for the shared caches, replace-not-duplicate cell writes.
- `app/services/lead_search_service.py` — the full pipeline the API + worker
  both call; owns one transaction per run, marks status pending→scoring→
  complete/failed, degrades demographics gracefully.
- 36 new tests (123 total passing), incl. 5 PostGIS integration tests.
- Verified end to end against live PostGIS: `90210` → 38 cells scored and
  persisted, re-score replaces (not duplicates), failure path marks `failed`.

**Not built yet:** the API surface, the worker/job wiring, the entire frontend.

---

## Blockers / things needed from you

| # | Item | Why it matters | Effort |
|---|---|---|---|
| 1 | **Census API key** → set `CENSUS_API_KEY` | ACS now requires a key for *every* request. Without it the demand term is absent from all scores. Free + instant: https://api.census.gov/data/key_signup.html | 2 min |
| 2 | **Commit decision** | Nothing is committed. `SETUP.md` also carries your pre-existing Reports Layering edits in the same diff. | — |
| 3 | **Submodule vs in-tree** | `feature-lead-locator/` is in-tree. Every other feature is a git submodule, which needs a GitHub repo (`endymion-lead-locator` or similar). Currently matches how `document-compliance-*` live. | — |
| 4 | **Docker WSL integration** | Was off at Phase 2 start; you turned it on. Keep it on — PostGIS is mandatory, no zero-service mode. | done |

Items 1 is the only true blocker (and only for the demand term — everything
else works without it). 2–3 are decisions, not blockers.

---

## Phase 3 — Scoring engine — DONE ✅

The core IP. Turns a resolved area into ranked, explainable hex cells.

**New files (all unmanaged — safe from scaffold upgrades):**

- `app/domain/scoring.py` — the opportunity model
- `app/domain/tiling.py` — H3 tiling of a boundary, with the res-8/9 +
  `max_cells_per_search` guardrails already in `SourceSettings`
- `app/services/lead_search_service.py` — orchestrates geocode → tile → gather
  → score → persist
- `app/infrastructure/repositories/` — PostGIS reads/writes for the 4 models
- `tests/test_scoring.py`, `tests/test_tiling.py`

**The model** (already sketched, weights provisional):

```
opportunity(cell) =
    w1 * traffic_proxy      # from ModeledTrafficSource (built)
  + w2 * demand             # ACS pop density + income + households, per tract
  - w3 * saturation         # competitor POIs already serving the cell
  + w4 * anchor_pull        # nearby strong traffic generators
```

Each term already has a home column on `HexCell` (`traffic_proxy`, `demand`,
`saturation`, `anchor_pull`) plus a `score_breakdown` JSONB for the drill-down.

**Work items:**

1. **Tiling** — `polygon_to_cells` over `ResolvedArea.tiling_rings()`. Enforce
   `max_cells_per_search`; if exceeded, either coarsen resolution or reject
   with a clear message (decide which). `log()` the drop, never silently cap.
2. **Demand term** — assign each cell's centroid to the tract that contains it
   (PostGIS `ST_Contains`), pull `population / area_land_sq_m`, income,
   households. Normalize within the search. Handle `None` (ACS-suppressed) as
   unknown, not zero.
3. **Saturation** — count same-category competitor POIs in/near the cell. What
   counts as a "competitor" is domain-specific (retail vs food vs grocery) —
   needs a decision on the target vertical.
4. **Anchor pull** — the strong-generator half already lives in the traffic
   proxy's category weights; decide whether anchor_pull is a distinct term or
   folded in. (Currently double-risk — resolve before tuning.)
5. **Normalization + weighting** — min-max or z-score each term within the
   search, combine with weights. Persist per-cell terms + breakdown.
6. **Ranking** — fill `HexCell.rank` by score desc.

**Open design question:** the weights `w1..w4` and category weights in
`traffic.py` are guesses. They can't be validated without a measured feed
(Placer/SafeGraph) or ground-truth. Ship with defaults, expose them as search
params, and revisit if/when a paid feed lands.

---

## Phase 4 — API surface (next)

Endpoints under `/api/leads` (base already wired). New router files are
unmanaged; don't reuse the scaffold's `feature.py` sample routes.

- `POST /searches` `{query, h3_resolution?, weights?}` → creates `LeadSearch`
  (status `pending`), publishes `LeadSearchRequested`, returns id. **202**, not
  a blocking score.
- `GET /searches/{id}` → status + counts (poll target while `scoring`)
- `GET /searches/{id}/cells?bbox=` → GeoJSON hex FeatureCollection for the map
- `GET /searches/{id}/leads?limit=` → ranked list (table view)
- `GET /searches/{id}/cells/{h3}` → drill-down: score breakdown, nearby POIs,
  tract demographics
- `GET /searches/{id}/pois?bbox=` → anchor overlay
- Error contracts: `AmbiguousQueryError` → **409** with candidates;
  `MissingCensusKeyError` → **200 with a `demographics_available: false`**
  flag rather than a hard failure (searches still work without it).

**Contracts:** define request/response schemas in `app/schemas/leads.py`;
update `contracts/api-contract.md` and the event schemas referenced in
`lead-locator-feature.json` (`LeadSearchRequested`, `LeadSearchScored`).

---

## Phase 5 — Async scoring (worker + job)

The scaffold already generated the stubs:

- `workers/score_on_search/handler.py` (`create_if_missing` — ours to fill) —
  consumes `LeadSearchRequested`, runs the Phase 3 service, flips status to
  `complete`/`failed`, publishes `LeadSearchScored`.
- `jobs/refresh_source_caches/runner.py` (`create_if_missing`) — nightly (cron
  `0 3 * * *`, already in the feature JSON) refresh of OSM/ACS caches for
  active regions so scoring reads warm data.

**Local reality:** there's no message bus running locally. Decide how the API
triggers scoring in dev — simplest is an in-process background task
(FastAPI `BackgroundTasks`) that calls the same service, with the
worker/event path reserved for deployed environments. Mirror how
reports-layering handles its `snapshot-on-publish` (immediate refresh locally,
event-driven in prod).

---

## Phase 6 — Frontend

`feature-lead-locator/frontend`, Vite/React on :3600. Nothing map-related
exists yet — only the scaffold's sample components.

**Deps to add:** `maplibre-gl`, `deck.gl` (`@deck.gl/react`,
`@deck.gl/aggregation-layers` for H3HexagonLayer), `h3-js`.

**Screens:**

1. **Search bar** — zip/city input; on `409 ambiguous`, show candidate chips.
2. **Ranked lead map** (the hero, per the original decision) — MapLibre base +
   deck.gl `H3HexagonLayer` colored by score, fit to search bbox. Show a
   "modeled estimate, not measured foot traffic" disclaimer (the
   `is_measured=false` flag exists for exactly this).
3. **Drill-down panel** — click a hex → score breakdown bars, nearby POIs,
   tract demographics. Show "demographics unavailable — no Census key" when the
   flag says so.
4. **Ranked list** — synced to the map, sortable.

**Base map tiles:** MapLibre needs a style/tile source. OSM raster tiles or a
free vector style (decide; some need a key even when "free"). Keep it in an env
var so it's swappable.

**Auth:** wire `VITE_API_BASE_URL` (already `:8600`) + the shell mock-auth
pattern the other frontends use.

---

## Cross-cutting / tech debt

- **Weights are unvalidated guesses.** Flagged in Phase 3. The whole point of
  the pluggable `TrafficSource` is that a measured feed replaces them — until
  then, treat every score as ordinal within one search, never absolute.
- **Parcel/ownership data is out of scope for MVP.** "Leads" = ranked hex
  cells, not deed-level parcels. Real acquisition targets need a parcel source
  (Regrid, county GIS) — a whole later layer. `HexCell` is the unit today.
- **Scaffold drift.** See [docs/scaffold-drift.md](docs/scaffold-drift.md).
  Before any `scaffold apply --upgrade`, re-read that file — two managed-file
  edits, if reverted, make autogenerate emit destructive migrations.
- **International.** US-only by construction (Census + TIGER). Out of scope.
- **Overpass is a shared free endpoint.** Fine for dev; a production build
  should consider a self-hosted Overpass or a paid POI source. Retry + mirror
  failover is in place but it's still someone else's rate limit.
- **`example_records` table + sample endpoints** are scaffold placeholders.
  Drop them once real endpoints exist (migration + model + `feature.py`).

---

## Suggested order

1. ~~Phase 3 scoring~~ — done.
2. Get the Census key (2 min, unblocks the demand term — scoring runs without it
   but demand is 0 everywhere until it's set).
3. Phase 4 API + Phase 5 local trigger together (small now that scoring exists;
   the service is the single entry point they both wrap).
4. Phase 6 frontend — the payoff, but pointless before there's scored data to draw.
5. Decide submodule + commit at any clean point.
