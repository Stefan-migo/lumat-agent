# Apply Progress: Tukulpan Canonical Boundary (PR 1)

## Status

- Work Unit: 1 — Canonical Boundary
- Delivery: stacked-to-main, PR 1 of 4
- Mode: Strict TDD
- Completed: 1.1, 1.2, 1.3
- Changed-lines estimate: 110 authored lines (well below the 300-line native attempt budget)

## Completed Tasks

- [x] 1.1 RED — Added canonical/legacy alias identity, canonical CRUD, and non-default project guard tests.
- [x] 1.2 GREEN — Moved the implementation to `app/services/tukulpan.py` and added the explicit milestone/decision staging contracts.
- [x] 1.3 GREEN — Reduced `app/services/memory.py` to a forwarding-only alias and routed the assistant memory read seam through Tukulpan while preserving the `registry.memory` test seam.

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/spec/test_memory_spec.py` | Integration/spec | ✅ 11/11 | ✅ Import failed because `tukulpan` did not exist | ✅ 13/13 | ✅ Alias identity + default CRUD + rejected project | ✅ Focused assertions kept in existing spec file |
| 1.2 | `tests/spec/test_memory_spec.py` | Integration/spec | ✅ 11/11 | ✅ 1.1 failure drove missing canonical module | ✅ 13/13 | ✅ Existing CRUD, embed, and project-guard scenarios | ✅ Canonical implementation retained existing behavior |
| 1.3 | `tests/unit/test_assistant_tools.py`, `tests/spec/test_memory_spec.py` | Unit/spec | ✅ 11/11 | ✅ Registry test initially failed after import seam rename | ✅ 22/22 | ✅ Bounded read and alias identity | ✅ `tukulpan as memory` preserves customer/test callers |

## Work Unit Evidence

| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `uv run pytest tests/unit/test_assistant_tools.py tests/spec/test_memory_spec.py -q` → **22 passed** |
| Runtime harness command/scenario and exact result | `uv run pytest tests/` → **285 passed, 2 failed, 384 errors**; errors are pre-existing environment/migration privilege failures (`permission denied to alter role`), and the two failures are unrelated terminology/spec-fixture failures |
| Rollback boundary | Revert the PR 1 service rename/alias, registry import seam, and `tests/spec/test_memory_spec.py`; persisted tables, enums, and `proyecto='default'` identifiers are untouched |

## Graph Check

- Nodes consulted: `memory.py`, `Memory`, `models.py`, `services/kb.py`, `embed_texts()`, `registry.py`, `upsert()`, `test_memory_spec.py`.
- Edges consulted: `memory.py --imports--> Memory`; `models.py --imports_from--> services/kb.py --contains--> embed_texts()`; `registry.py --imports_from--> memory.py`.
- Graph report: existing `graphify-out/GRAPH_REPORT.md`, stale-but-usable graph commit `a7abba4b` compared with branch base `c6f3c636`; no rebuild performed during the work unit.

## Ponytail Cuts

- `shrink:` merge alias migration with the consumer import update; one implementation plus one forwarding module.
- `yagni:` no generic writer, event bus, checkpointer, schema migration, or new test module.
- `stdlib:` retain existing JSON/SQLAlchemy/native uniqueness and embedding seams; add no dependency or abstraction.

## Issues / Deviations

- None from the design for Work Unit 1. Work Units 2–4 remain intentionally untouched.
