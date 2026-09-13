# Apply Progress: cortex-session

## Slice

- Delivery: auto-chain, stacked-to-main
- Work unit: PR 1 — validated assistant state, literal parser, and declarations
- Scope: Phase 1 tasks T1.1–T1.2 only
- Mode: Strict TDD

## Completed Tasks

- [x] T1.1 — Added validated `CortexSession` state, recursive assistant-state merge, fail-closed validation, gate helper, and exact literal command parser.
- [x] T1.2 — Added validated Cortex classification/command declarations to the registry and exposed them through assistant runtime configuration.

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| T1.1 | `tests/unit/test_cortex_session_foundation.py` | Unit | ✅ 41/41 | ✅ Import failure before helpers | ✅ 5 passed | ✅ Active/invalid, nested/leaf, command/free text cases | ✅ Clean minimal helpers |
| T1.2 | `tests/unit/test_agent_registry.py` | Unit | ✅ 15/15 | ✅ Missing attributes/declaration validation | ✅ 19 passed | ✅ Missing, invalid classes, invalid commands | ✅ Clean validation in existing loader |

## Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command and exact result | `uv run pytest tests/unit/test_cortex_session_foundation.py tests/unit/test_agent_registry.py tests/unit/test_assistant_config.py` — passed, 24 tests |
| Runtime harness command/scenario and exact result | N/A: PR 1 contains deterministic state/parser/registry seams only; no runtime boundary is wired until PR 2 |
| Rollback boundary | Revert `app/chat/assistant/state.py`, `app/chat/assistant/nodes.py`, `app/agent_registry.py`, `app/services/prompts.py`, `agent/registry.yaml`, and the two foundation test files; later loop/API/UI work remains untouched |

## Verification Notes

- Graphify was consulted in degraded read-only mode. The worktree has no usable `graphify-out/graph.json`; refresh was explicitly blocked. Prior stale nodes/edges recorded from the planning map: `NAVIGATION → PanelShell`, `PanelShell → AgentChat`, `submit_message → assistant graph`, `record_decision ↔ list_for_entity`, and `chat.py → approval`.
- Threat matrix cases are N/A per design; no threat RED tests were added.
- Full database-backed test command is recorded in the apply handoff after execution.
- Full command: `DATABASE_URL='postgresql+psycopg://app:app@localhost:5437/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5437/lumat' uv run pytest tests/` — could not complete within 300 seconds; fail-fast replay reports 1 pre-existing failure in `tests/functional/test_api_assistant_capabilities.py::test_admin_capabilities_reflect_real_tools_and_runtime_config` (`expected 13 tools, got 19`). Unit suite passed independently: `uv run pytest tests/unit` — 107 passed.
