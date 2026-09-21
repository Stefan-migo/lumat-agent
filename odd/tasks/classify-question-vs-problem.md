# ODD: classify-question-vs-problem

**A question about an appliance must reach the knowledge base, not the visit-capture flow.**

## Objective

Give the classifier an informational intent so that asking *about* an appliance is answered from the
KB, while reporting a *problem* with one keeps starting the visit capture. Today both land in the
same intent and both start capture.

## Problem

Found and measured by `odd/kb-answer-fidelity.md` (F4).

The routing is deliberate, not a bug. `openspec/changes/hito-1-setup-whatsapp/design.md:95-100` splits
`route` into a capture sub-flow and KB retrieval, and `CAPTURE_INTENTS = {"calefont", "caldera",
"calefaccion", "solicitar_visita"}` (`app/chat/nodes/orchestrate.py:32`) sends appliance messages to
capture on purpose: someone who mentions an appliance probably has a problem, so collect the visit
lead.

The defect is the **intent vocabulary**, which is too coarse. `calefont` covers both *"contame de
calefonts"* and *"mi calefont está roto"*. Measured on the real path: **14 of 30** answerable queries
started the capture flow, and the KB had chunks for most of them.

| query | classified | result | correct? |
|---|---|---|---|
| `que tipos de calefont instalan` | calefont | capture → "¿Cuál es tu nombre?" | ✗ |
| `cada cuanto tiempo se le hace mantencion` | calefont | capture | ✗ |
| `instalan calefaccion central` | calefaccion | capture | ✗ |
| `hacen instalacion de estufa a gas` | calefaccion | capture | ✗ |
| `instalacion cocina a gas` | solicitar_visita | capture | ✗ |
| `mi calefont no enciende` | calefont | capture | ✓ |
| `el calefon esta perdiendo agua` | calefont | capture | ✓ |
| `como pido una visita tecnica` | solicitar_visita | capture | ✓ |

The informational rows are questions the KB can answer — `catalogo-calefont`, `procedimientos`,
`tarifas` are all in the corpus. The customer gets a name prompt instead.

## Why now

It is the largest single remaining cause of answerable questions not being answered, and it is the
one the previous units kept running into: after the scope fix and the emergency-marker fix, 14 of the
remaining 24 unanswered answerable queries are capture, and 5 of those are plainly informational.

## Scope

**In:** `agent/personas/classify.md` (the intent rule), `app/services/prompts.py` (the frozen
fallback literal, which AC-3 requires to stay byte-identical to the file),
`app/chat/nodes/orchestrate.py` (`RETRIEVAL_INTENTS`), `tests/unit/test_routing_table.py`,
`tests/integration/test_chat_intent.py` (its local classifier mock, so one integration test can drive
the routing end to end), and this record.

**Discovered during implementation:** the classifier prompt exists twice — the `agent/*.md` file and
the `FALLBACKS` literal in `app/services/prompts.py:50-65` — and `test_fallbacks_equal_agent_files`
(AC-3) asserts they are byte-identical. Editing only the file fails that guard loudly, which is the
right behaviour; both are updated here.

**Out (explicitly):**

- **The capture flow (CM-2).** Untouched. The fields, the order, the skip handling and the completion
  reply are correct; this unit changes *who enters* the flow, not the flow.
- **`CAPTURE_INTENTS` membership.** The four appliance intents keep their meaning for problem
  reports and explicit visit requests. Only the informational case moves (D4).
- **The routing table shape (AO-3).** `_dispatch` keeps its `(intent, flags) -> next_step` contract;
  one more intent maps to an existing destination.
- **The classifier's model and prompt structure.** The SH-4 input-as-data shape, the JSON contract
  and the injection rules are unchanged; only the intent list and its disambiguation rule change.
- **CM-3's spec.** It requires classification and a `classified` activity; it does **not** enumerate
  intents, so no spec delta is needed.

## Spec constraints (binding — do not violate)

- `openspec/specs/conversation-manager/spec.md` — **CM-3** (intent and case classification) and
  **CM-2** (progressive capture). CM-3's requirement is unchanged and no vocabulary is specified;
  CM-2's flow is untouched.
- `openspec/specs/agent-orchestration/spec.md` — **AO-3** (deterministic orchestrator dispatch). The
  dispatch stays pure, deterministic and LLM-free.
