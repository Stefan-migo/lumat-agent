# Apply Progress: Tukulpan Canonical Boundary (PR 1 + PR 2 + PR 3)

## Status

- Work Unit: 3 — Meaningful Write Lifecycle
- Delivery: stacked-to-main, PR 3 of 4
- Mode: Strict TDD
- Completed: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3
- Changed-lines estimate: 200 authored lines for PR 3 (under the 700-line work-unit budget)

## Completed Tasks

- [x] 1.1 RED — Added canonical/legacy alias identity, canonical CRUD, and non-default project guard tests.
- [x] 1.2 GREEN — Moved the implementation to `app/services/tukulpan.py` and added the explicit milestone/decision staging contracts.
- [x] 1.3 GREEN — Reduced `app/services/memory.py` to a forwarding-only alias and routed the assistant memory read seam through Tukulpan while preserving the `registry.memory` test seam.
- [x] 2.1 RED — Added scope/entity, pinned-first, fixed-budget, source-ID, truncation, no-search, and graph-evidence integration failures.
- [x] 2.2 GREEN — Routed panel projection through canonical Tukulpan, partitioned pinned rows first, and emitted deterministic scope, source-ID, token, and truncation metadata.
- [x] 2.3 GREEN — Carried context metadata and projection evidence through `AssistantState` and the assistant graph.
- [x] 3.1 RED — Added MEM-7/HL-3 tests for milestone and decision types, bounded recap schema/key, retry idempotency, degraded writes, DB-authoritative rotation, and graph evidence.
- [x] 3.2 GREEN — Added bounded JSON recap upsert with savepoint-contained degradation, replaced the synthetic flush with meaningful recap content, and rotated only after a durable write.
- [x] 3.3 GREEN — Carried compaction and failed-write evidence through assistant state/graph and exposed degraded evidence in the graph result.

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/spec/test_memory_spec.py` | Integration/spec | ✅ 11/11 | ✅ Import failed because `tukulpan` did not exist | ✅ 13/13 | ✅ Alias identity + default CRUD + rejected project | ✅ Focused assertions kept in existing spec file |
| 1.2 | `tests/spec/test_memory_spec.py` | Integration/spec | ✅ 11/11 | ✅ 1.1 failure drove missing canonical module | ✅ 13/13 | ✅ Existing CRUD, embed, and project-guard scenarios | ✅ Canonical implementation retained existing behavior |
| 1.3 | `tests/unit/test_assistant_tools.py`, `tests/spec/test_memory_spec.py` | Unit/spec | ✅ 11/11 | ✅ Registry test initially failed after import seam rename | ✅ 22/22 | ✅ Bounded read and alias identity | ✅ `tukulpan as memory` preserves customer/test callers |
| 2.1 | `tests/integration/test_assistant_harness_context.py` | Integration | ✅ 4/4 | ✅ New projection and evidence assertions failed before wiring | ✅ 7/7 | ✅ Scope, ordering, truncation, no-search, and graph evidence | ✅ Existing context seam retained |
| 2.2 | `tests/integration/test_assistant_harness_context.py` | Integration | ✅ 4/4 | ✅ Canonical Tukulpan monkeypatch was not observed by legacy import | ✅ 7/7 | ✅ Newest projection order and fixed-budget metadata | ✅ Reused `estimate_tokens()` |
| 2.3 | `tests/integration/test_assistant_harness_context.py` | Integration | ✅ 4/4 | ✅ Projection evidence was absent from graph evidence | ✅ 7/7 | ✅ Context metadata survives graph invocation | ✅ Typed state fields only; no new graph node |
| 3.1 | `tests/spec/test_memory_spec.py`, `tests/integration/test_assistant_harness_session.py` | Integration/spec | ✅ 17/17 | ✅ Missing recap API and old synthetic flush contract failed | ✅ 22/22 | ✅ Two recap inputs plus failure and rotation cases | ✅ Assertions kept at existing seams |
| 3.2 | Same as 3.1 | Integration/spec | ✅ 17/17 | ✅ `write_recap` absent and flush accepted metadata only | ✅ 22/22 | ✅ JSON bound, same-key retry, embedding degradation | ✅ Savepoint and stdlib JSON; no new dependency |
| 3.3 | `tests/integration/test_assistant_harness_session.py` | Integration | ✅ 5/5 | ✅ Failed compaction was not represented in graph evidence | ✅ 25/25 | ✅ Successful and failed rotation paths | ✅ Typed evidence fields only |

## Work Unit Evidence

| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `DATABASE_URL='postgresql+psycopg://app:app@localhost:5433/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5433/lumat' uv run pytest tests/spec/test_memory_spec.py tests/integration/test_assistant_harness_session.py tests/unit/test_assistant_harness.py -q` → **25 passed** |
| Runtime harness command/scenario and exact result | Required harness DB env + `uv run pytest tests/` → **676 passed, 2 pre-existing failures, 1 warning** in 364.47s; failures are the explicitly out-of-scope archived harness-lumat terminology/path tests. |
| Rollback boundary | Revert PR 3 lifecycle changes in `app/services/tukulpan.py`, `app/services/agent_chat.py`, `app/chat/assistant/nodes.py`, `app/chat/assistant/state.py`, `app/chat/assistant/graph.py`, and the lifecycle tests; PR 1–2 projection behavior remains. |

## Graph Check

- Nodes consulted: `memory.py`, `Memory`, `models.py`, `services/kb.py`, `embed_texts()`, `registry.py`, `upsert()`, `test_memory_spec.py`, `agent_chat.py`, `assemble_context()`, `load_panel_context()`, `AssistantState`, `app/chat/assistant/nodes.py`, `app/chat/assistant/graph.py`.
- Edges consulted: `memory.py --imports--> Memory`; `models.py --imports_from--> services/kb.py --contains--> embed_texts()`; `registry.py --imports_from--> memory.py`; `agent_chat.py --contains--> assemble_context()`; `assemble_context() --calls--> load_panel_context()`; `load_panel_context() --reads--> Memory`; `nodes.py --uses--> AssistantState`; `graph.py --routes--> nodes.py`.
- Graph report: existing `graphify-out/GRAPH_REPORT.md`, stale-but-usable graph commit `a7abba4b`; WU3 queries/paths ran before edits; no rebuild performed during the work unit.

## Ponytail Cuts

- `shrink:` merge alias migration with the consumer import update; one implementation plus one forwarding module.
- `yagni:` no generic writer, event bus, checkpointer, schema migration, or new test module.
- `stdlib:` retain existing JSON/SQLAlchemy/native uniqueness and embedding seams; add no dependency or abstraction.
- `yagni:` no search adapter or projection object; the existing Tukulpan list seam and metadata dictionary are sufficient.
- `stdlib:` reuse `estimate_tokens()` and TypedDict state; no tokenization dependency or graph node was added.
- `stdlib:` JSON serialization and SQLAlchemy savepoints provide bounded payloads and transaction recovery; no writer abstraction or event bus was added.
- `yagni:` no metadata-only synthetic memory row; the recap is the only pre-rotation write.

## Issues / Deviations

- None from the design. Work Unit 4 remains intentionally untouched.
