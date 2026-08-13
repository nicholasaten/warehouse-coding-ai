# AI Warehouse Layout & Coding Management System

Generates Warehouse IDs and Location IDs from the company's fixed coding
formulas (SOPs), validates uploaded warehouse/location data, and explains
optimization opportunities (merge candidates, redundant/underutilized/
overloaded warehouses) with AI-written reasoning. The coding formulas
themselves are business rules, configured by an admin -- nothing in this
system ever invents or modifies them.

## Where this came from

Built from three real files: `Formula Warehouse and Location.pptx` (the
formula spec), `RSUS Mapping.xlsx` (a real hospital's raw-to-final mapping,
i.e. "the result we want"), and `RSUS Raw.xlsx` (that hospital's real
current/legacy data). The formula below was derived from the PPTX and then
verified against every single row of the Mapping file -- see
`api/tests/test_id_generator_service.py`, which sweeps all 61 real
warehouse rows and all 333 real location rows and asserts an exact string
match, not just a handful of hand-picked examples. `sample-data/` carries
copies of both Excel files so that regression sweep can never silently
drift from the real reference data.

## The confirmed formula

**Warehouse ID** = `{Site}-{WHType}{WHCode}[{DuplicateLetter}]`

e.g. `RSUS-A01A` (Site=RSUS, WHType=A/Non-General, WHCode=01/Pharmacy
Mainstore, duplicate letter A). The duplicate letter is entirely **omitted**
if only one warehouse exists for that Site+WHType+WHCode combination (e.g.
`RSUS-A02`, no other Pharmacy Outpatient warehouse exists) -- but as soon as
a second one is added, **every** warehouse in that group gets relettered
starting from A, not just the new one. `warehouse_service.create_warehouse()`
handles that relettering side effect for you; it's not just a formatting
function.

**Location ID** = `{ShortSiteCode}{WHType}{WHCode}[{DuplicateLetter}]-{LocType}[{Seq:02d}]`

e.g. `USA01A-A05` (ShortSiteCode=US, no hyphen before the warehouse portion,
hyphen only before LocType+Seq). Two edge cases, both confirmed by real
data, not guessed:

