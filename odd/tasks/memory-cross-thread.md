# ODD: memory-cross-thread

## Objective

Make the assistant's own memory cross-thread by default. A durable write from one panel thread
becomes reachable from every other thread, and a read or search reaches it without the model having
to name a scope. Amend the three normative requirements that currently mandate the opposite.

## Problem

The panel agent's memory is effectively thread-local, and the user's own tests prove it:

- Thread 1 wrote `agent:test-memoria` with the keyword `zapato`. The write used the schema default
  `visibility="thread"`, so the row landed at `scope='panel', entity_id='thread:159'`.
- Thread 2 searched for `zapato` and got zero results.

Two independent locks produce that outcome:

1. **The write default.** `MemoryWriteArgs.visibility` defaults to `"thread"`
   (`app/chat/assistant/tools/registry.py:143`), so any write that does not declare `visibility`
   stays episodic.
2. **The read path.** `memory.read` and `memory.search` require the model to pick `scope` from a
   discriminated union of `panel | customer | agent`
   (`app/chat/assistant/tools/registry.py:119-126`). A `panel` read is rebound server-side to
   `thread:<trusted thread id>`, so it can only ever see the current thread.

Nothing writes to the agent axis by default, and the read path never looks there. The cross-thread
capability itself is already specified and already implemented — it is simply unreachable in
practice.

## Why — current state (verified, not inferred)

- `visibility_target()` maps `project` to `("agent", f"agent:{proyecto}")` and `thread` to
  `("panel", f"thread:{thread_id}")` — `app/services/tukulpan.py:116-125`.
- `WRITABLE_PROYECTO = "default"`, so the global bucket is `agent:default` —
  `app/services/tukulpan.py:58`, `agent_memory_entity()` at `:101-108`.
- `_write_memory()` derives scope and entity from the declared visibility and never accepts them
  from the model — `app/chat/assistant/tools/registry.py:280-304`.
- `_read_memory()` and `_search_memory()` rebind the panel entity server-side, so a model-supplied
  `entity_id` cannot escape the current thread — `:247-277`.
- `DECAYING_TYPES = frozenset({MemoryType.SUMMARY, MemoryType.SESSION})` and
  `MEMORY_DECAY_DAYS = 30` — `app/services/tukulpan.py:60-61`. `memory.write` only accepts
  `decision | discovery | pattern | preference`, so **no agent-writable memory ever receives a
  `review_after`**.
- The spec already requires cross-thread readability — MEM-9
  `Scenario: Project visibility across threads`, `openspec/specs/memory/spec.md:172-175`.
- The spec currently requires the two behaviours being changed — MEM-9
  `Scenario: Thread default remains episodic` (`:177-180`) and MEM-10 "All other memory types MUST
  retain `review_after = NULL`" (`:182-195`).
- MEM-3 `Scenario: Role isolation` (`:63-66`) requires panel reads to return only the current
  thread's memories, which is why the read path cannot reach the agent axis today.

## Scope

**In:**

- `visibility` defaults to `project` on `memory.write`, so a durable write reaches the agent axis.
- `tipo` becomes required on `memory.write` (the `"discovery"` default is removed), so no write is
  classified by omission.
- `discovery` joins `DECAYING_TYPES`, so situational rows are surfaced as `stale` after 30 days.
- `memory.read` and `memory.search` collapse the model-facing scope to `own` (the default: the
  current thread **unioned with** the agent axis) and `customer` (explicit, client-gated). The
  model no longer names `panel` or `agent`.
- Amend MEM-3, MEM-9, and MEM-10; update the plan prompt and the persona.

**Out:**

- `memory.write` continues to accept only `decision | discovery | pattern | preference`; the other
  four `MemoryType` values stay unreachable from the tool.
- The `proyecto` axis stays hardcoded to `"default"`. Per-project memory is a separate unit; see
  the backlog note below.
- Renaming `visibility=project` to `visibility=global` is **not** in this unit. It is a persisted
  Postgres enum plus a check constraint, and it is registered as backlog.
- Query-less recall (a `mem_context`-style digest) is **not** in this unit. `query` stays required
  on `memory.search`. Registered as backlog.
- Panel context assembly stays pull-only. This unit does not reintroduce any push, so MEM-3
  `Scenario: Explicit search only` and `Scenario: Broad recall is not implicit` are untouched.
