# Design: Tukulpan Canonical Memory Boundary

## Technical Approach

Create `app.services.tukulpan` as implementation boundary; `app.services.memory`
is a forwarding re-export. Panel consumers migrate; WhatsApp, APIs, persisted names,
and explicit `memory.read` remain compatible.

Graph nodes consulted: `memory.py`, `Memory`, `models.py`, `kb.embed_texts()`,
`agent_chat.py`, `assemble_context()`, `load_panel_context()`,
`compact_session()`, `AssistantState`, assistant graph, `registry.py`,
`_read_memory()`, `memory.read`. Edges: memory → models ← agent chat → assembly;
agent chat → context/compaction; registry → list.
Graph report is stale-but-usable (`a7abba4b` vs `c6f3c636`); queries ran without rebuilding.

## Architecture Decisions

| Decision | Choice | Alternatives / rationale |
|---|---|---|
| Boundary | Move implementation to `tukulpan.py`; `memory.py` only re-exports public names. | A literal rename breaks imports; two implementations risk drift. |
| Projection | `list_for_entity(scope="panel", entity_id="thread:{id}")`, stable DB order, pinned partition first, then non-pinned, budgeted once. | No `hybrid_search()` in assembly: semantic recall is explicit and costly; deterministic projection is predictable. |
| Search boundary | Move `hybrid_search()` unchanged from `app/services/memory.py:217-287` into Tukulpan; it returns above-threshold fused-score results, ranked descending. | Alias re-exports it; threshold misses remain empty with no fallback. |
| Writes | Add explicit milestone/decision helpers and replace the synthetic flush with a bounded recap upsert. | No per-message writer, event bus, checkpointer, or Cortex-session runtime; those are deferred. |
| Failure | Catch embedding/persistence failures, return degraded evidence, and continue; never claim a successful flush. | Memory is auxiliary evidence, not a turn prerequisite. |

## Data Flow

```text
panel request → assemble_context → Tukulpan panel projection → budgeted context
             → assistant graph → response/evidence
                         └─ threshold → bounded recap upsert → rotation evidence
```

`assemble_context()` reads DB-authoritative history, obtains the panel projection,
and injects pinned rows, unpinned rows, newest fitting history (chronological),
then attachments. Each accepted item consumes `estimate_tokens()` from 4,000
tokens; skipped or byte-truncated items set `truncated`. Metadata contains source
IDs, total tokens, and truncation evidence. The projection never searches.
Moved `hybrid_search()` preserves its existing threshold and fused-score ranking;
below-threshold results return `[]`, with no fallback.

Per-turn sequence: authorize/load thread → project `panel/thread:{id}` → assemble
and record `context_meta` → planner explicitly chooses `memory.read` (or a direct
`hybrid_search()` tool call) when search is needed → plan/execute/respond →
collect evidence. “Search before responding” is therefore a planner/tool protocol,
not an assembly side effect; `registry.py` and the persona instruction document
it. At the
4,000-token threshold, compact before rotation: select the newest 2,000-token
 window, build a bounded recap, upsert it, then rotate. The recap is bounded
 JSON with `schema_version`, `thread_id`, `source_message_ids`, `source_tokens`,
 `truncated`, and `recap`. Its key is
`assistant-recap:{thread_id}:{last_source_message_id}`. The unique memory key
prevents duplicate retries; the result records `written`, `id`, or
`degraded_reason` in compaction evidence.

Milestone and decision writes use `tipo=SUMMARY`/`DECISION`, explicit topic keys,
and the default-project guard. A decision helper is available to deferred
Cortex-session integration. Embedding failures leave the transaction usable and
surface degraded evidence; callers may commit without a synthetic row.

Scope is always passed explicitly: panel uses `panel/thread:{id}` and WhatsApp
continues `customer/{id}` through legacy-compatible functions. Writes reject
non-`default` `proyecto`; reads return only visible scope/entity rows, so callers
without cross-project rights cannot cross the boundary. Panel reads cannot return
WhatsApp rows, and vice versa.

## Usage Protocol

The assistant searches before responding only when its planner selects explicit
`memory.read` (or requested `hybrid_search()`), with scope/entity arguments
validated by the tool contract. Assembly only uses deterministic projection.

## File Changes

| File | Action | Description |
|---|---|---|
| `app/services/tukulpan.py` | Create | Canonical memory implementation. |
| `app/services/memory.py` | Modify | Forwarding alias. |
| `app/services/agent_chat.py` | Modify | Projection, recap, evidence. |
| `app/chat/assistant/nodes.py` | Modify | Canonical seam imports/results. |
| `app/chat/assistant/state.py` | Modify | Context/compaction contracts. |
| `app/chat/assistant/tools/registry.py` | Modify | Explicit scoped read. |
| `app/chat/assistant/graph.py` | Modify | Preserve evidence flow. |
| `tests/` | Add/modify | Strict RED-GREEN contract coverage. |

## Interfaces / Contracts

```python
def record_milestone(session, *, thread_id: int, topic_key: str, title: str, content: str) -> Memory: ...
def record_decision(session, *, thread_id: int, topic_key: str, title: str, content: str) -> Memory: ...
def write_recap(session, *, thread_id: int, source_message_ids: list[int], recap: str, source_tokens: int, truncated: bool) -> dict: ...
```

All service functions remain caller-committed. The alias must expose identical
objects (`memory.upsert is tukulpan.upsert`) and must not contain business logic.

## Testing Strategy

Run `uv run pytest tests/` under strict TDD. Unit-test accounting, ordering,
recap key/schema, alias identity, and degradation; integration-test retry, scope
isolation, metadata, and failed compaction. Assert assembly skips search and
threshold misses return `[]`.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file
classification, or process-integration boundary.

## Migration / Rollout

No migration; deploy or revert module and alias together. Rows and identifiers remain.

## Open Questions

None blocking.

Ponytail design cuts: `yagni:` no event bus/checkpointer or generic writer;
`shrink:` one implementation plus re-export; `delete:` no schema rename,
sub-agents, or implicit search; `stdlib:` existing JSON, `ceil`, and SQLAlchemy
uniqueness.
