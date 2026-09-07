# Apply Progress: Conversation Realtime

Change: `conversation-realtime`  
Branch chain: **7 stacked slices**, PRs **#112–#118**, merged in order to `main`  
Mode: **Strict TDD**  
Artifact store: **hybrid** (OpenSpec + Engram)  
Verified implementation HEAD: `8eae542139c15688ba34d33741de31c71aefa5bf`

Status: **complete — all 14 tasks checked**

## Completed Tasks

- [x] **1.1–1.2** Event foundation: typed envelopes, scoped activity validation/history, bounded publisher, transaction-safe post-commit dispatch, rollback/no-ghost behavior.
- [x] **2.1–2.2** Internal chat token callback: ordered transient token delivery, failure isolation, unchanged synchronous POST contract, operator denial.
- [x] **3.1–3.2** Authenticated `/panel/ws`: direct mount, cookie/role authorization, snapshot-first ordering, subscription cleanup.
- [x] **4.1–4.2** Activity and recency writers: classified/KB/escalation activities, inbound/outbound recency, typed conversation state publication, reconnect-safe history.
- [x] **5.1–5.2** Active summary endpoint, customer-name join, active-window/state/null filtering, ordering, and migration/index.
- [x] **6.1–6.2** SPA realtime client, reducers, token/activity states, reconnect/refetch recovery, and live page updates.
- [x] **7.1–7.2** Active conversation rail, disconnected/error semantics, Vite WebSocket proxy, and nginx upgrade locations.

## TDD Cycle Evidence (Strict TDD)

