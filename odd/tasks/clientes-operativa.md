# ODD Task: clientes-operativa

Status: in progress — WU1 merged to `main` (PR #401 → `c2163ff6`). D1 decided: option A. Next: WU2 (equipment). WU3/WU4 still blocked on D2-D4.
Worktree: `../lumat-agent-odd-clientes-operativa`
Branch: `odd/clientes-operativa`
Base: `c4ad6fe2` (main, 2026-09-28)
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
- **WU3** A nullable amount field on `Case`, exposed in the API and the ficha.
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
| D2 | **Amount semantics**: what the field means (quoted value? invoiced value?) and its currency | WU3 | Nullable numeric, currency CLP (Lumat is Chilean), meaning "value of the service for this case". Flag if it should be USD or carry both. |
| D3 | **Merge rules**: which record survives (oldest? richest? most activity?) and what happens to conflicting scalar fields | WU4 | Survivor = the record with more activity; empty survivor fields filled from the loser; conflicting non-empty fields prefer the survivor and are recorded in the audit row. |
| D4 | **Merge in or out of this unit** | WU4 sequencing | **Out — its own unit.** Four FK reassignments plus memory re-keying is not the same size as the other three, and a failure corrupts customer history. |

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
| T2.1 | WU2 | Schema + migration `035` for the chosen equipment shape (D1) | blocked on D1 |
| T2.2 | WU2 | Capture path promotes the free-text equipment answer into structured rows | blocked on D1 |
| T2.3 | WU2 | Ficha renders and edits equipment; API serializer + endpoint | blocked on D1 |
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
- [ ] WU2 — **option A**, `CustomerEquipment` table; migration `035`. Needs a worktree-local
      `infra/.env` before the backend suite can run here (absent today; present only in the
      principal worktree)
- [ ] WU3 — blocked on D2
- [ ] WU4 — blocked on D3/D4

## Closure

Pending.

## Recovery

- Nothing to resume beyond the task list above; the worktree and branch are live at base `c4ad6fe2`.
- Note for the next session: another session is actively merging to `main`
  (`usuarios-aislamiento` WU1 landed as PR #400 during planning). `git fetch origin`
  immediately before any merge.
- Latest migration on main is `034`; WU2's is therefore `035`.
- Test DB: `bash infra/test-db.sh up|down|env` (project name derives from the worktree slug).
- `graphify-out/` is gitignored; query the graph from the principal worktree.
