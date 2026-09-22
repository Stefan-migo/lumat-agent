# ODD: cm4-linear-path-scope

## Objective

Make the CM-4 requirement, its traceability map, and its test names describe the path that actually
runs. No production behaviour changes: the code is already deliberate. What is wrong is the
documentation, and a false coverage claim that has already caused one wasted investigation.

**Updated after T1:** the investigation also established that the CM-4 branch is *unreachable*, not
merely untested (see "T1 result"), which makes the branch a guard rather than dead code and turns the
final disposition into a decision the human has to make. The unit is paused at that decision.

## Problem

The prior handoff recorded P8 as *"`declined` is structurally unreachable in the triage path"* and
framed it as a defect. Three separate statements were fused into that one claim, and only the first is
true. All three were verified against the source for this record.

**1. True, and deliberate.** A Kb-scoped miss in `research_triage` converges on `handoff`, not on
`respond`'s CM-4 branch. `app/chat/subgraphs/research_triage.py:112-129`: after the bounded retry
(AO-8, `MAX_TRIAGE_RETRIES`) is exhausted the node logs the unresolved question and returns
`{"next_step": "handoff", "escalate": True, "escalate_reason": "kb_miss"}`.

**2. False.** The handoff's framing implied the path was defective. It is pinned as intended:

```python
# tests/integration/test_chat_capture.py:222-226
# H2 (PR 2, AO-8): the scoped research_triage miss hands off directly
# (it does NOT reach respond's canned CANNOT_ANSWER_REPLY); the last reply
# is the handoff message announcing human takeover.
assert CANNOT_ANSWER_REPLY not in replies
assert replies[-1] == "Un asesor revisará tu caso y te contactará a la brevedad."
```

**3. Half true — and the correction matters.** This record originally claimed the "unreachable" framing was
an artefact of a misnamed test and an ambiguous scenario, and that CM-4 was merely **untested**. **T1
disproved that**: the branch is genuinely unreachable for every contract-legal intent, and the proof is
in "T1 result" below. Two things are true at once and must not be confused:

- The branch (`respond.py:139-150`) is **unreachable** — no intent in the classifier's declared
  vocabulary routes to it.
- The test is **still misnamed** (`test_cm4_kb_miss_cannot_answer_and_logs_unresolved` asserts the
  refusal is absent) and the requirement's scenario still reads as if it governs KB misses. Those are
  independent documentation defects that made the truth hard to see from either the spec or the suite.

**The consequences, both verified and both real:**

- **A false coverage claim.** `tests/README.md:75` maps CM-4's "no reliable answer" scenario to that
  test. The map points, for the requirement that says *it states it cannot answer reliably*, at a test
  asserting the refusal is never emitted. No test in the repository emits `CANNOT_ANSWER_REPLY`
  through the graph: `tests/unit/test_kb_fidelity.py:144-159` proves the *classifier* labels the
  string, and `tests/unit/test_prompts.py:468-475` compares the constant. Neither executes a turn.
- **A hidden customer-visible asymmetry.** The two paths do not show the customer the same thing:

  | path | what the customer receives |
  |---|---|
  | KB-intent miss (triage) | `HANDOFF_REPLY` — "Un asesor revisará tu caso y te contactará a la brevedad." |
  | CM-4 (linear) | `CANNOT_ANSWER_REPLY` **and** `HANDOFF_REPLY` — `replies` accumulates (`add` reducer) and `_after_respond` routes the escalation to `handoff`, which appends its own reply |

  That is the real, unstated difference: the path the spec names sends **two** messages; the path the
  handoff called defective sends **one**, and the cleaner one.

**What this is not.** CM-6 logging is satisfied on both paths. An earlier hypothesis that the triage
miss skips `log_unresolved` was checked and is **false**: `research_triage.py:115-121` calls
`respond_node.log_unresolved(...)` explicitly. Nothing is broken in observability.

## Scope

**In:** CM-4's requirement and scenarios in the canonical spec; the name of the misnamed test; the
living traceability map in `tests/README.md`; and the missing end-to-end test that proves CM-4's
refusal is emitted on the linear path.

