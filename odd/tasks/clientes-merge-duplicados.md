# ODD Task: clientes-merge-duplicados

Status: opened 2026-09-28. All decisions closed (D3, D4, surface scope, memory-collision policy, loser identity). No code written yet.
Worktree: `../lumat-agent-odd-clientes-merge-duplicados`
Branch: `odd/clientes-merge-duplicados`
Base: `16d94ced` (main, 2026-09-28)
Depends on: nothing
Source: split out of `odd/tasks/clientes-operativa.md` WU4 — D4 decided 2026-09-28: the duplicate merge is its own unit
Delivery strategy: `ask-on-risk`
Chain strategy: `stacked-to-main` (repo precedent: the Clientes campaign and `cases-route-alignment` both shipped stacked to main)
Engram mirror: topic `odd/clientes-merge-duplicados/tasks` — **pending**: the write was blocked by ambiguous active-session attribution (2 candidates for `lumat-agent` in this directory). Resync when the ambiguity is resolved; the decisions themselves are already saved at `odd/clientes-merge/decisions`.

## Objective

Make duplicate clients repairable. Today the system only *prevents* duplicates (a 409 on the
second phone); nothing repairs the pairs that already exist. This unit ships an assisted merge:
the operator picks the pair from the ficha, the rule picks the survivor, the preview shows what
moves, and one audited transaction reassigns every customer-linked row.

## Problem (verified in code, not inferred)

Identity is the normalized phone. `normalize_phone_e164()` (`app/services/customers.py:94-108`)
plus `Customer.phone_e164` unique and not null (`app/models.py:232-237`) make duplicates
impossible per phone — and therefore **duplicates exist only as the same person on two
numbers**. A create collision raises `PhoneAlreadyExists` (`app/services/customers.py:81`,
raised at `:169`), surfaced as HTTP 409 `phone_exists` with the existing id
(`app/panel/api/routes/clients.py:164-184`): duplicate *prevention*, not repair. No merge
endpoint, service, or UI exists anywhere.

**Five** columns reference `customers.id` (all `NOT NULL`, indexed, no `ondelete`). The
inherited problem statement said four; it predates WU2 and misses the equipment table:

| Table | Model | Migration |
|---|---|---|
| `conversations` | `app/models.py:277` | `001_init.sql:77` |
| `cases` | `app/models.py:361` | `001_init.sql:111` |
| `customer_notes` | `app/models.py:401` | `002_customer_notes.sql:13` |
| `customer_equipment` | `app/models.py:424` | `035_customer_equipment.sql:5` |
| `appointments` | `app/models.py:660` | `011_h3_scheduling.sql:18` |

Customer memories carry no FK: `Memory.entity_id` is a `String(100)` holding `str(customer_id)`
with `scope='customer'` (`app/models.py:538`), and `MemoryObservation` carries its **own**
`scope`/`entity_id` (`app/models.py:600-606`). Two keys are in use in production:
`customer_memo` — the living acta the chat writes per customer (`app/services/tukulpan.py:849-897`,
read at `app/panel/api/routes/clients.py:270-272`) — and `general`, the default for operator-created
memories (`app/panel/api/routes/clients.py:562`).

Two unique constraints bind any re-key (`app/models.py:515-519` and `:521-531`, the latter
recreated by `db/migrations/037_memory_owner_dedup.sql`):

- `uq_memories_owner_project_scope_entity_topic` on `(owner_id, proyecto, scope, entity_id, topic_key)`, `NULLS NOT DISTINCT`
- `uq_memories_normalized_content` on `(owner_id, proyecto, scope, entity_id, normalized_hash)`, partial where `normalized_hash IS NOT NULL`, `NULLS NOT DISTINCT`

**The collision is structural, not exceptional.** Both customers in a duplicate pair commonly own a
`customer_memo`, so a naive `UPDATE memories SET entity_id = <survivor>` aborts on a unique
violation. That is the crux of this unit, not an edge case.

**Without an identity alias the merge undoes itself.** `get_or_create_customer()`
(`app/services/customers.py:116-150`) is the only ingest entry point (`app/webhook/ingest.py:239`,
`app/chat/state.py:30`). Deleting the loser means the next message from that number creates a
fresh client; leaving it archived means `get_or_create_customer` **un-archives** it
(`app/services/customers.py:138-149`, `auto_unarchived`). Either way the duplicate comes back.

## Decisions (owner, 2026-09-28)

