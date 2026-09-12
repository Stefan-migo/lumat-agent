## Exploration: panel-cost-gate

### Current State
The WhatsApp graph runs `emergency_gate -> cost_gate -> handoff_gate` before any paid LLM call. `cost_gate` reads per-conversation and UTC-day spend from `app.services.costs`, alerts once per scope/threshold through `audit_log`, and produces `normal`, `conservative`, or `blocked`.

The panel assistant is a separate `AssistantState` graph: `assemble_context -> plan_llm -> guardrails -> execute/respond -> evidence`. Both `plan_llm` and the response branch in `execute` call the configured assistant model, but neither records usage or cost. `guardrails` currently sets `cost_allowed: True` for every path. The panel persistence boundary uses `InternalChatThread` and `InternalChatMessage`; those tables have no numeric cost column and are not part of the `messages` table used by `record_llm_cost`.

`record_llm_cost` accepts only a `message_id`, loads `app.models.Message`, and accumulates into `messages.cost_llm`. It does not accept an `InternalChatThread` or `InternalChatMessage`. `conversation_spend` is therefore not usable for panel threads without inventing a customer conversation. `daily_spend` sums `messages.cost_llm + messages.cost_meta` only. Existing limits are settings-KV keys `cost.conversation_limit` ($1.50 default) and `cost.daily_limit` ($5.00 default); `app/config.py` has no cost-limit fields because operational limits are deliberately stored in the KV service.

The planner receives non-streaming usage (`response.usage.prompt_tokens` / `completion_tokens`) when the provider returns it. The response branch streams chunks and currently has no `stream_options` or final usage handling, so response usage must be requested and captured from the terminal usage chunk. The configured assistant model (`google/gemini-2.5-flash`) is not in `LLM_RATES`; unknown models currently calculate $0, which would make panel spend appear free unless the rate table/configuration is extended.

### Affected Areas
- `app/services/costs.py` — extend the existing cost seam to record/sum internal assistant usage without creating a parallel ledger; preserve WhatsApp behavior and alert deduplication.
- `app/models.py` — `InternalChatMessage` currently lacks a numeric `cost_llm` field; a durable SQL cost column is the smallest reliable schema addition.
- `db/migrations/017_h4_internal_chat.sql` / new migration — add the internal message cost column (and grants remain covered by the table grant).
- `app/chat/assistant/graph.py` — insert a deterministic panel gate after context assembly and before `plan_llm`; blocked must terminate without entering any LLM node.
- `app/chat/assistant/nodes.py` — remove unconditional `cost_allowed: True`, record planner and streamed response usage, and implement concise/block panel behavior without WhatsApp handoff semantics.
- `app/services/agent_chat.py` — the request `InternalChatMessage` is available while the graph runs and is the natural row on which both planner and response costs can accumulate; failed/recovery paths must not duplicate a completed call.
- `app/config.py` and `app/services/settings.py` / panel settings route — assistant model pricing and any panel-specific limit need an explicit configuration decision; current limits are only conversation and daily KV settings.
- `tests/integration/test_cost_guardrails.py`, `tests/integration/test_send_costs.py`, and assistant harness tests — add coverage for internal cost persistence, threshold modes, no-LLM blocking, streaming usage, and alert dedupe.

### Approaches
1. **Reuse `messages` by creating synthetic conversations** — map each panel thread to a fake customer/conversation and call `record_llm_cost` unchanged.
   - Pros: almost no cost-service changes; existing sums and gates work.
   - Cons: corrupts domain meaning, violates the panel/WhatsApp context boundary, pollutes customer data, and makes operator/thread reporting misleading.
   - Effort: Low initially, high long-term risk.

2. **Extend the existing cost service to internal messages** — add `InternalChatMessage.cost_llm`, make the recorder accept the target internal message, sum internal costs in the daily read model, and add a thread-scoped spend helper. Store model and token counts in `assistant_metadata` for audit/debugging while keeping the numeric amount indexed as a column.
   - Pros: one cost service and one durable cost concept; no fake conversations or new ledger table; supports both planner and response calls and UTC daily enforcement.
   - Cons: requires a migration and a small generalization of spend queries; assistant model rates and a panel limit policy must be defined.
   - Effort: Medium.

3. **Create a dedicated LLM usage ledger** — one row per provider call with thread, actor, model, token counts, cost, and status.
   - Pros: best per-call auditability, retries, provider/model rate history, and future reporting.
   - Cons: duplicates the current `messages.cost_llm` ledger, requires broader migration/reporting changes, and is unnecessary for the requested gate.
   - Effort: High.

