# Proposal: Cortex-session Planning Surface

## Intent

Provide administrators a planning surface before a bounded SDB handoff, without adding a second engine.

## Scope

### In Scope
- Thread-level Cortex mode with a fail-closed gate, explicit UI and literal `/planning <topic>` / `/planning close` controls, and a visible indicator.
- Agentic `question` / `research` / `decision` / `continue` / `close` loop; durable Tukulpan artifacts; explicit merge under `assistant_state["cortex_session"]`.
- Close-time SDB SPEC handoff ending at an admin-approved plan; authenticated read-only list/detail/reopen APIs and planning navigation.
- Unit, spec, integration tests.

### Out of Scope
- Real SDB EXECUTE tool wiring, execution without approval, auto-close, multiple sessions per thread, new tables/event bus/planning engine, and multi-step research sub-agents.

## Capabilities

### New Capabilities
- `cortex-session`: Lifecycle, turn loop, durable artifacts, handoff proposal, and browse/reopen behavior.

### Modified Capabilities
- `harness-lumat`: Add Cortex routing; preserve guardrails and context boundaries.
- `internal-agent-chat`: Extend thread state without changing authorization/message contracts.
- `sdb-native`: Consume a closed session as SPEC; retain approval.
- `panel-app`: Add planning-session read/navigation contracts.
- `agent-config`: Declare Cortex runtime configuration.

## Approach

Extend `app/chat/assistant/{graph,nodes,state}.py` with a minimal gate and nodes. Persist turns through explicit merge in `app/services/agent_chat.py`. Use `tukulpan.record_decision`/`upsert` with required keys, panel scope, and thread identity. Add lifecycle/read endpoints following `PanelShell.NAVIGATION` plus `ProjectsPage`. Commands are literal; free text never changes lifecycle.

Ponytail: no new abstraction, table, bus, or planner; SDB remains discipline. Graph consulted: `NAVIGATION`, shell → `AgentChat`, `submit_message`, `record_decision` ↔ `list_for_entity`, `chat.py`. Graph is stale (`c4d13da7`); refresh is blocked by the unavailable OpenAI key.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/chat/assistant/` | Modified | Gate, loop, state |
| `app/services/{agent_chat,tukulpan}.py` | Modified | Merge/artifacts |
| `app/panel/api/routes/` | Modified | Lifecycle/read API |
| `web/src/components/{pages,domain}/` | Modified | UI/navigation |
| `agent/registry.yaml`, `tests/` | Modified | Config and coverage |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Multi-turn state or decisions are lost | Med | Nested merge and one key per decision |
| Handoff implies unavailable execution | High | Deliver and label only an approved plan |
| Trigger ambiguity bypasses lifecycle | Low | Literal commands and validation |

## Rollback Plan

Revert Cortex graph/state, endpoints, UI, registry, tests, and change specs. Existing chat and SDB paths remain; no migration is introduced.

## Dependencies

- Existing Tukulpan, thread, SDB approval, and panel-auth contracts.

## Success Criteria

- [ ] Admins can explicitly open, conduct, close, browse, and reopen one session per thread.
- [ ] Decisions/reports survive reload with required keys, scope, and entity identity.
- [ ] Close produces an approved SDB plan without claiming execution.
- [ ] Unit, spec, and integration suites pass.