Counts below are the observable test cases in the named RED files. Where a parametrized file's runtime count differs from its declared test-function count, both are stated. Safety-net values are the cumulative per-slice baselines recorded in Engram session records; no unrecorded number is inferred.

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---:|---|
| 1.1 | `tests/unit/test_realtime.py`; `tests/integration/test_realtime.py` | Unit + Integration | ✅ 592 (per-slice record) | ✅ Written (`ed078551`) | ✅ Passed (PR #112; 9 focused, 592 full-suite) | 9 declared cases (5 unit + 4 integration) | ➖ None needed |
| 1.2 | `tests/unit/test_realtime.py`; `tests/integration/test_realtime.py` | Unit + Integration | ✅ 592 (per-slice record) | ✅ Written (`ed078551`) | ✅ Passed (`ed078551`; 9 focused) | 9 declared cases | ➖ None needed |
| 2.1 | `tests/integration/test_agent_chat_realtime.py` | Integration | ✅ 592 (per-slice record) | ✅ Written (`6e5708e9`) | ✅ Passed (PR #113; 3 focused, 595 full-suite) | 3 cases: ordered tokens, delivery failure, operator denial | ➖ None needed |
| 2.2 | `tests/integration/test_agent_chat_realtime.py` | Integration | ✅ 592 (per-slice record) | ✅ Written (`6e5708e9`) | ✅ Passed (`6e5708e9`; 3 focused) | 3 declared cases | ➖ None needed |
| 3.1 | `tests/functional/test_api_realtime.py` | Functional | ✅ 595 (per-slice record) | ✅ Written (`deeacaa7`) | ✅ Passed (PR #114; 4 focused, 599 full-suite) | 4 declared cases: operator/admin snapshot and two auth denials | ➖ None needed |
| 3.2 | `tests/functional/test_api_realtime.py` | Functional | ✅ 595 (per-slice record) | ✅ Written (`deeacaa7`) | ✅ Passed (`deeacaa7`; 4 focused) | 4 declared cases | ➖ None needed |
| 4.1 | `tests/integration/test_realtime_writers.py` plus existing writer integration tests | Integration | ✅ 599 (per-slice record) | ✅ Written (`16ca4f83`) | ✅ Passed (PR #115; 58 focused, 606 full-suite) | 9 declared cases in `test_realtime_writers.py` | ➖ None needed |
| 4.2 | `tests/integration/test_realtime_writers.py` plus existing writer integration tests | Integration | ✅ 599 (per-slice record) | ✅ Written (`16ca4f83`) | ✅ Passed (`16ca4f83` + `6db4c9d2`; 608 full-suite after HH-6 correction) | 9 declared cases, including state publication and failure isolation | ➖ None needed |
| 5.1 | `tests/functional/test_api_conversations.py`; `tests/integration/test_migrations.py` | Functional + Integration | ✅ 608 (per-slice record) | ✅ Written (`8d4a1064`) | ✅ Passed (PR #116; endpoint 22 + migration 14, 611 full-suite) | 20 declared endpoint cases (22 runtime) + 14 migration cases | ➖ None needed |
| 5.2 | `tests/functional/test_api_conversations.py`; `tests/integration/test_migrations.py` | Functional + Integration | ✅ 608 (per-slice record) | ✅ Written (`8d4a1064`) | ✅ Passed (`8d4a1064`; endpoint 22 + migration 14) | 20 declared endpoint cases (22 runtime) + 14 migration cases | ➖ None needed |
| 6.1 | `web/src/realtime.test.ts` | Frontend unit (Vitest/jsdom) | ✅ 414 (per-slice record) | ✅ Written (`53eeea69`) | ✅ Passed (PR #117; frontend suite 438 at slice close, 444 final) | 4 cases: reducer updates, token replacement, reconnect/refetch, cleanup | ➖ None needed |
| 6.2 | `web/src/realtime.test.ts` | Frontend unit (Vitest/jsdom) | ✅ 414 (per-slice record) | ✅ Written (`53eeea69`) | ✅ Passed (`53eeea69`; frontend suite 438 at slice close) | 4 declared cases | ➖ None needed |
| 7.1 | `web/src/components/domain/realtimeRail.test.tsx`; `web/src/deployment.test.ts` | Frontend unit (Vitest/jsdom) | ✅ 438 (per-slice record) | ✅ Written (`0d3656fd`) | ✅ Passed (PR #118; focused regression 23 tests, 444 full frontend suite) | 5 cases: 3 rail + 1 Vite + 1 parametrized nginx host contract | ➖ None needed |
| 7.2 | `web/src/components/domain/realtimeRail.test.tsx`; `web/src/deployment.test.ts` | Frontend unit (Vitest/jsdom) | ✅ 438 (per-slice record) | ✅ Written (`0d3656fd`) | ✅ Passed (`0d3656fd`; 23 focused regression tests, 444 full frontend suite) | 5 declared/expanded contract cases | ➖ None needed |

Every `RED` entry is grounded in an existing test file on `main`; no RED state or count is fabricated. The final verify report independently confirms the full GREEN gates.

## Test Summary

- `uv run pytest tests/` → **611 passed**, exit 0; one existing `RuntimeWarning` about unawaited `_publish_all`.
- `cd web && npm test` → **66 files, 444 passed**, exit 0; existing React `act(...)` warnings remain.
- `cd web && npx tsc --noEmit && npm run build` → **passed**, exit 0.
- Final runtime evidence is recorded in `verify-report.md`; its behavioral matrix is 15/15 requirements and 28/28 scenarios.

## Work Unit Evidence

| Phase | Focus command | Result |
|---|---|---|
| 1 | `uv run pytest tests/ -k realtime` | 9 focused realtime tests passed; full suite 592 passed at slice close. |
| 2 | `uv run pytest tests/integration/test_agent_chat_realtime.py` | 3 focused tests passed; full suite 595 passed at slice close. |
| 3 | `uv run pytest tests/functional/test_api_realtime.py` | 4 focused tests passed; full suite 599 passed at slice close. |
| 4 | `uv run pytest tests/ -k realtime_writers` | 58 focused tests passed; full suite reached 606, then 608 after the HH-6 correction. |
| 5 | `uv run pytest tests/functional/test_api_conversations.py tests/integration/test_migrations.py` | Endpoint and migration tests passed; full suite 611 passed. |
| 6 | `cd web && npm test -- realtime` | Realtime client tests passed; frontend suite 438 at slice close. |
| 7 | `cd web && npm test -- --run src/components/domain/realtimeRail.test.tsx src/deployment.test.ts src/components/domain/AppShell.test.tsx` | 3 files / 23 tests passed; full frontend 444, typecheck and production build passed. |

## Files Changed Summary

Grouped from the verified implementation commits:

- **Phase 1:** `app/services/realtime.py`, `app/db.py`, `app/panel/deps.py`, `tests/unit/test_realtime.py`, `tests/integration/test_realtime.py`.
- **Phase 2:** `app/chat/graph.py`, `app/services/agent_chat.py`, `tests/integration/test_agent_chat_realtime.py`.
- **Phase 3:** `app/panel/api/deps.py`, `app/panel/api/routes/realtime.py`, `app/panel/routes/__init__.py`, `tests/functional/test_api_realtime.py`.
- **Phase 4:** `app/chat/nodes/classify_intent.py`, `app/chat/subgraphs/research_triage.py`, `app/chat/nodes/handoff.py`, `app/chat/state.py`, `app/webhook/ingest.py`, `app/services/conversations.py`, `tests/integration/test_realtime_writers.py`.
- **Phase 5:** `app/panel/api/routes/conversations.py`, `app/panel/api/serializers.py`, `db/migrations/018_conversation_realtime.sql`, `tests/functional/test_api_conversations.py`, `tests/integration/test_migrations.py`.
- **Phase 6:** `web/src/realtime.ts`, `web/src/realtime.test.ts`, `web/src/api.ts`, `web/src/types.ts`, `web/src/components/pages/{ConversationThread,ConversationsList,AgentChat}.tsx`.
- **Phase 7:** `web/src/components/domain/{AppShell,PanelShell}.tsx`, `web/src/components/domain/realtimeRail.test.tsx`, `web/src/deployment.test.ts`, `web/src/app.tsx`, `web/src/app.test.tsx`, `web/src/components/domain/AppShell.test.tsx`, `web/vite.config.ts`, both nginx host configs.

## Deviations from Design

- Advisory follow-ups remain non-blocking: **R3-001** around `AppShell.tsx:126`; the approved slice-3 **R3-001/R3-002** observations around `realtime.py` snapshot/stream handling; the slice-4 **R4-001** observation around `conversations.py:162`; and the slice-6 **R3-001** observation around `realtime.ts:83`.
- Phase 4 required the minimal HH-6 correction in `6db4c9d2`: state transitions stage a typed `conversation` envelope after the state-change flush and publication failure remains best-effort. This preserves the design's commit boundary rather than changing the authoritative REST transition.
- The existing backend unawaited `_publish_all` warning and frontend React `act(...)` warnings are non-blocking because all declared gates exit 0.

## Graph Record

Graph Check passed before source inspection. `graphify-out/GRAPH_REPORT.md` was consulted for the relevant hubs and communities: `services/realtime.py`, `api/routes/conversations.py`, `realtime.ts`, `domain/AppShell.tsx`, `domain/PanelShell.tsx`, `vite`, and nginx/proxy nodes. Consulted relationship evidence included the backend realtime publisher → chat/graph and panel realtime route connections, `AppShell → PanelShell`, SPA → `api.ts`/`realtime.ts`, `panel_websocket()` → realtime route, and nginx → Vite/API proxy boundaries. Directed cross-boundary paths from `app/services/realtime.py` to `web/src/realtime.ts` were absent, as expected for a WebSocket contract boundary.

The report is explicitly stale: it was built at commit **`de571274`**, while this artifact verifies **`8eae5421`**. No graph refresh was performed during this read-only reconstruction.

## Delivery / Branch / Commit

All seven slices used the `stacked-to-main` strategy and were merged through the following PRs:

| Phase | PR | Work-unit commit(s) | Merge commit on `main` |
|---|---:|---|---|
| 1 | #112 | `ed078551` | `28322923` |
| 2 | #113 | `6e5708e9` | `cd5af495` |
| 3 | #114 | `deeacaa7` | `de571274` |
| 4 | #115 | `16ca4f83`, `6db4c9d2` | `4c34899e` |
| 5 | #116 | `8d4a1064` | `0f6d4392` |
| 6 | #117 | `53eeea69` | `f147e972` |
| 7 | #118 | `0d3656fd` | `8eae5421` |

The implementation chain is complete on `main`. This file reconstructs the missing cumulative apply-progress admission artifact; it does not alter source, tests, specs, or the existing verify report.
