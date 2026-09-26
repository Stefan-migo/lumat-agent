# ODD Task: client-ficha-case-surface

Status: in progress
Worktree: `../lumat-agent-odd-client-ficha-case-surface`
Branch: `odd/client-ficha-case-surface`
Base: `cf5f8171` (main, after U1 `case-closure-fix` and the `set_case_status` rename)
Depends on: `case-closure-fix` (U1, delivered)
Source: `.rapsodia-code/sessions/ready-for-odd/2026-09-25-clientes-crm/report.md`
deleted from canonical sessions dir; local copy of record below.
Delivery strategy: `ask-on-risk`
Chain strategy: unresolved (asked only when the ~400-line budget is reached)

## Objective

`ClientFicha` becomes the fused Customer+Case surface:

- the active case gets a "Caso activo" block with case actions at the top of the
  main column, above Memo;
- the case payload carries what the surface needs to render and operate it
  (emergency, responsible, created_at, ack_by, and the users list);
- the visit-audit `<ol>` trail leaves the ficha (it belongs to the
  per-appointment page, U5 of `agenda-redesign`);
- messages get a real backend limit plus a shared collapsible (last 10) in both
  the ficha and the conversation thread.

Slices: **S1** (case payload + Caso activo + trail removal) ships first;
**S2** (message limit + shared collapsible) follows in the same unit.

## Problem

Verified against the code at base `cf5f8171`. Every claim is evidence.

### The ficha's case data is not enough to operate a case (F7)

`customer_history` serializes cases with only `id, conversation_id, service,
priority, status, summary` (`app/services/customers.py:279-289`). It omits
`customer_id`, `created_at`, `emergency`, `responsible_id`, `escalated_at`,
`closed_at`, `acknowledged_at` and `ack_by` — every field `to_case_dict` carries
(`app/panel/api/serializers.py:151-169`). The ficha endpoint also returns no
`users` list (`app/panel/api/routes/clients.py:108-133`); only `GET /cases`
returns `users` (`app/panel/api/routes/cases.py:61-75`). Without those, the ficha
cannot show responsible or emergency and has no assignment dropdown.

### The visit-audit `<ol>` is a workaround in the wrong surface (F3, D4)

`ClientFicha.tsx:248-254` renders `history.visit_history`, the flattened
`AppointmentHistory` trail of **all** appointments (`customers.py:252-267`):
`created_at · Agendada/Cancelada · actor`. It stacks under the real visits `<ul>`
with no hierarchy and no anchor to an appointment. `to_appointment_dict` already
carries `history` (`serializers.py:186-206`), so the per-appointment page
inherits the trail; the ficha copy is dead once the `<ol>` is gone.

### Messages are unbounded, and ascending (F4, D5)

`history.messages` returns every message of every conversation for the customer,
no limit (`customers.py:241-246`). The conversation detail does the same
(`routes/conversations.py:282-300`). Both order ascending `(created_at, id)`, so
a naive "first 10" collapse would show the **oldest** ones. The `limit=50` that
exists belongs to the conversation **queue** (`conversations.py:175-204`). A
visual-only collapse reduces neither payload nor DOM.

### The case actions exist but are unreachable (F6)

`CaseActions` is private to `CasesList.tsx:31-90`, which has no import in the app
tree. It already knows status + responsible + acknowledge against
`POST /panel/api/cases/{id}/update` and `/ack`. The ficha needs the same control,
so the component must be extracted, not reimplemented.

## Scope

**In (S1):** `odd/tasks/client-ficha-case-surface.md`,
`app/services/customers.py`, `app/panel/api/routes/clients.py`,
`tests/functional/test_api_clients.py`, `tests/integration/test_customers.py`,
`web/src/types.ts`, `web/src/components/pages/ClientFicha.tsx`,
`web/src/components/shared/CaseActions.tsx` (new),
`web/src/components/pages/CasesList.tsx`, `web/src/components/pages/ClientFicha.test.tsx`,
`web/src/stories/pages/ClientFicha.stories.tsx` (+ its test),
`web/src/stories/pages/CasesList.stories.test.tsx`.

