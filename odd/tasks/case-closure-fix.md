# ODD — case-closure-fix

## Objective

Closing a case from the panel must actually close it: the case leaves the open-cases
list and the dashboard, and the close is recorded with a timestamp. One canonical
definition of "closed case" must serve every query in the codebase.

## Problem

Verified in code, not inferred:

- `app/services/cases.py:150-184` — `update_case()` sets `status` and `responsible_id`
  and **never touches `closed_at`**.
- `app/services/cases.py:136` — `list_open_cases()` (which feeds `GET /panel/api/cases`)
  filters on `Case.closed_at.is_(None)`, **not** on status.
- `app/services/dashboard.py:119` — the urgent-cases query uses the same
  `Case.closed_at.is_(None)` filter.
- `app/panel/api/routes/conversations.py:91` — a third, status-based definition:
  `_CLOSED_CASE_STATUSES = ("closed", "cerrado", "finalizado", "cancelado")`, used only
  to rank which case a conversation shows.
- `rg closed_at app/` returns **no assignment** anywhere. The column is read, serialized
  and exported; it is never written.

Consequence: an operator sets a case to "Cerrado" (the frontend offers it,
`CasesList.tsx:24`, and paints it green, `toneMaps.ts:4`), and the case stays in
`GET /cases` and in the dashboard forever.

The existing test `tests/functional/test_api_cases.py:161-186`
(`test_cases_list_skips_closed_cases`) proves the *filter* works by setting `closed_at`
**directly in the database**. Nothing proves the *API* can produce that state. That gap
is the whole unit.

### Newly reachable re-escalation defect

The original fix made a previously unreachable defect reachable: after an operator closes
a case, the conversation can escalate again. `create_handoff_case()` calls
`get_or_create_case()`, which returns the latest case without filtering out closed rows;
handoff then sets its status to `escalado` without clearing `closed_at`. With a timestamp-gated
open predicate, that live re-escalated case remains hidden from the panel. The shared status
transition helper must cover both `update_case()` and `create_handoff_case()`.

Measured baseline (dev DB `infra-db-1`, 2026-09-25): 3 cases, all `status='abierto'`,
all `closed_at IS NULL`. **No legacy rows with a closing status and a NULL `closed_at`
exist in dev.** Production was not inspected.

### Incomplete centralization (post-review finding)

The invariant "`closed_at` is consistent with the status" was centralized in 2 of its 4
write sites. Two production paths still write `Case.status` directly:

- `app/chat/nodes/classify_intent.py:108` — `_store_classification()` assigns
  `case.status = result.get("status")` on every classified message (called at line 204).
- `app/chat/nodes/emergency.py:83` — the emergency node assigns `case.status = "escalado"`.

`get_or_create_case()` returns the conversation's latest case without filtering by status,
so both paths reach a case the operator already closed. Consequence: a closed case
(`status='cerrado'`, `closed_at=T`) plus one substantive inbound message re-activates the
status to `abierto`/`escalado` while `closed_at` keeps `T`. The D1 sentence claiming our own
code cannot produce that shape is false. Effects: the CSV export reports a close time for an
open case, and re-closing keeps the stale time (`_apply_status` only stamps when
`closed_at is None`). Under a `closed_at`-gated predicate the case would stay invisible — the
same defect T7 fixed in handoff, still live.

Note: `closure_gate.py` is the chat farewell gate and writes no case status; a bare
"gracias" never reaches classification. Re-activation requires a substantive message, which
matches the pre-unit behaviour of the conversation manager.

### Decision (D2) — status stays the gate, and AD-HOY-1 is amended

Owner decision (a): the status remains the source of truth and the live requirement
`AD-HOY-1` is amended to define urgent as "the case is still open", instead of naming the
`closed_at` column. Rationale: under a status gate a missed writer costs a stale timestamp;
under a `closed_at` gate a missed writer loses the case from operations entirely. This unit
already found 2 of 4 writers bypassing the invariant, so the graceful-degradation mode is the
safe one. The amendment ships as an OpenSpec change alongside its consumer.