| # | Decision | Value |
|---|---|---|
| D4 | Container | Own unit: own worktree, task doc, and review receipt, separate from `clientes-operativa`. |
| D3 | Merge rules | **Survivor = the record with more activity**, measured as the sum of linked rows (`Conversation` + `Case` + `Appointment` + `CustomerNote`); tie → the oldest `created_at`. Empty survivor scalar fields are filled from the loser. Conflicting non-empty scalars: the survivor wins and the discrepancy is recorded in the audit row. |
| Scope | Surface | Backend service + endpoint **and** the assisted UI. Two stacked PRs. |
| M1 | Memory collision | The merge always proceeds. Byte-equivalent rows are deduped (repoint `MemoryObservation.memory_id` and `MemoryRelation.id_a`/`id_b`, sum `duplicate_count`, delete the loser row). On the same composite key with different content: the survivor's row wins and the loser's content is recorded in the audit row (append-only). The preview reports how many memories collide. |
| M2 | Loser identity | The loser survives as an **archived tombstone** with `merged_into_customer_id` pointing at the survivor; `get_or_create_customer` follows that pointer instead of creating or un-archiving. Mirrors the `ProjectAlias` that `projects.merge()` already creates. |

## Reused precedent (do not reinvent)

`projects.merge()` (`app/services/projects.py:285-352`) solves the same shape: pessimistic lock
ordered by id (`_lock_projects`, `:191-205`), pre-flight key maps (`:310-319`), dedupe + repoint
(`:321-345`), alias + archive of the source (`:346-350`), one audit row (`:350`). Its tests are
`tests/spec/test_projects_spec.py:158-401`. **Copy the structure.** The one deliberate divergence
is the conflict branch: `projects.merge()` raises (`:316-319`); this unit keeps the survivor's row
and records the loser's content in the audit row, because the client collision is structural.

## Recorded interpretations (owner may override; recorded, not silent)

- **I1** — The operator selects the **pair**; the survivor is decided by the D3 rule. There is no manual override in the UI.
- **I2** — When exactly one side is archived, the non-archived one is the survivor regardless of activity: an archived ficha must not absorb the active one.
- **I3** — Refuse when the two ids are equal, or when either side is already a tombstone (`merged_into_customer_id IS NOT NULL`), or when the chosen survivor is itself a tombstone. A chain is never created.
- **I4** — No un-merge, no automatic duplicate detection, and no bulk merge in this unit. The audit row is the record.

## Scope

### In

- Migration `038` + `Customer.merged_into_customer_id` (nullable self-FK).
- `merge_customers()` service: guards, D3 survivor rule, five FK reassignments, memory + observation re-key with the M1 policy, tombstone, one audit row, single transaction.
- Ingest resolution: `get_or_create_customer` follows `merged_into_customer_id` and never un-archives a tombstone.
- API: merge preview and merge endpoints under the client, `require_operator_json`.
- Assisted UI from the ficha: pick the other client, see the preview, confirm.
- Tests: backend functional + integration (ingest/memory collision) + migration, frontend.

### Out (deliberately)

Un-merge/undo, automatic duplicate detection, bulk merge, equipment dedupe (the survivor may end
up with two similar equipment rows — that is data, not a constraint violation), editing or
un-archiving a tombstone from the UI, and everything already listed as out of
`clientes-operativa` (kanban, quoting, payments, catalogue, funnel reporting, per-channel consent,
email/SMS, custom fields/tags, organizations, recurrence).

## Graph check

Queried from the principal worktree (`graphify-out/`, `graph.json` refreshed 2026-09-28 18:37).

- `graphify query "customer identity phone normalization duplicate merge 409"` → nodes
  `PhoneAlreadyExists` (`app/services/customers.py:81`), `create_customer()` (`:153`),
  `get_or_create_customer()` (`:116`), `Customer` (`app/models.py:232`), `Conversation` (`:268`),
  `Case` (`:349`), `CustomerNote` (`:386`), `CustomerEquipment` (`:408`), `Appointment` (`:649`),
  `merge()` (`app/services/projects.py:272`), `ProjectAlias` (`app/models.py:208`), and the
  constraint spec `customers.phone_e164 UNIQUE` (`tests/integration/test_migrations.py:529`).
  This query is what surfaced the `projects.merge()` precedent and the migration-test location.
- `graphify query "customer memories entity_id scope store"` → nodes `memories` spec constraint
  (`tests/spec/test_memory_spec.py:209`), `Memory` (`app/models.py:505`), `list_for_entity()`
  (`app/services/tukulpan.py:566`), `update()` (`:589`), `test_api_clients.py`,
  `test_customers.py`, `ClientMemories.tsx`.
- `GRAPH_REPORT.md` community hubs consulted: `clients.py`, `test_api_clients.py`,
  `test_migrations.py`, `ClientFicha.stories.tsx`, `ClientMemories.tsx`, `Dialog.tsx`.
- **Caveat**: the report is stale (built from `16ba9cbf`) and AST-only — the LLM labeler is out of
  credit (402), so `graph.json` (8340 nodes / 19611 edges) was used as navigation and every claim
  above was verified against source. The `projects.py` and `models.py` line numbers come from
  reading the files, not from the graph.

