# ODD: planner-arguments-null

**Branch**: `odd/planner-arguments-null`
**Worktree**: `../lumat-agent-odd-planner-arguments-null`
**Base**: `53bbe320` (= `origin/main` at branch time)
**Status**: implemented and verified; native review approved and its authority burned
**Source**: item 1 of handoff Engram #4582, resolved by the reproduction recorded in Engram #4587.

## Objective

Stop the planner from rejecting the most common plan its own model produces: a `kind: "respond"`
payload whose `arguments` is an explicit `null`.

## Problem (measured, not inferred)

The panel planner's model authors `"arguments": null` when it answers in text instead of calling a
tool. `PlannerOutput` rejects that with a `ValidationError`:

```
arguments
  Input should be a valid dictionary [type=dict_type, input_value=None]
```

`app/chat/assistant/state.py:35` declares `arguments: dict = Field(default_factory=dict)`. **A Pydantic
default covers a missing key, not an explicit `null`.** The model's `null` is semantically right — a
`respond` plan has no arguments — but our contract discards the whole plan, `bounded_fallback` takes
over, and the responder then invents a plausible answer over the honest fallback.

This is why every planner state in the dev database carries `valid: false`: conversational turns are
the majority, and that path could never validate.

## How it was reproduced

Real `plan_llm` in-process against the real provider, with the real config, reconstructing the state
from the saved context of thread 157 in the dev database.

- **Fidelity check**: the reconstructed prompt measured **2691 prompt_tokens**, matching the value
  recorded in `internal_chat_messages.assistant_metadata->cost_calls` for that turn. Same model
  (`deepseek-flash`), same `temperature=0`, same `response_format`.
- **The failing turn is the conversational one**, not the tool one:

  | Turn | Content | Replay failures |
  |---|---|---|
  | msg 66 | `hey chat tienes acceso a la memoria ?` | **6/10, then 9/15** |
  | msg 68 | `quiero que guardes una memoria de esta conversacion como test...` | 1/10 |
  | msg 70 | `si apruebo` | 0/10 |

- In every sample, every **valid** plan was `kind: "tool"` and every `kind: "respond"` plan was
  rejected. The earlier "unreproducible" result came from replaying msg 70 only (15/15 and 20/20
  valid), where the model picks `memory.write` and `arguments` is a real dict.

## Decisions

**A — Normalize at the trust boundary, exactly as `summary` already is.** A `field_validator` with
`mode="before"` maps an explicit `None` to `{}`. Precedent in the same class:
`clamp_summary` (`state.py:39-44`) already normalizes model-authored input before validation. The
model is not trusted to send `{}`; we accept its honest `null` and give it the shape our contract needs.

**B — Only `None` is normalized.** No other type is coerced: `"arguments": []`, `""`, or a string stay
rejected. Widening this would soften the boundary for no measured reason, and one cause at a time is
what the previous instrumentation contract asks for.

**C — `extra="forbid"` stays untouched.** D1 of `planner-failure-observability` makes it deliberate.

**D — The second cause stays out.** In 1 of 15 runs the model also leaked its own `response_format`
into the payload (`"type": "json_object"`), rejected by `extra_forbidden`. Same validation class,
different mechanism, and the fix would require deciding whether to tolerate a known-benign key at the
trust boundary. That is a separate unit, deliberately not touched here.

**E — No prompt change.** The prompt asks for `arguments` and does not promise it must be an object;
the model's `null` is reasonable. Changing the prompt to paper over a schema that contradicts itself
would leave the defect in place for any other model.

## Scope

- `app/chat/assistant/state.py` — the `arguments` normalizer.
- `tests/unit/test_assistant_planner.py` — the RED/GREEN coverage.
- `odd/tasks/planner-arguments-null.md` — this record.

Nothing else. The prompt, the persona, `bounded_fallback`, `extra="forbid"`, `guardrails` and the
graph shape are out of scope.

## Authorized scope

- Human-approved on 2026-09-21: this unit and the worktree
  `../lumat-agent-odd-planner-arguments-null`.
- The `"type": "json_object"` leak and the persona/allowlist contradiction are **not** in this unit.

## Constraints

- Strict TDD is active (`openspec/config.yaml` -> `testing.strict_tdd: true`), runner `uv run pytest`.
  RED must be observed before implementation.
- RDD is ON (global). Every commit is a review candidate; the consent envelope is answered by the
  **human**. The lineage is bound to **this worktree**.
- Two commits: `fix(...)` then `docs(odd): record ...`. Conventional commits, no AI attribution.
- `pyproject.toml` sets `addopts = "-q"` — do not add a second `-q`.
- `.opencode/tools/package-lock.json` is untracked noise from `rapso worktree create`; never commit it.

## Acceptance criteria

1. A planner payload with `"arguments": null` validates at the trust boundary, and `arguments` becomes
   `{}`.
2. A `kind: "respond"` payload with `"arguments": null` keeps its `summary`, does not degrade to
   `bounded_fallback`, and is reported valid.
3. A `kind: "tool"` payload with `"arguments": null` normalizes to `{}` at the boundary; the tool's own
   argument model still decides validity later, unchanged.
4. `extra="forbid"` still rejects an unknown key.
5. Every payload rejected before this change, except the `arguments: null` family, is rejected after
   it: malformed shapes, wrong `summary` types, `tool` without `kind: "tool"` and the reverse.
6. The full suite is green, with the baseline and final counts both reported.

