# ODD: complaint-trigger-coverage

## Objective

Leave the HH-3 complaint trigger exactly as it is, and make its **recall measurable** so the next person
who wants to narrow it has something to measure against — plus pin the one case the corpus flags as a
false positive, so it stays a decision instead of being "fixed" twice.

## Problem

A previous handoff filed this as a defect: *"the complaint trigger gives a false positive on the word —
'cual es el guion para responder un reclamo' is a question ABOUT handling complaints, `\breclamo\b`
matches it, and it escalates."* Measured against the labelled corpus, **the claim is true about the word
and wrong about the harm.**

### The measurement (run against the shipped pattern, not a copy)

`_COMPLAINT_PATTERN` and `_PERSONA_PATTERN` were imported from `app/chat/nodes/handoff_gate.py` and
applied to all 52 corpus queries in `scripts/kb_calibration_corpus.yaml`:

| | |
|---|---|
| queries that fire the complaint trigger | **1 of 52** |
| which one | `q-guion-reclamo` — "cual es el guion para responder un reclamo" |
| its `visible_to` | **`internal`** |
| its `relevant_doc_ids` | `guion-interno-reclamos` — *"Guion interno para reclamos de operadores… Uso interno"* |
| queries that fire the persona trigger | 0 |
| **real complaint cases in the corpus** | **0** |

### Three consequences

**1. The flagged query is not a customer question.** The corpus marks it `visible_to: internal`, and the
document that answers it is the operator script. It models a Lumat operator's question, not an upset
customer's.

**2. Its customer-chat outcome is identical with or without the trigger.** With the trigger: escalate
with reason `complaint`. Without it: classification runs, `kb.retrieve(audience=customer)` finds nothing
(the document is `internal`), and the turn escalates through handoff anyway — `research_triage`'s
bounded-retry miss, or the CM-4 guard. **The escalation is correct.** The trigger only reaches it
earlier.

**3. The only inaccuracy is the label, and nothing consumes it.** The case ends with
`escalate_reason: "complaint"` for what was a question about complaints. Verified across the repository:
`escalate_reason` appears **nowhere** in `app/panel/` or `web/src/`. It is written into the case bundle
(`app/services/cases.py:59,91`) and into the CM-5 summary context
(`app/chat/nodes/summary.py:54`). No routing, no priority, no queue. The cost is cosmetic.

### The asymmetry that decides it

**The trigger's recall cannot be measured with this corpus, because the corpus contains zero real
complaint cases.** Narrowing the pattern would therefore trade a measured cosmetic cost for an
**unmeasurable** risk: we would see the false positive drop and never see the upset customer we stopped
escalating. HH-3 requires escalating on *"complaint, warranty, or upset customer"* — it is deliberately
high-recall, and over-escalating costs a human reading a case while under-escalating costs an ignored
customer.

That asymmetry, not the false positive, is the finding worth acting on.

## Scope

**In:** the gate's recall instrument (real customer complaint phrasings that MUST trigger, and benign
messages that MUST NOT); a pinned test for the accepted question-about-complaints case with its
rationale; and — added after the measurement surfaced a recall hole — four literal phrases in
`_COMPLAINT_PHRASES` that close 3 of the 4 measured gaps.

**Out:** `_COMPLAINT_WORDS` (the noun/infinitive list stays untouched: the gap is closed with phrases
rather than bare conjugations, on purpose), the `_COMPLAINT_PATTERN` construction, the persona trigger,
the pre-LLM gate ordering, the case bundle, the summary, the corpus
(`scripts/kb_calibration_corpus.yaml` — it measures retrieval, not the gate, and editing it would
invalidate the frozen Layer 1 baselines recorded in `odd/tasks/kb-retrieval-calibration.md`), and any
canonical spec. HH-3 is already satisfied; nothing in the spec needs to change.

## Spec constraints (binding — do not violate)

- `openspec/specs/human-handoff/spec.md:38-40` — **HH-3**: escalate when the customer *"asks to talk to
  a person; bot fails to understand after two attempts; emergency or risk to people/property; complaint,
  warranty, or upset customer…"*. The current trigger over-satisfies it by design. No delta is written:
  the requirement describes when to escalate, and that has not changed.
- `app/chat/nodes/handoff_gate.py:50-51` — the module comment already states the settings-configurable
  knob is the upgrade path. Preserved, not touched.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-complaint-trigger-coverage`
- Branch: `odd/complaint-trigger-coverage`
- Base: `e0e109f2` — verified with `git merge-base HEAD origin/main` after creation, equal to
  `origin/main` at that moment (the merge of PR #288).
- Files:
  - `odd/tasks/complaint-trigger-coverage.md`
  - `tests/integration/test_handoff.py`
  - `app/chat/nodes/handoff_gate.py` — added to the authorized set after the measurement surfaced the
    recall gaps; the human approved closing them with phrases (D5).

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml` (`testing.strict_tdd: true`), runner `uv run pytest`.
  The added tests are **characterization tests** of behaviour that already exists: they cannot produce a
  RED without changing production code, and none is invented. Declared, not dressed up.
