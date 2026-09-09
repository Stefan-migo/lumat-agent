# Apply Progress: Panel Asistente Lumat — PR 3

## Status

PR 1, PR 2, and PR 3 are complete and ready for verification. Delivery is
`auto-chain` with `stacked-to-main`; PR 3 is limited to frontend assistant chat
lifecycle UX. Attachments upload UI remains in PR 5.

Validator remediation is complete: PR 3 now supports explicit thread recovery,
stream-owned processing state, and the complete serialized approval contract.

## Completed Tasks

- [x] 1.1 RED role/recovery/SSE — AO-1, AO-3, IAC-2, IAC-3, IAC-6.
- [x] 1.2 Persist metadata — AO-1, IAC-2; migration 020 and ORM/serializer state.
- [x] 1.3 Build boundary — AO-1, AO-2, AO-3, IAC-6; separate graph, approval digest,
  evidence, recovery, service replacement, and admin SSE.
- [x] 2.1 RED tool security — AT-1, AT-2, AT-3, AR-7; typed validation, approval
  mismatch rejection, and bounded web adapter tests.
- [x] 2.2 Registry/executor — AT-1, AT-3, AO-2; direct-service reads, bounded
  results, JSON schemas, and graph executor dispatch.
- [x] 2.3 Automation audit — AT-2, AR-6/7, AO-3; assistant writes require an
  executor-origin marker and retain the existing audit/worker path.
- [x] 3.1 RED UI states — IAC-3/6; component RED tests cover streamed plan,
  evidence, approval/rejection, and recovery after reload; Storybook covers
  approval, evidence, and streaming states.
- [x] 3.2 Render lifecycle — IAC-2/3/6; typed plan/approval/evidence/events,
  fetch ReadableStream SSE consumption, plan controls, evidence cards, and
  persisted recovery rendering.

## Commits

- `a3efe133` — add planner approval and evidence graph.
- `6f9b2712` — persist panel graph metadata.
- `84686dec` — persist run metadata and recoverable events.
- `29e71a19` — expose admin assistant SSE stream.
- `4f42d0a6` — preserve streamed chat compatibility.
- `4328867d` — enforce approval expiry and digests.
- `a4e9776c` — sequence recoverable SSE events.
- `726aaa4b` — add assistant chat lifecycle UX.

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

No tools registry, web search, attachments upload UI, agent configuration
rebuild, WhatsApp pipeline, or dashboard changes are included in PR 3.

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

### PR 2 Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused tests | `DATABASE_URL=... TEST_ADMIN_DB_URL=... .venv/bin/pytest tests/unit/test_assistant_tools.py tests/integration/test_assistant_chat.py tests/integration/test_agent_chat_realtime.py -q` — **17 passed**. |
| Runtime harness | Assistant integration path executed against isolated `lumat_test_asistente`; existing PR 1 assistant/realtime contracts passed. Full requested `pytest tests/ -k "assistant or tools or automation or agent_chat" -q` remains to be run by verify with the isolated DB. |
| Rollback boundary | Revert `app/chat/assistant/tools/`, `app/chat/assistant/nodes.py`, `app/services/automation.py`, and `tests/unit/test_assistant_tools.py`; no WhatsApp, dashboard, or infra files changed. |

### PR 2 TDD Evidence

| Task | RED | GREEN | REFACTOR |
|---|---|---|---|
| 2.1 Tool security | Missing tools registry caused collection failure | Unit validation/approval/bounds tests pass | Shared typed definitions and bounded result conversion retained |
| 2.2 Registry/executor | Unknown registry import failed collection | Direct-service registry and graph dispatch pass focused suite | Aliased list/search names share one minimal handler |
| 2.3 Automation audit | Assistant-origin guard absent | Executor-origin assistant creation path and existing audit contracts pass | Existing panel actor behavior unchanged |

### Migration Decision

No `021_assistant_approvals.sql` was created. PR 1 already persists approval
state on `InternalChatThread` metadata and provides atomic conditional
consume-once validation; a second approval table would duplicate persistence
without adding required capability.

## PR 2 Graph Check

Consulted `GRAPH_REPORT.md` (3,803 nodes, 8,926 edges; built from PR 1
baseline) and queried:

- `AssistantState` → `assistant/graph.py` → `assistant/nodes.py` → approval/evidence.
- `create_rule()` → `AutomationRule` → `record_audit()` → worker/domain events.
- `customers.py`, `conversations.py`, `scheduling.py`, `cases.py`, `kb.py`, and
  `dashboard.py` service/model hubs.

