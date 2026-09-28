# ODD Task: usuarios-aislamiento

Status: open — WU1 implementation and remediation complete; stacked chain continues
Worktree: `../lumat-agent-odd-usuarios-aislamiento`
Branch: `odd/usuarios-aislamiento`
Base: `16ba9cbf` (main)
Depends on: nothing
Source: `.rapsodia-code/sessions/archived/2026-09-25-usuarios-aislamiento/report.md` (archived when this unit was opened)
Delivery strategy: `ask-on-risk`
Chain strategy: `stacked-to-main` (owner decision 2026-09-28)

## Objective

Each user's projects and agent memory are private to that user. WhatsApp, customers,
the business bot, and the knowledge base remain shared across the business. This is
per-user isolation inside one business, not real multi-tenancy.

## Why this unit exists

The application already has users, roles, authenticated panel routes, per-user agent
chat threads, and project-aware memory. The missing boundary is project ownership:
the project registry and memory key are global, so users can collide or see each
other's agent context. This unit adds the owner axis while preserving business-wide
WhatsApp and knowledge-base behavior.

The readiness `session.md` says there is no user-administration UI and that the seed
expects exactly one user. That claim is superseded by the code and by the correction
already recorded in the readiness `report.md`: user administration exists in
`app/panel/api/routes/users.py`, `app/services/users.py`, and
`web/src/components/pages/UserManagement.tsx`. User administration is out of scope.

## Decisions

| ID | Decision | Rationale | Rejected alternative |
|---|---|---|---|
| D1 | Isolation is per individual user inside the same business. | Matches the product request and the single-business WhatsApp configuration. | Real multi-tenancy would require tenant-specific WhatsApp credentials and webhook routing; that is a separate re-architecture. |
| D2 | Owner is part of the memory key `(proyecto, scope, entity_id, topic_key)`, not only `projects.owner_id`. | Users may use the same project slug; project ownership alone would not prevent memory collisions or cross-user recall. | Add only `projects.owner_id`; this gives cosmetic rather than actual memory isolation. |
| D3 | `memories.owner_id` is nullable; `NULL` means business memory. | Customer-scope memory, the knowledge base, and bot memory remain business-shared. | Make owner non-null for every row; this would break shared business memory. |
| D4 (owner, 2026-09-28) | The `default` project stays business-shared. Chat MUST force explicit project selection and MUST NOT silently fall back to `default`. | Preserves the shared seed row without letting project-specific agent work leak into it. | Per-user `default` projects; or silently using the business default when no project was selected. |
| D5 (owner, 2026-09-28) | Isolation is absolute: neither an admin nor anyone else can see another user's projects or agent memory. There is no admin override. | Project and agent memory privacy applies equally to all roles. | Admin supervision access. An orphaned project therefore requires database access to recover; this unit adds no in-app recovery. |
| D6 (owner, 2026-09-28) | `project_aliases` become per-user: migrate global `UNIQUE(alias)` to `UNIQUE(owner_id, alias)` and backfill the owner. | Aliases must allow the same name for different owners without global lookup leakage. | Keep aliases global, which prevents same-alias projects and preserves cross-user namespace behavior. |
| D7 (owner, 2026-09-28) | The panel gains project creation, and the agent tool `projects.create` remains. | Users need a direct panel path while existing agent workflows remain available. | Tool-only creation; or replacing the agent tool with panel-only creation. |
| D8 (owner, 2026-09-28) | Opening internal agent chat to `operador` and `tecnico`, with per-role tool authorization, is a separate dependent unit, `agent-role-access`; it starts only after this unit lands. Chat remains admin-only here. | Isolation work must not broaden chat access before tool permissions are defined per role. | Include role access in this unit without role-specific tool authorization. |
| D9 (owner, 2026-09-28) | Backfill legacy non-`default` projects and their agent memory to the admin; keep `default` business-shared and business-scope memory at `owner_id=NULL`. Migration 034 must enumerate legacy rows, and the owner must confirm the list before applying; stop for reassignment if multiple admins make a project's owner ambiguous. | Only admins can chat in the legacy system and therefore only admins could have created projects; ambiguity must not be silently resolved. | Assign legacy rows automatically or assign business memory to an individual owner. |

## Verified facts

