# ODD: memory-per-project-thread

## Objective

Make the project namespace a real, persisted property of a panel chat thread so that agent memory
declared `global` is scoped to that thread's project, closing the live MEM-9 violation in which a
global memory written while working in one project is reachable from any other project.

## Problem

`Memory.proyecto` has been the isolation axis since `009_memory.sql`, and `024_projects.sql` made
`proyecto` a real registry namespace. The spec already requires the qualified agent entity:

- `openspec/specs/memory/spec.md:157-160` (MEM-9): "The agent-axis entity MUST be project-qualified
  as `entity_id='agent:<project>'` so a memory declared `global` inside one project can never be
  reached by a read bound to another project."
- `openspec/specs/memory/spec.md:177-180` (MEM-9 scenario): a global-visible memory written from one
  thread is readable from "another thread **in the same project**".
- `openspec/specs/memory/spec.md:51`, `:66` (MEM-3): an `own` read unions the trusted thread axis
  with the **project-qualified** agent axis, returning "global-visible agent memories **from the same
  project**".
- `openspec/specs/assistant-tools/spec.md:63-65` (AT-9): `global` resolves to `scope="agent"`,
  `entity_id="agent:<project>"`, "with the project bound server-side".

The code pins the whole axis to one namespace instead:

- `app/services/tukulpan.py:58` — `WRITABLE_PROYECTO = "default"`, a hard constant.
- `app/chat/assistant/tools/registry.py:33` — `_AGENT_MEMORY_ENTITY` is frozen at import from that
  constant.
- `app/chat/assistant/tools/registry.py:316` — `_write_memory` hardcodes `memory.WRITABLE_PROYECTO`
  and never passes an `authorization`, so a non-default write would raise at
  `_guard_writable_project` (`app/services/tukulpan.py:128-138`).

So a memory declared `global` is written to `agent:default` and is reachable from every project. That
is precisely what MEM-9 says "can never" happen. It is a live violation, not a future risk.

**The missing plumbing is the thread binding.** `InternalChatThread` has no project column
(`app/models.py:797-809`), and there is no production path — backend or frontend — that binds a
thread to a project:

- `app/panel/api/routes/chat.py:262-292` never passes `project_authorization`; it defaults to `None`
  (`app/services/agent_chat.py:811`).
- `create_thread` takes no project (`app/services/agent_chat.py:500-506`).
- `app/services/agent_chat.py:997`, `:1149` read the project from `assistant_state.sdb.proyecto`,
  which only `persist_sdb_state` writes (`app/services/agent_chat.py:335-339`) from the same
  `state["project_authorization"]` nobody sets — circular.
- `app/panel/api/routes/projects.py` exposes only `GET /projects` and `GET /projects/{slug}`.
- `web/src/components/pages/ProjectsPage.tsx` has no chat, SDB, assistant or thread reference.

The only non-default slug anywhere in production code is a test fixture
(`tests/spec/test_projects_spec.py:202`).

## Why

- The unit is open in the memory backlog as item 2 and is the item whose cost grows with delay:
  every historical row keeps landing in `proyecto="default"` and has to be reclassified later via
  `origin_thread_id` → thread → project. The longer it waits, the larger that set.
- The design already anticipates it: `agent_memory_entity()` (`app/services/tukulpan.py:101-108`)
  documents that the project qualifies the entity "even when the writable namespace widens", and
  `_guard_writable_project` already requires a `_ProjectAuthorization` for a non-default write.
- No data migration is needed: `proyecto` is already in
  `UNIQUE(proyecto, scope, entity_id, topic_key)` (`app/models.py:466-478`).
- The correction that unblocked this unit: the handoff (`handoff/memory-backlog-next`) expected a spec
  amendment to MEM-9/AT-9. Verified against the real spec, that is wrong — the requirements already
  carry the project-qualified contract. The gap is implementation, so this unit amends no
  requirement, only one stale Purpose sentence.

## Scope

**In:**

- Migration `031_internal_chat_thread_project.sql`: `internal_chat_threads.proyecto`.
- `create_thread` accepts a server-validated project namespace and persists it on the thread.
- A single derivation point: the turn's project comes from the thread, not from the request.
- The memory tool axis is bound by the thread's project; the agent entity is resolved per call.
- `POST /chat/threads` accepts an optional project slug; the thread serializer exposes `proyecto`.
- The stale Purpose sentence in `openspec/specs/memory/spec.md:5`.
- Tests: the MEM-9 project-isolation scenario, the tool axis, and migration 031.

