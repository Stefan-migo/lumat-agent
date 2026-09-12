# Apply Progress: Panel Assistant Cost Gate

## Status

- Phase 1 (PR 1) tasks 1.1–1.4 and Phase 2 (PR 2) tasks 2.1–2.3 complete.
- Mode: Strict TDD.
- Delivery: chained PR slice, PR 2 boundary only. Phases 3–4 remain pending.
- Changed lines in this PR 2 slice: approximately 203 authored lines, below the 500-line attempt budget.

## Completed Work

- 1.1 RED: added migration-version, nullable-column, and app-grant assertions.
- 1.2 GREEN: added migration 023 and `InternalChatMessage.cost_llm` mapping.
- 1.3 RED: added internal-thread, combined UTC-day, explicit/idempotent pricing, unknown-model diagnostic, and WhatsApp regression coverage.
- 1.4 GREEN: generalized cost recording and aggregation; added configurable rates, exact-once internal call keys, and zero-cost diagnostics while retaining WhatsApp sums and audit alert dedupe.
- 2.1 RED: added blocked no-LLM persistence, conservative-mode, gate, and operator panel-access tests.
- 2.2 GREEN: added typed cost mode/directive state, inserted `panel_cost_gate` after context assembly, and short-circuited blocked requests before planning; conservative directives apply to planner and response prompts.
- 2.3 GREEN: retained the Phase 1 settings-KV `cost.llm_rates` defaults with documented source/effective date; gate reads the one-thread internal scope and global UTC-day scope.

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

## Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command | `DATABASE_URL='postgresql+psycopg://app:app@localhost:5434/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5434/lumat' uv run pytest tests/integration/test_assistant_chat.py tests/integration/test_assistant_harness_guardrails.py` — 21 passed. |
| Runtime harness | Same command exercised PostgreSQL-backed panel POST message, persisted blocked agent reply, realtime-compatible message path, and mocked LLM call boundary. |
| Full suite | `... uv run pytest tests/` — 694 passed, 1 pre-existing RuntimeWarning. |
| Rollback boundary | Revert `app/chat/assistant/state.py`, `app/chat/assistant/graph.py`, `app/chat/assistant/nodes.py`, `app/services/agent_chat.py`, and the two assistant integration test files; leave Phase 1 cost service/migration and Phases 3–4 untouched. |

## Ponytail Review

- Reused the existing cost service, settings KV, JSON metadata, and audit dedupe; no ledger, synthetic WhatsApp rows, or new dependency added.
- Gate uses existing `internal_thread_cost_state`, `daily_cost_state`, and `maybe_alert_owner`; no new UI or operator lockout was introduced.

## Graph Check

Nodes consulted: `AssistantState`, `assistant/state.py`, `assistant/graph.py`, `nodes.py`, `assemble_context()`, `plan_llm()`, `internal_thread_cost_state()`, `daily_cost_state()`, `maybe_alert_owner()`, `get_setting()`, `services/settings.py`, `agent_chat.py`, `test_assistant_chat.py`, `test_assistant_harness_guardrails.py`.

Edges consulted: `state.py` → `graph.py` → `nodes.py`; `assemble_context()` → `panel_cost_gate` → `plan_llm`; `conversation_cost_state()` ←calls— `cost_gate()` —calls→ `daily_cost_state()`; `get_setting()` ←contains— `services/settings.py`; `agent_chat.py` → existing message/realtime persistence path. Phase 1 nodes retained: `costs.py` → `daily_spend()`/`maybe_alert_owner()` → `InternalChatMessage`.