- Roles are `admin`, `operador`, and `tecnico` (`app/models.py:71-75`).
- `User` is defined at `app/models.py:238`; signed-session authentication reloads the user per request (`app/main.py:95-106`, `app/panel/api/deps.py:28-38`).
- Role dependencies are in `app/panel/api/deps.py:46-68`.
- `Memory` is defined at `app/models.py:458`; its current unique key is `(proyecto, scope, entity_id, topic_key)` (`app/models.py:466-469`). The implementation is `app/services/tukulpan.py`; `app/services/memory.py` re-exports it.
- `InternalChatThread` is defined at `app/models.py:798` and has `user_id` and `proyecto` fields (`app/models.py:803-805`). Chat thread creation and ownership-filtered routes live in `app/services/agent_chat.py` and `app/panel/api/routes/chat.py`.
- Project registry and alias behavior are in `app/services/projects.py`. Existing global slug and alias uniqueness originate in `db/migrations/024_projects.sql`; the seeded `default` project is global (`024_projects.sql:36-38`).
- The panel projects API is currently read-only; project creation exists as the `projects.create` agent tool. This unit adds panel creation without removing the tool.
- User administration already exists in the API, service, and frontend. The contrary statement in readiness `session.md` is stale and superseded, not an unresolved gap.
- The latest migration on main is `033_customer_archived_at.sql`; this unit opens with migration **034**. Readiness `report.md`'s former 031 → 032 note is stale.
- Every route in `app/panel/api/routes/chat.py`—thread create/list/read/update/delete, messages, stream, approval, attachments, `/assistant/capabilities`, and planning sessions—uses `require_admin_json` (for example, lines 69-89, 127-162, 189-208, 226-256, 278-361).
- `app/chat/assistant/tools/registry.py:26-33` defines `SDB_WRITE_ALLOWLIST` as `automation.create_rule`, `project.create`, `project.rename`, `project.archive`, and `project.merge`, and `AUTONOMOUS_WRITE_ALLOWLIST` as `memory.write`, `memory.update`, and `memory.delete`. Tool execution gates writes by these allowlists and approval/read-only mechanics (lines 588-608); it has no role filter.
- The only role-aware assistant behavior found is the manual SDB trigger downgrade in `app/chat/assistant/state.py:219-220` (`requested is True` with a non-admin role routes to normal).
- Concrete overreach if chat opens without per-role tool authorization: `automation.create_rule` is in the admin-only `automation-rules` navigation (`web/src/components/domain/PanelShell.tsx:45`); `project.rename`, `project.archive`, and `project.merge` are agent tools while `app/panel/api/routes/projects.py:1,17-39` exposes read-only project endpoints guarded by `require_operator_json`.
- The chat navigation item is `adminOnly: true` at `web/src/components/domain/PanelShell.tsx:40`; footer navigation adds chat only when `user.role === "admin"` at line 440.
- The projects panel routes use `require_operator_json` (`app/panel/api/routes/projects.py:17-27`), so operators can list and inspect projects but have no chat route access in this unit.
- One `meta_phone_number_id` is configured (`app/config.py:74`); WhatsApp remains business-shared.
- Strict TDD is on (`openspec/config.yaml:38`). Backend runner is `uv run pytest tests/` (`openspec/config.yaml:29,31`); web runner is `cd web && npm test`.
- The per-worktree test database convention is documented in `odd/tasks/test-db-isolation.md`; use `infra/test-db.sh` rather than a shared test database.

## Scope

**In scope**

- Migration 034: add project ownership, owner-scoped slug uniqueness, memory ownership and owner-aware memory uniqueness, and per-user aliases with owner backfill.
- Owner-aware project registry operations and agent context; preserve the business-shared `default` row without silently selecting it for a chat thread.
- Owner-aware memory write authorization, upsert, and recall, with `NULL` retained for shared business memory.
- Bind internal chat threads to their user and require explicit project selection.
- Owner-filter all project and memory panel/tool access, including admin requests; add panel project selection and creation while retaining `projects.create`.
- Explicit cross-user isolation, business-memory preservation, and migration/backfill tests.
- Legacy non-`default` project and associated agent-memory backfill follows D9, with the enumerated legacy list confirmed before applying migration 034.

**Out of scope**

- Real multi-tenant businesses, per-user WhatsApp credentials, or webhook routing by tenant.
- Changes to shared WhatsApp, customers, conversations, cases, scheduling, bot, or knowledge-base behavior.
- User administration, which already exists and is not part of this unit.
- Admin supervision or override access to another user's projects or agent memory.
- In-app recovery for orphaned projects; database access is required.
- Retroactive privatization of existing `default` threads or memory.
- Redesign of unrelated panel surfaces.
- Opening the agent chat to operador or tecnico, and per-role tool authorization — deferred to the dependent unit `agent-role-access`.

