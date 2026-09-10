# Apply Progress: Panel Conversations Redesign — Slice A

## Status

- **Slice:** A — backend read model and realtime snapshot
- **Mode:** Strict TDD
- **Delivery:** auto-chain, stacked-to-main; Slice A boundary is the backend API and realtime contract
- **Apply state:** implementation complete; full functional verification has one unrelated date-anchored dashboard failure
- **Tasks completed:** A.1, A.2, A.3

## Resolved Previous Blocker

The previous safety-net blocker is resolved. The worktree was sharing the `lumat` database with a live dev server and another worktree, so `clean_db` TRUNCATE deadlocked against live transactions. Tests now use the dedicated `lumat_conversaciones` database. The mandatory focused baseline is green: 38 passed.

## TDD Cycle Evidence

| Task | Test file | RED | GREEN | REFACTOR |
|---|---|---|---|---|
| A.1 | `tests/functional/test_api_conversations.py`, `test_api_realtime.py` | 5 expected contract failures after new tests | 41 passed in focused backend suite | Removed unused realtime import; preserved existing case mutation tests |
| A.2 | `tests/functional/test_api_conversations.py` | New envelope, search, ranked-case, detail-parity tests failed | 24 conversation tests passed | Shared ranked subquery and serializer; no new abstraction/dependency |
| A.3 | `tests/functional/test_api_realtime.py` | Snapshot parity tests failed | 41 focused backend tests passed | Snapshot reuses REST queue response |

## Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command and exact result | `TEST_ADMIN_DB_URL="postgresql://lumat:lumat@localhost:5432/lumat_conversaciones" DATABASE_URL="postgresql+psycopg://app:app@localhost:5432/lumat_conversaciones" uv run pytest tests/functional/test_api_conversations.py tests/functional/test_api_realtime.py tests/functional/test_api_cases.py -q -p no:cacheprovider` — **41 passed**. |
| Runtime harness command/scenario and exact result | Same focused command exercises authenticated REST list/detail, case mutation authority, and authenticated WebSocket snapshot; **41 passed**. |
| Rollback boundary | Revert commits `4f34b237`, `9fbbef23`, and the realtime commit to remove Slice A backend contract changes; `routes/cases.py` remains untouched. |

## Full Functional Verification

`TEST_ADMIN_DB_URL="postgresql://lumat:lumat@localhost:5432/lumat_conversaciones" DATABASE_URL="postgresql+psycopg://app:app@localhost:5432/lumat_conversaciones" uv run pytest tests/functional/ -q -p no:cacheprovider` reached 100% collection and reported **1 unrelated failure**: `test_today_excludes_cancelled_and_replied_rows_and_caps_each_projection` expected 20 appointments for 2026-09-09 while the runtime date is 2026-09-10, so the dashboard “today” query returned 0. No dashboard files were changed.

## Graph Check

- `graphify-out/graph.json` exists and is non-empty; `GRAPH_REPORT.md` was read.
- Consulted nodes: `serializers.py`, `routes/conversations.py`, `routes/realtime.py`, `Conversation`, `Customer`, `Case`, `Panel JSON API serializers`, `Panel JSON API conversations`, `realtime.ts`.
- Consulted edges: `routes/conversations.py --imports_from--> serializers.py`; `routes/realtime.py --imports_from--> routes/conversations.py`; `routes/conversations.py --imports_from--> models.py --contains--> Case`.

## Pre-apply Ponytail Check

Applied YAGNI → stdlib → native → one-line → minimum. No new dependency, cache/state abstraction, KPI layer, cursor pagination, or fixed captured-data schema. The existing REST queue helper is reused by realtime rather than introducing a second read model.

## Deviations and Risks

- The legacy `conversations` key is retained as an alias of `items` for compatibility while the new envelope is introduced.
- Full functional suite remains blocked by the date-anchored dashboard test described above; Slice A focused verification is green.

---

# Slice B — Frontend unified queue

## Status

- **Slice:** B — frontend queue UI
- **Mode:** Strict TDD
- **Delivery:** auto-chain, stacked-to-main; Slice B boundary is the queue page, API types/client, and queue interaction tests
- **Apply state:** implementation complete; focused, typecheck, and full web verification green
- **Tasks completed:** B.1, B.2 (Slice A A.1–A.3 retained above)

