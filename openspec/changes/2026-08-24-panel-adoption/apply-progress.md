# Apply Progress: Panel Adoption — S1 Auth + Gate

## Status

- Change: `2026-08-24-panel-adoption`
- Work unit: Phase 1 / S1 Auth + gate, tasks 1.1–1.4
- Mode: Strict TDD
- Delivery: `auto-chain`, `stacked-to-main`, PR1 focused boundary
- Rollback: revert the S1 commit
- Completed: 4/28 tasks

## Completed Tasks

- [x] 1.1 Added RED coverage for successful login, invalid/locked login, logout-to-login, and `postJson` success/error.
- [x] 1.2 Added `postJson<T>` and the production `LoginAuth` form with loading, generic errors, username preservation, and no account-existence leak.
- [x] 1.3 Replaced the anonymous stub with the real login gate and wired logout through `AppShell` and `PanelShell`.
- [x] 1.4 Converted `Login.stories.tsx` into a thin wrapper while preserving `LoginAuth`, `LoginDefault`, `LoginError`, and `LoginLoading` exports.

## TDD Cycle Evidence

| Task | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `web/src/app.test.tsx`, `web/src/api.test.ts` | Integration-style component/API fetch stubs | 25 existing focused tests passed | Written; failed on missing `postJson`, `LoginAuth`, and logout | 30 focused tests passed | Success, locked-login, logout, POST success/error cases | Clean |
| 1.2 | `web/src/app.test.tsx`, `web/src/stories/pages/Login.stories.test.tsx` | Component integration | Existing login story coverage passed | Written before `LoginAuth` existed | 30 focused tests + 6 Login tests passed | Loading, invalid/locked error, username preservation, and success paths | Clean |
| 1.3 | `web/src/app.test.tsx` | Component integration | AppShell baseline passed | Written before gate/logout wiring | Logout and successful-login tests passed | Authenticated admin and return-to-login paths | Clean |
| 1.4 | `web/src/stories/pages/Login.stories.test.tsx` | Component | Existing story tests passed | Wrapper import/export contract written before wrapper change | 6/6 Login story tests passed | Triangulation skipped: structural wrapper/export preservation has one contract surface | Clean |

## Work Unit Evidence

| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `cd web && npm test -- app api` — PASS; 4 test files, 30 tests passed. |
| Additional story test | `cd web && npm test -- Login` — PASS; 1 test file, 6 tests passed. |
| Type check | `cd web && npx tsc -b` — PASS; exit code 0. |
| Runtime harness command/scenario and exact result | N/A — S1 has no server/runtime boundary; app and API behavior use native fetch stubs in Vitest. |
| Rollback boundary | Revert the S1 commit; removes `LoginAuth`, `postJson`, gate/logout wiring, tests, and the Login story wrapper without touching later slices. |

## Graph Check

Graph was present and non-empty at `graphify-out/graph.json`; `graphify-out/GRAPH_REPORT.md` was read before implementation.

Consulted nodes:

- `App()` / `web/src/app.tsx`
- `AppShell()` / `web/src/components/domain/AppShell.tsx`
- `AppShell.tsx`
- `PanelShell()` / `web/src/components/domain/PanelShell.tsx`
- `api.ts` / `web/src/api.ts`
- `Login.stories.tsx`
- `api/routes/auth.py` and `login()` / backend auth contract

Consulted edges:

- `app.tsx --imports_from--> AppShell.tsx`
- `AppShell.tsx --imports_from--> PanelShell.tsx`
- `app.tsx --imports_from--> api.ts`
- `Login.stories.tsx --imports_from--> LoginAuth.tsx` (validated as the intended new wrapper edge)
- `App()` → `AppShell()` → `PanelShell()` shortest path (2 hops from `app.tsx` to `PanelShell.tsx`)

## Remaining Tasks

Phase 2 / S2 remains pending. No later slice was started.

## Issues

- `pytest tests/` was attempted as the configured backend runner but was blocked during collection by the pre-existing missing dependency `psycopg` in `tests/conftest.py`. S1 is frontend-only; the required frontend checks passed.
