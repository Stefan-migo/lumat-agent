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

## WU-3 SDB Authorization and Propagation

### Status

- Work unit: WU-3 (SDB Authorization and Propagation), stacked PR slice 3/5
- Delivery: `auto-chain`, `stacked-to-main`
- Mode: Strict TDD
- State: ready for verification
- Scope: WU-3 only; WU-4 and WU-5 remain intentionally unimplemented.

### Completed Tasks

- [x] 3.1 Injection rejection, project-aware artifact, recovery, identity, and phase RED tests
- [x] 3.2 Authorized project propagation through assistant state and SDB persistence/recovery
- [x] 3.3 Focused refactor and stable verification

### TDD Cycle Evidence

| Task | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 3.1 | `tests/integration/test_sdb_persistence.py`, `tests/spec/test_sdb_phases.py`, `tests/spec/test_sdb_recovery.py` | Integration/spec | ✅ 46/46 baseline | ✅ Injection and project propagation tests failed before implementation | ✅ 59/59 focused suite | ✅ Default, authorized namespace, recovery forwarding, and seven-phase paths | ✅ Clean |
| 3.2 | `app/chat/assistant/state.py`, `app/chat/assistant/nodes.py`, `app/chat/assistant/graph.py`, `app/services/agent_chat.py` | Integration/spec | ✅ Existing SDB suite | ✅ Missing authorization seam and scope project failed | ✅ Authorized SPEC/STATE/RESULT persistence passes | ✅ Capability validation, default compatibility, and recovery re-authorization | ✅ Clean |
| 3.3 | Actual equivalents listed below | Integration/spec | ✅ 59/59 | ✅ Prior RED evidence | ✅ 59/59, repeated | ✅ Same deterministic result on both runs | ✅ Clean |

### Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command and exact result, run 1 | `DATABASE_URL='postgresql+psycopg://app:app@localhost:5436/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5436/lumat' uv run pytest tests/integration/test_chat_state.py tests/integration/test_assistant_chat.py tests/integration/test_sdb_persistence.py tests/spec/test_sdb_phases.py tests/spec/test_sdb_recovery.py tests/spec/test_sdb_trigger.py -p no:warnings` → **59 passed in 27.72s**, exit 0 |
| Focused test command and exact result, run 2 | Same command immediately repeated → **59 passed**, exit 0 |
| Runtime harness command/scenario and exact result | The focused integration suite exercised the real LangGraph/SDB persistence and recovery seams against dedicated PostgreSQL `:5436`; **59 passed**. |
| Rollback boundary | Revert `app/chat/assistant/state.py`, `app/chat/assistant/nodes.py`, `app/chat/assistant/graph.py`, `app/services/agent_chat.py`, the three WU-3 test updates, and WU-3 bookkeeping; WU-1/WU-2 registry, lifecycle, and Tukulpan capability changes remain intact. |

### Graph Check

- Supplied graph consulted (not rebuilt): nodes `assistant/state.py` (`AssistantState`), `assistant/graph.py` (`run_assistant`, `build_assistant_graph`), `assistant/nodes.py` (`sdb_clarify`, `sdb_spec`, `sdb_plan`, `sdb_execute`, `sdb_verify`, `sdb_deliver`), `services/agent_chat.py` (`persist_sdb_state`, `_run_sdb_tasks`, `resume_thread`), `services/tukulpan.py` (`persist_sdb_artifact`), `services/projects.py` (`agent_context`), `recovery.py`, `test_sdb_persistence.py`, `test_sdb_phases.py`, and `test_sdb_recovery.py`.
- Edges/context: `run_assistant` → assistant graph state; SDB phase nodes → unchanged seven-node graph; `persist_sdb_state` → Tukulpan typed artifact seam; Tukulpan → project authorization capability; `resume_thread`/`_run_sdb_tasks` → checkpoint recovery; persistence tests → panel scope, thread identity, and `sdb:{run_id}:{kind}` keys.
- Queries/paths: `graphify query "assistant state sdb_scope proyecto validated project"`; `graphify query "agent_chat persist_sdb_state recover_sdb state graph nodes phases"`; `graphify query "project propagation selected authorized project run_assistant persist_sdb_state"`; paths `assistant/state.py → services/agent_chat.py` (no directed path found), `chat/assistant/nodes.py → chat/assistant/recovery.py` (ambiguous same-node resolution), and `persist_sdb_state() → agent_chat.py`.

### Deviations and Issues

- The task-listed `tests/integration/test_agent_chat.py` and `tests/spec/test_sdb_native_spec.py` do not exist. Closest real equivalents were used: `tests/integration/test_assistant_chat.py`, `tests/integration/test_sdb_persistence.py`, `tests/spec/test_sdb_phases.py`, `tests/spec/test_sdb_recovery.py`, and `tests/spec/test_sdb_trigger.py`.
- No seven phases were added or reordered. `proyecto` is derived only from the service-issued `_ProjectAuthorization`; arbitrary `proyecto` injection into `persist_sdb_state` is rejected by the API boundary.
- The known pre-existing `tests/unit/test_assistant_extensions.py::test_all_inventoried_lumat_sdb_consumers_use_guardrails_terminology` failure was not run or changed in this slice.

