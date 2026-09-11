# Proposal: Tukulpan Canonical Memory Boundary

## Intent

Make Tukulpan the active panel-harness memory boundary without breaking persisted
contracts or existing imports. Turn the existing read/flush seams into
deterministic injection and meaningful writes; keep search explicit and WhatsApp
separate.

## Scope

### In Scope
- Add the canonical Tukulpan façade; retain `app.services.memory` as a thin
  compatibility alias and migrate active panel consumers.
- Define `assemble_context()` injection: `scope=panel`, `entity_id=thread:{id}`,
  pinned-first ordering, fixed budget, source IDs, and truncation metadata.
- Implement milestone/decision writes and a bounded pre-rotation recap; preserve
  WhatsApp close and observation paths.
- Document “search before responding, save after milestones”; keep
  `hybrid_search()` explicit.

### Out of Scope
- Database/type or archived-artifact renames; a second event bus or generic
  every-message writer.
- WhatsApp changes, panel sub-agents, SDB, or Cortex-session implementation
  (deferred to SDD #3/#4).

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `memory`: Tukulpan boundary, panel projection, and milestone/recap lifecycle;
  preserve CRUD, search, customer, and persisted contracts.
- `harness-lumat`: Deterministic Tukulpan injection and pre-compaction evidence.

## Approach

Use exploration Approach 2: a canonical façade, forwarding-only legacy module,
and active-consumer/spec migration. Reuse `AssistantState`, `assemble_context()`,
`compact_session()`, and the existing graph; add no checkpointer or implicit
retrieval. Define recap payload, idempotency, and write failure behavior in design.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/{tukulpan,memory}.py` | New/Modified | Façade and alias |
| `app/chat/assistant/nodes.py`, `app/services/agent_chat.py` | Modified | Read/write seams |
| `app/chat/assistant/state.py`, specs, tests | Modified | Budget/contracts |
| WhatsApp graph/state, models, migration, archives | Preserved | Existing boundaries |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Alias drift or scope leakage | Med | Consumer migration and scope/entity tests |
| Recap loses evidence | Med | Bounded schema, idempotency, metadata, failure policy |

## Rollback Plan

Revert façade, consumer, and lifecycle commits as a unit. Keep database rows,
identifiers, and archives; restore the old flush seam and replay DB thread history.

## Success Criteria

- [ ] Panel turns inject only deterministic panel/pinned context within budget.
- [ ] Decisions, milestones, and bounded recaps persist without per-message writes.
- [ ] `hybrid_search()` stays explicit; WhatsApp and legacy imports remain compatible.

## Ponytail Cuts

- `delete`: second event bus, generic writes, and panel sub-agents; later SDDs cover them.
- `shrink`: literal rename; façade plus alias preserves behavior and audit history.
- `yagni`: implicit search; deterministic projection is sufficient and cheaper.

## Graph nodes validated

`memory.py`, `Memory`, `models.py`, `assemble_context()`, `agent_chat.py`,
`load_panel_context()`, `compact_session()`, `flush_panel_session()`,
`memory.read`, assistant graph, and `AssistantState`. Validated edges include
`assemble_context() → agent_chat.py → models.py → Memory` plus panel read/
compaction seams; no new graph or checkpointer is required.
