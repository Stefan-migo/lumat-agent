# Tasks: Agent-Owned Projects Namespace

## Phase 1: Registry Foundation (WU-1)

- [x] 1.1 RED: Add migration/model tests for `projects`, `project_aliases`, `project_audit`, default seed, unique normalized slugs, and `vector(384)`.
- [x] 1.2 GREEN: Create `db/migrations/024_projects.sql` and `Project`, alias, and audit mappings in `app/models.py`; preserve `Memory.proyecto` constraints.
- [x] 1.3 RED: Add service contract tests for exact lookup, bounded candidates, and normalized purpose deduplication.
- [x] 1.4 GREEN: Create `app/services/projects.py` typed `list/find/create` skeleton using `kb.embed_texts()`; use cosine threshold `>=0.85`, top three candidates, and approval for ambiguity.
- [x] 1.5 REFACTOR: Keep registry persistence and embedding policy minimal; run `uv run pytest tests/integration/test_db.py tests/spec/test_projects_spec.py`.

## Phase 2: Lifecycle and Memory Valves (WU-2)

- [x] 2.1 RED: Test rename migration failure, active-run rejection, alias/audit creation, merge conflict atomicity, active-run rejection, and default merge protection.
- [x] 2.2 GREEN: Implement `rename/archive/merge` in `app/services/projects.py` with deterministic locks, byte-equivalent conflict validation, aliases, audits, and one transaction.
- [x] 2.3 RED: Test authorized non-default Tukulpan writes and unauthorized writes rejected before persistence.
- [x] 2.4 GREEN: Extend `app/services/tukulpan.py` authorization to the project capability while keeping `app/services/memory.py` forwarding-only and default-compatible.
- [x] 2.5 REFACTOR: Run `uv run pytest tests/spec/test_projects_spec.py tests/spec/test_memory_spec.py tests/integration/test_db.py` (no Tukulpan-specific test file exists).

## Phase 3: SDB Authorization and Propagation (WU-3)

- [x] 3.1 RED: Test user/arbitrary project injection rejection and project-aware SPEC/STATE/RESULT persistence, recovery, entity identity, and unchanged seven phases.
- [x] 3.2 GREEN: Propagate validated project state through `app/chat/assistant/state.py`, `app/services/agent_chat.py`, `app/chat/graph.py`, and `app/chat/assistant/nodes.py`; preserve run keys and panel scope.
- [x] 3.3 REFACTOR: Run `uv run pytest tests/integration/test_chat_state.py tests/integration/test_agent_chat.py tests/spec/test_sdb_native_spec.py`.

## Phase 4: Typed Tools and Approval (WU-4)

- [x] 4.1 RED: Test typed schemas/classification, whitelist enforcement, ambiguity no-selection, SHA-256/15-minute expiry, SDB `APPROVE`, replay, and changed-payload rejection.
- [x] 4.2 GREEN: Add project tools to `app/chat/assistant/tools/registry.py`, allow-list them in `agent/registry.yaml`, and include canonical project payloads in `app/chat/assistant/approval.py`.
- [x] 4.3 REFACTOR: Run `uv run pytest tests/integration/test_assistant_tools.py tests/integration/test_assistant_chat.py`.

## Phase 5: Read-Only Panel Browse (WU-5)

- [x] 5.1 RED: Test operator-only list/detail, SDB-only filtering/grouping, WhatsApp exclusion, missing project, and absent CRUD routes.
- [x] 5.2 GREEN: Add serializers and `app/panel/api/routes/projects.py`, register routes in `app/panel/api/__init__.py`, and guard with `require_operator_json` (read-only browse is an operator capability, not admin-only).
- [x] 5.3 RED: Add route/navigation/list-detail/read-only control tests for `/panel/app/projects`.
- [x] 5.4 GREEN: Update `web/src/api.ts`, `web/src/types.ts`, `web/src/components/domain/{panelRoutes,PanelShell,AppShell}.tsx`, and create `ProjectsPage.tsx` using existing grammar.
- [x] 5.5 REFACTOR: Run focused backend tests, web tests, and `cd web && npm run build`; the full suite is intentionally not run because it is known to exceed 300s.

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 900 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested work-unit / PR boundaries | PR1 WU-1 → PR2 WU-2 → PR3 WU-3 → PR4 WU-4 → PR5 WU-5; stacked to main |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High