- The WhatsApp customer memory path is untouched.
- No `scope='all'` union across customer memory. Customer rows stay client-gated and reachable only
  by naming the customer.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-memory-cross-thread`
- Branch: `odd/memory-cross-thread`
- Base: `f031721b`
- Files: `odd/tasks/memory-cross-thread.md`, `app/chat/assistant/tools/registry.py`,
  `app/services/tukulpan.py`, `agent/prompts/assistant_plan.md`, `agent/personas/assistant.md`,
  `openspec/specs/memory/spec.md`, `tests/unit/test_memory_tool_axes.py`,
  `tests/spec/test_memory_spec.py`, `tests/unit/test_memory_model.py`

## Constraints

- **Strict TDD: ON** — source: `openspec/config.yaml` (`testing.strict_tdd: true`). Runner:
  `uv run pytest tests/`. Observe RED before the source change; never invent RED evidence.
- Integration commands require `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat`.
- **The server keeps deriving the target.** `_write_memory()` must not start accepting `scope` or
  `entity_id`. Collapsing the read scope is a schema change, not a widening of model authority.
- **Thread isolation must survive.** A `panel` row written by thread A must remain invisible to
  thread B. The union adds the agent axis; it does not expose other threads' episodic rows.
- **Customer memory stays gated.** `customer` remains an explicit scope requiring a matching
  entity id.
- `agent:` remains the required `topic_key` namespace.
- Two work units, one concern each, `≤5` files per commit.

## Design decisions

**D1 — Collapse the model-facing scope to `own | customer`.** The agent should not be choosing
between `panel` and `agent` at all: that is an implementation axis, not a user intent. This follows
the principle already stated in the codebase that the server derives the target rather than
accepting it from the model (`app/services/tukulpan.py:102-107`, `registry.py:280-304`). Under
`own`, the server derives `thread:<trusted thread id>` ∪ `agent:<proyecto>`. Keeping `panel` and
`agent` as model-selectable values is what made the reported bug structurally possible.

**D2 — `own` is the default.** An omitted `scope` resolves to `own`. The union is a superset of the
old `panel` behaviour, so no caller loses reach.

**D3 — `tipo` required, `discovery` decaying.** With `visibility` defaulting to `project`, an
omitted `tipo` would silently place an unclassified row in the shared axis. Requiring `tipo`
removes classification by omission, and decaying `discovery` gives situational rows a visible
staleness signal.

**D4 — Decay stays a signal, never a deletion.** `_review_after()` and `_is_stale()` already exist
and `hybrid_search()` already returns `stale`. Adding `discovery` reuses that path; it does not
introduce a sweeper.

## Tasks

- [x] **T1** — RED: `tests/unit/test_memory_tool_axes.py` — `MemoryWriteArgs` rejects a payload
      without `tipo`, and defaults `visibility` to `"project"`.
- [x] **T2** — RED: `tests/spec/test_memory_spec.py` — a `DISCOVERY` write receives a `review_after`
      approximately 30 days out; `DECISION`/`PATTERN`/`PREFERENCE` stay `NULL`.
- [x] **T3** — GREEN: `MemoryWriteArgs.tipo` required, `visibility` default `"project"`
      (`app/chat/assistant/tools/registry.py:137-144`).
- [x] **T4** — GREEN: `DECAYING_TYPES` includes `MemoryType.DISCOVERY`
      (`app/services/tukulpan.py:60-61`).
- [x] **T5** — Amend MEM-9 and MEM-10 in `openspec/specs/memory/spec.md`.
- [x] **WU1 commit** — write default, required type, discovery decay.
- [x] **T6** — RED: `tests/unit/test_memory_tool_axes.py` — the advertised read/search variants are
      `own` and `customer`; an omitted `scope` resolves to `own`; `customer` still requires a
      matching entity id; `panel` and `agent` are rejected.
- [x] **T7** — RED: `tests/spec/test_memory_spec.py` — an `own` read returns the current thread's
      rows unioned with the agent axis, and a thread A `panel` row stays invisible to thread B.
- [x] **T8** — GREEN: collapse the read/search scope schemas and add the union handler
      (`app/chat/assistant/tools/registry.py:77-134`, `:247-277`).
- [x] **T9** — GREEN: rewrite the memory-axis line in `agent/prompts/assistant_plan.md:7` and the
      persona memory sentence in `agent/personas/assistant.md:1`.
- [x] **T10** — Amend MEM-3 `Scenario: Role isolation` in `openspec/specs/memory/spec.md:63-66`.
- [x] **WU2 commit** — cross-thread read path.

## Verification

- `uv run pytest tests/unit/test_memory_tool_axes.py tests/unit/test_memory_model.py`
- `uv run pytest tests/spec/test_memory_spec.py`
- `uv run pytest tests/` (full suite)
- Manual: write a memory in one panel thread with the default visibility, then search for its keyword
  from a second thread and confirm it returns with `visibility='project'` provenance.

## Acceptance criteria

1. A write that omits `visibility` persists with `visibility='project'`, `scope='agent'`, and
   `entity_id='agent:default'`.
2. A write that omits `tipo` is rejected before persistence.
3. A `DISCOVERY` write receives a `review_after` approximately 30 days out; `DECISION`, `PATTERN`,
   and `PREFERENCE` keep `review_after = NULL`.
4. A read or search from thread B returns a project-visible memory written from thread A, without
   the model naming any scope.
5. A `panel` row written by thread A is still invisible to thread B.
6. Customer memory remains reachable only by naming the customer.
7. No memory row is injected into panel context by any code path.

## Backlog (registered in Engram, `backlog/memory-cross-thread-followups`)

- **Per-project memory.** `proyecto` stays `"default"`. Unblocking it needs a project binding on
  `InternalChatThread` (`app/models.py:797-809`, no such column today) and un-pinning
  `_AGENT_MEMORY_ENTITY` (`registry.py:32-33`). The design already anticipates the widening
  (`app/services/tukulpan.py:102-107`) and `_guard_writable_project()` already gates non-default
  writes (`:128-138`). No data migration needed: `proyecto` is already in the unique key.
- **Rename `visibility=project` to `visibility=global`.** Persisted Postgres enum plus the
  `memories_visibility_scope_coherence` check constraint (`db/migrations/026_memory_provenance.sql`).
- **Query-less recall.** `memory.search` requires `query`; there is no `mem_context`-style digest
  for "what do you know about me".

## Outcome

Closed. All ten tasks completed; both work units landed as four commits on `odd/memory-cross-thread`.

| Commit | Subject |
|---|---|
| `261ac0b5` | `feat(memory): default writes to project visibility` |
| `db273974` | `feat(memory): union own reads across threads` |
| `2d704fe3` | `test(memory): align stale tool tests with the own-scope contract` |
| `f63ecb29` | `test(memory): align stale integration harness tests with the own-scope contract` |

**Verification.** `uv run pytest tests/` -> **1154 passed, 0 failed** (exit 0, 133s), against the
worktree test database. 11 files changed, 235 insertions, 102 deletions.

Note for future runs: `pyproject.toml` already sets `addopts = "-q"`, so passing another `-q`
makes it `-qq` and suppresses the final summary line. The exit code remains authoritative; use
`-o addopts=""` when the count itself matters.

**Review (native RDD).** Lineage `review-523bea45a91c6152`, one consolidated lens
(`review-reliability`, order 0), `medium` risk, 11 files / 337 lines, correction budget 169.
Consent relayed to the human and `granted`. **Approved**, authority burned on
`gentle-ai.review-acknowledged/v1`.

**Advisory finding (non-blocking, registered as backlog).** `R3-own-read-limit` —
`_read_memory` concatenates thread rows before agent rows and applies `[:limit]` afterwards, so a
thread already holding at least `limit` rows (default 10) with no `topic` filter can hide the whole
project axis. `_search_memory` does not share the defect because it orders by score across both
axes. The review contract forbids re-running review for an advisory finding, so a fix is a new
candidate; it is recorded in `backlog/memory-cross-thread-followups` alongside per-project memory
and the `visibility=project` -> `visibility=global` rename.

**Scope notes.** The two stale-test passes were not planned tasks: changing the model-facing
contract broke 15 tests across four files that pinned `panel | agent` and the optional `tipo`. Each
was rewritten to assert the new contract at the same strictness, and every guard they protected —
server-derived write target, fail-closed behaviour without a trusted thread, the 2000-character
search bound, DB idempotency on the unique key — was preserved.
