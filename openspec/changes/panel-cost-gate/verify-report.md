```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:3f66792dd6bfbf3396ed4477adff1d55b45da2627f2982b3936127fd5b1f04ec
verdict: fail
blockers: 2
critical_findings: 2
requirements: 1/3
scenarios: 13/14
test_command: DATABASE_URL='postgresql+psycopg://app:app@localhost:5434/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5434/lumat' uv run pytest tests/
test_exit_code: 0
test_output_hash: sha256:2a305f032a080462475aecde8a14198cfa359937c1bf7931bc95fbfa9a17211b
build_command: cd web && npm run build
build_exit_code: 127
build_output_hash: sha256:1903a8e0a26dd04894e01abe157d0f2af28b52e5d840c4b7b819dbdf8f8390bd
```
## Verification Report

**Change**: `panel-cost-gate`  
**Mode**: Strict TDD  
**Artifact store**: both  
**Evidence revision**: commit `440d02b3`

### Completeness
| Metric | Result |
|---|---:|
| Tasks | 11/11 complete |
| Requirements | 1/3 fully compliant |
| Scenarios | 13/14 fully compliant |
| Graph check | Passed |

### Build and tests
- **Tests**: PASS — 706 passed, 0 failed, 1 existing RuntimeWarning; exit 0.
- **Build**: FAIL — `cd web && npm run build` exits 127: `tsc: command not found`.
- **Coverage**: Not configured (`coverage_threshold: 0`).

### Requirement compliance
| Requirement | Result | File:line evidence |
|---|---|---|
| IAC-2 Context Boundary | PARTIAL | Gate/wiring: `app/chat/assistant/graph.py:24-45`; modes and blocked reply: `app/chat/assistant/nodes.py:155-193`; usage: `app/chat/assistant/nodes.py:138-152`. Terminal stream accounting has CRITICAL-1. |
| IAC-3 Panel States | COMPLIANT | Blocked persistence: `app/chat/assistant/nodes.py:162-185`, `app/services/agent_chat.py:237-271`; reconnect authority: `app/services/agent_chat.py:324-325`. |
| SS-3 Cost Guardrails | PARTIAL | Schema: `db/migrations/023_panel_cost_llm.sql:3-7`; lock/idempotency/pricing: `app/services/costs.py:57-118`; aggregation: `app/services/costs.py:121-164`; terminal usage defect is CRITICAL-1. |

### Scenario compliance matrix
| Requirement | Scenario | Covering test | Result |
|---|---|---|---|
| IAC-2 | History-aware assistant response | `tests/integration/test_assistant_chat.py::test_planner_and_terminal_stream_usage_are_persisted_once` | PARTIAL — planner asserted; terminal cost not asserted and implementation has CRITICAL-1. |
| IAC-2 | Conservative mode | `tests/integration/test_assistant_harness_guardrails.py::test_cost_gate_injects_conservative_directive_after_context`; `::test_conservative_directive_is_added_to_planner_user_prompt` | COMPLIANT |
| IAC-2 | Blocked mode | `tests/integration/test_assistant_chat.py::test_blocked_cost_gate_persists_canned_reply_without_llm`; `tests/integration/test_assistant_harness_guardrails.py::test_cost_gate_blocked_never_invokes_planner` | COMPLIANT |
| IAC-2 | Unknown pricing or usage | `tests/integration/test_cost_guardrails.py::test_unknown_model_records_zero_and_diagnostic`; `::test_missing_usage_is_zero_but_diagnostic_is_persisted` | COMPLIANT |
| IAC-2 | Operator denied | `tests/integration/test_assistant_chat.py::test_operator_cannot_read_assistant_stream` | COMPLIANT |
| IAC-3 | Approval recovery | `tests/integration/test_assistant_chat.py::test_pending_plan_survives_thread_reload` | COMPLIANT |
| IAC-3 | Processing recovery | `tests/integration/test_assistant_chat.py::test_failed_run_does_not_persist_partial_response` | COMPLIANT |
| IAC-3 | Blocked recovery | `tests/integration/test_assistant_harness_session.py::test_blocked_state_is_persisted_as_completed_and_recoverable` | COMPLIANT |
| IAC-3 | Stream failure | `tests/integration/test_assistant_chat.py::test_stream_disconnect_keeps_known_usage_and_failed_request`; `tests/integration/test_assistant_harness_session.py::test_reconnect_uses_persisted_events_as_authority` | COMPLIANT for state/reconnect; cost caveat CRITICAL-1 |
| SS-3 | Internal thread limit | `tests/integration/test_cost_guardrails.py::test_internal_thread_spend_is_scoped_to_one_thread`; `tests/integration/test_assistant_harness_guardrails.py::test_cost_gate_injects_conservative_directive_after_context` | COMPLIANT |
| SS-3 | Combined daily limit | `tests/integration/test_cost_guardrails.py::test_daily_spend_combines_whatsapp_and_internal_once`; `::test_daily_cost_state_blocked_at_100` | COMPLIANT |
| SS-3 | Usage recorded once | `tests/integration/test_assistant_chat.py::test_planner_and_terminal_stream_usage_are_persisted_once`; `tests/integration/test_cost_guardrails.py::test_internal_cost_call_key_is_idempotent_under_concurrent_retry` | FAILING — first usage-less stream chunk claims response key; terminal usage is discarded. |
| SS-3 | Unknown model pricing | `tests/integration/test_cost_guardrails.py::test_unknown_model_records_zero_and_diagnostic` | COMPLIANT |
| SS-3 | WhatsApp non-regression | `tests/integration/test_assistant_chat.py::test_rejected_approval_only_leaves_planner_cost_and_preserves_whatsapp_totals`; `tests/integration/test_cost_guardrails.py::test_daily_spend_combines_whatsapp_and_internal_once`; `tests/integration/test_send_costs.py` | COMPLIANT — no WhatsApp production files changed; `messages.cost_llm`/`cost_meta` aggregation remains separate at `app/services/costs.py:121-164`. |