- **The trailing sequence is entirely omitted** for a "whole warehouse"
  location type (e.g. `USB12-B`, not `USB12-B00`) -- some warehouses (mostly
  General Items / corporate departments) are tracked as one undifferentiated
  location, so there's nothing to number. `LocationTypeConfig.is_whole_warehouse`
  marks which LocType code means this, since it differs by scheme (General's
  "B" vs Non-General's "H").
- **A reserved sequence 99** is a fixed catch-all bucket ("STAGING RECEIVE")
  for uncategorized racks -- never renumbered into the normal sequence, and
  multiple raw racks with no clear category all collapse into this one
  location per warehouse.

`ShortSiteCode` (e.g. RSUS -> US, SHMD -> MD, SHBP -> BP) looks like "last
two letters" from the three confirmed examples, but is stored as an
explicit, separately-configured field on `Site` rather than derived
algorithically -- three examples isn't enough to trust as a universal rule
for a fixed business code.

## What's built

**Phase 0 -- the formula engine:**
- **Config module**: `Site`, `WarehouseTypeConfig`, `WarehouseCodeConfig`,
  `LocationTypeConfig`, `CategoryRackMapping` -- all admin-editable via
  `/config/*`, all scoped correctly by `warehouse_type_code` where the
  formula requires it (the same letter/number can mean different things
  under General vs Non-General). `scripts/seed_config.py` loads the real
  values extracted from the PPTX (insert-if-missing, never overwrites an
  admin's own edits on a re-run).
- **`Warehouse` / `Location` models + `/warehouses`, `/locations`** --
  creating either one auto-generates its code server-side via
  `id_generator_service`; you never type a code in by hand.
- **Auth**: JWT access token + httpOnly refresh cookie, same pattern as the
  sibling WMS Readiness Tracker project. Started as admin-only; became a
  real two-role system in Phase 5 below once the Review Workflow feature
  was requested.

**Phase 1 -- Excel upload ingestion (Step 3/4 of the brief):**
- `POST /uploads/warehouse-master` -- columns `Site Code`, `Warehouse Type
  Code`, `Warehouse Code`, `Warehouse Name`, `Description` (optional),
  `Capacity` (optional). Upserts on `(site, warehouse_type_code,
  warehouse_code, name)` -- **name is part of the key on purpose**: the
  formula allows several warehouses to share one type+code, disambiguated
  only by the auto-assigned duplicate letter, so name is the only column
  that tells them apart on a re-upload. Uploading a second, differently-
  named warehouse under an existing type+code correctly triggers the
  relettering side effect for the whole group, live through the upload
  path, not just the direct API.
- `POST /uploads/location-master` -- columns `Warehouse Code` (the
  already-generated warehouse ID), `Category Rack`, `Description`. Note
  this deliberately does **not** match the brief's illustrative
  `Zone/Rack/Bay/Level/Bin` example -- the real, verified formula doesn't
  use those fields at all, so the real files took priority over the
  brief's placeholder text.
- Two layers of duplicate handling, deliberately different: an **exact**
  `(warehouse, location_type, description)` repeat is rejected outright,
  nothing to do, it's already there. A **similar-but-not-exact** description
  goes to Phase 2 below instead of either extreme (auto-create or reject).
- Partial-success-per-row throughout, same pattern as the sibling project:
  one bad row never blocks the rest of a file, and every rejection names
  the row, column, and reason.

**Phase 2 -- AI-assisted merge suggestions (Responsibilities #3/#5/#9):**
- When an uploaded location's description doesn't exactly match an existing
  one in the same (warehouse, location type) but is textually similar
  (`difflib.SequenceMatcher`, same deterministic approach and 0.82
  threshold as the sibling project's fuzzy email-match feature -- no LLM
  call, free, exactly reproducible), the row is held as a `MergeSuggestion`
  instead of being auto-created **or** silently rejected.
- `GET /merge-suggestions?status=pending` -- each one carries a plain-English
  `reasoning` string (e.g. *"'DRUG - TABLET' is 96% textually similar to the
  existing location 'DRUGS - TABLET' (USA01-A01)..."*) -- the brief's
  "every recommendation must include a clear explanation" requirement.
- `POST /merge-suggestions/{id}/approve` -- confirms it's the same place;
  creates **no** new Location.
- `POST /merge-suggestions/{id}/reject` -- confirms it's genuinely
  different; creates the real Location the normal way, through the same
  `id_generator`-backed path as everything else.
- **Nothing merges or gets created automatically** -- this was the explicit
  "suggest, never auto-apply" decision from Phase 0, now actually built,
  not just designed.

**Phase 3 -- Capacity analysis + validation summary (Responsibilities #4/#5/#6):**
- `GET /dashboard/summary` -- Warehouse Summary (total/active/empty/
  underutilized/overloaded/no-capacity-set) + Location Summary (total,
  pending duplicate review), matching the brief's dashboard spec as closely
  as is honestly measurable -- see the important limitation below.
- `GET /warehouses/{id}/capacity` -- per-warehouse detail (location count,
  capacity, occupancy rate, status).
- **Important, deliberately-stated limitation**: this system has no
  inventory/stock model -- it only knows whether a location's *code*
  exists, never how much physical stock sits there. "Occupancy" here is a
  proxy: `location_count / warehouse.capacity` (how many storage slots are
  defined vs. how many the warehouse is sized for), not "how full of goods
  is this warehouse," which the brief's wording implies but nothing in
  this system can compute without a real inventory feed. Thresholds:
  0 locations = empty; <30% = underutilized; >100% = overloaded.
- Most of what the brief calls "duplicate/format validation" turned out to
  already be prevented structurally rather than needing an after-the-fact
  check: `generated_code` is always server-computed, never accepted as
  user input, and duplicate warehouses/locations are blocked at the
  database level by unique constraints plus the upload pipeline's
  exact-match and merge-suggestion checks. Documented in
  `dashboard_service.py`'s own docstring rather than building fake checks
  for things that can't actually happen.

**Phase 4 -- Optimization recommendations (Responsibilities #7/#8/#9):**
- `optimization_service.py` finds candidates with plain SQL/Python, no LLM
  involved: **merge opportunities** (two active warehouses, same site +
  same warehouse type, both empty/underutilized, and consolidating one
  into the other wouldn't exceed either one's own capacity), **redundant
  warehouses** (active, zero locations), **underutilized**/**overloaded**
  singles not already covered by a merge suggestion (avoids saying the
  same thing twice with less context).
- `POST /recommendations/generate` -- runs that analysis and, only if
  anything was found, makes **exactly one** Groq call (`response_format:
  json_object`, one structured explanation per candidate returned in a
  single response) to write the reasoning -- never one call per
  recommendation. This was a deliberate cost/rate-limit concern raised
  directly, not an assumption: viewing recommendations via `GET
  /recommendations` afterward costs nothing, and generation only runs when
  explicitly triggered, never automatically on page load.
- **Graceful, no-invented-data fallback**: if `GROQ_API_KEY` is unset or
  the call fails for any reason, deterministic template explanations
  (built from the same real numbers) are used instead -- this feature can
  never fail to produce recommendations just because the AI layer is
  unavailable, same principle as the sibling project's AI Insight card.
- Recommendations are a fresh snapshot per generation, not a history table
  -- re-running replaces the previous set rather than accumulating.

**Phase 5 -- Warehouse & Location Review Workflow (requested as a follow-up
feature, not part of the original 10 AI Responsibilities):**
- **5a, the auth foundation**: `users.role` (`admin`/`pic`) + `users.site_id`
  (`NULL` for admin, required for `pic`, enforced by a DB `CHECK`
  constraint, not just application code). JWTs now carry `role`/`site_id`
  as claims. `POST /users` (admin-only) creates PIC accounts scoped to
  exactly one Hospital Unit (`Site`). Every existing `warehouses`/`locations`
  endpoint was rewired so a PIC's `site_id` silently overrides (never
  trusts) any `site_id` the client passes -- a PIC sees and can only ever
  touch their own Hospital Unit's data. `Location` has no `site_id` of its
  own, so its scoping joins through `Warehouse`.
- **5b, the Revision workflow itself** (the brief's actual 3 numbered
  items): a PIC never writes to `warehouses`/`locations` directly --
  `POST /revisions` is their only path, and it only accepts a fixed,
  small set of **descriptive** fields per entity (`name`/`description`/
  `capacity` for a Warehouse; `description`/`category_rack_raw` for a
  Location) -- never the formula-driving fields (`site_id`, type/code,
  `duplicate_letter`, `seq`, `generated_code`), so a revision can never
  desync the deterministic ID formula from the actual row. Every
  `Revision` snapshots `original_value` at submission time, holds the
  PIC's `proposed_value` + required `comment`, and stays `pending` until
  an admin acts:
  - `POST /revisions/{id}/approve` -- applies `proposed_value` as-is.
  - `POST /revisions/{id}/reject` -- entity untouched, requires a
    `rejection_reason`.
  - `POST /revisions/{id}/edit-approve` -- admin supplies their own
    `final_value` (may differ from the PIC's `proposed_value`); both are
    kept on the row so the history stays honest about what was actually
    asked for vs. actually applied.
  - `GET /revisions` -- the admin's full Review Queue (filterable by
    `status`/`entity_type`); a PIC calling the same endpoint only ever
    sees their own submitted revisions, never other PICs' requests.
  - Admin also got a **separate, direct** edit path -- `PATCH
    /warehouses/{id}` / `PATCH /locations/{id}`, same descriptive-fields
    scope plus `is_active` -- since the brief's item #1 ("Admin can
    review, edit, and revise") is a distinct power from reviewing a PIC's
    proposal, not routed through the Revision table at all.
  - `GET /warehouses` / `GET /locations` gained `is_active` and
    `has_pending_revision` filters (the latter computed per-request
    against the `revisions` table, since neither entity carries that flag
    itself) to back the brief's Admin Monitoring filter requirements
    (Hospital Code via existing `site_id`, Warehouse, Location, status,
    revision status).
- Verified with 10 new SQLite integration tests (submit/approve/reject/
  edit-approve, cross-site submission blocked with 403, formula-field
  submission blocked with 400, PIC-scoped queue visibility, admin
  direct-PATCH vs. PIC-blocked-403, `has_pending_revision` filtering) plus
  a full live pass against the real Neon database: a real PIC account
  proposed 4 real revisions against a real warehouse, and every reviewer
  action (approve, reject, edit-approve) was confirmed to produce exactly
  the documented effect on the real row -- then all of it (PIC account,
  test warehouse, its revisions) was deleted afterward, same
  verify-then-clean-up convention as every earlier phase.
- **5c, the frontend**, built as a follow-up in the same project: a new
  role-aware `/revisions` page -- admin sees the full **Review Queue**
  (status filter, per-request Approve/Reject/Edit & Approve, and full
  history for resolved requests: who submitted, when, the original →
  proposed diff, the reviewer's action, and the final applied value); a
  PIC sees **My Revisions**, a read-only list scoped automatically to
  their own submissions (the backend does the scoping, not the frontend).
  Warehouses/Locations pages gained: a role-aware action column (admin
  gets an inline **Edit** form calling the direct `PATCH` endpoint; a PIC
  gets an inline **Request Revision** form pre-filled with current values,
  disabled while a revision is already pending on that record), a
  `Revision Pending`/`Inactive` badge per row, and the Admin Monitoring
  filter row (Hospital Code, Status, Revision Status) from item #1. The
  post-login landing route is now role-aware too -- `/dashboard` stays
  admin-only on the backend, so a PIC lands on `/warehouses` instead
  (their `/dashboard` link is also hidden from the sidebar, along with
  the other admin-only pages).
  Verified: clean `tsc --noEmit`, clean `eslint .`, clean `npm run build`
  (8 static routes now, `/revisions` included). Confirmed live in the
  browser that all touched routes (including the new `/revisions`) still
  correctly redirect to `/login` with zero console errors when hit
  unauthenticated -- did **not** click through the authenticated app
  myself, same standing rule as Phases 0-4's frontend.
- **5d, a Users page** (admin-only, `/users`) so account creation no
  longer requires a raw API call: lists every user (name, email, role,
  Hospital Unit, status) and a create form wired to `POST /users`, same
  admin/PIC + conditional `site_id` validation as the API already
  enforces. 9 static routes now. Verified the same way as 5c -- clean
  `tsc`/`eslint`/`build`, and a live unauthenticated-redirect check
  confirming `/users` mounts and redirects cleanly with zero console
  errors.

**Phase 6 -- AI-assisted Raw Import** (requested as a follow-up: "so if
upload the raw data the apps can automatic generate as the mapping one?"):
uploading a legacy raw export (Organization/CodeStore/Store/CodeStoreRack/
StoreRack/ActiveStoreRack -- none of which are the formula's own fields)
directly through the normal Uploads page has always failed outright, since
that page expects data that's already coded. This phase adds a real bridge
from raw to coded, following the exact same "suggest, never auto-apply"
principle as the merge-suggestion engine and the Revision workflow --
nothing here ever creates a Warehouse or Location on its own:
- `POST /raw-import/upload` (site chosen explicitly, never inferred from
  the file's free-text Organization column) parses the file, groups rows
  into distinct legacy stores, and makes a **first round** of Groq calls
  suggesting a Warehouse Type Code + Warehouse Code per store -- but only
  ever from the **already-configured** valid pairs; any value the model
  returns that isn't a real configured pair is nulled back out before an
  admin ever sees it, a validated hard rule, not just a prompt instruction.
- `GET/POST /raw-import/warehouses/*` -- the admin's Review Queue for
  those suggestions: approve as-is, edit-and-approve (override the
  type/code, or supply one manually where the AI had no confident match),
  or reject. Approving goes through `create_warehouse()`, the exact same
  path a manual or file-upload warehouse creation uses.
- `POST /raw-import/batches/{id}/locations/suggest` -- a **second round**,
  triggered explicitly once warehouse review is done (can't run earlier:
  the valid Category Rack options are scoped by the warehouse's real type,
  which isn't known until its suggestion is approved). Covers every
  approved warehouse's raw rack rows; safe to call again later as more
  warehouses get approved, it only covers what's new.
- `GET/POST /raw-import/locations/*` -- same review pattern; approving may
  create a real Location, or -- if it's textually similar to one that
  already exists -- a MergeSuggestion instead, exactly like a normal
  Location Master upload would (reuses `find_similar_location`/
  `create_suggestion` directly, not a reimplementation).
- **Caught and fixed a real reliability issue against real data, not
  synthetic tests**: the first live pass against the actual 61-store,
  325-row `RSUS Raw.xlsx` showed the model silently skipping 5 of 61
  stores in one large batched call (near-duplicate-looking names like
  "EMERGENCY" vs "EMERGENCY NONCHARGEABLE" confuse it) -- the strict
  order/count-matching check correctly caught the mismatch and safely
  fell back to "no suggestion" for the *entire* batch rather than
  guessing which suggestion belonged to which store. Fixed properly, not
  by loosening the check: suggestions are now chunked into small batches
  (40 candidates/call) and matched back to their candidate by an explicit
  `index` field the model returns with each entry, so a bad chunk only
  blanks out those few rows, never the whole batch.
- Re-verified live end-to-end after the fix, real data, real Groq calls:
  all 61 stores got a real suggestion or an honest "no match", and the
  AI's confident suggestions matched the real, human-verified
  `RSUS Mapping.xlsx` ground truth exactly (e.g. EMERGENCY -> A/08,
  PHARMACY MAINSTORE DRUGS -> A/01). Ran the full approve/override/reject
  flow on both suggestion types against the real Neon database, confirmed
  the resulting Warehouse/Location codes were generated correctly through
  the normal `id_generator_service` path, then deleted all of it
  afterward -- same verify-then-clean-up convention as every phase.
- 13 new SQLite tests (fallback path, grouping, incomplete-row handling,
  approve/override/reject for both suggestion types, the merge-suggestion
  trigger path, idempotent location-suggestion generation).
- Frontend: a new admin-only `/raw-import` page -- upload form (file +
  Hospital Unit), a batch picker, a Warehouse Suggestions queue and a
  Location Suggestions queue (each with status filters and inline
  approve/override/reject actions), and a "Generate for approved
  warehouses" button for the second Groq round. 10 static routes now.
- **Few-shot grounding from confirmed history** (requested directly: "if i
  had the rsus already mapped by me can you make the ai learn the new
  answer?"): every approved suggestion -- the AI's own guess or an admin's
  override, doesn't matter which -- is fed back into FUTURE suggestion
  prompts as a confirmed example, drawn from every prior batch and every
  site (the naming conventions and Warehouse Type/Code meanings are the
  same across every Siloam hospital, so cross-site examples are valid
  signal). This is retrieval from data already in the DB, not model
  fine-tuning -- Groq's hosted API doesn't offer that, and it would be
  overkill for what's really a lookup problem. `confirmed_warehouse_
  examples`/`confirmed_location_examples` (public, not `_`-prefixed --
  meaningfully testable on their own) query prior `approved` suggestion
  rows; capped at 60 most-recent examples so the few-shot section stays
  small relative to the actual candidates being suggested. No new Groq
  calls added -- same two-round-per-batch structure, just enriched
  prompts. 2 new SQLite tests (confirms only `approved` rows count, and
  that the value stored is the FINAL applied one, not the AI's original
  guess, when an admin overrode it) plus a live check against the real
  Neon database: approved a real suggestion through the real API, then
  confirmed both example-query functions read it back correctly from live
  Postgres, and that a second real upload succeeds cleanly with the
  extra "Confirmed examples" prompt section included.
- **Warehouse-consolidation clustering** (requested directly: "so you can
  study how the answer to be like the file i share," pointing at
  `RSUS Mapping.xlsx`): studying that file closely surfaced a real gap --
  its `WH` sheet shows 61 legacy store names collapsing into only **48**
  real final warehouses, because billing/status variants of one physical
  department (e.g. "EMERGENCY" + "EMERGENCY NONCHARGEABLE") are meant to
  become ONE warehouse, not two. The feature as first built treated every
  distinct legacy store name as its own separate warehouse candidate,
  which would have produced extra, wrong duplicate-lettered warehouses.
  Fixed with a THIRD Groq call round, at upload time, before Type/Code
  suggestion: `_suggest_clusters` groups legacy names that are the same
  physical place under a different billing/status label. Simple keyword
  rules aren't reliable for this on their own (floor variants like
  "OPD 1ST FLOOR"/"OPD 2ND FLOOR" must NOT merge, but billing variants
  almost always should) -- confirmed by testing both directly against the
  real file, so this needs the AI's judgment, deliberately biased toward
  NOT merging when unsure (a missed consolidation just costs an extra
  warehouse; a wrong merge silently combines two different real places).
  `consolidated_legacy_names` (new column) records which legacy names got
  folded into each suggestion, shown in both the API response and the
  frontend card.
  **Live-verified against the real 61-store file and cross-checked row by
  row against `RSUS Mapping.xlsx`'s actual answer** -- 6 of the file's 10
  real consolidation groups matched exactly (Emergency, Dialysis,
  Laboratory, Radiology, Medical Rehab, Nutrition & Dietetics); 2 were
  safely under-merged (the Pharmacy Mainstore Drugs and Consumables
  families each split into two correctly-coded pairs instead of one group
  of 3-4 -- not wrong, just an extra warehouse instead of the ideal one);
  and 2 were genuinely over-merged (OPD pulled in "1ST FLOOR" and "ONE DAY
  CARE," which are real, different warehouses; Operating Theatre pulled in
  an unrelated Pharmacy Emergency Trolley item). Both wrong merges were
  caught by inspecting the suggestion queue and fixed by rejecting them
  through the normal reject flow -- exactly the safety net "suggest, never
  auto-apply" is meant to provide. **Known limitation, stated plainly
  rather than glossed over**: there's currently no way to partially
  accept a wrongly-clustered group (split some members back out while
  keeping the rest merged) -- rejecting discards the whole group, and the
  legacy stores in it would need a fresh upload or manual creation to
  re-approach individually. 2 new SQLite tests (a pure merge-logic test,
  and a no-AI-key-never-consolidates safety test).

**Phase 7 -- Admin hard delete for Warehouse/Location, plus a
self-service Hospital Unit form** (requested as a follow-up: "the admin
can change the warehouse or delete the warehouse and also the location"):
admin direct-edit (PATCH) and the PIC revision workflow already existed
from Phase 5 -- the one missing piece was an actual DELETE.
- `DELETE /warehouses/{id}` and `DELETE /locations/{id}`, admin-only,
  hard delete (not a soft `is_active` flip). A Warehouse delete cascades
  its Locations and any MergeSuggestions at the DB level.
- **Found and fixed a real FK gap before it could 500 on a real user**:
  the raw-import audit tables (`RawWarehouseSuggestion.created_warehouse_id`,
  `RawLocationSuggestion.warehouse_id`/`created_location_id`) had no
  `ondelete` behavior, so deleting any warehouse/location ever touched by
  the raw-import feature would have failed with a bare FK-violation 500.
  Migration `0009` sets `created_warehouse_id`/`created_location_id` to
  `SET NULL` (the audit row survives, its back-reference just goes null)
  and `warehouse_id` to `CASCADE` (that column is NOT nullable, so the
  audit row is removed along with its parent warehouse -- consistent with
  `warehouse_suggestion_id`, which already cascaded the same way).
  Live-verified with a real Groq-backed raw-import suggestion against
  Neon: approved it, deleted the warehouse it created, confirmed the
  suggestion row survived with a nulled reference instead of vanishing or
  500ing.
- Blocked by a still-pending Revision (409, "approve or reject it before
  deleting") -- an application-level check, since `Revision.entity_id` is
  polymorphic across two possible target tables and has no DB-level FK.
- **Deliberately does NOT re-letter surviving sibling warehouses or close
  Location sequence-number gaps on delete** -- stated as a real scope
  decision, not an oversight. Re-lettering a survivor would change its
  `generated_code`, and the system has no existing path to cascade that
  into its already-created Locations' own codes (a pre-existing gap in
  `create_warehouse`'s own relettering step, discovered while reasoning
  through this feature but explicitly left alone as out of scope).
- 7 new SQLite tests (cascade, pending-revision block, not-found, the
  no-relettering guarantee, location delete success/block/not-found) --
  had to turn SQLite's FK enforcement on explicitly in the test fixture
  (`PRAGMA foreign_keys=ON`), since it's off by default and would have let
  the cascade tests pass without exercising real FK behavior.
- Frontend: a Delete button (with a native confirm prompt describing what
  cascades) next to Edit in both the Warehouses and Locations tables,
  admin-only, matching the existing row-actions pattern.
- Also added a self-service **Add Hospital Unit** form on the Config page
  (`POST /config/sites` already existed; this phase just gave it a UI) so
  an admin doesn't need a one-off API call to onboard a new Hospital Unit.
- Live-verified the whole delete flow through a real public tunnel
  (see "Sharing a live link" below): created a disposable test warehouse,
  deleted it through the actual browser UI, confirmed both the confirm
  gate and the cascade worked end-to-end against real Neon.

**94 passing tests total** (101 including this phase's), including an
exhaustive sweep of every real reference-data row (not just samples),
SQLite integration tests for every phase's stateful logic, and full live
passes against the real Neon database for every phase -- the upload
pipeline, the merge-suggestion approve/reject flow, the dashboard
summary, and a real Groq-generated recommendation set (3 real merge
opportunities among 3 real warehouses, one live API call, real
natural-language reasoning returned for each).

### Sharing a live link

For a quick trial with someone outside the dev machine, this project uses
free **Cloudflare Quick Tunnels** (`cloudflared tunnel --url http://localhost:PORT`)
rather than a real deployment -- no account needed, but Cloudflare gives
these **no uptime guarantee**, and the URL changes every time the tunnel
process restarts.

**Standing rule: always share a production build, never `next dev`.**
`next dev` compiles each route on first visit and keeps a hot-reload
websocket open that fails repeatedly through the tunnel (visible as
constant retry spam in the tunnel's log) -- observed making `/raw-import`
take 6+ seconds to first load. `next build && next start -p 3001` fixed
both (0.47s load, no more retry spam).

Steps: `npm run build` in `web/`, start it with `npm start -- -p 3001`,
run two `cloudflared` tunnels (one for the backend on 8001, one for the
frontend on 3001), then point `web/.env.local`'s `NEXT_PUBLIC_API_URL` at
the backend tunnel URL and `api/.env`'s `CORS_ORIGINS` at the frontend
tunnel URL. Because frontend and backend then live on two different
`trycloudflare.com` subdomains, `COOKIE_SAMESITE` must be `none` (not
`lax`) or the httpOnly refresh cookie gets silently dropped on cross-site
requests, breaking silent session-resume on reload. `NEXT_PUBLIC_API_URL`
is baked in at build time, so the frontend needs a rebuild (not just a
restart) whenever the backend tunnel URL changes.

### Phase 8 -- Reassign a Location to a different Warehouse

Requested as a follow-up design discussion: an admin asked how to fix a
warehouse that was coded wrong, and separately how to combine two
warehouses into one without losing their Locations. `generated_code` is
deliberately never a free-text editable field (it's derived from
Site + WarehouseType + WarehouseCode + duplicate letter, and would let
someone type a code that doesn't match any real config or collides with
another warehouse). The answer for both cases turned out to be the same
existing move: create a warehouse with the right code, then move each
Location into it, then delete the old one.

- `POST /locations/{id}/reassign-warehouse`, admin-only, body
  `{warehouse_id}`. Recomputes the Location's `generated_code`/`seq`
  through the exact same `format_location_code`/`next_location_sequence`
  rules `create_location` uses, since the code embeds the warehouse's own
  type/code/duplicate letter -- never edited as a raw string.
- Guards: 404 if the Location doesn't exist, 400 if it's already in the
  target warehouse (avoids an ambiguous seq-recompute against its own
  current row), 409 if a Revision is still pending on it (same rule as
  edit/delete), and 400 if the target warehouse's `warehouse_type_code`
  doesn't have the Location's `location_type_code` configured (moving
  across warehouse types can genuinely make a LocationTypeConfig invalid,
  since that config is scoped by type) or 409 if the target already has
  its own whole-warehouse location of that type.
- Frontend: a "Move" button next to Edit/Delete in the Locations table
  (admin-only), opening a form that just picks the target warehouse --
  the code is always shown as computed, never entered.
- 8 new SQLite tests (successful move + code recompute, next-free-seq
  assignment in the target instead of reusing the source's own seq,
  same-warehouse block, pending-revision block, invalid location-type
  under a different warehouse type, whole-warehouse conflict, not-found
  for both the location and the target warehouse). 109 tests total.
- Live-verified through the real shared tunnel, in an actual browser:
  created two disposable warehouses (`ASRI-A01C`/`ASRI-A02`), created a
  Location under the first (`ASA01C-A01`), moved it to the second, and
  confirmed its code became `ASA02-A01` and its Hospital Code column
  updated to the new warehouse -- both the DOM update and a fresh read
  from Neon agreed. Cleaned up the disposable warehouses (which cascade
  their Locations) and the throwaway verification admin account
  afterward, same convention as every phase.

### Phase 9 -- Merge a Warehouse into another existing Warehouse

Direct follow-up to Phase 8: "if we combine 2 warehouses into 1 so the
location doesn't want to be deleted." Confirmed the workflow described
back to the user first (create the correctly-coded warehouse, move every
Location over, retire the old one) since it's exactly what Reassign
Warehouse already does one Location at a time -- this phase just wraps
that into a single admin action instead of clicking Move on every row.

- `POST /warehouses/{source_id}/merge-into`, admin-only, body
  `{target_warehouse_id}`. Moves every Location out of `source` into
  `target` via the same `reassign_location_warehouse` call the Move
  button uses (never a raw copy), then hard-deletes `source` -- it stops
  showing up in the list entirely, exactly as asked ("the warehouse not
  visible because merge to another warehouse").
- **Validates every Location can move BEFORE moving any of them** --
  pending Revision, `location_type_code` still configured under the
  target's `warehouse_type_code`, no whole-warehouse conflict -- so a
  large warehouse with one bad Location fails cleanly with nothing
  half-merged, rather than leaving some Locations moved and others
  stranded in a warehouse that's about to be deleted.
- Guards: 400 merging a warehouse into itself; 404/400 if source/target
  don't exist; 400 if source and target belong to different Hospital
  Units (a merge only makes sense within one physical hospital); 409 if
  a Revision is pending on the source warehouse OR on any of its
  Locations; 400/409 for the same per-Location checks Reassign Warehouse
  already enforces.
- Frontend: a "Merge" button (admin-only) next to Edit/Delete in the
  Warehouses table, opening a form that only offers same-Hospital-Unit
  warehouses as a target -- with a confirm prompt spelling out exactly
  what happens (every Location moves, then this warehouse is deleted).
- 9 new SQLite tests (successful merge with code recompute + source
  deletion, self-merge blocked, cross-site blocked, pending revision on
  the source warehouse blocked, pending revision on one of its Locations
  blocked -- confirmed the source and its Location are left completely
  untouched, not half-merged -- invalid location-type under the target
  blocked, whole-warehouse conflict blocked, source/target not found).
  118 tests total.
- Live-verified through the real shared tunnel: created two disposable
  warehouses under the same Hospital Unit, put two real Locations in the
  first, clicked Merge, picked the second as the target, and confirmed
  both Locations moved over with recomputed codes (`ASA02-A01`/
  `ASA02-A02`) and the first warehouse vanished from the list entirely.
  **Hit and fixed one real operational issue along the way, unrelated to
  this feature's own logic**: the long-running backend process's
  connection pool had picked up bad state from earlier rapid manual
  retries during debugging, making Postgres report a duplicate-key
  conflict for a code that a fresh connection could insert immediately --
  confirmed via a direct probe insert, fixed by simply restarting the
  backend process for a clean pool. Cleaned up the disposable warehouse/
  Locations and the throwaway verification admin account afterward.

**Frontend (`web/`)** -- Next.js 16 + TypeScript + Tailwind, same
architecture as the sibling WMS Readiness Tracker (in-memory access token,
httpOnly refresh cookie, client-side route guard) but its **own visual
identity** -- an industrial steel-blue palette (not the sibling's teal),
grounded in the warehouse/logistics subject rather than reused wholesale,
plus a distinct "signal" amber accent used specifically to mark
AI-generated content (recommendations) as different from deterministic
data. Pages: Dashboard (summary stat tiles + the recommendations panel),
Warehouses (create + list with live occupancy status), Locations (create +
list, filterable by warehouse), Uploads (both Excel templates, surfaces
the new `pending_count` bucket), Merge Suggestions (approve/reject with
the AI reasoning shown inline), Config (read-only viewer of the seeded
formula -- editing happens via `seed_config.py`/the API, not a form yet).
Runs on port **3001** locally (not 3000) specifically so it can run
alongside the sibling project's frontend without a port conflict --
`CORS_ORIGINS` is set accordingly.

Verified: clean `tsc --noEmit`, clean `eslint .` (hit and fixed the same
`react-hooks/set-state-in-effect` trap already documented in the sibling
project -- inlined each effect's own fetch instead of calling a named
`load()` function from inside `useEffect`), clean `npm run build` (7
routes). Confirmed live in a real browser: the login page renders
correctly, and all 6 protected routes correctly redirect to `/login` with
zero console errors when unauthenticated -- did **not** click through the
authenticated app in the browser myself, per this project's standing rule
against ever typing a real account's password into a login form.

## What's deliberately NOT built yet

This is a genuinely large system (10 AI responsibilities, a full dashboard,
an optimization engine, plus two follow-up features requested after the
core was live) -- building all of it in one pass would mean none of it
gets verified properly. Phases 0-4 plus their frontend, all of Phase 5
(5a auth, 5b Revision workflow backend, 5c its frontend, 5d Users page),
and Phase 6 (Raw Import) are the well-understood, high-confidence core --
all proven correct against real data. What's left:

1. Genuinely still open, not deferred by choice: **an inventory/stock data
   model**, if "how full of actual goods is this warehouse" turns out to
   matter more than "how many storage slots are defined" -- flag if this
   distinction matters to you, since Phases 3-4's capacity/optimization
   features are both built on the latter.
2. Editable config forms in the UI -- **Sites (Hospital Units) got one**
   (`SiteForm` on the Config page, calling the already-existing
   `POST /config/sites`, admin-only) after being asked directly while
   sharing the app for testing. Warehouse Types/Codes/Location Types/
   Category Rack Mappings remain viewable but not yet editable there --
   `scripts/seed_config.py` and the `/config/*` API handle those today.
3. Future-features wishlist from the brief (heatmap visualization,
   forecasting, ABC analysis, slotting, picking-distance optimization,
   simulation, formula version management, chat assistant) -- not started,
   listed here only so nothing from the original brief gets silently lost.

## Assumptions made, unanswered when asked

Two architecture questions were asked before starting and went unanswered,
so the recommended default was used for both (documented here per this
project's convention, so it isn't lost):

- **Standalone app**, not a module inside the WMS Readiness Tracker -- own
  repo, own database, matching how the other two sibling apps are also
  separate.
- **AI suggests merges, never auto-applies them** (see Phase 2 above --
  this is now actually implemented, not just a stated intention).

Also: `MRCCC`'s `short_code` (seeded as `CC`) is **not** confirmed by any
real example in the source files, unlike RSUS/SHMD/SHBP's -- verify it
before generating any real MRCCC location codes.

## Setup

1. Create a Neon Postgres project (separate from the WMS Readiness Tracker's
   -- this is a different app/domain).
2. `cd api`, create a venv, `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env`, fill in `DATABASE_URL` and a random
   `JWT_SECRET`. `GROQ_API_KEY` is optional -- unset, optimization
   recommendations still work, just with template explanations instead of
   AI-written ones (same key as the sibling project can be reused; get a
   free one with no card at [console.groq.com/keys](https://console.groq.com/keys)).
4. `alembic upgrade head`
5. `python -m scripts.seed_config` -- loads the real formula config.
6. `python -m scripts.seed_admin --email you@yourorg.com --name "Your Name" --password "..."`
   -- creates the first admin account. PIC accounts (scoped to one Hospital
   Unit each) are created afterward by an admin via `POST /users`, not this
   script.
7. `uvicorn app.main:app --host 127.0.0.1 --port 8001` -- not `--reload`,
   not port 8000 (that's the sibling project's). Then check `GET /health`.
8. `pytest` -- should show 94 passed.

Frontend:

9. `cd web`, `npm install`.
10. Copy `.env.example` to `.env.local` if you need to change the API URL
    -- defaults to `http://localhost:8001`, matching step 7 above.
11. `npm run dev` -- runs on port **3001** by default (see `package.json`),
    not 3000, so it can run alongside the sibling project's frontend.
12. Sign in with the admin account from step 6.
