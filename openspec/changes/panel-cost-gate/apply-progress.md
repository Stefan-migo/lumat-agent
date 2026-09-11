# Apply Progress: Panel Assistant Cost Gate

## Status

- Phase 1 (PR 1) tasks 1.1–1.4 complete.
- Mode: Strict TDD.
- Delivery: chained PR slice, PR 1 boundary only. Phases 2–4 remain pending.
- Changed lines: approximately 201 authored lines, below the 500-line attempt budget.

## Completed Work

- 1.1 RED: added migration-version, nullable-column, and app-grant assertions.
- 1.2 GREEN: added migration 023 and `InternalChatMessage.cost_llm` mapping.
- 1.3 RED: added internal-thread, combined UTC-day, explicit/idempotent pricing, unknown-model diagnostic, and WhatsApp regression coverage.
- 1.4 GREEN: generalized cost recording and aggregation; added configurable rates, exact-once internal call keys, and zero-cost diagnostics while retaining WhatsApp sums and audit alert dedupe.

## TDD Cycle Evidence

| Task | RED | GREEN | REFACTOR |
|---|---|---|---|
| 1.1 | Migration tests failed before 023 existed (missing version/column). | Migration and grant tests pass. | N/A; retained existing migration runner convention. |
| 1.2 | Same migration/type failures. | Focused migration tests pass. | `git diff --check` passes. |
| 1.3 | Cost tests failed before internal model/service support. | Focused guardrail tests pass. | Added shared seed helper and reset internal tables per test. |
| 1.4 | Same guardrail failures. | 41 focused tests pass; full suite passes. | Preserved legacy positional `Message` recorder API and alert path. |

## Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command | `DATABASE_URL='postgresql+psycopg://app:app@localhost:5434/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5434/lumat' uv run pytest tests/integration/test_migrations.py tests/integration/test_cost_guardrails.py` — 41 passed. |
| Runtime harness | Same command exercised PostgreSQL on localhost:5434, migration runner, app-role grants, SQL aggregation, and persisted SQLAlchemy rows. |
| Full suite | `... uv run pytest tests/` — 689 passed, 1 pre-existing RuntimeWarning. |
| Rollback boundary | Revert `db/migrations/023_panel_cost_llm.sql`, `app/models.py`, `app/services/costs.py`, `app/services/settings.py`, and the two integration test files; leave Phases 2–4 untouched. |

## Graph Check

Nodes consulted: `costs.py`, `daily_spend()`, `maybe_alert_owner()`, `InternalChatMessage`, `internal_chat_messages.cost_llm NUMERIC(12,6)`, `test_cost_guardrails.py`, `db/migrations/023_panel_cost_llm.sql`, `models.py`, `record_audit()`.

Edges consulted: `costs.py` ←imports_from— `test_cost_guardrails.py`; `daily_spend()` ←calls— `cost_gate()` —calls→ `maybe_alert_owner()`; migration 023 → `InternalChatMessage` (design/spec contract).

## Ponytail Review

- Reused the existing cost service, settings KV, JSON metadata, and audit dedupe; no ledger, synthetic WhatsApp rows, or new dependency added.
