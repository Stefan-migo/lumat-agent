# ODD Task: agent-role-access

Status: **in progress** — WU1–WU4a delivered; WU4b is the last open slice
Unit worktree: `../lumat-agent-odd-agent-role-access` (`odd/agent-role-access`, base `8f9d7a8e`)
Current slice: WU4b — worktree `../lumat-agent-odd-agent-role-access-wu4b`, branch `odd/agent-role-access-wu4b`, base `c0c78ebe` (merge of PR #431, WU4a)
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
| D9 (owner, 2026-09-29) | The R3-001 follow-up is resolved by filtering the `GET /assistant/capabilities` catalog by role, not by relaxing IAC-1. | IAC-1 (`openspec/specs/internal-agent-chat/spec.md:24`) already requires the surface not to expose privileged tools; the code was the wrong side. Filtering also fixes the user-visible count a `tecnico` read ("24 herramientas disponibles" while 10 were denied). | Change IAC-1 from "expose" to "execute", which would have left the panel count incoherent. |
| D10 (owner, 2026-09-29) | `TechnicianShell` navigates with URL-backed routing over a restricted view set (`agenda`, `chat`, `projects`, `planning-sessions`), reusing `panelRoutes`. | `AgentChat` receives its project only from the URL (`AgentChat.tsx:274`, `?proyecto=`) and `ProjectsPage`'s open-chat action must work for `tecnico`; the rest of the panel already navigates with the History API. | Local view state, which would need a new `projectSlug` prop on `AgentChat` — a second source of truth for the same state — and would leave the technician without deep links or browser history. |

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

### WU4a — real identity in the message author (DELIVERED)

- **U4.3** `AgentChat.tsx` author driven by the authenticated role instead of the hardcoded `"admin"`; `AgentChatProps.role` is now **required**, so every render site must pass it.
- **U4.4** Backend opening-message author no longer assumes `admin` (`agent_chat.py:529`).
- **U4.5** Tests: frontend role gating and author rendering, and the backend opening-message author.
- **Delivered:** PR #431, merge `c0c78ebe`. Authored size 80 lines after the WU4 split (estimate was 150–250).

### WU4b — technician chat reachability and role-gated dashboard (last slice)

Owner decisions: keep `TechnicianShell` and put the chat inside it — do NOT route `tecnico` through `AppShell`, which would expose the business navigation the unit deliberately keeps out of reach (D3); the technician chat includes the Proyectos and Sesiones de planificación tabs (D6); the shell navigates with URL-backed routing (D10).

- **U4b.1** `PanelShell.tsx`: the chat is reachable by `operador` in the sidebar **and** in the footer. `kb`, `automation-rules`, `settings` and `users` stay `admin`-only. The footer is a separate hardcoded list (`:439-444`), not derived from `NAVIGATION`, so it must be changed independently.
- **U4b.2** `TechnicianShell.tsx`: URL-backed routing (D10) over a restricted view set — `agenda` → `TechnicianAgenda`; `chat` / `projects` / `planning-sessions` → `AgentChat` (with `role` and `sectionTabs`), `ProjectsPage`, `PlanningSessions`, reusing `AssistantTabs` and the `AssistantView` derivation at `AppShell.tsx:108-110`. No business navigation is exposed. Any other view falls back to `agenda`.
- **U4b.3** `Dashboard.tsx`: the "Agente Lumat" card follows the role; "Automatizaciones" stays `admin`-only (D7).
- **U4b.4** One source of truth for the role→label map: `PanelShell.tsx:90`, `AgentChat.tsx:278` and `UserManagement.tsx:12` carry three copies. Promote the typed `Record<Role, string>` to a shared module and consume it in all three. Separate commit, droppable.
- **U4b.5** Tests: a technician reaches the chat with its three tabs; `operador` sees the chat in the sidebar and the footer; the dashboard chat card follows the role while automation stays admin-only; new `TechnicianShell.test.tsx` (there is none today).

Estimated authored size: 250–400 changed lines. The backend is **not** expected to change; if the technician routing turns out to need an API change, stop and re-scope.

**`AgentChat` contract WU4b must satisfy:** `role` is required; the project arrives only through the URL (`AgentChat.tsx:274`); `threadId` has both a prop and a `?thread_id=` URL fallback (`:276-277`). `create_run_message` reads the role with `getattr(user.role, "value", user.role)` on purpose — do not "simplify" it.

### WU4 — superseded

WU4 was split after WU4a. Its remaining navigation, dashboard and technician-shell work is WU4b above; the original U4.3/U4.4 author work is WU4a. The original estimate (150–250) was too small for a single slice.

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
- **WU4b touches `web/`.** Before opening its PR, diff its paths against every in-flight frontend branch and run the local integration over the merged tree: the frontend suite, `cd web && npm run build`, and the backend suite. `tsc -b` lives only inside `npm run build`, so a green Vitest run does not prove the tree type-checks.
- **Confirm `origin/main` has not moved before merging.** In WU4a `main` moved between the pre-merge check and the merge itself, so the landed tree had to be re-verified afterwards.
- **WU4b risks the ~400-line budget** (estimated 250–400). Under `ask-on-risk`, if the diff exceeds it, stop and ask whether to split before opening the PR.
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
- [x] U3.1 — `appointments.upcoming` granted to `tecnico` in the map and scoped to the requesting technician in the same slice. Evidence: `_upcoming_appointments` dispatches on role; `tecnico` reads `scheduling.list_for_technician(session, owner_id)` and fails closed without an authenticated owner; `admin`/`operador` keep `list_for_range`. The owner chain was verified end to end (`chat.py:305-311` `user_id=current.id` -> `run_assistant` -> `state["user_id"]` -> `execute_tool(owner_id=...)`).
- [x] U3.2 — Tests: a technician sees only their own appointments and never another technician's; the other technician sees theirs; `admin`/`operador` keep the mapped view; the role matrix allows the tool for `tecnico`; the scoped technician catalog advertises it.
- [x] WU3 — technician-scoped upcoming appointments. Evidence: role-dispatched handler + owner-scoped seam, unit seam and fail-closed tests, DB-backed scoping test, role matrix and capabilities catalog updated.
- WU3 authored size: 153 changed lines (additions plus deletions; estimate: 80–140).
- [x] Follow-up `uv.lock` — synced to `pyproject` `2026.09.7`. Evidence: PR #425, merge `ecc67e48`.
- [x] Follow-up R3-001 — the capabilities catalog is filtered by role (D9). Evidence: PR #426, merge `e77da7d7`; catalog-vs-executable invariant test per role.
- [x] WU4a — real identity in the message author, front and back: `AgentChatProps.role` is required and the author is derived from the authenticated role. Evidence: PR #431, merge `c0c78ebe`. Authored size 80 lines.
- WU4 was split after WU4a; the remaining navigation, dashboard and technician-shell work is WU4b, the last slice.
- [x] WU4b.1 — `operador` reaches the chat in the sidebar and the footer; automation/kb/settings/users stay `admin`-only. Evidence: `e566b48e`.
- [x] WU4b.2 — technician chat reachable inside `TechnicianShell` with URL-backed routing (D10) and its three tabs. Evidence: `713dfbd9`; `ff66f5fe` preserves legacy agenda story callers and desktop mobile-nav visibility.
- [x] WU4b.3 — the dashboard agent card follows the role; automation stays `admin`-only. Evidence: `36e57dc2`.
- [x] WU4b.4 — one shared role→label map, three copies removed. Evidence: `188fdbd1`.
- [x] WU4b.5 — tests: technician chat reachability, `operador` sidebar and footer, dashboard card per role. Evidence: `e566b48e`, `713dfbd9`, `36e57dc2`.
- WU4b authored size: 238 changed lines (additions plus deletions; estimate 250–400) at `7e73288e`. Under the ~400 budget, so `ask-on-risk` did not trigger a split.
- [x] Orchestrator verification — `cd web && npm run build` passed (`tsc -b` + vite); `cd web && npm test` 868/868 passed, both re-run by the orchestrator on `7e73288e`. Slice baseline was 858 passed / 1 failed, the failure being the known load-flaky `AgendaPage.test.tsx > creates and selects a manual case inline, then uses it to create the visit`, which passes in isolation.
- Scope correction — the slice had also changed the shared `AssistantTabs.tsx` first-tab label from `"Chat"` to `"Asistente"`, which is outside WU4b's scope and alters the admin and operador UI. Reverted in `7e73288e`; the technician bottom-nav chat item keeps `"Asistente"`. Recorded because it was not in the slice's declared plan.
- Native RDD assessment over `c0c78ebe..7e73288e`: risk `medium`, 238 changed lines, `review_due: false`, `review_due_reason: "under_budget"`.
- [x] WU4b delivered as **PR #436** (`odd/agent-role-access-wu4b` -> `main`, label `type:feature`). `origin/main` moved twice while the slice was in flight (PR #433 -> `4644ba99`, PR #434 -> `8c42702d`); both were merged into the branch, and the full local integration ran green over the merged tree. The #434 merge is docs-only, so the tested code tree is byte-identical to the pushed one.

## Next step

WU1–WU3 and WU4a are delivered; the two carried follow-ups (`uv.lock`, R3-001) are closed. **WU4b is implemented, verified and delivered as PR #436** from `odd/agent-role-access-wu4b`, with `origin/main` `8c42702d` merged into the branch. The full local integration ran green over the merged tree: backend 1727 passed / 2 deselected, frontend 871 passed, `npm run build` passed. Remaining: owner review and merge; that closes the `agent-role-access` unit.
