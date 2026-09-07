# Tasks: Conversation Realtime

Strict TDD: each phase is a stacked, independently verifiable slice under 400 changed lines; RED precedes GREEN.

## Phase 1: Event Foundation
- [x] 1.1 RED — Add backend tests for `classified`/`kb_retrieved` validation, escalation reuse, activity-only history, bounded filtering/drop cleanup, and no ghost publication (CM-3, CM-10, CRT-3); files `tests/unit/test_realtime.py`, `tests/integration/test_realtime.py`; est 90; deps none; evidence focused pytest failures.
- [x] 1.2 GREEN — Create `app/services/realtime.py`; modify `app/db.py`, `app/models.py`, `app/panel/api/routes/conversations.py`; implement validator, query filter, per-subscriber queues, conversation filtering, post-commit dispatch; est 190; deps 1.1; evidence `uv run pytest tests/` focused pass.

## Phase 2: Internal Chat Tokens
- [x] 2.1 RED — Test ordered token callback delivery, unchanged synchronous response, delivery failure, and operator denial (IAC-6, CRT-3); files `tests/integration/test_agent_chat_realtime.py`; est 55; deps Phase 1; evidence focused pytest failures.
- [x] 2.2 GREEN — Add optional callback to `app/chat/graph.py`; publish chunks in `app/services/agent_chat.py` without changing POST persistence/authorization (IAC-6, CRT-3); est 145; deps 2.1; evidence focused pytest pass and existing chat tests.

## Phase 3: Authenticated WebSocket
- [ ] 3.1 RED — Add `TestClient.websocket_connect` tests for `/panel/ws` mount, cookie/role rejection, snapshot-first ordering, and disconnect cleanup (CRT-1, CRT-2, threat HTTP/WebSocket routing); files `tests/functional/test_api_realtime.py`; est 75; deps Phase 1; evidence failing websocket tests.
- [ ] 3.2 GREEN — Create `app/panel/api/routes/realtime.py`; register directly in `app/panel/routes/__init__.py`; reuse `app/panel/api/deps.py` session auth and snapshot subscription (CRT-1/2/3); est 150; deps 3.1; evidence focused pytest pass.

## Phase 4: Activity and Recency Writers
- [ ] 4.1 RED — Test classification/retrieval activities, webhook/chat/panel `last_message_at`, escalation publication, and reconnect-safe history (CM-3, CM-10, HH-1/6); files existing integration tests plus `test_realtime_writers.py`; est 70; deps Phase 3; evidence failing integration tests.
- [ ] 4.2 GREEN — Modify `app/chat/nodes/classify_intent.py`, `app/chat/subgraphs/research_triage.py`, `app/chat/nodes/handoff.py`, `app/webhook/ingest.py`, `app/services/agent_chat.py`, `app/panel/api/routes/chat.py`, and serializers (CM-3/10, HH-1/6); est 190; deps 4.1; evidence `uv run pytest tests/` focused pass.

## Phase 5: Active Summary API
- [ ] 5.1 RED — Test authorized `GET /panel/api/conversations/active`, customer-name join, bot/human + 24-hour/non-null exclusions, ordering, and null behavior (CRT-4); files `tests/functional/test_api_conversations.py`; est 55; deps Phase 4; evidence failing endpoint tests.
- [ ] 5.2 GREEN — Add active query/serializers in `app/panel/api/routes/conversations.py`, `app/panel/api/serializers.py`, and migration `db/migrations/018_conversation_realtime.sql` (CRT-4); est 150; deps 5.1; evidence focused endpoint and migration tests.

## Phase 6: SPA Realtime Client
- [ ] 6.1 RED — Add deterministic fake-WebSocket Vitest coverage for reconnect/cleanup, reducers, activity `role=status`, token states, and REST refetch (PNL-APP-13/15, DS-RT-1); files `web/src/realtime.test.ts`; est 85; deps Phase 5; evidence `cd web && npm test` failures.
- [ ] 6.2 GREEN — Create `web/src/realtime.ts`; modify `web/src/api.ts`, `web/src/types.ts`, `ConversationThread.tsx`, `ConversationsList.tsx`, and `AgentChat.tsx` for live updates, reconnect recovery, and accessible activity/error states (PNL-APP-13/15, DS-RT-1); est 210; deps 6.1; evidence focused Vitest pass.

## Phase 7: Rail and Deployment Wiring
- [ ] 7.1 RED — Test active-summary loading/error/disconnected rail behavior, compact keyboard/reduced-motion states, Vite `ws:true`, and nginx upgrade headers/timeouts (PNL-APP-14, DS-RT-1/2, CRT-5, threat routing); files shell/config/infra tests; est 65; deps Phase 6; evidence failing web/infra assertions.
- [ ] 7.2 GREEN — Wire `AppShell.tsx` → `PanelShell.tsx` active rail; modify `web/vite.config.ts`, `infra/nginx/panel.lumat.cl.conf`, and `infra/nginx/agente.lumat.cl.conf` (PNL-APP-14, DS-RT-1/2, CRT-5); run all gates; est 180; deps 7.1; evidence tests/typecheck/build pass.

## Review Workload Forecast
| Phase | Est. lines | Focused test / runtime harness | Rollback boundary |
|---|---:|---|---|
| 1 | 280 | `uv run pytest tests -k realtime`; publisher queue scenario | realtime seam, model/query tests |
| 2 | 200 | `uv run pytest tests -k agent_chat_realtime`; authorized POST | graph/chat token changes |
| 3 | 225 | `uv run pytest tests/functional/test_api_realtime.py`; TestClient WS | route/auth files |
| 4 | 260 | `uv run pytest tests -k realtime_writers`; webhook/chat/panel commits | writer integrations |
| 5 | 205 | `uv run pytest tests/functional/test_api_conversations.py`; endpoint request | endpoint/migration |
| 6 | 295 | `cd web && npm test -- realtime`; fake socket reconnect | SPA client/surfaces |
| 7 | 245 | `cd web && npm test && uv run pytest tests/`; browser/proxy handshake scenario | rail/Vite/nginx |
| **Total** | **1710** | **Seven autonomous stacked slices** | **Revert one phase at a time** |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

## Graph Check
Consulted nodes: `models.py`, `session_scope()`, `graph.py`, `agent_chat.py`, `panel/deps.py`, `serializers.py`, `PanelShell.tsx`, `AppShell.tsx`, `vite`, nginx service. Edges: `graph.py → agent_chat.py`, `session_scope() → events.py`, `AppShell → PanelShell`, panel auth → routes.
