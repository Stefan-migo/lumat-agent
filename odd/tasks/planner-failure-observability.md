# ODD: planner-failure-observability

**Branch**: `odd/planner-failure-observability`
**Worktree**: `../lumat-agent-odd-planner-failure-observability`
**Base**: `01f8ceda` (= `origin/main` at branch time)
**Status**: scoped — not started
**Discovered by**: the owner, by hand, testing the panel assistant (2026-09-21)

## Objective

Make the panel planner's failure **observable and diagnosable after the fact**. Today the planner can
fail completely and nothing records why: the turn is silently disguised as a normal chat answer, the
exception is discarded, and the fallback even throws away its own reason string.

This work unit does **not** change what the operator sees, and does **not** fix the failure. It makes
the failure knowable. That is the prerequisite for fixing it.

## Problem (verified against the dev database, 2026-09-21)

The panel assistant's planner has **never produced a valid plan in production**. Measured:

- `internal_chat_threads.assistant_state->'planner'`: **every** thread that has a planner state carries
  `kind = "respond"`, `valid = false`, `summary = "I could not safely plan that request. Please try
  again."` — the `bounded_fallback` summary. Threads 157 (the owner's test), 156, 154, 153, 152, 151,
  149, 147, 145 all show it.
- `audit_log` where `action = 'internal_chat.execution'`: **24 rows, only 3 with a non-null
  `after->>'tool'`** — in the entire history of the panel.
- The planner call **does** reach the provider: `internal_chat_messages.assistant_metadata->'cost_calls'`
  for the failing request carries `"...:planner": {"model": "deepseek-flash", "prompt_tokens": 2449,
  "completion_tokens": 817}`.

So the provider answered, the usage was recorded, and then something in
`_completion_text` / `json.loads` / `parse_planner_output` raised.

### Why it is invisible

`plan_llm` (`app/chat/assistant/nodes.py:397-436`) wraps the whole call in a bare `except Exception:`
that **logs nothing** and calls `bounded_fallback("provider failure")`. And `bounded_fallback`
(`nodes.py:132-139`) **accepts a `reason` parameter and discards it** — every reason returns the same
object:

```python
def bounded_fallback(reason: str) -> PlannerOutput:
    """Return a safe, short response plan for malformed planner output."""
    return PlannerOutput(
        kind="respond",
        arguments={},
        summary="I could not safely plan that request. Please try again.",
        requires_approval=False,
    )
```

Then the degradation completes itself: `guardrails` sees `planner.valid == False`, chooses
`decision: "fallback"` and `status: "responding"`, the graph routes to `respond_stream`, and the
responder generates a fluent answer that **overwrites** the honest fallback summary. The operator reads
a confident reply and has no signal that planning failed.

### The failure could not be reproduced

The exact production prompt was replayed against the real provider, from the production container, with
the real assembled context, `temperature=0`, `response_format={"type": "json_object"}`, model
`deepseek-flash`: **15/15 valid**, every one selecting `kind=tool, tool=memory.write` (368-1001
completion tokens). A second campaign with a stub context: 8/8 valid.

Therefore the exception's cause is **unknown**, and it is unknown precisely because nothing records it.
A previously stated inference — that 817 completion tokens was "too long for a valid plan" — was
**wrong** and is retracted: valid plans measured 368-1001 tokens.

## Decisions (agreed — do not re-litigate)

| # | Decision |
|---|---|
| **D1** | `PlannerOutput` is **not modified**. It is the trust boundary and `extra="forbid"` is deliberate. The diagnostic travels in the state dict alongside `valid`, exactly as `valid` already does. |
| **D2** | The diagnostic is **persisted in `assistant_state.planner`**, not only logged. A stdout-only log would not have survived to be read, and a DB-queryable field is how this defect was found at all. |
| **D3** | A **bounded excerpt of the raw provider text** is part of the diagnostic. The failure stage alone cannot answer the question this work unit exists to answer ("what did the model actually return?"). The panel is an internal admin surface whose database already stores full conversation content, so a bounded excerpt of the model's own planning output is proportionate. Bound it to a fixed maximum. |
| **D4** | `bounded_fallback`'s `reason` stops being discarded: it becomes the diagnostic's `reason` at each call site. Its **signature and return type stay unchanged** — existing tests compare two `bounded_fallback(...)` values for equality, and the reason must not enter `PlannerOutput` (D1). |
| **D5** | **User-visible behavior is unchanged.** An invalid plan still degrades exactly as it does today. Changing what the operator sees is a separate product decision and is out of scope. |
| **D6** | No retry, no relaxed validation, no prompt change, no persona change. Each is a separate work unit. |

## Authorized scope

- `app/chat/assistant/nodes.py` — the diagnostic, the reasons, the logging.
- `app/chat/assistant/state.py` — only if a state key needs documenting.
- `tests/unit/test_assistant_planner.py` and one focused test module — the RED/GREEN coverage.
- `odd/tasks/planner-failure-observability.md` — this record.

## Out of scope (do not touch)

- `PlannerOutput` and its validators (D1).
- `agent/prompts/assistant_plan.md`, `agent/personas/assistant.md`, `agent/prompts/assistant_respond.md`.
- The `guardrails` decision logic and the graph shape.
- The responder, the panel UI, and the WhatsApp bot.
- Any retry, backoff, or fallback-to-a-second-model behaviour (D6).
- The `AUTONOMOUS_WRITE_ALLOWLIST` / persona contradiction — a separate work unit.

## Implementation contract

1. **Every failure path carries a distinguishing reason.** After this change, no two different causes
   may produce the same recorded reason. The four paths to cover: the provider call itself failing, an
   empty completion, text that is not valid JSON, and JSON that fails `PlannerOutput` validation.
2. **The failure stage is explicit**, not inferred from the reason string.
3. **The raw excerpt is bounded** to a fixed maximum and is never empty on a non-empty response.
4. **A log record is emitted per failure**, carrying the same diagnosis, using the repository's
   `logging.getLogger(__name__)` convention.
5. **The diagnostic is queryable**: `assistant_state.planner.failure` must be readable with a single
   SQL expression, the way `assistant_state->'planner'->>'valid'` already is.
6. **A successful plan records no failure diagnostic**, and `planner.valid` stays `true`.
7. **No user-visible behaviour change** (D5): the degraded turn is byte-for-byte what it is today.

## Tasks

- [ ] **T1 — RED.** Failing tests that encode acceptance 1-6 before any production edit: each of the
      four failure paths produces its own reason, its own stage, a bounded non-empty excerpt, and a log
      record; a success produces none of them.
- [ ] **T2 — Diagnostic + reasons.** Build the diagnostic; give each failure path a distinguishing
      reason; stop discarding `bounded_fallback`'s argument.
- [ ] **T3 — Logging.** Emit one log record per failure with the same diagnosis.
- [ ] **T4 — Persistence.** Carry the diagnostic into `assistant_state.planner.failure`.
- [ ] **T5 — Verify.** Focused tests, then the full suite; counts measured and reported.

## Acceptance criteria

1. A completion whose text is not valid JSON records the parse stage, the exception type, and a bounded
   excerpt of the raw text.
2. A completion whose JSON fails `PlannerOutput` validation records the validation stage, the
   validation error, and the excerpt.
3. An empty completion records its own distinct stage.
4. A provider call that raises records its own distinct stage and exception.
5. The four reasons are mutually distinct; no two causes collapse into one recorded reason.
6. Each failure emits a log record carrying the same diagnosis.
7. The excerpt never exceeds the fixed bound.
8. A valid plan records no failure diagnostic and `planner.valid` is `true`.
9. The degraded turn's user-visible output is unchanged from the baseline.
10. The full suite is green; the baseline is measured before any edit and both counts are reported.

## Checks

```bash
export PATH="$HOME/.local/bin:$PATH"
eval "$(bash infra/test-db.sh env)"
uv run pytest tests/                              # full suite
uv run pytest tests/unit/test_assistant_planner.py tests/integration/test_assistant_harness_guardrails.py
```

`pyproject.toml` sets `addopts = "-q"` — do not add a second `-q`. No linter, type checker, or formatter
exists; the tests are the verification.

## Baseline (measured before any edit)

```
uv run pytest tests/  ->  1052 passed, 2 warnings, exit 0, 127.87s
```

## Progress

- [x] Graph Check before editing — `graphify query` on the planner area;
      `graphify path plan_llm bounded_fallback` → **`plan_llm() --calls--> bounded_fallback()`, 1 hop**.
- [x] Worktree created and provisioned; `uv sync`; `infra/.env` copied; test DB up and migrated
      (through `029`); `.opencode/tools/package-lock.json` removed.
- [x] Baseline measured (above).
- [ ] T1-T5.

## Notes for the executor

- **Strict TDD is ON** (`openspec/config.yaml` → `testing.strict_tdd: true`), runner `uv run pytest`.
  RED must be observed before implementing.
- **RDD is ON (global).** Every commit is a review candidate. The consent envelope is answered by the
  **human**, never by the agent. The lineage is bound to **this worktree**.
- The environment is already provisioned here. If starting fresh: `cp ../lumat-agent/infra/.env
  infra/.env` (gitignored), `uv sync` **before** `infra/test-db.sh env`, and `infra/test-db.sh up` —
  `env` does **not** start the database.
- `tests/unit/test_assistant_planner.py:75` asserts `malformed == bounded_fallback("x")`. That equality
  holds because the reason is not stored in `PlannerOutput`. Do **not** break that property (D1, D4).
- The review candidate excludes untracked files; commit before the review preflight.
- Commits: conventional, **no AI attribution**.
- Do not merge `main` into this branch before the PR if it breaks byte-identity with the reviewed
  candidate.
- This work unit's own acceptance is deliberately narrow: it proves the failure is **recorded**, not
  that it is **fixed**. Do not expand it into a fix.