## Tasks

### Backend slice (PR 1)

| ID | Task | Route |
|----|------|-------|
| B1 | Migration `038`: `customers.merged_into_customer_id BIGINT NULL REFERENCES customers(id)`; `Customer.merged_into_customer_id` beside the other columns. No new grants (existing `customers` grants cover the column). | delegated (writer, backend) |
| B2 | RED: functional tests in the `tests/functional/test_api_clients.py` shape — merge reassigns all five FK tables and the customer memories; survivor by activity; tie → oldest; guards (self, tombstone, archived preference); one audit row; preview counts. | delegated (same writer) |
| B3 | GREEN: `merge_customers()` — lock both rows `with_for_update()` ordered by id, apply I1–I3 guards, resolve the survivor by D3, reassign the five FKs, re-key `memories` **and** `memory_observations` (`entity_id` and `memory_id` are two separate updates), apply the M1 policy, write the tombstone, write one `record_audit` row (`action="customer.merged"`) carrying the scalar conflicts and the memory conflicts. Caller commits. | delegated (same writer) |
| B4 | Ingest resolution in `get_or_create_customer`: follow `merged_into_customer_id` to the survivor; never un-archive a tombstone. Regression test: a message from the loser's number resolves to the survivor and creates no new customer. | delegated (same writer) |
| B5 | API: `GET /clients/{id}/merge-preview?with={other_id}` and `POST /clients/{id}/merge` (`require_operator_json`), error mapping to 400/404/409. | delegated (same writer) |
| B6 | Verification: focused backend, full `pytest tests/`, migration test. | delegated per-action |

### Frontend slice (PR 2)

| ID | Task | Route |
|----|------|-------|
| F1 | RED: the ficha offers "Fusionar con otro cliente"; the dialog loads the preview and confirms the merge. | delegated (writer, frontend) |
| F2 | GREEN: dialog reusing `Dialog` + `Input`/`Select`; pick the other client, show survivor + what moves + memory conflicts, refresh the ficha after save. | delegated (same writer) |
| F3 | Verification: `npm test` and `npm run build` (`tsc -b`). | delegated per-action |

### Orchestrator