## Why

The panel gives the operator a control whose effect is a lie. Beyond the panel, the same
defect pollutes the dashboard's urgent cases, and the three competing definitions mean
the next change to "closed" will silently desync one of them — which is exactly how this
bug was born.

## Scope (authorized by the owner)

**In:**

- `app/services/cases.py` — the canonical closing-status set, the canonical open-case
  predicate, `update_case` stamping/clearing `closed_at`, and `list_open_cases` using the
  canonical predicate.
- `app/services/dashboard.py` — the urgent-cases filter uses the canonical predicate.
- `app/panel/api/routes/conversations.py` — the local `_CLOSED_CASE_STATUSES` tuple is
  deleted; the ranking uses the canonical predicate.
- `tests/functional/test_api_cases.py` — RED first, plus the dashboard/ranking coverage
  the predicate now needs.

**Out:**

- **No migration and no backfill.** See D1.
- No frontend change. The UI already offers "Cerrado"; nothing on the web side moves.
- No new statuses. The closing set is exactly the four values already in use.
- No change to the audit snapshot shape (`{"status", "responsible_id"}`): existing tests
  pin it exactly (`test_api_cases.py:265-266`).
- `app/services/tukulpan.py:967-977` (`_fires_oportunidad`, keyed on `case.status is None`)
  is not a closure query and is not touched.
- `app/panel/routes/export.py` only reads `closed_at` for the CSV; no change.

## Decision (D1) — where the truth lives

**The case status is the source of truth for closure; `closed_at` is the recorded
timestamp of that transition.**

Rationale: nothing in the codebase writes `closed_at` today, so the status is already the
de facto truth — an operator's "Cerrado" is a status change, not a timestamp. Making the
status canonical means legacy rows (closing status, `closed_at` NULL) are handled with no
migration and **no fabricated timestamp**. `update_case` then stamps `closed_at` when the
status enters the closing set and clears it when the status leaves, so the column becomes
real without ever becoming the gate.

Consequence accepted: a contradictory row (`closed_at` set, status not closing) is treated
as **open**. After the corrective unit (D2/T8) every `Case.status` writer goes through the
shared helper, so our own code cannot produce that shape; before T8 it could, through
`classify_intent` and `emergency`. No production row has `closed_at` set at all today.

## Constraints

- **Strict TDD ON.** Runner: `eval "$(infra/test-db.sh env)" && uv run pytest tests/`. RED must be observed before GREEN.
- **The predicate must be NULL-safe and status-only.** `Case.status` is nullable — `get_or_create_case`
  (`cases.py:34-51`) creates a bare case with no status until classification fills it. A
  bare `Case.status.not_in(CLOSING)` evaluates to SQL `NULL` for a NULL status and would
  silently **hide a brand-new open case**. Open must be expressed positively as
  `or_(status.is_(None), status.not_in(CLOSING))`; `closed_at` records transitions but is
  not a closure gate.
- `update_case`'s `status=None` contract means "keep": `closed_at` must not be touched
  when the body omits `status`.
- Re-stamping on a no-op is wrong: closing an already-closed case must not move its
  original close time. Stamp only when `closed_at is None`.
- Operator-facing copy in Spanish; code, identifiers, comments, tests and docs in English.
- Graph check before writing (see below).

## Graph check

`graphify query "case lifecycle close closed_at open cases list dashboard rank"` →
nodes consulted: `list_open_cases` / `Case.closed_at` (`app/services/cases.py`),
`Dashboard()` and the `urgent_cases` query (`app/services/dashboard.py`),
`routes/conversations.py` and its `_CLOSED_CASE_STATUSES`,
`closed_at set -> case excluded from the open list (HH-4)` —
`tests/functional/test_api_cases.py:162` (the graph surfaced the exact test that hides
this gap), `Case` (`app/models.py:334`), communities `test_api_cases.py`,
`cases.py`, `routes/conversations.py`, `Dashboard.tsx`.

## Expected fix shape

