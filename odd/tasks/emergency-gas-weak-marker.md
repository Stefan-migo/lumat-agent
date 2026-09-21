# ODD: emergency-gas-weak-marker

**Stop bare `gas` from escalating routine commercial questions to a human.**

## Objective

Remove `gas\b` from the weak emergency markers, so that mentioning the word the business is named
after stops routing a customer to a human before classification and before retrieval — without
losing the phrasings that actually signal a gas risk.

## Problem

Found and measured by `odd/kb-answer-fidelity.md` (F3).

`app/services/emergency.py` classifies every inbound message before any LLM call. A **strong** hit
runs the EM-3 safety protocol; a **weak** hit escalates to a human (EM-5). `_WEAK_MARKERS` contains
`r"gas\b"`, so **any** message mentioning gas escalates — before the intent is classified and before
the KB is consulted.

Measured on the real path: **6 of 52** queries, every one of them answerable, none of them an
emergency.

| query | outcome |
|---|---|
| `instalacion cocina a gas` | handoff |
| `hacen instalacion de estufa a gas` | handoff |
| `necesito regularizar la instalacion de gas ante la sec` | handoff |
| `que valor tiene la mantencion de una estufa a gas` | handoff |
| `cuanto cobran por revisar el medidor de gas natural` | handoff |
| `huelo gas en la cocina que hago` | handoff |

For a **gasfitería**, "gas" is the business's own name. It appears in the majority of commercial
questions, so the marker fires on the normal case and not on the exception.

### The suite pins the false positive as correct

`tests/integration/test_emergency.py:101` asserts that `"no me llega gas al calefont"` is a **weak**
hit. That is a routine service complaint — gas not reaching the water heater is a job — encoded as
"must escalate to a human". The benign examples in the same file (`:115-120`) carefully avoid the
word gas, so nothing in the suite ever measured the product's real input distribution. This is the
same failure mode as the KB scope defect fixed in `odd/kb-triage-scope.md`.

### The diagnosis

Every other weak marker describes a **perception**:

```python
"huele raro", "huele feo", "olor raro", "olor extraño", "olor a quemado", "a quemado", "olorcito"
```

`gas\b` is the only one that describes a **subject**. A gas leak is perceived by smell or by a leak,
and both are already **strong** keywords: `olor a gas`, `huele a gas`, `fuga`, `fuga de gas`,
`explosión`, `monóxido`, `intoxicación`. Bare `gas`, with no smell, no leak and no explosion,
carries no risk information — it carries the topic.

## Scope

**In:** `app/services/emergency.py` (the marker, its comment, and the module docstring that names
bare `gas` as the example of a weak hit), `tests/integration/test_emergency.py`, and this record.

**Out (explicitly):**

- **The strong keyword list.** Unchanged. Adding a keyword there runs the **full EM-3 protocol** —
  safety instructions, emergency contacts, technician notification, case flagged, state to human —
  which is a far larger action than the weak handoff. Expanding it is a separate decision for the
  client, not a side effect of this one (D3).
- **The benign-qualifier logic for strong stems.** `fuga de agua` staying benign while
  `fuga de gas` is strong is correct and untouched.
- **The settings knob.** The strong list is already panel-configurable (SS-2); no new mechanism.
- **The historical design record.** `openspec/changes/hito-1-setup-whatsapp/design.md:107` records
  the original design decision ("weak hit (e.g. `huele raro`, `gas` stem) → handoff"). It is a
  shipped change's record and is left as written; this record supersedes it (D4).
- The fidelity corpus and its numbers. The measurement is re-run, not edited.

## Spec constraints (binding — do not violate)

- `openspec/specs/emergency-detection/spec.md` — **EM-5** ("Conservative Default"): ambiguous or
  possibly-risky messages MUST default to escalation, never silent resolution. The requirement does
  not name bare `gas` and does not enumerate markers, so **no spec delta is needed**: the mechanism
  and the conservative default are unchanged. What changes is which inputs count as ambiguous, and
  the residual gap is documented rather than hidden (D2).
