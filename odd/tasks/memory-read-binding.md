# ODD: bind panel memory reads to the trusted thread

**Work unit:** #7 of the Tukulpan/Engram series (reported defect carried over from WU#4)
**Source:** `odd/tasks/memory-axes.md` → "Explicitly out of scope" → *"a `panel` read may target `thread:{any id}` … gets its own work unit"*
**Worktree:** `../lumat-agent-odd-memory-read-binding` · branch `odd/memory-read-binding` · base `5a7297c3`
**Status:** completed

---

## Objective

Close the cross-thread read exposure in the assistant memory tools. Today a
`panel` `memory.read` / `memory.search` can target `thread:{any id}` because the
model supplies `entity_id` and the server only checks the `thread:` prefix. Bind
the panel read target to the trusted thread, server-side, the same way the write
path already binds it.

## Problem

The assistant's `execute()` already carries the trusted thread id and forwards it
to the dispatcher (`app/chat/assistant/nodes.py:480-514`), but the dispatcher
injects it into **only** `memory.write`
(`app/chat/assistant/tools/registry.py:412-420`). The read handlers receive
`(session, parsed)` and use the model's `entity_id` verbatim
(`registry.py:218-236`). The only guard is a prefix check
(`registry.py:80-81`), so `thread:999` is accepted while the session's trusted
thread is `thread:7`.

The write path is already safe: `visibility_target()` derives
`thread:{thread_id}` server-side (`app/services/tukulpan.py:105-114`). The reads
never got the same treatment. There is no legitimate feature that reads *another*
thread; the only consumer of a panel entity id is the recap instruction
(`app/chat/assistant/nodes.py:203-207`), which means "read the current thread".

## Decision (locked with the human)

**B — derive the panel read target server-side.** For `scope="panel"` the server
owns the target: `entity_id = thread:<trusted thread id>`. The model does not
supply it. A model-supplied `entity_id` on a panel read is **rejected**, not
silently ignored, because MEM-9 already fixed this exact pattern for writes with
the wording *"derive this target … rather than accepting it from the model."* A
silent ignore would hide model confusion and delete an existing cross-scope
validation; a rejection keeps the contract honest and fail-loud at a trust
boundary.

Rejected alternative — **A, validate-match**: keep the model-supplied `entity_id`
and only assert it equals `thread:{trusted}`. Smaller diff, but it leaves the
model holding the identity. That is precisely the pattern that produced the
WU#4 CRITICAL, and it re-introduces the "model copies the id wrong → read fails"
failure mode for no benefit.

## Authorized scope

The assistant read-tool contract (`memory.read`, `memory.search`), its dispatch
binding, the recap prompt line, the specs those contract rules live in, and the
tests that pin them.

## Explicitly out of scope