### Required assertions
- **Exact-once accounting**: row lock and call-key dedupe are present at `app/services/costs.py:71-117`; concurrent retry passed. Blocked bypasses planning at `app/chat/assistant/graph.py:24-25`; denied/expired approvals reject before execution at `app/chat/assistant/nodes.py:277-295`; planner-only approval tests passed. Terminal stream accounting is not exact for an initial usage-less chunk (CRITICAL-1).
- **Pricing honesty**: unknown model and absent usage produce zero plus diagnostics at `app/services/costs.py:82-118`; tests passed.
- **WhatsApp non-regression**: no WhatsApp production file changed in `e95a2b92..440d02b3`; separate sums are at `app/services/costs.py:121-164`; regression tests passed.

### Design coherence and deferred boundaries
| Boundary/decision | Result | Evidence |
|---|---|---|
| No dedicated ledger | PASS | Message columns/metadata only: `app/services/costs.py:121-164`. |
| No per-operator caps | PASS | Thread/global settings only: `app/services/settings.py:102-110`. |
| No synthetic conversations | PASS | Internal rows are queried directly: `app/services/costs.py:138-164`. |
| No UI | PASS (scope) | No web source changes; build attempted, toolchain missing. |
| Approval lifecycle unchanged | PASS | Existing pending/consumed validation: `app/chat/assistant/approval.py:32-72`; no approval source diff. |
| Strict TDD RED → GREEN | PASS (reported evidence) | `apply-progress.md:24-38` records RED/GREEN for all phases; current full suite passed. |

### Graph evidence
Nodes consulted: `AssistantState`, `assistant/state.py`, `assistant/graph.py`, `nodes.py`, `assemble_context()`, `panel_cost_gate`, `plan_llm()`, `execute()`, `internal_thread_cost_state()`, `daily_cost_state()`, `maybe_alert_owner()`, `record_llm_cost()`, `agent_chat.py`, `stream_events()`, `recover_events()`, `test_cost_guardrails.py`, `test_assistant_chat.py`, `test_assistant_harness_session.py`. Edges: `state.py → graph.py → nodes.py`; `assemble_context() → panel_cost_gate → plan_llm → guardrails → execute`; `agent_chat.py → run_assistant() → plan_llm()/execute()`; `stream_events() → recover_events()`; `nodes.py → record_llm_cost() → InternalChatMessage`; `costs.py → daily_spend()/maybe_alert_owner()`.

### Issues
**CRITICAL**
1. **CRITICAL-1** — `app/chat/assistant/nodes.py:384-386` calls `_record_usage(state, "response", chunk)` for every stream chunk. `app/services/costs.py:78-81` claims the call key on the first chunk. If that chunk has `usage=None`, it persists zero/`usage_unavailable`; the later terminal usage chunk is a duplicate and is ignored. This violates terminal usage accumulation and exact-once accounting. The passing test does not assert response cost.
2. **CRITICAL-2** — configured build command exits 127 because `tsc` is unavailable.

**WARNING**
1. Existing unrelated `RuntimeWarning` in `tests/integration/test_webhook_ingest.py::test_startup_sweep_reprocesses_received`.

**SUGGESTION**
1. Add a regression assertion for terminal response `cost_llm` and make only the terminal usage chunk claim the response key.

### Verdict
**FAIL** — full pytest passes, but one required accounting scenario is substantively broken and the configured build command fails.
