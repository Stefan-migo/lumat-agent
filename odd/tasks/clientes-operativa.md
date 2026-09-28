# ODD Task: clientes-operativa

Status: in progress — WU1 merged (`c2163ff6`, PR #401) and WU2 merged (`4a67d6be`, PR #402; native review `review-d64cbb138ad3cca7` approved, authority burned). D1, D2, D5 decided. **WU3 (case amount) in progress on `odd/clientes-operativa-wu3`.** WU4 still blocked on D3/D4.
Worktree: `../lumat-agent-odd-clientes-operativa-wu3` (one worktree, one branch per work unit)
Branch: `odd/clientes-operativa-wu3`
Base: `4a67d6be` (main, 2026-09-28; merge of WU2 — also the reviewed boundary carried into this slice)
Depends on: nothing
Source: scope comparison `.rapsodia-code/sessions/archived/2026-08-07-reunion-cierre/propuesta-final-lumatagent.md` vs the owner's own-investment decision of 2026-09-28
Delivery strategy: `ask-on-risk`
Chain strategy: `stacked-to-main` (repo precedent: the Clientes campaign and `cases-route-alignment` both shipped stacked to main)

## Objective

Make the Clientes section operational rather than a read-only record, as **own
investment** — not a Lumat scope change and not a line item in any quote. Four
improvements were identified in the scope comparison as cheap relative to the
capability they unlock. Their real size is recorded honestly below: two are small,
two are not.

## Problem (verified in code, not inferred)

### WU1 — A client's stage is editable only from the ficha, not from the list
`ClientesList.tsx:41-45` renders `customer.state` as a badge and `:175-178` offers only
archive/restore as a row action. Stage editing lives on the ficha
(`ClientFicha.tsx:145-160, 289-307`) through `changeClientState`. The backend is already
complete: `POST /clients/{id}/state` (`clients.py:255-260`) with a validated transition
graph (`customers.py:36-73`) enforced by `set_customer_state` (`customers.py:197-226`),
which audits the change. **Frontend-only gap.**

### WU2 — Equipment is captured as free text and then lost
The chat capture node asks for equipment "marca, modelo y años aproximados"
(`capture.py:25-34`) and stores the answer under a single `equipment` key inside
`Conversation.captured_data` (JSONB, `models.py:254-277`; migration `003`). It is never
promoted to structured storage: `update_captured_data` writes only `name`, `email`,
`comuna`, `address` (`customers.py:443-461`). Nothing renders equipment anywhere — the
ficha has no equipment field (`ClientFicha.tsx:260-268`). So the data Lumat's own
request asks to collect (1.5) is collected and discarded. Routing for equipment intents
is already covered by `test_route_capture_path_for_equipment_intents`
(`tests/integration/test_chat_intent.py:333`). **Real scope: a data model + migration +
API + UI.**

### WU3 — A Case cannot record an amount
`Case` has no money field (`models.py:335-368`: `id`, `conversation_id`, `customer_id`,
`created_at`, `service`, `priority`, `status`, `emergency`, `responsible_id`, `summary`,
`escalated_at`, `closed_at`, `notified_at`, `acknowledged_at`, `ack_by`,
`reminder_count`, `bundle`). The only money in the schema is LLM/Meta cost accounting
(`Message.cost_llm`, `cost_meta`, `models.py:329-332`), unrelated to service value.
`to_case_dict` (`serializers.py:152-169`) and the `customer_history` case payload
(`customers.py:386-404`) expose no amount. **Scope: migration + serializer + UI.**

### WU4 — There is no way to merge duplicate clients
Identity is the normalized phone (`customers.py:93-107`, `Customer.phone_e164` unique and
not null, `models.py:218-235`). A create collision raises `PhoneAlreadyExists`, surfaced
as HTTP 409 with the existing id and an "open the existing ficha" affordance — duplicate
*prevention*, not repair. No merge endpoint, workflow or UI exists. A merge must reassign
four direct foreign keys to `customers.id` — `Conversation.customer_id`
(`models.py:261-264`), `Case.customer_id` (`:342-348`), `CustomerNote.customer_id`
(`:384-387`), `Appointment.customer_id` (`:604-608`) — plus customer memories keyed by
string `entity_id` (no declared FK, `models.py:466-494`). **The heaviest and riskiest of
the four; blast radius is every customer-linked table.**

## Scope

### In

- **WU1** Editable stage in the client list (frontend only, reusing the existing endpoint).
- **WU2** Structured equipment storage, captured from the conversation and editable in the ficha.
- **WU3** A nullable amount field on `Case`, recorded by the operator through the existing case update path and exposed in the API and the ficha.
- **WU4** Assisted merge of two duplicate clients (reassign FKs, pick the survivor).

### Out (deliberately, reserved for separate quotes)

Kanban/pipeline board, quoting/presupuestos, payments, service catalogue, funnel and
conversion reporting, per-channel consent, email/SMS as a conversation channel, custom
fields/tags/segments, organization records, and recurrence/next-maintenance scheduling.
These are M3 or generic-product work and must not be smuggled in here.

Also out: ownership/isolation of customer data. `usuarios-aislamiento` (delivered WU1,
PR #400) scoped assistant memory and project namespaces (`db/migrations/034_project_owners.sql`);
`Customer` still has no `owner_id`.

## Open decisions (owner input required)

| # | Decision | Blocks | Recommendation |
|---|----------|--------|----------------|
| D1 | **Equipment shape** — **DECIDED 2026-09-28: option A, a `CustomerEquipment` table** (multiple rows per client) | Resolved | Chosen by the owner. Lumat's request 3.4 puts "Equipos, direcciones y antecedentes técnicos" under **base de clientes**, and one client can own a calefont *and* a caldera. Rejected: a column set on `Customer`, because a client with two appliances would force a second migration. |
| D2 | **Amount semantics**: what the field means (quoted value? invoiced value?) and its currency — **DECIDED 2026-09-28: nullable numeric, currency CLP, meaning "value of the service for this case"** | Resolved — WU3 unblocked | Chosen by the owner from the recorded recommendation, unchanged. Rejected: non-null (would invent an amount for historical and non-billable cases) and a dual-currency field (the business is Chilean; a second currency is speculation). Currency is implicit in the stored scalar, documented rather than modelled. |
| D3 | **Merge rules**: which record survives (oldest? richest? most activity?) and what happens to conflicting scalar fields | WU4 | Survivor = the record with more activity; empty survivor fields filled from the loser; conflicting non-empty fields prefer the survivor and are recorded in the audit row. |
| D4 | **Merge in or out of this unit** | WU4 sequencing | **Out — its own unit.** Four FK reassignments plus memory re-keying is not the same size as the other three, and a failure corrupts customer history. |
| D5 | **Equipment promotion shape** — **DECIDED 2026-09-28: promote the captured text verbatim** | WU2 | The capture asks one open question and stores a single `equipment` string (`capture.py:30`). Parsing it into marca/modelo/antigüedad would invent data. Chosen: the row keeps the verbatim answer in `details`, `equipment_type` is pre-filled from the capture intent when it names an appliance (calefont/caldera/calefaccion), and marca/modelo/antigüedad are operator-editable in the ficha. Rejected: restructuring the capture into per-field questions — it changes customer-facing behaviour and its tests, out of proportion to WU2. |

WU1 is unblocked and needs none of these.

## Graph check

Queried from the principal worktree (`graphify-out/2026-09-28/`).

- `graphify query "Customer Case state editing and client list"` → nodes `Customer`
  (`models.py:218`), `Case` (`models.py:335`), `ClientesList.tsx`/`ClientesListState`,
  `ClientFicha.tsx`, `get_or_create_customer()`, `customers.py`,
  `serializers.py:46` (`to_customer_dict`), `test_api_clients.py`; communities
  `clients.py`, `ClientFicha.tsx`, `Customer`.
- `graphify query "customer captured data equipment and duplicate merge"` → nodes
  `update_captured_data()` (`customers.py:443`), `capture.py`, `client_profile_update()`
  (`clients.py:161`), `_apply_consent_and_customer()` (`capture.py:87`),
  `test_route_capture_path_for_equipment_intents()` (`test_chat_intent.py:333`).
- `graphify path ClientesList.tsx clients.py` → no directed path (expected: the list
  reaches the API through `api.ts`, not through a code edge). Matches the known
  limitation that the graph cannot see through the HTTP boundary.

## Tasks

| ID | Work unit | Task | Route |
|----|-----------|------|-------|
| T1.1 | WU1 | RED: the client list renders a stage control and changing it calls `changeClientState` and refreshes the row | delegated (writer) |
| T1.2 | WU1 | GREEN: implement the row control reusing `Dialog` + `Select` and the existing endpoint | delegated (writer, same unit as T1.1) |
| T1.3 | WU1 | Verification: `npm test` (web) and `npm run build` (`tsc -b`) green | delegated per-action |
| T2.1 | WU2 | Migration `035`: `customer_equipment` table — FK `customer_id` NOT NULL and indexed, nullable `equipment_type`/`brand`/`model`/`age`/`details`, partial unique `source_conversation_id` (promotion idempotency), timestamps, grants | delegated (writer, backend) |
| T2.2 | WU2 | `CustomerEquipment` model beside `Customer`/`CustomerNote` | delegated (same writer) |
| T2.3 | WU2 | Service: list/create/update/delete a customer's equipment, audited with `record_audit` (the `set_customer_state` pattern) | delegated (same writer) |
| T2.4 | WU2 | Promotion: on the consent turn, upsert the captured equipment into a row keyed by `source_conversation_id`; `equipment_type` pre-filled from the capture intent when it names an appliance | delegated (same writer) |
| T2.5 | WU2 | API under the customer: list/create/update/delete with `require_operator_json`, response shape mirroring `clients.py` | delegated (same writer) |
| T2.6 | WU2 | Ficha equipment section — view, add, edit — reusing `Dialog` + `Input`/`Select` | delegated (writer, frontend) |
| T2.7 | WU2 | Tests: backend functional (`test_api_clients.py` pattern) plus promotion idempotency (retry/recapture yields one row); frontend (`ClientFicha.test.tsx` pattern) | delegated per side |
| T3.1 | WU3 | Record path: the problem states a Case "cannot **record** an amount", and `POST /cases/{id}/update` already exists (`routes/cases.py:94`, audited via `cases_service.update_case`). WU3 therefore records through that path instead of shipping a nullable column nothing can write — the doc's "exposed in the API and the ficha" alone would be a dead field | decided (interpretation, recorded) |
| T3.2 | WU3 | RED: `amount` round-trips through `POST /cases/{id}/update` and appears in `to_case_dict` and the `customer_history` case payload; omitted keeps the current value, explicit `null` clears it; the change is audited | delegated |
| T3.3 | WU3 | GREEN backend: migration `036` (`cases.amount` numeric NULL, grant pattern copied from `035`), `Case.amount` (`models.py`), `to_case_dict` (`serializers.py`), `customer_history` (`customers.py`), `update_case` service + `CaseUpdateBody.amount` reusing the existing `_UNSET` keep-vs-clear sentinel. The null-vs-omit contract is documented in the service/route docstrings — this is the R2-001 pattern, not repeated | delegated (same writer) |
| T3.4 | WU3 | GREEN frontend: the ficha shows the case amount and lets the operator set it (WU2 equipment pattern: `Dialog` + `Input`, refresh after save) | delegated (same writer) |
| T3.5 | WU3 | Verification: focused backend (`test_api_cases.py`, `test_migrations.py`, `test_api_clients.py`), full `pytest tests/`, `npm test`, `npm run build` (`tsc -b`) | delegated per-action |
| T3.6 | WU3 | Assessment + review slice bookkeeping on base `4a67d6be` | orchestrator |
| T4.1 | WU4 | Merge service: reassign the four FKs and re-key memories, single transaction, audited | blocked on D3/D4 |

## Delivery

Frontend and backend slices, all inside the Clientes section. Forecast: WU1 ~100-150
changed lines, WU2 ~250-350, WU3 ~120-180, WU4 ~200-300. The unit will exceed the ~400
authored-line review budget once WU2 lands, so slices ship chained per the stacked-to-main
strategy, one PR per work unit.

## Progress / Evidence

- [x] **WU1 delivered** — `web/src/components/pages/ClientesList.tsx` and
      `ClientesList.test.tsx`, 61 insertions / 7 deletions. The row now offers
      "Cambiar estado <cliente>"; the dialog loads the option list from the same source the
      ficha uses (`GET /clients/{id}` → `states`, which is every `CustomerState` value, not a
      per-row transition subset) and saves through the existing `changeClientState`, then
      refreshes the list. The archive/restore actions and the 409 "open the existing ficha"
      affordance are untouched. No backend file changed.
- [x] **WU1 RED** — `npx vitest run src/components/pages/ClientesList.test.tsx` failed because
      the row had no button named "Cambiar estado Marcela Fuentes".
- [x] **WU1 GREEN** — same focused command: 1 file, 24 tests passed. Full suite
      `npm test`: 90 files, 823 tests passed. `npm run build` (includes `tsc -b`): passed.
- [x] **WU1 parent spot check** — the focused test was re-run by the parent: 24/24 passed.
- [x] **WU1 assessment** — `gentle-ai review assess --base-ref c4ad6fe2 --committed-only`:
      `risk: medium` (`executable_change`), `changed_lines: 216`, `review_due: false`,
      `review_due_reason: under_budget`. No review transaction and no consent were opened; the
      slice stays pending until a later commit reaches the review budget. The assessed base
      remains `c4ad6fe2`.
- [x] **Commits** — `18c41083 docs(odd): open the clientes-operativa unit`,
      `e26215ae feat(clients): change a client's stage from the list`,
      `8095381c docs(odd): record the WU1 delivery and assessment`.
- [x] **WU1 merged** — PR #401, merge commit `c2163ff6`. Pre-merge integration ran over the
      tree that landed (after merging `origin/main` into the branch): frontend suite
      **90 files / 823 tests**, `npm run build` (includes `tsc -b`) passed, and both CI jobs
      (`test`, `panel`) green. The merged branch was deleted (local and remote) and the
      worktree was reparked to `odd/clientes-operativa-wu2` off the updated `main`.
- [x] **WU2 delivered** — `customer_equipment` (migration `035`) in the D5 shape: the verbatim
      capture in `details`, `equipment_type` pre-filled from the capture intent when it names an
      appliance, brand/model/age operator-editable, and a partial unique index on
      `source_conversation_id` so promotion is idempotent per conversation. Promotion runs on the
      consent turn; a re-promotion only writes non-null captured values, so an operator edit is
      never wiped. API: list/create/update/delete under `GET|POST /clients/{id}/equipment` and
      `PATCH|DELETE /clients/{id}/equipment/{equipment_id}` (`require_operator_json`), serializer
      `to_equipment_dict`. Ficha: an "Equipos" section with add/edit through `Dialog` +
      `Input`/`Select`; **no delete control** — the stated ficha scope is view/add/edit and the
      DELETE endpoint is covered by backend tests only.
- [x] **WU2 RED** — backend: `tests/functional/test_api_clients.py` failed collection with
      `ImportError: cannot import name 'CustomerEquipment' from 'app.models'`. Frontend:
      `npx vitest run src/components/pages/ClientFicha.test.tsx` → 3 failed / 28 passed, the
      equipment section and its add/edit controls absent.
- [x] **WU2 GREEN** — backend focused: `test_migrations.py` 23 passed, `test_chat_capture.py`
      13 passed, `test_api_clients.py` 30 passed; full `pytest tests/` passed. Frontend focused:
      `ClientFicha.test.tsx` 31 passed; full `npm test` 90 files / 826 tests passed; `npm run
      build` (`tsc -b`) passed.
- [x] **WU2 corrections** — `0480a9b3`: re-promotion no longer nulls an operator-set
      `equipment_type`/`details`, with a regression test asserting one row and exactly one
      promotion audit; and the generic `"quiero una visita"` scenario was restored in
      `test_cm2_complete_capture_persists_and_confirms`, which now asserts `equipment_type is None`
      while still promoting `details`.
- [x] **WU2 parent spot checks** — `uv run pytest tests/integration/test_chat_capture.py` 13
      passed; `npx vitest run src/components/pages/ClientFicha.test.tsx` 31 passed; full
      `npm test` 90 files / 826 tests passed. An earlier `AgendaPage` cancellation-test timeout
      did not reproduce and is not WU2 territory.
- [x] **WU2 commits** — `41e1941c docs(odd): plan WU2 equipment storage and record the D5
      decision`, `d4126465 feat(clients): add customer equipment table and model`, `51f8a68d
      feat(clients): promote captured equipment into customer fichas`, `e66bbc10 feat(clients):
      expose equipment CRUD in clients API`, `0480a9b3 fix(clients): preserve operator equipment
      values on promotion`, `50bd48b3 feat(clients): show and edit customer equipment on the ficha`.
- [x] **WU2 assessment** — `gentle-ai review assess --base-ref c4ad6fe2 --committed-only`:
      `risk: high` (`process_boundary` — `tests/integration/test_migrations.py`), `changed_paths:
      17`, `changed_lines: 938`, `review_due: true` (`high_risk`). The base is `c4ad6fe2`, not the
      WU2 branch point `c2163ff6`, because the WU1 slice assessed as `under_budget` and never
      advanced the reviewed boundary; `c2163ff6` would leave WU1's `ClientesList` change
      unreviewed. The review receipt belongs in the PR body, not in this doc.
- [x] **WU2 merged** — PR #402, merge commit `4a67d6be`. Native review `review-d64cbb138ad3cca7`: 4 lenses, tier `high`, 970 lines, **approved**, authority burned. Pre-merge integration ran over the tree that landed (after merging `origin/main` into the branch): backend suite green, `npm run build` (`tsc -b`) green, CI (`test`, `panel`) green. **The WU2 receipt lives in the PR #402 body, not here** — this doc was frozen between `review start` and merge, which is why the status line above still read "pending native review and PR" on `main`.
- [x] **WU2 advisories (non-blocking, not corrections)** — R2-001: the equipment `PATCH` null-vs-omit contract is undocumented (`clients.py:392-398`); R3-001: a stale async `getClientFicha` response can overwrite the options of the client-state dialog opened later (`ClientesList.tsx:163-171`, a WU1 file). Both are separate work, recorded in the PR #402 body.
- [x] **WU3 provisioned** — new worktree `../lumat-agent-odd-clientes-operativa-wu3` (branch `odd/clientes-operativa-wu3`, base `4a67d6be`), `.venv` via `uv sync`, `web/node_modules` installed, isolated test DB up on port 5475. `.rapsodia-code/worktree.json` was regenerated fresh; the stale-branch trap that crashed `rapso worktree cleanup` after WU2 does not apply to a newly created worktree.
- [x] **WU3 D2 decided** — nullable numeric, CLP, "value of the service for this case" (owner, 2026-09-28): the recorded recommendation unchanged.
- [x] **WU3 Graph Check** — queried from the principal worktree (`graphify-out/` stamped at `4a67d6be`). `graphify query "Case model fields and case serialization to_case_dict customer_history"` → `to_case_dict()` (`serializers.py:169`), `customer_history()` (`customers.py:486`), `Case` (`models.py:349`), `test_stream_events_preserves_compatible_event_serialization()`. `graphify query "client ficha cases section display amount"` → `cases.py` services + `routes/cases.py`, `test_api_cases.py`, `dashboard.py`, `ClientFicha.test.tsx`, `record_audit()`, `publish_event()`. `graphify path "Case" "to_case_dict"` → "no directed path" with an ambiguous source match; the edge is direct in code (`serializers.to_case_dict(case)`), so this is the known node-resolution limitation, not a missing link.
- [x] **WU3 — implemented** — `cases.amount NUMERIC NULL` (migration 036; no default or backfill) records the service value in CLP through the existing `/cases/{id}/update` route. The service reuses `_UNSET`: omitted keeps the value, explicit `null` clears it, with the contract documented in the service and route docstrings. Updates remain actor-audited; amount is present in case responses and customer history. Client ficha renders CLP values, explicitly renders `Sin monto registrado` for null, and edits through a dialog that refreshes after save. No manual-case amount, conversion, invoicing, payment, report, or pipeline work was added.
- [x] **WU3 RED** — backend: `eval "$(infra/test-db.sh env)" && uv run pytest tests/functional/test_api_cases.py -q` → `1 failed`; amount update returned HTTP 200 but response serialization raised `KeyError: 'amount'`. Frontend: `npx vitest run src/components/pages/ClientFicha.test.tsx` → 1 failed / 31 passed; expected CLP amount was absent from the ficha.
- [x] **WU3 GREEN / verification** — focused backend `eval "$(infra/test-db.sh env)" && uv run pytest tests/functional/test_api_cases.py tests/integration/test_migrations.py -q` → 42 passed. Full backend `eval "$(infra/test-db.sh env)" && uv run pytest tests/ -q` → passed; existing coroutine/model warnings remain. Frontend focused `npx vitest run src/components/pages/ClientFicha.test.tsx` → 32 passed; amount fixture and story shape check `npx vitest run src/components/pages/ClientFicha.test.tsx src/stories/pages/_shared/mockData/cases.test.ts` → 42 passed. `npm run build` (`tsc -b` + Vite) passed (existing >500 kB chunk warning). Final full `npm test` → 90 files / 827 tests passed. Earlier full-suite attempts hit the known ~5s load timeouts (and once caught the case serializer fixture's outdated expected keys); `npx vitest run src/components/pages/AgendaPage.test.tsx` → 37 passed isolated and `npx vitest run src/components/domain/AppShell.test.tsx` → 29 passed isolated, then the updated full suite passed.
- [x] **WU3 commits** — `73daa8c7 feat(cases): add nullable amount to cases`; `07e125ec feat(cases): record and expose the case amount`; `c0159e03 test(cases): assert amount in customer history`; `40a7d3e7 feat(clients): show and edit the case amount on the ficha`; `64b7a7fd test(clients): update case amount story fixtures`.
- [x] **WU3 correction round** — `8b4042a76d8b4ffc4f4dd9c137cc01fe2d72ec70 fix(cases): emit a distinct event when only the amount changes`; `456682c18f6e2130ef844755e93068d1ea5654f2 chore(cases): tighten migration 036`; `e55731ab docs(odd): record the WU3 correction`. C1 RED: `eval "$(infra/test-db.sh env)" && uv run pytest tests/functional/test_api_cases.py::test_amount_only_updates_publish_events_with_each_new_amount -q` failed with `assert 1 == 2` because both amount-only updates reused one event; GREEN: the same command passed after the dedupe key included amount. Migration hygiene: `036` now uses `ADD COLUMN IF NOT EXISTS` and relies on existing cases grants. Recreated the isolated test DB with `bash infra/test-db.sh down && bash infra/test-db.sh up`. Focused backend (`eval "$(infra/test-db.sh env)" && uv run pytest tests/functional/test_api_cases.py tests/integration/test_migrations.py -q`) passed; full backend (`eval "$(infra/test-db.sh env)" && uv run pytest tests/ -q`) passed with the existing coroutine/model warnings; `cd web && npm run build` passed with the existing large-chunk warning. No `web/` file changed in this correction round.
- [x] **WU3 graph check** — query `case amount update path and case serialization` consulted `Case` (`app/models.py`), `update_case()` (`app/services/cases.py`), `cases.py` route, serializer/customer history modules and functional test nodes. `graphify path "update_case" "to_case_dict" --undirected` gave the route path `update_case() <--calls-- case_update() --calls--> to_case_dict()`. The directed query found no path; `ClientFicha` ↔ API and `Case` ↔ `ClientFicha` paths also cannot cross the HTTP boundary. Query `client ficha cases section display amount` consulted `ClientFicha.tsx`, `ClientFicha.test.tsx`, `api.ts`, `types.ts`, `Case`, and `record_audit()`. God nodes from `GRAPH_REPORT.md`: `Case` (97 edges), `record_audit()` (93 edges). Graph built at `16ba9cbf`, predating this branch, so structural results were treated as navigation and verified against source.
- [x] **WU3 T3.6 assessment** — done. Native review `review-755c72be3927448f`: 4 lenses, tier `high`, 229 lines, **approved**, authority burned. PR #404 merged to `main` as `c1fff81c`. The WU3 receipt lives in the PR #404 body, not here: this doc was frozen between `review start` and merge.
- [x] **WU2/WU3 advisories closed** — the four non-blocking advisories were delivered as separate
      later work in PR #408 (merged `6c567d41`, branch `odd/clientes-operativa-advisories`, task doc
      `odd/tasks/clientes-operativa-advisories.md`): WU3 `R1-001` (CLP float precision bound
      documented in `to_case_dict` + exact round-trip test), WU3 `R3-001` (negative/non-finite guard
      in the case-amount editor), WU2 `R2-001` (equipment `PATCH` keep-vs-clear contract documented),
      WU2 `R3-001` (`useRef` request-sequence guard in `openState`). Native review
      `review-e5fdb2a1b90ce4b7`: 1 lens (`review-reliability`), risk `medium`, **0 findings**,
      approved, authority burned. Verification: backend exit 0, frontend 90 files / 829 tests,
      `npm run build` exit 0 — also re-run over the merged tree with `origin/main` (`b5ddfee1`). The
      receipt lives in the PR #408 body.
- [ ] WU4 — blocked on D3/D4

## Closure

WU1–WU3 are delivered and merged to `main`: PR #401 (`c2163ff6`), PR #402 (`4a67d6be`), PR #404
(`c1fff81c`). The WU2/WU3 review advisories were closed as separate later work in PR #408
(`6c567d41`). The unit is **not fully closed**: WU4 (duplicate merge) remains, blocked on D3/D4.

## Recovery

- Nothing to resume beyond the task list above. No branch of this unit is live: `odd/clientes-operativa`
  (WU1), `-wu2`, `-wu3`, and `-advisories` no longer exist (local or remote) after PRs
  #401/#402/#404/#408 — one worktree, one branch per work unit.
- WU3's review slice base is `4a67d6be` (the last reviewed boundary, advanced by WU2's approved
  review), **not** the WU3 branch point `c2163ff6`: WU1 assessed as `under_budget`, so the boundary
  advanced past both.
- Note for the next session: another session is actively merging to `main`
  (`usuarios-aislamiento` WU1 landed as PR #400 during planning). `git fetch origin`
  immediately before any merge.
- Latest migration on `main` is `036` (`db/migrations/036_case_amount.sql`, from WU3); WU3's review
  slice base was `4a67d6be` and its work was sliced against it.
- Test DB: `bash infra/test-db.sh up|down|env` (project name derives from the worktree slug).
- `graphify-out/` is gitignored; query the graph from the principal worktree.
