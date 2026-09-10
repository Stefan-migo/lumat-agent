# Tasks: Panel Conversations Redesign

## Review Workload Forecast

Estimated changed lines: A ~320, B ~360, C ~340; total ~1,020. Each slice stays below 400; chained PRs are required. Delivery strategy: auto-chain. Chain strategy: pending user selection.

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Slice work units

| Slice | Focused test command | Runtime harness | Rollback boundary |
|---|---|---|---|
| A / PR 1 | `uv run pytest tests/functional/test_api_conversations.py tests/functional/test_api_realtime.py tests/functional/test_api_cases.py` | Authenticated REST list/detail and WebSocket snapshot fixture | Backend API/realtime files and their tests |
| B / PR 2 | `cd web && npm test -- --run src/components/pages/ConversationsList.test.tsx src/api.test.ts` | Render queue fixture; search, tab, page, and quick-action interactions | Queue page, API/types files, and tests |
| C / PR 3 | `cd web && npm test -- --run src/components/pages/ConversationThread.test.tsx src/components/domain/panelRoutes.test.tsx src/components/domain/AppShell.test.tsx` | Render workspace and parse `/panel/app/cases` | Workspace, routing, realtime client, and tests |

## Slice A — Backend read model and snapshot (PR 1)

- [x] A.1 RED — Add precedence, nullable context, `q`, pagination, counts, detail parity, ack authority, and snapshot-parity tests in `tests/functional/test_api_conversations.py`, `test_api_cases.py`, and `test_api_realtime.py`. Verify: focused pytest. Commit: `test(panel): define unified conversation read contracts`.
- [x] A.2 GREEN — Implement ranked case join, shared serialization, search/envelope/counts, deterministic ordering, and detail parity in `app/panel/api/serializers.py` and `app/panel/api/routes/conversations.py`; keep `routes/cases.py` mutations unchanged. Verify: focused pytest. Commit: `feat(panel): expose case-aware paginated conversations`.
- [x] A.3 GREEN — Make `app/panel/api/routes/realtime.py` reuse the REST-equivalent queue rows, counts, and case precedence; verify snapshot tests and full `uv run pytest tests/functional/`. Commit: `feat(panel): align realtime snapshots with queue contract`.

## Slice B — Unified queue UI (PR 2)

- [x] B.1 RED — Extend `web/src/api.test.ts` and `web/src/components/pages/ConversationsList.test.tsx` for typed envelope requests, tabs/counts/order, search/page parameters, empty/error DOM rows, and Tomar/Reconocer refresh. Verify: focused Vitest. Commit: `test(panel): define unified queue interactions`.
- [x] B.2 GREEN — Update `web/src/types.ts`, `web/src/api.ts`, and `web/src/components/pages/ConversationsList.tsx` for queue tabs, priority display, search, limit/offset pagination, direct rows, and actions. Verify: focused Vitest plus `cd web && npx tsc -b`. Commit: `feat(panel): build unified conversation queue`.

## Slice C — Workspace, realtime refresh, and routing (PR 3)

- [ ] C.1 RED — Add workspace, captured-data, bounded-refresh, bookmarked-route, malformed-route, and no-`CasesList` tests in `ConversationThread.test.tsx`, `realtime.test.ts`, `panelRoutes.test.ts`, and `AppShell.test.tsx`. Verify: focused Vitest. Commit: `test(panel): define workspace and route compatibility`.
- [ ] C.2 GREEN — Update `ConversationThread.tsx`, `web/src/realtime.ts`, `panelRoutes.ts`, and `AppShell.tsx` for right-side context, flexible data, coalesced snapshot refresh, `/cases`→`Casos`, and safe fallback; retire `CasesList.tsx` only after tests pass. Verify: focused Vitest plus `npx tsc -b`. Commit: `feat(panel): unify workspace and cases routing`.
- [ ] C.3 VERIFY — Run `uv run pytest tests/`, `cd web && npm test`, and `cd web && npx tsc -b`; confirm each PR remains under 400 authored changed lines and rollback boundaries remain independent. Commit: `test(panel): verify conversations redesign slices`.

## Graph task mapping

- A → `Conversation`, `Customer`, `Case` → `serializers.py` → `routes/conversations.py` → `routes/realtime.py`/`routes/cases.py` (REST and mutation edges).
- B → `ConversationsList.tsx` → `api.ts`/`types.ts` → `ConversationsList.test.tsx` (API-client and UI edges).
- C → `ConversationThread.tsx` ↔ `realtime.ts`; `AppShell.tsx` → `panelRoutes.ts` → `CasesList.tsx` (workspace and routing edges).

Ponytail review: `shrink:` merged separate backend contract tasks into one RED/GREEN slice; `yagni:` retained no new state/cache abstraction, cursor pagination, KPI layer, or fixed captured-data schema; `native:` uses existing local state, API client, DOM rows, and route parser. net: -3 unnecessary task groups.
