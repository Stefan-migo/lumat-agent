# Apply Progress: Tukulpan Canonical Boundary (PR 1 + PR 2 + PR 3 + PR 4)

## Status

- Work Unit: 4 — Isolation and Evidence Hardening
- Delivery: stacked-to-main, PR 4 of 4
- Mode: Strict TDD
- Completed: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3
- Changed-lines estimate: 91 authored lines for PR 4 (under the 800-line work-unit budget)

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
- [x] 4.1 RED — Added panel `thread:{id}` versus WhatsApp `customer:{id}` isolation, explicit scoped-read validation, no-search projection, and failed-compaction evidence cases.
- [x] 4.2 GREEN — Preserved Tukulpan `hybrid_search()` threshold/fused ranking and no-fallback behavior; validated panel/customer entity shapes for `memory.read` while retaining legacy numeric WhatsApp IDs.
- [x] 4.3 GREEN — Changed failed compaction graph results to `degraded`, retained canonical Tukulpan seams, and verified deferred boundaries without adding runtime subsystems.

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
| 4.1 | `tests/spec/test_memory_spec.py`, `tests/integration/test_assistant_harness_context.py`, `tests/integration/test_assistant_harness_compatibility.py` | Spec/integration | ✅ 36/36 | ✅ Isolation, scoped-read, no-search, and degraded-result assertions failed before implementation | ✅ 40/40 | ✅ Panel/customer isolation plus legacy numeric customer compatibility | ✅ Reused existing Tukulpan and graph seams |
| 4.2 | Same as 4.1 | Spec/integration | ✅ 36/36 | ✅ Cross-scope `memory.read` shape was accepted before validation | ✅ 40/40 | ✅ Valid panel/customer reads and threshold-empty search | ✅ Pydantic validator only; no new adapter |
| 4.3 | `tests/integration/test_assistant_harness_compatibility.py` | Integration | ✅ 36/36 | ✅ Failed compaction retained `completed` status | ✅ 40/40 | ✅ Degraded evidence and status are both preserved | ✅ One status expression; no graph node or bus added |

## Work Unit Evidence

| Evidence | Result |
|----------|--------|
| Focused test command and exact result | Required DB env + `uv run pytest tests/spec/test_memory_spec.py tests/integration/test_assistant_harness_context.py tests/integration/test_assistant_harness_compatibility.py tests/integration/test_assistant_harness_session.py -q` → **40 passed** |
| Runtime harness command/scenario and exact result | Required DB env + `uv run pytest tests/` → **681 passed, 2 pre-existing failures, 1 warning** in 371.09s; both failures are the explicitly out-of-scope archived `harness-lumat` terminology/path tests. |
| Rollback boundary | Revert PR 4 changes in `app/chat/assistant/tools/registry.py`, `app/chat/assistant/nodes.py`, and the three PR 4 test files; PR 1–3 canonical, projection, and lifecycle behavior remains. |

## Graph Check

- Nodes consulted: `memory.py`, `Memory`, `models.py`, `services/kb.py`, `embed_texts()`, `registry.py`, `upsert()`, `test_memory_spec.py`, `agent_chat.py`, `assemble_context()`, `load_panel_context()`, `AssistantState`, `app/chat/assistant/nodes.py`, `app/chat/assistant/graph.py`.
- Edges consulted: `memory.py --imports--> Memory`; `models.py --imports_from--> services/kb.py --contains--> embed_texts()`; `registry.py --imports_from--> memory.py`; `agent_chat.py --contains--> assemble_context()`; `assemble_context() --calls--> load_panel_context()`; `load_panel_context() --reads--> Memory`; `nodes.py --uses--> AssistantState`; `graph.py --routes--> nodes.py`.
- Additional nodes consulted: `registry.py`, `memory.read`, `hybrid_search()`, `list_for_entity()`, `agent_chat.py`, `nodes.py`, `graph.py`, `test_memory_spec.py`, `test_assistant_harness_context.py`, `test_assistant_harness_compatibility.py`.
- Additional edges consulted: `registry.py <--references--> tasks.md <--references--> memory.read`; `tukulpan.py --contains--> hybrid_search() --references--> list_for_entity()`; `nodes.py --imports_from--> llm.py <--imports_from-- chat/graph.py`; `agent_chat.py --imports_from--> nodes.py`.
- Graph report: existing `graphify-out/GRAPH_REPORT.md`, stale-but-usable graph commit `a7abba4b`; required WU4 queries/paths ran before edits; no rebuild performed during the work unit.

## Ponytail Cuts

- `shrink:` merge alias migration with the consumer import update; one implementation plus one forwarding module.
- `yagni:` no generic writer, event bus, checkpointer, schema migration, or new test module.
- `stdlib:` retain existing JSON/SQLAlchemy/native uniqueness and embedding seams; add no dependency or abstraction.
- `yagni:` no search adapter or projection object; the existing Tukulpan list seam and metadata dictionary are sufficient.
- `stdlib:` reuse `estimate_tokens()` and TypedDict state; no tokenization dependency or graph node was added.
- `stdlib:` JSON serialization and SQLAlchemy savepoints provide bounded payloads and transaction recovery; no writer abstraction or event bus was added.
- `yagni:` no metadata-only synthetic memory row; the recap is the only pre-rotation write.
- `shrink:` reused `MemoryArgs` and `collect_evidence()` rather than adding a separate authorization or compaction-result abstraction.
- `stdlib:` Pydantic's existing `model_validator` handles scope/entity validation; no new schema or dependency.

## Issues / Deviations

- None from the design. The two full-suite failures are pre-existing and explicitly out of scope: archived `openspec/changes/harness-lumat/...` references in `tests/unit/test_assistant_extensions.py`.

## Deferred boundaries verified

- No SDB subgraph added or loaded.
- No Cortex-session mode added.
- No archived-artifact rename performed.
- No second event bus introduced.
- No implicit search: `assemble_context()` and `load_panel_context()` use deterministic `list_for_entity()` only; search remains explicit.
