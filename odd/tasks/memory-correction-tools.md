# ODD: memory-correction-tools

**Branch**: `odd/memory-correction-tools`
**Worktree**: `../lumat-agent-odd-memory-correction-tools`
**Base**: `d4b58554` (= `main` at branch time)
**Status**: in progress

## Objective

Give the panel assistant an explicit way to correct a memory it wrote itself:

1. **`memory.update`** — fix the title, content or kind of one agent-authored memory, addressed by `id`.
2. **`memory.delete`** — remove one agent-authored memory, addressed by `id`, so a wrong `topic_key` stops
   being permanent.

Both are autonomous (no approval step), under the same bounded-autonomy contract that `memory.write`
already established.

## Problem

The agent writes memory but cannot repair it. Three measured holes.

### Hole 1 — modification is implicit and unsteered

`memory.write` is the only write tool (`app/chat/assistant/tools/registry.py:402`). Modification happens
only as a side effect of the composite-key upsert: `_upsert_resolved()`
(`app/services/tukulpan.py:231-238`) looks the row up by
`(proyecto, scope, entity_id, topic_key)` and refreshes content plus embedding when it matches.

Nothing tells the model that. The tool description is `"Write memory; global across threads by default"`
and `_write_memory` (`registry.py:339`) returns `{"written": True, "id": ..., "topic_key": ...}` with no
`created`/`updated` discriminator. If the model corrects by inventing a new `topic_key`, the write lands
as a **new row**: the wrong memory survives next to the right one. The second lookup by
`normalized_hash` (`tukulpan.py:241-248`) only folds identical content, so corrected text never folds.

### Hole 2 — a bad `topic_key` is irreparable

There is no delete and no rename reachable by the agent. `MemoryWriteArgs.topic_key` carries
`pattern=r"^agent:"` (`registry.py:144`), so the agent cannot touch a system-authored row either. A key
mistake stays in the store forever, and `memory.read`/`memory.search` keep surfacing it.

### Hole 3 — the raw delete primitive has no ownership guard

`tukulpan.delete(session, memory_id)` (`app/services/tukulpan.py:578-585`) deletes **any** row by id and
validates nothing. The only guard today is `_ficha_memory_or_404` on the customer route
(`app/panel/api/routes/clients.py:76`, used at `:363`). Exposing a model-supplied `id` without a
server-side ownership check means one hallucinated integer can delete a customer memory or a system
recap. This is the security core of the unit.

## Scope

### In scope

| File | Change |
|---|---|
| `app/services/tukulpan.py` | `update(session, memory_id, *, titulo=None, contenido=None, tipo=None)`: in-place field update, re-embed only when `contenido` changes, raise `ValueError` when absent. Export it. |
| `app/chat/assistant/tools/registry.py` | `MemoryUpdateArgs`, `MemoryDeleteArgs`, `_owned_agent_memory_or_raise`, `_update_memory`, `_delete_memory`, two `ToolDefinition` entries, extend `AUTONOMOUS_WRITE_ALLOWLIST`, route both through the trusted-thread branch of `execute_tool()` |
| `agent/registry.yaml` | `memory.update` and `memory.delete` added to `assistant.tools_whitelist` (19 -> 21) |
| `agent/personas/assistant.md` | the autonomy clause currently names only `memory.write`; it must name all three |
| `openspec/specs/assistant-tools/spec.md` | new requirement **AT-11** (AT-1..AT-10 are taken) |
| `tests/unit/test_assistant_tools.py` | args validation, the ownership matrix, in-place update, delete |
| `tests/integration/test_assistant_harness_guardrails.py` | node-level autonomy for both new tools, DB-backed execution, and the stale `19 tools` comment |
| `odd/tasks/memory-correction-tools.md` | this document |

### Out of scope

- **`topic_key` in `memory.update`.** The only reason to change a key is to repair a bad one, and
  `delete` + `write` already covers that. Accepting `topic_key` would add a collision path against
  `UNIQUE(proyecto, scope, entity_id, topic_key)` for zero new capability. Rejected deliberately.
- **Human surface for agent memories.** The panel CRUD stays customer-scoped
  (`clients/{id}/memories`). Exposing `scope="agent"`/`"panel"` rows in the panel is a separate product
  decision.
- **Approval flow for these tools.** They are autonomous by design, consistent with `memory.write`.
- **Soft-delete or archive.** `tukulpan.delete` is a hard delete and that is the precedent the human
  route already uses (`clients.py:363`). `set_mark(status=ARCHIVED)` exists but a correction the human
  asked for should actually remove the row.
