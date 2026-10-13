# ODD — chatbot-assistant-metrics

Feature: `chatbot-assistant-metrics` (Frente 2, unit 1)
Branch: `odd/chatbot-assistant-metrics` · Base: `main` = `38b9ed15`

## Objective

Give the panel assistant a **read-only** tool `analytics.chatbot_metrics` that reports how
the WhatsApp bot is performing over a bounded time window, so the assistant can read →
analyze → propose improvements to the bot.

## Problem / Why

Frente 2 makes the Lumat panel assistant an optimizer of the WhatsApp chatbot. Unit 1 is
the **read** layer for bot performance. Today the assistant can read the panel KPI summary
(`dashboard.summary`) but has no bot-specific metrics: containment, deflection, unknown
intents, turns-to-resolve, KB hit-rate, cost per conversation.

## Scope

**In:** one read-only tool + its analytics aggregate service + registry / whitelist / role
wiring + tests.

**Out (later units):** conversation inspection (2), N1-2 approval loop (3), prompt PRs (4),
UI (5).

## Data sources — verified against code, no new instrumentation

| Source | Fields | Used for |
|---|---|---|
| `Message` | `conversation_id`, `direction=inbound`, `created_at` | contacts, turns |
| `ConversationEvent` | `event`, `cause`, `created_at` | handoffs, unknown intents, KB |
| `Conversation` | `state`, `closed_at` | resolved conversations |
| `Case` | `escalated_at` | handoff cross-check |
| `app/services/costs.py::conversation_spend` | — | cost per conversation |

Persisted `ConversationEvent.event` vocabulary (authoritative): `classified`,
`kb_retrieved`, `escalation` (`app/services/realtime.py:17` `ACTIVITY_EVENTS`), plus
`emergency`, `unknown_intent`, `state_change` written directly. **Never invent event
names** — grep the writers before adding a query.

KB activity: `record_activity(..., "kb_retrieved", cause="chunks:N")`
(`app/chat/subgraphs/research_triage.py:88-94`).
Escalation: `record_activity(..., "escalation", cause="handoff:<reason>", actor="rule")`
(`app/chat/nodes/handoff.py:88-94`), so the escalation **reason** is persisted in `cause`.

## Metric definitions of record

Window: `start = now(utc) - timedelta(days=window_days)`, mirroring
`dashboard.compute_kpis`. Rates are floats rounded to 4 decimals; **`null` means "no data",
never `0`**.

1. `conversations` — distinct inbound conversation ids in window (int).
2. `handoffs` — distinct conversations with an `escalation` event in window (int).
3. `handoff_rate` — `handoffs / conversations`, `0.0` when none.
4. `containment_rate` — `1 - handoff_rate`.
5. `handoff_reasons` — `{reason: count}`, reason parsed from `cause` `handoff:<reason>`.
6. `unknown_intents` — count of `unknown_intent` events in window (int).
7. `kb_hits` / `kb_misses` / `kb_hit_rate` — `kb_retrieved` events, `escalation` events with
   `cause = "handoff:kb_miss"`, and `kb_hits / (kb_hits + kb_misses)` (`null` when both 0).
8. `turns_to_resolve` — avg inbound messages per conversation with `Conversation.closed_at`
   in window (`null` when none closed).
9. `cost_per_conversation` — avg `costs.conversation_spend` over the window's conversations
   (`null` when none).
10. `window_days` — echo of the requested window.

## Tasks

| ID | Task | Route |
|---|---|---|
| T1 | RED: unit tests for `chatbot_metrics` over a seeded DB (each metric + null cases) | inline (writer) |
| T2 | GREEN: `app/services/analytics.py::chatbot_metrics(session, window_days)` | delegated |
| T3 | RED+GREEN: `analytics.chatbot_metrics` registered in `TOOL_REGISTRY` (read_only, tier `default`, args schema) | delegated |
| T4 | Wire: `ROLE_TOOL_ALLOWLIST` (ADMIN + OPERADOR) and `agent/registry.yaml` `assistant.tools_whitelist` | delegated |
| T5 | Update `tests/unit/test_tool_tiers.py` `DEFAULT_TOOLS`; confirm roles/capabilities/whitelist suites | delegated |

Single writer; each task closes with one work-unit commit.

## Constraints (verified)

- **Strict TDD ON** — source `openspec/config.yaml:28` (`apply.tdd=true`), `:38`
  (`strict_tdd: true`). Runner: `uv run pytest tests/`. RED before implementation.
- Adding a tool breaks `tests/unit/test_tool_tiers.py` (exact default/opt-in sets) and must
  be reflected in `ROLE_TOOL_ALLOWLIST`; `tests/unit/test_assistant_tool_roles.py` derives
  ADMIN/OPERADOR from `TOOL_REGISTRY` and keeps TECNICO explicit.
- Tool must be in `TOOL_REGISTRY` **and** `assistant.tools_whitelist` or the catalog drops it.
- `read_only=True` → no approval path, no write tier.
- Keep the handler deferring panel-coupled imports inside the function, mirroring `_kpis`
  (`registry.py:367`).
- Test DB: `infra/.env` copied into the worktree; `infra/test-db.sh up`.

## Acceptance criteria

- AC-1: `chatbot_metrics` returns every metric above over a seeded window.
- AC-2: metrics with an empty window return `0` counts and `null` rates/avgs.
- AC-3: `analytics.chatbot_metrics` appears in `tool_schemas()` and in the assistant
  whitelist; tier is `default`; `read_only` is True.
- AC-4: `uv run pytest tests/ -q` green.

## Checks

- `uv run pytest tests/ -q`
- Targeted: `uv run pytest tests/unit/test_tool_tiers.py tests/unit/test_assistant_tool_roles.py tests/unit/test_assistant_tools.py -q`

## Graph nodes consulted

`Registry`, `Assistant`, `ToolValidationError`, `execute_tool()`, `get_tool()`,
`test_tool_registry_declares_exact_default_and_opt_in_tiers()`, `is_tool_whitelisted()`,
`resolve_delegation_scope()`, `load_registry()` — community `registry.py` /
`agent_registry.py` / `test_assistant_delegation.py`.

## Progress

- [ ] T1 · [ ] T2 · [ ] T3 · [ ] T4 · [ ] T5

## Next step

Implement T1–T5 in the worktree, then run the checks; do not start unit 2.