- Test DB for this worktree: `infra/test-db.sh up`; `eval "$(bash infra/test-db.sh env)"` before pytest.
  `infra/.env` copied in and `uv sync` run.
- Backend only: no `web/` file is touched, so the frontend suite is not part of the gate — declared.
- The corpus is NOT edited: adding complaint phrasings there would invalidate the frozen Layer 1
  baselines recorded in `odd/tasks/kb-retrieval-calibration.md` and
  `odd/tasks/kb-answer-fidelity.md`, and it measures retrieval rather than the gate.

## Decisions

- **D1 — The trigger stays.** The user chose to keep it and make it measurable over narrowing it. The
  rationale is the asymmetry above: measured cosmetic cost versus unmeasurable recall risk.
- **D2 — Recall becomes measurable in the test, not in the corpus.** A parametrized set of real customer
  complaint phrasings pins what the trigger MUST catch. This is what turns "we cannot measure recall"
  from a permanent excuse into a coverage gap someone can close.
- **D3 — The accepted false positive is pinned as a decision.** The
  `q-guion-reclamo` phrasing gets a test asserting it escalates, with the measurement and the reasoning
  in the docstring. Without it, the next reader sees a "bug" and "fixes" it; with it, they see the
  trade-off and the cost of the trade.
- **D4 — No spec delta.** HH-3 states when escalation is required; the trigger satisfies it. Documenting
  a deliberate over-reach belongs next to the code and the test that enforce it, not in a requirement
  that would then contradict the shipped behaviour.
- **D5 — Close the measured recall gap with PHRASES, not conjugations.** The vocabulary gap is
  morphological: the list has the nouns and the infinitive `devolver`, while customers write
  `devolvieron` / `devuelvan` / `estafaron`. The obvious fix — adding those as bare words — was rejected
  because `devuelven` also appears in the routine status question "¿cuándo me devuelven el calefont?",
  which would manufacture the very false positive this unit declined to chase. Literal phrases
  (`me estafaron`, `me devuelvan la plata`, `no me devolvieron`, `nadie responde`) hit the complaint
  constructions and leave the status question alone, and both halves are pinned by tests.

## Recall gaps found while building the instrument

Writing the recall set required checking candidate phrasings against the shipped pattern **before**
asserting them, which surfaced something the false-positive discussion had hidden: **the trigger knows
the noun forms and misses the verb conjugations customers actually write.**

Of 13 real complaint phrasings tested, 9 fire and **4 do not**:

| phrasing | fires? |
|---|---|
| "me devolvieron el equipo roto y nadie responde" | **no** |
| "me estafaron con el presupuesto" | **no** |
| "quiero que me devuelvan la plata" | **no** |
| "la boleta vino mal y necesito una correccion" | **no** |

The mechanism: `_COMPLAINT_WORDS` carries `reclamo`, `queja`, `devolucion`, `reembolso`, `estafa` — the
**nouns** — and the only verb in the list is the infinitive `devolver`, which a customer filing a
complaint essentially never types. They type `devolvieron`, `devuelvan`, `estafaron`.

**This is a recall hole measured on the side that matters**, and it is the exact opposite of the false
positive the handoff wanted to fix: the handoff wanted fewer escalations, and the evidence says the
trigger is more likely missing upset customers than over-catching calm ones.

**The trade-off is not purely additive**, which is why it was escalated instead of fixed on sight: bare
`devuelvan`/`devuelven` also appears in benign status questions ("¿cuándo me devuelven el calefont?"),
so adding the conjugations as words would create precisely the kind of false positive this unit decided
not to chase. Adding **phrases** instead ("me estafaron", "me devuelvan la plata", "no me devolvieron",
"nadie responde") targets the complaint constructions without catching the status question.

**Status: resolved.** El humano eligió cerrar el hueco con frases. Resultado medido: **3 de los 4
huecos cerrados, 0 mensajes benignos atrapados**, y el resultado del corpus sin cambios en 1 de 52.

