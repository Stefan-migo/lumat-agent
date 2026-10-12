# conversations-closed-pagination

## Objective

In the Conversations queue, stop showing closed conversations in the live tabs (closed = archived; they
live in "Cerradas"), and make the list paginate server-side at 10 per page.

## Problem

The queue fetches up to the backend default (50) and filters tabs client-side, so "Todas" includes closed
conversations and the footer shows "12 de 12" on a single page.

- Backend: `app/panel/api/routes/conversations.py:123-220` supports `state`/`responsible_id`/`q`/`limit`/
  `offset` and applies `LIMIT/OFFSET`, but has no default closed exclusion and no emergency/case filters.
- Frontend: `web/src/components/pages/ConversationsList.tsx:25-28,52-63` filters tabs locally and calls
  `listConversations()` with no args for the default view; the footer label is `visibleRows.length` of
  `total` (`:112-114,132`).
- The `Pagination` primitive exists (`web/src/components/primitives/Pagination.tsx`) but the page renders
  its own prev/next.

## Scope

**In:**
- Live tabs ("Todas", "Atención humana", "Emergencias", "Con caso") exclude closed; "Cerradas" shows only
  closed.
- Server-side tab filtering + real pagination at 10 per page using the `Pagination` primitive and the
  server `total`/`offset`/`limit`.
- Small backend addition: `exclude_closed`, `emergency`, `has_case` query params; tab counts align with
  each tab's row predicate.
- Backend + frontend tests.

**Out (deliberate):**
- No new DB column/flag: the `closed` state IS the archive (owner).
- No change to the conversation lifecycle (a new inbound already creates a new conversation —
  `app/chat/state.py:47-66`).
- No per-client history viewer (that is S2).
- No change to the state machine, actions, or realtime behavior.

## Authorized scope

- Worktree: `lumat-agent-odd-conversations-closed-pagination`
- Branch: `odd/conversations-closed-pagination`
- Base: `8d620058` (`origin/main`)
- Files (expected):
  - `odd/tasks/conversations-closed-pagination.md` (this record)
  - `app/panel/api/routes/conversations.py` (filters + counts)
  - `tests/functional/test_api_conversations.py` (backend tests)
  - `web/src/api.ts` (`ConversationFilters`)
  - `web/src/components/pages/ConversationsList.tsx` (+ `.test.tsx`)
  - `web/src/stories/pages/ConversationsList.stories.tsx` (only if variants need updating)
  - `web/src/stories/pages/ConversationsList.stories.test.tsx` (assertion updated for the new query)
  - `web/src/components/pages/ConversationsList.css` (only if the footer/pagination needs it)

Any file outside this list needs a scope update here first.

## Constraints

- **Strict TDD: ON.** Python `uv run pytest tests/`; web `cd web && npx vitest run`; type check
  `cd web && npm run build`. Observe RED before the source change.
- **Design:** reuse the `Pagination` primitive; tokens only; no new dependency; UI copy neutral Chilean
  Spanish; code/comments/commits English.
- Keep the response contract keys: `items`, `total`, `offset`, `limit`, `counts`, `conversations`.

## Behavior spec (target)

1. Tab → query mapping (always `limit=10`):
   - `all` → `exclude_closed=true`
   - `human` → `state=human`
   - `emergency` → `exclude_closed=true&emergency=true`
   - `case` → `exclude_closed=true&has_case=true`
   - `closed` → `state=closed`
2. `counts` equal each tab's row predicate over the q/responsible-filtered set:
   `all` = non-closed; `human` = human; `emergency` = non-closed & unacknowledged emergency;
   `case` = non-closed & has selected case; `closed` = closed.
3. The footer shows the real page range (e.g. "Mostrando 1–10 de 34") and the `Pagination` primitive
   drives page changes.
4. Changing tab / search / responsible resets `offset` to 0.

## Decisions

- **D1 — `closed` IS archived.** No new flag; live tabs exclude `state=closed`, and "Cerradas" is the
  archive view.
- **D2 — server-side tabs.** Local tab filtering is incompatible with server pagination, so each tab
  becomes a query.
- **D3 — "Emergencias" = non-closed, unacknowledged emergency.** Aligns the tab with the existing count
  predicate (`selected_case_emergency AND acknowledged_at IS NULL`) and the design intent (unacknowledged
  exceptions surface). The old client filter matched any emergency; this is the deliberate alignment.
- **D4 — 10 rows per page.**

## Work units (stable IDs)

### C1 — Backend filters + counts
- [x] `exclude_closed`, `emergency`, `has_case` params on `GET /panel/api/conversations`, applied in
      `_queue_base`.
- [x] Counts recomputed per tab predicate (tab-independent base = q/responsible only).
- [x] Functional tests (filters + counts + pagination).

### C2 — Frontend queue
- [x] `ConversationFilters` gains `exclude_closed` / `emergency` / `has_case`.
- [x] Tab → params; `limit=10`; fetch keyed on tab/offset/filters.
- [x] `Pagination` primitive + real range footer.
- [x] Vitest for tab queries + pagination.

### C3 — Evidence
- [x] Focused backend + web suites green; `npm run build` green.

## Acceptance criteria

1. "Todas" (and the other live tabs) never list a closed conversation; "Cerradas" lists only closed.
2. The queue shows at most 10 rows per page with working pagination and a truthful range/count.
3. Tab counts equal the rows their tab shows.
4. `uv run pytest tests/` green; focused web suite + `npm run build` green.

## Checks

- `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/ -q`
- `cd web && npx vitest run src/components/pages/ConversationsList.test.tsx`
- `cd web && npm run build`
- `git diff --check`

## Graph Check (consulted)

`graphify query "conversations queue list pagination closed filter tabs conversations endpoint"`: nodes
`Pagination()`, `ConversationsList.tsx` (community `ConversationThread.tsx`), `Tabs()`, the
`conversations` Storybook mock data, and the `queue()` helper in `ConversationsList.test.tsx`. Affected
communities: `ConversationsList.tsx` and `api.ts`.

## Progress log

- Worktree created from `origin/main` = `8d620058`; branch `odd/conversations-closed-pagination`. Env:
  `uv sync`, `infra/.env`, worktree test DB up, `npm install`.
- RED: new backend filter/count test failed because params were ignored and counts included closed/acknowledged cases; frontend suite had 4 failures because it still requested unfiltered 20-row data and the range/pagination contract was absent.
- GREEN: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/functional/test_api_conversations.py -q` (27 passed); `cd web && npx vitest run src/components/pages/ConversationsList.test.tsx` (16 passed); `cd web && npm run build` (passed; existing chunk-size advisory); full backend `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/ -q` (passed, 100%; two existing warnings); `git diff --check` (passed).
- Graph check: consulted `Pagination()`, `ConversationsList.tsx`, `queue()`, `conversations`, and `routes/conversations.py`; report communities include `ConversationsList.tsx`/`ConversationThread.tsx`, `api.ts`, and `routes/conversations.py`. Directed path between frontend list and route was not found.
- **CI caught a missed assertion (orchestrator).** The `panel` job runs the full web suite and failed in `web/src/stories/pages/ConversationsList.stories.test.tsx`: it still expected the bare `/panel/api/conversations` URL. Fixed to match the new filtered query (`exclude_closed=true&limit=10`) and added to the authorized scope. Local focused runs had missed this file; the full web suite is only reachable via CI in this environment.
