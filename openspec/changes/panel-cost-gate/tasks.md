# Tasks: Panel Assistant Cost Gate

## Review Workload Forecast

Chained PRs recommended: Yes
400-line budget risk: High
Estimated changed lines: 560
Decision needed before apply: No

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|---|---|---|---|---|---|
| 1 | Schema and cost seam | PR 1 | `uv run pytest tests/integration/test_migrations.py tests/integration/test_cost_guardrails.py` | PostgreSQL + pytest | migration 023, `app/models.py`, `app/services/costs.py` |
| 2 | Gate, modes, and settings | PR 2 | `uv run pytest tests/integration/test_assistant_chat.py tests/unit/test_assistant_planner.py` | panel API POST message with mocked LLM | gate/mode files and `app/services/settings.py` |
| 3 | Accounting and recovery | PR 3 | `uv run pytest tests/integration/test_assistant_chat.py tests/integration/test_assistant_harness_session.py` | panel stream/reconnect and retry scenarios | `app/services/agent_chat.py` accounting paths |
| 4 | Regression proof | PR 4 | `uv run pytest tests/` | full pytest; no UI/E2E by design | tests only |

## Phase 1: Migration and Cost Service (PR 1)

- [x] 1.1 **RED:** In `tests/integration/test_migrations.py`, assert migration 023, nullable `internal_chat_messages.cost_llm`, and app-role grants (SS-3 schema contract); map graph `migration 023` → `InternalChatMessage`.
- [x] 1.2 **GREEN:** Create `db/migrations/023_panel_cost_llm.sql` and map `InternalChatMessage.cost_llm` in `app/models.py`; preserve idempotent migration behavior and grants (IAC-2/SS-3).
- [x] 1.3 **RED:** In `tests/integration/test_cost_guardrails.py`, add failing tests for internal-thread, combined UTC-day, explicit/unknown pricing diagnostics, and WhatsApp byte-identical totals (SS-3 scenarios); graph `costs.py` → `test_cost_guardrails.py`.
- [x] 1.4 **GREEN:** Generalize `app/services/costs.py` for internal rows, thread/day aggregation, configurable rates, and zero-cost diagnostics while preserving `Message` behavior and alert dedupe (SS-3 scenarios); graph `costs.py` → `daily_spend()`/`maybe_alert_owner()`.

## Phase 2: Gate and Modes (PR 2)

- [x] 2.1 **RED:** Add tests in `tests/integration/test_assistant_chat.py` and `tests/integration/test_assistant_harness_guardrails.py` for gate-after-context, conservative directive, blocked canned reply, no LLM, and operator access (IAC-2; threat `test_blocked_bypasses_llm`); graph `state.py` → `graph.py` → `nodes.py`.
- [x] 2.2 **GREEN:** Add cost state/directive fields in `app/chat/assistant/state.py`, wire `panel_cost_gate` in `app/chat/assistant/graph.py`, and implement gate/conservative/blocked nodes in `app/chat/assistant/nodes.py` (IAC-2/IAC-3).
- [x] 2.3 **GREEN:** Add `cost.llm_rates` defaults and documented source/effective date in `app/services/settings.py`; ensure `cost.conversation_limit` remains one internal-thread scope and daily scope is global (SS-3 scenarios).

## Phase 3: Accounting, Failure, Recovery (PR 3)

- [ ] 3.1 **RED:** Add tests for planner/terminal usage, `SELECT FOR UPDATE` call-key idempotency, missing usage, disconnect, blocked persistence, and retry/reconnect authority in `tests/integration/test_cost_guardrails.py`, `test_assistant_chat.py`, and `test_assistant_harness_session.py` (SS-3/IAC-3).
- [ ] 3.2 **GREEN:** Pass request ID and persist diagnostics in `app/services/agent_chat.py`; implement atomic `record_llm_cost` accumulation and recovery-safe call keys across `app/chat/assistant/nodes.py` and `agent_chat.py` (SS-3/IAC-3); graph `agent_chat.py` → `stream_events()`/recovery.

## Phase 4: Non-Regression (PR 4)

- [ ] 4.1 **RED:** Add failing non-regression tests in `tests/integration/test_assistant_harness_guardrails.py`, `test_assistant_harness_session.py`, `tests/unit/test_assistant_planner.py`, and `tests/integration/test_assistant_chat.py` for denied/expired approval, WhatsApp unchanged, normal flow, alerts, and persisted blocked/recovery states (IAC-2/IAC-3/SS-3).
- [ ] 4.2 **GREEN:** Make the regression suite pass without changing approval lifecycle or WhatsApp behavior; run `uv run pytest tests/` (IAC-2/IAC-3/SS-3).

## Graph task mapping

Consulted nodes/edges: `migration 023` → `InternalChatMessage`; `costs.py` → `daily_spend()`/`maybe_alert_owner()`; `state.py` → `graph.py` → `nodes.py`; `agent_chat.py` → `stream_events()`; tests import covered seams.

## Ponytail task cuts

- Reused existing cost service, KV settings, audit dedupe, evidence, and recovery paths; no ledger, UI, synthetic WhatsApp rows, or new abstraction tasks.