## Work units

Delivery uses a stacked-to-main chain. Each slice is one cohesive PR candidate, with
tests for its behavior in the same slice. Estimates are authored additions plus
deletions, not targets to code-golf; the total forecast remains approximately
500–800 changed lines. Reassess honestly during implementation and ask on risk.

### WU1 — ownership schema and project registry

The chat role opening and its per-role tool authorization are deliberately not part
of WU1–WU4; track them in the dependent `agent-role-access` unit after this unit lands.

**Start:** base `16ba9cbf`, current global project registry and memory schema.
**End:** migration 034 supplies owner-aware project/alias schema and backfill;
project registry methods enforce owner scope; `default` remains shared and is not
silently chosen for an unselected chat.

**Intentional intermediate behavior (stacked-to-main):** In WU1, `owner_id=None`
means business scope only (fail-closed). Until WU2/WU3 pass the authenticated
owner, the panel project list, `project.find`/`project.list`, and `agent_context`
see only `NULL`-owner projects. Forgetting to pass the owner must fail closed,
never expose another user's project. This is a known intermediate state of the
`stacked-to-main` chain, not final user-visible functionality.

- [x] **U1.1** — Add migration 034 for `projects.owner_id`, owner-scoped slug
  uniqueness, nullable `memories.owner_id` and owner-aware memory key, and
  `project_aliases.owner_id` with backfill and `UNIQUE(owner_id, alias)`.
- [x] **U1.2** — Make list/find/create/merge and agent-context registry operations
  owner-aware; enforce per-owner slug and alias uniqueness.
- [x] **U1.3** — Preserve shared `default` handling without introducing implicit
  chat fallback; add focused migration and service tests.

**Acceptance slice:** two owners may use the same slug and alias; lookups are owner
scoped; migration backfills existing ownership safely; the shared default remains
business-owned/shared and is never an implicit chat selection.
**Checks:** migration tests and focused project service tests; `git diff --check`.
**Estimated authored size:** 180–240 changed lines.
**Rollback boundary:** migration 034 and owner-aware project registry changes.

### WU2 — private memory and explicit chat project binding

**Start:** WU1 merged to main and included in the child branch.
**End:** memory and agent chat flows consistently enforce user ownership; no
silent default fallback remains.

- [ ] **U2.1** — Add owner-aware write guard, upsert, and recall in
  `app/services/tukulpan.py`; preserve `owner_id=NULL` for business memory.
- [ ] **U2.2** — Bind thread creation and project use to the authenticated owner in
  `app/services/agent_chat.py`; require an explicit project selection.
- [ ] **U2.3** — Update the tool registry and project tools so no tool reads or writes
  another user's project or memory; keep `projects.create` available.
- [ ] **U2.4** — Add focused tests for authorization, no implicit `default`, and
  business-memory behavior.

**Acceptance slice:** cross-user memory recall is impossible through agent chat or
tools; writes require the caller's owned project; business memory remains shared.
**Checks:** focused memory, agent-chat, and tool tests; `git diff --check`.
**Estimated authored size:** 170–240 changed lines.
**Rollback boundary:** owner enforcement in memory/chat/tool flows, independent of
the panel UI.

### WU3 — owner-filtered panel API and project UI

**Start:** WU2 merged to main and included in the child branch.
**End:** the panel lists and selects only the current user's projects and can create
them; admins receive no cross-user override.

- [ ] **U3.1** — Filter project API reads and mutations by the authenticated owner;
  add create endpoint and validation as required by the panel.
- [ ] **U3.2** — Add project selection and project creation to the panel, using the
  existing projects page/API contracts.
- [ ] **U3.3** — Ensure chat selection is explicit and empty/unselected state cannot
  silently submit against `default`.
- [ ] **U3.4** — Add API and frontend tests for owner filtering, creation, selection,
  and admin non-override behavior.

**Acceptance slice:** each role sees only its own projects; project creation is
available in the panel; chat requires selection; the existing agent create tool
continues to work.
**Checks:** focused backend API tests; `cd web && npm test`; `npm run build` from
`web/` (includes the frontend `tsc -b` type check); `git diff --check`.
**Estimated authored size:** 150–220 changed lines.
**Rollback boundary:** panel endpoints and frontend project creation/selection;
preserve the already-merged service ownership contract.