- The `memory.kpis` misnomer (WU#5) and the DSML leak in the responder (WU#6).
- The hard-coded `localhost:5432` in `tests/integration/test_db.py:203`
  (regression from PR #240). Known environmental failure; not absorbed here.
- `proyecto` authorization on reads. The tool schema forbids a model-supplied
  `proyecto` and the service default (`WRITABLE_PROYECTO`) applies; nothing in
  this unit widens or narrows that.
- The panel REST reads (`app/panel/api/routes/chat.py:186-203`) — they already
  derive `thread.id` server-side and need no change.
- The `customer` axis `delete()` / `set_mark()` by-ID paths.
- Widening `AUTONOMOUS_WRITE_ALLOWLIST`. It stays exactly one member.

## Constraints

- **Strict TDD is active** (`apply.tdd=true`, `test_command "pytest tests/"`).
  RED must be observed **at assertion level** before implementation — a
  collection `ImportError` is not RED.
- Technical artifacts in English. No AI attribution. Conventional commits.
- No new tool ⇒ the assistant tool whitelist count must not change, and
  `read_only` stays `True` for both read tools.
- Test DB: `eval "$(infra/test-db.sh env)"` (this worktree derives port `6303`).
  Never `docker compose down -v`.
- Known environmental failure, pre-existing and not ours:
  `tests/integration/test_db.py::test_audit_is_append_only_via_grants` hard-codes
  `localhost:5432` while every worktree derives its own port.

## Graph check

Graph queried from the main worktree (`graphify-out/graph.json`, built from
`5a7297c3` = this branch's base; the worktree carries the same tree).

- `graphify query "memory read entity_id scope panel thread isolation trusted thread"`
  → 514 nodes. God-ish nodes: `list_for_entity()` (`app/services/tukulpan.py:412`),
  `execute()` (`app/chat/assistant/nodes.py:480`),
  `test_execute_forwards_trusted_thread_to_memory_write()` (`tests/integration/test_assistant_harness_guardrails.py:265`),
  `_memory_plan()` (same file `:233`), `upsert()` (`tukulpan.py:151`),
  the MEM-3 spec node `"Panel thread and WhatsApp customer scopes never cross-read (MEM-3)."`.
- Communities in the blast radius: `tukulpan.py`, `nodes.py`, `registry.py`,
  `test_assistant_tools.py`, `test_memory_spec.py`, `test_assistant_harness_guardrails.py`.
- `GRAPH_REPORT.md` hub list confirms `registry.py` and `tukulpan.py` as
  navigation hubs; `nodes.py` is a listed hub.
- Refresh (`graphify . --update`) is deferred to session close, per the Graphify
  policy.

## Design

### The panel read target is derived, never an argument

| scope | `entity_id` supplied by the model | resolved target |
|---|---|---|
| `panel` | **forbidden** (rejected if present) | `thread:{trusted thread id}` |
| `customer` | required: `customer:{id}` or a legacy numeric id | as supplied, validated |
| `agent` | required: must equal `agent:{WRITABLE_PROYECTO}` | as supplied, validated |

`entity_id` becomes optional in the schema (`str | None = None`) and
conditionally required: required for `customer` and `agent`, forbidden for
`panel`. The read handlers resolve the panel target from the trusted thread that
the dispatcher already carries.

### Fail closed when there is no trusted thread

`app/services/agent_chat.py:187-192` calls `execute_tool()` without a
`trusted_thread_id`. A panel read on that path has no thread to bind to, so it
must be rejected rather than defaulted. The guard mirrors the existing
autonomous-write guard (`registry.py:364-365`): a positive `int` trusted thread
id is required for a panel read.

### One source for the thread entity format

`f"thread:{thread_id}"` is currently written in `visibility_target()`
(`tukulpan.py:112`) and would otherwise be duplicated in the read handler. A
`thread_memory_entity(thread_id)` helper next to `agent_memory_entity()` keeps
one source, and `visibility_target()` uses it.

### Trade-off check (Ponytail, two-sided)

If the rejection were softened to a silent ignore, what dies: the existing
cross-scope validation (`tests/integration/test_assistant_harness_compatibility.py:130-148`
rejects a `panel` read carrying a `customer:` entity) and the honest signal that
the model sent something meaningless. Cost accepted: `entity_id` is now a
conditional field, and the recap prompt line must stop telling the model to send
the identity. Both are small and are covered by tasks.

## Tasks

- [x] **T1 — `app/services/tukulpan.py`: `thread_memory_entity(thread_id)`.**
  New helper returning `f"thread:{thread_id}"`; `visibility_target()` uses it so
  the format has one source. Export it in the module's `__all__`.

- [x] **T2 — `app/chat/assistant/tools/registry.py`: read schema.**
  `_MemoryScopeArgs.entity_id` becomes `str | None = Field(default=None, max_length=100)`.
  The validator requires it for `customer` and `agent` (unchanged rules) and
  **rejects** a supplied `entity_id` for `panel` with a message stating the thread
  is derived server-side.

- [x] **T3 — `registry.py`: read handlers and dispatch.**
  `_read_memory` / `_search_memory` take `*, trusted_thread_id: int | None`. For
  `scope="panel"` they resolve `entity_id = memory.thread_memory_entity(trusted_thread_id)`
  and ignore the (already-forbidden) argument. `execute_tool` passes
  `trusted_thread_id` to both read tools. A panel read without a positive trusted
  thread id raises `ToolValidationError`, mirroring the autonomous-write guard.

- [x] **T4 — `app/chat/assistant/nodes.py`: recap prompt line.**
  The `History recap saved:` instruction currently tells the model to pull the
  recap "using the conversation identity above" (`nodes.py:203-207`). Replace it
  with a call that omits `entity_id` (`memory.read` with `scope=panel`), so the
  prompt matches the new contract.

- [x] **T5 — Specs.**
  `openspec/specs/assistant-tools/spec.md`: amend AT-8 so a panel read derives
  `thread:<thread id>` server-side and a model-supplied `entity_id` is rejected;
  keep AT-9's write rule intact. `openspec/specs/memory/spec.md`: land the MEM-3
  *Role isolation* scenario so it names the read-binding guarantee it already
  promises.

- [x] **T6 — Tests (RED first, assertion level).**
  A panel read with `entity_id="thread:999"` while the trusted thread is `7` is
  rejected (today it reads `thread:999`); a panel read with no `entity_id` reads
  `thread:7`; a panel read with no trusted thread id fails closed; `customer`
  and `agent` reads keep their existing validation; the `memory.read` /
  `memory.search` kwargs pinned in
  `tests/integration/test_assistant_harness_compatibility.py` are updated to the
  new binding (as a deliberate contract change, not a relaxed assertion); tool
  count and `read_only` flags unchanged.

## Acceptance criteria

1. A `panel` `memory.read` / `memory.search` can only ever resolve to
   `thread:{trusted thread id}`; no model-supplied value can change it.
2. A `panel` read that carries an `entity_id` is rejected.
3. A `panel` read with no positive trusted thread id is rejected (fail closed,
   including the SDB dispatch path that passes none).
4. `customer` and `agent` reads behave exactly as before.
5. The recap prompt no longer instructs the model to supply a panel entity id.
6. Specifications AT-8 and MEM-3 describe the derived read binding.
7. Tool whitelist count and `read_only` flags unchanged.
8. Full suite green except the known `test_db.py` hard-coded-port failure.

## Checks

- Targeted: `eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/unit/test_assistant_tools.py tests/integration/test_assistant_harness_compatibility.py tests/integration/test_assistant_harness_guardrails.py -q`
- Memory specs: `... tests/spec/test_memory_spec.py -q`
- Full suite: `eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/` — ~900
  tests, ~7 minutes. `pyproject.toml` already sets `addopts = "-q"`; do not add a
  second `-q`.
- No linter, typechecker, or pre-commit hook exists in this repo. The tests are
  the verification.

## Progress and evidence

_(appended as tasks complete — RED output, GREEN output, suite result, review lineage)_

## Next step

All tasks are implemented and verified; no next implementation step remains.

## Apply progress

### T1 — thread entity helper

- RED: `eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/unit/test_tukulpan_provenance.py::test_thread_memory_entity_is_derived_from_thread -q` → `AttributeError: module 'app.services.tukulpan' has no attribute 'thread_memory_entity'` (assertion-level failure).
- GREEN: `eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/unit/test_tukulpan_provenance.py::test_thread_memory_entity_is_derived_from_thread tests/unit/test_tukulpan_provenance.py::test_visibility_target_maps_declared_visibility -q` → `.. [100%]`.
- Graph nodes consulted: `agent_memory_entity()`, `visibility_target()`, `tukulpan.py`, `MemoryVisibility`; edge `visibility_target() <--contains-- tukulpan.py`.

### T2 — conditional read entity schema

- RED: `eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/unit/test_assistant_tools.py::test_memory_scope_entity_is_conditional_and_panel_entity_is_forbidden -q` → `ValidationError: MemoryArgs.entity_id Field required` for a panel read without `entity_id` (assertion-level failure).
- GREEN: same command → `. [100%]`.
- Graph nodes consulted: `_MemoryScopeArgs`, `registry.py`, `execute_tool()`; edge `_MemoryScopeArgs <--contains-- registry.py --contains--> execute_tool()`.

### T3 — trusted read dispatch binding

- RED: `eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/unit/test_assistant_tools.py::test_panel_memory_read_uses_trusted_thread_and_fails_closed tests/unit/test_assistant_tools.py::test_memory_search_is_scoped_and_bounds_content -q` → `FF`; assertions observed `entity_id: None` instead of `thread:7` for both read and search.
- GREEN: `eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/unit/test_assistant_tools.py::test_panel_memory_read_uses_trusted_thread_and_fails_closed tests/unit/test_assistant_tools.py::test_memory_search_is_scoped_and_bounds_content tests/unit/test_assistant_tools.py::test_memory_read_is_bounded_and_uses_memory_service -q` → `... [100%]`.
- Graph nodes consulted: `_read_memory()`, `_search_memory()`, `execute_tool()`, `ToolValidationError`; edge `execute_tool() <--contains-- registry.py --contains--> _read_memory()`.

### T4 — recap prompt contract

- RED: `eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/unit/test_assistant_planner.py::test_context_text_announces_saved_recap_after_rotation -q` → `F`; assertion expected `memory.read with scope=panel and no entity_id` but the prompt still said `using the conversation identity above`.
- GREEN: same command → `. [100%]`.
- Graph nodes consulted: `_context_text()`, `nodes.py`, `write_recap()`, `test_assistant_planner.py`; edge `_context_text() <--contains-- nodes.py`.

### T5 — specification contract

- RED: N/A — documentation-only contract amendments have no executable red phase; the existing `test_mem3_role_isolation` executable scenario was retained.
- GREEN: `eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/spec/test_memory_spec.py::test_mem3_role_isolation -q` → included in the passing focused run (`45 passed`).
- Graph nodes consulted: `AT-8 Scoped Memory Contract`, `AT-9 Autonomous Thread Memory Write`, `MEM-3 Explicit, Scoped Hybrid Search`, `Memory Specification`; edge `AT-8 --references--> assistant-tools Specification --references--> ... --references--> MEM-3`.

### T6 — regression and compatibility coverage

- RED: covered by the T3 assertion-level RED above: panel reads/searches passed `None` to the service instead of deriving `thread:7`; the compatibility contract was then extended to pin rejection of `thread:999` and forwarding of `thread:7`.
- GREEN: `eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/unit/test_assistant_tools.py tests/integration/test_assistant_harness_compatibility.py tests/integration/test_assistant_harness_guardrails.py tests/spec/test_memory_spec.py -q` → `84 passed`.
- Graph nodes consulted: `test_assistant_harness_compatibility.py`, `test_assistant_harness_guardrails.py`, `execute_tool()`, `registry.py`, `nodes.py`; edge `test_memory_read_rejects_cross_scope_entity_shapes() --calls--> execute_tool() <--calls-- execute() <--calls-- test_execute_forwards_trusted_thread_to_memory_write()`.

### Final verification

- Targeted command: `eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/unit/test_assistant_tools.py tests/integration/test_assistant_harness_compatibility.py tests/integration/test_assistant_harness_guardrails.py tests/spec/test_memory_spec.py -q` → `84 passed`.
- Full-suite command: `eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/` → `916 passed, 2 warnings in 441.41s (0:07:21)`.
- An earlier full-suite run exposed one contract assertion in `test_plan_llm_includes_whitelisted_tool_catalog_in_prompt`; it was updated to expect only `scope` as required and the optional `entity_id`, then the full suite passed. The documented hard-coded-port failure did not reproduce in this environment.