- **`memory.list`.** Not needed: `memory.read` with `scope="own"` and `memory.search` both return `id`
  and `topic_key` (`registry.py:250-274`, and `hybrid_search` returns `id`/`topic_key` at
  `tukulpan.py:683-690`), so the model can already find the id it needs.

## Contract

### `MemoryUpdateArgs` (write, autonomous)

```python
model_config = ConfigDict(extra="forbid")
id: int = Field(gt=0)
titulo: str | None = Field(default=None, min_length=1, max_length=200)
contenido: str | None = Field(default=None, min_length=1, max_length=2000)
tipo: Literal["decision", "discovery", "pattern", "preference"] | None = None
```

- A `model_validator(mode="after")` MUST reject a patch where all three are `None`: an empty patch is a
  model error, not a no-op.
- No `scope`, no `entity_id`, no `topic_key`. Target comes from `id` plus the server-side guard.

### `MemoryDeleteArgs` (write, autonomous)

```python
model_config = ConfigDict(extra="forbid")
id: int = Field(gt=0)
```

### The ownership guard — `_owned_agent_memory_or_raise`

Shared by both handlers. Given the row for `id`, all of the following MUST hold, else the handler
**raises `ToolValidationError`** (a deterministic rejection, never a degraded result):

1. `row.proyecto == proyecto`
2. `row.producer is MemoryProducer.AGENT` — this is the real boundary; recaps, milestones and decisions
   are written with `producer=SYSTEM` (`tukulpan.py:365-415`, `write_recap`) and customer memories with
   other producers.
3. `row.topic_key.startswith("agent:")` — consistent with the write-side namespace rule of AT-9.
4. `(row.scope, row.entity_id)` is one of the two axes `memory.write` can produce:
   - `("panel", f"thread:{trusted_thread_id}")`
   - `("agent", memory.agent_memory_entity(proyecto))`

**Why raise and not degrade.** AT-7 (Write Failure Truthfulness) governs *persistence* failures. A
missing row or a row the agent does not own is an authorization rejection: the graph must report
`failed`, not a soft message the model can retry against a different id. Only embedding or flush
failures take the degraded path, matching `_write_memory`.

### The autonomy boundary

```
AUTONOMOUS_WRITE_ALLOWLIST = frozenset({"memory.write", "memory.update", "memory.delete"})
```

The existing generic precondition in `execute_tool()` (`registry.py:442`) already requires a positive
real `int` `trusted_thread_id` for **every** member of the allowlist, and `_is_autonomous_write()`
(`nodes.py:530`) is the single shared predicate used by both `guardrails()` and `execute()`. Neither
needs a per-name special case; both new tools inherit the boundary.

The chain probe of the DB (see "Production evidence") confirms the model can obtain the `id` from
`memory.read`, so the guard's target is discoverable without a new tool.

## Why this shape

- **`id` is the only new input.** Everything else is derived server-side, so the model cannot express a
  target the policy forbids. Same reasoning that made `memory.write` take no `scope`/`entity_id`.
- **`update` is in-place, not a re-upsert.** Re-using `upsert` for a `topic_key` change is what forces
  the collision path; an in-place field update has none.
- **Re-embed only when `contenido` changes.** A title-only or kind-only correction must not pay for an
  embedding call, and must not silently change retrieval behaviour.
- **The guard lives in the tool layer**, where the trusted-thread identity is available, exactly like the
  existing trusted-thread routing in `execute_tool()`.

## Tasks

- [x] **T1 — RED.** Write the failing tests first: args validation (empty patch, unknown field,
  `topic_key`/`scope`/`entity_id` rejected), the ownership matrix (own thread row accepted, own agent row
  accepted, another thread's row rejected, customer row rejected, system/recap row rejected, foreign
  `proyecto` rejected), in-place update with re-embed, delete, allowlist membership, and node-level
  autonomy for both names with and without a trusted thread.
  *Check:* the new tests fail on the base for the right reason (unknown tool / missing behaviour), and
  the RED output is recorded verbatim. **See the RED limitation under "Verification evidence".**
- [x] **T2 — GREEN.** `tukulpan.update()`, the two args models, the guard, the two handlers, the
  registry entries, the allowlist extension, the `execute_tool()` routing.
  *Check:* the RED tests pass; `memory.write` behaviour is unchanged.
- [x] **T3 — Persona and whitelist.** `agent/personas/assistant.md` names all three autonomous tools;
  `agent/registry.yaml` carries both new names.
  *Check:* the harness assertion that every whitelisted tool name appears in the prompt passes.