**Out:** any change to production behaviour, the routing table, `_dispatch`, `respond`, `handoff`,
`research_triage`, `HANDOFF_REPLY`, `CANNOT_ANSWER_REPLY`, AO-8's retry bound, CM-6 logging, the
emission of two replies on the linear path (recorded here as a finding, not fixed here), and the
historical `openspec/changes/hito-1-setup-whatsapp/verify-report.md`, whose stale reference is left
intact on purpose.

## Spec constraints (binding — do not violate)

- `openspec/config.yaml` `rules.specs` — scenarios use Given/When/Then and RFC 2119 keywords.
- `openspec/specs/conversation-manager/spec.md:47-59` — CM-4 as it stands. The requirement text itself
  is accurate and stays; what changes is which path its scenarios name.
- `openspec/specs/agent-orchestration/spec.md:110-116` — **AO-8** bounds the retry to ≤1 and requires
  the sub-agent to hand off rather than loop. The triage behaviour is AO-8 working as specified.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-cm4-linear-path-scope`
- Branch: `odd/cm4-linear-path-scope`
- Base: `95f27db7` — verified with `git merge-base HEAD origin/main` after creation, equal to
  `origin/main` at that moment (the merge of PR #285).
- Files:
  - `odd/tasks/cm4-linear-path-scope.md`
  - `openspec/specs/conversation-manager/spec.md`
  - `tests/integration/test_chat_capture.py`
  - `tests/README.md`

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml` (`testing.strict_tdd: true`), runner `uv run pytest`.
  The rename and the spec edit change no behaviour, so they cannot produce a RED; the new test is a
  **characterization test** of existing behaviour and is declared as such rather than dressed up with
  an invented RED. It either passes (CM-4 is reachable, the claim is settled) or fails (CM-4 is not
  reachable, and then this unit has found a real defect and must say so instead of adjusting the test).
- Test DB for this worktree: `infra/test-db.sh up`, migrations via
  `DATABASE_URL="$TEST_ADMIN_DB_URL" APP_DB_PASSWORD=app PYTHON="$PWD/.venv/bin/python" bash db/migrate.sh`.
  `eval "$(bash infra/test-db.sh env)"` before pytest.
- Artifacts in English.
- Backend only: no frontend file is touched, so `cd web && npm run test` is not part of the gate —
  declared, not silently skipped.
- The historical verify-report is NOT edited.

## Decisions

- **D1 — The fix is documentation, chosen over changing behaviour.** The human chose aligning the docs
  to the code rather than the code to the spec. Rationale: both paths already log and escalate, the
  handoff text is defensible, and the divergent path is the one that sends two redundant messages —
  so "fixing" the triage path to match the spec would import the redundancy, not remove it.
- **D2 — The spec names the path, not just the condition.** CM-4's "No reliable answer" scenario is
  narrowed to the linear path, and a second scenario records the KB-intent escalation with its reason
  (AO-8) and the fact that the canned refusal is not emitted. Without the second scenario the false
  model is reconstructible from the spec alone, which is exactly how it was constructed the first time.
- **D3 — The test is renamed to assert what it verifies, not what it references.** A test whose name
  says `cm4_cannot_answer` while asserting `CANNOT_ANSWER_REPLY not in replies` is the root cause of
  the false coverage claim. Renaming is the whole fix for that claim.
- **D4 — The missing coverage is added here rather than deferred.** The map declares a coverage that
  does not exist; correcting the map without adding the coverage would make the documentation true and
  the reality still unverified. The test is the only instrument that can settle whether CM-4 exists.
- **D5 — The historical verify-report is left stale, on purpose.** It records what was verified when
  Hito 1 closed. Rewriting it would be falsifying a record; the living map is the place that tracks
  current test names.
- **D6 — The double reply on the linear path is recorded, not fixed.** `CANNOT_ANSWER_REPLY` followed
  by `HANDOFF_REPLY` is a real finding with a real customer-facing cost, and it is out of this unit's
  scope (it is behaviour, not documentation). It is written down here so it is a decision and not an
  accident.
- **D7 — The branch stays, reclassified as a guard.** After T1 established that the branch is
  unreachable, the human chose to keep it and document it, over deleting it. Rationale: without the
  branch, an undeclared intent with no KB content would fall through to `_answer_from_kb(text, "")` —
  the model answering from an empty `<kb>` block. Deleting it removes defence in depth, not weight.
  The third option, making it reachable by changing how `unknown` is handled, was rejected: it changes
  customer-visible behaviour to fix something with no measured harm.

