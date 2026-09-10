# Tasks: Harness Lumat

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 650–900 (implementation, tests, config/docs) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 context/config → PR 2 planner/guardrails → PR 3 compaction/recovery/terminology |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

Stacked-to-main is selected for independently mergeable slices. PR 1 targets main; later slices target the previous slice branch until it merges.

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Context, state, and read-only config | PR 1 | `uv run pytest tests/unit/test_assistant_harness.py tests/unit/test_prompts.py` | N/A: pure contracts; DB scenarios follow in PR 2 | assistant state/context/config files and tests |
| 2 | Structured planner and ordered guardrails | PR 2 | `uv run pytest tests/unit/test_assistant_planner.py tests/integration/test_assistant_harness_guardrails.py` | Admin panel turn with `TEST_ADMIN_DB_URL` | planner/dispatch/guardrail files and tests |
| 3 | Compaction, recovery, SSE, terminology | PR 3 | `TEST_ADMIN_DB_URL=... uv run pytest tests/integration/test_assistant_harness_session.py` | Authorized admin turn, approval, SSE replay, reload | compaction/recovery/routes/docs changes |

## Phase 1: Context and Configuration

- [x] 1.1 **RED first:** add estimator/state contract tests for HL-1/HL-3, IAC-2, AO-1; then update `app/chat/assistant/state.py` and `app/config.py` for UTF-8/4 ceiling, 4,000 injection budget, additive `context_meta|planner|guardrails|compaction|extension_hooks`, and 8,000/4,000/2,000 limits.
- [x] 1.2 **RED first:** add `tests/integration/test_assistant_harness_context.py` ordered-history, attachment-truncation, and Tukulpan-seam tests for HL-1/IAC-2; then wire `load_panel_context`/`flush_panel_session` through `app/services/agent_chat.py` and `app/chat/assistant/nodes.py` (panel+pinned only).
- [x] 1.3 **RED first:** add `tests/unit/test_assistant_config.py` read-only complete/missing-reference and skill-exclusion tests for AC-6/AC-9; then extend `app/services/prompts.py`, `agent/registry.yaml`, `agent/prompts/assistant_plan.md`, `agent/prompts/assistant_respond.md`, `agent/prompts/assistant_classify.md`, and `agent/personas/assistant.md` without loading skills.

## Phase 2: Planning and Guardrails

- [ ] 2.1 **RED first:** add `tests/unit/test_assistant_planner.py` strict-schema, extra-field, tool-requirement, complex-hook, and bounded-fallback tests for HL-2/AO-1; then implement planner models/fallback in `app/chat/assistant/state.py` and `app/chat/assistant/nodes.py`.
- [ ] 2.2 **RED first:** add `tests/integration/test_assistant_harness_guardrails.py` whitelist-rejection, typed-argument, cost, exact-approval, and audit/evidence-order tests for HL-2/AO-2/AO-3/AT-1; then enforce schema→whitelist→args→cost→approval→handler→audit→evidence in `app/chat/assistant/tools/registry.py`, `app/chat/assistant/nodes.py`, and existing audit/cost seams.

## Phase 3: Session, Compatibility, and Scope

- [ ] 3.1 **RED first:** add `tests/integration/test_assistant_harness_session.py` threshold-flush, newest-2,000 retention, rotation-metadata, and recovery-no-duplicate tests for HL-3/AO-1; then update `app/services/agent_chat.py` and `app/chat/assistant/recovery.py` with DB-authoritative persistence and no checkpointer.
- [ ] 3.2 **RED first:** add `tests/integration/test_assistant_harness_compatibility.py` admin-only SSE, exact-approval replay, streaming-failure recovery, compatible-serialization, and WhatsApp-isolation tests for IAC-6/IAC-2/AO-2/AO-3; then wire `app/panel/api/routes/chat.py`, `app/chat/assistant/graph.py`, and `app/services/agent_chat.py` while preserving shipped contracts.
- [ ] 3.3 **RED first:** add `tests/unit/test_assistant_extensions.py` hook non-execution and terminology-consumer inventory checks for HL-3/AC-6; then expose metadata-only SDB/panel-sub-agent hooks and rename old SDB references in `agent/skills/sdb.md`, `agent/README.md`, `openspec/specs/agent-config/`, and every inventoried consumer. Do not implement internals.

## Phase 4: Verification

- [ ] 4.1 Verify HL-1/HL-2/HL-3, IAC-2/IAC-6, AO-1/AO-2/AO-3, AT-1, and AC-6/AC-9 with focused cycles, then `TEST_ADMIN_DB_URL=... uv run pytest tests/`; all threat rows are N/A and require no RED tests.