- [x] **T4 — Spec.** `AT-11` in `openspec/specs/assistant-tools/spec.md`, in the same
  `### Requirement: AT-N — Title` + `#### Scenario:` GIVEN/WHEN/THEN shape, RFC 2119 keywords.
  *Check:* scenarios cover the ownership guard, the rejection of a non-owned row, the empty patch, and
  that every other write stays approval-gated.
- [x] **T5 — Full suite.** Targeted suites green, then the whole suite green.
  *Check:* the full command below, with its real pass count recorded. **`1290 passed, 2 warnings`.**

## Constraints

- **Strict TDD** (`openspec/config.yaml:38`). Observed RED before implementation, then GREEN.
  Runner: `uv run pytest tests/`.
- **One concern per commit**, work-unit commits on `odd/memory-correction-tools`. Conventional commits.
  No `Co-Authored-By` and no AI attribution.
- **Do not widen autonomy beyond these three names.** The allowlist has exactly three members and the
  unit that adds the two must not weaken the approval requirement for anything else.
- **English artifacts**: code, tests, spec, persona, this document.
- Ponytail applies after each task's code is written: the same authorized behaviour in fewer lines wins.
  It never removes authorized behaviour and never picks a pattern or a dependency.

## Checks

- `uv run pytest tests/unit/test_assistant_tools.py tests/unit/test_agent_registry.py` — focused contract.
- `uv run pytest tests/integration/test_assistant_harness_guardrails.py tests/functional/test_api_assistant_capabilities.py`
- Full suite: two steps, because this worktree derives its own DB port and the port is not `5432`:
  ```
  cp ../lumat-agent/infra/.env infra/.env     # test-db.sh reads the db-test superuser password
  bash infra/test-db.sh up                    # derived port + compose project for this worktree
  eval "$(bash infra/test-db.sh env)" && uv run pytest tests/    # exports DATABASE_URL + TEST_ADMIN_DB_URL
  ```
  ~2 minutes; pass an explicit long timeout to the shell. Without the derived URLs the suite errors
  (not fails) on connection: an environment gap, not a code bug.
- The repo has no linter, typechecker, pre-commit or hooks. The tests are the verification.

## Acceptance criteria

1. The agent can change the title, content or kind of a memory it authored, by `id`, without approval.
2. The agent can delete a memory it authored, by `id`, without approval.
3. No other write tool gained autonomy, and the SDB path still fails closed.
4. A row that is not agent-authored, or not on the agent's two axes, or in another project, is rejected
   and is not mutated.
5. `memory.write` behaves exactly as before.
6. The canonical spec carries the contract as AT-11, and the persona no longer under-describes the
   autonomy boundary.
7. Full suite green.

## Production evidence

The trigger is real usage, read from the running panel DB (`infra-db-1`, `lumat`) on 2026-09-22. Threads
1-5, all authored by user `1`:

| Thread | Turn | Observed |
|---|---|---|
| 2 | `id=6`, `id=10` | Two `memory.write` calls executed autonomously and returned `written: true` with `id` and `topic_key` |
| 3 | `id=12` | `memory.read` executed and returned a table of the three agent rows with `id`, `topic_key`, `visibility`, `producer` |
| 2 | `id=8` | The agent could **not** confirm a keyword was included in a memory it had just written — `_write_memory`'s payload carries no echo of the stored content |

The chain is what the unit depends on: `memory.read` returns `id`, `memory.write` returns `id`, and
nothing can act on that `id` afterwards. That last gap is the unit.

## Verification evidence

Environment first: this worktree had no `infra/.env`, so `infra/test-db.sh` refused to derive anything
and the delegated writer's full-suite run errored on connection (`2 failed, 396 passed, 892 errors` — the
892 errors were `db-test` connection failures on a port that was never up, not code failures). Resolved
by following the script's own instruction: `cp ../lumat-agent/infra/.env infra/.env`, then
`bash infra/test-db.sh up`, which derived port **5736** and compose project
`lumat-test-lumat-agent-odd-memory-correction-tools`.

- **Focused (delegated writer):**
  `uv run pytest tests/unit/test_assistant_tools.py tests/unit/test_agent_registry.py` -> `68 passed in 0.60s`.
- **Full suite (orchestrator, after the correction):** `1290 passed, 2 warnings in 119.75s`.
  Both warnings are pre-existing at the base (never-awaited `_publish_all`; the fastembed mean-pooling
  notice at `app/services/kb.py:132`).
- The registry-derived assertions (`tests/unit/test_agent_registry.py`,
  `tests/functional/test_api_assistant_capabilities.py`) needed **no** edit: both derive their sets from
  `TOOL_REGISTRY`, so the 19 -> 21 change propagated by construction.
