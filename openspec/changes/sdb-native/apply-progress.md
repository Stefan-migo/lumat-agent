# Apply Progress: Native SDB Seven-Phase Subgraph

## Work Unit

- **Unit**: WU-1 (PR1 of 5, stacked-to-main)
- **Scope**: Trigger and contracts only
- **Status**: Complete; WU-2 through WU-5 remain pending
- **Mode**: Strict TDD
- **Delivery**: auto-chain; current slice is contracts and routing gate

## Completed Tasks

- [x] WU-1 RED — trigger scenarios and threat-matrix tests
- [x] WU-1 GREEN — validated state/config contract, fail-closed gate, normal-route preservation

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| WU-1 RED | `tests/spec/test_sdb_trigger.py` | Unit | N/A (new) | ✅ Written; collection failed because `sdb_trigger_gate` did not exist | ✅ 7 passed | ✅ classified, admin, malformed, undeclared, conflicting, unauthorized, ordinary complex | ✅ Strict `SDBTrigger` validation and bounded reason codes |
| WU-1 GREEN | `tests/spec/test_sdb_trigger.py` | Unit | ✅ 30 related tests passed | ✅ Existing RED retained | ✅ 7 passed | ✅ 7 scenarios | ✅ Related suite and graph compilation passed |

## Work Unit Evidence

| Evidence | Exact result |
|---|---|
| Focused test command | `DATABASE_URL='postgresql+psycopg://app:app@localhost:5435/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5435/lumat' uv run pytest tests/spec/test_sdb_trigger.py -q` — **7 passed** |
| Related regression command | Same dedicated DB environment, `uv run pytest tests/spec/test_sdb_trigger.py tests/unit/test_assistant_planner.py tests/unit/test_assistant_config.py tests/unit/test_agent_registry.py tests/unit/test_assistant_harness.py -q` — **30 passed** |
| Runtime harness | `APP_SECRET='test-app-secret' VERIFY_TOKEN='test-verify-token' DATABASE_URL='postgresql+psycopg://app:app@localhost:5435/lumat' DEEPSEEK_API_KEY='sk-test' META_ACCESS_TOKEN='meta-test-token' META_PHONE_NUMBER_ID='123456789' PANEL_SESSION_SECRET='test-panel-session-secret' uv run python -c 'from app.chat.assistant.graph import build_assistant_graph; build_assistant_graph(); print("graph compiled")'` — **graph compiled** |
| Full suite | Dedicated DB command `DATABASE_URL='postgresql+psycopg://app:app@localhost:5435/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5435/lumat' uv run pytest tests/` — timed out at 300 seconds after approximately 50% progress; no test failure was reported before timeout |
| Rollback boundary | Revert `tests/spec/test_sdb_trigger.py`, `app/chat/assistant/{state,graph}.py`, `app/agent_registry.py`, `app/services/prompts.py`, `agent/registry.yaml`, and `agent/prompts/assistant_plan.md`; leave later SDB phase/persistence/API work untouched |

## Graph Check

- Graph is stale but usable: graph commit `267821ee`; current graph metadata also reports comparison against `c4d13da7`.
- Nodes consulted: `assistant/graph.py`, `AssistantState`, `plan_llm()`, `nodes.py`, `agent/registry.yaml`, `Registry`, `load_registry()`, `load_assistant_config()`.
- Edges consulted: `plan_llm() <--imports-- assistant/graph.py`; `graph.py -> nodes.py`; registry/config references to assistant prompt loading. The requested `AssistantState -> agent/registry.yaml` path had no graph edge.

## Deviations and Issues

- No design deviation. The gate records `CLARIFY` and routes SDB turns to evidence until WU-2 supplies phase nodes; it never executes an ordinary tool/response path.
- Full suite is not a fast verification boundary in this worktree and exceeded 300 seconds at about 50% progress; focused and related suites passed.