No graph refresh was run mid-session; the graph remains the PR 1 baseline as
required by the project session policy.

## PR 3 TDD Evidence

| Task | RED | GREEN | REFACTOR |
|---|---|---|---|
| 3.1 UI states | Added failing lifecycle/approval/SSE tests before production changes | `AgentChat.test.tsx` and Storybook state tests pass | Reused Card, Badge, Button, and existing chat fixtures; no new dependency |
| 3.2 Render lifecycle | Component suite initially failed on absent SSE rendering/approval controls | Typed SSE parser, reducer-style event handling, plan/evidence cards, and recovery pass | Kept fetch ReadableStream local to `api.ts`; no state library or SSE package |

## PR 3 Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused tests | `npm test -- --run src/components/pages/AgentChat.test.tsx src/stories/pages/ChatWithAgent.stories.test.tsx` — **2 files passed, 14 tests passed**. |
| Runtime harness | Storybook lifecycle harness via `ChatWithAgent.stories.test.tsx` — **6 tests passed**; mocked fetch SSE path exercises plan → tool → evidence → response rendering. |
| Typecheck | `npx tsc --noEmit` — **passed**. |
| Frontend suite | `npm test` — **69 files passed, 490 tests passed**. |
| Build sanity | `npm run build` — **passed**, Vite production bundle generated. |
| Backend regression | `DATABASE_URL="postgresql+psycopg://app:app@localhost:5432/lumat_test_asistente" TEST_ADMIN_DB_URL="postgresql://lumat:lumat@localhost:5432/lumat_test_asistente" .venv/bin/pytest tests/integration/test_assistant_chat.py -q` — **10 passed**. |
| Rollback boundary | Revert commit `726aaa4b` for `web/src/{api.ts,types.ts,components/pages/AgentChat.tsx,components/pages/AgentChat.test.tsx,stories/pages/ChatWithAgent.stories.tsx}`; no backend, dashboard, WhatsApp, infra, or attachment files changed. |

## PR 3 Graph Check

Graph baseline: `graphify-out/graph.json` from `4f42d0a6`; no refresh was run
mid-session. Consulted before the task and before each affected module:

- `AgentChat()` → `createChatThread()` / `getChatThread()` / `sendChatMessage()`
  → `api.ts` frontend API client.
- `stream_events()` → `recover_events()` → `InternalChatThread` for event
  payload and persisted recovery shape.
- `stream_thread()` → `stream_events()` for the dedicated SSE route.
- `ChatWithAgent.stories.tsx` → `PlanCard()` → `Button()` / `Card()` / `Badge()`
  for Storybook primitive reuse.
- `types.ts` frontend API client community and `Agent Chat UI` community.

God nodes consulted: `InternalChatThread`, `agent_chat.py`, `stage_event()`,
`models.py`; communities: Frontend API Client, Recovery Helpers, Agent Chat UI,
Shared UI Components, Frontend Test & Storybook Deps.

## PR 3 Validator Remediation

| Gap | Fix | Test |
|---|---|---|
| Persisted thread recovery | `AgentChat` accepts `threadId` and reads `?thread_id=`; GET restores plan, approval, evidence, lifecycle, events, and active run, reconnecting recoverable streams | `recovers a persisted plan by thread id without creating a new thread` — passed |
| Stream-owned processing | Removed request `finally` reset and response-event reset; `openStream` clears processing only after ReadableStream completion or error | `keeps processing until the SSE stream closes` — passed |
| Approval contract | `AssistantApproval` mirrors backend token hash, tool, arguments, argument hash, expiry, status, and consumed timestamp fields | TypeScript compile-time fixture in `AgentChat.test.tsx` — passed |

### Remediation Evidence

| Evidence | Result |
|---|---|
| Focused tests | `npm test -- --run src/components/pages/AgentChat.test.tsx` — **1 file passed, 10 tests passed**. |
| Full frontend | `npm test` — **69 files passed, 492 tests passed**. |
| Typecheck | `npx tsc --noEmit` — **passed**. |
| Build | `npm run build` — **passed**. |
| Backend regression | Isolated `tests/integration/test_assistant_chat.py -q` — **10 passed**. |
| Rollback boundary | Revert the remediation commit affecting `AgentChat.tsx`, `AgentChat.test.tsx`, `types.ts`, and this progress artifact; prior PR 3 behavior and all backend/WhatsApp/dashboard boundaries remain intact. |