```python
# app/services/cases.py
CLOSING_CASE_STATUSES = frozenset({"closed", "cerrado", "finalizado", "cancelado"})

def case_is_open_expr():
    """Canonical 'this case is still open' predicate (NULL-safe)."""
    return or_(Case.status.is_(None), Case.status.not_in(CLOSING_CASE_STATUSES))

def _apply_status(case: Case, status: str) -> None:
    was_closing = case.status in CLOSING_CASE_STATUSES
    is_closing = status in CLOSING_CASE_STATUSES
    case.status = status
    if is_closing and not was_closing and case.closed_at is None:
        case.closed_at = datetime.now(timezone.utc)
    elif not is_closing:
        case.closed_at = None
```

Call `_apply_status()` from both `update_case()` (only when status is provided) and
`create_handoff_case()`. `list_open_cases`, the dashboard filter and the conversation ranking
all call `case_is_open_expr()`; `conversations.py` no longer defines a local closing set.

**Flagged behavior change for the writer to confirm, not assume:** the ranking's current
expression treats a NULL-status case as *not* priority-1 (the `NOT IN` yields NULL and the
`CASE WHEN` falls through). The canonical predicate treats it as open, so it becomes
priority-1. That is the correct reading of a brand-new case, but it is a change — the full
suite decides whether anything else depended on the old rank.

## Tasks

| ID | Task | Route |
|----|------|-------|
| T1 | RED: `POST /cases/{id}/update {"status":"cerrado"}` must stamp `closed_at` and drop the case from `GET /cases`. Must fail against today's code. | delegated (writer) |
| T2 | RED: reopening (`status` back to a non-closing value) clears `closed_at` and the case returns to `GET /cases`. | delegated (writer, same unit as T1) |
| T3 | GREEN: canonical set + predicate; `update_case` stamp/clear; `list_open_cases` and the dashboard filter call the predicate. | delegated (writer, same unit as T1) |
| T4 | RED+GREEN: a closed case is excluded from the dashboard's urgent cases. | delegated (writer) |
| T5 | GREEN: `conversations.py` drops its local tuple and ranks with the canonical predicate; full suite confirms no regression. | delegated (writer) |
| T6 | Full suite `eval "$(infra/test-db.sh env)" && uv run pytest tests/`. | delegated per-action |
| T7 | RED+GREEN: re-escalating a previously closed case reopens it; share the status transition helper with `create_handoff_case`, and make the open predicate status-only per D1. | corrective (writer) |
| T8 | RED+GREEN: route `classify_intent._store_classification` and `emergency.emergency` through `_apply_status`, so a re-activated closed case clears `closed_at` on both paths. | delegated (writer) |
| T9 | OpenSpec change `case-closure-open-status`: amend live `AD-HOY-1` so urgent means "the case is still open" by status (D2); ship with its consumer. | delegated (writer, same unit as T8) |

## Delivery

Backend-only, three source files plus tests, plus one OpenSpec change directory for the
`AD-HOY-1` amendment: well inside the ~400-line review budget → **single PR against `main`**,
label `type:bug`, no chained slices. Merge is the owner's decision.

## Progress / Evidence

- [x] T1 RED observed — `test_case_update_closes_case_and_removes_it_from_open_list` failed because `closed_at` remained `None` after setting status to `cerrado`.
- [x] T2 RED observed — added the missing assertion that the close request actually sets `closed_at`; the test then failed for the same reason. The initial T2 test design passed without exposing the bug and was corrected before implementation.
- [x] T3 GREEN observed — canonical predicate, timestamp transitions, and open-list/dashboard queries implemented; focused cases/dashboard/conversation tests passed.
- [x] T4 RED+GREEN — pre-implementation dashboard test failed because the canceled case remained urgent; the focused suite passed after implementation.
- [x] T5 ranking unified + full suite — conversation ranking now uses the canonical predicate; the full suite passed with no reported regression from NULL-status ranking behavior.
- [x] T6 suite green — `1464 passed, 2 warnings in 239.61s` after the re-escalation correction.
- [x] T7 RED+GREEN — the new service-path re-escalation test failed before the correction because `closed_at` remained set and the case was absent from the open list; both the re-escalation and status-only predicate tests pass after the correction.

