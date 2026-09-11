```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:f8fe4ed25061aca47163df2af573cb1668255b7dbbd8f2474c7e3b6332b50583
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 5/5
scenarios: 15/15
test_command: DATABASE_URL='postgresql+psycopg://app:app@localhost:5433/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5433/lumat' uv run pytest tests/
test_exit_code: 0
test_output_hash: sha256:7b191340121f19c8a2c1fcca261e56b84af52c1fed8b98e5c81c515d1c967ed9
build_command: uv run python -m compileall -q app tests
build_exit_code: 0
build_output_hash: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

## Verification Report

**Change**: tukulpan
**Version**: N/A
**Mode**: Strict TDD

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 12 |
| Tasks complete | 12 |
| Tasks incomplete | 0 |

### Build & Tests Execution
**Build**: ✅ Passed — `uv run python -m compileall -q app tests` (exit 0).

**Tests**: ✅ 683 passed / ❌ 0 failed / ⚠️ 1 warning in 398.50s.
The required PostgreSQL/pgvector harness command passed exactly. The warning is a pre-existing `RuntimeWarning` about coroutine `_publish_all` not being awaited in `tests/integration/test_webhook_ingest.py`.

**Coverage**: ➖ Not available.

### Spec Compliance Matrix
| Requirement | Scenario | Runtime test and implementation evidence | Result |
|-------------|----------|-------------------------------------------|--------|
| MEM-2 | Canonical and legacy imports | `tests/spec/test_memory_spec.py::test_mem2_canonical_and_legacy_services_are_identical`; `app/services/memory.py:1-3` | ✅ COMPLIANT |
| MEM-2 | Upsert writes memory | `tests/spec/test_memory_spec.py::test_mem2_upsert_writes_memory`; `app/services/tukulpan.py:114-169` | ✅ COMPLIANT |
| MEM-2 | Non-default project rejected | `tests/spec/test_memory_spec.py::test_mem2_non_default_project_rejected`; `app/services/tukulpan.py:85-90,133` | ✅ COMPLIANT |
| MEM-3 | Explicit search only | `tests/integration/test_assistant_harness_context.py::test_assembly_does_not_search_and_reports_fixed_budget_metadata`; `app/services/agent_chat.py:104-117`, `app/chat/assistant/nodes.py:21-32` | ✅ COMPLIANT |
| MEM-3 | Threshold recall | `tests/spec/test_memory_spec.py::test_mem3_threshold_recall_and_order`; `app/services/tukulpan.py:320-389` | ✅ COMPLIANT |
| MEM-3 | Panel and WhatsApp isolation | `tests/spec/test_memory_spec.py::test_mem3_panel_and_whatsapp_entities_are_isolated`; `app/services/tukulpan.py:353-367` | ✅ COMPLIANT |
| MEM-3 | Role isolation | `tests/spec/test_memory_spec.py::test_mem3_role_isolation`; `app/services/tukulpan.py:353-367` | ✅ COMPLIANT |
| MEM-3 | Empty result | `tests/spec/test_memory_spec.py::test_mem3_empty_result_no_fallback`; `app/services/tukulpan.py:369-389` | ✅ COMPLIANT |
| MEM-7 | Milestone and recap writes | `tests/spec/test_memory_spec.py::test_mem7_milestone_and_decision_use_meaningful_types`, `test_mem7_recap_has_bounded_schema_and_idempotent_key`; `app/services/tukulpan.py:172-249` | ✅ COMPLIANT |
| MEM-7 | Idempotent retry and failure | `tests/spec/test_memory_spec.py::test_mem7_recap_failure_returns_degraded_evidence_and_keeps_session_usable`, `tests/integration/test_assistant_harness_session.py::test_compaction_write_failure_is_degraded_evidence_and_rotation_is_not_successful`; `app/services/tukulpan.py:233-249`, `app/chat/assistant/nodes.py:339-358` | ✅ COMPLIANT |
| MEM-7 | Deferred boundaries | `tests/unit/test_assistant_extensions.py` and `tests/integration/test_assistant_harness_context.py::test_panel_loader_never_falls_back_to_hybrid_search`; changed-file diff adds no SDB subgraph, Cortex-session mode, archived rename, second bus, or implicit search | ✅ COMPLIANT |
| HL-1 | Deterministic context assembly | `tests/integration/test_assistant_harness_context.py::test_context_keeps_history_in_created_order_and_pinned_first`, `test_panel_projection_uses_canonical_scope_and_preserves_newest_rows`; `app/services/agent_chat.py:117-186` | ✅ COMPLIANT |
| HL-1 | Context over budget | `tests/integration/test_assistant_harness_context.py::test_context_truncates_attachments_after_history`, `test_assembly_does_not_search_and_reports_fixed_budget_metadata`; `app/chat/assistant/state.py:11-27`, `app/services/agent_chat.py:125-185` | ✅ COMPLIANT |
| HL-3 | Preflight compaction | `tests/integration/test_assistant_harness_session.py::test_compaction_writes_bounded_recap_before_rotation`, `test_compaction_records_rotation_metadata`; `app/services/agent_chat.py:48-101` | ✅ COMPLIANT |
| HL-3 | Recovery after interruption | `tests/integration/test_assistant_harness_session.py::test_recovery_replays_each_persisted_event_once`, `test_compaction_write_failure_is_degraded_evidence_and_rotation_is_not_successful`; `app/services/agent_chat.py:73-100`, `app/chat/assistant/nodes.py:347-357` | ✅ COMPLIANT |

**Compliance summary**: 15/15 scenarios compliant; 5/5 requirements satisfied.

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| MEM-2 | ✅ Implemented | `tukulpan.py` is canonical; legacy module is forwarding-only; `kb.embed_texts()` is reused; default-project guard runs before embedding/DB access; CRUD identifiers and model/table names are unchanged. |
| MEM-3 | ✅ Implemented | Hybrid search remains explicit, scoped, thresholded, fused-score ranked, and without fallback; panel projection uses `panel/thread:{id}` and customer reads retain customer scope. |
| MEM-7 | ✅ Implemented | Meaningful milestone/decision helpers and bounded idempotent recap are present; savepoint degradation is surfaced; no synthetic metadata-only row or per-message writer was added. |
| HL-1 | ✅ Implemented | Fixed 4,000-token budget, pinned-first partition, source IDs, truncation metadata, and graph propagation are present. |
| HL-3 | ✅ Implemented | Recap is attempted before rotation; rotation occurs only after a durable write; failure becomes degraded evidence and DB history remains authoritative. |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| Canonical Tukulpan boundary plus forwarding alias | ✅ Yes | `app/services/tukulpan.py` contains implementation; `memory.py` re-exports it. |
| Deterministic panel projection, no implicit search | ✅ Yes | `list_for_entity()` is used by panel loading; `hybrid_search()` is not called by assembly/loading. |
| Bounded recap with stable idempotency key | ✅ Yes | Key is `assistant-recap:{thread_id}:{last_source_message_id}` and payload preserves source/truncation evidence. |
| Failure degradation without false success | ✅ Yes | Nested savepoint catches write failures; compaction and graph evidence report degraded status. |
| Deferred SDB/session/event-bus/schema boundaries | ✅ Yes | No such runtime boundary was introduced in the change diff. |

### Strict TDD Evidence
The supplied apply ledger records RED then GREEN evidence for all 12 tasks (apply-progress.md:28-41), including focused runtime safety nets and triangulation. The retained RED tests drove the canonical import, projection, recap, isolation, and degraded-compaction implementations; the full GREEN suite passed at this revision.

### Compatibility and Baseline Classification
- `memory.upsert is tukulpan.upsert` and the corresponding CRUD identities pass (`tests/spec/test_memory_spec.py:104-110`).
- Persisted `Memory` table, enum, and identifiers are untouched by the change; the diff contains no model or migration changes.
- All canonical creation/update paths default to and guard `proyecto='default'` (`app/services/tukulpan.py:85-90,114-169`).
- WhatsApp customer paths remain in Tukulpan and retain customer scope; panel paths use `panel/thread:{id}`.
- Commit `0022759b` only restores the archived harness terminology test/spec path. The base `c6f3c636` terminology tests were red because the archive path was missing; that baseline fallout is not attributed to Tukulpan.

### Issues Found
**CRITICAL**: None.

**WARNING**: One pre-existing runtime warning: `_publish_all` coroutine was never awaited during `test_startup_sweep_reprocesses_received`. It does not fail the suite and is outside the Tukulpan diff.

**SUGGESTION**: Add a focused regression test proving ID-based `delete`/`set_mark` cannot mutate a non-default project row if such rows can exist through administrative or migration paths; current public creation/update writes are guarded and all shipped tests pass.

### Verdict
**PASS WITH WARNINGS**

All 12 tasks, 5 requirements, and 15 scenarios are satisfied at evidence revision `0022759b`; the only finding is a non-blocking pre-existing test warning.
```
