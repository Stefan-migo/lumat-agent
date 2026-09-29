# ODD Task: usuarios-aislamiento

Status: open — WU1, WU2, and WU3 merged; WU4 remains
Worktree: none live — the WU3 worktree `../lumat-agent-odd-usuarios-aislamiento-wu3` was removed at cleanup
Branch: WU1 on `odd/usuarios-aislamiento` (merged, PR #400); WU2 on `odd/usuarios-aislamiento-wu2` (merged, PR #407); WU3 on `odd/usuarios-aislamiento-wu3` (merged, PR #412, branch deleted)
Base: `2adc0eb9` (current `origin/main`, the WU3 merge)
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
- `Memory` is defined at `app/models.py:504`; its unique key is `(owner_id, proyecto, scope, entity_id, topic_key)` (`app/models.py:514-518`). Migration 037 scopes normalized-content deduplication to `(owner_id, proyecto, scope, entity_id, normalized_hash)`, with `NULLS NOT DISTINCT` and a partial predicate for non-NULL hashes (`db/migrations/037_memory_owner_dedup.sql:4-6`); it was authored as 035, renumbered to 036 when main's PR #402 took 035 for `035_customer_equipment.sql`, and renumbered again to 037 when main's PR #404 merged `036_case_amount.sql`. Migration 034 adds/backfills the owner axis (`db/migrations/034_project_owners.sql`). The implementation is `app/services/tukulpan.py`; `app/services/memory.py` re-exports it.
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

- [x] **U2.1** — Add owner-aware write guard, upsert, and recall in
  `app/services/tukulpan.py`; preserve `owner_id=NULL` for business memory.
- [x] **U2.2** — Bind thread creation and project use to the authenticated owner in
  `app/services/agent_chat.py`; require an explicit project selection.
- [x] **U2.3** — Update the tool registry and project tools so no tool reads or writes
  another user's project or memory; keep `projects.create` available.
- [x] **U2.4** — Add focused tests for authorization, no implicit `default`, and
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

- [x] **U3.1** — Filter project API reads and mutations by the authenticated owner;
  add create endpoint and validation as required by the panel.
- [x] **U3.2** — Add project selection and project creation to the panel, using the
  existing projects page/API contracts.
- [x] **U3.3** — Ensure chat selection is explicit and empty/unselected state cannot
  silently submit against `default`.
- [x] **U3.4** — Add API and frontend tests for owner filtering, creation, selection,
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
main (e98b6683) → WU1 (merged) → WU2 → WU3 → WU4
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

- [x] Graph Check recorded for planning and U2.3 (see nodes and relationships above).
- [x] WU1 — migration 034 and owner-aware project registry.
- [x] U2.1 — owner-scoped memory writes/recall, dedup index, and consistent project merge owner resolution.
  - `feat(db): scope memory content dedup index by owner` → `2953102a`
  - `feat(memory): scope memory writes and recall by owner` → `4c5a0add`
  - `fix(projects): resolve one consistent owner for project merge` → `72da3d6a`
  - Strict TDD observed: service RED was `TypeError: upsert() got an unexpected keyword argument 'owner_id'` before implementation. Migration RED was an `AssertionError` showing the pre-035 index `(proyecto, scope, entity_id, normalized_hash)` without `owner_id`; recovered by reverting only the migration and ORM index, then rerunning `test_memory_dedup_index_includes_owner_and_allows_cross_owner_duplicates`. Both were GREEN after restore.
  - Full backend suite on the branch: `uv run pytest tests/` → `1544 passed, 2 warnings`; the warnings are the known pre-existing `_publish_all` and fastembed pooling warnings.
  - `git diff --check` passed.
- U2.2 registration (landed before this U2.3 work):
  - `b6213632` makes `_effective_owner_id` derive ownership from project authorization and reject contradictory explicit owners, closing finding R1-001 at the write seam.
  - `744bbe55` binds `agent_chat` thread creation and project use to the authenticated owner; `e641283e` aligns fixtures.
  - Strict TDD RED exposed that the inserted memory had `owner_id=None` despite owner-bearing authorization. The focused test passed after implementation.
  - Full suite on `e641283e`: `1546 passed` with the two known pre-existing warnings.
- U2.3 scope decision (owner decision): explicit project-selection enforcement remains in WU3 (option B); U2.2 delivered owner binding only.
- [x] U2.3 — owner-scoped assistant registry and project/memory tools, retaining `project.create`.
  - Added the authenticated `owner_id` parameter and a fail-closed guard for project/memory tools whenever a positive trusted thread id is present without an owner.
  - Project list/find/create/rename/archive/merge now forward the owner; `projects.rename` and `projects.archive` accept owner scope. `memory.read`/`search` resolve project authorization and filter both own-memory axes by that project's owner, while customer memory remains business-scoped. Writes derive ownership from project authorization; update/delete verify the row owner.
  - Propagated `state.user_id` from both assistant node tool-execution sites and `thread.user_id` plus `thread.id` from `_run_sdb_tasks`. Project creation flushes at the registry boundary so the same SDB run can resolve the newly created project for its next task.
  - Replaced the mocked blind spot with `tests/integration/test_assistant_tool_owner_isolation.py`, using the real test database and real `execute_tool`/`agent_context` paths. It covers SDB project creation and following project use, two users sharing a slug, cross-owner memory read/update/delete denial, business-memory visibility, and project-list isolation.
  - Strict TDD RED observed before implementation: `eval "$(infra/test-db.sh env)" && uv run pytest tests/integration/test_assistant_tool_owner_isolation.py -q` failed on unmodified production code with:
    ```text
    >           assert project.owner_id == thread.user_id
    E           assert None == 1
    E            +  where None = <app.models.Project object at 0x7f0aae0ff750>.owner_id
    E            +  and   1 = <app.models.InternalChatThread object at 0x7f0aae236f90>.user_id
    ```
    GREEN after implementation: the same command passed `2 passed`.
  - Focused verification: `eval "$(infra/test-db.sh env)" && uv run pytest tests/integration/test_assistant_tool_owner_isolation.py tests/unit/test_assistant_tools.py tests/spec/test_sdb_recovery.py tests/spec/test_projects_spec.py tests/spec/test_memory_spec.py tests/unit/test_agent_chat_thread_project.py tests/integration/test_assistant_harness_compatibility.py tests/unit/test_memory_tool_axes.py -q` passed `194 passed` with one known fastembed pooling warning.
  - Required focused command over the integration, assistant tools, SDB recovery, project spec, memory spec, and agent-chat project tests passed `166 passed` with one known fastembed pooling warning.
  - Full backend suite: `eval "$(infra/test-db.sh env)" && uv run pytest tests/` passed `1562 passed, 2 warnings`; warnings were the known `_publish_all` unawaited coroutine and fastembed pooling warnings.
- WU2 native review (slice 2 + U2.3), lineage `review-016eba14e5434eaa`: **approved**, authority
  **burned** (`gentle-ai.review-acknowledged/v1`, consumed revision
  `sha256:3a3c896d7f0464cae275a04fc643859f4e48e7c14b2257e29f2d83a8da01fa70`). The candidate is
  this branch's own unreviewed work with base `f27077ec` (the merged `origin/main`): 21 paths,
  664 changed lines, tier `high`, correction budget 200, four lenses (risk, resilience,
  readability, reliability), no correction opened. That base is deliberate: the previous
  boundary `18f78aca` is a branch commit, so `18f78aca..HEAD` also carried the
  `agenda-agente-whatsapp` content merged from main (1438 lines) that was already reviewed and
  burned in its own lineage (PR #403); `f27077ec..HEAD` isolates this unit's work. All three
  findings are non-blocking advisory follow-ups, not reopened review:
  - R2-001 (readability, WARNING, `tests/unit/test_memory_tool_axes.py:187`): only some of the
    non-default-project own-memory tests install the `projects.agent_context` mock, so those
    axis assertions are weaker than they read.
  - R2-002 (readability, SUGGESTION, `app/chat/assistant/tools/registry.py:623-624`): the
    owner-scoped guard infers tool families from name prefixes; explicit tool metadata would
    survive a future rename.
  - R3-001 (reliability, WARNING, `app/chat/assistant/tools/registry.py:618`): the
    owner-presence guard only rejects a missing owner when a positive `trusted_thread_id` is
    supplied, so an owner-scoped tool called without that id can still run with
    `owner_id=None` against the null-owner namespace. Harden this fail-closed contract in U2.4.
- WU1 merge registration: WU1 merged as PR #400 → merge commit `c4ad6fe2`. PR #399 (`docs(odd): close the case-closure-fix unit`) merged afterward as `e98b6683`, the current `main`.
- R3-001 closed by `fix(projects): resolve one consistent owner for project merge` (`72da3d6a`): one `_resolve_owner_id` resolution point is shared by `merge` and `_lock_projects`; an explicit `owner_id` wins, disagreeing objects raise, and an explicit owner contradicted by an owned `Project` raises.
- Schema finding and fix: migration 037 (`db/migrations/037_memory_owner_dedup.sql`, authored as 035, renumbered to 036 when main's PR #402 took that number for customer equipment, and renumbered again to 037 when main's PR #404 merged `036_case_amount.sql`) replaces `uq_memories_normalized_content`, created in migration 028 on `(proyecto, scope, entity_id, normalized_hash)` without `owner_id`, with an owner-scoped index on `(owner_id, proyecto, scope, entity_id, normalized_hash) NULLS NOT DISTINCT WHERE normalized_hash IS NOT NULL`; `app/models.py` is aligned. WU1 allows two owners to share a project slug, so without this, upsert could resolve and rewrite another owner's row and legitimate inserts could collide. Rollback SQL is documented in the migration file.
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
- U2.3 graph check ran from `/home/stefan/repos/lumat-agent` without rebuilding.
  Queries covered assistant tool registry and project/memory owner scoping. Consulted
  nodes: `Registry`, `execute_tool()`, `ToolValidationError`, `_read_memory()`,
  `_owned_agent_memory_or_raise()`, `projects.py`, `nodes.py`, `agent_chat.py`,
  `Project`, `Memory`, and `InternalChatThread`; neighborhoods connect registry
  dispatch to project/memory services and SDB execution to tool execution.
  `graphify path "execute_tool()" "_run_sdb_tasks()"` returned “No directed path
  found”; recorded as the permitted degenerate path, not a blocker.
- WU1 native review: lineage `review-64f9d66f93cac584`, four lenses (risk, resilience,
  readability, reliability), **approved**, authority burned. Both findings are
  non-blocking and recorded here as follow-ups:
  - R2-001 (readability, WARNING, `odd/tasks/usuarios-aislamiento.md:359`): the
    `## Recovery` section still said the implementation had not started, contradicting
    this Progress. Corrected in the same follow-up commit that records this review.
- R3-001 (reliability, WARNING, `app/services/projects.py`): resolved in
  `72da3d6a`; `_resolve_owner_id` is shared by merge and project locking, with
  tests for inferred, explicit, and contradictory owner paths.
- U2.4 — focused owner authorization coverage and the R3-001 fail-closed hardening.
  - `279a2471 fix(chat): require the authenticated owner for project tools` — `execute_tool`
    now fails closed whenever a `project.*` tool is called without an authenticated `owner_id`,
    independent of `trusted_thread_id` (R3-001). Memory behavior is unchanged: own-scope
    read/search already fail closed on a missing thread in their handler, all three memory
    writes are covered by the autonomous-write guard, and customer-scope memory stays
    business-shared. The existing project-tool unit tests now pass `owner_id=1`, so they keep
    testing approval/argument mechanics instead of the new guard.
  - `fb5a03d8 test(chat): cover cross-owner recall and shared business memory` — the
    integration suite now asserts cross-owner recall is zero through the real tool path, that
    customer business memory stays shared (read and search), and that an ownerless
    `project.list` fails closed. `tests/unit/test_memory_tool_axes.py` gains a focused test
    proving the derived owner reaches both own-memory axes for a non-default project (R2-001).
  - `48615439 test(chat): relocate same-slug thread binding coverage to integration` —
    discovered during U2.4 verification: `test_same_slug_projects_bind_and_resolve_by_authenticated_owner`
    used a real database but lived in `tests/unit/`, whose conftest makes `migrated_db`/`clean_db`
    no-ops for the DB-free unit suite; it only passed when another suite migrated first. Moved
    to `tests/integration/test_agent_chat_thread_project.py` so it gets a migrated, truncated
    database regardless of test order.
  - Strict TDD RED: before the guard change,
    `tests/unit/test_assistant_tools.py::test_project_tools_fail_closed_without_authenticated_owner`
    failed with `Failed: DID NOT RAISE ToolValidationError` on the first `project.list`
    assertion; GREEN after.
  - Focused suite (order-independent): `114 passed`. Full backend suite: `1568 passed, 2
    warnings` (the known `_publish_all` unawaited and fastembed pooling warnings).
    `git diff --check` passed.
  - R3-001 closed. R2-001 addressed with the focused owner-threading test. R2-002 (explicit
    tool metadata instead of name prefixes) remains a non-blocking suggestion.
- Branch state after the crash: the branch had already merged `origin/main` at `1aa0a060`
  (parents `82922ce5`, `4a67d6be`) before U2.4 started; this merge was not recorded in memory or
  in the prior handoff and is documented here. Delivery decision (owner, 2026-09-28): WU2 ships
  as a **single PR with maintainer-approved `size:exception`** (the slice is ~668 changed lines
  over the ~400 review budget); it is not split.
- WU2 full-slice native review (owner-granted on the whole PR slice), lineage
  `review-b2bdde6e4c280287`: **approved**, authority **burned**
  (`gentle-ai.review-acknowledged/v1`, consumed revision
  `sha256:e27d17aec90de75770233a96888c8462bf3bb414bb514f3181c7a8a053c55138`). Candidate is the
  branch's own work against current `origin/main`: 22 paths, 840 changed lines, tier `high`,
  correction budget 200, four lenses (risk, resilience, readability, reliability), **zero
  findings**, no correction opened. This is the WU2 PR-slice review, distinct from the earlier
  U2.1–U2.3 review (`review-016eba14e5434eaa`); it was run because the merged-main range made
  the slice over the review budget and high-risk (`tests/integration/test_migrations.py`
  `shell_process`). Review is now closed; push/PR/merge remain separate owner decisions.
- [x] WU2 — owner-aware memory, thread/project binding, and tools (U2.1–U2.4 delivered).
- [x] WU3 — owner-filtered panel API and project selection/creation.
  - [x] U3.1 — owner-scoped project reads and the authenticated create endpoint (`82a09a44`).
    - Strict TDD RED verified by the orchestrator against unmodified production code:
      `assert ['shared', 'shared'] == ['shared']` (the old list exposed another owner's
      same-slug project) and `assert 405 == 201` (no create route existed). GREEN after:
      `32 passed, 1 warning` (the known fastembed pooling warning); `git diff --check` clean.
    - Reads: `GET /panel/api/projects` and `GET /panel/api/projects/{slug}` filter
      `Project.owner_id == current.id`; the SDB artifact browse also filters
      `Memory.owner_id == current.id`, so a same-slug project owned by another user cannot
      leak artifacts. A non-owned project is a 404, never a 403, and an admin gets no
      override.
    - Creation: `POST /panel/api/projects` (201, `require_operator_json`) mirrors the
      `ProjectCreateArgs` bounds so panel and agent tool cannot drift, resolves the owner
      from the session, and returns 409 with `candidates` on a purpose ambiguity. A
      duplicate slug for the same owner is also 409: RED showed an uncaught `IntegrityError`
      (`uq_projects_owner_normalized_slug`) would have answered 500.
    - Owner decision (2026-09-28): U3.3 enforcement is **strict** — the chat thread endpoint
      will require an explicit `proyecto`, and the ~53 existing `json={}` call sites in 8
      integration test files are updated to `{"proyecto": "default"}`.
  - [x] U3.2 — project creation and selection in the panel (`3d592cc0`, `d511e693`).
    - `ProjectsPage` gains a bounded creation form (slug/name/purpose, mirroring the API bounds) that calls
      the new `createProject` helper and refreshes the list on 201. A 409 surfaces the conflicting
      candidates when present and the duplicate-slug `detail` otherwise. Opening a project still navigates
      to chat bound to that project (`AppShell`), which is the panel's selection surface.
  - [x] U3.3 — explicit chat project selection, no silent `default`
    (`c2fde67d`, `ec3cdbb4`, `32942a88`, `525f35b5`, `b7a8ff95`).
    - Backend: `POST /panel/api/chat/threads` requires `proyecto`; the `else "default"` fallback is gone and
      an explicitly sent `"default"` still binds the business-shared project (owner decision: strict).
    - Client: `createChatThread(proyecto: string)` always sends `{proyecto}` — the `{}` branch is gone. The
      `AgentChat` "Nuevo chat" flow reuses the URL/thread project when present and otherwise lists the
      user's own projects in a picker, refusing to create a thread when nothing is selected.
    - Fixtures: 54 call sites across 8 integration test files now state `{"proyecto": "default"}`. The first
      sweep missed one `f"..."` call site (`test_assistant_chat.py:938`) and only the full backend suite
      caught it; `525f35b5` fixes it. Focused files alone are not a sufficient gate here.
    - RED for the route contract: `3 failed, 7 passed` before the change (body-less and `{}` creation
      returned 201), GREEN `10 passed` after.
  - [x] U3.4 — route and frontend contract tests.
    - `tests/integration/test_chat_thread_project_selection.py`: no body → 422, `{}` → 422, another user's
      project → 400 with no thread row created, own project → 201 bound to it, explicit `"default"` → 201.
    - `tests/functional/test_api_projects.py`: owner-scoped list/detail, same-slug isolation, artifact owner
      scoping, admin non-override, creation ownership, purpose ambiguity → 409 with candidates, duplicate
      slug → 409, invalid body → 422.
    - `web`: `ProjectsPage.test.tsx` (creation success and both 409 shapes), `AgentChat.test.tsx` (picker
      instead of a silent default, no thread without a project), `api.test.ts` (the POST always carries
      `proyecto`).
  - Gate results with WU3 applied: `uv run pytest tests/` → `1592 passed, 2 warnings` (the known
    `_publish_all` unawaited and fastembed pooling warnings); `cd web && npm test` → `90 test files, 835
    tests passed`; `cd web && npm run build` (`tsc -b` + vite) passed; `git diff --check` clean. No Python
    linter/formatter is configured in this repo, so tests and the build are the complete check set.
  - WU3 delivered as **PR #412** (`feat(panel): owner-scoped project API and explicit chat project
    selection`), merged as `2adc0eb9` with a merge commit and a single `type:feature` label, under
    maintainer-approved `size:exception` (634 changed lines: 498 insertions, 136 deletions over 20 files).
  - Native review of the delivered candidate: lineage `review-89e87986c882ceaa`, tier `medium`, one lens
    (reliability), **approved**, authority burned (`gentle-ai.review-acknowledged/v1`, consumed revision
    `sha256:f1dda9cd…`). An earlier review of the same own-work candidate
    (`review-a650106515207a19`, zero findings) was invalidated when `origin/main` advanced to
    `ef76b729` after it; the branch then merged main (`30f6d127`), the integration was re-run over the
    merged tree (`1600 passed` backend, `835` web, build OK — main touched none of the 20 files) and the
    review was repeated against the real tree. CI was green (`panel` 2m49s, `test` 2m40s, GitGuardian
    pass) and `origin/main` was verified contained in the branch before merging.
  - Advisory follow-up from the WU3 delivery review, non-blocking and deliberately not corrected on this
    candidate: **R3-001** (`web/src/components/pages/ProjectsPage.tsx:35-40`) — the creation POST and the
    follow-up list refresh share one `try`, so a refresh failure after a successful create is reported as
    a creation error and the persisted project does not appear until reload. Route it to WU4.
  - Cleanup after merge: worktree `../lumat-agent-odd-usuarios-aislamiento-wu3` removed, branch
    `odd/usuarios-aislamiento-wu3` deleted locally and remotely, this worktree's `db-test` container and
    network removed, and local `main` fast-forwarded to `2adc0eb9`.
- [ ] WU4 — cross-user isolation suite and final gate.
- [ ] Migration apply, verification, and rollback documentation completed.
- [ ] Acceptance criteria verified; unit closed.

## Closure

To be completed after implementation, verification, and the stacked PR chain are
complete. Record merged PRs, exact test results, migration evidence, and cleanup.

## Recovery

- WU3 is merged: **PR #412**, merge commit `2adc0eb9` (see the Progress record). Its worktree was removed
  and its branch deleted locally and remotely.
- Next slice: **WU4** — cross-user isolation suite, migration 034 apply/rollback verification, and the
  final gate, plus the advisory **R3-001** from the WU3 delivery review
  (`web/src/components/pages/ProjectsPage.tsx:35-40`). Create its worktree following the ODD convention
  (`../lumat-agent-odd-<slug>`) from the current `origin/main` (`2adc0eb9`).
- Delivery is `stacked-to-main` (`ask-on-risk`); WU4 is the fourth PR of the chain and its candidate is
  its own work against the current `origin/main`. Isolate it with `git diff --stat <base-ref> HEAD`
  before any review, because a branch commit as `--base-ref` drags already-reviewed main content into
  the candidate.
- Never mutate a branch after the review authority is burned, docs included: the delivered candidate must
  equal the reviewed one. A merge-time record goes in a later doc-hygiene PR, as WU1–WU3 did.
- Per-worktree test database: `infra/test-db.sh up` / `eval "$(infra/test-db.sh env)"` /
  `infra/test-db.sh down`, with `infra/.env` copied from the primary worktree and never sourced before
  `test-db.sh env`. The WU3 worktree derived port `5592` and Compose project
  `lumat-test-lumat-agent-odd-usuarios-aislamiento-wu3`; both were torn down at cleanup.
- Graphify is PARTIAL: `graphify . --update` fails the semantic chunking step with
  `402 Insufficient Balance` and `tree_sitter_sql` is missing, so the graph is navigation
  only, never authority.
- Migration 034 still has a production-apply gate: apply only through `migrate.sh`; verify it
  and keep rollback steps documented before any deployment.
- Do not start `agent-role-access` until `usuarios-aislamiento` is delivered. The
  dependent-unit handoff is `/home/stefan/repos/lumat-agent/.rapsodia-code/handoffs/2026-09-28-agent-role-access.md`;
  its base must be this unit's closure commit.
- Do not push, open PRs, merge, or deploy without explicit owner authorization.
