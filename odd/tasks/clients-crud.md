# ODD Task: clients-crud

Status: in progress
Worktree: `../lumat-agent-odd-clients-crud`
Branch: `odd/clients-crud-wu3`
Base: `1fdddcee` (main after WU2; this worktree started at `50bce481`, current `origin/main`)
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
`tests/functional/test_api_clients.py`, `tests/integration/test_customers.py`,
`tests/integration/test_migrations.py` (its `schema_migrations` registry is a
hardcoded expected list, so adding a migration requires extending it — see
Constraints).

**In (frontend):** `web/src/api.ts`, `web/src/types.ts`,
`web/src/components/pages/ClientesList.tsx`,
`web/src/components/pages/ClientFicha.tsx`, their tests, their stories.

**Out:** any Customer/Case data-model merge; the `/panel/app/cases` page and its
placement (U4); lifecycle-vs-operational status and tasks/reminders (Q4,
explicitly out); the per-appointment page (U5, `agenda-redesign`); any new
dependency; `tokens.css` values; hard/soft **delete** of a customer.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-clients-crud`
- Branch: `odd/clients-crud-wu3`
- Base: `1fdddcee` (worktree start: `50bce481`)
- Files: as listed in Scope.

## Constraints

- **Strict TDD: ON** (`openspec/config.yaml` → `testing.strict_tdd: true`).
  Backend runner `uv run pytest tests/`; frontend runner `cd web && npm run test`.
  Observe RED before each source change; never invent RED evidence.
- Migrations are plain SQL files applied by `./db/migrate.sh` (sorted, tracked in
  `schema_migrations`, one transaction per file). There is no Alembic. The test
  suite applies them through the `migrated_db` fixture (`tests/conftest.py:100`).
  **Adding a migration also requires extending the hardcoded expected version list
  in `tests/integration/test_migrations.py` (`test_schema_migrations_records_version`
  around `:344-382`)**; otherwise the full suite fails on that registry.
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

### WU1 — archive, backend vertical — DELIVERED as PR #378

- [x] **T1 (be)** — RED first in `tests/integration/test_customers.py` and
  `tests/functional/test_api_clients.py`: `search_customers` excludes an archived
  customer by default and includes it with `include_archived=True`;
  `archive_customer` / `unarchive_customer` set and clear `archived_at` and write
  `customer.archived` / `customer.unarchived` audit rows; an inbound
  `get_or_create_customer` on an archived phone clears `archived_at` and writes
  `customer.auto_unarchived`.
- [x] **T2 (be)** — the schema and the service: migration
  `033_customer_archived_at.sql`, `Customer.archived_at`, the `search_customers`
  parameter, the two archive functions and the auto-unarchive branch in
  `get_or_create_customer`. Delivered as two commits: `68744267` (migration +
  model) and `f181e8c6` (service + tests).
- [x] **T3 (be)** — the routes and the payload: `POST /clients/{id}/archive`,
  `POST /clients/{id}/unarchive` (audited, actor from `require_operator_json`),
  `include_archived` on `GET /clients`, and `archived_at` in `to_customer_dict`.
  Commit `c5b43049`.
- [x] **WU1 verification of record** — full `uv run pytest tests/` → **1499
  passed**, exit 0. Slice branch `odd/clients-crud` pushed; PR **#378** (base
  `main`, label `type:feature`).

### WU2 — create, profile update and consent, backend vertical

- [x] **T4 (be)** — RED first in `tests/functional/test_api_clients.py`:
  `POST /clients` returns `201` with the new ficha for a fresh phone, `409` with
  `{"code": "phone_exists", "customer_id": <id>}` for an existing phone
  (archived included), `422` for a missing or non-normalizable phone; the created
  customer has `state = nuevo` and `consent_status = false`; `PATCH /clients/{id}`
  updates name/email/comuna/address, ignores an omitted field, rejects an empty
  string with `400`, and **cannot** change the phone; `POST /clients/{id}/consent`
  flips consent with `customer.consent_updated` in the audit carrying the actor.
  Delivered as `2f2487ad` and `fb57ff30`.
- [x] **T5 (be)** — a `create_customer` service function that raises a typed
  conflict carrying the existing id (the route maps it to `409`, following the
  exception-to-409 pattern of `routes/appointments.py:56-70`); the three routes;
  route-level `record_audit` for the profile update (D4).
- [x] **WU2 verification of record** — full `uv run pytest tests/` → **1508
  passed**, exit 0 (1499 at the WU2 base, +9 tests). Slice code diff
  `2a5c53dd..HEAD` over `app/ tests/`: **309 changed lines** (307 added, 2
  deleted), 4 files.
- [x] **WU2 native review: not applicable — `under_budget`.** `gentle-ai review
  assess` over `2a5c53dd..HEAD --committed-only` reports `risk: medium` (reason
  `executable_change` on `app/panel/api/routes/clients.py`), `changed_lines: 311`,
  `review_due: false`, `review_due_reason: under_budget`. Native RAR owns
  verification applicability, so **no review transaction was started** and no
  receipt exists for this slice. The orchestrator does not author PASS and does
  not manufacture a review RAR declares inapplicable. Independent checks that do
  exist: the parent read the entire production diff against the contract, reran
  the full suite, and CI runs both the `test` and `panel` jobs on the PR.

### WU3 — frontend: api layer + list page

- [x] **T6 (fe)** — RED first: `ApiError` exposes the parsed structured detail
  (D6); `listClients` takes `includeArchived`; `createCustomer`,
  `updateCustomerProfile`, `archiveCustomer`, `unarchiveCustomer` exist with the
  routes above.
- [x] **T7 (fe)** — RED first in `ClientesList`: a "Nuevo cliente" action opens a
  create form in the existing `Dialog` primitive (phone required; a duplicate
  phone surfaces "abrir la ficha existente" and navigates to it); a "Mostrar
  archivados" toggle drives `include_archived`; an archived row is visibly
  marked; the row archive action fetches the ficha once and confirms with the D7
  counts.
- [x] **WU3 verification of record** — `cd web && npm run test` → **91 files / 806
  tests passed**, exit 0; `cd web && npx tsc -b --noEmit` → exit 0;
  `cd web && npm run build` → exit 0 (Vite production build; existing >500 kB
  chunk advisory). The first full-suite attempt exceeded its 120-second command
  timeout and the next run exposed unrelated intermittent timeouts; isolated
  reruns passed, and the subsequent complete suite passed. Focused WU3 tests:
  **60 passed**. RED evidence: T6 `apiFetch > preserves structured conflict
  detail additively` lacked `structuredDetail`; `client API contracts > lists
  clients with encoded search and archive filters` called the unfiltered path;
  `client API contracts > uses the customer CRUD routes and payloads` failed
  because `createCustomer` was not a function. T7 `ClientesList > opens the
  create dialog and offers ficha navigation for a duplicate phone` could not
  find `Nuevo cliente`; `ClientesList > loads D7 counts once before confirming
  archive and supports unarchive` could not find the row archive action; and
  `ClientesList > shows the archived filter and marks archived customers` could
  not find the archived filter checkbox. Strict TDD RED was observed before the
  production edits; the focused tests and full suite then passed.

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
- [x] **Graph freshness caveat (recorded):** `graphify-out/` is shared by every
      worktree and a concurrent actor refreshed the top-level
      `GRAPH_REPORT.md` mid-session: it read `Built from commit: 7fb8cd10` at plan
      time and `28fd4ad3` afterwards (another branch's tip). The dated snapshot
      `graphify-out/2026-09-26/GRAPH_REPORT.md` still records `7fb8cd10`, which is
      this branch's base, and is the report of record for this unit. The nodes this
      unit depends on (`Customer`, `search_customers`, `record_audit`, `clients.py`,
      `serializers.py`) are unchanged across both commits, so the query results stay
      valid — but a graph check taken from the shared top-level file can silently
      describe someone else's branch.
- [x] T1/T2/T3 (WU1) — archive backend vertical. RED observed (no
      `archive_customer`; archived records still listed; archive routes missing),
      then GREEN. Commits `68744267` (migration + model), `f181e8c6` (service +
      tests), `c5b43049` (routes + serializer + tests). WU1 code diff
      `7fb8cd10...HEAD` over `app/ db/ tests/`: **203 changed lines** (201 added,
      2 deleted), 7 files.
- [x] Migration registry updated — `tests/integration/test_migrations.py` gains
      `("033_customer_archived_at",)`. This was the writer's single suite failure
      (`1498 passed, 1 failed`) and it was **outside the originally authorized
      list**; it is a mechanical, already-understood consequence of adding a
      migration, not a new requirement, so it was authorized and fixed inline.
- [x] WU1 verification of record: `uv run pytest tests/` → **1499 passed**
      (229.49s), exit 0 — up from the 1493 baseline (+6 new tests).
- [x] **WU1 native review** — lineage `review-252398aaefabd88a`, risk tier
      `high` (reason `process_boundary` / `shell_process` on
      `tests/integration/test_migrations.py`, i.e. a test that spawns
      `db/migrate.sh` — not production code). Four lenses (risk, resilience,
      readability, reliability), **zero findings**, `approved`, authority
      **burned** (`gentle-ai.review-acknowledged/v1`). Owner granted the review
      through the consent envelope; the owner also chose `stacked-to-main` and
      Q2 = "warn, do not block" earlier in the session.
- [x] **PR #378** opened — `feat(clients): archive customers without deleting
      them`, base `main`, label `type:feature`. Branch `odd/clients-crud`.
- [x] **Coverage caveat (recorded, and stated in the PR):** the receipt freezes
      the candidate `7fb8cd10..e5e1cfe4` (`candidate_tree` `acd4d413`). This
      docs-only commit — the one that records the PR number — lands **after**
      that freeze and is **not** covered by it. Neither is any merge commit that
      brings the branch level with `main` before merge. No coverage is claimed
      for either.
- [x] **WU2 implemented** on branch `odd/clients-crud-wu2` off the merged `main`
      (`2a5c53dd`). Commits `2f2487ad` (service + integration tests), `fb57ff30`
      (routes + functional tests), `e89db7fa` (login-contract coverage). The
      contract was followed, including the two ordering hazards it named:
      `PhoneAlreadyExists` subclasses `ValueError`, so the route must catch it
      **first**, or the `409` degrades into a `422`; and `create_customer`'s
      duplicate lookup deliberately does **not** filter `archived_at`, because the
      phone is the identity and a phone held by an archived record is still taken.
- [x] **Coverage gap found in WU1 and fixed here.** `test_clients_endpoints_require_login_401_json`
      claims to cover "every clients endpoint" but WU1 never added
      `POST /{id}/archive` and `POST /{id}/unarchive` to its list. The runtime
      behaviour was already correct (`require_operator_json` is a route
      dependency); only the enumerated contract was incomplete. Both are now in
      the list, committed **before** this slice's assessment so they sit inside
      whatever coverage the slice has.
- [x] **Graph refreshed** to `2a5c53dd` — the post-merge refresh the Rapsodia
      policy owns, triggered by the verified merge SHA of PR #378 on `main`.
      `graphify <root> --update` then `graphify cluster-only <root>`;
      `GRAPH_REPORT.md` now reads `Built from commit: 2a5c53dd`. **Honest note:**
      the Graphify guidance states the incremental update has no API cost; it
      actually consumed ~74.8k input / ~30.3k output tokens (~US$0.019) on this
      repo, and the report only regenerates with the separate `cluster-only` step.
      `odd/tasks/clients-crud.md` is included in the graph corpus now that it is
      on `main`.
- [x] **PR #381** opened — `feat(clients): create clients and edit their profile
      and consent`, base `main`, label `type:feature`. Branch
      `odd/clients-crud-wu2`. `main` moved twice more while this slice was in
      flight (#379, #380); the base `2a5c53dd` stayed an ancestor and
      `git merge-tree --write-tree origin/main HEAD` reported a clean merge
      before the push.
- [x] **WU3 implemented** on `odd/clients-crud-wu3`, starting at `50bce481`.
      T6/T7 delivered in commits `aa793758` (API types, structured conflict
      payload, list and mutation functions; 60 changed lines across 3 files) and
      `1f09748b` (create/archive list workflows and tests; 160 changed lines
      across 3 files). Total authored code diff: **220 changed lines**, 6 files.
- [x] **WU3 Graph Check record** — the orchestrator completed the graph check
      before this implementation; no graph refresh was run. Nodes consulted:
      `ClientesList.tsx`, `ClientFicha.tsx`, `api.ts`, `apiFetch()`, `postJson()`,
      `types.ts`, `useAsyncData.ts`, `Button.tsx`, `Dialog.tsx`,
      `app/panel/api/serializers.py` (`to_customer_dict`), and
      `shared/StateMessage.tsx`. Communities: `ClientesList.tsx`,
      `ClientFicha.tsx`, `types.ts`, `useAsyncData`, and `pages/CasesList.tsx`.
- [x] **WU3 implementation details** — the page now uses `fetchClients` rather
      than a divergent inline fetch, retains controlled props and `useAsyncData`,
      reads ficha counts only after the operator requests archiving, and uses the
      existing `Dialog`, `Input`, `Button`, `Badge`, and `DataTable` primitives.

## Recovery

- Worktree: `/home/stefan/repos/lumat-agent-odd-clients-crud`,
  branch `odd/clients-crud-wu3`, base `1fdddcee` (started at `50bce481`).
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