## TDD Cycle Evidence

| Task | Test file | RED | GREEN | REFACTOR |
|---|---|---|---|---|
| B.1 | `web/src/api.test.ts`, `web/src/components/pages/ConversationsList.test.tsx` | 7 expected queue failures after adding envelope, tabs, search, pagination, and action tests; baseline had 12 passed / 7 failed | Focused queue suite passed 19 tests | Preserved legacy response alias and story compatibility; no new dependency |
| B.2 | `web/src/api.test.ts`, `web/src/components/pages/ConversationsList.test.tsx` | B.1 RED failures drove typed queue implementation | Focused queue suite passed 19 tests and full web suite passed 499 tests | Reused `Tabs`, `SearchInput`, `DataTable`, and pagination primitive; local state only |

## Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command and exact result | `cd web && npm test -- --run src/components/pages/ConversationsList.test.tsx src/api.test.ts` — **2 files, 19 tests passed**. |
| Runtime harness command/scenario and exact result | `cd web && npm test -- --run src/components/pages/ConversationsList.test.tsx src/api.test.ts src/stories/pages/ConversationsList.stories.test.tsx` — **3 files, 24 tests passed**; exercises rendered queue fixture, search, tabs, pagination state, and quick actions. |
| Rollback boundary | Revert `feat(panel): build unified conversation queue` and its queue source changes to restore the Slice A-compatible list; the backend contract and unrelated pages remain untouched. |

## Full Web Verification

- `cd web && npx tsc -b` — **passed**.
- `cd web && npm test` — **69 files, 499 tests passed**.
- `npm ci` initially reported a transient lockfile usage error; `npm ci --package-lock=true` installed 318 packages successfully. No dependency files changed.

## Graph Check

- `graphify-out/graph.json` exists and is non-empty; `GRAPH_REPORT.md` was read.
- Consulted nodes: `ConversationsList()`, `ConversationsList.tsx`, `api.ts`, `types.ts`, `listConversations()`, `apiFetch()`, `Tabs`, `SearchInput`, `DataTable`, `Unified Conversation Queue Capability`.
- Consulted edges: `ConversationsList.tsx --imports_from--> api.ts`; `api.ts --imports_from--> types.ts`; `ConversationsList.tsx --imports_from--> types.ts`; `ConversationsList.tsx --imports_from--> Tabs/SearchInput/DataTable`; `api.ts --calls--> apiFetch()`.

## Pre-apply Ponytail Check

Applied YAGNI → stdlib → native → one-line → minimum. Reused existing local state, API client, DOM table, tabs, search, and pagination primitives. No state library, cache, cursor pagination, virtualization, KPI row, fixed captured-data schema, or new dependency. Intentional simplification ceiling: client-side tab filtering applies only to the authoritative current page; server search and offset pagination remain the source of truth.

## Deviations and Risks

- `listConversations()` omits default query parameters for the legacy no-argument call, while queue search/page requests explicitly send `limit` and `offset`; this preserves existing consumers and still satisfies queue navigation requests.
- `Conversation` queue fields remain optional and `conversations` remains an optional compatibility alias so existing stories and thread consumers compile during Slice C migration.
- React test output includes existing `act(...)` warnings during debounced search; assertions and all tests pass.

---

# Slice C — Workspace, realtime refresh, and routing

## Status

- **Slice:** C — workspace, realtime refresh, and routing
- **Mode:** Strict TDD
- **Delivery:** auto-chain, stacked-to-main; Slice C boundary is the conversation workspace, bounded realtime refresh, unified cases routing, and compatibility tests
- **Apply state:** implementation complete; web verification green; full backend suite attempted with pre-existing test-environment failures beyond the documented dashboard date failure
- **Tasks completed:** C.1, C.2, C.3 (Slice A A.1–A.3 and Slice B B.1–B.2 retained above)

## TDD Cycle Evidence