- **EM-1** (deterministic keyword detection) and **EM-3** (safety instructions) are untouched.
- **CM-3** and **KB-2**: the intent that now reaches classification and retrieval is the point of the
  change, not a violation of it.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-emergency-gas-weak-marker`
- Branch: `odd/emergency-gas-weak-marker`
- Base: `53bbe320` (= `origin/main`; PR #280 is open and independent — it touches
  `app/chat/graph.py`, this unit touches `app/services/emergency.py`). Verified with
  `git merge-base HEAD origin/main` before writing this record.
- Files:
  - `odd/tasks/emergency-gas-weak-marker.md`
  - `app/services/emergency.py`
  - `tests/integration/test_emergency.py`

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml` (`testing.strict_tdd: true`); runner `uv run pytest`.
- Test DB: `eval "$(bash infra/test-db.sh env)"` is required before pytest, and a fresh test database
  needs `bash db/migrate.sh` first.
- A fresh worktree has no `.venv`: `uv sync` before anything else.
- Known worktree artifact: `rapso worktree create` leaves `.opencode/tools/package-lock.json`
  untracked. Declare it to the review preflight, never commit it.
- This is the **safety path**. Every removed signal must be accounted for in a test, and the residual
  gap must be pinned loudly rather than left silent.
- No commit, push, or PR from a delegated phase unless the orchestrator authorizes it.

## Decisions

- **D1 — Remove `gas\b`; do not narrow it to risk phrasings.** Narrowing (e.g. matching only
  `hay|siento|sale gas`) would keep a signal that duplicates the strong list for the realistic
  phrasings, at the cost of a new regex with its own tests and its own drift. The risk information
  lives in perception words, and those are already strong. The clean removal also deletes the whole
  false-positive class instead of shrinking it.

- **D2 — The residual gap is pinned by a test, not left silent.** Removing the marker narrows
  coverage: a leak phrased with `gas` and a verb, and neither `fuga` nor `olor` — `"se escapa el
  gas"`, `"me está saliendo gas"` — is no longer detected. That is a real reduction in EM-5's net.
  The mitigation is that the strong list is panel-configurable (SS-2), so the client can add those
  phrasings without a code change. A test asserts the gap explicitly, so it is a known boundary that
  a future change must update deliberately rather than an accident nobody recorded.

- **D3 — No new strong keywords in this unit.** A strong hit runs the full EM-3 protocol, not a
  handoff. Widening what triggers the protocol is a client-facing safety decision with a different
  blast radius, and it belongs to its own unit with the client in the room.

- **D4 — The historical design record is left as written.**
  `openspec/changes/hito-1-setup-whatsapp/design.md:107` documents the original decision. Rewriting a
  shipped change's record would falsify the trail; this record is the supersession.

## Tasks

- [x] **T1** — `odd/tasks/emergency-gas-weak-marker.md` (this record).
- [x] **T2** — RED: seven new assertions failed against the unfixed marker — the five commercial
      gas phrasings in the no-hit list and the two residual-gap phrasings.
- [x] **T3** — `app/services/emergency.py`: the marker removed, and both docstrings that named bare
      `gas` as the weak example corrected.
- [x] **T4** — GREEN: the emergency suite, the focused set, and the full suite pass.
- [x] **T5** — Re-ran the sibling fidelity harness. `emergency_weak_hit` went **6 → 0**.

## Findings

### The false-positive class is gone, measured on the real path

Same corpus, same threshold, same model, real provider, all 52 queries.

| | before | after |
|---|---|---|
| `emergency_weak_hit` handoffs | **6** | **0** |
| answerable queries answered | 5 | **6** |
| answerable queries handed off | 10 | **6** |

The five queries the marker used to intercept now reach classification and retrieval:

| query | now | intent |
|---|---|---|
| `que valor tiene la mantencion de una estufa a gas` | **answered** (4 chunks) | valores |
| `cuanto cobran por revisar el medidor de gas natural` | **answered** (4 chunks) | valores |
| `instalacion cocina a gas` | capture_started | solicitar_visita |
| `necesito regularizar la instalacion de gas ante la sec` | capture_started | solicitar_visita |
| `hacen instalacion de estufa a gas` | capture_started | calefaccion |

The three that still do not answer are now blocked by the **capture routing** (F4, unit P3), not by
the safety gate. That is a different defect with a different owner, and this unit's boundary ends
here.

### The safety property held, and the near_miss rows are the proof

`ungrounded: []` on all 52 queries, and the two `near_miss` turns that returned free text are
**refusals in prose**, not fabrications:

- `cuanto cobran por revisar el medidor de gas natural` →
  *"No tengo información sobre un servicio de revisión de medidor de gas natural, así que no puedo
  confirmarte si lo realizamos ni cuánto costaría."*
- `cuanto sale instalar un tanque de agua` →
  *"No puedo responderte eso con seguridad: no tengo información sobre precios ni sobre instalación
  de tanques de agua en los datos que manejo."*

Both are the CM-4 prompt contract working through the model. Removing the safety-gate intercept
therefore did **not** produce an invented answer — the next layer caught it, in prose, with no
ungrounded numbers. This is the honest answer to the risk the change was trading against.

It also sharpens the classifier caveat recorded in `odd/kb-answer-fidelity.md`: the `answered`
bucket contains both grounded answers and free-text refusals, so `answered_rate` is an upper bound
on real answers and separating them needs the `--judge` pass or a human.

### Variance, stated rather than smoothed

`emergencia` handoffs moved 2 → 3 and `near_miss` answered 1 → 2 between the two runs. Both are
intent-classification variance in the same 52 queries, not effects of this change: it touches only
which messages reach classification, not how they are classified. The number this unit owns is
`emergency_weak_hit`, and it moved 6 → 0 deterministically.

## Acceptance criteria — result

1. RED observed before T3 (7 failures), GREEN after.
2. The realistic risk phrasings still escalate: `siento olor a gas en la cocina`, `huele a gas en el
   calefont`, `hay una fuga de gas en el calefont` and `parece intoxicación por gas` remain **strong**;
   `huele raro el calefont` and `hay un olor a quemado en el patio` remain **weak**. Pinned by
   `EMERGENCY_SENTENCES` and `test_weak_hit_escalates_not_ignored`.
3. `uv run pytest tests/integration/test_emergency.py tests/functional/ -q` → **278 passed** across
   the focused set.
4. `uv run pytest tests/` → **exit 0, 100%**, no failures or errors.
5. `git diff --name-only` shows only the authorized files plus the known untracked
   `.opencode/tools/package-lock.json`.
6. The fidelity harness reports `emergency_weak_hit` **6 → 0**, with `ungrounded: []` still holding
   across all 52 queries.

## Applicable checks

- `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/integration/test_emergency.py -q`
- `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/ -q`
- `git diff --name-only` → only the authorized files
- `git diff --check` → no whitespace errors

## Graph Check (Step 1 of the 5-Step Gate)

Consulted before writing: `classify_emergency` and the `_WEAK_PATTERN` compile
(`app/services/emergency.py`), `compile_keywords` and the strong-list benign-qualifier logic,
`emergency_gate` and its `escalate_reason` labelling (`app/chat/nodes/emergency_gate.py`), the
graph's routing of weak hits to `handoff` (`app/chat/graph.py:137-143`), and the emergency
integration suite (`tests/integration/test_emergency.py`). `graphify query "knowledge base retrieval
and calibration"` (depth 2, 407 nodes) previously confirmed the emergency gate runs before
classification and retrieval, with no other consumer of the weak markers.