## Tasks

- [x] **T1** — Written, **failed, and that failure is the finding.** The end-to-end test could not reach
      CM-4 (see "T1 result" below). The assertion was NOT weakened: it was replaced by two tests that
      assert the truth — the explicit characterization work.
- [x] **T1b** — `test_cm4_guard_refuses_an_undeclared_intent_with_no_kb`: exercises the guard directly by
      running `respond` with an undeclared intent and no KB content. GREEN.
- [x] **T1c** — `test_unknown_intent_never_reaches_the_cm4_refusal`: the negative half — turn 1 adds
      nothing beyond the greeting, turn 2 escalates (HH-3), and the refusal never appears. GREEN.
- [x] **T2** — Renamed to `test_triage_kb_miss_hands_off_without_the_cm4_refusal`, with a docstring
      stating that the old name is what made the traceability map claim a coverage this test cannot
      provide. The module docstring's CM-4 mapping line was corrected too.
- [x] **T3** — `tests/README.md`: the CM-4 row now points at the two tests that actually cover the
      requirement and labels it a defensive guard; the renamed triage test was added to the CM-6 row.
- [x] **T4** — `openspec/specs/conversation-manager/spec.md`: CM-4's requirement gained the guard
      paragraph, the "No reliable answer" scenario is scoped to an undeclared intent, and the
      KB-intent handoff scenario was added.
- [x] **T5** — Verification, all observed:
  - `uv run pytest tests/integration/test_chat_capture.py -q` → **11 passed**.
  - `uv run pytest tests/` → **1121 passed, exit 0**, 2 warnings. Net `+1` test versus the base (one test
    replaced by two, derived from the diff — the base count was not re-measured). Both warnings are
    unrelated to this change (a `_publish_all` coroutine warning in `test_webhook_ingest.py`, and the
    fastembed mean-pooling warning); they are reported, not claimed as pre-existing-by-measurement.
  - `git diff --check` → no whitespace errors.
  - `git diff --name-only | grep '^app/'` → **nothing**. No production source was touched.
  - Frontend suite not run: no `web/` file is touched. Declared, not silently skipped.

## T1 result — CM-4's refusal branch is unreachable, and this is now proven, not inferred

The planned test routed an `unknown` message with no KB content and asserted `CANNOT_ANSWER_REPLY in
replies`. **It failed**, and the failure is the answer:

```
AssertionError: assert 'Lo siento, no puedo responder con seguridad...' in
['Hola, soy el asistente virtual de Lumat, ... 8. Hablar con una persona']
```

The turn produced only the greeting menu. Reading the code explains why, and the explanation closes the
question:

1. **The classifier's declared vocabulary** (`agent/personas/classify.md:1`) is exactly
   `consulta, calefont, caldera, calefaccion, solicitar_visita, valores, postventa, emergencia, persona,
   unknown`.
2. **The routing** (`orchestrate._dispatch`, `orchestrate.py:70-94`) sends every one of them elsewhere:
   `calefont`/`caldera`/`calefaccion`/`solicitar_visita` → `capture`; `valores`/`postventa`/`consulta` →
   `research_triage`; `persona`/`emergencia` → `handoff`. **`unknown` is the only intent that lands on
   the linear `respond` node.**
3. **And `unknown` never reaches the retrieval** — `respond.py:121-128` returns first: turn ≤ 1 returns
   nothing (the CM-1 greeting already answered the turn), turn > 1 returns `CLARIFICATION_REPLY`.
4. Therefore `respond.py:139-150` — the CM-4 branch — is reachable **only if the classifier emits an
   intent outside its declared vocabulary**. That is a contract violation, not a path.

**So the original handoff was right and the alternative hypothesis in this record's Problem section was
wrong.** `declined` is not "never tested but presumably reachable": it is unreachable for every
contract-legal input, and the failing test is the proof rather than an inference from a 52-query sample.

**One nuance that keeps `CANNOT_ANSWER_REPLY` alive:** the constant is also the empty-completion
fallback at `respond.py:112`, inside `_answer_from_kb` — which runs on a KB **hit**. So the text can
still reach a customer, just never through the CM-4 branch.