| Task | Test file | RED | GREEN | REFACTOR |
|---|---|---|---|---|
| C.1 | `ConversationThread.test.tsx`, `realtime.test.ts`, `panelRoutes.test.ts`, `AppShell.test.tsx` | New workspace, coalescing, `/cases`, and no-standalone-page assertions failed against the Slice B implementation | Focused suite passed 44 tests after implementation | Kept local state and the existing route/parser seam; no state library or cache layer |
| C.2 | Same focused web files plus `ConversationsList.tsx` realtime integration | C.1 failures drove context rendering, snapshot coalescing, route canonicalization, and unified cases rendering | Focused suite passed 44 tests; typecheck passed | Reused `setTimeout`, local state, existing queue API, and the existing shell tab grammar |
| C.3 | Full web and backend suites | Full-suite verification exposed stale standalone-case coverage and the pre-existing backend environment/date issues | Full web suite passed 489 tests; backend focused Slice A contract suite passed 41 tests | Removed stale standalone CasesList story coverage while preserving the unmounted legacy module for the sub-400-line Slice C boundary |

## Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command and exact result | `cd web && npm test -- --run src/components/pages/ConversationThread.test.tsx src/realtime.test.ts src/components/domain/panelRoutes.test.ts src/components/domain/AppShell.test.tsx` — **4 files, 44 tests passed**; `cd web && npx tsc -b` — **passed**. |
| Runtime harness command/scenario and exact result | `cd web && npm test` — **68 files, 489 tests passed**; exercises workspace rendering, `/cases` canonicalization, unified queue route, and snapshot refresh behavior. |
| Rollback boundary | Revert Slice C commits `4ac99406`, `92685a8c`, `32b5f09e`, and the verification cleanup commit; Slice A backend and Slice B queue implementation remain independently intact. |

## Full Backend Verification

The mandatory command was attempted exactly as required:

`TEST_ADMIN_DB_URL="postgresql://lumat:lumat@localhost:5432/lumat_conversaciones" DATABASE_URL="postgresql+psycopg://app:app@localhost:5432/lumat_conversaciones" uv run pytest tests/ -q -p no:cacheprovider`

It did not produce a clean full-suite result. The documented pre-existing failure remains `tests/functional/test_api_dashboard.py::test_today_excludes_cancelled_and_replied_rows_and_caps_each_projection` because it is anchored to 2026-09-09 while runtime date is 2026-09-10. Additionally, many integration tests use module-local hardcoded `postgresql://.../lumat` cleanup URLs instead of the mandatory dedicated URL, so their cleanup runs against the shared database while the application uses `lumat_conversaciones`; this caused cascading dirty-database failures and duplicate-key/row-count errors. No backend files were changed. The dedicated Slice A contract suite remains green at **41 passed**.

## Graph Check

- `graphify-out/graph.json` exists and is non-empty; `GRAPH_REPORT.md` was read.
- Consulted nodes: `ConversationThread()`, `ConversationThread.tsx`, `ConversationThread.test.tsx`, `RealtimeClient`, `realtime.ts`, `realtime.test.ts`, `AppShell.tsx`, `panelRoutes.ts`, `panelRoutes.test.ts`, `CasesList.tsx`, `ConversationsList.tsx`.
- Consulted edges: `ConversationThread.tsx --imports_from--> realtime.ts`; `AppShell.tsx --imports_from--> panelRoutes.ts`; `AppShell.tsx --imports_from--> ConversationThread.tsx/ConversationsList.tsx`; `panelRoutes.ts --compatibility route--> CasesList.tsx` (legacy route ownership removed in implementation).

## Pre-apply Ponytail Check

Applied YAGNI → stdlib → native → one-line → minimum. Used local React state, a bounded native `setTimeout` coalescer, the existing API client, route parser, shell tab grammar, and existing DOM primitives. No new dependency, state library, cache abstraction, or fixed `captured_data` schema was introduced. Intentional simplification ceiling: snapshot refreshes coalesce within a 100 ms window; authoritative REST remains the source of truth.

## Deviations and Risks

- `ConversationsList.tsx` was also modified because it owns queue subscription and must consume the bounded snapshot coalescer; this is within Slice C behavior even though the initial file list emphasized the workspace/routing files.
- `CasesList.tsx` is no longer mounted by `AppShell`; its legacy source remains in the worktree to keep Slice C under the 400 authored-line review budget, while its standalone Storybook coverage was retired.
- Full backend verification is blocked by stale module-local test database URLs and the documented date-anchored dashboard test; no backend production code was touched.
