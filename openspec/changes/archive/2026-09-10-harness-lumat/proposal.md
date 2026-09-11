# Proposal: Harness Lumat

## Intent

Evolve the shipped panel assistant from a stateless, keyword-planned turn into a durable, session-aware Lumat harness. The change must make thread history, approved agent configuration, bounded memory context, and LLM planning truthful without duplicating persistence or weakening the existing admin safety contract.

## Scope

### In Scope
- Evolve the existing LangGraph graph toward `START → assemble_context → plan_llm → guardrails → execute_tool | respond_stream → persist + evidence → END`.
- Wire `assistant_{plan,respond,classify}` and the assistant persona from `agent/registry.yaml`; assemble DB thread history, attachments, and Tukulpan `panel` + pinned context.
- Add deterministic whitelist, approval, cost, audit/evidence ordering, recovery, rolling-session, preflight compaction, memory-flush, hooks, and read-only approved-config behavior.
- Rename Lumat’s “SDB (Deterministic Behavior Database)” terminology to “Gates deterministas / Guardrails”, with a repository-wide consumer inventory.

### Out of Scope
- Tukulpan internals or service rename; the seven-phase Spec Driven Behavior subgraph; Cortex-session interaction; panel sub-agents. Only extension hooks are allowed.
- LangGraph checkpointer, a second runtime loop, new panel configuration editing, or unrelated H2/M2/M3 features.

## Capabilities

### New Capabilities
- `harness-lumat`: Session-aware panel harness, context assembly, LLM planning, guardrails, compaction, and extension hooks.

### Modified Capabilities
- `internal-agent-chat`: Preserve admin-only durable threads, compatible endpoints/SSE, DB-authoritative recovery, and non-coupling to WhatsApp.
- `assistant-operations`: Extend planning/context while preserving exact-argument approval, audit/evidence ordering, and durable recovery.
- `assistant-tools`: Enforce the assistant registry whitelist at dispatch without duplicating domain tools.
- `agent-config`: Consume validated persona/prompts/config read-only at runtime; retain non-executable skills.

## Approach

Use the existing AssistantState graph and database persistence boundary. Add minimal state for assembled context, structured planner output, guardrail decisions, and compaction evidence. Adapt existing deterministic gate and audit patterns; keep DB history authoritative and omit a checkpointer. Prior art already shipped: `config-agente-lumat`, `panel-asistente-lumat`, `memoria-persistente-lumat`, and `h2-router-langgraph`; this change adds their missing panel harness integration, not replacement systems.

Exact injection budget, compaction threshold/window, token measurement, per-run/cost budgets, and planner fallback semantics remain design decisions.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/chat/assistant/*`, `app/services/agent_chat.py` | Modified | Graph, context, session, persistence, and recovery seams |
| `agent/registry.yaml`, `agent/prompts/*`, `agent/personas/assistant.md` | Modified | Runtime prompt/config consumption |
| `app/chat/assistant/tools/registry.py`, guardrails/audit services | Modified | Whitelist and deterministic safety |
| `agent/skills/sdb.md`, docs/spec consumers | Modified | Terminology migration |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Invalid or unsafe LLM plan | Med | Strict schema validation; bounded safe fallback; never unchecked execution |
| Context growth loses facts or raises cost | High | Design-time budgets, token measurement, pre-compaction flush, persisted evidence |
| Compatibility or terminology regressions | Med | Preserve serialized fields/order and run consumer grep plus contract tests |

## Rollback Plan

Revert the harness graph/config and terminology commits as a unit, retaining existing DB rows and API contracts. Disable new planner/context paths behind the existing runtime boundary and replay/recover from persisted thread state; no checkpointer or destructive migration is introduced.

## Success Criteria

- [ ] Authorized panel turns use the target topology with DB history and declared registry prompts.
- [ ] Unauthorized tools/writes cannot execute; exact approvals, audit/evidence order, SSE, and recovery remain compatible.
- [ ] Context budgets and compaction/flush behavior are deterministic and observable.
- [ ] All old SDB terminology consumers are inventoried and renamed without changing Spec Driven Behavior scope.