### Evidence

The initial test DB setup was blocked until the owner supplied the worktree-local `infra/.env`; subsequent runs used the canonical test command in Constraints.

- Focused command: `uv run pytest tests/functional/test_api_cases.py::test_case_update_closes_case_and_removes_it_from_open_list -q` — ERROR at fixture setup, not a behavioral RED; `db/migrate.sh` could not connect to PostgreSQL at `127.0.0.1:6066`.
- `infra/test-db.sh up` could not start the worktree-isolated database because `infra/.env` is absent in this worktree. No environment file was copied from another worktree.
- RED: `eval "$(infra/test-db.sh env)" && uv run pytest tests/functional/test_api_cases.py::test_case_update_closes_case_and_removes_it_from_open_list tests/functional/test_api_cases.py::test_case_update_reopening_clears_close_time_and_restores_case -q` — `2 failed`, both at `assert _case_row(case_id).closed_at is not None` (`None is not None`).
- T4 RED: pre-implementation `test_closed_case_is_excluded_from_dashboard_urgent_cases` failed at the final exclusion assertion (`assert False`).
- GREEN: `eval "$(infra/test-db.sh env)" && uv run pytest tests/functional/test_api_cases.py tests/functional/test_api_dashboard.py tests/functional/test_api_conversations.py -q` — `60 passed`.
- Full suite: `eval "$(infra/test-db.sh env)" && uv run pytest tests/` — `1462 passed, 2 warnings in 227.37s`.
- T7 RED: `eval "$(infra/test-db.sh env)" && uv run pytest tests/functional/test_api_cases.py::test_reescalating_closed_case_restores_it_to_open_list tests/functional/test_api_cases.py::test_open_status_remains_listed_when_close_timestamp_is_set -q` — `2 failed`; first, re-escalation left `closed_at` non-null, and second, an open status with `closed_at` set was omitted from the list.
- T7 GREEN: `eval "$(infra/test-db.sh env)" && uv run pytest tests/functional/test_api_cases.py tests/functional/test_api_dashboard.py tests/functional/test_api_conversations.py tests/integration/test_handoff.py -q` — passed.
- Corrected full suite: `eval "$(infra/test-db.sh env)" && uv run pytest tests/` — `1464 passed, 2 warnings in 239.61s`.
- Corrective graph query surfaced `get_or_create_case()`, `Case`, the handoff path, and `test_api_cases.py`; requested `create_handoff_case` → `case_is_open_expr` path returned no predicate node in the existing graph.
- Graph check: queried the requested lifecycle area; the graph surfaced `list_open_cases`/`Case.closed_at`, `Dashboard()` urgent query, `routes/conversations.py`, `Case`, the existing closed-case test, and communities `test_api_cases.py`, `cases.py`, `routes/conversations.py`, `Dashboard.tsx`. Requested path `list_open_cases` → `update_case` returned no directed path.

### Corrective unit (a) — implemented and reviewed

- [x] T8 RED observed — both closed-case reactivation tests failed on stale non-null `closed_at` before implementation.
- [x] T8 GREEN — classification and emergency writers route through `_apply_status`; `None` status is accepted and treated as open.
- [x] T9 — the archived `case-closure-open-status` change contains the proposal, `advanced-dashboards` spec delta, and completed tasks; its `AD-HOY-1` delta is synced into the live spec.
- [x] Full suite green: `1466 passed, 2 warnings in 165.58s`.
- [x] Parent spot check (2 passed), then a new native review approved with zero findings; lineage `review-b2c7c2f6145c0c7b`.

#### Corrective unit evidence