**In (S2):** `app/panel/api/routes/conversations.py`,
`app/services/customers.py`, the shared messages/collapsible component under
`web/src/components/shared/`, `web/src/components/pages/ClientFicha.tsx`,
`web/src/components/pages/ConversationThread.tsx`, and their tests/stories,
`tests/functional/test_api_conversations.py`.

**Out:** any change to the `Customer`/`Case` data model or migrations; the
`/panel/app/cases` page and its placement (U4); client create/update/archive
(U3); the per-appointment page (U5, `agenda-redesign`); `tokens.css` values; any
new dependency.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-client-ficha-case-surface`
- Branch: `odd/client-ficha-case-surface`
- Base: `cf5f8171`
- Files: as listed in Scope.

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml` (`testing.strict_tdd: true`).
  Backend runner `uv run pytest tests/`; frontend runner `cd web && npm run test`.
  Observe RED before each source change; never invent RED evidence.
- The canonical open-case predicate is `case_is_open_expr()` /
  `CLOSING_CASE_STATUSES` (`app/services/cases.py:33-48`). It is **not**
  reimplemented in TypeScript.
- Actions reuse the existing endpoints; no new business logic, no new route.
- UI copy stays neutral Chilean Spanish; no raw backend identifier reaches the
  surface (`DESIGN_SYSTEM.md:425`).
- Artifacts in English. Conventional commits, no AI attribution.
- Work-unit commits on this branch are authorized. Push and PR require explicit
  owner authorization.
- Graph Check (Rapsodia Step 1) runs before each task; record the nodes
  consulted in the Progress section.

## Decisions

- **D1 — The active case is decided server-side.** `is_open` is computed in
  `customer_history` from the canonical predicate, so the surface filters on data
  instead of reimplementing the closure rule. Alternative rejected: derive "open"
  in TS from a status list, which would be a second definition of the same fact.
- **D2 — `visit_history` leaves the ficha payload.** With the `<ol>` gone nothing
  consumes it (`rg visit_history` → types, ficha, stories, one API test); U5
  reads `to_appointment_dict.history`. Alternative rejected: keep a dead payload
  field to avoid touching one test.
- **D3 — `CaseActions` is promoted to `shared/`.** Two named consumers exist
  (ficha + `CasesList`), which is the register's promotion rule. Production
  component from day one.
- **D4 — "Caso activo" is the first block of the main column (handoff D3); the
  Casos table becomes the archive.** The table renders the cases that are not the
  active one, so the live case is never duplicated.
- **D5 — S2 pays a real backend limit.** Both message lists gain a `limit` that
  returns the **latest** N in ascending order, plus a total so the UI can say
  "N de M". A visual-only collapse is rejected: it leaves the payload and DOM
  unbounded.
- **D6 — The ficha case serialization stays inline in `customer_history`.** S1
  extends the existing dict; it does not invent a service→panel-API import
  (layering inversion) nor a shared serializer module (larger refactor). The
  divergence from `to_case_dict` is a recorded ceiling, not a hidden bug.

## Tasks

### Slice S1 — case payload + Caso activo + trail removal

- [ ] **T1 (be)** — RED first in `tests/functional/test_api_clients.py` (and
  `tests/integration/test_customers.py` for the service shape): `customer_history`
  cases carry `customer_id`, `created_at`, `emergency`, `responsible_id`,
  `escalated_at`, `closed_at`, `acknowledged_at`, `ack_by`, `is_open`; and
  `GET /clients/{id}` returns `users: [{id, username}]`.
- [ ] **T2 (be)** — RED first: `visit_history` is removed from `customer_history`
  and its payload assertions are updated/deleted.
- [ ] **T3 (fe)** — RED first: extract `CaseActions` to
  `web/src/components/shared/CaseActions.tsx`; `CasesList` consumes it with no
  behaviour change (its story test stays green).
- [ ] **T4 (fe)** — RED first: the "Caso activo" block renders as the first block
  of the main column with the shared `CaseActions` wired to
  `/cases/{id}/update` and `/ack` and a refetch; the `<ol>` trail is gone; the
  Casos table renders the non-active cases.
- [ ] **T5 (fe)** — stories + test matrix for the new block and the removed
  trail.
- [ ] **S1 verification of record** — full `uv run pytest tests/` and
  `cd web && npm run test` + `npx tsc -b --noEmit` + `npm run build`.

### Slice S2 — message limit + shared collapsible