- `openspec/specs/knowledge-base/spec.md` — **KB-2**. The informational intent reaches the same
  retrieval the `valores`/`postventa` intents already use.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-classify-question-vs-problem`
- Branch: `odd/classify-question-vs-problem`
- Base: `53bbe320` (= `origin/main`; PRs #280 and #281 are open and independent — they touch
  `app/chat/graph.py` and `app/services/emergency.py`, this unit touches the classifier prompt and
  the routing table). Verified with `git merge-base HEAD origin/main` before writing this record.
- Files:
  - `odd/tasks/classify-question-vs-problem.md`
  - `agent/personas/classify.md`
  - `app/services/prompts.py`
  - `app/chat/nodes/orchestrate.py`
  - `tests/unit/test_routing_table.py`
  - `tests/integration/test_chat_intent.py`

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml` (`testing.strict_tdd: true`); runner `uv run pytest`.
- Test DB: `eval "$(bash infra/test-db.sh env)"` is required before pytest, and a fresh test database
  needs `bash db/migrate.sh` first.
- A fresh worktree has no `.venv`: `uv sync` before anything else.
- Known worktree artifact: `rapso worktree create` leaves `.opencode/tools/package-lock.json`
  untracked. Declare it to the review preflight, never commit it.
- `agent/personas/classify.md` is loaded by the classifier on every turn; a malformed edit degrades
  every classification. The file is a single line and must stay one.
- No commit, push, or PR from a delegated phase unless the orchestrator authorizes it.

## Decisions

- **D1 — A new `consulta` intent, not a stretched `valores`.** The cheaper option is to tell the
  classifier that informational questions are `valores`. It is rejected: `valores` means prices, and
  the intent is written to the case as its `service`
  (`app/chat/nodes/classify_intent.py:104-108`), so *"que tipos de calefont instalan"* would be
  recorded as a price case. It also blurs the boundary with `postventa`. A dedicated informational
  intent keeps each label's meaning and the case record honest.

- **D2 — The prompt rule separates ASK from REPORT.** The appliance intents are for a **reported
  problem**; `solicitar_visita` is for an **explicit visit request**; `consulta` is for anything
  informational the KB can answer — services, procedures, coverage, hours, characteristics. Without
  the second half of that rule the classifier has nowhere to put a question, which is exactly how it
  ended up answering questions with the capture flow.

- **D3 — The classifier's real accuracy is MEASURED, not asserted.** The suite's classifier is the
  keyword mock in `tests/integration/conftest.py:117-141`, which never reads the prompt — and it
  encodes the same coarseness (it checks `calefont` before `cuanto`). So the suite can prove the
  **routing** of the new intent, and only the fidelity harness can measure whether the real
  classifier now separates questions from problem reports. Both are reported; neither is claimed as
  the other.

- **D4 — `CAPTURE_INTENTS` is not modified.** Removing an appliance intent from capture would send
  problem reports to the KB, where retrieval would likely hit *something* and answer a broken
  appliance with a catalogue page. The appliance intents keep their meaning; only the informational
  case changes destination.

## Tasks

- [x] **T1** — `odd/tasks/classify-question-vs-problem.md` (this record).
- [x] **T2** — RED: the `consulta -> research_triage` routing case and the integration test failed
      against the unfixed routing (`active_sub_agent` was `None`).
- [x] **T3** — `app/chat/nodes/orchestrate.py` (`consulta` in `RETRIEVAL_INTENTS`),
      `agent/personas/classify.md` and the matching `FALLBACKS` literal in `app/services/prompts.py`.
- [x] **T4** — GREEN: routing, prompt-identity and full suites pass.
- [x] **T5** — Re-ran the sibling fidelity harness and measured the real classifier.

## Findings

### This change also closes F5 (`unknown` answerable queries)

`odd/kb-answer-fidelity.md` recorded F5 as a separate defect: four answerable queries
(`atienden en maipu`, `cuales son las comunas donde trabajan`, `en cuanto tiempo responden un
mensaje`, `cuales son los horarios de atencion`) were classified `unknown` and received only the
CM-1 menu. They were never a separate defect — they were the same coarse vocabulary, with nowhere
for a question to go.

Measured on the same base, before and after:

| | unknown total | by class |
|---|---|---|
| before | 19 | 2 answerable, 5 near_miss, 12 out_of_domain |
| after | **12** | **12 out_of_domain** |

Three of the four are now **answered** from the KB; the fourth (`atienden en maipu`) reaches the KB
and misses the gate with `chunks=0`, which is a **retrieval** problem — the title-phrased query
against the `comunas` document — and belongs to F7 (titles are not embedded), not to classification.

The 12 remaining `unknown` are genuinely out of domain (an empanada recipe, the dollar rate, a
football channel). Each receives the menu only, with no fabrication: the correct outcome.

**No further unit is needed for F5.**

### The real classifier separates questions from problem reports

Same corpus, same threshold, same model, real provider, 52 queries. The comparison is against the
**same base** (`53bbe320` plus the graph fix) so the delta is this unit's.

