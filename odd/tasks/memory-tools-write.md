# ODD: memory-tools-write

## Objective

Give the panel assistant two memory tools over the channel that already exists:

1. **`memory.search`** — wire the already-built `hybrid_search()` (`app/services/tukulpan.py:414`) so the
   agent can find memory when it does **not** know which entity holds it, with a bounded result payload.
2. **`memory.write`** — let the agent persist its own memory **autonomously**, restricted to the current
   panel thread and with no human approval step.

This is work unit **#3** of the Tukulpan/Engram series (decision **D1**,
`.cortex-sessions/ready-for-odd/2026-09-17-memoria-tukulpan-vs-engram/report.md:34-37,153`). Its
dependencies are satisfied: WU#1 (#235) gave the planner the real tool catalog with schemas, and WU#2
(#236) removed the panel memory push, so a memory write no longer has blast radius over every prompt in
the thread. Base commit: `9db746b7`.

## Problem

**`hybrid_search()` has no production caller.** It is defined and exported at
`app/services/tukulpan.py:51`, `:69`, `:414` and nothing invokes it. The panel assistant can only call
`memory.read` (`app/chat/assistant/tools/registry.py:190-194`), which lists rows for a **known**
`scope` + `entity_id` and filters by exact `topic_key`. When the agent does not know where a memory
lives, it has no tool at all. Meanwhile the agent cannot record anything it learns: every write tool in
the registry is approval-gated.

Decision **D1** (user product decision) rejected keeping the assistant read-only: *memory only the
system writes is not the agent's memory*. But the existing safety boundary makes autonomous writes
impossible, and two premises inherited from the earlier handoff turned out to be false.

### Premise correction 1 — `tool_evidence` has no size budget

`app/chat/assistant/nodes.py:573-576` interpolates the raw tool result into the responder prompt:

```python
"tool_evidence": str(state.get("tool_result") or "")
```

The 4000-token injection budget (`app/config.py:46`, `app/services/agent_chat.py:426-485`) governs
assembled history and attachments only. It does **not** cap tool evidence. The only bounds are
`MAX_ITEMS = 20` and `_plain()` (`registry.py:140-153`).

`hybrid_search()` returns the full `contenido` of every row (`tukulpan.py:470-484`). Wiring it directly
would inject an unbounded blob into the responder prompt. **`memory.search` must bound its own output.**

### Premise correction 2 — autonomous writes are impossible today

`app/chat/assistant/tools/registry.py:334-337`:

```python
if not definition.read_only and not approval:
    raise ToolValidationError("write tool requires consumed exact approval")
```

That approval is a SHA-256 digest over the tool name plus canonical arguments, consumed and unexpired
(`app/chat/assistant/approval.py:175-217`, digest at `:11-16`). `guardrails()` additionally pauses the
graph before execution for any non-read tool (`nodes.py:467-472`). So today the assistant **cannot**
write anything without a human approving exact arguments.

### The security consequence of the chosen design

The approved design is **bounded autonomy: `memory.write` targets only the current panel thread**.
That restriction **cannot** be expressed as a tool argument. The planner is an LLM: if `memory.write`
accepted `scope`/`entity_id`, the model could write into `thread:<other>` or `customer:<x>`, and the
policy would collapse on the first hallucination. The target must be derived **server-side from the
trusted turn identity** (`AssistantState.thread_id`, `app/chat/assistant/state.py:147`), never from
model-supplied arguments.

## Why this shape

- **No new plumbing beyond one parameter.** `execute_tool()` already has an escape hatch for handler
  context: the `project.*` tools pass `_approval=` into their handlers (`registry.py:317-329`). The
  trusted thread id travels the same way.
- **`SDB_WRITE_ALLOWLIST` is not the right lever.** It gates writes reachable from the SDB planner
  (`registry.py:21-27`, `app/services/agent_chat.py:131-192`), which has no panel thread. A separate
  `AUTONOMOUS_WRITE_ALLOWLIST` keeps the two concerns apart and lets the SDB path fail closed.
- **Reads stay as they are.** `memory.search` mirrors `memory.read`'s existing `scope` + `entity_id`
  contract (AT-8). Changing read reach is out of scope; the asymmetry is deliberate — a read surfaces
  data the assistant is already authorized to read, a write mutates state with no approval.
- **Reuse the recap write pattern.** `write_recap()` (`tukulpan.py:306-343`) already solves savepoint
  containment and idempotency: `session.begin_nested()`, `upsert` by `topic_key`, and degraded return
  instead of raising.

## Scope

### In scope

| File | Change |
|---|---|
| `app/chat/assistant/tools/registry.py` | `MemorySearchArgs`, `MemoryWriteArgs`, `_search_memory`, `_write_memory`, two `ToolDefinition` entries, `AUTONOMOUS_WRITE_ALLOWLIST`, `trusted_thread_id` parameter on `execute_tool()` |
| `app/chat/assistant/nodes.py` | `guardrails()` honors the autonomy allowlist; `execute()` passes `trusted_thread_id=state.get("thread_id")` |
| `agent/registry.yaml` | `memory.search` and `memory.write` added to `assistant.tools_whitelist` |
| `openspec/specs/assistant-tools/spec.md` | AT-8 extension (`memory.search`) + new requirement for the autonomous write contract |
| `tests/unit/test_assistant_tools.py` | Coverage for both tools, the bound, and the fail-closed paths |
| `tests/unit/test_agent_registry.py` | Update the assistant whitelist count for the two required tools |
| `tests/integration/test_assistant_harness_guardrails.py` | Node-level autonomy, SDB fail-closed, and DB idempotency coverage |
| `tests/functional/test_api_assistant_capabilities.py` | Update the capabilities tool count and surfaced-tool set |

### Out of scope

- Two-axis memory, provenance column, visibility rule (WU#4).
- The `memory.kpis` misnomer (WU#5) and the responder DSML leak (WU#6).
- Read reach changes: `memory.read`/`memory.search` keep the current explicit `scope` + `entity_id`.
- WhatsApp memory push — a separate channel, deliberately excluded by the original proposal.

## Contract

### `memory.search` (read-only)

```
MemorySearchArgs:
  query: str, 1..500, required
  scope: Literal["panel", "customer"], required
  entity_id: str, 1..100, required   # same scope/entity validator as MemoryArgs
  limit: int, 1..10, default 5
```

Handler delegates to `memory.hybrid_search(session, query, scope=..., entity_id=..., top_k=args.limit)`.

**Output bound (required):** each returned row's `contenido` is truncated to a fixed character cap
before the payload leaves the handler. The row count is already bounded by `limit` (max 10) and the
service's own `top_k`. The cap is what keeps `tool_evidence` finite.

### `memory.write` (write, autonomous, thread-anchored)

```
MemoryWriteArgs:
  titulo: str, 1..200, required
  contenido: str, 1..2000, required
  topic_key: str, 1..200, required, must start with "agent:"
  tipo: Literal["decision", "discovery", "pattern", "preference"], default "discovery"
```

- **No `scope`, no `entity_id`.** Both are derived: `scope="panel"`,
  `entity_id=f"thread:{trusted_thread_id}"`.
- **`topic_key` is namespaced** with an `agent:` prefix so an autonomous write can never overwrite a
  system-authored row such as the recap (`assistant-recap:{thread_id}:{last_id}`,
  `tukulpan.py:330-340`). The `UNIQUE(proyecto, scope, entity_id, topic_key)` constraint plus `upsert`
  makes repeated writes idempotent instead of duplicating.
- Returns `{"written": True, "id": ..., "topic_key": ...}` or
  `{"written": False, "degraded_reason": ...}` — never raises on embedding/flush failure.

### The autonomy boundary

```
AUTONOMOUS_WRITE_ALLOWLIST = frozenset({"memory.write"})
```

In `execute_tool()`:

- a write in `AUTONOMOUS_WRITE_ALLOWLIST` skips the approval requirement **only if**
  `trusted_thread_id` is a positive `int`; otherwise it raises `ToolValidationError` (fail closed);
- any other write keeps the current approval requirement unchanged.

In `guardrails()` the same rule decides `approval_required`, otherwise the graph pauses for approval
before execution is ever reached.

## Tasks

- [x] **T1 — `memory.search`.** Add `MemorySearchArgs` (with the shared scope/entity validator),
      `_search_memory` wrapping `hybrid_search()` with a per-row `contenido` cap, and the read-only
      `ToolDefinition`. Whitelist it.
      *Check:* a panel search returns only scoped rows; a long `contenido` comes back truncated; an
      out-of-scope `entity_id` returns nothing.
- [x] **T2 — `memory.write` args + handler.** Add `MemoryWriteArgs`, `_write_memory` using the
      `write_recap` pattern (`begin_nested` + `upsert` + degraded return), and the write
      `ToolDefinition`. Whitelist it.
      *Check:* a write lands at `scope="panel"`, `entity_id="thread:<id>"`; repeating the same
      `topic_key` updates instead of duplicating; a `topic_key` without the `agent:` prefix is
      rejected; an embedding failure returns `written: False` without raising.
- [x] **T3 — autonomy boundary.** Add `AUTONOMOUS_WRITE_ALLOWLIST` and the `trusted_thread_id`
      parameter to `execute_tool()`; update `guardrails()` and `execute()` in `nodes.py`.
      *Check:* `memory.write` executes with no approval when a trusted thread is present; raises when
      it is absent; every other write tool still demands approval; the SDB path fails closed.
- [x] **T4 — spec.** Extend AT-8 with the `memory.search` scenarios and add the autonomous write
      requirement with its scenarios (bounded target, prefix guard, approval still required elsewhere).
- [x] **T5 — tests + full suite.** Focused tests green and the full suite green (`886 passed`). Two stale
      whitelist-count assertions outside the original file set were updated as direct consequences of the
      required configuration change.

## Constraints

- **Strict TDD** (`openspec/config.yaml`, `strict_tdd: true`). Observed RED before implementation, then
  GREEN. Runner: `uv run pytest tests/`.
- **No approval bypass beyond `memory.write`.** The autonomy allowlist has exactly one member.
- **No model-supplied memory target for writes.** Derive it from the trusted turn identity.
- English artifacts: code, tests, spec, commits, this document.
- No `Co-Authored-By` or AI attribution in commits. Conventional commits.
- One concern per commit; the ODD doc is committed with the work unit.

## Checks

- `uv run pytest tests/unit/test_assistant_tools.py` — focused contract coverage.
- `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/` — full suite
  (~7-8 minutes, 877 tests at base). Without the admin URL the setup fails with
  `InsufficientPrivilege: permission denied to alter role`; that is an environment gap, not a code bug.
- The repo has no linter, typechecker, pre-commit, or hooks. The tests are the verification.

## Acceptance criteria

1. `memory.search` is invocable by the planner, returns scoped ranked results, and its payload is
   bounded per row.
2. `memory.write` persists to the current panel thread with no approval step, is idempotent by
   `topic_key`, and cannot target any other scope or entity.
3. No other write tool gained autonomy, and the SDB path cannot use `memory.write`.
4. Spec scenarios and tests cover the bound, the prefix guard, and both fail-closed paths.
5. Full suite green.

## Progress

- [x] Reconnaissance (read-only) complete; two handoff premises corrected.
- [x] Design decision: bounded autonomy to the current thread (user-approved).
- [x] Worktree consent (user-approved).
- [x] T1 — `memory.search` with a per-row `contenido` bound.
- [x] T2 — `memory.write` args + handler with savepoint/`upsert`/degraded return.
- [x] T3 — autonomy boundary (`AUTONOMOUS_WRITE_ALLOWLIST`, `trusted_thread_id`, `guardrails()`/`execute()`).
- [x] T4 — spec: AT-8 extension + AT-9 + scenarios.
- [x] T5 — tests green, full suite green.
- [x] RDD review approved, authority burned.

## Verification evidence

- Behavioral RED for the exact search bound: `1 failed in 0.26s` (`AssertionError: assert 1999 == 2000`).
- Behavioral RED for the trusted-thread guardrail: `1 failed, 1 passed in 1.36s` (`assert 'approval_pending' == 'executing'`).
- Behavioral RED for SDB fail-closed: `1 failed in 0.75s` (`assert 'completed' == 'failed'`).
- Behavioral RED for DB idempotency/key contract: `1 failed in 0.75s` (`assert 0 == 1`).
- GREEN focused/integration run: `86 passed in 8.62s`.
- Full suite command: `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/`
- Full suite result (final, after the stale-count corrections): **`886 passed, 2 warnings in 514.34s (0:08:34)`**.
  The 2 warnings are pre-existing at the base commit (`_publish_all` never awaited, and the fastembed
  mean-pooling notice), not introduced here.

### Corrective-pass premise correction

The claim that the registry-count assertion was the only full-suite failure was false. After correcting
`tests/unit/test_agent_registry.py`, the full suite exposed a second stale count assertion in
`tests/functional/test_api_assistant_capabilities.py:36` (`len(payload["tools"]) == 19`). Both are direct
consequences of the required whitelist change, not scope creep, and both were corrected: the capability
test now asserts 21 tools and includes the two new names in its surfaced-tool set.

### Review

- RDD, tier **medium**, one lens: `review-reliability`.
- Lineage `review-601dee2c0fe3f580`, target
  `sha256:e53ad6cb21712d4897a0d84cf514bfd8862ac3a5a9976b18a94342302ffd9afc`.
- Findings: **0**. Acknowledgement consumed `sha256:0404cc8924291cdce6e82c292a0d1ee2f158388bcfa04a4af65529cd35b7d8ce`,
  `authority: burned`, 0 corrections used of a 164-line budget.

### Final shape

- 8 files, `+311/−15` tracked, plus this untracked ODD document.
- `memory.search`: `MemorySearchArgs` (scoped) → `hybrid_search(top_k=limit)` → per-row `contenido` capped at
  `MEMORY_SEARCH_CONTENT_LIMIT = 2_000`, matching the write cap.
- `memory.write`: `MemoryWriteArgs` with no `scope`/`entity_id`, `agent:`-namespaced `topic_key`,
  `tipo` closed to four agent-memory kinds; handler derives `scope="panel"` and
  `entity_id=f"thread:{trusted_thread_id}"`, wraps `upsert` in `begin_nested()`, and degrades instead of raising.
- Boundary: `AUTONOMOUS_WRITE_ALLOWLIST = frozenset({"memory.write"})`; `execute_tool()` requires a positive
  real `int` `trusted_thread_id` for an allow-listed write and raises otherwise; `_is_autonomous_write()`
  in `nodes.py` is the single shared predicate used by both `guardrails()` and `execute()`. No other write
  gained autonomy and `SDB_WRITE_ALLOWLIST` is untouched.

## Next step

Implementation, verification, and review are complete and the review authority is burned. Delivery
(commit, push, PR) is a separate human decision under ordinary repository policy and has not been taken.
