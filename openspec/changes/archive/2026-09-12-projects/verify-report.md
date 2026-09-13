```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:837c45ab33dd952fc1852afa929477e163a3685e4456e16f0dea5caf0a9cb208
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 12/12
scenarios: 27/27
test_command: DATABASE_URL='postgresql+psycopg://app:app@localhost:5436/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5436/lumat' uv run pytest tests/spec/test_projects_spec.py tests/spec/test_memory_spec.py tests/spec/test_sdb_phases.py tests/spec/test_sdb_recovery.py tests/integration/test_db.py tests/integration/test_migrations.py tests/integration/test_sdb_persistence.py tests/functional/test_api_projects.py tests/unit/test_assistant_tools.py -p no:warnings
test_exit_code: 0
test_output_hash: sha256:837c45ab33dd952fc1852afa929477e163a3685e4456e16f0dea5caf0a9cb208
build_command: npm run build
build_exit_code: 0
build_output_hash: sha256:7ed63c3a8a10dd4ba1d0d84110399ae25e6e78e503503b9c6a980e28e35152d8
```

# Verification Report

**Change**: `projects`
**Version**: N/A
**Mode**: Strict TDD

## Completeness

| Metric | Value |
|---|---:|
| Tasks total | 21 |
| Tasks complete | 21 |
| Tasks incomplete | 0 |

## Build & Tests Execution

| Command | Observed result |
|---|---|
| `DATABASE_URL='postgresql+psycopg://app:app@localhost:5436/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5436/lumat' uv run pytest tests/spec/test_projects_spec.py tests/spec/test_memory_spec.py tests/spec/test_sdb_phases.py tests/spec/test_sdb_recovery.py tests/integration/test_db.py tests/integration/test_migrations.py tests/integration/test_sdb_persistence.py tests/functional/test_api_projects.py tests/unit/test_assistant_tools.py -p no:warnings` | **100 passed in 50.46s**, exit 0; output hash `sha256:837c45ab33dd952fc1852afa929477e163a3685e4456e16f0dea5caf0a9cb208` |
| `cd web && npm test -- --run` | **71 test files, 515 tests passed**, exit 0; output hash `sha256:b2d4958500f4aa529206d107b9dd85e4bcb434da86ce8fa46c2fc69ed7c18237` |
| `cd web && npm run build` | TypeScript and Vite build succeeded; **76 modules transformed**, exit 0; output hash `sha256:7ed63c3a8a10dd4ba1d0d84110399ae25e6e78e503503b9c6a980e28e35152d8` |
| `DATABASE_URL='postgresql+psycopg://app:app@localhost:5436/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5436/lumat' uv run pytest tests/unit/test_assistant_extensions.py::test_all_inventoried_lumat_sdb_consumers_use_guardrails_terminology -q -p no:warnings` | **1 pre-existing failure**, exit 1: `openspec/specs/agent-config/spec.md`; unrelated terminology inventory, not changed by this change |

The full `uv run pytest tests/` suite was not run because the repository documents that it exceeds 300 seconds. Coverage percentage was not collected; runtime scenario coverage below is based on the focused backend and complete web runner.

## Spec Compliance Matrix

