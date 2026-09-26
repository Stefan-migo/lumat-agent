# ODD Task: clients-crud

Status: in progress
Worktree: `../lumat-agent-odd-clients-crud`
Branch: `odd/clients-crud`
Base: `7fb8cd10` (main, after U1 `case-closure-fix` and U2 `client-ficha-case-surface`)
Depends on: nothing — U3 is independent of U1/U2
Source: `.rapsodia-code/sessions/ready-for-odd/2026-09-25-clientes-crm/report.md`
Delivery strategy: `ask-on-risk`
Chain strategy: `stacked-to-main` (owner decision 2026-09-26) —
PR 1 = WU1 (archive backend), PR 2 = WU2 (create/profile/consent backend),
PR 3 = WU3 (api layer + list page), PR 4 = WU4 (ficha profile/consent/archive)

## Objective

The Clientes section gets a working CRUD on top of what already exists:

- `POST /clients` — phone required, `409` when the phone already exists, initial
  state `nuevo`, consent `false`;
- `PATCH /clients/{id}` — profile edit (name, email, comuna, address) reusing
  `update_captured_data`; the phone is immutable from the panel;
- `POST /clients/{id}/consent` — consent editable, actor in the audit trail;
- archive through a new nullable `archived_at` column plus a filter in
  `search_customers`, with the UI in the list and in the ficha;
- auto-unarchive on re-contact (D6): an archived customer who writes again comes
  back on its own.

## Problem

Verified against the code at base `7fb8cd10`. Every claim is evidence.

### Read and partial update exist; create, profile update and delete do not (F2)

`app/panel/api/routes/clients.py` exposes `GET /clients` (`:98`), `GET /clients/{id}`
(`:109`), `POST /clients/{id}/state` (`:142`), `POST /clients/{id}/notes` (`:161`),
plus the memory routes (`:191`, `:229`, `:250`, `:302`, `:358`, `:385`). There is
**no** create, **no** profile update, **no** archive and **no** consent route.

The service layer already has every piece the routes need:
`normalize_phone_e164` (`app/services/customers.py:85`),
`get_or_create_customer` (`:107`), `set_customer_state` (`:137`),
`add_note` (`:174`), `list_notes` (`:182`), `search_customers` (`:198`),
`customer_history` (`:224`), `update_captured_data` (`:342`),
`record_consent` (`:363`).

### There is no archive concept at all (F2, P1)

`Customer` (`app/models.py:218-235`) has `id`, `phone_e164` (String(20),
non-null, **unique**), `name`, `email`, `comuna`, `address`, `state`,
`consent_status`, `consent_at`, `created_at`. No `archived_at`, no `is_active`,
no soft delete. `search_customers` has no archive predicate, and
`to_customer_dict` (`app/panel/api/serializers.py:45-59`) carries no archive
field. Nothing in `app/` reuses `state = cancelado` for this, and `CustomerState`
(`app/models.py:60-68`) is a business lifecycle
(`NUEVO, CONTACTADO, PENDIENTE, AGENDADO, EN_EVALUACION, FINALIZADO, CANCELADO,
POSTVENTA`), not a working-record flag.

The nearest precedent in the repo is `AssistantAttachment.deleted_at`
(`app/models.py:831-843`, migration `db/migrations/022_assistant_attachments.sql:11-13`)
with query-level `deleted_at.is_(None)` filters — a nullable timestamp plus a
filtered read, which is the shape this unit follows.

### Hard delete is impossible, and a naive insert is a crash

Every FK into `customers` has no `ondelete`, so an archive row cannot be removed;
that is why the unit uses `archived_at`. Conversely `phone_e164` is
**NOT NULL UNIQUE** (`app/models.py:222`), so a naive `INSERT` on a duplicate
phone raises an integrity error instead of a clean `409`.

### Nothing consumes the field yet, but one consumer will (F2, P1)

`update_captured_data` and `record_consent` (**neither audits**) are consumed by
the bot's capture node (`app/chat/nodes/capture.py:93` and `:102`), which is why
this unit does not change their contract (see D4). `search_customers` is consumed
not only by the panel (`routes/clients.py:105`) but also by the assistant tool
registry (`app/chat/assistant/tools/registry.py:256-257`, registered as
`customers.search` / `customers.list` at `:540-541`), so a default filter changes
what the bot can see (see D2).

## Scope

**In (backend):** `db/migrations/033_customer_archived_at.sql` (new),
`app/models.py`, `app/services/customers.py`,
`app/panel/api/routes/clients.py`, `app/panel/api/serializers.py`,
`tests/functional/test_api_clients.py`, `tests/integration/test_customers.py`.

