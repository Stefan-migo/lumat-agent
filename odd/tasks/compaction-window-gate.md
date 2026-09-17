# ODD: compaction-window-gate

## Objective

Make the assistant's session compaction actually fire, so a panel thread accumulates memory and the
assistant can recall it. Today the gate is unreachable by construction.

## Problem

`compact_session` (`app/services/agent_chat.py:337`) proceeds only when
`before_tokens >= COMPACTION_THRESHOLD_TOKENS` (4000). Its only caller (`agent_chat.py:635`) passes
`context["meta"]["estimated_tokens"]`, and `assemble_context` caps that value at
`INJECTION_TOKEN_BUDGET` (4000). The input can never exceed the value it is compared against, so the
gate never opens — measured: never flushed at 4 different message volumes.

Consequence: `write_recap` never runs, so the only automatic writer of panel-scope memory is dead.
A normal assistant thread never accumulates memory, and the assistant correctly reports having
nothing stored.

## Why — root cause (verified, not inferred)

The design states the model explicitly — `openspec/changes/archive/2026-09-10-harness-lumat/design.md:19`:

> | Rolling session | **8,000-token window; preflight at 4,000**, flush recap/evidence, retain newest 2,000, persist rotation. |

and the compaction state shape (`design.md:65`) is a before/after pair of the **window**
(`before_tokens` / `after_tokens`, where `after_tokens` = the retained ≤2000). So `before_tokens`
means **window occupancy (0..8000)**, not injected context (0..4000). **The caller passes the wrong
quantity** — the constant is not mis-set.

Three stacked defects:

| # | Defect | Evidence |
|---|---|---|
| 1a | Wrong input: the gate receives the capped injected-context size instead of the thread's window occupancy | `agent_chat.py:635`, `design.md:19,65` |
| 1b | `SESSION_WINDOW_TOKENS = 8_000` is dead — no production consumer, so nothing ever computes a window | `state.py:13`; only `tests/unit/test_assistant_harness.py:32` asserts it |
| 1c | Dead configuration — all four settings in `config.py:46-49` are never read; the code uses the hardcoded constants in `state.py:12-15`. The spec says "the **configured** compaction threshold" | grep: settings appear only in `config.py` + one unit test |

Why it went unnoticed: all six compaction tests call `compact_session(...)` **directly** with a
hand-supplied `before_tokens=4_000` (`tests/integration/test_assistant_harness_session.py:24,41,71,85`).
No test exercises the real caller's input, so the wiring bug was structurally invisible.

## Scope

**In:** the gate input, the window computation, config wiring for the four limits, the tests that
hand-feed the boundary, and the `harness-lumat` spec wording for the trigger.