| Requirement | Scenario | Runtime covering test | Result |
|---|---|---|---|
| Project registry identity and purpose | Exact project lookup | `tests/spec/test_projects_spec.py::test_find_prefers_exact_slug_without_embedding` | COMPLIANT |
| Project registry identity and purpose | Bounded purpose candidates | `tests/spec/test_projects_spec.py::test_find_returns_at_most_three_close_candidates_and_requires_approval` | COMPLIANT |
| Agent-owned lifecycle operations | Create a distinct project | `tests/spec/test_projects_spec.py::test_project_slug_is_normalized_and_unique` | COMPLIANT |
| Agent-owned lifecycle operations | Purpose deduplication is uncertain | `tests/spec/test_projects_spec.py::test_create_deduplicates_normalized_purpose_as_ambiguous`, `test_create_deduplicates_semantically_similar_purpose_as_ambiguous` | COMPLIANT |
| Stable rename and atomic artifact migration | Approved rename | `tests/spec/test_projects_spec.py::test_rename_records_name_alias_and_audit_without_changing_slug` | COMPLIANT |
| Stable rename and atomic artifact migration | Rename cannot complete safely | `tests/spec/test_projects_spec.py::test_rename_validation_failure_leaves_registry_and_artifacts_unchanged` | COMPLIANT |
| Merge preserves target and rejects active runs | Merge with no active runs | `tests/spec/test_projects_spec.py::test_merge_preserves_target_and_records_source_alias` | COMPLIANT |
| Merge preserves target and rejects active runs | Merge during active SDB | `tests/spec/test_projects_spec.py::test_rename_and_merge_reject_active_runs_before_changes` | COMPLIANT |
| Namespace selection is approval-safe | Approved semantic selection | `tests/unit/test_assistant_tools.py::test_approved_project_find_selects_candidate` | COMPLIANT |
| Namespace selection is approval-safe | Expired or absent approval | `tests/unit/test_assistant_tools.py::test_project_approval_rejects_replay_expiry_and_changed_payload` | COMPLIANT |
| MEM-2 Tukulpan boundary | Authorized project propagation | `tests/spec/test_memory_spec.py` project authorization scenarios | COMPLIANT |
| MEM-2 Tukulpan boundary | Default compatibility and unauthorized namespace | `tests/spec/test_memory_spec.py` default/unauthorized write scenarios | COMPLIANT |
| MEM-8 typed native artifacts | Typed artifact persistence | `tests/integration/test_sdb_persistence.py` typed project artifact scenarios | COMPLIANT |
| MEM-8 typed native artifacts | Default project compatibility | `tests/spec/test_sdb_recovery.py` default compatibility scenarios | COMPLIANT |
| MEM-8 typed native artifacts | Broad recall is not implicit | `tests/spec/test_memory_spec.py` scoped search scenarios | COMPLIANT |
| SDB-5 propagation | Run artifact isolation | `tests/spec/test_sdb_phases.py`, `tests/integration/test_sdb_persistence.py` | COMPLIANT |
| SDB-5 propagation | Cross-thread or project-level artifact | `tests/integration/test_sdb_persistence.py` entity identity scenarios | COMPLIANT |
| SDB-5 propagation | Phase and recovery compatibility | `tests/spec/test_sdb_recovery.py`, `tests/spec/test_sdb_phases.py` | COMPLIANT |
| AT-4 typed project tools | Exact project read | `tests/unit/test_assistant_tools.py::test_exact_project_read_is_unapproved` | COMPLIANT |
| AT-4 typed project tools | Lifecycle tool classification | `tests/unit/test_assistant_tools.py` whitelist/classification assertions | COMPLIANT |
| AT-5 project approval boundary | Semantic ambiguity | `tests/unit/test_assistant_tools.py::test_ambiguous_project_find_requires_approval_without_selecting_namespace` | COMPLIANT |
| AT-5 project approval boundary | Approved mutation | `tests/unit/test_assistant_tools.py` approval digest/expiry/replay/changed-payload scenarios | COMPLIANT |
| PNL-APP-1 routing | Projects navigation | `web/src/components/domain/AppShell.test.tsx`, `web/src/components/domain/panelRoutes.test.ts` | COMPLIANT |
| PNL-APP-1 routing | Compatibility deep links | `web/src/components/domain/AppShell.test.tsx` | COMPLIANT |
| PNL-APP-1 routing | History and authorization remain safe | `web/src/components/domain/AppShell.test.tsx` | COMPLIANT |
| PNL-APP-27 read-only browse | Project detail contents | `tests/functional/test_api_projects.py`, `web/src/components/pages/ProjectsPage.test.tsx` | COMPLIANT |
| PNL-APP-27 read-only browse | Read-only boundary | `tests/functional/test_api_projects.py`, `web/src/components/pages/ProjectsPage.test.tsx` | COMPLIANT |