**Resolved before S2:** owner chose `stacked-to-main` (PR 1 = S1, PR 2 = S2) and
chose to **keep** the ficha Mensajes table, fixing it with a `Conversación`
column that links to `/panel/app/conversations/:id`, with the collapsible applied
there too. The table is not dropped.

Backend contract (D5):

- `customer_history(session, customer_id, messages_limit=None)` returns
  `messages` and `messages_total`. A positive `messages_limit` returns the
  **latest** N in ascending order (query DESC + limit, then reverse); no limit
  keeps the full ascending list.
- `GET /clients/{id}` gains an optional `messages_limit` query param.
- `GET /conversations/{id}` gains the same param and returns `messages_total`.
- The `limit=50` on the conversation **queue** is unrelated and stays.

- [x] **T6 (be)** — `customer_history(session, customer_id, messages_limit=None)`
      returns `messages_total` and, for a positive limit, the latest N reversed to
      ascending; `GET /clients/{id}` and `GET /conversations/{id}` accept
      `messages_limit` and the thread returns `messages_total`. RED observed (both
      endpoints returned the full list), then GREEN. Commit `161651a8`.
- [x] **T7a (fe)** — `web/src/components/shared/CollapsibleMessages.tsx`: a
      presentational disclosure control (`total`/`previewCount`/`expanded`/`onToggle`)
      that owns no fetch and no rendering. RED observed (module not resolvable), then
      GREEN. Commit `061f062c`.
- [x] **T7b (fe)** — the ficha requests `messages_limit=10` while collapsed, expands
      through the hook's `retry()` (clearing the `refreshed` override first), and its
      Mensajes table gains a `Conversación` link column. RED observed (link absent,
      `messages_limit=10` missing), then GREEN. Commit `1047e0e1`.
- [x] **T7c + T8 (fe)** — `getConversation(id, messagesLimit?)`; the thread requests
      the last 10 and expands through `retry()`; `ConversationThread` and its fixtures
      gain `messages_total`; a `ManyMessages` story shows the disclosure. RED observed
      (initial call missing `messages_limit=10`), then GREEN. Commit `cdddc9db`.
- [x] S2 verification of record: `uv run pytest tests/` → **1479 passed**;
      `cd web && npm run test` → **89 files / 769 tests**; `npx tsc -b --noEmit` →
      exit 0; `npm run build` → exit 0 (pre-existing >500 kB chunk warning).
- [x] S2 code size `4a395f3e..HEAD`: **290 changed lines** (255 added, 35 deleted)
      across `app/ tests/ web/` — under the ~400 review-focus budget.
- [x] Unit code size `cf5f8171..HEAD`: **768 changed lines** (594 added, 174 deleted).
      Delivery: `stacked-to-main`, PR 1 = S1 (~482, over budget by owner choice),
      PR 2 = S2 (~290).

Design note for the wiring: `useAsyncData` refetches only on `attempt`,
`enabled` or `refreshKey` changes (it reads the fetcher through a ref), so the
expand/collapse toggle must drive the refresh through the refresh key or an
explicit `retry()` **after** the state commit — never by calling a memoised
fetch closure captured in the current render.

## Acceptance criteria

1. The ficha shows the active case with working status, responsible and emergency
   acknowledge actions; closing it removes it from the block and the open list
   (U1 invariant already guarantees the last part).
2. The ficha's `<ol>` visit trail is gone and `visit_history` is no longer in the
   payload.
3. No raw backend identifier and no consumer of the removed field remain.
4. `CaseActions` has a single implementation used by both `CasesList` and the
   ficha.
5. Messages in both surfaces are bounded by a real backend limit and expand to
   the full set on demand (S2).
6. Only the authorized files change.
7. `uv run pytest tests/`, `cd web && npm run test`,
   `cd web && npx tsc -b --noEmit` and `cd web && npm run build` pass.

## Checks

- `eval "$(./infra/test-db.sh env)" && uv run pytest tests/`
- `cd web && npm run test`
- `cd web && npx tsc -b --noEmit`
- `cd web && npm run build`
- `git diff --check`

## Progress

- [x] Worktree created (`rapso worktree create client-ficha-case-surface --yes`),
      provisioned (`uv sync`, `npm ci`), test DB up on `:5650`.