**Consequence for the branch's status:** it is not merely dead, it is a **guard**. If it were removed,
a KB miss on that path would fall through to `_answer_from_kb(text, "")` with an empty `<kb>` block —
the model answering from nothing, which is exactly the hallucination CM-4 exists to prevent. That makes
"delete the dead branch" a materially different trade-off from "delete dead code", and is why the
decision is escalated rather than taken here.

**Status: resolved.** The decision was escalated to the human, who chose to **keep the guard** and align
the documentation (option B below). That is what T2–T5 implement. The alternative — deleting the branch
— was rejected because of the empty-KB fall-through described above; changing `unknown` to emit the
refusal was rejected as a behaviour change with no measured harm to fix.

## Acceptance criteria

1. ~~A test proves that a turn routed to the linear `respond` path with no KB content emits
   `CANNOT_ANSWER_REPLY` and escalates.~~ **Resolved by the second branch of this criterion.** The test
   was written, it failed, and this record reports CM-4 as genuinely unreachable — the assertion was not
   weakened. The guard it protects is now covered directly by `test_cm4_guard_refuses_an_undeclared_intent_with_no_kb`
   and its unreachability by `test_unknown_intent_never_reaches_the_cm4_refusal`.
2. No test name claims CM-4 coverage over a path CM-4's refusal does not serve.
3. The spec's CM-4 scenarios name the path each one governs, and the KB-intent escalation is recorded
   as specified behaviour (AO-8), not as a gap.
4. `tests/README.md` maps CM-4's "no reliable answer" to a test that actually emits the refusal.
5. Production source is unchanged: the diff touches the spec, two test files, and this record only.
6. The full backend suite is green.

## Checks

- `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/integration/test_chat_capture.py -q`
- `uv run pytest tests/ -q`
- `git status --short` / `git diff --check`

## Progress

- [x] Created this ODD record before the first source change.
- [x] Worktree created (`rapso worktree create cm4-linear-path-scope`); base verified as `95f27db7`.
      `infra/.env` copied into the worktree and `uv sync` run — this unit runs pytest, so unlike the
      previous web-only unit the backend venv IS required.
- [x] Graph Check (Step 1): `graphify query "CM-4 cannot answer reply linear respond path"` run over the
      chat area. Nodes consulted: `respond()` (`app/chat/nodes/respond.py:115`), the respond node
      description ("KB-grounded answers + unresolved logging (CM-4, CM-6)"),
      `test_cm4_kb_miss_cannot_answer_and_logs_unresolved()` (`tests/integration/test_chat_capture.py:217`
      — the graph itself surfaces the misnamed test, which is how the traceability problem was noticed),
      `test_triage_reply_duplication.py`, `session_scope()` (`app/db.py:27`).

## Size

Source and docs: **3 files, 98 insertions, 11 deletions** (`tests/integration/test_chat_capture.py`,
`openspec/specs/conversation-manager/spec.md`, `tests/README.md`), plus this record. No production
source changed, so the review surface is documentation and test coverage.

## Recovery

Resume with `mem_context`, then the project-scoped `mem_search` for this feature, then
`mem_get_observation` for the full document, then read this file.

## Next step

Implementation and verification are complete. Delivery (commit, push, PR) is the human's decision under
ordinary repository policy.

Deliberately NOT folded into this unit:

1. **The linear path's double reply.** `CANNOT_ANSWER_REPLY` followed by `HANDOFF_REPLY` on the linear
   path is real and customer-facing (`replies` accumulates and `_after_respond` routes the escalation to
   `handoff`, which appends its own reply). It is behaviour, not documentation, and it is unreachable
   today by the same argument that makes the guard unreachable — so fixing it would fix a path no input
   reaches. Recorded as D6.
2. **`settings.get_message` and the `messages.<key>` overrides (SS-5) are declared and unwired** —
   verified: no production caller exists. `CANNOT_ANSWER_REPLY` is hardcoded at `respond.py:147`, and
   the constant's other use (`respond.py:112`, the empty-completion fallback) is hardcoded too. This is
   the third declared-but-unconsumed mechanism, alongside `kb_scope` and `source_meta.category` (P10),
   and it is the only one that lies directly to an admin. Its own unit.
3. **The historical `openspec/changes/hito-1-setup-whatsapp/verify-report.md:938,940`** still names the
   old test. Left stale on purpose (D5): it records what was verified when Hito 1 closed.