- T8 RED command: `eval "$(infra/test-db.sh env)" && uv run pytest tests/integration/test_chat_intent.py::test_classification_reopens_closed_case_and_restores_it_to_open_list tests/integration/test_emergency.py::test_emergency_reopens_closed_case_and_restores_it_to_open_list -q` — `2 failed`. The classification and emergency tests each failed at `assert case.closed_at is None` because the seeded close timestamp remained set after status changed to `abierto` / `escalado`.
- T8 GREEN command: `eval "$(infra/test-db.sh env)" && uv run pytest tests/integration/test_chat_intent.py::test_classification_reopens_closed_case_and_restores_it_to_open_list tests/integration/test_emergency.py::test_emergency_reopens_closed_case_and_restores_it_to_open_list -q` — `2 passed`.
- Focused command: `eval "$(infra/test-db.sh env)" && uv run pytest tests/functional/test_api_cases.py tests/integration/test_emergency.py tests/integration/test_chat_intent.py -q` — `passed` (100%); captured output showed 74 test dots and no failure summary because the repository's pytest quiet setting suppresses it.
- Full command: `eval "$(infra/test-db.sh env)" && uv run pytest tests/` — `1466 passed, 2 warnings in 165.58s`. Warnings: an un-awaited `_publish_all` coroutine in `test_startup_sweep_reprocesses_received` and fastembed's model pooling notice in `test_project_slug_is_normalized_and_unique`.
- Final `rg -n "\.status\s*=" app/` audit: only `app/services/cases.py:45` assigns a `Case.status`. The two removed sites were `app/chat/nodes/classify_intent.py:108` and `app/chat/nodes/emergency.py:83`. Remaining assignments are to `Message` (`app/webhook/ingest.py`, `app/services/agent_chat.py`, `app/services/send.py`), `DomainEvent` (`app/ops/worker.py`), `Memory` (`app/services/tukulpan.py:630`), `Appointment` (`app/services/scheduling.py:108`), project records (`app/services/projects.py:244,308`), notification/operation/attempt records (`app/services/notifications.py`, `app/panel/api/routes/notifications.py`), and calendar sync records (`app/services/calendar.py`). Other matches are comparisons, not assignments.
- Graph check before implementation: queries surfaced `_store_classification()` (`app/chat/nodes/classify_intent.py`), `emergency()` (`app/chat/nodes/emergency.py`), `Case` (`app/models.py`), `cases.py`, `test_chat_intent.py`, `test_emergency.py`, `AD-HOY-1 Operational HOY Projection` (`openspec/specs/advanced-dashboards/spec.md`), and `today_projection()` (`app/services/dashboard.py`). Path `emergency()` → `Case` traversed `get_or_create_case()`; `AD-HOY-1` → `today_projection()` had no directed path, and graph extraction has no `_apply_status()` node (path attempt reported no matching node). The existing graph report's hubs include `chat/graph.py`, `models.py`, `services/dashboard.py`, `test_emergency.py`, and `test_api_cases.py`.
- `uv run ruff check ...` was attempted but could not run: `ruff` is not installed (`Failed to spawn: ruff`). `git diff --check` passed. No runtime harness was required: these integration tests execute the production graph and emergency node against the test database.

### Commits

- `73fbdaed test(cases): cover case closure lifecycle`
- `19d7134d fix(cases): synchronize status and closure timestamp`
- `82779d40 fix(cases): keep closure invariant on re-escalation`
- `f8d02c4c fix(cases): clear stale timestamp on open status`
- `1afcdb7e fix(cases): centralize all status transitions`
- `aa9adb7b docs(openspec): define urgent cases by open status`
- `586ad244 docs(odd): record case closure corrective evidence`
- `0a66a60c docs(openspec): archive case closure status delta`
- `6088ab89 docs(odd): record case closure delivery`
- `dbf48883 docs(odd): reconcile archived change status`

## Delivery outcome

Delivered in PR #365, merged as merge commit `33f1feba`. The OpenSpec change was archived and
the `AD-HOY-1` delta synced into the live specification.

Follow-up: the shared helper was renamed `_apply_status` → `set_case_status`, because it is
imported across `cases`, `classify_intent` and `emergency`, so a module-private name no longer
matched its role. The `_apply_status` references earlier in this document record the name as it
stood at the time; the archived OpenSpec artifacts keep theirs unchanged for the same reason.
