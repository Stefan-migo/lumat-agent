# Proposal: H2 — Multi-Agent LangGraph Router

## Intent

Fase-2 (AC-4/D-A7): realize the declared multi-agent architecture. Registry is data-only; routing is linear `classify → route → respond`. H2 supervises dispatch to per-capability sub-agents reusing vetted nodes — better internal resolution, end-customer unchanged.

## Scope

### In Scope
- Multi-agent `registry.yaml` schema + read-only startup reader.
- `orchestrate` node; gate prefix (`emergency→cost→handoff`) stays the outer envelope; dispatch on `(intent, flags)`.
- Node-wrapping sub-graphs. Slice-first: ships router + **KB research/triage** sub-agent; others later.
- Tools whitelist (thin boundary, not a service layer); KB/memory scoping via optional filter — no schema change, no tables.
- Routing determinism (fix-the-router table); keep `test_chat_intent`/`handoff`/`cost_guardrails` green.
- Invisible orchestration: end-customer tone/format unchanged.

### Out of Scope
- No checkpointer (D2 correct — per-message rebuild).
- No production panel inbox/chat endpoints (frontend = separate worktree).
- No new DB tables, no M2 web, no M3 payments; no gate-envelope change.
- No sub-agent dispatches in `audit_log` (operational, not business transitions).

## Capabilities

### New Capabilities
- `agent-orchestration`: supervisor router, per-sub-agent dispatch, node-wrapping sub-graphs, tools whitelist boundary, KB/memory scoping, determinism contract.

### Modified Capabilities
- `agent-config` (AC-4/D-A7): schema → multi-agent; enforcement flips "until H2" → orchestrator-enforced (backward-compatible; one-orchestrator test green).

## Approach

**Approach 1 — supervisor-with-subgraphs wins** (ponytail-minimal): gates are a tested envelope; AC-4 deferred to H2; wrap, not replace vetted nodes. Alt (2) separate routing + worker tools: cleanest whitelist, most glue, highest effort; (3) linear graph + intent-only sub-agents: smallest diff, sub-agent model unrealized.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/chat/graph.py`, `state.py` | Modified | `orchestrate` dispatch; extend `ConversationState` |
| `app/chat/nodes/*` | Modified | Wrap; KB retrieval into research sub-graph |
| `app/agent_registry.py` | New | Read-only startup reader on existing loader |
| `prompts.py` | Referenced-only | Registry stays data-only — NOT wired into `prompts.py`/`respond.py` |
| `agent/registry.yaml` | Modified | Multi-agent schema |
| `app/services/kb.py` | Modified | Optional scope filter |

## Risks

| Risk | Mitigation |
|------|------------|
| Checkpointer — H2 doesn't need one | Recorded; not re-litigated |
| Routing determinism | Gate prefix + pure `(intent, flags)` router, table-tested |
| Cost multi-LLM (classify+orchestrator+N) | SQL SUM gate covers all; conservative + blocked escape; re-verify thresholds |
| Registry churn vs AC-4 | Data-only, backward-compatible; one-orchestrator test |

## Rollback Plan

Rollback = git revert of the graph/nodes/registry wiring; no feature flag is introduced (YAGNI). Registry data-only — no DB migration.

## Dependencies

- Archived: `config-agente-lumat`, `panel-h2-advance`; LangGraph StateGraph (existing).

## Success Criteria

- [ ] Router dispatch deterministic + table-tested for all gate/intent combos.
- [ ] KB research/triage performs a scoped, bounded re-query (≤1 retry) with the scope filter; unresolved KB intents reach handoff with the escalation reason — no silent failure.
- [ ] `test_chat_intent`/`test_handoff`/`test_cost_guardrails` stay green.
- [ ] End-customer copy/tone identical on common paths (invisible orchestration).
