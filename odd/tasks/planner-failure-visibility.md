# ODD: planner-failure-visibility

**Branch**: `odd/planner-failure-visibility`
**Worktree**: `../lumat-agent-odd-planner-failure-visibility`
**Base**: `b9bd8a6f` (= `origin/main` at branch time)
**Status**: merged — PR #291 (`f031721b`).
**Source**: the third pending the owner asked to close after the panel memory-read fix (#287) and the
planner-snapshot fix (#289). The owner chose option **A** on 2026-09-22: show the failure and do not
answer. `planner-failure-observability` had already named this path and left it out of scope on purpose —
its decision D5 says *"Changing what the operator sees is a separate product decision"*. This is that
decision being taken.

## Objective

When a plan does not survive the trust boundary, the operator reads the honest fallback summary instead
of a fluent answer generated on top of a plan that never existed.

## Problem (the measured path)

`guardrails` degrades in two places, and both return `decision: "fallback"` with the plan set to
`bounded_fallback(...)`, whose `kind` is `"respond"`:

- `nodes.py:520-521` — the planner itself failed (`planner.valid` is false).
- `nodes.py:535-541` — the plan was rejected by the boundary (not whitelisted, or invalid arguments).

`_after_guardrails` (`graph.py:59-62`) routes on the plan's `kind`, so a fallback plan is indistinguishable
from a legitimate `kind: "respond"` plan and goes to `respond_stream`. The responder then generates a
fluent answer, and because `agent_chat.py:726-733` persists `result["response"]`, that answer — not the
fallback summary — becomes the operator's message.

Observed during the #287 verification: the responder happened to be honest ("no voy a inventar ni
reconstruir lo que diría la memoria"), but that is the responder's own judgement, not the product telling
the operator that planning failed. The summary `bounded_fallback` builds was never read by anyone.

## Decisions

**A — route to `END` when `guardrails.decision` is `"fallback"`.** One condition in `_after_guardrails`,
covering both degradation paths, using a field `guardrails` already writes. No new state key, no new
status, no change to `guardrails`' decision logic itself.

**B — the fallback summary is localized to Spanish.** Until now this string was internal: the responder
always overwrote it, so its language did not matter. This unit is what makes it operator-facing, and the
panel's user-facing copy is Spanish (`agent_chat.py:729`, `:745`). Promoting an English internal string to
production copy would ship an inconsistency, so the string moves with the promotion. This is the only
reason the copy changes, and it is disclosed rather than slipped in.

**C — nothing else about the degraded turn changes.** `status` stays `"responding"`, the state keys stay
as they are, and no retry, prompt or persona change is introduced.

**D — only plan-level failures are terminal, decided after the full suite forced the question.** The
first version of the routing treated every `fallback` as terminal. That is broader than the defect: a
**provider outage** dresses nothing, because nothing answers — and today its second failure is what marks
the message `failed` and `recoverable`. Making it terminal would have quietly traded a visible failure
and its recovery signal for a `processed` message carrying a summary. The owner chose the narrow scope:
`extraction`, `completion`, `parse` and `guardrails` stages end the turn on the summary; `provider` and
`instrumentation` keep the existing path. `test_model_failure_marks_message_failed_and_recoverable`
(`tests/integration/test_h4_chat.py:114`) is the witness that the narrow scope is required, and it stays
meaningful.

## Scope

- `app/chat/assistant/graph.py` — the fallback routing and the stage predicate.
- `app/chat/assistant/nodes.py` — the fallback summary copy.
- `tests/integration/test_assistant_chat.py` — the end-to-end coverage.
- `tests/unit/test_assistant_planner.py` — the assertion that pins the old copy.
- `tests/integration/test_h4_chat.py`, `tests/integration/test_agent_chat_realtime.py`,
  `tests/integration/test_assistant_harness_production.py` — four tests that encoded the old contract.
  They must move with the routing: leaving them out would mean committing a red suite, and they are the
  evidence that the first, broader version of the fix was wrong. This is the second unit in a row to
  exceed the repo's five-file commit guideline, by three files, and for the same reason.
- `odd/tasks/planner-failure-visibility.md` — this record.

Nothing else. `guardrails`' decision logic, `bounded_fallback`'s signature, the responder itself,
`PlannerOutput`, and the panel UI are out of scope.

## Authorized scope

- Human-approved on 2026-09-22: option A of the product fork, as the third pending after #287 and #289.

## Constraints

- Strict TDD is active (`openspec/config.yaml` -> `testing.strict_tdd: true`), runner `uv run pytest`.
  RED must be observed before implementation.
- RDD is ON (global). Every commit is a review candidate; the consent envelope is answered by the
  **human**. The lineage is bound to **this worktree**.
- Two commits: `fix(...)` then `docs(odd): record ...`. Conventional commits, no AI attribution.
- `pyproject.toml` sets `addopts = "-q"` — do not add a second `-q`.
- `.opencode/tools/package-lock.json` is untracked noise from `rapso worktree create`; never commit it.
- Preflight with an explicit `--base-ref=<origin/main> --committed-only`: the #289 mis-projection showed
  that a selectorless status covers only the working tree when the worktree also has uncommitted changes.

## Acceptance criteria

1. A turn whose planner fails does not call the responder at all.
2. That turn's operator-visible message is the fallback summary, in the panel's language.
3. A turn whose plan is rejected by the boundary behaves the same way.
4. A legitimate `kind: "respond"` plan still reaches the responder unchanged, so the fallback and the
   normal answer path are distinguishable.
5. A successful tool plan still executes and then responds.
6. The full suite is green, with the baseline and final counts both reported.

## Checks

```bash
eval "$(bash infra/test-db.sh env)"
uv run pytest tests/integration/test_assistant_chat.py
uv run pytest tests/unit/test_assistant_planner.py
uv run pytest tests/
```

## Baseline (measured before any edit, in this worktree)

```
uv run pytest tests/  ->  1128 passed, 2 warnings, 116.20s
```

## Tasks

- [ ] **T1 — RED.** A planner failure must not reach the responder, and the operator must read the
      fallback summary; a legitimate respond plan must still reach it.
- [ ] **T2 — Routing.** `_after_guardrails` sends fallback turns to `END`.
- [ ] **T3 — Copy.** The fallback summary moves to the panel's language.
- [ ] **T4 — Verify.** Focused files, then the full suite; counts reported.
- [ ] **T5 — Review and record.**

## Progress

- [x] Graph Check before editing — `graphify query` resolved `guardrails()`
      (`app/chat/assistant/nodes.py:515`) and the community `test_assistant_harness_guardrails.py`. The
      graph does not model the conditional edges, so the routing was read from `graph.py:59-62` instead.
- [x] Worktree provisioned: `uv sync`, `infra/.env` copied, test DB up. Base `b9bd8a6f`.
- [x] Baseline measured (above).
- [x] **T1 — RED.** Four tests over the real route. `2 failed, 2 passed`: both degradation paths reached
      the responder, while the legitimate `respond` and tool paths already behaved correctly, which is the
      control that stops the fix from over-reaching.
- [x] **T2 / T3 — implemented.** One routing condition plus the localized summary.
- [x] **T4 — Verify.** `uv run pytest tests/` -> **1132 passed, 2 warnings** (baseline 1128, +4 tests).
- [ ] T5.

## What the full suite taught this unit

The first routing version made every fallback terminal: **6 failed, 1126 passed**. All six were tests
that encoded the old contract, and reading them changed the design:

- **5 were stubs that accidentally failed the planner.** `_FakeChatClient` (`test_h4_chat.py:31`) and
  `_StreamingChatClient` (`test_agent_chat_realtime.py:28`) return a plain answer for *every* call, the
  planner included, so the planner failed with `invalid_json` or `empty_completion` and the test passed
  because the responder ran anyway. Repairing the stubs to return a valid plan for the non-streaming call
  preserves each test's intent: the h4 test still asserts the persisted answer, and the two realtime tests
  still assert call index 1 is the streaming call and the SSE preview contract.
- **1 was a different failure class**, and produced decision D above.
- **1 more** (`test_malformed_or_unwhitelisted_production_plan_falls_back_without_execution`) asserted
  `len(captured) == 3`, counting a responder call that a rejected plan no longer makes. It now asserts 2
  and checks the persona separation on the planner prompt instead — the responder prompt is still covered
  for a valid plan by the neighbouring production test.

None of the six was a real regression: every one of them passed only because the planner was failing
silently and the responder covered it. That is the defect this unit exists to close.

## Verification evidence

RED before the fix, over the real route and the real graph — both degradation paths reached the responder:

```
FAILED test_a_failed_planner_does_not_reach_the_responder
FAILED test_a_boundary_rejected_plan_does_not_reach_the_responder
2 failed, 2 passed
```

The two that passed are the controls: a legitimate `kind: "respond"` plan and a successful tool plan
still reach the responder, so the change cannot over-reach.

After: `uv run pytest tests/integration/test_assistant_chat.py -k ...` -> **4 passed**; full suite
**1132 passed, 2 warnings**.

Not verified through the panel UI. The observable is the persisted agent message and the provider calls,
and the tests drive the real HTTP route, the real graph and the real database — only the provider is
substituted. The one exception is the production test, which goes through a real HTTP provider stub via
`respx`.

## Review outcome

- Native review lineage `review-8dc13d685a5ff03c`, one consolidated lens (`review-reliability`, order 0),
  `medium` risk, 7 files / 119 changed lines, correction budget 60. Consent relayed to the human and
  answered `granted`. Result: **approved, zero findings**. `authority: burned` on consumed revision
  `sha256:6013455503d88f61a3f5c37321de21cb2f0761dad08407be9b70455c6e786109`.
- The preflight ran with `--base-ref=<origin/main> --committed-only` from the start, so the projection was
  the committed fix and this record stayed out of the reviewed bytes. The #289 mis-projection did not
  repeat.

## Delivery

Pending: push the branch, open the pull request, and wait for CI.