### Recommendation
Choose Approach 2. Use the request/admin `InternalChatMessage` as the cost record, accumulating both the planner and response calls for one turn. Add a nullable `cost_llm NUMERIC(12,6)` to `internal_chat_messages`; retain `model`, `prompt_tokens`, and `completion_tokens` in `assistant_metadata` (or a bounded per-call list) because those are diagnostic data, not the spend aggregate. Generalize the recorder around a cost-bearing row rather than around `Message` only, and add `internal_thread_spend` plus daily aggregation that includes both WhatsApp and internal rows.

The natural guard scope is **internal thread + global UTC day**: the thread catches a runaway conversation, while the daily cap protects the owner across all WhatsApp and panel usage. Do not add an operator cap in this change; `InternalChatThread.user_id` identifies the actor but the current settings model has no operator limits, and a global daily cap is the existing operational safety boundary. Reuse `cost.daily_limit` for the global cap. If a per-thread cap is required, add a clearly named KV key such as `cost.internal_thread_limit` rather than pretending a panel thread is a customer conversation; this is a settings/API contract decision, not an `app/config.py` environment setting.

Place `panel_cost_gate` between `assemble_context` and `plan_llm`. `normal` continues unchanged. `conservative` permits the LLM but applies a bounded/concise directive to planning and response and records the mode in state. `blocked` returns a deterministic internal message such as “The assistant is temporarily unavailable because the configured usage limit was reached. Please review cost settings.”, marks the run completed/degraded as appropriate, and routes directly to evidence/end; it must not escalate the operator or call a WhatsApp handoff path. The gate should alert on daily/thread threshold crossings using the existing audit-deduped alert mechanism.

For usage, record the planner response immediately after a successful non-streaming completion. Request streaming usage for the response and record the terminal chunk's usage once; do not estimate billable tokens silently. If the provider omits usage, record a diagnostic “usage unavailable” marker and avoid claiming measured spend. Add explicit rates for the active assistant model (or a validated settings-based pricing map); treating unknown models as zero is not acceptable for a cost gate.

### Risks
- **Double counting:** planner and response are two legitimate calls, but each must be recorded exactly once on the request message; retries/recovery must not replay a completed LLM call or append the same usage twice.
- **Missing usage on failure/stream disconnect:** provider failures can leave no usage object; preserve failure state and a diagnostic marker, and do not fabricate precise cost from character estimates.
- **Unknown pricing:** the current assistant model has no `LLM_RATES` entry, so implementation must fail closed for billing configuration or explicitly configure a rate rather than silently recording zero.
- **Alert spam/race conditions:** retain audit-log dedupe for thread/date + threshold; concurrent gates may need a transaction-safe uniqueness strategy if existing deployment concurrency exposes duplicate alerts.
- **Operator lockout:** blocked mode must stop paid calls, not deny panel access, prevent reading threads, or invoke customer-facing escalation.
- **Test-DB side effects:** assistant integration tests share the internal tables and mocked clients; cleanup must truncate internal chat rows/costs and SMTP must remain mocked for threshold tests.
- **Schema/query compatibility:** adding internal rows to daily spend changes the meaning of the existing panel snapshot; tests must verify WhatsApp totals remain unchanged and internal costs are included exactly once.

### Ready for Proposal
Yes. The proposal should commit to a SQL cost column on `InternalChatMessage`, reuse of the existing daily limit and alert mechanism, thread-plus-daily scope, pre-planner gate placement, and explicit assistant-model pricing. It should explicitly defer a dedicated usage ledger, operator-specific caps, and UI redesign beyond exposing the existing spend snapshot.

Graph nodes consulted: `costs.py`, `record_llm_cost()`, `conversation_spend()`, `daily_spend()`, `conversation_cost_state()`, `daily_cost_state()`, `maybe_alert_owner()`, `spend_snapshot()`, `app/chat/nodes/cost_gate.py`, `assistant/graph.py`, `plan_llm()`, `execute()`, `InternalChatThread`, `InternalChatMessage`, `test_cost_guardrails.py`, `test_send_costs.py`, `settings.py`, `get_settings()`.

skill_resolution: cortex-persona and graphify skills were read first; Graphify report was read and query/path checks completed. Directed paths from the file-level assistant graph to costs were absent, so the undirected conceptual path was consulted: `plan_llm() -> nodes.py -> audit.py -> costs.py -> record_llm_cost()`, plus `assistant/graph.py -> nodes.py -> audit.py -> costs.py`. Graph built at commit `c4d13da7`, while this worktree is `e95a2b92`; no rebuild was run because the user required exploration against the existing graph and no code was modified.
