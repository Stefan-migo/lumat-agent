# ODD Task: agenda-manual-case

Status: complete (pending owner push/PR)
Worktree: `../lumat-agent-odd-agenda-manual-case`
Branch: `odd/agenda-manual-case`
Depends on: `agenda-crud-contract` (PR #361, merged `9cf2bf6a`)

## Objective

Allow a `Case` to exist without a `Conversation`, so the operator can create a case
from the Agenda. This is the schema foundation that unblocks U4
(`agenda-visit-dialog`): without it there is no way to create a visit for a walk-in
customer.

## Problem

`Case.conversation_id` is `NOT NULL` (`app/models.py:342-344`). The only two creators
are conversation-bound:

- `get_or_create_case(session, conversation_id, customer_id)` — `app/services/cases.py:34`
- `create_handoff_case(session, state, ...)` — `app/services/cases.py:97` (needs a `ConversationState`)

`app/panel/api/routes/cases.py` exposes only `GET /cases`, `POST /cases/{id}/update`
and `POST /cases/{id}/ack`. There is no `POST /cases`.

Consequence: a counter-born case cannot exist, and `Case.service` being nullable
(`app/models.py:350`) is the reason the Agenda's "Caso" field breaks visit creation.

## Why (approved decisions)

- **D1**: the visit stays tied to a chatbot `Case`; the Agenda gains the ability to
  create a case. Traceability `conversación → caso → cita` is preserved.
- **D2 (option a2)**: `Case.conversation_id` becomes **NULLABLE**. A case may or may
  not originate from a conversation. A synthetic "mostrador" conversation would lie in
  the data and pollute the inbox.

## Scope

Backend/data plus the minimal web type. **No UI wiring** — no dialog redesign, no
`Combobox` extension (that is U4).

## Constraints

- Work is born in this worktree on `odd/agenda-manual-case`; never touch `main`.
- **Strict TDD is ON** (`openspec/config.yaml:38`). RED → GREEN → REFACTOR, no exceptions.
- Runner: `uv run pytest tests/`. Web: `cd web && npm test`. Type check is only
  `cd web && npm run build` (`tsc -b`). No linter, no formatter.
- `Appointment.case_id` is `NOT NULL` (`app/models.py:606`) and `Appointment.service`
  is `NOT NULL` (`app/models.py:604`): the visit still needs a case and a service even
  when that case has no conversation.
- `Case.service` is nullable (`app/models.py:350`).
- Migration numbering: next free number is **032**; convention `db/migrations/NNN_name.sql`.
- Tests need the per-worktree database: `eval "$(infra/test-db.sh env)"` before any
  pytest run. Without it `db/migrate.sh` connects as the `app` role and fails with
  `permission denied to alter role` — environmental, not a code failure.

## Blast radius — the five consumers that assume non-null

1. `app/panel/api/routes/conversations.py:109-147` — `partition_by=Case.conversation_id`
   and `_selected_case` choose the thread's case.
2. `app/services/notify.py:300` (`Case.conversation_id == conversation_id`) and `:380`
   (`session.get(Conversation, case.conversation_id)`).
3. `app/services/tukulpan.py:960`.
4. `app/panel/api/serializers.py:155` — `to_case_dict`.
5. `web/src/types.ts` — the `Case` type.

## Work units

### WU1 — Nullable `conversation_id` (schema + model)

- [x] `db/migrations/032_case_conversation_nullable.sql`: `ALTER TABLE cases ALTER COLUMN conversation_id DROP NOT NULL;`
- [x] `app/models.py:342` → `conversation_id: Mapped[int | None]`, `nullable=True`
- [x] RED: `tests/integration/test_migrations.py` — `test_cases_conversation_id_is_nullable`
- [x] Applied-migration list in `test_schema_migrations_records_version` includes `032_case_conversation_nullable`
- **Verify**: `uv run pytest tests/integration/test_migrations.py` — passed
- **Note**: the first attempt (`246fbe3c`) landed the model edit on
  `Message.conversation_id` instead of `Case.conversation_id`, and left the applied-migration
  list red. Corrected in `cd33edc3`.

### WU2 — Consumers tolerate `None`

- [x] `conversations.py:109-147` — structurally safe: a NULL `conversation_id` forms its own
  partition and the `ranked.conversation_id == Conversation.id` join predicate never matches it.
  Pinned by `test_conversations_queue_does_not_assign_manual_case`.
- [x] `notify.py:300` — `Case.conversation_id == conversation_id` never matches NULL.
  Pinned by `test_ack_does_not_select_manual_emergency_case`.
- [x] `notify.py:380` — added the `is not None` guard around `session.get(Conversation, ...)`;
  the bare call returns `None` today but SQLAlchemy warns it may raise on a future release.
  Pinned by `test_reminder_tolerates_manual_case_without_conversation`.
- [x] `tukulpan.py:960` — structurally immune (`Case.conversation_id == conversation.id`);
  no test written, a direct call would only restate the SQL filter.
- [x] `serializers.py:155` — `to_case_dict` passes `None` through; already asserted by the
  `POST /cases` test (`conversation_id is None`).
- [x] `web/src/types.ts` — `Case.conversation_id: number | null` was already correct.
- **Verify**: full backend suite — passed

### WU3 — New `POST /cases`

- [x] `app/services/cases.py`: `create_manual_case(session, customer_id, service, *, summary=None)`
      (bare row shape, `conversation_id=None`, publishes `case.created`)
- [x] `app/panel/api/routes/cases.py`: `POST /cases` (operator auth, body
      `{customer_id, service, summary?}`, 404 on unknown customer, returns `{"ok", "case"}`)
- [x] RED → GREEN: `test_manual_case_creation_returns_and_lists_open_case`
- **Verify**: full backend suite — passed

### WU4 — Regression and build

- [x] Existing visit creation still works (whole suite green, appointments untouched)
- [x] `uv run pytest tests/` — **1476 passed in 161.94s** (after the rebase onto `main`)
- [x] `cd web && npm run build` — ✓ built in 5.51s
- [x] Work-unit commits (see below)

## Acceptance criteria

- [x] The migration makes `cases.conversation_id` nullable.
- [x] The five consumers tolerate null without breaking.
- [x] `POST /cases` creates a case with `conversation_id null`, and it appears in
      `list_open_cases`. A `status=None` manual case counts as open under
      `case_is_open_expr()` (`case-closure-fix`, #365).
- [x] Existing visit creation still works.
- [x] Backend tests green; web build green.

## Verification (observed)

- `uv run pytest tests/ -o addopts='' -q` → `1476 passed in 161.94s (0:02:41)` (rebased branch)
- `cd web && npm run build` → `✓ built in 5.51s` (only the pre-existing chunk-size advisory)
- Before the rebase onto `main` (`33f1feba`): `1464 passed in 143.69s`, web `5.28s`
- Commits (rebased): `64c75566` (Case nullable + migration list), `e297a25f` (lock sync),
  `edcc1ebb` (consumers + regression pins), `ccb299b6` (POST /cases)

## Findings / follow-ups

- `session.get(Conversation, None)` emits `SAWarning: fully NULL primary key identity
  cannot load any object. This condition may raise an error in a future release` — guarded.
- The reminder sweep will send for any emergency case with `notified_at` set, including a
  manually created one. `create_manual_case` never sets `notified_at`, so this is not
  API-reachable today; the test pins characterization, not a product decision.
- Rebased onto `main` (`33f1feba`) before the PR — the branch was 25 commits behind. `main`
  added no migrations (still `031`), so `032` does not collide.
- `main`'s `case-closure-fix` (#365) changed `list_open_cases` from `closed_at IS NULL` to
  `case_is_open_expr()` (status-based) and touched `app/services/cases.py` and
  `tests/functional/test_api_cases.py`. The conflict was resolved keeping both test groups;
  the manual case is created with `status=None`, which the new predicate treats as open, so it
  still lists. Re-verified after the rebase: 1476 passed.
- `POST /cases` does not reject an empty `service`; not required by the acceptance criteria
  (`R3-001`, non-blocking advisory).

## Native review receipt

- Transaction `review-b5b759d414d48b77` — four lenses (`review-risk`, `review-resilience`,
  `review-readability`, `review-reliability`), risk `high`, 11 paths / 318 lines.
- Result **`approved`**; the only finding is the non-blocking advisory `R3-001` above.
  Authority burned via `gentle-ai review acknowledge-approved` (`action: acknowledged`).
- **Scope, stated honestly**: the receipt is bound to the **pre-rebase** candidate trees
  (base `f62b80c3`). The branch was then rebased onto `main` (`33f1feba`) to open the PR, so
  the reviewed authored delta is preserved but its tree binding no longer matches the rebased
  commits. `main`'s changes came in underneath it; the conflict resolution above is the only
  authored delta introduced after the receipt.

## Graph nodes consulted

- Nodes: `Case` (`app/models.py` L334), `Message` (L279), `Conversation` (L253),
  `models.py`, `services/cases.py`, `routes/cases.py`, `routes/conversations.py`,
  `serializers.py`, `notify.py`, `tukulpan.py`, `types.ts`, `api.ts`, `scheduling.py`,
  `Customer`, `test_api_conversations.py`, `test_emergency_notify.py`.
- Edges: `Case → Conversation` (FK), `Case → Customer` (FK), `Appointment → Case` (FK),
  `Message → Conversation` (FK).
- `graphify query` over the Case/cases area was run before the fix; the graph was built
  from `8e25037c`. The backend Case/cases area is unchanged since, so the map holds.
  Refresh at session close.

## Progress

- [x] WU1 done — `64c75566`
- [x] WU2 done — `edcc1ebb`
- [x] WU3 done — `ccb299b6`
- [x] WU4 done — suite 1476 passed, web build green
- [x] Rebased onto `main` (`33f1feba`)
- [ ] Owner decision: push and open the PR
