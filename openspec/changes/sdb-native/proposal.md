# Proposal: Native SDB Seven-Phase Subgraph

## Intent

Implement handoff #3 in the panel assistant; `complex` planning emits deferred metadata.

## Scope

### In Scope
- Native branch: `CLARIFY → SPEC → PLAN → APPROVE → EXECUTE → VERIFY → DELIVER`.
- Dual trigger: structured planner classification plus authenticated admin request; malformed/conflicting signals fail closed.
- Reuse cost, approval, audit, evidence, replay, claim, and recovery.
- Persist bounded SPEC/STATE/RESULT and checkpoints through Tukulpan with panel scope, thread entity, and `proyecto='default'` at every seam.
- Freeze scope at SPEC; require verifiable task outputs; checkpoint tasks; distinguish `scope-not-found` from `not-exist`; verify against SPEC.

### Out of Scope
- Projects registry, deduplication, project UI, and non-default project behavior; separate future SDD.
- Separate runtime, tables, command center, sub-agents, or implicit/broad search. Recall, if needed, is explicit and scope-frozen.

## Capabilities

### New Capabilities
- `sdb-native`: Seven-phase execution, artifacts, triggers, approval, verification, and recovery.

### Modified Capabilities
- `harness-lumat`, `assistant-operations`, `internal-agent-chat`: Extend routing, safety, and durable resume.
- `memory`: Store typed artifacts with explicit project parameterization.
- `agent-config`: Declare structured SDB classification.

## Approach

Branch after `plan_llm` through a trigger gate in `AssistantState`. Keep thread JSON authoritative; use Tukulpan for bounded artifacts. Digest phase/task plans. Preserve normal routing.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `app/chat/assistant/`, `app/services/` | Modified | Graph, state, persistence, resume, approval, Tukulpan. |
| `app/panel/api/routes/chat.py`, `agent/` | Modified | Trigger and classification contract. |
| `tests/` | New | Phase, approval, recovery, scope, artifacts. |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Retry duplicates work | Med | Checkpoints and atomic claims. |
| Approval covers changed SPEC | Med | Digest phase/task payload; verify SPEC. |
| State grows unbounded | Med | Bound outputs, events, and payloads. |

## Rollback Plan

Disable the trigger and revert SDB graph/state/persistence changes. Normal routing, approvals, and thread data remain usable.

## Dependencies

- Handoff #1/#2; migration 009 expected sufficient.

## Success Criteria

- [ ] Both triggers enter seven phases; ordinary turns are unchanged.
- [ ] Approval, cost, evidence, audit, replay, and resume remain intact.
- [ ] Artifacts/checkpoints are typed, bounded, frozen, and default `proyecto='default'`.
- [ ] Tests prove no duplicate execution, no implicit search, and no Projects work.

## Ponytail Cuts

- `delete:` Runtime, tables, Projects CRUD/UI, sub-agents, and broad memory registration.
- `yagni:` New approval tokens; reuse `approval.py` digest and atomic claim.
- `native:` New event bus/checkpointer; reuse LangGraph state, JSONB, replay, and Tukulpan.

## Graph Nodes Validated

Nodes: `plan_llm()`, `AssistantState`, graph/nodes, `agent_chat.py`, `tukulpan.py`, `upsert()`, approval, registry, audit, search. Edges: `run_assistant() → agent_chat.py → tukulpan.py → upsert()`; `issue_approval() → approve_plan()`. Stale graph: `c4d13da7` vs `267821ee`; read-only.