| ID | Task | Route |
|----|------|-------|
| O1 | Assessment + review slice bookkeeping on the last reviewed boundary (confirm with `gentle-ai review assess`; the handoff's `2b7ea9c0` is stale). | orchestrator |

## Delivery

Forecast: backend ~350-450 authored changed lines (migration + service + ingest + API + tests),
frontend ~150-250. The unit exceeds the ~400-line review budget, so it ships as two stacked PRs
under `stacked-to-main`: **PR 1 backend, PR 2 UI**, PR 2 rebased on the updated `main` after PR 1
merges. No `size:exception` is needed because the split keeps each PR under budget; if PR 1 alone
lands over budget, stop and ask before opening it.

Risk note: WU2's assessment classified `tests/integration/test_migrations.py` as a
`process_boundary`, so this unit's assessment will likely come back `high` — expect a real review
transaction with consent, not a passive pass.

## Verification (exact commands)

```bash
# Backend (needs the isolated DB):
eval "$(infra/test-db.sh env)" && uv run pytest tests/ -q
# Focused first, for example:
eval "$(infra/test-db.sh env)" && uv run pytest tests/functional/test_api_clients.py -q

# Frontend:
cd web && npm test
cd web && npm run build        # tsc -b lives only here; not optional
```

The frontend suite is load-flaky: `AppShell` and `AgendaPage` have ~5.4s timeouts against a 5s
default. If the full suite fails on a timeout, run those files isolated before believing a
regression.

## Progress / Evidence

- [x] **Unit opened** — worktree `../lumat-agent-odd-clientes-merge-duplicados`, branch
      `odd/clientes-merge-duplicados` off `16d94ced`, provisioned (`.env`, `uv sync`, isolated test
      DB on port 5941, `web/node_modules`). Consent for worktree creation given explicitly.
- [x] **Decisions closed** — D4, D3 (with the activity definition the parent doc never specified),
      surface scope, M1 (memory collision), M2 (loser identity). Recorded in Engram at
      `odd/clientes-merge/decisions`.
- [x] **Graph check** — queries and nodes above; the graph surfaced the `projects.merge()`
      precedent, `ProjectAlias`, and the migration-test location.
- [x] **Five FKs confirmed** — the inherited "four FKs" list is stale; `customer_equipment`
      (`models.py:424`, migration 035) is the fifth.
- [x] **B1-B3 delivered** — migration `038_customer_merge.sql` (`ALTER TABLE customers ADD COLUMN IF NOT EXISTS merged_into_customer_id BIGINT REFERENCES customers (id)`; no new grants needed — `036`/`037` add none either), `Customer.merged_into_customer_id` (`models.py:249-251`, no `relationship` — nothing needs it), and `merge_customers()` (`app/services/customers.py:233-360`). The service locks both rows `with_for_update()` ordered by id, applies the I2/I3 guards, resolves the survivor by D3 (activity sum, tie → older `created_at`, then lower id for determinism), fills empty scalars and records conflicts, reassigns the five FKs, applies the M1 memory policy (dedupe byte-equivalent rows with `MemoryObservation.memory_id` + `MemoryRelation` repointing and `duplicate_count` summed; survivor wins on a content conflict with the loser's content in the audit payload), re-keys `memory_observations.entity_id` in a separate update, writes the M2 tombstone, and emits exactly one `customer.merged` audit row. Commits `96928f5c` (migration + model + migration test) and `1f2c0781` (service + tests).
- [x] **B1-B3 RED** — `eval "$(infra/test-db.sh env)" && uv run pytest tests/integration/test_customers.py -q -k merge_customers` → 5 failed, all `AttributeError: module 'app.services.customers' has no attribute 'merge_customers'`.
- [x] **B1-B3 GREEN** — focused `tests/integration/test_customers.py` and `tests/integration/test_migrations.py` green; full `uv run pytest tests/ -q` reached `[100%]` with no failures (pre-existing unawaited-`_publish_all` and fastembed warnings only). New coverage: five FK reassignment + audit, activity survivor + scalar fill, `same`/`tombstone` guards, observation re-key, tie → older + archived preference, equivalent-memory dedupe + content conflict recorded. `test_customers_merge_tombstone_column` asserts the new column and its self-FK.
- [x] **B1-B3 parent spot check** — re-ran `tests/integration/test_customers.py tests/integration/test_migrations.py`: **57 passed**.
- [x] **B1-B3 graph check** — the writer queried the merge/lock/memory/migration areas and consulted `merge()`, `_lock_projects()`, `_memory_equivalent()`, `Customer`, `Conversation`, `Case`, `CustomerNote`, `CustomerEquipment`, `Appointment`, `MemoryObservation`, `MemoryRelation`, `record_audit()`, `test_migrations.py`. Source inspection confirmed five pre-existing customer FKs (the sixth `ForeignKey("customers.id")` match is the new self-FK) and that `036`/`037` add no grants.
- [x] **B1-B3 parent diff review** — read the whole diff, not just the report. Two claims checked against source: (1) the conflict branch deletes the loser memory without repointing its `MemoryObservation.memory_id` — **harmless**, because production never sets `memory_id` (`_write_observation`, `tukulpan.py:918-930`, writes only `scope`/`entity_id`/`tipo`/`detalle`); the writer did repoint `MemoryRelation`, whose FKs are `NOT NULL` and therefore genuinely required. It is a latent asymmetry worth an advisory, not a defect. (2) All customer memories are `scope='customer'` + `entity_id=str(customer_id)` (`clients.py:569`, `:271`, `:441`), so the merge's memory scope is complete — the other `entity_id` uses are audit rows or `scope='panel'` with `thread:{id}`.
- [x] **B1-B3 advisory (non-blocking)** — repointing `MemoryRelation` endpoints can create a self-loop (`id_a == id_b`) if a relation ever linked a loser memory to the survivor's corresponding row. `MemoryRelation` has no constraint preventing it and `projects.merge()` behaves identically, so it is inherited, improbable (relations are judged within one customer's memories) and not a constraint violation. Recorded, not fixed.
- [ ] B4-B6 — backend slice (ingest resolution + API)
- [ ] F1-F3 — frontend slice
- [ ] O1 — assessment + review

## Closure

Not closed. No code written. Backend slice is the next unit of work.

## Recovery

- Nothing to resume beyond the task list above.
- Parent unit: `odd/tasks/clientes-operativa.md` — WU1-WU3 merged, WU4 moved here.
- Other live worktrees — do not touch: `../lumat-agent-odd-agenda-agente-whatsapp`
  (`odd/agenda-agente-whatsapp`) and the principal worktree. Remote branch
  `origin/odd/agenda-operator-technicians` also exists.
- The principal worktree's `stash@{0}` (`uv.lock regenerated locally`) is pre-existing from
  another handoff: do not touch.
- Latest migration on `main` is `037` (`037_memory_owner_dedup.sql`); this unit's migration is `038`.
- `main` moves on its own: `git fetch origin` immediately before every merge/PR.
- Test DB: `bash infra/test-db.sh up|down|env` (project name derives from the worktree slug).
- `graphify-out/` is gitignored; query the graph from the principal worktree.