**In (frontend):** `web/src/api.ts`, `web/src/types.ts`,
`web/src/components/pages/ClientesList.tsx`,
`web/src/components/pages/ClientFicha.tsx`, their tests, their stories.

**Out:** any Customer/Case data-model merge; the `/panel/app/cases` page and its
placement (U4); lifecycle-vs-operational status and tasks/reminders (Q4,
explicitly out); the per-appointment page (U5, `agenda-redesign`); any new
dependency; `tokens.css` values; hard/soft **delete** of a customer.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-clients-crud`
- Branch: `odd/clients-crud`
- Base: `7fb8cd10`
- Files: as listed in Scope.

## Constraints

- **Strict TDD: ON** (`openspec/config.yaml` → `testing.strict_tdd: true`).
  Backend runner `uv run pytest tests/`; frontend runner `cd web && npm run test`.
  Observe RED before each source change; never invent RED evidence.
- Migrations are plain SQL files applied by `./db/migrate.sh` (sorted, tracked in
  `schema_migrations`, one transaction per file). There is no Alembic. The test
  suite applies them through the `migrated_db` fixture (`tests/conftest.py:100`).
- Artifacts in English. Conventional commits, no AI attribution. Merge commits,
  never squash.
- UI copy stays neutral Chilean Spanish; no raw backend identifier reaches the
  surface (`web/DESIGN_SYSTEM.md`).
- Work-unit commits on this branch are authorized. Push, PR and merge require
  explicit owner authorization.
- Graph Check (Rapsodia Step 1) runs before each task; record the nodes consulted
  in the Progress section. `graphify-out/` is gitignored: query it from
  `/home/stefan/repos/lumat-agent`.

## Decisions

- **D1 — Archive is a nullable `archived_at` column plus a filter, not
  `state = cancelado` (P1).** `cancelado` is a business fact that gets measured;
  archived means "a record that is not worked" (spam, test, duplicate).
  Alternative rejected: reuse the state enum, which would overwrite a measured
  business fact and need no migration but corrupt the CRM baseline (F8).
- **D2 — `search_customers` gains `include_archived: bool = False`; the default
  excludes archived records.** The panel passes `true` only for the "show
  archived" toggle and for resolving a create conflict. The assistant tools keep
  the default: the bot does not resurrect archived spam. **Recorded ceiling:** an
  operator asking the assistant about an archived record gets "not found"; if that
  turns out to matter, the fix is a tool-schema parameter, not a change here.
  Alternative rejected: filter only in the panel route, which would leave the bot
  as a second, divergent definition of "archived".
- **D3 — Auto-unarchive lives inside `get_or_create_customer`
  (`app/services/customers.py:107`).** That function is already the "contact
  arrives" write path (it inserts and audits `customer.auto_created` on first
  contact) and it is the single place every inbound path funnels through
  (`app/webhook/ingest.py:239`, `app/chat/state.py:30`). Putting it there means
  D6 cannot be bypassed by a new caller. Alternative rejected: hook it in
  `app/webhook/ingest.py` only, which would leave a second inbound caller
  unarchived and needs the same code twice.
- **D4 — `update_captured_data` and `record_consent` do not change contract.**
  Neither audits today; the **route** supplies the actor with `record_audit`,
  exactly like `POST /clients/{id}/state` (`routes/clients.py:152-154`, where the
  service audits internally) and `POST /clients/{id}/notes` (`:174-181`, where the
  route audits). Consequence, recorded as a ceiling: a profile field cannot be
  **cleared** through the API in this unit — `None` already means "do not touch"
  in `update_captured_data`, and the bot's capture node depends on that meaning.
  An empty string is rejected with `400`, not silently ignored. Upgrade path if
  the owner wants clearing: a dedicated `clear` convention, decided on its own.
- **D5 — The create conflict returns a structured `409` carrying the existing
  customer id.** Precedent: `routes/appointments.py:64-66`,
  `routes/calendar_templates.py:72` and `routes/notifications.py:78` already
  return `detail={"code": ..., "message": ...}` on `409`; `routes/users.py:67`
  returns a plain string. The ficha must offer "open the existing record"
  (handoff), and the server has already resolved the E.164 identity, so the id is
  returned instead of making the client re-derive it. **Rejected alternative:**
  the frontend re-searches by phone and matches in TS — that reimplements E.164
  normalization in TypeScript, exactly the second-definition mistake U2 rejected
  for the open-case predicate.
- **D6 — `ApiError` gains an optional parsed `detail` payload
  (`web/src/api.ts:10-22`).** Today `apiFetch` only assigns `detail` when the JSON
  `detail` is a string, so a structured `409` reaches the UI as raw JSON text and
  the id is unreachable. The change is additive: `detail` keeps its type and
  string behaviour, and a new optional field carries the object. Alternative
  rejected: loosen the `409` detail to a string plus a custom header, which hides
  the identifier in a transport header the SPA would have to parse by hand.
- **D7 — Archiving warns, it does not block (Q2, owner decision 2026-09-26).**
  The confirm step shows how many open cases and how many future appointments the
  customer has, and lets the operator proceed. This keeps D6's philosophy
  (archiving is not a wall) while the risk — losing the surface to operate live
  work — stays visible at the moment of deciding. **No new backend query:** the
  ficha payload already carries `is_open` per case (U2) and the appointments, so
  the counts are computed from data already loaded. A row action in the **list**
  fetches the ficha once, on the operator's click, before confirming — one request
  on an explicit action, never an N+1 over the page.
- **D8 — Archive and unarchive are `POST /clients/{id}/archive` and
  `POST /clients/{id}/unarchive`.** The file's existing shape is `POST` on a
  sub-resource for a state change (`/{id}/state`, `/{id}/notes`), and archive is a
  state change with an audit. Alternative rejected: a `PATCH` field, which would
  let a profile edit silently archive a customer.
- **D9 — No index on `archived_at`.** The list is capped at `limit=100`
  (`routes/clients.py:105`) and `customers` is small; the nearest precedent adds a
  composite index (`022_assistant_attachments.sql:13`) but for a much larger
  table. Recorded ceiling: if `customers` grows past a few tens of thousands,
  revisit with `(archived_at, created_at DESC)`.

## Tasks

Forecast at planning time: **~1150–1400 authored lines** across backend, frontend
and tests — well over the ~400 review-focus budget, so the chain strategy applies
before the first source commit (owner decision pending).

### WU1 — archive, backend vertical

- [ ] **T1 (be)** — RED first in `tests/integration/test_customers.py` and
  `tests/functional/test_api_clients.py`: `search_customers` excludes an archived
  customer by default and includes it with `include_archived=True`;
  `archive_customer` / `unarchive_customer` set and clear `archived_at` and write
  `customer.archived` / `customer.unarchived` audit rows; an inbound
  `get_or_create_customer` on an archived phone clears `archived_at` and writes
  `customer.auto_unarchived`.
- [ ] **T2 (be)** — the schema and the service: migration
  `033_customer_archived_at.sql`, `Customer.archived_at`, the `search_customers`
  parameter, the two archive functions and the auto-unarchive branch in
  `get_or_create_customer`. Commit split so each commit stays ≤5 files:
  (a) migration + model, (b) service + tests.
- [ ] **T3 (be)** — the routes and the payload: `POST /clients/{id}/archive`,
  `POST /clients/{id}/unarchive` (audited, actor from `require_operator_json`),
  `include_archived` on `GET /clients`, and `archived_at` in `to_customer_dict`.
- [ ] **WU1 verification of record** — full `uv run pytest tests/`.

### WU2 — create, profile update and consent, backend vertical

- [ ] **T4 (be)** — RED first in `tests/functional/test_api_clients.py`:
  `POST /clients` returns `201` with the new ficha for a fresh phone, `409` with
  `{"code": "phone_exists", "customer_id": <id>}` for an existing phone
  (archived included), `422` for a missing or non-normalizable phone; the created
  customer has `state = nuevo` and `consent_status = false`; `PATCH /clients/{id}`
  updates name/email/comuna/address, ignores an omitted field, rejects an empty
  string with `400`, and **cannot** change the phone; `POST /clients/{id}/consent`
  flips consent with `customer.consent_updated` in the audit carrying the actor.
- [ ] **T5 (be)** — a `create_customer` service function that raises a typed
  conflict carrying the existing id (the route maps it to `409`, following the
  exception-to-409 pattern of `routes/appointments.py:64-66`); the three routes;
  route-level `record_audit` for the profile update (D4).
- [ ] **WU2 verification of record** — full `uv run pytest tests/`.

### WU3 — frontend: api layer + list page

- [ ] **T6 (fe)** — RED first: `ApiError` exposes the parsed structured detail
  (D6); `listClients` takes `includeArchived`; `createCustomer`,
  `updateCustomerProfile`, `archiveCustomer`, `unarchiveCustomer` exist with the
  routes above.
- [ ] **T7 (fe)** — RED first in `ClientesList`: a "Nuevo cliente" action opens a
  create form in the existing `Dialog` primitive (phone required; a duplicate
  phone surfaces "abrir la ficha existente" and navigates to it); a "Mostrar
  archivados" toggle drives `include_archived`; an archived row is visibly
  marked; the row archive action fetches the ficha once and confirms with the D7
  counts.
- [ ] **WU3 verification of record** — `cd web && npm run test` +
  `npx tsc -b --noEmit` + `npm run build`.

### WU4 — frontend: ficha profile, consent and archive

- [ ] **T8 (fe)** — RED first in `ClientFicha`: the "Identidad" card gets a
  profile edit form in a `Dialog` (phone shown read-only); a consent control posts
  to `/clients/{id}/consent` and refetches; an "Archivar" / "Restaurar" control
  confirms with the D7 warning (open cases + future appointments) and refetches
  the ficha. Stories updated for the new states.
- [ ] **WU4 verification of record** — `cd web && npm run test` +
  `npx tsc -b --noEmit` + `npm run build`.
- [ ] **Review measurement** — `gentle-ai review assess` over
  `base-ref..HEAD --committed-only` before declaring the unit closed; a docs-only
  commit can cross the budget on its own (handoff trap 10).

## Acceptance criteria

1. A customer can be created from the panel with a phone, and a duplicate phone
   produces a `409` whose UI affordance opens the existing ficha — never a raw
   error and never a duplicate row.
2. Profile fields (name, email, comuna, address) can be edited; the phone cannot
   be changed from the panel.
3. Consent is editable and the audit row names the operator who changed it.
4. A customer can be archived and restored from the panel; an archived customer
   disappears from the default list and from the assistant's view, and is visible
   again behind the "show archived" toggle.
5. An archived customer who writes again is unarchived automatically, with an
   audit row.
6. Archiving warns about open cases and future appointments and does not block.
7. Only the authorized files change; no new dependency.
8. `uv run pytest tests/`, `cd web && npm run test`, `cd web && npx tsc -b --noEmit`
   and `cd web && npm run build` pass.

## Checks

- `eval "$(./infra/test-db.sh env)" && uv run pytest tests/`
- `cd web && npm run test`
- `cd web && npx tsc -b --noEmit`
- `cd web && npm run build`
- `git diff --check`

## Progress

- [x] Worktree created (`rapso worktree create clients-crud --yes`), provisioned
      (`uv sync`, `npm ci`), test DB up on `:5702`.
- [x] Baseline on the untouched worktree at `7fb8cd10`: `uv run pytest tests/` →
      **1493 passed** (183.96s); `cd web && npm run test` → **91 files / 792
      tests, all passing**; `npx tsc -b --noEmit` → exit 0.
- [x] Graph Check (Step 1) at plan time, from `/home/stefan/repos/lumat-agent`
      (graph built from `7fb8cd10` — the same commit as this branch's base):
      `graphify query "client CRUD customers panel routes and customer service
      state transitions"`. Nodes consulted: `Customer` (`app/models.py:218`),
      `CustomerState` (`app/models.py:60`), `models.py`, `serializers.py`,
      `routes/conversations.py`, `ClientFicha.tsx`, `ClientesList.tsx`,
      `pages/CasesList.tsx`, `ConversationsList.tsx`, `record_audit()`
      (`app/services/audit.py:18`), `get_settings()`, `StateMessage()`
      (`web/src/components/shared/StateMessage.tsx:19`), `client()`
      (`tests/conftest.py:127`), `test_api_cases.py`, `test_api_kb_settings.py`.
      Communities: `Customer`, `models.py`, `serializers.py`, `ClientFicha.tsx`,
      `pages/CasesList.tsx`. **Note:** an earlier delegated mapping pass read a
      stale report (`graphify-out/2026-09-22/`, commit `4e027047`) and wrongly
      reported "no modal component exists" — `web/src/components/primitives/Dialog.tsx`
      exists, together with `Input`, `FieldShell`, `Select`, `Button`, `Textarea`,
      `Combobox`, `Badge`, `StatusBadge`. The create form and the archive confirm
      reuse them; nothing is invented.
- [ ] T1 …

## Recovery

- Worktree: `/home/stefan/repos/lumat-agent-odd-clients-crud`,
  branch `odd/clients-crud`, base `7fb8cd10`.
- Test DB: `bash infra/test-db.sh up|down|env`, project
  `lumat-test-lumat-agent-odd-clients-crud`, port `5702`.
- `graphify-out/` is gitignored and absent from this worktree: query the graph
  from `/home/stefan/repos/lumat-agent`. Refresh once at session close.
- On resume: read this file and reconcile the checkbox state against `git log`
  before continuing.
- Session of record:
  `.rapsodia-code/sessions/ready-for-odd/2026-09-25-clientes-crm/`.
- Handoff of record: `.rapsodia-code/handoffs/2026-09-26-clientes-u3-u4.md`
  (Engram `#5112`).