**Out:**

- The web entry point in the project page. Slice 2; it is an affordance over an API that slice 1
  already makes reachable.
- `Memory.proyecto`, its unique key, and the `memory_visibility` enum — already correct.
- A foreign key from the thread to `projects`. The slug is a stable namespace identifier; a rename
  changes presentation only and must never rewrite the namespace
  (`openspec/changes/archive/2026-09-12-projects/design.md:9-14`).
- Reclassifying historical rows; no data migration.
- `AT-8` (`openspec/specs/assistant-tools/spec.md:29-31`), which declares
  `scope="panel"|"customer"|"agent"` while the code exposes `own|customer`
  (`app/chat/assistant/tools/registry.py:90-108`) and the tests reject `panel|agent`
  (`tests/unit/test_memory_tool_axes.py:109-115`). Pre-existing drift against MEM-3
  (`openspec/specs/memory/spec.md:51`); a separate advisory, not this unit.
- `assistant_state.sdb.proyecto` keeps being written as the SDB run's mirror; it stops being the
  authority. No change to its shape.
- `persist_sdb_state`'s from-`authorization` behavior. MEM-8 requires the seam to accept an explicit
  `proyecto`; only the caller's derivation changes.
- `db/migrate.sh`, and the memory service layer beyond the thread binding.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-memory-per-project-thread`
- Branch: `odd/memory-per-project-thread`
- Base: `9760a1e7` (main at worktree creation; `0fe3eae7` is an ancestor. Between them the
  vps-ops continuity work landed — `docs/`, `infra/` and `odd/tasks/` only, nothing under `app/`,
  `openspec/` or `db/`, so every line anchor in this record still resolves.)
- Slice 1 files, as delivered: `db/migrations/031_internal_chat_thread_project.sql`,
  `app/models.py`, `app/services/agent_chat.py`, `app/chat/assistant/tools/registry.py`,
  `app/chat/assistant/nodes.py`, `app/panel/api/routes/chat.py`, `app/panel/api/serializers.py`,
  `openspec/specs/memory/spec.md`, `tests/integration/test_migrations.py`,
  `tests/integration/test_h4_chat.py`, `tests/integration/test_assistant_harness_compatibility.py`,
  `tests/spec/test_memory_spec.py`, `tests/unit/test_agent_chat_thread_project.py`,
  `tests/unit/test_assistant_tools.py`, `tests/unit/test_memory_tool_axes.py`, and this record.
  Two deviations from the planned list, both recorded rather than papered over: the T2/T3 unit tests
  went to a new `tests/unit/test_agent_chat_thread_project.py` instead of `tests/spec/test_memory_spec.py`,
  and the panel-API test went to `tests/integration/test_h4_chat.py` alongside the existing
  thread-creation coverage instead of `tests/functional/test_api_memories.py`, which was not touched.

## Constraints

- **Strict TDD: ON** — source: `openspec/config.yaml` (`testing.strict_tdd: true`). Runner:
  `uv run pytest tests/`. RED is required before each behavioural change, then GREEN, then REFACTOR.
- **Fail closed.** An unauthorized, unknown, or archived project MUST be rejected before persistence.
  The write path MUST re-validate the capability rather than trust the stored slug.
- Migration 031 MUST be idempotent under the runner. `ADD COLUMN IF NOT EXISTS ... NOT NULL DEFAULT`
  fills existing rows, so there is no separate backfill statement.
- The app role's grants on `internal_chat_threads` are table-level
  (`db/migrations/020_assistant_metadata.sql:15`), so a new column needs no grant statement.
- `test_schema_migrations_records_version` (`tests/integration/test_migrations.py:257-288`) lists
  every applied version explicitly and MUST gain `031`.
- `POST /chat/threads` currently takes no body (`app/panel/api/routes/chat.py:65-67`); the change MUST
  stay backwards compatible for existing callers.
- The tool handlers MUST NOT accept the project from the model; it is bound server-side. An
  unrecognised argument MUST still be rejected by the argument models.
- `persist_sdb_state` MUST keep accepting `authorization` and deriving `proyecto` from it (MEM-8).
  The thread binding applies at its callers, never inside the seam.
- `_run_agent_turn_session` and `submit_message` take `project_authorization` and no caller supplies
  a non-`None` value (production enters through `run_agent_turn`, `app/services/agent_chat.py:775-790`).
  The thread becomes the single source; a caller-supplied namespace MUST NOT silently override it.
- One concern, `≤5` files per commit.
- `pyproject.toml` sets `addopts = "-q"`; use `-o addopts=""` when the count matters. The per-test
  timeout is 120s.
- Lint is not run: `ruff` is not installed and no linter is configured.

## Design decision

**D1 — the project is a property of the thread, persisted.** Chosen over deriving it per turn from
the request. A turn-derived namespace flickers: a plain turn would write `agent:default` and a
following SDB turn `agent:<slug>`, so one thread's `own` read (thread axis ∪ agent axis) would return
an incoherent set, and `global` would stop meaning one stable thing per thread. The spec treats the
namespace as a boundary, so it must be stable for the life of the thread.

**D2 — the binding is explicit at thread creation, validated server-side, chosen by a human.** The
model never selects the namespace, matching AT-9's "the project bound server-side". `create_thread`
normalizes and validates the slug through `projects.agent_context`, which requires an active project
(`app/services/projects.py:151-157`).

**D3 — one derivation point.** `_run_agent_turn_session` already holds both `session` and `thread`
and already forwards `project_authorization` into `run_assistant`
(`app/services/agent_chat.py:629`, `:646-668`). Deriving the capability there from the thread column
makes `state["project_authorization"]` authoritative for the whole turn and always equal to the
thread's binding. This closes the divergence in `_project_slug`
(`app/chat/assistant/nodes.py:51-60`), which today returns `"default"` whenever the turn carries no
capability — i.e. it would disagree with a project-bound thread.

**D4 — no foreign key; the column mirrors `Memory.proyecto`'s shape.** `VARCHAR(100) NOT NULL DEFAULT
'default'`, exactly as `app/models.py:480-482`. Renaming a project changes presentation, never the
namespace, so the slug is deliberately not a foreign key.

**D5 — the write path re-validates the capability.** `_write_memory` obtains it via
`projects.agent_context(session, proyecto)` for a non-default project instead of trusting the stored
slug. One extra query per non-default write, and the project's live status is re-checked: if it was
archived after the thread was bound, the write is rejected rather than persisted.

**D6 — the agent entity is resolved per call.** `_AGENT_MEMORY_ENTITY`
(`app/chat/assistant/tools/registry.py:33`) is a module constant frozen at import from
`WRITABLE_PROYECTO`; it becomes `memory.agent_memory_entity(proyecto)` at each call site.

**D7 — the SDB seam keeps its explicit namespace; the caller is what binds it to the thread.**
MEM-8 (`openspec/specs/memory/spec.md:130-133`) requires every seam to accept an explicit `proyecto`
and SDB to pass authorized namespaces through. That contract is untouched: `persist_sdb_state` keeps
deriving `proyecto` from the `authorization` it is handed, so
`test_project_aware_sdb_persistence_uses_authorized_namespace`
(`tests/integration/test_sdb_persistence.py:260-286`) stays valid as the seam's own unit proof.
What changes is the caller: `_run_sdb_tasks` derives its capability from the thread
(`_thread_project_authorization`), so a run can never name a namespace different from its thread's.
The seam stays parameterized; the product cannot diverge.

**No backfill of `assistant_state.sdb.proyecto`, and this is provable, not assumed.** Its only writer
is `persist_sdb_state`, and its only production callers pass `_thread_project_authorization(thread)`
(`app/services/agent_chat.py:997`, `:1149`), which returns the declared namespace and `None` when it
is `'default'`. Starting from `'default'` that is a fixed point: `None` in, `'default'` out, forever.
No production thread can hold a non-default `sdb.proyecto`, so the column needs no reconciliation
pass and the column is the sole authority. The writer MUST confirm this with a query against the dev
database before relying on it.

Rejected: adding a project argument to `memory.write`/`memory.read` so the model chooses — it
contradicts AT-9 and MEM-9, which require the server to derive the target.
Rejected: promoting `assistant_state.sdb.proyecto` to the authority instead of adding a column — it
is buried in the SDB sub-object, only filled by one flow, and a namespace axis belongs in a declared
column that can be queried.
Rejected: a foreign key — a rename must not rewrite the namespace.

Trade-off accepted: `assistant_state.sdb.proyecto` remains written as a mirror, so the value exists in
two places. They are consistent by construction because both derive from the same capability, and the
column is the authority.

## Tasks

- [x] **T1** — Schema: migration `031_internal_chat_thread_project.sql` with
      `ADD COLUMN IF NOT EXISTS proyecto VARCHAR(100) NOT NULL DEFAULT 'default'`, the matching
      `InternalChatThread.proyecto` column, and the `031` entry in
      `test_schema_migrations_records_version`.
- [x] **T2** — Service binding: `create_thread(session, user, *, proyecto="default")` validates and
      normalizes through `projects.agent_context` for a non-default project and persists the slug;
      `_thread_project_authorization` reads the column instead of `assistant_state.sdb.proyecto`.
- [x] **T3** — Single derivation point: `_run_agent_turn_session` derives the capability from the
      thread and forwards it to `run_assistant`, so `_project_slug` always sees the thread's project.
- [x] **T4** — Tool axis: `execute_tool` takes the bound project; `_read_memory`, `_search_memory` and
      `_write_memory` resolve the agent entity and filter by it; `_write_memory` re-validates the
      capability; both call sites (`app/chat/assistant/nodes.py:651`, `app/services/agent_chat.py:187`)
      pass it.
- [x] **T5** — Panel reachability: `POST /chat/threads` accepts an optional project slug and the thread
      serializer exposes `proyecto`.
- [x] **T6** — Spec: correct the stale Purpose sentence at `openspec/specs/memory/spec.md:5`.
- [x] **T7** — Verify: RED before each behavioural change, targeted suites, full suite, mutation check.

## Verification

- `uv run pytest tests/unit/test_memory_tool_axes.py tests/unit/test_assistant_tools.py tests/spec/test_memory_spec.py -o addopts=""`
- `uv run pytest tests/integration/test_migrations.py -o addopts=""`
- `uv run pytest tests/ -o addopts=""` (full suite; needs this worktree's test database)
- **Mutation check (the load-bearing evidence):** neuter the axis and the project-isolation test
  MUST go red. Two distinct bindings need pinning and they are pinned in different places: the
  isolation test calls `_read_memory`/`_write_memory` directly with an explicit `proyecto`, so the
  honest mutation is inside the tool handler (force the persisted namespace back to `WRITABLE_PROYECTO`
  in `_write_memory`), not at the turn's derivation point. The derivation point is pinned separately,
  by `test_agent_turn_derives_project_authorization_from_thread`.

## Acceptance criteria

1. A thread created with a project namespace stores it, and a thread created without one stores
   `default`.
2. A global memory written from a project-bound thread is persisted with
   `entity_id='agent:<slug>'` and `proyecto='<slug>'`, not `agent:default`.
3. The MEM-9 scenario is proven for the first time: a global memory written from a thread bound to
   project A is NOT readable from a thread bound to project B, and IS readable from another thread
   bound to project A.
4. An `own` read and search from a project-bound thread union that thread's panel axis with
   `agent:<slug>` only.
5. An unknown, inactive, or archived project is rejected at thread creation, and a project archived
   after binding causes the memory write to fail closed rather than persist.
6. The tool argument models still reject a model-supplied project, scope, or entity.
7. Migration 031 applies to a populated `internal_chat_threads` table, backfilling every existing row
   to `'default'`, and is idempotent under the runner.
8. `POST /chat/threads` without a body keeps working, and with a slug returns the thread carrying it.
9. The mutation check turns the project-isolation test red.
10. The full suite stays green.

## TDD note

Strict TDD is ON. Each behavioural task records an observed RED before the source change and a GREEN
after it, with the runner and the counts. The migration task has no behaviour to observe on its own,
so its evidence is the migration test plus criterion 7.

## Outcome

Delivered. Ten commits on the branch, plus this record as the closing commit.

| Commit | Subject |
|---|---|
| `cfabad58` | `docs(odd): record memory-per-project-thread` |
| `e5ee12a5` | `docs(odd): pin the SDB namespace authority for memory-per-project-thread` |
| `c5c0f041` | `feat(db): add the chat thread project namespace column` |
| `53fe2099` | `feat(memory): bind agent turns to the thread project` |
| `55022d2b` | `test(memory): pin the thread project binding and its fail-closed paths` |
| `77a00514` | `feat(memory): scope the agent memory axis to the thread project` |
| `7eb5684c` | `feat(memory): pass thread project to assistant tools` |
| `71a6d831` | `feat(panel): accept a project namespace when creating a chat thread` |
| `aba69386` | `test(memory): assert project filters on assistant memory queries` |
| `b80a8fda` | `docs(spec): record the per-thread project binding for agent memory` |

**Change.** Migration 031 adds `internal_chat_threads.proyecto` (`VARCHAR(100) NOT NULL DEFAULT
'default'`, no FK). `create_thread` validates a non-default slug through `projects.agent_context` and
persists it, auditing the namespace. `_thread_project_authorization` reads the column.
`_run_agent_turn_session` derives the capability from the thread and forwards it, so
`state["project_authorization"]` is the thread's binding for the whole turn. `execute_tool` takes the
project; `_read_memory`, `_search_memory` and `_write_memory` resolve `agent:<project>` per call and
filter both axes by it, and `_write_memory` re-validates the capability inside its own `try`, so an
archived project yields the degraded result the tool contract already requires rather than a raise.
`POST /chat/threads` accepts an optional project body and the serializer exposes `proyecto`.
`create_run_message`, `submit_message` and `_run_agent_turn_session` lost their `project_authorization`
parameter: no caller supplied a non-`None` value, and with a persisted binding a caller-supplied
namespace is a second source of truth, which is exactly how the divergence started.

**What the unit turned out to be, versus what the handoff predicted.** The handoff
(`handoff/memory-backlog-next`) directed the work to start with a spec amendment to MEM-9/AT-9. That
was wrong and was corrected before any code existed: MEM-9 (`memory/spec.md:157-160`), MEM-3
(`:51`, `:66`) and AT-9 (`assistant-tools/spec.md:63-65`) already carried the project-qualified
contract. The gap was implementation, and it was a live violation rather than a future risk. Only one
Purpose sentence was amended (`memory/spec.md:5`, with a `(Previously: ...)` note).

**Accepted deviations from this record's first draft.** (1) The base was first recorded as `0fe3eae7`;
main advanced to `9760a1e7` when the parallel vps-ops session merged PR #300 mid-session, and the
worktree was created from the newer commit. Corrected in place, with the file evidence that the delta
touched no `app/`, `openspec/` or `db/` path. (2) The T2/T3 tests went to a new
`tests/unit/test_agent_chat_thread_project.py` rather than `tests/spec/test_memory_spec.py`.
(3) The panel-API test went to `tests/integration/test_h4_chat.py` rather than
`tests/functional/test_api_memories.py`. (4) The mutation target was corrected — see Verification.

**TDD.** Strict TDD ON (`openspec/config.yaml`, `testing.strict_tdd: true`), runner `uv run pytest tests/`.

- T1 RED: **2 failed** after adding the `031` version expectation and the column assertions with no
  migration file; GREEN: **19 passed**.
- T2/T3 RED: **3 failed**; GREEN: **3 passed**.
- Corrective round: three more tests covering Acceptance criteria 1 (the default half) and 5
  (fail-closed at creation and after binding), plus the column-versus-`assistant_state` regression
  guard. That round added coverage for behaviour that already existed, so **no RED is claimed for it**;
  once relocated in the same file it reads 6 passed.

**Verification.**

- `uv run pytest tests/integration/test_migrations.py -o addopts=""` -> **19 passed**.
- `uv run pytest tests/spec/test_memory_spec.py -o addopts=""` -> **26 passed**.
- `uv run pytest tests/unit/test_memory_tool_axes.py tests/unit/test_assistant_tools.py -o addopts=""` -> **58 passed**.
- `uv run pytest tests/functional/ -o addopts=""` -> **219 passed**.
- `uv run pytest tests/ -o addopts=""` -> **1207 passed, 2 warnings in 153.14s** at the closing
  revision. `--collect-only` also reports **1207 tests collected**.
- Collection delta measured in this worktree against its own base: **1060 test functions at
  `9760a1e7`, 1068 at HEAD (+8), 0 removed** — one migration test, six unit tests, one API test. An
  earlier count in this session reported +7; that measurement used the pathspec `tests/*.py`, which
  misses a file, and the corrected one uses `git ls-files tests/`. Recorded because the wrong number
  was stated out loud before it was fixed.
- **Mutation check, verified.** Forcing the persisted namespace back to `memory.WRITABLE_PROYECTO`
  inside `_write_memory` (`app/chat/assistant/tools/registry.py`) makes
  `test_mem9_global_visibility_records_provenance_and_cross_thread_read` go RED at
  `tests/spec/test_memory_spec.py:808` with
  `AttributeError: 'NoneType' object has no attribute 'producer'` — the row landed in `default`, so
  `get_by_key(..., proyecto=project_a)` finds nothing. The file was restored with
  `git checkout -- app/chat/assistant/tools/registry.py` and the test re-ran green (1 passed). A test
  that stayed green there would prove nothing about the binding.

**Interruption, declared.** One full-suite invocation was interrupted by the 120s harness ceiling
during this unit. The re-run passed in 153.14s. `odd/tasks/pytest-timeout.md:10-19` records this
class of intermittent stall as undiagnosed and independent of the code under test.

**Lint: not run.** `ruff` is not installed and `pyproject.toml` configures no linter, so there is no
lint gate to satisfy.

**Review (native RDD).** Lineage `review-3614a64b02306afb`, risk `high`, 16 paths, 717 changed lines,
correction budget 200, four lenses (`review-risk`, `review-resilience`, `review-readability`,
`review-reliability`). The four-lens plan was selected because the migration test starts subprocesses
(`risk_reasons`: `process_boundary` / `shell_process` on `tests/integration/test_migrations.py`).
Result: **approved**, authority burned (`gentle-ai.review-acknowledged/v1`), **zero blocking findings**,
**two non-blocking advisories**:

| ID | Lens | Location | Claim |
|---|---|---|---|
| `R3-project-resolution-cleanup` | reliability | `app/services/agent_chat.py:638` | Project authorization is resolved before the turn's `try`/failure-handling block, so an archived or otherwise invalid bound project can raise out of the turn runner without marking the run or message failed. |
| `R4-project-auth-failure` | resilience | `app/services/agent_chat.py:632` | Same mechanism: the derivation precedes the turn's `try`/cleanup, so the turn can terminate without recording a failed result. |

The advisories are non-blocking by contract and are **not** re-run against this candidate. One
correction on their scope, from reading `run_agent_turn` (`app/services/agent_chat.py:775-806`): the
production entry point wraps `_run_agent_turn_session` in an `except Exception` that rolls back, sets
`message.status = "failed"`, merges `{"stage": "failed"}` into `assistant_state` and commits. So a
turn bound to an archived project does not vanish silently in production — the claim holds for
`_run_agent_turn_session` in isolation and for the `submit_message` wrapper, and what is genuinely
missing on the production path is that the failure is handled by the background runner's generic
handler instead of the turn's own error path, and no live push is published. Follow-up work for a new
candidate, deliberately not folded into this one.

**Graph nodes consulted.** `InternalChatThread`, `Memory`, `agent_chat.py`, `models.py`,
`tukulpan.py`, `registry.py`, `projects.py`, `list_for_entity()`, `visibility_target()`,
`agent_memory_entity()`, `thread_memory_entity()`, `create_thread`, `Exploration: Projects (proyecto
namespace and read-only browse UI)`; migration, chat-route and serializer communities. No directed
path resolved between `chat.py` and `serializers.py`.

**Remaining backlog.** Item 4 (query-less recall) stays open in `backlog/memory-cross-thread-followups`,
alongside the `R3-search-failure-coverage` advisory left by `odd/read-failure-truthfulness`. Two new
follow-ups: the `R3-project-resolution-cleanup` / `R4-project-auth-failure` pair above, and the web
entry point that slice 2 owes ("open a conversation in this project" from the project page), without
which a human still cannot bind a thread to a project from the UI.
