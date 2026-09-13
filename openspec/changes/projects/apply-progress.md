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

## Bounded Correction

- Scope: Corrected only the three WU-1 gate findings; WU-2 through WU-5 remain untouched.
- Approval boundary: Removed the public `allow_ambiguous` parameter. `create` now returns approval-bound candidates and does not add a project when either normalized-purpose deduplication or semantic deduplication finds a candidate.
- Semantic policy: `create` shares `find`'s cosine `>=0.85`, top-three candidate policy through `_semantic_candidates`.
- Test stability: Rewrote the `Memory` unique-constraint assertion to match its explicit column set; added coverage for semantic create deduplication, persistence prevention, and absence of the bypass parameter.

### Correction Evidence

| Evidence | Result |
|---|---|
| Focused test command, run 1 | `DATABASE_URL='postgresql+psycopg://app:app@localhost:5436/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5436/lumat' uv run pytest tests/integration/test_db.py tests/spec/test_projects_spec.py -q` → **15 passed**, 1 warning, exit 0 |
| Focused test command, run 2 | Same command immediately repeated → **15 passed**, 1 warning, exit 0 |
| Correction commit | `9cc6c8be77e8bfea7b9d4ff3cc85e4b8eb22263e` (`fix(projects): enforce approval on ambiguous create (Slice 1/5)`) |
| Runtime harness | Dedicated PostgreSQL `:5436` via `migrated_db`; both focused runs passed. No separate service runtime boundary exists in WU-1. |
| Rollback boundary | Revert correction commit `9cc6c8be77e8bfea7b9d4ff3cc85e4b8eb22263e`; only `app/services/projects.py` and `tests/spec/test_projects_spec.py` are changed by the correction. |

### Correction Graph Check

- Nodes consulted: `projects.py`, `create()`, `find()`, `_semantic_candidates`, `ProjectCandidate`, `Project`, `services/kb.py`, `embed_texts()`, `test_projects_spec.py`, `test_create_deduplicates_normalized_purpose_as_ambiguous()`.
- Edges/context: `create()` and `find()` call `embed_texts()`; both use `Project.purpose_embedding`; `test_projects_spec.py` imports and exercises `projects.py`; `projects.py` shares the `Project` model and KB embedding boundary.
- Graph rebuilt for `/home/stefan/repos/lumat-agent-projects` from `ab7c28e9`; report updated before implementation.

## WU-2 Lifecycle and Memory Valves

### Status

- Work unit: WU-2 (Lifecycle and Memory Valves), stacked PR slice 2/5
- Delivery: `auto-chain`, `stacked-to-main`
- Mode: Strict TDD
- State: ready for verification

### Completed Tasks

- [x] 2.1 Lifecycle RED tests
- [x] 2.2 Atomic `rename`, `archive`, and `merge` lifecycle service
- [x] 2.3 Tukulpan authorization RED tests
- [x] 2.4 Agent-owned project capability authorization
- [x] 2.5 Focused refactor and stability verification

### TDD Cycle Evidence

| Task | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 2.1 | `tests/spec/test_projects_spec.py` | Integration | ✅ WU-1 focused suite | ✅ Missing lifecycle APIs | ✅ Lifecycle tests pass | ✅ rename, active runs, merge conflict, merge success, default guard | ✅ Clean |
| 2.2 | `tests/spec/test_projects_spec.py` | Integration | ✅ 13 WU-1 tests | ✅ API absence | ✅ 39 focused tests | ✅ stable locks, alias/audit, conflict/no-conflict paths | ✅ Clean |
| 2.3 | `tests/spec/test_projects_spec.py`, `tests/spec/test_memory_spec.py` | Integration | ✅ Existing memory suite | ✅ Unauthorized capability path | ✅ Authorized and unauthorized writes pass | ✅ default, authorized project, mismatched capability | ✅ Clean |
| 2.4 | `app/services/tukulpan.py` | Integration | ✅ Existing default CRUD | ✅ Non-default rejected by old guard | ✅ Capability reaches persistence | ✅ forwarding alias and SDB seam preserved | ✅ Clean |
| 2.5 | `tests/spec/test_projects_spec.py`, `tests/spec/test_memory_spec.py`, `tests/integration/test_db.py` | Integration | ✅ 39/39 | ✅ Prior RED evidence | ✅ 39/39 | ✅ Two identical runs | ✅ Clean |

### Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command and exact result | `DATABASE_URL='postgresql+psycopg://app:app@localhost:5436/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5436/lumat' uv run pytest tests/spec/test_projects_spec.py tests/spec/test_memory_spec.py tests/integration/test_db.py -q -p no:warnings` → **39 passed**, exit 0; repeated immediately with the same result: **39 passed**, exit 0. |
| Runtime harness command/scenario and exact result | Same focused command exercised `migrated_db` against dedicated PostgreSQL `:5436`; lifecycle transactions, memory capability writes, and rollback/conflict scenarios passed. |
| Rollback boundary | Revert `app/services/projects.py`, `app/services/tukulpan.py`, `tests/spec/test_projects_spec.py`, and this WU-2 bookkeeping; WU-1 registry schema/models and `app/services/memory.py` forwarding alias remain intact. |

### Graph Check

- Supplied graph consulted (not rebuilt): nodes `projects.py`, `tukulpan.py`, `models.py`, `Project`, `Memory`, `InternalChatThread`, `test_projects_spec.py`, `test_memory_spec.py`, `services/kb.py`, and `embed_texts()`.
- Edges/context: `projects.py` imports `models.py`; `Project` owns lifecycle registry rows; `tukulpan.py` owns the canonical memory write seam; `Memory` stores project namespaces; `InternalChatThread` supplies active-run state; `projects.py` uses `kb.embed_texts()` only through the existing WU-1 create path.
- Queries: `graphify query "projects.py lifecycle rename archive merge and project authorization"`; `graphify query "Project lifecycle service rename archive merge locks aliases audits active SDB runs"`; paths `projects.py → models.py` and `tukulpan.py → memory.py` (the latter had no directed path).

### Deviations and Issues

- The planned `tests/integration/test_tukulpan.py` does not exist; existing spec and SDB persistence coverage were used instead.
- Full `uv run pytest tests/ -q -p no:warnings` has three unrelated failures: migration expectations omit migration 024/projects tables, and an existing terminology inventory assertion fails in `openspec/specs/agent-config/spec.md`. The WU-2 focused suite is green and stable.
- WU-3 through WU-5 remain intentionally unimplemented.
