# Apply Progress: Panel Assistant Cost Gate

## Status

- Phase 1 (PR 1) tasks 1.1–1.4 and Phase 2 (PR 2) tasks 2.1–2.3 complete.
- Mode: Strict TDD.
- Delivery: chained PR slice, final PR 4 boundary.
- Changed lines in this PR 4 slice: 132 authored lines (127 additions, 5 deletions), below the 400-line review budget and 400-line attempt budget.

## Completed Work

- 1.1 RED: added migration-version, nullable-column, and app-grant assertions.
- 1.2 GREEN: added migration 023 and `InternalChatMessage.cost_llm` mapping.
- 1.3 RED: added internal-thread, combined UTC-day, explicit/idempotent pricing, unknown-model diagnostic, and WhatsApp regression coverage.
- 1.4 GREEN: generalized cost recording and aggregation; added configurable rates, exact-once internal call keys, and zero-cost diagnostics while retaining WhatsApp sums and audit alert dedupe.
- 2.1 RED: added blocked no-LLM persistence, conservative-mode, gate, and operator panel-access tests.
- 2.2 GREEN: added typed cost mode/directive state, inserted `panel_cost_gate` after context assembly, and short-circuited blocked requests before planning; conservative directives apply to planner and response prompts.
- 2.3 GREEN: retained the Phase 1 settings-KV `cost.llm_rates` defaults with documented source/effective date; gate reads the one-thread internal scope and global UTC-day scope.
- 3.1 RED: added planner/terminal usage, missing-usage, disconnect, concurrent call-key, and persisted reconnect-authority tests.
- 3.2 GREEN: passed request message IDs through the assistant graph, recorded planner and terminal stream usage with recovery-safe keys, preserved diagnostics on failure, and refreshed locked rows before idempotency checks.
- 4.1 RED: added non-regression coverage for rejected approvals, alert scopes, normal planner flow, blocked recovery persistence, and WhatsApp-row isolation; the first focused run exposed and then corrected an incomplete audit-session test double.
- 4.2 GREEN: no production changes were required; approval lifecycle and WhatsApp behavior remain untouched.

## TDD Cycle Evidence

| Task | RED | GREEN | REFACTOR |
|---|---|---|---|
| 1.1 | Migration tests failed before 023 existed (missing version/column). | Migration and grant tests pass. | N/A; retained existing migration runner convention. |
| 1.2 | Same migration/type failures. | Focused migration tests pass. | `git diff --check` passes. |
| 1.3 | Cost tests failed before internal model/service support. | Focused guardrail tests pass. | Added shared seed helper and reset internal tables per test. |
| 1.4 | Same guardrail failures. | 41 focused tests pass; full suite passes. | Preserved legacy positional `Message` recorder API and alert path. |
| 2.1 | New assistant gate tests failed at collection because `panel_cost_gate` did not exist. | Focused assistant tests pass. | Kept operator authorization unchanged; asserted panel session access remains available. |
| 2.2 | Same missing-node/behavior failures. | Focused assistant tests pass; blocked API path persists the canned reply with zero LLM calls. | Reused existing graph evidence and `agent_chat.py` persistence/realtime path. |
| 2.3 | Phase 1 already supplied the required settings defaults and scope semantics. | Existing settings/cost tests plus full suite pass. | No duplicate pricing abstraction or new settings table. |
| 3.1 | New usage/recovery tests failed before request-ID accounting existed. | Focused PR 3 tests pass. | Concurrent retry test exposed stale SQLAlchemy identity-map state under `FOR UPDATE`. |
| 3.2 | Same usage/recovery failures. | Focused tests and full suite pass. | Flush each accounting update before the next locked call-key check; preserve existing WhatsApp recorder API. |
| 4.1 | New regression tests were written before implementation; initial runs exposed incomplete test doubles/JSON mutation setup, then fixtures were corrected. | 40 focused tests pass. | Tests reuse existing approval, gate, persistence, and message seams; no production code added. |
| 4.2 | Same regression tests were the acceptance set. | Full suite passes: 706 passed, 1 existing RuntimeWarning. | Verified no approval or WhatsApp production files changed. |

## Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command | `... uv run pytest tests/integration/test_cost_guardrails.py tests/integration/test_assistant_chat.py tests/integration/test_assistant_harness_session.py` — 53 passed. |
| Runtime harness | Same command exercised PostgreSQL-backed panel POST, planner/stream provider usage, disconnect persistence, concurrent retry locking, and reconnect event replay. |
| Full suite | `... uv run pytest tests/` — 700 passed, 1 RuntimeWarning (existing webhook async cleanup warning). |
| Rollback boundary | Revert `app/chat/assistant/state.py`, `app/chat/assistant/graph.py`, `app/chat/assistant/nodes.py`, `app/services/agent_chat.py`, `app/services/costs.py`, and the three PR 3 test files; leave Phase 1–2 behavior and Phase 4 untouched. |

For PR 4 specifically, rollback only the four modified test files; no production behavior is removed.

## Ponytail Review

- Reused the existing cost service, settings KV, JSON metadata, and audit dedupe; no ledger, synthetic WhatsApp rows, or new dependency added.
- Gate uses existing `internal_thread_cost_state`, `daily_cost_state`, and `maybe_alert_owner`; no new UI or operator lockout was introduced.
- `SELECT ... FOR UPDATE` must use `populate_existing=True`; otherwise SQLAlchemy can return a stale identity-map object and charge concurrent retries twice. A flush makes each committed call key visible before the next call in the same transaction.
- PR 4 cut all production scope: the regression work reuses existing seams and adds no abstraction, dependency, ledger, synthetic WhatsApp row, or approval change.

## Graph Check

Nodes consulted: `AssistantState`, `assistant/state.py`, `assistant/graph.py`, `nodes.py`, `assemble_context()`, `plan_llm()`, `execute()`, `internal_thread_cost_state()`, `daily_cost_state()`, `maybe_alert_owner()`, `record_llm_cost()`, `get_setting()`, `services/settings.py`, `agent_chat.py`, `stream_events()`, `recover_events()`, `claim_execution()`, `test_cost_guardrails.py`, `test_assistant_chat.py`, `test_assistant_harness_session.py`.

Edges consulted: `state.py` → `graph.py` → `nodes.py`; `assemble_context()` → `panel_cost_gate` → `plan_llm` → `guardrails` → `execute`; `agent_chat.py` → `run_assistant()` → `plan_llm()`/`execute()`; `agent_chat.py` → `stream_events()` → `recover_events()`; `resume_thread()` → `claim_execution()` → `execute()`; `nodes.py` → `record_llm_cost()` → `InternalChatMessage`; `costs.py` → `daily_spend()`/`maybe_alert_owner()` → `InternalChatMessage`.

## Final PR 4 Evidence

| Evidence | Exact result |
|---|---|
| Focused test command | `DATABASE_URL='postgresql+psycopg://app:app@localhost:5434/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5434/lumat' uv run pytest tests/integration/test_assistant_harness_guardrails.py tests/integration/test_assistant_harness_session.py tests/unit/test_assistant_planner.py tests/integration/test_assistant_chat.py` — **40 passed** in 27.86s. |
| Runtime harness | Same focused integration command exercised PostgreSQL-backed panel approval/rejection, persisted blocked/recovery state, alert selection, normal flow, and WhatsApp-row isolation. |
| Full suite | `DATABASE_URL='postgresql+psycopg://app:app@localhost:5434/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5434/lumat' uv run pytest tests/` — **706 passed, 1 existing RuntimeWarning** in 373.68s. |
| Rollback boundary | Revert only `tests/integration/test_assistant_chat.py`, `tests/integration/test_assistant_harness_guardrails.py`, `tests/integration/test_assistant_harness_session.py`, and `tests/unit/test_assistant_planner.py`. |

## Completion

All 11 tasks (1.1–4.2) are complete. No production files were changed in PR 4.