## Checks

```bash
eval "$(bash infra/test-db.sh env)"
uv run pytest tests/unit/test_assistant_planner.py
uv run pytest tests/
git diff --name-only   # only state.py, the planner test, and this record
```

## Baseline (measured before any edit, in this worktree)

```
uv run pytest tests/  ->  1097 passed, 2 warnings, exit 0, 153.51s
```

## Tasks

- [ ] **T1 — RED.** A test that a `PlannerOutput` payload with `"arguments": null` validates and yields
      `arguments == {}`, driven through `parse_planner_output` and through `plan_llm` for the
      `kind: "respond"` case. It must fail against the current schema.
- [ ] **T2 — Normalizer.** Map an explicit `None` to `{}` in a `mode="before"` field validator.
- [ ] **T3 — Verify.** Focused file, then the full suite; counts reported.
- [ ] **T4 — Empirical re-check.** Re-run the reproduction of the failing turn (msg 66) against the real
      provider and confirm no failure carries the `arguments`/`dict_type` cause any more. Report the
      observed outcome honestly, including any remaining failure and its cause.
- [ ] **T5 — Review and record.** Native review, then the `docs(odd)` commit with the outcome.

## Progress

- [x] Graph Check before editing — `graphify query` and `graphify path` resolved `PlannerOutput`
      (`app/chat/assistant/state.py:26`, community `assistant/state.py`) and
      `plan_llm() --calls--> parse_planner_output()` (1 extracted hop). The graph exposes no directed
      edge from `parse_planner_output()` to `PlannerOutput` because the constructor call is not an
      extracted edge; `arguments_digest()` (`app/chat/assistant/approval.py:11`) is the downstream
      consumer of the same field.
- [x] Worktree created and provisioned: `uv sync`, `infra/.env` copied, test DB up.
- [x] Baseline measured (above).
- [x] **T1 — RED.** `test_planner_output_accepts_explicit_null_arguments` and
      `test_plan_llm_keeps_respond_plan_with_null_arguments` failed with `assert False is True`;
      `test_planner_output_normalizes_null_arguments_for_tool_plans` failed with
      `ValidationError ... arguments ... [type=dict_type, input_value=None]`. The guard test
      (`..._still_rejects_wrong_argument_types_and_extra_keys`) passed before **and** after, as a guard
      must.
- [x] **T2 — Normalizer.** The `arguments` field validator, 8 lines, placed after `clamp_summary`.
- [x] **T3 — Verify.** `uv run pytest tests/unit/test_assistant_planner.py` -> **29 passed**;
      `uv run pytest tests/` -> **1101 passed, 2 warnings** (baseline 1097, +4 new tests).
      `git diff --name-only` -> `app/chat/assistant/state.py` and
      `tests/unit/test_assistant_planner.py` only.
- [x] **T4 — Empirical re-check.** Below.
- [x] **T5 — Review and record.** Below.

## Verification evidence — empirical re-check (T4)

The unit suite proves the validator; it does not prove the fix addresses the measured production
failure. So the reproduction was re-run against the **real provider**, in this worktree, with the fixed
code:

| Check | Command | Result |
|---|---|---|
| Fidelity of the reconstruction | `/tmp/t4.py`, first call | `prompt_tokens = 2167`, matching the value recorded in production for that turn |
| The failing turn, 15 runs, fixed code | `/tmp/t4.py` | **15/15 valid, 0 failures**, `dict_type`/`arguments` causes: **0** |
| Plan choice distribution | same run | 9 of 15 chose `kind: "respond"` and **validated**; 6 chose `kind: "tool"` (`memory.read`) |

The 9 `respond` plans are the decisive datum: that is the path that was rejected on **every** sample
before this change. The same prompt that failed 6/10 and 9/15 against the unmodified code now validates
15/15.

Honest limits of this check: it exercises the provider, so it is not deterministic, and it does not
prove the `"type": "json_object"` leak is gone — that is a separate cause, deliberately out of scope
(decision D). The validator fixes the cause the measurement named; the suite pins it; this run shows the
measured failure no longer occurs.

## Review outcome

- Native review lineage `review-c6035fe229e4bd3c`, one consolidated lens (`review-reliability`,
  order 0) because the candidate is `medium` risk: 2 changed files, 83 changed lines.
- Consent relayed to the human and `granted`; the review ran over the frozen candidate tree
  `ceb6e059ca10128e4f866c5a2bc34fccded7b327` with `--untracked-scope=exclude`, so neither this record
  nor the untracked `package-lock.json` was part of the reviewed bytes.
- Result: **approved, zero findings**. The reviewer confirmed the normalizer and its parsing, tool-plan,
  type-validation and regression coverage.
- `authority: burned` on consumed revision
  `sha256:27d468927b071c85fdb5899b5223cdbd09deca783a75bbc0102e6fe6dcbcbdc6`.
- The reviewed revision is the `fix(...)` commit below; this record is carried by the second commit.

## Follow-up, deliberately out of scope

The `"type": "json_object"` leak stays open: in 1 of 15 measured runs the model echoed its own
`response_format` into the payload, rejected by `extra_forbidden`. It is the same validation class as
this defect but a different mechanism, and fixing it requires a decision about whether the trust
boundary tolerates a known-benign key. Decision D keeps it out of this unit.

## Delivery

Human decision pending. The reviewed candidate is committed as the `fix(...)` commit; nothing has been
pushed and no pull request exists yet.