**Out (separate decisions, do not touch here):** the `memory.read` argument contract and
`_context_text` discarding `context.meta`; customer-scope reachability (needs a thread↔customer
binding); `MemoryArgs` accepting unknown scopes; `record_milestone` dead code;
`PlannerOutput.summary max_length=200`.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-compaction-window-gate`
- Branch: `odd/compaction-window-gate`
- Files: `app/services/agent_chat.py`, `app/chat/assistant/state.py`, `app/config.py`,
  `tests/integration/test_assistant_harness_session.py`, `tests/unit/test_assistant_harness.py`,
  `openspec/specs/harness-lumat/spec.md`, `odd/tasks/compaction-window-gate.md`

## Constraints

- **TDD: ON** — source: project config `openspec/config.yaml` (`apply.tdd: true`,
  `strict_tdd: true`). Runner: `uv run pytest tests/`. Observed RED is required before implementation.
- Integration tests need `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat`
  (9 environment errors without it).
- HL-1 must not change: `assemble_context` keeps its deterministic injection budget and truncation
  metadata. This change fixes *what compaction measures*, not what gets injected.
- Conventional commits, no AI attribution.
- Planning heuristic: ~400 authored changed lines; this is expected to be far smaller.

## Tasks

- [ ] **T1 — RED.** Add a test that exercises the **real caller input** (the integration path that
      assembles context and then compacts), asserting compaction flushes once the thread exceeds the
      threshold. It must fail against the current code.
- [ ] **T2 — GREEN.** Make the gate measure window occupancy, computed from `messages` (which
      `compact_session` already receives and iterates), bounded by `SESSION_WINDOW_TOKENS`.
- [ ] **T3 — Config wiring.** Make the four limits in `config.py:46-49` the live source, removing the
      duplicated hardcoded constants in `state.py:12-15` or binding them to the settings.
- [ ] **T4 — Test hygiene.** Update the tests that hand-feed `before_tokens=4_000` so the value comes
      from the production path, not from the test.
- [ ] **T5 — Spec sync.** `openspec/specs/harness-lumat/spec.md:58-62` says "the configured compaction
      threshold is reached" without saying *of what*. State that it measures window occupancy.

## Acceptance criteria

1. A test exists that **fails on the current code and passes after**, exercising the caller's real
   value rather than a hand-supplied one.
2. A thread whose history exceeds the threshold flushes exactly once and retains ≤ the retention
   limit; a small thread does not flush.
3. Changing the threshold setting changes behaviour — i.e. the configuration is live, not decorative.
4. `assemble_context` still caps injected context at the injection budget (HL-1 unchanged).
5. The full suite passes.

## Checks

- Targeted: `uv run pytest tests/integration/test_assistant_harness_session.py tests/unit/test_assistant_harness.py -q`
- Full: `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/ -q`

## Progress

- [x] **T1 — RED.** Added `test_compaction_fires_once_the_thread_window_fills` and
      `test_compaction_stays_idle_for_a_short_thread` to
      `tests/integration/test_assistant_harness_session.py`, driving the real path
      (POST a message → the caller assembles the context → the caller compacts).
      RED observed for the right reason: `assert injected < threshold` **passed** while
      `assert compaction["flushed"] is True` **failed** (`assert False is True`).
- [x] **T2 — GREEN.** `compact_session` now computes window occupancy from `messages`
      (`min(sum(estimate_tokens), session_window)`) and the `before_tokens` parameter was
      **removed** — it was both redundant (the function already receives `messages`) and the
      exact surface where the defect lived. The caller no longer passes it.
- [x] **T3 — Config wiring.** Settings are now the single source: added
      `harness_limits()` (`HarnessLimits` NamedTuple) in `agent_chat.py`, which
      `compact_session` and `assemble_context` resolve at call time. The four duplicated
      constants were deleted from `state.py`, which stays importable without environment
      variables (deliberate: `app.models` already requires them at import; `state.py` did not).
- [x] **T4 — Test hygiene.** The four tests that hand-fed `before_tokens=4_000` now build
      real message histories that genuinely exceed the threshold. Added
      `test_harness_limits_come_from_settings`, which proves the knob is live.
- [x] **T5 — Spec sync.** `openspec/specs/harness-lumat/spec.md` HL-3 now states that the
      trigger measures the thread's window occupancy and MUST NOT be fed the injected
      context, plus a scenario pinning that boundary.

## Verification evidence

| Check | Command | Result |
|---|---|---|
| RED (before the fix) | `uv run pytest tests/integration/test_assistant_harness_session.py -k "thread_window_fills"` | **FAILED** — `assert False is True` on `compaction["flushed"]`; the preceding `assert injected < threshold` passed, proving the gate never opened while the thread exceeded it |
| Targeted | `uv run pytest tests/integration/test_assistant_harness_session.py tests/unit/test_assistant_harness.py tests/integration/test_assistant_harness_context.py -q` | **23 passed** |
| Full suite | `TEST_ADMIN_DB_URL=… uv run pytest tests/ -q` | **866 passed**, 0 failed |
| Config is live | `test_harness_limits_come_from_settings` | threshold 1234 / retention 321 / window 4321 / budget 111 all observed in behaviour |
| HL-1 unchanged | `assert injected < harness_limits().compaction_threshold` + `test_assembly_does_not_search_and_reports_fixed_budget_metadata` | passed |

Warnings observed are pre-existing (a `_publish_all` coroutine never awaited in
`test_webhook_ingest.py`, and a fastembed pooling notice) — unrelated to this change.

**Graph nodes consulted (Graph Check, Step 1):** `compact_session()`
(`agent_chat.py:337`), `assemble_context()`, `estimate_tokens()` (`state.py:26`),
`flush_panel_session()` (`agent_chat.py:261`), `write_recap()` (`tukulpan.py:306`),
`Settings` (`config.py:16`), `_run_agent_turn_session()` (`agent_chat.py:607`),
`test_harness_budget_defaults_are_resolved()`, `test_compaction_records_rotation_metadata()`.

## Next step

Commit as two work units (code+tests, then docs) and open the PR.

