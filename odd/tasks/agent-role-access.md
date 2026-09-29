# ODD Task: agent-role-access

Status: **in progress** — plan recorded, no slice implemented yet
Worktree: `../lumat-agent-odd-agent-role-access`
Branch: `odd/agent-role-access`
Base: `8f9d7a8e` (merge of PR #420, the `usuarios-aislamiento` closure record)
Depends on: `usuarios-aislamiento` — **delivered and closed** (`odd/tasks/usuarios-aislamiento.md` `## Closure`)
Source: `.rapsodia-code/handoffs/2026-09-29-agent-role-access.md`
Delivery strategy: `ask-on-risk`
Chain strategy: **stacked-to-main** (owner-confirmed 2026-09-29)

## Objective

Every authenticated role can reach the internal agent chat and has agent memory private to
that user. Tool authorization becomes explicit per role: `tecnico` gets no business-data
reads, `operador` keeps the business reads its panel already grants it, and `admin` keeps the
full catalog except other users' memory, which no role can read. Chat conversations stay
private to their owner.

## Why this unit exists

The previous unit made projects and agent memory private per user, and deliberately left the
chat admin-only (`usuarios-aislamiento` D8) because no role-to-tool authorization existed to
open it safely. That dependency is now delivered: the owner axis is in the schema, memory
recall is owner-scoped, and panel projects are owner-filtered.

What is missing is the authorization boundary itself. Today every chat route uses one guard
(`require_admin_json`) and the tool execution site receives no role at all, so opening the
chat without this unit would either keep the feature admin-only or hand every role the full
catalog — including `customers.search`, `conversations.list`, `kb.retrieve`, and
`dashboard.summary`. This unit defines and enforces the per-role map.

## Decisions

| ID | Decision | Rationale | Rejected alternative |
|---|---|---|---|
| D1 (owner, 2026-09-29) | Every role (`admin`, `operador`, `tecnico`) reaches the agent chat and holds private agent memory. | Lumat wants every person in the business to have private agent memory; this is the unit's purpose. | Keep chat admin-only, which leaves the isolation work unused. |
| D2 (owner, 2026-09-29) | `operador` keeps full business read in chat — `customers.*`, `conversations.*`, `cases.list`, `kb.retrieve`, `dashboard.summary` — and the only difference from `admin` is privileged writing. | The operator's panel surface already grants those reads; restricting them in chat would break the role's function. | Restrict `operador` reads the same as `tecnico`, which contradicts the operator's existing panel access. |
| D3 (owner, 2026-09-29) | `tecnico` gets **zero** business-data reads. `appointments.upcoming` is scoped to the requesting technician. | A technician must not reach sensitive business information, and a global appointments tool would leak the whole agenda. | Give `tecnico` the global `appointments.upcoming`; this exposes every customer's visit. |
| D4 (owner, 2026-09-29) | `admin` keeps the full catalog with one exception: no role, admin included, reads another user's agent memory. | Per-user privacy of the conversation with the agent is absolute. | Admin supervision access to another user's memory or threads. |
| D5 (owner, 2026-09-29) | A chat thread may not be bound to the business-shared `default` namespace by a role that must not read business memory. | `default` is business-shared memory (`usuarios-aislamiento` D4); binding to it would bypass D3. | Leave the API open and rely on the UI not offering `default`. |
| D6 (owner-confirmed, 2026-09-29) | `tecnico`'s private set is `memory.*`, `project.*`, `web.*`, and `assistant.capabilities`; that includes owner-scoped project reads and creation. `appointments.upcoming` is granted to `tecnico` only in WU3, together with its scoping. | Without project list/create, `tecnico` cannot select a project and the chat cannot open; project namespaces are private, not business data. Withholding the global appointments tool until WU3 scopes it means no slice ever exposes it unscoped. | Grant only chat routes, which leaves `tecnico` unable to create a thread; or grant the unscoped appointments tool in WU1, which leaks the whole agenda for the window between WU2 and WU3. |
| D7 | `automation.create_rule` stays `admin`-only. | Its panel surface is already admin-gated, it is unreachable by a non-admin through any current request path, and D2 excludes privileged writing from `operador`. | Grant it to `operador` as a non-privileged write. |
| D8 | The role-to-tool map is declared explicitly per tool, not inferred from name prefixes. | Replaces the advisory R2-002 name-prefix family inference as the authorization source, so a future tool rename cannot silently change coverage. | Extend the existing `project.`/`memory.` prefix inference with more prefixes. |

## Verified facts

All line numbers were re-verified on this worktree at `8f9d7a8e` before writing this document.

- Roles are `admin`, `operador`, `tecnico` (`app/models.py:71-75`). Panel role dependencies are `app/panel/api/deps.py:46-68`; the admin dependency is `deps.py:66` with the admin-only JSON contract documented at `deps.py:65`.
- **The chat API is uniformly admin-only.** Every route in `app/panel/api/routes/chat.py` uses `require_admin_json` (import `chat.py:16`; 15 route dependencies, e.g. `:73`, `:86`, `:130`, `:146`, `:159`, `:188`, `:194`, `:206`, `:225`, `:241`, `:254`, `:277`, `:310`, `:343`, `:359`).
- Thread creation requires an explicit project: `ChatThreadBody.proyecto` is required (`chat.py:55-56`) and is passed to `create_thread(session, current, proyecto=body.proyecto)` (`chat.py:70-76`). `create_thread` resolves non-`default` projects through `projects.agent_context(...).slug` and treats the literal `"default"` as the business-shared namespace without a role check (`app/services/agent_chat.py:507-518`).
- **`tecnico` cannot start a chat today.** `web/src/components/pages/AgentChat.tsx:489-490` errors with "Crea un proyecto primero para iniciar un chat." when the caller has no projects, and all three project routes use `require_operator_json` (`app/panel/api/routes/projects.py:30`, `:37`, `:56`), so `tecnico` receives 403 and the picker cannot load.
- `projects.list` filters `owner_id == owner_id` (`app/services/projects.py:55-57`), so the business-shared `default` row (owner `NULL`) never appears in the picker; the API body still accepts it.
- **Tool execution receives no role.** `execute_tool` signature at `app/chat/assistant/tools/registry.py:602-614` takes `trusted_thread_id`, `proyecto`, and `owner_id`. Its gate runs at `:617-676`: optional whitelist (`:617-618`), autonomous-write thread requirement (`:619-621`), the WU2 owner guard (`:622-630`), non-read-only allowlists (`:631-632`), cost gate (`:633-634`), project approval validation (`:645-672`), and consumed approval for non-autonomous writes (`:673-676`).
- The owner guard infers families by name prefix (`name.startswith("project.")`, and `memory.` with a positive thread id) at `registry.py:622-630`. This is the open advisory **R2-002**.
- **The role existed upstream but was absent from the `AssistantState` schema.** `app/services/agent_chat.py:679` passes `actor_role=user.role.value`, and `app/chat/assistant/graph.py:172-187` adds it to the initial state. The prior `app/chat/assistant/state.py:77` declaration was on `SDBTrigger`, not `AssistantState`; WU1 adds `actor_role` to the `AssistantState` `TypedDict` so LangGraph retains it. All three tool execution sites now pass it to `execute_tool`.
- Tool execution happens at three sites, all with a whitelist: `nodes.py:567` (delegation scope path), `nodes.py:958` (main path), and `app/services/agent_chat.py:193` (SDB task path, whitelist from `load_assistant_config().tools_whitelist`).
- A per-assistant `tools_whitelist` already flows from the agent registry (`app/agent_registry.py:52`, `:63`, `:73`) into `AssistantRuntimeConfig.tools_whitelist` (`app/services/prompts.py:105`, `:155`). The role map must intersect with it, not replace it.
- **The catalog is 24 tools: 16 read-only, 8 writes** (`registry.py:563-588`). Write allowlists at `registry.py:26-33`.
- Role map denominators for WU1: `admin` 24 allowed / 0 denied; `operador` 23 allowed / 1 denied (`automation.create_rule`); `tecnico` 14 allowed / 10 denied. The WU1 `tecnico` denials are `customers.search`, `customers.list`, `customers.operational_history`, `conversations.search`, `conversations.list`, `cases.list`, `kb.retrieve`, `dashboard.summary`, `automation.create_rule`, and `appointments.upcoming`. `appointments.upcoming` is withheld from `tecnico` in WU1 and granted only in WU3 together with its technician scoping, so no slice ever exposes the unscoped global tool; after WU3 the `tecnico` map is 15 allowed / 9 denied.
- `kb.retrieve` reads the whole corpus including internal documents by deliberate choice (`registry.py:313-315`).
- `appointments.upcoming` is global: `_upcoming_appointments` calls `scheduling.list_for_range(session, date, date+30d, "UTC")` with no owner or technician filter (`registry.py:279-282`).
- **Memory privacy is already enforced.** `_owned_agent_memory_or_raise` (`registry.py:442-458`) requires matching `proyecto`, `owner_id`, `producer`, `agent:` topic prefix, and an owned axis, so D4's exception already holds in code.
- `app/chat/nodes/` and `app/chat/subgraphs/` are the **WhatsApp bot** pipeline (`ConversationState`, intents, handoff, emergency), not the internal agent chat. `is_tool_whitelisted` (`app/chat/nodes/orchestrate.py:99`) belongs to that pipeline and is out of scope.
- The frontend hardcodes the admin identity as the message author: `web/src/components/pages/AgentChat.tsx:95`, `:578`, `:614`, `:913`; and so does the backend opening-message lookup, `where(InternalChatMessage.author == "admin")` (`app/services/agent_chat.py:529`).
- Navigation is admin-gated for chat: `NAVIGATION` chat entry `adminOnly: true` and the sidebar filter at `web/src/components/domain/PanelShell.tsx:38-40`, `:129`; footer entry `user.role === "admin" ? ["chat"] : []` at `:440`. Dashboard cards gate on `role === "admin"` at `web/src/components/pages/Dashboard.tsx:193` and `:206`.
- Strict TDD is on (`openspec/config.yaml:38`). Backend runner `uv run pytest tests/` (`openspec/config.yaml:29`, `:31`); web runner `cd web && npm test`. There is no linter, formatter, or standalone type checker: `tsc -b` exists only inside `cd web && npm run build`.
- The per-worktree test database convention is `infra/test-db.sh up` / `eval "$(infra/test-db.sh env)"` / `infra/test-db.sh down`, with `infra/.env` copied from the primary worktree and never sourced before `test-db.sh env` (`odd/tasks/test-db-isolation.md`).

### Graph check

Graph refreshed in this worktree to `8f9d7a8e` (8498 nodes, 18413 edges, 718 communities); it was stale at `16ba9cbf` with a previously documented PARTIAL extraction, now resolved.

Nodes consulted: `execute_tool()` and `get_tool()` (`registry.py:602`, `:591`), `ToolValidationError` (`registry.py:42`), `_read_memory` (`registry.py:326`), `_owned_agent_memory_or_raise` (`registry.py:442`), `issue_approval()` (`approval.py:93`), `is_tool_whitelisted()` (`orchestrate.py:99`, WhatsApp bot — out of scope), `NAVIGATION` / `PanelShell()` (`PanelShell.tsx:38`, `:158`), `Role` (`web/src/types.ts:8`), `_ProjectAuthorization` (`services/projects.py:18`), `Admin-only JSON routes (PDW-API-4)` (`deps.py:65`), `InternalChatThread` (`models.py:855`), `assistant/graph.py`, `assistant/nodes.py`, `services/agent_chat.py`.

Edges consulted: `chat.py` -> `deps.py` -> `User`; `assistant/nodes.py` -> `registry.execute_tool()` -> `services/projects.py` and `services/tukulpan.py`; `services/agent_chat.py` -> `registry.execute_tool()` and `models.InternalChatThread`; `PanelShell.tsx` -> `Dashboard.tsx` -> `Role`.

## Scope

**In scope**

- An explicit role-to-tool authorization map covering all 24 catalog tools.
- Enforcement of that map at the tool execution site and at all three execution call sites.
- Role-aware panel chat route authorization for the 15 chat routes.
- All five planning-session routes are open to every panel role; `open_planning_session`'s implicit `default` binding is changed in WU2 to caller-selected project binding (or a role-denied 400).
- Panel project read and creation access for `tecnico`, so the chat project selection is reachable.
- Role-aware rejection of binding a chat thread to the business-shared `default` namespace.
- Technician-scoped `appointments.upcoming`.
- Frontend and backend author identity driven by the authenticated role, not a hardcoded `admin`.
- Navigation and dashboard gating per role.
- Route-level, tool-level, and frontend tests proving both the allowed behavior and the denial of privileged tools.
- Delta amendments to `internal-agent-chat` and `assistant-operations` specs are included in WU2 because their live contracts contradict the approved role boundary.

**Out of scope**

- Project or memory isolation, which is delivered and closed; do not reopen `usuarios-aislamiento`.
- The WhatsApp bot pipeline (`app/chat/nodes/`, `app/chat/subgraphs/`), customer-facing WhatsApp behavior, and the knowledge base contents.
- Any change to the shared `default` project's existence or to business-shared memory semantics.
- A new role, a permission-editing UI, or per-user permission overrides.
- Real multi-tenancy, per-tenant credentials, or webhook routing by tenant.
- Production migration work. Migrations 034 and 037 remain under their own production gate from the previous unit.

## Work units

Delivery is a chained PR sequence; each slice is one cohesive PR candidate with its tests in
the same slice. Estimates are authored additions plus deletions, not code-golf targets. The
total forecast is approximately 610–950 changed lines, well above the ~400 review budget, so
the chain split is forced by size rather than optional.

### WU1 — role-to-tool authorization map and enforcement

- **U1.1** Declare the explicit role-to-tool authorization map for all 24 catalog tools, colocated with `TOOL_REGISTRY`, so tool family membership stops being inferred from name prefixes (closes the R2-002 advisory).
- **U1.2** Thread the authenticated role into `execute_tool` and deny any tool outside that role's map. An unknown, missing, or non-string role fails closed.
- **U1.3** Apply the role at all three execution call sites: `nodes.py:567`, `nodes.py:958`, and `agent_chat.py:193`, preserving the existing `tools_whitelist` intersection and the delegation read-only constraint.
- **U1.4** Tests: for every tool category, assert each role is allowed or denied as the map declares, including an unknown-role fail-closed case and a delegated-scope case.

Estimated authored size: 180–260 changed lines.

### WU2 — chat routes, project access for tecnico, and the default-namespace guard

- **U2.1** Replace `require_admin_json` with a role-aware chat guard on all 15 routes, including all five planning-session routes; every panel role is allowed.
- **U2.2** Grant `tecnico` read and create access to its own projects so the chat project picker is reachable, without weakening owner scoping for any role.
- **U2.3** Reject binding a chat thread to the business-shared `default` namespace for roles the map excludes, and validate that the requested project belongs to the caller.
- **U2.4** Tests: a route allow/deny matrix per role, the `default`-binding rejection, and cross-user project rejection.

Estimated authored size: 200–300 changed lines.

### WU3 — technician-scoped upcoming appointments

- **U3.1** Grant `appointments.upcoming` to `tecnico` in the role map and scope it to the requesting technician in the same slice, replacing the unfiltered global range query. `admin` and `operador` keep their mapped view.
- **U3.2** Tests: a technician sees only their own appointments; a technician cannot observe another technician's or an unassigned appointment; `admin` and `operador` keep their mapped view; the map now allows the tool for `tecnico`.

Estimated authored size: 80–140 changed lines.

### WU4 — real identity in the navigation, the dashboard, and the message author

- **U4.1** `PanelShell.tsx` navigation gating per role: chat reachable by every role, automation still `admin`-only.
- **U4.2** `Dashboard.tsx` chat and automation cards per role.
- **U4.3** `AgentChat.tsx` author driven by the authenticated role instead of the hardcoded `"admin"`, and the project picker working for `tecnico`.
- **U4.4** Backend opening-message author no longer assumes `admin` (`agent_chat.py:529`).
- **U4.5** Tests: frontend role gating and author rendering, and the backend opening-message author.

Estimated authored size: 150–250 changed lines.

## Acceptance criteria

| Criterion | Evidence required |
|---|---|
| Every role can open the agent chat | Route tests per role plus a `tecnico` thread-creation test that includes project selection |
| `tecnico` reaches no business-data read (`customers.*`, `conversations.*`, `cases.list`, `kb.retrieve`, `dashboard.summary`) | Tool-level denial tests per role |
| `tecnico` sees only its own appointments | Scoped-appointment tests |
| `operador` has the full business read and no privileged write | Allow tests for the reads and a denial test for `automation.create_rule` |
| `admin` keeps the full catalog | Map-coverage test asserting every tool is allowed for `admin` except as D4 states |
| No role reads another user's agent memory or thread | Existing isolation tests still pass plus the role-map tests |
| No role can bind a thread to the business-shared `default` namespace contrary to D5 | Rejection test |
| The message author reflects the authenticated role in frontend and backend | Frontend render test and backend opening-message test |
| Chat navigation is reachable per role and automation stays admin-only | Frontend gating tests |
| The backend suite, the web suite, and the web build pass | `uv run pytest tests/`, `cd web && npm test`, `cd web && npm run build` |

## Checks

- `uv run pytest tests/` — full backend suite.
- `cd web && npm test` — full frontend suite.
- `cd web && npm run build` — the repository's only frontend type check (`tsc -b` plus vite).
- `git diff --check` — whitespace and conflict-marker hygiene.
- Per-worktree test database through `infra/test-db.sh`; never a shared test database.

## TDD

Strict TDD is active (`openspec/config.yaml:38`). Every unit of behavior starts with a failing
test (RED), then the minimal implementation (GREEN), then refactor with the suite green.
Backend runner `uv run pytest tests/`; web runner `cd web && npm test`.

## Risks and carried-forward context

- **R2-002** (advisory, from WU2 of the previous unit): tool families were inferred from name prefixes. D8 closes the authorization concern; the separate concern of renaming a tool that a *delegation scope* declares remains a registry-validation matter.
- **Semantic-merge risk** across a four-slice chain: `registry.py`, `nodes.py`, `chat.py`, `projects.py`, `PanelShell.tsx`, and `AgentChat.tsx` are touched by more than one slice type and by other in-flight work. Merge the current base into a branch before pushing, and run the frontend suite plus `npm run build` plus the backend suite on the merged tree.
- **Review budget:** the forecast exceeds the ~400-line budget; the chain split is required, not optional.
- **D6 was owner-confirmed 2026-09-29.** WU2 grants `tecnico` owner-scoped project access.
- **Planner/catalog role-coherence follow-up:** `assistant.capabilities` (`registry.py:532-544`) and the planner catalog (`nodes.py:518`, `:620`) are built from `tools_whitelist` only, not filtered by role. A non-admin planner may therefore be offered a tool its role cannot execute; execution rejects it at the authorization gate. This is a coherence/UX follow-up, not a security defect, because execution remains the boundary. Fold it into whichever later slice first makes the gap visible; do not implement it in WU1.
- No push, PR, merge, or deploy happens without separate explicit owner authorization.

## Progress

- [x] Unit opened: worktree `../lumat-agent-odd-agent-role-access` on `odd/agent-role-access` from `8f9d7a8e` (owner authorized 2026-09-29).
- [x] Graph refreshed in this worktree to `8f9d7a8e`; scope clarified so the WhatsApp bot pipeline is excluded.
- [x] Role-to-tool map decided with the owner (D1–D5, D7).
- [x] WU1.1 — declared an explicit per-tool `UserRole` authorization map for all 24 tools.
- [x] WU1.2 — enforced role authorization fail-closed in `execute_tool` without replacing existing gates.
- [x] WU1.3 — passed `actor_role` from delegation, main graph execution, and SDB execution into the gate; declared `actor_role` in `AssistantState` so LangGraph retains it.
- [x] WU1.4 — added role/tool matrix, completeness, fail-closed, execution-site, and delegated-scope tests; updated existing execution tests to declare their role.
- WU1 authored size: 343 changed lines (additions plus deletions; estimate: 180–260).
- [x] U2.1 — role-aware guard applied to all 15 chat routes. Evidence: `test_chat_and_project_route_authorization_matrix` checks route access for every role and unauthenticated JSON 401 responses.
- [x] U2.2 — project list/detail/create now admit `tecnico` without altering owner filters. Evidence: technician-owned create/list coverage and existing owner-isolation tests.
- [x] U2.3 — reject technician binding to `default`, pass optional project through planning creation, preserve owner validation. Evidence: default rejection/no persistence, planning own-project and cross-owner rejection tests.
- [x] U2.4 — route/tool/declaration matrix coverage. Evidence: route authorization test, guard role completeness test, and business-memory/tool declaration coherence test.
- [x] WU2 — chat routes, `tecnico` project access, and the `default`-namespace guard. Evidence: role-aware guard + 15 route dependencies; three project dependencies; route and namespace tests; updated live specs.
- WU2 authored size: 316 changed lines (additions plus deletions).
- [ ] WU3 — technician-scoped upcoming appointments.
- [ ] WU4 — real identity in navigation, dashboard, and message author.

## Next step

WU2 is implemented and verified in its feature worktree; proceed to WU3 after review.
