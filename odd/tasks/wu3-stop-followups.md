# wu3-stop-followups

## Objective

Close the two non-blocking WARNING follow-ups of A6 WU3 (cooperative stop) so the
cooperative stop is never lost silently and never lets a cancelled `approval_pending`
approval execute a tool afterward. Backend only.

## Problem

A6 WU3 shipped cooperative stop. An independent verifier flagged two races:

1. **Stop can be lost (terminal commit race).** The runner's terminal write
   (`app/services/agent_chat.py:_run_agent_turn_session`, the success merge at ~L451-468)
   unconditionally overwrites `assistant_state`. A `stop_request` written after the last
   `on_stage` boundary check but before the terminal commit is clobbered: the stop route
   answered `{"status":"stopping"}` but the run ends `completed`.
2. **`approval_pending` stop is not atomic with approval consume.** `stop_thread_run`
   (`app/panel/api/routes/chat.py:357-383`) settles `cancelled` but leaves
   `approval.status = "pending"`. The approval path (`approve_plan`,
   `app/services/agent_chat.py:749-759`) still matches its `#>> '{approval,status}' = 'pending'`
   guard and executes the tool after the cancellation was recorded.

## Why

The owner confirmed the stop intent must be honored or rejected honestly, never lost
silently, and a cancelled run must not run its pending tool. These are correctness fixes
to already-shipped behavior.

## Scope

**In:** `app/services/agent_chat.py`, `app/panel/api/routes/chat.py`, and their tests
(`tests/integration/test_assistant_chat.py` primary; unit tests only if needed).

**Out:** no migration (all state is `assistant_state` JSONB), no frontend changes, no new
endpoint, no behavioral change for non-stop paths.

## Decisions (closed)

- F1 fix: immediately before the terminal success merge, re-read the thread's
  `assistant_state.stop_request` under the row lock (`SELECT ... FOR UPDATE`) and, if it
  matches `run_id`, raise `_StopRequested` so the existing catch branch (L501-520) settles
  `cancelled`. Outcome: honored, or the stop route sees a terminal `live.status` and answers
  `409 not active` — never silently lost.
- F2 fix: when `stop_thread_run` settles `cancelled` for an `approval_pending` run, revoke
  the pending approval in the same locked transaction (`approval.status = "revoked"`, only
  when it is `pending`). Additionally make `approve_plan` refuse a run whose
  `live.status`/`stage` is already terminal (`cancelled`).
- No new dependency, no signature change to public service functions.

## Work units (stable IDs)

### F1 — Terminal-stop race
- [x] RED: a test in `tests/integration/test_assistant_chat.py` where `run_assistant` (monkeypatched)
      writes `stop_request` **after** the last `on_stage` boundary (no further boundary call),
      then the run completes. Today the outcome is `completed`; the test must assert `cancelled`.
- [x] GREEN: re-check `stop_request` under the thread row lock right before the terminal merge.
- [x] Ensure no regression: existing `test_runner_cooperatively_cancels_at_graph_stage_boundary` stays green.

### F2 — `approval_pending` stop atomicity
- [x] RED: a test that sets an `approval_pending` run with a valid pending approval, calls the
      stop route (→ `cancelled`), then calls the approval route with the same token/run_id and
      asserts it is refused (409) and the tool does NOT execute; assert `approval.status == "revoked"`.
- [x] GREEN: revoke the pending approval in the stop branch; make `approve_plan` refuse a terminal run.
- [x] Ensure no regression: existing `test_stop_route_accepts_approval_pending_as_running` stays green.

## Acceptance criteria

1. Both new tests fail before their fix (observed RED) and pass after (observed GREEN).
2. Full backend suite green: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/`.
3. No frontend files touched; no migration; conventional commits; no AI attribution.

## Checks

- Backend: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/` from the worktree root.
- Targeted first: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/integration/test_assistant_chat.py -q`.
- Graph Check done: nodes `_run_agent_turn_session`, `run_agent_turn`, `_publish_stage_or_stop`,
  `approve_plan` (`app/services/agent_chat.py`); `stop_thread_run`, `approve_thread_plan`,
  `StopBody` (`app/panel/api/routes/chat.py`); `merge_assistant_state` (`app/chat/assistant/state.py`);
  `issue_approval`/`validate_approval`/`consume_approval` (`app/chat/assistant/approval.py`).
- RDD: `review assess` per work-unit commit; run the returned transition verbatim when `review_due`.

## Env / setup

- Worktree `../lumat-agent-odd-wu3-stop-followups`, branch `odd/wu3-stop-followups`, from `main` = `54fb4527`.
- `uv sync --frozen`; `cp <primary>/infra/.env infra/.env`; `bash infra/test-db.sh up`; tests need
  `eval "$(bash infra/test-db.sh env)"` first. Frontend untouched → no `npm ci` needed.

## Progress log

- Worktree created from `main` = `54fb4527`. Baseline `uv run pytest tests/integration/test_assistant_chat.py -q` → 62 passed.
- F1 — `9615dadf`: terminal stop race test observed RED (`completed` instead of `cancelled`), then GREEN; terminal-stop test and existing stage-boundary cancellation test → 2 passed.
- F2 — `918f587b`: approval stop test observed RED (`pending` instead of `revoked`), then GREEN; approval stop and existing approval-pending stop test → 2 passed.
- Verification (2026-10-10). Targeted `tests/integration/test_assistant_chat.py` → 64 passed. Full backend
  `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/` → **1873 passed, 2 warnings** (pre-existing:
  unawaited `_publish_all` coroutine + fastembed pooling). Parent spot check re-ran the targeted file → 64 passed.
- RDD: native immutable review transport **unavailable for OpenCode** (`review status` →
  `immutable_review_transport_unsupported`, `next_action: stop`; `review assess --base-ref 54fb4527
  --committed-only` → `high` / `unassessable`). Same runtime condition the A6 WU3 handoff recorded, not a code
  defect. Applied the RDD-off fallback: writer self-verification + **one independent verifier** →
  **PASS-WITH-WARNINGS, 0 blockers**. Advisory (no correction): (a) the F1 test does not assert
  `active_run_id` / sibling-key preservation; (b) F2 cannot undo a tool execution already committed if an
  approval won the race first (inherent honest limitation).
- Docs commit `93a1718a` (`docs(odd): track wu3-stop-followups`). Branch `odd/wu3-stop-followups`; not pushed.