El cuarto ("la boleta vino mal y necesito una correccion") quedó **decidido como no-objetivo el
2026-09-23** (unidad `complaint-gap-non-goal`, Engram #4793). Es un pedido de corrección de
facturación, no una queja, y la lista de HH-3 ("complaint, warranty, or upset customer") no lo cubre.
Dos motivos medidos para no plegarlo al trigger:

- El vocabulario del clasificador (`agent/personas/classify.md`) no tiene concepto de facturación —
  `postventa` es "garantías, devoluciones y cobertura de trabajos ya hechos" — así que el mensaje
  probablemente cae en `unknown`, donde `respond` no agrega nada en el turno 1 y el turno escala recién
  al segundo `unknown`: el cliente llega igual al humano, a lo sumo un mensaje después.
- El cliente tampoco queda varado: el menú del turno 1 ofrece "Postventa/Garantía", y cualquier intent
  con retrieval miss escala en el turno 1 con `escalate_reason: kb_miss`.

Agregar la frase escalaría de inmediato, pero etiquetaría un pedido de facturación como `complaint`, y
la diferencia de resultado nunca se midió. Ver `odd/tasks/complaint-gap-non-goal.md`.

## Tasks

- [x] **T1** — `test_gate_complaint_recall_across_real_customer_phrasings`: 12 real customer complaint
  phrasings, parametrized, each asserting `handoff_reason == "complaint"`. The first 9 were measured to
  fire before being asserted; the last 3 are the measured gaps this unit closes.
- [x] **T1b** — `test_gate_benign_messages_do_not_fire_the_complaint_trigger`: 6 benign messages that
  MUST NOT trigger, including "cuando me devuelven el calefont" and "me devolvieron el equipo arreglado
  y quedo bien". This is the precision half: what proves the phrasing did not widen the net.
- [x] **T2** — `test_gate_escalates_a_question_about_complaints_by_design`: pins the accepted case, with
  the measurement and the trade-off in the docstring so the next reader sees a decision and not a bug.
- [x] **T4** — `app/chat/nodes/handoff_gate.py`: four phrases added to `_COMPLAINT_PHRASES`. **RED
  observed first**: `uv run pytest -k "complaint_recall or benign"` → **3 failed** (exactly the three
  new phrasings) with the benign set green, against the unchanged source. **GREEN after the change**:
  the file collects **39 passed**.
- [x] **T5** — Verification, all observed:
  - `uv run pytest tests/integration/test_handoff.py -q` → **39 passed** (the file collected 30 before
    this unit; the change adds 19 items — 12 recall phrasings, 6 benign, 1 pinned case — derived from
    the diff and confirmed by collection).
  - `uv run pytest tests/` → **1145 passed, exit 0**, 2 warnings. The previous measurement on this
    branch was 1136, and the +9 matches the two parametrized sets added after it, so the delta is
    consistent rather than assumed.
  - Corpus re-measured after the change → **still exactly 1 of 52** queries firing the complaint
    trigger. The four new phrases introduced no corpus false positive.
  - `git diff --check` → clean. Frontend suite not run: no `web/` file is touched. Declared.

## Acceptance criteria

1. A parametrized set of real complaint phrasings asserts the trigger fires for each, and the set is
   named so a future narrowing fails loudly against it.
2. The `q-guion-reclamo` case is pinned as accepted, with the measured evidence and the asymmetry in the
   test itself — not only in this record.
3. The only production change is four phrases added to `_COMPLAINT_PHRASES`; nothing else in `app/`
   moves, `_COMPLAINT_WORDS` is untouched, and the corpus is untouched.
4. The full backend suite is green.

## Checks

- `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/integration/test_handoff.py -q`
- `uv run pytest tests/ -q`
- `git status --short` / `git diff --check`

## Progress

- [x] Created this ODD record before the first source change.
- [x] Worktree created (`rapso worktree create complaint-trigger-coverage`); base verified as `e0e109f2`.
      `infra/.env` copied in and `uv sync` run.
- [x] Measurement run before this record was written: `_COMPLAINT_PATTERN`/`_PERSONA_PATTERN` imported
      from the shipped module and applied to all 52 corpus queries. Result table above. Measurement
      entry points consulted: `app/chat/nodes/handoff_gate.py:52-77` (the words, phrases and pattern),
      `:84-96` (`evaluate_handoff` and its trigger order), `app/chat/nodes/orchestrate.py` (routing),
      `scripts/kb_calibration_corpus.yaml:283-292` (the internal operator document) and `:425-429` (the
      query),       `app/services/cases.py:59,91` and `app/chat/nodes/summary.py:54` (the only consumers of
      `escalate_reason`), and `openspec/specs/human-handoff/spec.md:38-40` (HH-3).
- [x] Recall-gap measurement and fix: 13 candidate complaint phrasings were checked against the shipped
      pattern **before** any was asserted, which found 4 that do not fire. Candidate phrases were then
      measured on both sides (4 complaint constructions and 6 benign messages) before being added, the
      tests were written to RED against the unchanged source, and the corpus was re-measured after the
      change. No step of that sequence was assumed.

## Recovery

Resume with `mem_context`, then the project-scoped `mem_search` for this feature, then
`mem_get_observation` for the full document, then read this file.

## Next step

T1 then T2.
