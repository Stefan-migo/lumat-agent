# Design: Panel Assistant Cost Gate

## Technical Approach

Extend the existing cost seam without synthetic WhatsApp rows. Each request
message owns measured spend; the graph adds a pre-planning gate with normal,
conservative, and blocked modes.

## Architecture Decisions

| Decision | Choice | Alternatives / rationale |
|---|---|---|
| Cost ownership | Add `InternalChatMessage.cost_llm`; accumulate planner and response calls there. | A ledger or fake `Message` pollutes WhatsApp data. |
| Spend aggregation | `daily_spend` sums WhatsApp columns plus internal `cost_llm` separately. | Separate sums prevent double-counting and preserve byte-identical WhatsApp behavior. |
| Exact once | In the caller transaction, `record_llm_cost` executes `SELECT ... FOR UPDATE` on the request row, checks `assistant_metadata.cost_calls[call_key]`, and updates cost plus metadata before releasing the lock. | The row lock serializes concurrent retries/reconnects; a committed call key becomes a no-op. |
| Pricing | Read settings-KV `cost.llm_rates` keyed by model; its default documents provider source/effective date. Unknown model or usage contributes zero plus a diagnostic. | Configurable rates avoid stale hardcoded prices. |

## Data Flow

`submit_message` sets `request_message_id` → `assemble_context` →
`panel_cost_gate` reads thread/day KV limits and alerts → `plan_llm` records
non-streaming usage → `guardrails` → `execute` records terminal stream usage →
`agent_chat` persists request metadata and response.

Planner usage is recorded after successful completion, even if parsing falls
back. Streaming requests usage (`stream_options`) and captures one terminal
chunk. The lock-and-call-key guard shares the accumulation transaction.
Failure/disconnect records only known usage/diagnostics; never fabricates cost.

## File Changes

| File | Action | Description |
|---|---|---|
| `db/migrations/023_panel_cost_llm.sql` | Create | Add nullable `cost_llm NUMERIC(12,6)` to `internal_chat_messages`; retain app grants. Rollback: controlled `ALTER TABLE ... DROP COLUMN` after disabling gate. |
| `app/models.py` | Modify | Map nullable `InternalChatMessage.cost_llm` as `Decimal`. |
| `app/services/costs.py` | Modify | Generalize recording, thread spend, combined UTC-day sum, and pricing diagnostics; leave WhatsApp behavior intact. |
| `app/chat/assistant/{state,graph,nodes}.py` | Modify | Add request/cost state, gate edge, conservative prompt directive, blocked node, planner/stream accounting. |
| `app/services/agent_chat.py` | Modify | Pass request ID, persist metadata, and keep recovery/retry idempotent. |
| `app/services/settings.py` | Modify | Keep `cost.conversation_limit` as the one internal-thread scope and add configurable `cost.llm_rates` defaults with source/effective-date documentation. |
| `tests/integration/test_cost_guardrails.py`, `tests/integration/test_assistant_chat.py`, `tests/integration/test_migrations.py`, `tests/integration/test_assistant_harness_guardrails.py`, `tests/integration/test_assistant_harness_session.py`, `tests/unit/test_assistant_planner.py` | Modify | RED-first migration, aggregation, gate, usage, failure, and recovery tests. |

## Interfaces / Contracts

```python
record_llm_cost(session, *, target, call_key, model, prompt_tokens, completion_tokens)
# SELECT FOR UPDATE target; returns Decimal; updates cost and metadata atomically
```

The gate sets `cost_mode: Literal["normal", "conservative", "blocked"]` and
`cost_directive` in `AssistantState`. `cost.conversation_limit` limits one
internal thread; `cost.daily_limit` is global UTC-day spend. Thresholds are
`<80% normal`, `80–<100% conservative`, `>=100% blocked`; worst wins.
`maybe_alert_owner` handles each crossing.

Conservative appends “Answer concisely; use the minimum necessary context and
avoid optional tool calls.” to both user prompts, not the persona. Blocked
routes to `blocked_reply` then evidence, and persists:
“The assistant is temporarily unavailable because the configured usage limit
was reached. Please review cost settings.” The operator remains authorized to
read/use the panel; only paid assistant calls are short-circuited. This is an
ordinary assistant message through the existing `agent_chat.py` persistence and
`stage_event` realtime path, with no new UI. It renders/reconnects normally and
can be retried after the block. Operator approval/denial remains the
pre-existing `app/chat/assistant/approval.py` lifecycle (`pending → consumed`);
this change does not alter it. For denied, expired, or never-approved
approvals, only an already-completed planner call is charged and the
un-executed tool costs nothing; a turn that never reached an LLM costs nothing.
Resume/reconnect reuses the same call key and cannot double-charge.

## Testing Strategy

Strict TDD: add failing tests first; run
`DATABASE_URL='postgresql+psycopg://app:app@localhost:5434/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5434/lumat' uv run pytest tests/`.
Cover migration/type, concurrent exact-once usage, unknown/missing diagnostics,
failure/disconnect, thread/day modes, alert dedupe, blocked no-call persistence,
conservative text, WhatsApp non-regression, and recovery retry. No E2E/UI work.

## Threat Matrix

| Boundary | Status | Safe/failure behavior and RED test |
|---|---|---|
| Assistant routing | Applicable | Gate can reach only planner or blocked reply; blocked never reaches an LLM (`test_blocked_bypasses_llm`). |
| Shell/subprocess | N/A — none introduced | — |
| VCS/PR automation | N/A — none introduced | — |
| Executable classification | N/A — none introduced | — |
| Process integration | N/A — no new process boundary | — |

## Migration / Rollout

Apply migration 023 first. Disable the gate to roll back behavior; the nullable
column may remain or be dropped in a controlled down migration.

## Open Questions

None. `cost.conversation_limit` is the internal-thread limit, and pricing is
the configurable `cost.llm_rates` map whose default documents provider source
and effective date.

## Non-Goals and Deferrals

No dedicated ledger, synthetic conversations, operator caps, cost UI, WhatsApp
changes, or pricing history. Per-call history, operator budgets, and UI
redesign are deferred.

Ponytail design cuts: `delete:` dedicated ledger and synthetic conversations;
`yagni:` operator caps and pricing-history abstraction; `shrink:` reuse the
existing cost service, KV limits, audit dedupe, and evidence path instead of
new layers. net: -4 items cut from plan.