### WU4 — isolation proof and final gate

**Start:** WU3 merged to main and included in the final chain branch.
**End:** explicit cross-user tests, business-memory regression coverage, migration
verification, and full gates provide evidence for closure.

- [ ] **U4.1** — Add an explicit two-user test suite: same slug, cross-user recall
  equals zero, and shared business memory remains available.
- [ ] **U4.2** — Test owner backfill and per-user alias migration behavior, including
  collision/error cases that the migration must handle safely.
- [ ] **U4.3** — Run the full backend and web gates, build, migration apply, and
  documented rollback verification before deployment.

**Acceptance slice:** no route or tool reads or writes another user's project or
memory, admin included; the business-shared memory path still works; all required
gates pass.
**Checks:** `uv run pytest tests/`; `cd web && npm test`; from `web/`, `npm run
build`; migration via `migrate.sh`; `git diff --check`.
**Estimated authored size:** 100–160 changed lines.
**Rollback boundary:** test-only additions and final migration/rollback evidence;
production rollback remains migration 034's documented rollback plan.

### Chain order

```text
main (16ba9cbf) → WU1 → WU2 → WU3 → WU4
```

Every child branch starts from its immediate predecessor and is rebased/updated to
the current base before review. Do not push, open, or merge PRs without owner
authorization.

## Acceptance criteria

- Two users can own projects with the same slug and alias without collision.
- A user's agent-memory recall never returns another user's project memory; an
  explicit cross-user test asserts zero results.
- Business memory (`scope=customer`, knowledge base, and bot context) remains shared
  and accessible to the business.
- No route or tool reads or writes another user's project or memory, admin included.
- `default` stays business-shared; chat requires explicit project selection and never
  silently falls back to `default`.
- Project aliases are owner-scoped, migrated, and backfilled.
- The panel supports project creation and selection; `projects.create` remains.
- Existing WhatsApp behavior is unchanged.
- User administration remains unchanged and out of scope.
- Migration 034 has an explicit backfill and documented rollback; existing data is
  not silently assigned an incorrect owner.
- The agent chat remains admin-only in this unit.
- Legacy non-default projects and their agent memory are backfilled to the admin under D9, with the legacy list confirmed before applying.
- Backend suite, web suite, and web build/type check pass.

## Checks and constraints

- Strict TDD is **ON** (`openspec/config.yaml:38`): observe RED before each production
  change and GREEN after it; never invent test results.
- Backend: `uv run pytest tests/`.
- Web tests: `cd web && npm test`.
- Frontend type check and build: `cd web && npm run build`; `tsc -b` is included
  only in the build command.
- Migration: apply through `migrate.sh`; record verification and document rollback
  before deployment. Do not apply a production migration as part of this documentation
  unit.
- Per-worktree test DB: use `infra/test-db.sh` as described in
  `odd/tasks/test-db-isolation.md`; never run this worktree against another
  worktree's database.
- Use work-unit commits, keeping each slice's tests with the behavior they verify.
  Forecast is over the approximate 400-line review budget, so preserve the chosen
  `stacked-to-main` strategy and ask on risk rather than shrinking code to hit a
  line target.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| `default` remains global | Most-used chat path could mix agent context if treated as an implicit project. | Keep it business-shared; require explicit project selection; pin no-fallback behavior in tests. |