- [x] Baseline on the untouched worktree: `uv run pytest tests/` → **1476
      passed** (172.61s); `cd web && npm run test` → **87 files, 750 tests, all
      passing**.
- [x] Graph Check (Step 1) for the ficha/case area at plan time:
      `graphify query "ClientFicha panel client ficha case surface"`. Nodes
      consulted: `ClientFicha()` (`web/src/components/pages/ClientFicha.tsx:67`),
      `Case` (`app/models.py:334`), `serializers.py`, `customers.py`,
      `services/cases.py`, `apiFetch()`, `useAsyncData()`, `AppShell.tsx`.
      Communities: `ClientFicha.tsx`, `Customer`, `get_or_create_customer`,
      `serializers.py`. Note: `graphify-out/graph.json` was built 09:38, before
      the 09:52 `set_case_status` rename on main; the rename is public-only and
      does not touch the files this unit reads.
- [x] T1 — backend payload: `case_is_open()` added next to `case_is_open_expr()`
      (`app/services/cases.py:41`); `customer_history` cases carry the full field set
      + `is_open` (`app/services/customers.py:282-297`); `GET /clients/{id}` returns
      `users` (`app/panel/api/routes/clients.py:131-138`). RED observed (missing
      `users`; missing extended keys; `KeyError: 'is_open'`), then GREEN. Commit
      `6eb21ace`. Parent correction: `summary` had been dropped from the case dict and
      was restored (ClientFicha renders it); the local `customers -> cases` import is
      documented — a top-level import cycles through `app.chat.state`.
- [x] T2 — trail removal, two commits. **T2a** backend: `visit_history` removed from
      `customer_history`; the functional test now asserts the appointment survives and
      the field is gone. RED observed, then GREEN. Commit `4a9f3fb2`. **T2b**
      frontend: the `<ol>`, the `visitHistory` variable, the `VisitHistoryEvent` type
      and the story fixture removed. RED observed (`<ol aria-label="Ciclo de vida de
      visitas">` still present), then GREEN; `tsc -b --noEmit` exit 0. Commit
      `f8e2ea2a`.
- [x] T3 — `CaseActions` promoted to `web/src/components/shared/CaseActions.tsx`
      with the minimal `CaseActionTarget` (no `customer` requirement) and
      `CASE_STATUSES`; `CasesList` consumes it. RED observed (module not resolvable),
      then GREEN. Commit `871e54a6`.
- [x] T4 + T5 — "Caso activo" block as the first child of `.detail-region__main`,
      wired to the shared `CaseActions` with `updateCase`/`acknowledgeCase` posting to
      `/cases/{id}/update` and `/ack` and refetching the ficha; local error feedback
      via the existing `LocalFeedback` (not `CasesList`'s unhandled rejection). The
      Casos table is the archive (`archivedCases`, heading "Casos anteriores"). Types
      and the story matrix (incl. an unanswered emergency) updated. RED observed,
      then GREEN. Commit `4a395f3e`.
- [x] S1 verification of record: `uv run pytest tests/` → **1477 passed**;
      `cd web && npm run test` → **88 files / 759 tests**; `npx tsc -b --noEmit` →
      exit 0; `npm run build` → exit 0 (pre-existing >500 kB chunk warning).
- [x] S1 code size `cf5f8171..HEAD`: **482 changed lines** (341 added, 141 deleted)
      across `app/ tests/ web/`. Over the ~400 review-focus heuristic; the
      `ask-on-risk` strategy applies before S2. Owner decision requested.
- [ ] T6 …

## Recovery

- Worktree: `/home/stefan/repos/lumat-agent-odd-client-ficha-case-surface`,
  branch `odd/client-ficha-case-surface`, base `cf5f8171`.
- Test DB: `./infra/test-db.sh up|down|env`, project
  `lumat-test-lumat-agent-odd-client-ficha-case-surface`, port `5650`.
- Dev server (if needed): `cd web && npm run dev -- --host 127.0.0.1 --port 5177`
  with `VITE_API_TARGET` pointed at the running API.
- On resume: read this file and reconcile the checkbox state against `git log`
  before continuing.
- Session of record:
  `.rapsodia-code/sessions/ready-for-odd/2026-09-25-clientes-crm/`.
