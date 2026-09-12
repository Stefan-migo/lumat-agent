# Proposal: Panel Assistant Cost Gate

## Intent

Panel calls lack durable spend records and bypass existing guardrails. Extend the cost seam so panel usage is measurable and bounded without contaminating WhatsApp data.

## Scope

### In Scope
- Add nullable `cost_llm NUMERIC(12,6)` to `InternalChatMessage` through migration `023` and ORM mapping.
- Accumulate planner and terminal response usage on the request message; include internal spend in UTC-day totals once.
- Gate after `assemble_context`, before `plan_llm`, using `cost.conversation_limit`, `cost.daily_limit`, and `maybe_alert_owner`.
- Implement `normal`, concise-directive `conservative`, and deterministic canned-reply `blocked`; blocked stops LLM calls but not panel access.
- Make pricing explicit; unknown models or absent usage record zero plus a diagnostic, never fabricated cost.

### Out of Scope
- Dedicated ledger/table, synthetic WhatsApp conversations, per-operator caps, cost UI, or WhatsApp cost changes.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `internal-agent-chat`: measured cost, pre-planner gate, persisted blocked reply.
- `settings-scope-limits`: guardrails include thread and combined daily spend.

## Approach

Generalize `app/services/costs.py` for WhatsApp and internal rows, adding thread spend and combined daily aggregation while retaining alert deduplication. Insert `panel_cost_gate` in the graph. Capture both calls once, storing model/token diagnostics in `assistant_metadata` and accumulating them on the request row through `agent_chat.py`.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `app/services/costs.py` | Modified | Recording, thread/day aggregation, pricing diagnostics. |
| `app/chat/assistant/{graph,nodes}.py` | Modified | Gate, modes, usage. |
| `app/services/agent_chat.py` | Modified | Request-row accumulation and persistence. |
| `app/models.py`, `db/migrations/023_panel_cost_llm.sql` | Modified/New | Cost column. |
| `tests/integration/*`, assistant tests | Modified | Persistence, thresholds, streaming. |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Duplicate/missing usage | Med | Record completed calls once; preserve diagnostics. |
| Unknown pricing | High | Explicit rate map; diagnostic zero until configured. |
| Alert races | Med | Reuse audit dedupe and test repeated crossings. |

## Rollback Plan

Disable the panel gate and restore prior aggregation. The nullable column may remain or be removed with a controlled down migration.

## Dependencies

- Active-model rate and existing settings-KV limits.

## Success Criteria

- [ ] Both calls persist exactly once on the request message.
- [ ] Thread/day modes include panel spend; WhatsApp totals do not change.
- [ ] Blocked mode makes no LLM call and persists an internal reply.

## Proposal question round

Confirm: conversation limit means one internal thread; daily limit is global; diagnostics are the only unknown-pricing surface.

## Ponytail cuts

- Dedicated ledger: deleted; existing message columns suffice.
- Synthetic WhatsApp conversations: deleted; domains stay separate.
- Per-operator caps: deferred; no policy/settings contract exists.
- Cost UI: deleted; retain the existing spend snapshot only.
