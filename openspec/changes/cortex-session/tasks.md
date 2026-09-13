# Tasks: Cortex-session Planning Surface

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 700–950 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 → PR 4 |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High
Test command: `DATABASE_URL='postgresql+psycopg://app:app@localhost:5437/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5437/lumat' uv run pytest tests/`

### Work-unit breakdown / PR slices

| Slice | Start → finish | Verification | Runtime harness | Rollback boundary |
|---|---|---|---|---|
| PR 1 | Existing assistant/config → validated gate, parser, declarations | Same env + `uv run pytest tests/` | N/A: deterministic seams | `app/chat/assistant/*`, registry/config tests |
| PR 2 | PR 1 → durable loop, merge, Tukulpan closure, truthful handoff | Same env + `uv run pytest tests/` | Active thread → close → approval | `app/services/{agent_chat,tukulpan}.py` and tests |
| PR 3 | PR 2 → authenticated API and serializers | Same env + `uv run pytest tests/` | TestClient lifecycle/auth matrix | `app/panel/api/routes/chat.py`, `app/panel/api/serializers.py` |
| PR 4 | PR 3 → SPA planning surface and chat controls | `cd web && npm run build`; pytest command | Navigate, reopen, open/close, literal command | `web/src/**` planning UI and tests |

## Phase 1: Foundation and RED tests

- [x] T1.1 RED: pytest `AssistantState` schema, recursive merge, invalid flag, and literal parser; GREEN: minimum helpers in `app/chat/assistant/state.py` and `nodes.py`.
- [x] T1.2 RED: registry tests for five classes, commands, and bad references; GREEN: update `agent/registry.yaml`, `app/agent_registry.py`, and `app/services/prompts.py`.

## Phase 2: Assistant loop and durable handoff

- [ ] T2.1 RED: test preflight ordering, question/research valve, five classes, and inactive routing; GREEN: wire `app/chat/assistant/{graph,nodes}.py`.
- [ ] T2.2 RED: test nested preservation, keyed decisions, `upsert` then `set_mark(..., MemoryStatus.ARCHIVED)`, reload; GREEN: update `app/services/{agent_chat,tukulpan}.py`.
- [ ] T2.3 RED: test digest rejection, checkpoint resume, and approved-plan-only stub; GREEN: reuse approval in `app/services/agent_chat.py`, adding no executor/table/migration.

## Phase 3: Authenticated API

- [ ] T3.1 RED: TestClient auth and 400/401/403/404/409 matrix; GREEN: open/close/list/detail/reopen in `app/panel/api/routes/chat.py` and `app/panel/api/serializers.py`.
- [ ] T3.2 RED: test approval with valid, expired, consumed, and changed tokens; GREEN: route report-derived SPEC through existing approval.

## Phase 4: SPA integration and verification

- [ ] T4.1 RED: frontend tests for API/types, navigation, list/detail/error/reopen; GREEN: update `web/src/api.ts`, `types.ts`, `web/src/components/domain/PanelShell.tsx`, and create `web/src/components/pages/PlanningSessions.tsx`.
- [ ] T4.2 RED: test indicator, controls, exact commands, inert free text, stream failure/recovery; GREEN: update `web/src/components/pages/AgentChat.tsx` and related `web/src/**`.
- [ ] T4.3 Run the provided database-backed command and `cd web && npm run build`; verify CS-1–CS-5, AC-9/12, PNL-APP-28/29, IAC-2/3/7, HL-2/3/5, and SDB-1/4. Threat matrix: all rows are explicitly N/A, so no threat RED tests are added.

Ponytail review: merged lifecycle/report/handoff checks; deleted new service, bus, planner, executor, route, migration, and threat-test tasks (YAGNI/N/A). Reuse existing seams. Graph consulted: `NAVIGATION`→`PanelShell`→`AgentChat`, `submit_message`→assistant graph, `record_decision`↔`list_for_entity`, `chat.py`→approval; graph stale/degraded at `c4d13da7`.
