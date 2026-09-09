# Tasks: Panel Asistente Lumat

## Delivery and Review Workload Forecast

Five stacked-to-main PRs; tests travel with behavior. Ponytail review: merged validation/tests, removed proxy abstractions, retained direct services/httpx.

| Slice | Estimate | Risk | Rollback boundary |
|---|---:|---|---|
| PR 1 Boundary | 360 lines | High | assistant graph, route, migration 020 |
| PR 2 Tools | 430 lines | High | tools, migration 021, assistant automation actor |
| PR 3 UX | 280 lines | Medium | AgentChat/api/types changes |
| PR 4 Config | 190 lines | Low | agent files, registry validation, capability route |
| PR 5 Attachments | 390 lines | High | upload/context, migration 022, media files |

| PR | Focused test | Runtime harness | Rollback |
|---|---|---|---|
| 1 | `pytest tests/integration/test_assistant_chat.py` | admin submits, reloads, reconnects | graph/routes/020 |
| 2 | `pytest tests/{unit,integration}/test_assistant_tools.py` | approve rule; inspect worker/audit | tools/021/automation actor |
| 3 | `npm test -- AgentChat` | Storybook lifecycle states | AgentChat/api/types |
| 4 | `pytest tests/unit/test_agent_registry.py` | capability GET as admin/operator | config/registry route |
| 5 | `pytest tests/integration/test_assistant_attachments.py` | upload document/image, cleanup | upload/context/022 |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

## PR 1 — Assistant Graph Boundary

- [x] 1.1 **RED role/recovery/SSE** — `tests/integration/test_assistant_chat.py`: operador/cross-thread denial, approval recovery, ordered reconnect, no partial completion; req AO-1/3, IAC-2/3/6, threat matrix.
- [x] 1.2 **Persist metadata** — migration `020_assistant_metadata.sql`, `app/models.py`, `app/panel/api/serializers.py`, `app/chat/assistant/state.py`; req AO-1/IAC-2.
- [x] 1.3 **Build boundary** — `app/chat/assistant/{graph,nodes,approval,evidence,recovery}.py`, `app/services/agent_chat.py`, `app/panel/api/routes/chat.py`; replace old backend and add SSE; req AO-1/2/3, IAC-6.

## PR 2 — Native Tools and Safe Automation

- [x] 2.1 **RED tool security** — `tests/unit/test_assistant_tools.py`, `tests/integration/test_assistant_tools.py`: reject invalid/unknown, unapproved/tampered/replayed/expired calls; DDG failures are evidence; req AT-1/2/3, AR-7.
- [x] 2.2 **Registry/executor** — `app/chat/assistant/tools/{__init,registry}.py`, bounded DDG/httpx; typed direct-service reads and executor; req AT-1/3, AO-2.
- [x] 2.3 **Automation audit** — `app/services/automation.py` and integration coverage: assistant actor, executor-origin check, `record_audit`, existing unique execution and worker history; req AT-2, AR-6/7, AO-3.

## PR 3 — Frontend UX

- [x] 3.1 **RED UI states** — `AgentChat.test.tsx`/`AgentChat.stories.tsx`: lifecycle, approve/reject, reconnect, attachments; req IAC-3/6.
- [x] 3.2 **Render lifecycle** — `web/src/components/pages/AgentChat.tsx`, `api.ts`, `types.ts`: cards, controls, SSE reducer, recovery; req IAC-2/3/6.

## PR 4 — Agent Configuration

- [ ] 4.1 **RED registry tests** — `tests/unit/test_agent_registry.py`: malformed/missing refs fail; valid registry resolves one assistant; req AC-4/9.
- [ ] 4.2 **Validated config/view** — `app/agent_registry.py`, `agent/registry.yaml`, `agent/personas/`, `agent/prompts/`, capability route/view/tests; req AC-4/9/10.

## PR 5 — Attachments

- [ ] 5.1 **RED upload/context** — `tests/integration/test_assistant_attachments.py`: MIME/size/count/traversal, cross-thread, cleanup, extraction, vision-limit rejection; req AA-1/2/3.
- [ ] 5.2 **Isolated uploads** — `022_assistant_attachments.sql`, `app/panel/api/routes/chat.py`, assistant storage/cleanup: private thread-scoped files; req AA-1/3.
- [ ] 5.3 **Multimodal context** — `app/services/llm.py` and assistant context: `kb.extract_text()`, validate `google/gemini-2.5-flash`, limits, OpenRouter image parts; req AA-2.

## Graph Check

Consulted nodes/edges: `graph.py → run_internal_conversation() → InternalChatThread`; `AgentChat.tsx → api.ts`; `automation_rules.py → AutomationRule → worker.py`; `services/kb.py → extract_text`; `agent_registry.py → agent/registry.yaml`; `record_audit → AuditLog`; `llm.py → get_settings`; god nodes `record_audit`, `User`, `Conversation`, `Customer`, `Case`, `session_scope`.