- The DB-backed integration tests genuinely ran (not skipped) and cover both new tools end to end:
  `test_execute_forwards_trusted_thread_to_memory_correction` inserts an agent row, dispatches through
  `execute()`, and asserts the row was updated in place or is gone.

### RED limitation (declared, not hidden)

The observed RED was **import-level**, not behavioral:

```
ImportError: cannot import name 'MemoryDeleteArgs'
```

For a brand-new public API that is the honest floor — the test module cannot execute at all before the
symbols exist. It is **not** the behavioral RED this project's strict-TDD convention asks for. The
ownership-matrix tests are written so they *would* fail behaviorally against a guard that accepted a
non-owned row, but that state could only be observed after the symbols existed. No behavioral RED is
claimed here because none was observed.

### Corrections applied during the unit

1. **Persona regression, caught by the full suite only.** `agent/personas/assistant.md` was rewritten to
   name the three autonomous tools, which dropped the exact phrase `already authorized and runs without
   asking` pinned by the pre-existing `tests/unit/test_assistant_config.py:28`. The scoped correction
   keeps the widening **and** the pinned phrase instead of editing the pre-existing contract test:

   > ... except `memory.write`, `memory.update`, or `memory.delete` on this panel thread. **Each is
   > already authorized and runs without asking**, because it only touches the assistant's own
   > `agent:`-namespaced memories on either the current thread axis or the project axis.

   Re-run after the correction: full suite green. Same lesson the sibling unit `assistant-grounding-gate`
   recorded — a green scoped subset is not evidence that the branch is green, and here the assertion lived
   in a suite the writer never ran.

## Progress

- 2026-09-22 — reconnaissance complete. Three holes named, three design rejections recorded.
- 2026-09-22 — worktree created with explicit human consent: `../lumat-agent-odd-memory-correction-tools`,
  branch `odd/memory-correction-tools`, base `d4b58554`.
- 2026-09-22 — T1 RED recorded: the new args import failed because `MemoryDeleteArgs` did not exist, and
  the integration parametrization initially lacked its `tool` argument; the database-backed suite was also
  blocked by the absent worktree `infra/.env` and unavailable test database on port 5736.
- 2026-09-22 — T2 GREEN implementation completed for the service primitive, typed correction tools,
  ownership guard, trusted-thread dispatch, and autonomous allowlist. `_is_autonomous_write()` was verified
  generic and unchanged.
- 2026-09-22 — T3/T4 completed: whitelist, persona clause, stale 21-tool comment, and AT-11 were updated.
- 2026-09-22 — environment gap resolved by the orchestrator (`cp ../lumat-agent/infra/.env infra/.env`,
  `bash infra/test-db.sh up` -> port 5736) and the full suite run. One scoped correction: the persona
  phrase pinned by `tests/unit/test_assistant_config.py:28` was restored. **Full suite green: 1290 passed.**

## Graph nodes/edges consulted

- `registry.py`, `nodes.py`, `tukulpan.py`, `models.py` (communities per `GRAPH_REPORT.md`)
- `ExecuteTool` / `AUTONOMOUS_WRITE_ALLOWLIST` / `memory.write` -> `execute_tool` -> `_write_memory`
- `graphify query "memory save update modify tool"` — 576 nodes, truncated at 64
- `graphify query "tukulpan Memory update embedding normalized_hash review_after delete exports"` — `delete()`,
  `Memory`, `upsert()`, `_review_after()`, `hybrid_search()`
- `graphify query "assistant registry MemoryWriteArgs _write_memory execute_tool autonomy allowlist"` —
  `MemoryWriteArgs`, `_write_memory()`, `execute_tool()`, `ToolValidationError`, `ToolDefinition`
- `graphify query "assistant harness guardrails trusted thread autonomous tools"` — `guardrails()`,
  `_is_autonomous_write()`, `execute_tool()`, `test_assistant_harness_guardrails.py`
- `graphify query "assistant registry correction tools persona whitelist specification"` — `registry.py`,
  `agent_registry.py`, `assistant-tools Specification`, `Assistant`, `nodes.py`
- Consulted edge: `memory.write` -> `execute_tool` -> `_write_memory`; consulted edge: `execute_tool` ->
  `AUTONOMOUS_WRITE_ALLOWLIST`; consulted edge: `guardrails()` -> `_is_autonomous_write()`.

## Next step

Delivery is not taken. The branch `odd/memory-correction-tools` is local: nothing pushed, no PR. Commit,
push and PR remain the human's decisions under ordinary repository policy.
