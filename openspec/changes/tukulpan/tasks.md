# Tasks: Tukulpan Canonical Memory Boundary

## Review Workload Forecast

Chained PRs recommended: Yes
400-line budget risk: High
Estimated changed lines: 820
Decision needed before apply: No

Auto-chain uses stacked-to-main. Estimate: ~470 production lines across the six existing implementation modules plus ~350 strict-TDD test lines; `tukulpan.py` is a new canonical copy, and tests cover integration seams.

## Work Unit 1: Canonical Boundary (PR 1)

- [x] 1.1 RED — Add alias-identity and CRUD/project-guard tests in `tests/spec/test_memory_spec.py` for MEM-2 canonical/legacy imports, upsert, and non-default rejection.
- [x] 1.2 GREEN — Create `app/services/tukulpan.py` with the existing CRUD/embed/project-guard implementation and explicit `record_milestone()`/`record_decision()` contracts (MEM-2 scenarios).
- [x] 1.3 GREEN — Replace `app/services/memory.py` implementation with forwarding-only exports and update `app/chat/assistant/tools/registry.py` imports/read seam; preserve customer callers and identifiers (MEM-2, MEM-3).

## Work Unit 2: Deterministic Projection (PR 2)

- [ ] 2.1 RED — Extend `tests/integration/test_assistant_harness_context.py` with panel/entity scope, pinned-first, fixed-budget, source-ID, truncation, and “no hybrid search” failures (HL-1, MEM-3 scenarios).
- [ ] 2.2 GREEN — Update `app/services/agent_chat.py` and `app/chat/assistant/nodes.py` to load `panel/thread:{id}` through Tukulpan, partition pinned rows first, and emit deterministic metadata (HL-1, MEM-3).
- [ ] 2.3 GREEN — Update `app/chat/assistant/state.py` and `app/chat/assistant/graph.py` to carry `context_meta` and projection evidence through the assistant graph (HL-1).

## Work Unit 3: Meaningful Write Lifecycle (PR 3)

- [ ] 3.1 RED — Add milestone/decision, bounded recap schema/key, retry-idempotency, and failure-evidence tests in `tests/integration/test_assistant_harness_session.py` and `tests/spec/test_memory_spec.py` (MEM-7, HL-3 scenarios).
- [ ] 3.2 GREEN — Implement recap upsert and degraded-result handling in `app/services/tukulpan.py`, replacing the synthetic flush seam in `app/chat/assistant/nodes.py` and `app/services/agent_chat.py` (MEM-7, HL-3).
- [ ] 3.3 GREEN — Preserve compaction evidence and failed-write status through `app/chat/assistant/state.py` and `app/chat/assistant/graph.py`; keep rotation DB-authoritative (HL-3).

## Work Unit 4: Isolation and Evidence Hardening (PR 4)

- [ ] 4.1 RED — Add scope/entity isolation, WhatsApp compatibility, threshold-empty-search, explicit `memory.read`, and failed-compaction integration cases in `tests/spec/test_memory_spec.py`, `tests/integration/test_assistant_harness_context.py`, and `tests/integration/test_assistant_harness_compatibility.py` (MEM-3, HL-1, HL-3).
- [ ] 4.2 GREEN — Move/preserve `hybrid_search()` in `app/services/tukulpan.py`, wire validated scoped reads in `app/chat/assistant/tools/registry.py`, and verify panel/WhatsApp boundaries (MEM-3).
- [ ] 4.3 GREEN — Finalize canonical seam imports/results in `app/chat/assistant/nodes.py`, `app/services/agent_chat.py`, and `app/chat/assistant/graph.py`; run `uv run pytest tests/` and verify deferred boundaries (MEM-7, HL-3).

## Work-Unit Verification

Each PR keeps its RED tests with the GREEN behavior. Focused commands are `uv run pytest tests/spec/test_memory_spec.py`, `uv run pytest tests/integration/test_assistant_harness_context.py tests/integration/test_assistant_harness_session.py`, then `uv run pytest tests/`. Runtime harness: `uv run pytest tests/` against the migrated PostgreSQL/pgvector fixtures. Rollback boundaries are PR 1 alias/service, PR 2 projection, PR 3 lifecycle, and PR 4 isolation/evidence respectively.

Graph task mapping: PR 1 → `memory.py`/`Memory`/`kb.embed_texts()`; PR 2 → `agent_chat.py`/`assemble_context()`/`load_panel_context()`/`AssistantState`; PR 3 → `compact_session()`/`nodes.py`/`graph.py`; PR 4 → `registry.py`/`memory.read`/`hybrid_search()`/tests. Graph edges consulted: memory → models, agent chat → assembly/compaction, registry → list/read, graph → nodes/state, tests → each seam.

Ponytail task cuts: `shrink:` merged alias migration with its consumer import update; `yagni:` no separate generic writer, event bus, checkpointer, schema migration, or new test module; `stdlib:` JSON recap serialization and token ceiling stay in existing seams. Net: -3 task groups from the design’s broader possibilities.
