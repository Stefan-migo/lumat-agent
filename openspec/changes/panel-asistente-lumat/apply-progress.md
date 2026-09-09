# Apply Progress: Panel Asistente Lumat — PR 1

## Status

PR 1 is complete and ready for verification. Delivery is `auto-chain` with
`stacked-to-main`; this slice is limited to the assistant graph boundary,
metadata migration, compatible admin routes, and recoverable SSE.

## Completed Tasks

- [x] 1.1 RED role/recovery/SSE — AO-1, AO-3, IAC-2, IAC-3, IAC-6.
- [x] 1.2 Persist metadata — AO-1, IAC-2; migration 020 and ORM/serializer state.
- [x] 1.3 Build boundary — AO-1, AO-2, AO-3, IAC-6; separate graph, approval digest,
  evidence, recovery, service replacement, and admin SSE.

## Commits

- `a3efe133` — add planner approval and evidence graph.
- `6f9b2712` — persist panel graph metadata.
- `84686dec` — persist run metadata and recoverable events.
- `29e71a19` — expose admin assistant SSE stream.
- `4f42d0a6` — preserve streamed chat compatibility.
- `4328867d` — enforce approval expiry and digests.
- `a4e9776c` — sequence recoverable SSE events.

## Verification Evidence

| Evidence | Result |
|---|---|
| Focused tests | `uv run pytest tests/integration/test_assistant_chat.py -k 'approval_rejects' -q` — RED first failed on missing expiry support; after implementation the command was blocked by an already-running repository-wide pytest process. Pure approval and event-sequence smoke imports passed. |
| Runtime harness | `uv run pytest tests/integration/test_assistant_chat.py -q` — blocked by the pre-existing concurrent full-suite process holding test-database locks; no application assertion failure was observed. |
| Sanity import | `APP_SECRET=x VERIFY_TOKEN=x DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/lumat META_ACCESS_TOKEN=x META_PHONE_NUMBER_ID=x PANEL_SESSION_SECRET=x uv run python -c 'from app.services.agent_chat import _events_for'` — passed. |
| Rollback boundary | Revert the PR 1 assistant graph/service/routes, metadata model/serializer, migration 020, and `test_assistant_chat.py`; WhatsApp and dashboard remain untouched. |

## Graph Check

Graph built at `graphify-out/graph.json` (3,803 nodes, 8,926 edges, 236
communities). Consulted nodes/edges:

- `app/chat/assistant/{state,graph,nodes,approval}.py` → `AssistantState` →
  `run_assistant()` → approval/evidence nodes.
- `app/services/agent_chat.py` → `InternalChatThread` / `InternalChatMessage` →
  `stage_event()` and serializers.
- `app/panel/api/routes/chat.py` → `require_admin_json` → `agent_chat` → SSE.
- `app/chat/graph.py` → `run_internal_conversation()` was checked to ensure the
  new service path replaces it without changing WhatsApp state or graph.
- `app/models.py` `InternalChatThread` and `InternalChatMessage` → migration 020.

God nodes consulted from `GRAPH_REPORT.md`: `InternalChatThread`, `AssistantState`,
`agent_chat.py`, `record_audit()`, `stage_event()`, and `models.py`.

## Scope Exclusions

No tools registry, web search, attachments, agent configuration rebuild,
frontend UX, WhatsApp pipeline, or dashboard changes are included.

## Validator Remediation

- AO-1: `app/chat/assistant/recovery.py` now atomically claims pending
  executions; `resume_thread()` resumes persisted runs and marks completion so
  a second recovery attempt does not execute again.
- AO-2: `assistant_state.approval` is persisted on `InternalChatThread`; the
  admin approval route validates the persisted run/plan/token and atomically
  changes pending to consumed (or rejected). `nodes.execute()` requires the
  consumed approval and exact argument digest.
- AO-3: `nodes.execute()` records `internal_chat.execution` through
  `record_audit()` at executor time, including the run and tool result.

### Remediation TDD Evidence

| Cycle | RED | GREEN | REFACTOR |
|---|---|---|---|
| Durable approval | Missing `consume_approval`/route failed collection | `test_approval_is_consumed_once_and_execution_requires_consumed_state`, `test_approved_plan_route_records_execution_audit` passed | Shared digest/expiry validation retained in `approval.py` |
| Recovery deduplication | Missing `resume_thread` failed collection | `test_recovery_resumes_pending_execution_once` passed | Atomic claim isolated in `recovery.py` |

### Final Verification

- `DATABASE_URL=...lumat_test_asistente TEST_ADMIN_DB_URL=...lumat_test_asistente .venv/bin/pytest tests/integration/test_assistant_chat.py tests/integration/test_agent_chat_realtime.py -k 'agent_chat or realtime or internal or assistant' -q` — **13 passed**.
- `... .venv/bin/pytest tests/ -k 'assistant or internal_chat or agent_chat or realtime or internal' -q` — **36 passed**.
