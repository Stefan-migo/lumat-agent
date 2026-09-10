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