## Validator Remediation — PR 2

- Conversations now use `app.services.conversations.list_conversations`; appointments
  use `app.services.scheduling.list_for_range`. Registry handlers no longer query
  those models directly.
- Added bounded `memory.read` through `app.services.memory.list_for_entity`, with
  scope/entity/topic validation and a maximum of 20 results.
- `DuckDuckGoSearch` raises `SearchFailure` for network/malformed responses;
  `execute_tool` converts it to explicit error evidence while valid no-hit results
  remain completed with an empty result.
- Approval rejection now appends error evidence and records
  `internal_chat.execution_rejected` before raising. The persisted agent-chat
  failure event includes that evidence.

### Remediation TDD Evidence

| Gap | RED | GREEN | REFACTOR |
|---|---|---|---|
| Service-backed reads | Registry service-seam test failed because handlers used raw SQL | Conversation and appointment seam tests pass | Read query ownership remains in existing service modules |
| Memory read | Import/registry test failed because no memory tool existed | Bounded `memory.read` test passes | Reused `list_for_entity`; no new memory abstraction |
| Web failure evidence | `SearchFailure` import/test failed | Search failure returns explicit error evidence; valid empty remains distinct | Provider adapter keeps one replaceable interface |
| Approval evidence | Approval test observed `PermissionError` without evidence | State, exception, audit, and persisted failure event carry error evidence | Existing consume-once approval validation unchanged |

### Remediation Verification

| Evidence | Result |
|---|---|
| Focused tests | `... .venv/bin/pytest tests/unit/test_assistant_tools.py tests/integration/test_assistant_chat.py tests/integration/test_agent_chat_realtime.py -q` — **21 passed**. |
| Runtime harness | `... .venv/bin/pytest tests/ -k 'assistant or tools or automation or agent_chat' -q` — **33 passed**. |
| Sanity import | Settings-backed import of `tool_schemas()` and `build_assistant_graph()` — **13 tools, CompiledStateGraph**. |
| Rollback boundary | Revert service seam additions, registry/search/nodes/agent-chat remediation, tests, and this progress section; no infra, dashboard, or WhatsApp files involved. |

## Verify Remediation — PR 2

- Web search now validates the HTML document shape and every result candidate;
  missing document structure or unsafe result URLs raise `SearchFailure` and
  become error evidence through the registry. Valid no-hit HTML remains an
  empty successful result.
- Added an isolated-DB runtime test covering approval consumption, real
  `automation.create_rule(... actor="assistant", executor_origin=True)`, rule
  listing alongside a UI-created rule, audit actor/history, and worker event
  evaluation.
- H4 cleanup and test database fallbacks now derive the admin URL from
  `DATABASE_URL` when `TEST_ADMIN_DB_URL` is absent. No cleanup path targets
  the hardcoded default database.

### Verify Remediation Evidence

| Evidence | Result |
|---|---|
| Focused tests | `... .venv/bin/pytest tests/integration/test_assistant_chat.py tests/unit/test_assistant_tools.py tests/integration/test_agent_chat_realtime.py tests/integration/test_h4_automations.py -q` — **27 passed**. |
| Runtime harness | `... .venv/bin/pytest tests/ -k 'assistant or tools or automation or agent_chat' -q` — **35 passed**. |
| Malformed search test | Unsafe DDG result HTML raises `SearchFailure`; registry failure evidence path remains covered. |
| Runtime automation test | `tests/integration/test_assistant_tools.py::test_approved_assistant_rule_is_persisted_audited_and_worker_visible` — passed against isolated PostgreSQL. |
| Database isolation | `tests/conftest.py`, `tests/integration/conftest.py`, and H4 cleanup derive `postgresql://` admin URL from configured `DATABASE_URL`; no hardcoded cleanup URL remains in the exercised paths. |

## Verify Remediation Follow-up

- H4 worker and notification cleanup fixtures were also switched to the same
  derived `ADMIN_DB_URL`, preventing adjacent H4 suites from cleaning the
  default database when the isolated admin URL is omitted.
- Final requested verification: focused assistant/tools/realtime/H4 suite
  **27 passed**; related assistant/tools/automation/agent-chat selection
  **35 passed**; H4 worker/notification isolation suites **12 passed**.

Graph checks consulted the assistant search/evidence path, automation approval
and worker path, and the database migration/test cleanup path. No graph refresh
was run mid-session.