## WU-4 Typed Tools and Approval

### Status

- Work unit: WU-4 (Typed Tools and Approval), stacked PR slice 4/5
- Delivery: `auto-chain`, `stacked-to-main`
- Mode: Strict TDD
- State: ready for verification
- Scope: WU-4 only; WU-5 panel API/UI remains intentionally unimplemented.

### Completed Tasks

- [x] 4.1 Typed schema, classification, whitelist, ambiguity, approval digest/TTL, replay, and changed-payload RED tests
- [x] 4.2 Typed project tools, registry allow-list, and canonical project approval payloads
- [x] 4.3 Focused assistant tool/chat refactor and repeated verification

### TDD Cycle Evidence

| Task | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 4.1 | `tests/unit/test_assistant_tools.py` | Unit | ✅ 13/13 | ✅ Missing project tools and approval payload behavior | ✅ 5 new contract tests pass | ✅ exact read, invalid bounds, whitelist, ambiguity, mutation/replay/change cases | ✅ Clean |
| 4.2 | `app/chat/assistant/tools/registry.py`, `app/chat/assistant/approval.py`, `agent/registry.yaml` | Unit/integration | ✅ 13/13 | ✅ Registry/approval contracts failed before implementation | ✅ Typed handlers and digest contract pass | ✅ six tools, read/write classes, registry load, exact approval | ✅ Clean |
| 4.3 | `tests/integration/test_assistant_tools.py`, `tests/integration/test_assistant_chat.py`, `tests/unit/test_assistant_tools.py`, `tests/unit/test_agent_registry.py`, `tests/spec/test_sdb_recovery.py` | Integration/spec/unit | ✅ Existing assistant suite | ✅ Prior RED evidence | ✅ 31/31 focused tests pass | ✅ repeated suite and registry/SDB compatibility suite | ✅ Clean |

### Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command and exact result, run 1 | `DATABASE_URL='postgresql+psycopg://app:app@localhost:5436/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5436/lumat' uv run pytest tests/integration/test_assistant_tools.py tests/integration/test_assistant_chat.py tests/unit/test_assistant_tools.py -q -p no:warnings` → **31 passed**, exit 0 |
| Focused test command and exact result, run 2 | Same command immediately repeated → **31 passed**, exit 0 |
| Additional compatibility command | Same database environment with `uv run pytest tests/unit/test_agent_registry.py tests/unit/test_assistant_config.py tests/spec/test_sdb_recovery.py -q -p no:warnings` → **22 passed**, exit 0 |
| Runtime harness command/scenario and exact result | Focused integration tests exercised the real assistant approval endpoint, execution path, persisted thread state, and dedicated PostgreSQL `:5436`; **31 passed** on both runs. |
| Rollback boundary | Revert `app/chat/assistant/tools/registry.py`, `app/chat/assistant/approval.py`, `app/chat/assistant/nodes.py`, `agent/registry.yaml`, WU-4 tests, and WU-4 bookkeeping; WU-1–WU-3 registry, lifecycle, Tukulpan, and SDB propagation changes remain intact. |

### Graph Check

- Supplied graph consulted (not rebuilt): nodes `registry.py`, `ToolDefinition`, `execute_tool()`, `approval.py`, `issue_approval()`, `validate_approval()`, `validate_execution()`, `consume_approval()`, `agent_registry.py`, `projects.py`, `find()`, `create()`, `rename()`, `archive()`, `merge()`, `nodes.py`, `execute()`, `test_assistant_tools.py`, and `test_assistant_chat.py`.
- Edges/context: `execute_tool()` → `ToolDefinition`/typed argument models and project service handlers; `nodes.execute()` → whitelist and approval validation immediately before execution; `issue_approval()`/`validate_execution()` → exact SHA-256 tool/project payload and expiry; `agent_registry.py` → `agent/registry.yaml` allow-list; project handlers → `app/services/projects.py` lifecycle boundary.
- Queries/paths: `graphify query "typed assistant project tools registry approval service execution"`; `graphify path "app/chat/assistant/tools/registry.py" "app/chat/assistant/approval.py"` (no directed path); `graphify path "app/chat/assistant/approval.py" "app/services/projects.py"` (ambiguous/no directed path). `GRAPH_REPORT.md` was read; supplied graph was not rebuilt.

### Deviations and Issues

- `tests/unit/test_assistant_tools.py` exists and was included as requested.
- `tests/integration/test_assistant_tools.py` contains the existing automation runtime harness; project tool runtime contracts are covered at the unit service seam in this slice. WU-5 panel API/UI was not implemented.
- The pre-existing terminology failure in `tests/unit/test_assistant_extensions.py` was not fixed.