| answerable (n=30) | without this change | with it |
|---|---|---|
| `capture_started` | **11** | **3** |
| `answered` | 5 | **14** |
| intent `consulta` | 0 | **13** |
| intent `calefont` (problem reports) | 6 | 3 |
| intent `solicitar_visita` | 4 | 0 |

The two plainly informational queries that could be measured cleanly are now answered from the KB:
`que tipos de calefont instalan` and `instalan calefaccion central`, both with 5 chunks retrieved.

### The control direction holds

The three problem reports in the corpus still start the capture flow, with the appliance intent
intact:

| query | outcome | intent |
|---|---|---|
| `mi calefont no enciende` | capture_started | calefont |
| `el calefon esta perdiendo agua` | capture_started | calefont |
| `mi calefon hace un ruido raro` | capture_started | calefont |

D4 did its job: no reported problem was routed to the KB.

### The near_miss "answered" count went up, and every one is a prose refusal

`near_miss` answered moved 2 → 6. Sending more questions to the KB naturally sends more *unanswerable*
questions there too, so this is the risk direction of the change and it was read in full. **All six
decline in prose and redirect to what the company actually does**, with `ungrounded: []`:

- `reparan termos electricos` → *"No puedo confirmar eso con la información que tengo. Lo que aparece
  en nuestros registros es la instalación y reparación de **artefactos a gas**…"*
- `hacen capacitacion para gasfiteres` → *"No puedo responder eso con seguridad: en la información que
  manejo no aparece ningún servicio de capacitación para gasfiteres. Lo que sí ofrecemos es…"*
- `arriendan herramientas de gasfiteria` → *"…no menciona arriendo de herramientas."*
- `cuanto sale instalar un tanque de agua` → *"No puedo darte un valor: no manejo precios ni
  cotizaciones…"*

Not one fabricates a service or a price. This is the CM-4 prompt contract working, and it is a better
outcome than the previous behaviour, which asked the customer for their name. It also sharpens the
classifier caveat recorded in `odd/kb-answer-fidelity.md`: `answered` counts prose refusals, so
`answered_rate` is an upper bound on real answers.

### Honest limits of this measurement

- **The corpus has no explicit visit-request query**, so the "a real visit request still captures"
  direction is **not measured here** — only asserted by the suite's control test
  (`test_route_capture_path_for_equipment_intents`) and the mock's `visita` branch. The residual risk
  is that the new rule makes the classifier too conservative and a genuine request lands on
  `consulta`. Closing it needs visit-request queries added to the corpus, which is a follow-up, not a
  claim this unit can make.
- **This base predates PRs #280 and #281.** `emergency_weak_hit` shows 6 in this run because the
  bare-`gas` marker is still present here, and two of the five informational queries
  (`instalacion cocina a gas`, `hacen instalacion de estufa a gas`) are blocked by that gate rather
  than by the routing this unit changed. With #281 merged they reach classification as well.
- **One borderline case:** `como pido una visita tecnica` is now `consulta` and handed off, because
  the corpus does not cover the request process. D2 says a question *about* the process is
  informational, so this is the designed behaviour; whether the KB should cover it is a content
  question.

## Acceptance criteria — result

1. RED observed before T3 (routing case + integration test), GREEN after.
2. `uv run pytest tests/unit/test_routing_table.py tests/integration/test_chat_intent.py -q` →
   **33 passed**; `uv run pytest tests/unit/test_prompts.py -q` → **30 passed** (the AC-3
   byte-identity guard between the `.md` file and the `FALLBACKS` literal).
3. `uv run pytest tests/` → **exit 0, 100%**, no failures or errors.
4. Measured above, both directions, including the misrouting risk and its honest limit.
5. `git diff --name-only` shows only the authorized files plus the known untracked
   `.opencode/tools/package-lock.json`.

## Applicable checks

- `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/unit/test_routing_table.py -q`
- `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/ -q`
- `git diff --name-only` → only the authorized files
- `git diff --check` → no whitespace errors

## Graph Check (Step 1 of the 5-Step Gate)

Consulted before writing: `orchestrate._dispatch` and the two intent sets
(`app/chat/nodes/orchestrate.py:31-88`), `classify_intent` and its `_store_classification` write to
the case (`app/chat/nodes/classify_intent.py:104-116,203-222`), the classifier prompt
(`agent/personas/classify.md`) and its render slot (`agent/prompts/classify.md`), the mocked
classifier (`tests/integration/conftest.py:117-141`), the routing-table test
(`tests/unit/test_routing_table.py`), and the design's routing split
(`openspec/changes/hito-1-setup-whatsapp/design.md:95-100`).
