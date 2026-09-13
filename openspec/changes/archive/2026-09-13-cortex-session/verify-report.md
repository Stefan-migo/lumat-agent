```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:1888796a21c927c37a3198b407ee697067477558a475e2da35dd0e64305bba23
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 15/15
scenarios: 41/41
test_command: DATABASE_URL='postgresql+psycopg://app:app@localhost:5437/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5437/lumat' uv run pytest tests/integration/test_cortex_session_runtime.py tests/integration/test_sdb_persistence.py tests/integration/test_assistant_harness_compatibility.py tests/unit/test_cortex_session_loop.py tests/unit/test_cortex_session_foundation.py tests/functional/test_api_cortex_sessions.py tests/spec/test_sdb_trigger.py tests/spec/test_sdb_recovery.py tests/spec/test_sdb_phases.py
test_exit_code: 0
test_output_hash: sha256:a4063dbb08aab4894809288f5d9cb545bd0f868b0b23beab899727d48f0ba375
build_command: cd web && npm run build
build_exit_code: 0
build_output_hash: sha256:92924f4b22b8c614c364a2df8ddbae7ad77a0194f0c65d8a64549ad71b64ffdb
```

## Verification Report

**Change**: cortex-session
**Version**: N/A
**Mode**: Strict TDD — re-verification after remediation

### Completeness
| Metric | Value |
|---|---:|
| Tasks total | 10 |
| Tasks complete | 10 |
| Tasks incomplete | 0 |

### Build & Tests Execution
**Build**: ✅ Passed — `cd web && npm run build` (exit 0; TypeScript/Vite build).

**Focused tests**: ✅ 67 passed in 27.32s (exit 0). This includes CS-3, HL-5, IAC-3 failure recovery, persistence, API, assistant, and SDB suites.

**Full backend confirmation**: ⚠️ Completed in 405.50s: 796 passed, 1 failed, 2 warnings (exit 1). The sole failure is `tests/functional/test_api_assistant_capabilities.py::test_admin_capabilities_reflect_real_tools_and_runtime_config`, expecting 13 tools while the unchanged registry exposes 19. This reproduces the known base-commit failure at `1e4d39cf`; no Cortex diff touches that tools list. The focused command is the authoritative change verification command above.

**Frontend**: Apply evidence records 523 frontend tests passed; current production build independently passed.

**Coverage**: ➖ Not available; no coverage tool detected.

### Spec Compliance Matrix
All 15 requirements and all 41 scenarios were mapped. Every scenario has a passing covering test; six are deliberately marked PARTIAL where the test covers only part of the stated behavior.

| Requirement | Scenarios and evidence | Result |
|---|---|---|
| CS-1 | Open/reopen: API lifecycle + SPA tests. Invalid/free text: foundation/parser tests plus missing-gate runtime test. | ✅ / ⚠️ PARTIAL (invalid submission indirect) |
| CS-2 | Five classes/question valve unit tests. Close: API and `AgentChat.test.tsx`. | ⚠️ PARTIAL (bounded research execution) / ✅ |
| CS-3 | `test_two_cortex_decisions_survive_thread_reload`; recursive merge and SDB preservation tests. | ✅ / ✅ |
| CS-4 | Report approval, digest, and no-fabricated-execution SDB tests. | ✅ / ✅ |
| CS-5 | API browse/detail/auth and `PlanningSessions.test.tsx`. | ✅ / ✅ |
| HL-2 | Read, SDB, Cortex, and invalid-plan guardrail suites. | ✅ all 4 |
| HL-3 | Compaction tests and failure/reload recovery test. | ✅ / ⚠️ PARTIAL (no duplicate-work assertion) |
| HL-5 | Inactive routing test; `test_missing_cortex_flag_reaches_gate_and_routes_normal`. | ✅ / ✅ |
| IAC-2 | History, SDB, blocked-mode tests; CS-3 reload and merge tests. | ✅ / ✅ / ⚠️ PARTIAL (broader active-turn matrix) / ✅ |
| IAC-3 | Failure reload: `test_cortex_failure_preserves_active_session_after_thread_reload`; serializer/UI recovery tests. | ✅ / ⚠️ PARTIAL (no unified UI reload assertion) |
| IAC-7 | `AgentChat.test.tsx` close-control/literal-command equivalence. | ✅ |
| SDB-1 | Classified, explicit-admin, closed-Cortex-SPEC, conflicting-trigger tests. | ✅ all 4 |
| SDB-4 | Changed-spec, checkpoint-resume, truthful-stub tests. | ✅ all 3 |
| PNL-APP-28 | List/detail, reopen, API auth/error tests and planning page tests. | ✅ / ✅ / ⚠️ PARTIAL (no SPA failed-read test) |
| PNL-APP-29 | Active indicator and inert free-text component tests. | ✅ / ✅ |
| AC-9 | Valid registry and invalid-reference tests. | ✅ both |
| AC-12 | Valid and unknown classification declaration tests. | ✅ both |

