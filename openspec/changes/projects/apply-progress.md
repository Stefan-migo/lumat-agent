# Apply Progress: projects — WU-1 Registry Foundation

## Status

- Change: `projects`
- Work unit: WU-1 (Registry Foundation), stacked PR slice 1/5
- Delivery: `auto-chain`, `stacked-to-main`
- Mode: Strict TDD
- State: ready for verification

## Completed Tasks

- [x] 1.1 Migration and ORM contract tests
- [x] 1.2 Registry migration and mappings
- [x] 1.3 Lookup and deduplication contract tests
- [x] 1.4 Minimal typed registry service
- [x] 1.5 Refactor and focused verification

## TDD Cycle Evidence

| Task | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 1.1 | `tests/spec/test_projects_spec.py` | Integration | N/A (new) | ✅ Missing model import | ✅ 5/5 | ✅ Schema, uniqueness, seed, vector, constraint cases | ✅ Clean |
| 1.2 | `tests/spec/test_projects_spec.py` | Integration | N/A (new) | ✅ Missing `Project` mappings | ✅ 5/5 | ✅ Model and database round trips | ✅ Minimal schema/mappings |
| 1.3 | `tests/spec/test_projects_spec.py` | Integration | N/A (new) | ✅ Missing service import | ✅ 5/5 | ✅ Exact, bounded, and deduplication paths | ✅ Clean |
| 1.4 | `tests/spec/test_projects_spec.py` | Integration | N/A (new) | ✅ Service contract failure | ✅ 5/5 | ✅ Exact lookup, four-candidate bound, duplicate purpose | ✅ Minimal API |
| 1.5 | `tests/spec/test_projects_spec.py` | Integration | N/A (new) | ✅ Prior RED evidence | ✅ 13/13 focused tests | ✅ Full WU command | ✅ Clean |

## Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command and exact result | `DATABASE_URL='postgresql+psycopg://app:app@localhost:5436/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5436/lumat' uv run pytest tests/integration/test_db.py tests/spec/test_projects_spec.py -q` → **13 passed**, 1 warning, exit 0 |
| Runtime harness command/scenario and exact result | pytest `migrated_db` ran `db/migrate.sh` against dedicated `:5436`; migration 024 and registry scenarios passed. No separate service runtime boundary exists in WU-1. |
| Rollback boundary | Revert `db/migrations/024_projects.sql`, `app/models.py` project mappings, `app/services/projects.py`, `tests/spec/test_projects_spec.py`, and WU-1 bookkeeping; existing `Memory.proyecto` and unique constraint remain untouched. |

## Graph Check

Supplied graph consulted (not rebuilt):

- Nodes: `models.py`, `Memory`, `services/kb.py`, `embed_texts()`, `tukulpan.py`, `memory.py`, `test_db.py`, `test_memory_spec.py`.
- Edges/context: `Memory` → memories schema and unique key; `services/kb.py` → `embed_texts()` local 384d policy; `tukulpan.py` → memory embedding/search boundary; `models.py` → `Base` ORM mappings.
- The supplied report identifies `/home/stefan/repos/lumat-agent` rather than this worktree; it was used as supplied and not rebuilt per instruction.

## Deviations and Issues

None from the WU-1 design. WU-2 through WU-5 remain intentionally unimplemented.
