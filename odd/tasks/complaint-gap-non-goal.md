# ODD: complaint-gap-non-goal

**Close the fourth complaint-trigger recall gap as a decided non-goal, not an open item.**

## Objective

Turn the last open item of `odd/tasks/complaint-trigger-coverage.md` — the fourth measured recall
gap, `"la boleta vino mal y necesito una correccion"` — into a decided non-goal, so the repository
stops presenting it as "open on purpose" and a future reader sees a decision with its evidence
instead of a pending task. Ratify the unit's accepted false positive too; it was already decided and
needs no code.

## Problem

The unit closed 3 of its 4 measured recall gaps and left the fourth open on purpose, with the
rationale in the record and repeated as a comment in `tests/integration/test_handoff.py:229-232`.
"Open on purpose" is honest while the decision is pending; once the decision is made it is a stale
claim, and it reads as a TODO. No code changes either way: the phrase does not fire today, and the
decision is to leave it that way.

## Decisions

- **D1 — The accepted false positive is RATIFIED, not reopened.** `"cual es el guion para responder
  un reclamo"` keeps escalating with reason `complaint`. It is the language of Lumat's operator
  script (`visible_to: internal`), its customer-chat outcome is the same handoff with or without the
  trigger (the internal document is invisible to customer retrieval, so the turn escalates as
  `kb_miss`), and only the label differs. Narrowing the pattern would trade that measured cosmetic
  cost for an unmeasurable recall risk. The unit already pinned it with
  `test_gate_escalates_a_question_about_complaints_by_design` (D1/D3 of that record).
  - Honest caveat carried from that record: `escalate_reason` is not entirely inert — nothing in
    `app/panel/` or `web/src/` consumes it, but it reaches the case bundle
    (`app/services/cases.py:91`) and the CM-5 summary prompt (`app/services/prompts.py:91`). Still
    no routing and no priority.

- **D2 — The fourth gap is a NON-GOAL.** `"la boleta vino mal y necesito una correccion"` is a
  billing-correction request, not "complaint, warranty, or upset customer" (HH-3), and adding the
  phrase would label a billing request `complaint`. The customer is not stranded without it: the
  turn-1 menu offers "Postventa/Garantia", and any intent with a retrieval miss escalates on turn 1
  with `escalate_reason: kb_miss`.

## Evidence (measured against `origin/main`, not recited)

The shipped pattern was imported (`app.chat.nodes.handoff_gate._COMPLAINT_PATTERN`) and applied to
the phrases:

| phrasing | fires? |
|---|---|
| `cual es el guion para responder un reclamo` (accepted FP) | **yes** |
| `la boleta vino mal y necesito una correccion` (this gap) | no |
| `me devolvieron el equipo roto y nadie responde` | yes |
| `me estafaron con el presupuesto` | yes |
| `quiero que me devuelvan la plata` | yes |
| `la boleta vino mal`, `me cobraron de mas en la boleta`, `el monto de la boleta esta mal`, `necesito corregir la factura` | no |
| `cuando me devuelven el calefont`, `cuanto sale la mantencion` (benign) | no |

Routing read from the code, not inferred from a run:

- `agent/personas/classify.md` has no billing concept (`postventa` = "garantias, devoluciones y
  cobertura de trabajos ya hechos"), so the billing message most likely classifies `unknown`.
- `app/chat/nodes/respond.py:122-131`: `unknown` on turn <= 1 adds no reply; turn > 1 returns the
  clarification; escalation happens on the second `unknown` (`unknown_intent_twice`). Any other
  intent with a retrieval miss escalates on turn 1 (`respond.py:152-163`).

**What is NOT measured**: the actual classifier output for the billing phrase (it needs the
provider). The "one extra exchange" cost is inferred from the vocabulary, not observed. The decision
does not depend on it: the gap is closed on HH-3's scope, and the phrase must not fire either way.

## Scope

**In:** `odd/tasks/complaint-trigger-coverage.md` (the "stays open on purpose" line becomes the
decided non-goal), `tests/integration/test_handoff.py` (the comment at `:229-232`), and this record.

**Out (explicitly):** any change to `app/chat/nodes/handoff_gate.py`, the trigger pattern, the
corpus, or any canonical spec. No behavior changes. A test that pins the non-firing (symmetric to
the accepted false positive's test) is deliberately NOT added here: this is a docs-only close, and
the decision is recorded, not made executable.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-complaint-gap-non-goal`
- Branch: `odd/complaint-gap-non-goal`
- Base: `9b4c464f` (= `origin/main` at branch time; includes PR #319 and release v2026.09.5)
- Files:
  - `odd/tasks/complaint-gap-non-goal.md` (this record)
  - `odd/tasks/complaint-trigger-coverage.md`
  - `tests/integration/test_handoff.py`

## Constraints

- Docs and comment only. If `git diff` shows anything other than comment/doc text, the change is
  wrong.
- Strict TDD does not apply: there is no behavior to drive. The applicable check is that the touched
  test module still passes and the diff is comment-only.

## Tasks

- [x] **T1** — this record.
- [x] **T2** — update `odd/tasks/complaint-trigger-coverage.md` (fourth gap: open -> decided
      non-goal).
- [x] **T3** — update the comment in `tests/integration/test_handoff.py`.
- [x] **T4** — verify: the touched test module, `git diff` is comment-only, `git diff --check`.

## Applicable checks

- `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/integration/test_handoff.py -q`
- `git diff` -> only comment/doc text (no executable line changed)
- `git diff --check` -> clean

## Graph Check (Step 1 of the 5-Step Gate)

- `graphify query "handoff gate complaint trigger and escalation reason"` -> `handoff_gate.py`
  (community `models.py`), `handoff()` (`app/chat/nodes/handoff.py:48`), the record
  `odd/tasks/complaint-trigger-coverage.md`, and `escalation` (`agent/personas/escalation.md`).
- The graph confirms the trigger's only code surface is `handoff_gate.py`; this unit does not touch
  it.

## Progress

- [x] Created this record before touching any file.
- RED/GREEN does not apply: docs/comment only, no behavior to drive. Observed instead:
  - `uv run pytest tests/integration/test_handoff.py -q` -> **39 passed, exit 0**.
  - `git diff -- tests/integration/test_handoff.py` -> every changed line is a comment (checked
    with a filter over the diff; no executable line changed).
  - `git diff --check` -> clean.

## Recovery

Resume with `mem_context`, then the project-scoped `mem_search` for `complaint-gap-non-goal`, then
`mem_get_observation` for the full record, then read this file.