**Compliance summary**: 35/41 fully compliant; 6/41 partial; 0 untested; 0 failing. Coverage count is 41/41 because each scenario has runtime covering evidence; partial means bounded behavioral coverage, not a missing test.

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|---|---|---|
| Fail-closed lifecycle | ✅ | Missing flag returns `invalid-session`; literal commands only; free text inert. |
| Recursive state merge | ✅ | Normal and exception paths use `merge_assistant_state`; Cortex and unrelated keys survive failed-turn reload. |
| Durable artifacts/closure | ✅ | Required decision/report keys, panel scope, thread entity, and archived-to-closed mapping are preserved. |
| Honest SDB boundary | ✅ | Handoff is SPEC/approved-plan only and execution is explicitly `not-implemented`; no execution claim. |
| API/UI contracts | ✅ | Auth matrix, lifecycle, browse/reopen, indicator, and controls are implemented and build. |
| Architecture boundary | ✅ | No new table, migration, engine, bus, planner, executor, or dependency. |

### Coherence (Design)
| Decision | Followed? | Notes |
|---|---|---|
| Existing LangGraph seam | ✅ | No second engine. |
| Nested JSONB state | ✅ | `assistant_state.cortex_session` is merged, not replaced. |
| Tukulpan closure | ✅ | Existing `ARCHIVED` maps to public `closed`. |
| Existing approval | ✅ | Exact digest/claim route reused. |
| Honesty boundary | ✅ | Only approved plan is delivered; execution remains unavailable. |
| Graphify | ⚠️ Degraded | Stale snapshot `c4d13da7`; refresh blocked and not run. Consulted `Persistence boundary for the panel assistant graph`, `PlanningSessions`, `AgentChat`, `submit_message`, `cortex_session_gate`, `record_decision`, `list_for_entity`, and `chat.py` relationships. No source changes made. |

### TDD Compliance
| Check | Result |
|---|---|
| TDD evidence and tests for all tasks | ✅ 10/10 |
| Formerly missing CS-3, HL-5, IAC-3 runtime evidence | ✅ Passing |
| Focused GREEN evidence | ✅ |
| Full-suite GREEN | ⚠️ One unrelated base failure |
| Triangulation | ⚠️ Six scenarios remain partial by scope |

### Issues Found
**CRITICAL**: None for this change.

**WARNING**:
1. The full backend command has one pre-existing capability-count failure: expected 13 tools, unchanged registry exposes 19; this is outside the Cortex diff.
2. Six scenarios remain partial: CS-1 invalid-state end-to-end submission, CS-2 bounded research execution, HL-3 duplicate-work recovery, IAC-2 full active-turn context matrix, IAC-3 unified UI recovery presentation, and PNL-APP-28 SPA failed-read rendering.
3. Graphify remains degraded read-only at stale `c4d13da7`.
4. Existing pytest/frontend warnings remain non-failing.

**SUGGESTION**: Add the six focused tests and refresh Graphify when the environment permits.

### Exactly What Improved Since Prior FAIL
- CS-3 changed from UNTESTED to COMPLIANT: two keyed decisions now pass a PostgreSQL thread-reload test.
- HL-5 missing-flag changed from UNTESTED to COMPLIANT: the runtime gate now has a passing direct test returning `invalid-session` and normal routing.
- IAC-3 stream failure changed from UNTESTED to COMPLIANT: a DB-backed failure/reload test passes.
- The production exception path in `app/services/agent_chat.py` now recursively merges failed state, preserving `cortex_session` and unrelated keys while recording `stage: failed` and `recoverable: true`.
- The full backend run now completes in 405.50s; the only failure is the known unrelated base failure, replacing the prior environmental timeout.

### Verdict
PASS WITH WARNINGS
Focused implementation verification passes, all 41 scenarios have covering runtime evidence, six remain partial by scope, and the completed full-suite failure is pre-existing and unrelated.