**Compliance summary**: 27/27 scenarios compliant; 12/12 requirements covered.

## Correctness (Static Evidence)

| Area | Status | Evidence |
|---|---|---|
| Migration/model foundation | Implemented | `db/migrations/024_projects.sql:3-38` creates registry, alias/audit tables, `vector(384)`, normalized slug index, and active `default` seed; `app/models.py:151-198` maps all three models. |
| Deduplication and ambiguity | Implemented | `app/services/projects.py:13-14,59-148` enforces cosine `>=0.85`, top-three candidates, exact lookup, normalized-purpose deduplication, and approval-bound reuse/distinct creation. |
| Lifecycle valves | Implemented | `app/services/projects.py:168-289` locks rows, checks active/recoverable runs, validates conflicts, protects default, records aliases/audits, and mutates in one session transaction. |
| Authorized writes | Implemented | `app/services/tukulpan.py:88-98,122-177` rejects non-default writes without the opaque project capability; `app/services/agent_chat.py:88-105` revalidates SDB authorization. |
| SDB propagation | Implemented | `app/chat/assistant/nodes.py:179-243` preserves the seven phases and project-bearing scope; persistence/recovery tests passed against PostgreSQL `:5436`. |
| Typed tools and approval | Implemented | `app/chat/assistant/tools/registry.py:99-127,244-257` defines bounded typed tools; `app/chat/assistant/approval.py:33-73,76-146` binds project payloads to SHA-256 and 15-minute approval validation. |
| Read-only panel | Implemented | `app/panel/api/routes/projects.py:17-39` exposes GET-only operator routes filtered to `scope='panel'` and `topic_key LIKE 'sdb:%'`; `web/src/components/pages/ProjectsPage.tsx:10-26` has list/detail presentation with no mutation controls. |

## Design Coherence

| Decision | Followed? | Evidence |
|---|---|---|
| Dedicated registry beside `memories` | Yes | Migration and model mappings preserve `Memory.proyecto` and add project tables only. |
| Stable slug with aliases instead of namespace rewrite | Yes | Rename keeps `row.slug` and writes `ProjectAlias`; merge preserves target and archives source. |
| Agent-only mutation boundary | Yes | Opaque `_ProjectAuthorization` is required for non-default Tukulpan writes; panel depends on `require_operator_json` only for reads. |
| Existing seven SDB phases and recovery remain unchanged | Yes | Phase implementations remain CLARIFY/SPEC/PLAN/APPROVE/EXECUTE/VERIFY/DELIVER; focused phase/recovery suites passed. |
| SDB-only read surface | Yes | Detail query requires panel scope and `sdb:%` topic keys; no WhatsApp conversation query is present. |

## Issues Found

**CRITICAL**: None.

**WARNING**:

1. The full backend suite was not executed because it is known to exceed 300 seconds; verification used the complete project-focused backend set plus the complete web runner. Evidence: test execution table above.
2. `tests/unit/test_assistant_extensions.py::test_all_inventoried_lumat_sdb_consumers_use_guardrails_terminology` fails on unchanged `openspec/specs/agent-config/spec.md`; this is the documented pre-existing main-branch failure and is unrelated to `projects`.
3. Web tests emit existing React `act(...)` and jsdom navigation warnings, but all 515 tests passed and the build succeeded.

**SUGGESTION**:

1. Update the unrelated terminology inventory failure in its owning `sdb-native`/agent-config change rather than coupling it to this project namespace change.

## Verdict

**PASS WITH WARNINGS** — all 12 requirements and 27 scenarios have passing focused runtime coverage, all tasks are complete, and the production web build succeeds; warnings are limited to the known unrelated failure, non-failing test warnings, and the documented full-suite timeout limitation.
