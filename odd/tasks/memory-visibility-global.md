# ODD: memory-visibility-global

## Objective

Rename the `memory_visibility` enum value `project` to `global`, so the declared visibility
vocabulary stops colliding with the `proyecto` namespace axis.

## Problem

`visibility` is a pure mirror of `scope`, and the database already says so
(`db/migrations/026_memory_provenance.sql:13,20`):

```sql
CREATE TYPE memory_visibility AS ENUM ('thread', 'project');
CHECK ((visibility = 'project') = (scope = 'agent'))
```

The label `project` has **no** relationship to `proyecto`. It means "reachable from every thread",
which is genuinely `global` from the thread's point of view. The collision with `proyecto` is not
theoretical: `agent_memory_entity(proyecto)` builds `entity_id='agent:<project>'`, so `project`
appears on both sides of the same write — one as a visibility label, one as a namespace — and
backlog item 2 (per-project memory) is about to make `proyecto` a real, user-visible axis.

The misnomer got worse in `odd/memory-cross-thread`: `visibility=project` is now the *default*
write, so the wrong word is the one the model and the specs use most.

## Why

- Registered in Engram as `backlog/memory-cross-thread-followups` (obs #4614), item 3.
- Item 2 is blocked by this: it cannot introduce a real `proyecto` axis while `project` is already
  taken by an unrelated meaning. Renaming first leaves the axis clean.
- Human decision, recorded: the target label is `global` (not `cross_thread`, not `agent`).

## Scope

**In:**

- New migration `db/migrations/030_memory_visibility_global.sql`: `ALTER TYPE ... RENAME VALUE`
  plus drop/add of the coherence CHECK.
- `MemoryVisibility` (`app/models.py:150-152`), `visibility_target()` (`app/services/tukulpan.py:123`),
  `MemoryWriteArgs.visibility` (`app/chat/assistant/tools/registry.py:148`).
- Specs MEM-9 (`openspec/specs/memory/spec.md`) and AT-9 (`openspec/specs/assistant-tools/spec.md`).
- Every test that pins the label.

**Out:**

- `kb_visibility` (`db/migrations/027_kb_visibility.sql`, `KbVisibility` in `app/models.py:424-425`)
  is a DIFFERENT enum with a different meaning (`internal`/`customer`). Untouched.
- No data migration: `RENAME VALUE` is an in-place catalog update, it does not rewrite rows.
- No prompt or persona change: `rg` confirms neither mentions `visibility`.
- Item 2 (binding `proyecto` to a real axis) stays open.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-memory-visibility-global`
- Branch: `odd/memory-visibility-global`
- Base: `38a6bcc3`
- Files:
  - `odd/tasks/memory-visibility-global.md`
  - `db/migrations/030_memory_visibility_global.sql` (new)
  - `app/models.py`, `app/services/tukulpan.py`, `app/chat/assistant/tools/registry.py`
  - `openspec/specs/memory/spec.md`, `openspec/specs/assistant-tools/spec.md`
  - `tests/unit/test_memory_model.py`, `tests/unit/test_tukulpan_provenance.py`,
    `tests/unit/test_memory_tool_axes.py`, `tests/unit/test_assistant_tools.py`,
    `tests/spec/test_memory_spec.py`, `tests/functional/test_api_memories.py`,
    `tests/integration/test_assistant_harness_guardrails.py`, `tests/integration/test_migrations.py`

## Constraints

- **Strict TDD: ON** — source: `openspec/config.yaml` (`testing.strict_tdd: true`). Runner:
  `uv run pytest tests/`. Observe RED before the source change; never invent RED evidence.
- `026_memory_provenance.sql` is already applied everywhere and MUST NOT be edited. The rename is a
  new forward migration only.
- `visibility='thread'` and its default are unchanged; only the `agent`-scope label moves.
- The CHECK must stay exact: `(visibility='global') = (scope='agent')`.
- `pyproject.toml` already sets `addopts = "-q"`; use `-o addopts=""` when the count matters.
- One concern, `≤5` files per commit.

## Design decision

**D1 — `global` names the declared visibility, not the storage partition.** The model declares
"should this be reachable beyond this thread?" — the answer is `thread` or `global`. Where the row
is *stored* (`scope='agent'`, `entity_id='agent:<project>'`) is enforcement the server derives and
the model cannot supply. Item 2 keeps that partition; it does not add a third visibility value, so
`global` stays the honest word for the declaration even once a thread is bound to a project.
Trade-off accepted: after item 2, a `global` memory is reachable from every thread *of its project*,
not from every project. The alternative — `cross_thread` — is more literal but leaks the storage
axis into the vocabulary the model chooses from, which is the coupling this rename removes.

## Tasks

- [x] **T1** — RED: pin the new vocabulary in the tests before touching app code — enum labels,
      `MemoryWriteArgs`, `visibility_target()`, persisted value, coherence violation, and that the
      old `project` label is now rejected.
- [x] **T2** — Migration `030_memory_visibility_global.sql`: rename the enum value + swap the CHECK.
- [x] **T3** — GREEN: `MemoryVisibility.GLOBAL`, `visibility_target()`, `MemoryWriteArgs.visibility`.
- [x] **T4** — Amend MEM-9 and AT-9.
- [x] **T5** — Verify: targeted files, then the full suite; collection delta against the base.

## Verification

- `uv run pytest tests/integration/test_migrations.py -o addopts=""`
- `uv run pytest tests/unit/test_memory_model.py tests/unit/test_tukulpan_provenance.py tests/unit/test_memory_tool_axes.py tests/unit/test_assistant_tools.py -o addopts=""`
- `uv run pytest tests/spec/test_memory_spec.py tests/functional/test_api_memories.py tests/integration/test_assistant_harness_guardrails.py -o addopts=""`
- `uv run pytest tests/ -o addopts=""` (full suite)

## Acceptance criteria

1. `pg_enum` for `memory_visibility` is exactly `['thread', 'global']`.
2. The coherence CHECK rejects a `global` row with `scope='panel'` and accepts a `global` row with
   `scope='agent'`.
3. `MemoryVisibility` exposes `GLOBAL == "global"` and no `PROJECT` member.
4. `memory.write` accepts `visibility="global"`, defaults to it, and rejects `"project"`.
5. `visibility_target("global", ...)` returns the canonical `agent` axis; `"project"` raises.
6. Persisted agent writes read back `visibility == "global"`.
7. `visibility='thread'` behavior and every default are unchanged.
8. No `kb_visibility` surface changed.

## Outcome

Closed. Four work units plus this record.

| Commit | Subject |
|---|---|
| `12a6affc` | `refactor(memory): rename the visibility value project to global` |
| `787c1586` | `test(memory): align the visibility unit and spec tests with the global label` |
| `27e59bca` | `test(memory): align the migration and API surface tests with global` |
| `dd5b8666` | `docs(specs): rename the declared memory visibility to global` |

**Change.** `memory_visibility` is `('thread', 'global')`; the coherence CHECK is
`(visibility='global') = (scope='agent')`; `MemoryVisibility.GLOBAL`,
`visibility_target()`, and the model-facing `MemoryWriteArgs.visibility` literal all speak
`global`. `app/chat/assistant/tools/registry.py`, `app/models.py` and `app/services/tukulpan.py`
carry the code change (4 lines); `db/migrations/030_memory_visibility_global.sql` is the whole
schema change and touches no row. `kb_visibility` and every `visibility='thread'` default are
unchanged.

**TDD.** RED observed before the source change, on the unmodified app code
(`12a6affc` had not landed yet):

- `uv run pytest tests/unit/test_memory_model.py tests/unit/test_tukulpan_provenance.py
  tests/unit/test_memory_tool_axes.py tests/unit/test_assistant_tools.py
  tests/spec/test_memory_spec.py tests/functional/test_api_memories.py
  tests/integration/test_assistant_harness_guardrails.py tests/integration/test_migrations.py
  -o addopts=""` -> **15 failed, 132 passed**. Representative failure:
  `AssertionError: assert ['thread', 'project'] == ['thread', 'global']`
  (`tests/integration/test_migrations.py:358`).

Then GREEN, same selection, after the migration and the three source edits -> **147 passed**. The
migration applied through the normal runner, so the RED includes the real database state.

**Verification.**

- `uv run pytest tests/ -o addopts=""` -> **1156 passed, 0 failed** (exit 0, 173.53s) against the
  worktree test database (port 6006).
- Collection delta measured with `--collect-only -o addopts=""`: **1155 before, 1156 after (+1)**,
  the one new test pinning that the retired `project` label is rejected. The baseline is this
  worktree's own, not a borrowed number.
- CI parity: `.github/workflows/tests.yml` runs `uv sync --frozen` + `uv run pytest tests/`; no
  dependency or lockfile change here.

**Review (native RDD).** Lineage `review-243fe5dc2e6eebcd`, one lens (`review-reliability`, order 0),
`medium` risk, 14 files / 133 lines. Consent was relayed to the human and `granted`. **Approved with
zero findings**, authority burned on `gentle-ai.review-acknowledged/v1`
(`consumed_revision sha256:7a348628…`).

**Notes.**

- The handoff's test surface was incomplete: `tests/functional/test_api_memories.py:611` also used
  `MemoryVisibility.PROJECT`. Found by `rg`, not by trusting the list.
- AT-9 claimed `memory.write` "defaults to `thread`". That was already false before this change —
  MEM-9, the code and the tests all default to the agent axis. Corrected to `global` in the same
  sentence this rename had to touch anyway; recorded here because it is a pre-existing spec error,
  not a rename side effect.
- The untracked inventory (`.opencode/tools/package-lock.json`, this task doc) needed the
  provider-bound selection JSON with `untracked_scope: exclude`; it is mutually exclusive with the
  legacy `--untracked-scope` flag.
- The OpenCode transport is `opencode_provider_injected`; `capture-result --materialize` is
  unavailable for it and the reviewer result is collected through the live host Task.
- This doc was committed after the review, matching `odd/memory-own-read-limit`: the record carries
  the review outcome, so it cannot be part of the frozen candidate.

**Remaining backlog.** Per-project memory (item 2) and query-less recall (item 4) stay open in
`backlog/memory-cross-thread-followups`. Item 2 is now unblocked on the vocabulary side: `project`
no longer means two different things.