| Memory recall regresses silently | Cross-user disclosure or an agent that appears to forget context. | Two-user same-slug test; cross recall must equal zero. |
| Business memory is isolated accidentally | The bot loses customer/KB context. | `owner_id=NULL` means business memory; test shared retrieval. |
| Global slug uniqueness remains | Users cannot create the same project slug. | Replace the global unique index with owner-scoped uniqueness. |
| Alias migration/backfill collision or bad ownership | Aliases fail to migrate or resolve to the wrong owner's project. | Backfill explicitly, migrate uniqueness to `(owner_id, alias)`, test collisions and verify before deploy. |
| Memory unique-key migration touches live data | Data loss, duplicate conflicts, or incorrect ownership during migration. | Explicitly backfill existing rows to the approved owner/business scope; verify with `migrate.sh`; document and rehearse rollback. |
| `test_seed.py` or bootstrap assumptions fail with multiple users | CI or setup regression. | Verify seed and integration tests against multiple users; change only if evidence requires it. |
| Absolute isolation strands an orphaned project | No administrator can recover it in-app. | Explicitly accepted by D5; document that recovery requires database access. |
| Admin override is accidentally retained | Admin routes or tools leak other users' projects/memory. | Apply owner filters regardless of role and test admin as a non-override user. |
| Existing `default` threads/memory have ambiguous ownership | Retroactive privatization could alter behavior or lose business context. | Do not retroactively privatize in this unit; preserve existing business-shared behavior and document the migration boundary. |
| Opening the agent to non-admin roles without per-role tool filtering would escalate privileges beyond panel permissions | Operators or technicians could access mutations not available through their panel routes, including automation authoring and project rename/archive/merge. | Keep chat admin-only in this unit; define and test per-role tool authorization in the dependent `agent-role-access` unit, which must start only after this unit lands. |
| Legacy non-default projects or associated agent memory have ambiguous ownership | Incorrect backfill could assign private project context to the wrong user. | Migration 034 must enumerate legacy rows and require owner confirmation before applying; if multiple admins make a project's owner ambiguous, stop and reassign before applying. Preserve `default` as shared and business-scope memory as `owner_id=NULL`. |
| Worktree test databases collide | Parallel tests interfere or destroy fixtures. | Follow the per-worktree DB helper and verify the resolved test DB before running suites. |

## Deliberately not built (YAGNI)

- Real multi-tenant businesses.
- Per-user WhatsApp credentials or tenant-specific webhook routing.
- Admin supervision view or override access.
- Retroactive privatization of existing `default` threads or memory.
- In-app recovery for orphaned projects.

## Graph check

The graph report was read at `graphify-out/GRAPH_REPORT.md` (built from
`16ba9cbf`; god nodes include `User`, `tukulpan.py`, `agent_chat.py`, and
`services/projects.py`). The required owner/isolation query and the scoped panel
query consulted these nodes and their graph neighborhood:

- `User` (`app/models.py:238`), `UserRole` (`app/models.py:71`), `Memory`
  (`app/models.py:458`), and `InternalChatThread` (`app/models.py:798`).
- `app/services/agent_chat.py`, `app/services/tukulpan.py`,
  `app/services/projects.py`, and `app/services/users.py`.
- `app/panel/api/deps.py`, `app/panel/api/routes/chat.py`,
  `app/panel/api/routes/users.py`, and `app/panel/api/routes/projects.py`.
- `app/chat/assistant/tools/registry.py`.
- `web/src/components/pages/ProjectsPage.tsx`, `web/src/types.ts`, and
  `web/src/api.ts`.

Recorded relationships: `User` is connected to role/auth and per-user chat-thread
ownership; `Memory` is connected to the project/scope/entity/topic key and
`tukulpan.py`; project registry and `ProjectsPage.tsx` are linked through project
API/type usage. The graph supports navigation but does not prove authorization
semantics; service and route tests must establish those.

## Progress

- [ ] Graph Check recorded for planning (see nodes and relationships above).
- [x] WU1 — migration 034 and owner-aware project registry.
- Scope evidence: `scope='customer'` is written/read as customer business memory
  (`app/services/tukulpan.py:743,780,789,833,896`); `scope='panel'` is written for
  thread memory (`app/services/tukulpan.py:379,405,431,485,525` and
  `app/chat/assistant/tools/registry.py:332,376`); `scope='agent'` is the explicit
  project-axis `AGENT_SCOPE` (`app/services/tukulpan.py:59`) and is written with
  `agent:<proyecto>` (`app/chat/assistant/tools/registry.py:335,383`). The
  `daily`/`conversation` values in `app/chat/nodes/cost_gate.py:42,49` are passed
  to `costs.maybe_alert_owner`; `app/services/costs.py:265-285` writes/deduplicates
  them in `AuditLog`, not `memories`. Accordingly, migration 034 backfills
  non-`default` `panel` and `agent` memories only when exactly one admin exists;
  `customer` and `default` stay NULL. No ambiguous memory scope was found.
- `eval "$(infra/test-db.sh env)" && uv run pytest 'tests/integration/test_migrations.py::test_migration_034_backfills_only_owned_project_axis_memory' -q`
  — `2 passed`; this is the exact D9 backfill result. The broader focused command,
  `eval "$(infra/test-db.sh env)" && uv run pytest tests/integration/test_migrations.py tests/spec/test_projects_spec.py -q`,
  passed `40 passed` (one known fastembed warning).
- D9 backfill test: real scratch database migrated through 033, populated with
  legacy project/memory rows and admin user(s), then only 034 applied. It asserts
  panel+agent ownership with one admin; both remain NULL along with customer and
  default memory when exactly two admins exist; reapplying migration SQL preserves
  owner values. Focused result: `40 passed` (one known fastembed warning).
- Strict TDD evidence: temporarily checked out pre-WU1 `app/models.py` and
  `app/services/projects.py` from `fd14b106`; the service tests failed `4` tests
  (`StopIteration` for the owner-aware unique key, and three `TypeError` failures
  for missing `owner_id` parameters). Restored implementation; same suite passed
  `18 passed` (one known fastembed warning).
- `eval "$(infra/test-db.sh env)" && uv run pytest tests/` — `1539 passed, 2 warnings`;
  the warnings are the existing async `_publish_all` unawaited warning and fastembed
  pooling warning.
- `git diff --check` — passed.
- Graph check: queried `projects project_aliases memories owner user registry` in
  the main worktree and `projects service list find create merge agent_context
  project_aliases owner` in this worktree. Consulted `Project`, `ProjectAlias`,
  `Memory`, `User`, `services/projects.py` (`list`, `find`, `create`, `merge`,
  `agent_context`), `models.py`, `test_projects_spec.py`, and
  `test_migrations.py`. The undirected path connected `services/projects.py` to
  `ProjectsPage.tsx` through `api.ts`/`postJson()`; no direct directed path from
  service to model was found. The code and focused tests, not graph relationships,
  establish runtime behavior.
- WU1 native review: lineage `review-64f9d66f93cac584`, four lenses (risk, resilience,
  readability, reliability), **approved**, authority burned. Both findings are
  non-blocking and recorded here as follow-ups:
  - R2-001 (readability, WARNING, `odd/tasks/usuarios-aislamiento.md:359`): the
    `## Recovery` section still said the implementation had not started, contradicting
    this Progress. Corrected in the same follow-up commit that records this review.
  - R3-001 (reliability, WARNING, `app/services/projects.py:180-184`): `_lock_projects`
    infers the owner from the first `Project` argument, but `merge` validates
    `source_row.owner_id != owner_id` against the possibly-`None` argument, so a caller
    that passes owned `Project` objects without `owner_id` raises even for same-owner
    projects, while string-slug callers without an owner only see the shared namespace.
    The optional-owner contract must be settled explicitly (infer consistently or require
    the owner) in WU2, with a test for the omitted-argument path.
- [ ] WU2 — owner-aware memory, explicit project-bound chat, and tools.
- [ ] WU3 — owner-filtered panel API and project selection/creation.
- [ ] WU4 — cross-user isolation suite and final gate.
- [ ] Migration apply, verification, and rollback documentation completed.
- [ ] Acceptance criteria verified; unit closed.

## Closure

To be completed after implementation, verification, and the stacked PR chain are
complete. Record merged PRs, exact test results, migration evidence, and cleanup.

## Recovery

- Resume in `/home/stefan/repos/lumat-agent-odd-usuarios-aislamiento` on
  `odd/usuarios-aislamiento`; current planning base is `16ba9cbf`.
- WU1 is implemented and its native review is approved (authority burned). Continue the
  chain with WU2. Confirm the branch includes the current main base before beginning a
  work unit; the chain is WU1 → WU2 → WU3 → WU4.
- Provision dependencies for the worktree as needed. Copy the ignored database
  environment file only as documented in `odd/tasks/test-db-isolation.md`; use
  `infra/test-db.sh up`, `eval "$(infra/test-db.sh env)"`, and `infra/test-db.sh down`
  for this worktree's test database.
- For each unit, run focused tests first. Final gates: `uv run pytest tests/`,
  `cd web && npm test`, and `cd web && npm run build`.
- Apply migration 034 only through `migrate.sh`; verify it and keep rollback steps
  documented before any deployment.
- Do not start `agent-role-access` until `usuarios-aislamiento` is delivered. The
  dependent-unit handoff is `/home/stefan/repos/lumat-agent/.rapsodia-code/handoffs/2026-09-28-agent-role-access.md`;
  its base must be this unit's closure commit.
- Do not push, open PRs, merge, or deploy without explicit owner authorization.
