# ODD: kb-answer-fidelity

**Layer 2 of the KB measurement work: the answer, not the retrieval.**

## Objective

Measure whether the KB RAG's **answer** is faithful to the chunk it was given, and whether the
system declines or hands off when the corpus does not cover the question. Layer 1
(`odd/tasks/kb-retrieval-calibration.md`) measures what retrieval *returns*; nothing measures what
the model *does* with it.

## Problem

The retrieval layer is measured and frozen. The answer layer has **zero** measurement, and this is
structural, not an oversight:

- The retrieval harness stops at retrieval. It never calls the LLM.
- `respond._answer_from_kb` (`app/chat/nodes/respond.py:89-112`) is the only place the customer-facing
  free text is produced, and **no test in the repo exercises it against a real provider**. Every
  integration and functional test intercepts the call with `respx`
  (`tests/integration/conftest.py:144-195`, `os.environ["DEEPSEEK_API_KEY"] = "sk-test"` at
  `tests/integration/conftest.py:49-52`). The suite pins the plumbing around the model and never the
  model's output.
- Consequently the expensive failure class is invisible to the entire suite: the bot stating a price,
  a plazo, or a guarantee that the retrieved chunk does not contain.

This is not hypothetical. Layer 1 measured that at the shipped gate (`min_sim=0.50`) **3 of 10
`near_miss` queries pass it** (`odd/tasks/kb-min-sim.md:34`, `odd/tasks/kb-retrieval-calibration.md`
F3). Those three queries reach the model holding a chunk that does not answer them. What the model
does next has never been observed.

## Why now

The user's open question is exactly this one: retrieval "looks functional" in the panel, but its
quality is unmeasured at the answer level. Layer 1 answered "does it bring the right chunk". Nobody
has answered "does it stay faithful to that chunk". That is the remaining half of the RAG's quality,
and it is the half the client actually experiences.

## Scope

**In:** the fidelity harness script; its model-free scoring core; the model-free unit tests; this
record. The corpus is **reused verbatim**, not extended.

**Out (explicitly):**

- **No production file may change.** `app/`, `web/`, `db/`, `agent/`, `openspec/` stay untouched —
  same guard as the retrieval slice. In particular: no seam added to expose `escalate`, no change to
  `min_sim`, `top_k`, the ranking, the chunking, the prompts, or `respond.py`.
- **The panel assistant path is out of scope.** It has no grounding contract and no deterministic
  no-coverage branch (`agent/personas/assistant.md`, `agent/prompts/assistant_respond.md`,
  `app/chat/assistant/tools/registry.py:212-215`). That is a separate front with its own decision.
- The LLM judge is **opt-in**, never a default.
- No retuning. This unit produces a measurement, not a threshold.

## Spec constraints (binding — do not violate)

- `openspec/specs/knowledge-base/spec.md` — **KB-2** (retrieval with configured top-k and threshold)
  and **KB-5** (document audience). Both are exercised, neither is changed.
- **CM-4 / CM-6** (`app/chat/nodes/respond.py:1`, `:139-150`) are the refusal and unresolved-log
  contracts this unit measures the *observable behaviour* of. It does not modify them.
- **AO-7** (`agent/registry.yaml`) — the topic `scope` axis. The research-triage path passes a scope;
  the harness must reproduce the same arguments the production path uses, not invent its own.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-kb-answer-fidelity`
- Branch: `odd/kb-answer-fidelity`
- Base: `153c3275` (= `origin/main`, verified with `git log -1 --format=%h origin/main`)
- Files:
  - `odd/tasks/kb-answer-fidelity.md`
  - `scripts/kb_fidelity.py`
  - `tests/unit/test_kb_fidelity.py`

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml` (`testing.strict_tdd: true`); runner `uv run pytest`.
  Observe RED before each artifact; never invent RED evidence.
- Test DB: `eval "$(bash infra/test-db.sh env)"` is **required** before any DB work, or migrations
  connect as the unprivileged `app` role and fail with a misleading password error (pre-existing
  harness quirk).
- **The harness MUST NOT run inside `pytest tests/`.** It calls a real paid provider and is not
  deterministic. Only the model-free parts are suite-covered; the real run is an explicit manual
  invocation and its output is recorded by hand — the same boundary as
  `tests/unit/test_kb_calibration.py:1-15`.
- Artifacts in English. The corpus bodies and query texts stay Chilean Spanish: they are the
  product's real input distribution, not a documentation language choice.
- Known worktree artifact: `rapso worktree create` leaves `.opencode/tools/package-lock.json`
  untracked. It must be declared to the review preflight, not committed.
- No commit, push, or PR from a delegated phase unless the orchestrator authorizes it.

## Decisions

- **D1 — Reuse `scripts/kb_calibration_corpus.yaml` verbatim.** Same 52 queries (30 `answerable`,
  10 `near_miss`, 12 `out_of_domain`), same 24 documents, same labels. Two layers measured on
  identical inputs stay comparable, and there is no second fixture to drift. Building a fresh
  "small set" was proposed and is rejected as duplicate work: the labeled set already exists.

- **D2 — Drive the real path through `run_conversation`, not a re-implementation.**
  `app/chat/graph.py:254` (`run_conversation(session, message) -> list[str]`) is the real entry point
  and the same one `scripts/chat_harness.py:5-9` drives. The harness reuses that pattern
  (`ensure_conversation`, `run_turn`) and adds no production seam.

- **D3 — One isolated customer and conversation per query.** This is a correctness requirement of the
  instrument, not a convenience. A handoff sets the conversation to `human`; a human or closed
  conversation suppresses the later gates, and a closed conversation is never reopened (CR-5,
  `scripts/chat_harness.py:74-83`). Sharing one conversation across 52 queries would make query N's
  outcome depend on query N−1's. Each query gets a fresh customer.

- **D4 — The outcome is read from persisted state and reply strings, never from a new seam.**
  `run_conversation` returns only `list[str]` (`app/chat/graph.py:254-267`) and the `escalate` /
  `escalate_reason` flags live in graph state that is discarded. Classification is
  `answered` / `declined` / `handed_off` / `other`, derived from the reply text
  (`CANNOT_ANSWER_REPLY`, `app/chat/nodes/respond.py:30-33`; `HANDOFF_REPLY`) plus the persisted
  conversation state and events. Exposing the flags would be a production change and is out of scope.

- **D5 — The chunk set is RE-DERIVED, not captured, and the limitation is declared.**
  The chunks that reached the model come from `kb.retrieve` at `app/chat/nodes/respond.py:130-151`
  and are formatted at `:151`. The harness re-runs `kb.retrieve` with the **same arguments the path
  used** (`audience=KbVisibility.CUSTOMER`; the registry scope on the research-triage path).
  Retrieval is deterministic for a fixed DB state and query, so re-derivation is exact; a divergence
  would be an instrument defect, not a finding. LIMITATION, recorded rather than hidden: when a turn
  was handed off by `research_triage` before `respond` was reached, **no chunk reached the model at
  all**. The harness records that explicitly and never invents a chunk to check against.

- **D6 — The deterministic core is `ungrounded_numbers(reply, chunks)`.** Numeric tokens are extracted
  from the reply and from the chunk set after normalization (thousands separators `45.000` → `45000`,
  `pesos`/`CLP`, ranges). Any number present in the reply and absent from the chunk set is flagged.
  This targets the expensive class directly — an invented tariff or plazo — with zero LLM and zero
  ambiguity. HONEST FRAMING: **a flag is a candidate, not a verdict.** A faithful reply may
  legitimately introduce numbers the chunk does not contain (a count, a date, a phone number), and a
  chunk may state a number in a unit the reply restates. The harness reports the flagged list and the
  count; the interpretation is human. It is a triage instrument that shrinks the human reading to a
  shortlist. It is not a judge and must never be reported as one.

- **D7 — The LLM judge is opt-in (`--judge`) and its output is labelled model-produced.** Default OFF,
  so the deterministic run stays reproducible and free. When enabled, its verdict is reported in its
  own section and never merged into the deterministic counts.

- **D8 — The report is JSON with a stable shape**, carrying per query: the query, its class, the
  outcome, the reply, the re-derived chunk ids with similarities, the ungrounded-number flags, and
  whether the retrieval gate produced any chunk. Plus a summary per class: answer / decline / handoff
  rates and the ungrounded-flag rate. A report that cannot be diffed between runs is not a
  measurement.

- **D9 — Cost is forecast before the first call, not after.** 52 turns × 1 chat completion ≈ 52
  provider calls, doubled with `--judge`. The forecast is printed before the run starts, so a paid
  long run is never a surprise.

- **D10 — The measured turn is the real first-contact turn; the CM-1 greeting is detected and
  excluded, not avoided.** Two facts force this. `replies` is an accumulator
  (`app/chat/state.py:175`, `Annotated[list, add]`), so replies from several nodes merge into one
  list rather than replacing each other. And `receive` emits the greeting+menu whenever
  `state.turn <= 1` (`app/chat/nodes/receive.py:20-21`), where `turn` is the count of inbound messages
  (`app/chat/state.py:203-208`). So a fresh conversation's first query yields
  `[greeting, <terminal reply>]`, and "the answer" is ambiguous if the list is read naively.

  The harness therefore records **all** replies per turn, flags `greeting_emitted` by comparing
  against `greeting_with_menu()`, and takes the **last** reply as the outcome. That is sound rather
  than assumed: `receive` is the only node that can emit before the routing decision, and the
  remaining reply always comes from the terminal node (`respond`, `handoff`, `emergency`, `summary`).

  Rejected: a synthetic warm-up turn to push the measurement to turn 2. It adds rows and possible
  cost to buy unambiguity that a deterministic string comparison already provides, and it would
  measure a turn the real customer never experiences. Also rejected: assuming `replies[0]` is the
  answer, which silently breaks when `handoff_gate` short-circuits to `handoff` before `receive`
  runs (`app/chat/graph.py:205-209`) and no greeting is emitted at all.

## Tasks

- [x] **T1** — `odd/tasks/kb-answer-fidelity.md` (this record).
- [x] **T2** — `tests/unit/test_kb_fidelity.py`: model-free contracts for the scoring core
      (`ungrounded_numbers` normalization and known-by-construction cases; the outcome classifier
      including the CM-1 greeting, the CM-2 capture prompts and the EM-3 emergency event; the
      per-class summary math, the layer split and the report shape). RED observed:
      `ModuleNotFoundError: No module named 'kb_fidelity'`.
- [x] **T3** — `scripts/kb_fidelity.py`: pure core plus the I/O shell. Reuses `kb_calibration`'s
      corpus, ingest and environment guard, and `chat_harness`'s `ensure_conversation` / `run_turn`.
- [x] **T4** — Real run against the isolated test DB with the real provider
      (`deepseek/deepseek-flash`, `min_sim=0.50`), all 52 queries. Numbers below.
- [x] **T5** — Findings recorded below.

## Findings

Model `deepseek/deepseek-flash`, threshold `0.50`, 52 queries, 24 documents → 27 chunks ingested
through the real pipeline. Report artifact: `/tmp/kb-fidelity.json`.

| class | n | answered | handed_off | capture_started | greeted_only | emergency_protocol |
|---|---|---|---|---|---|---|
| answerable | 30 | **0** | 14 | 10 | 4 | 2 |
| near_miss | 10 | 0 | 3 | 3 | 4 | 0 |
| out_of_domain | 12 | 0 | 0 | 0 | 12 | 0 |

Handoffs by layer: `kb_miss` 8, `emergency_weak_hit` 6, `emergencia` 2, `complaint` 1.

**F1 — The answer layer never runs, so the fidelity question cannot yet be answered.** Retrieval
delivered at least one chunk above the gate for **25 of 30** answerable queries (83%), with best
similarities from 0.5038 to 0.8277. **Zero of those 25 reached the answer layer.** The KB is not the
bottleneck; every layer above it discards the turn. The instrument works — what it revealed is that
the layer it was built to measure produces no output to measure.

**F2 (production defect, first order) — `source_meta.category` is read but never written, so the
`valores`/`postventa` intents can never reach the KB.** `app/services/kb.py:359` filters on
`source_meta["category"]`; `research_triage` always passes `scope=["valores", "postventa"]`
(`agent/registry.yaml:33`, `app/chat/subgraphs/research_triage.py:74,98`); and **no production path
populates the field**: the panel upload calls `ingest_document` with no `source_meta`
(`app/panel/api/routes/kb.py:143-145`), and every new version is stored with `source_meta=None`
(`app/services/kb.py:235`). The scoped filter therefore returns zero chunks for every document a
client can actually upload, and every question routed to those intents escalates to a human
regardless of content. Measured here: **5 answerable queries where unscoped retrieval had the chunk
and the scope filter threw it away** (`kb_miss` on a query whose `chunks` list is non-empty).

The suite hides it: every test that needs the scoped retrieval to work seeds the category by hand
(`tests/integration/test_chat_capture.py:189`, `test_kb.py:437`, `test_memory_pipeline.py:67`,
`test_chat_intent.py:383`, `test_cost_guardrails.py:608`). The tests prove the filter works and
never exercise the fact that nothing in production satisfies it.

**F3 (by design, product decision) — bare `gas` is a weak emergency marker, so routine questions
escalate before classification.** `WEAK_MARKERS` includes `r"gas\b"` (`app/services/emergency.py:41`)
and a weak hit routes straight to handoff (EM-5). For a **gasfitería** business this intercepts the
most ordinary commercial phrasing: "instalacion cocina a gas", "hacen instalacion de estufa a gas",
"necesito regularizar la instalacion de gas", "que valor tiene la mantencion de una estufa a gas",
"cuanto cobran por revisar el medidor de gas". 6 of 52 queries, all of them answerable, none of them
an emergency. The `_BENIGN_QUALIFIERS` escape hatch exists for "fuga de agua" but has no equivalent
for the service vocabulary this business lives on. This is deliberate and documented, so it is a
decision to revisit, not a bug to fix.

**F4 — The intent router sends service questions to the visit-capture flow.** 10 answerable queries
classified `calefont` / `solicitar_visita` / `calefaccion` were routed to `capture` and replied
"¿Cuál es tu nombre?". The KB was never consulted even though retrieval had chunks for 8 of them.
Not a KB failure either — a routing decision that consumes questions the KB could answer.

**F5 — 4 answerable queries are classified `unknown` and get only the CM-1 menu.** "atienden en
maipu", "cuales son las comunas donde trabajan", "en cuanto tiempo responden un mensaje", "cuales
son los horarios de atencion" — all four are exactly the title-phrased questions F7 of the retrieval
slice flagged, and all four had chunks available.

**F6 (safety) — the property that matters holds.** Zero ungrounded numbers across all 52 queries, and
**zero fabricated answers**: no `near_miss` or `out_of_domain` query was ever answered. The system
declines, escalates, greets or captures — it never invents. This is the one result that is clean, and
it is clean by a wide margin.

**F7 — `declined` is structurally unreachable on the intents that matter.** `CANNOT_ANSWER_REPLY`
never fired in 52 queries. A miss routed through `research_triage` converges on `handoff`, not on
`respond`'s CM-4 branch (`app/chat/subgraphs/research_triage.py:124-128`), so the deterministic
"cannot answer reliably" reply only exists on the `respond` path. CM-4's observable surface is
narrower than the spec implies.

**F8 — The complaint trigger false-positives on the word, not the act.** "cual es el guion para
responder un reclamo" is a question *about* handling complaints; `\breclamo\b` matched it and
escalated (`app/chat/nodes/handoff_gate.py:53`).

**Honest limit — F1 means the headline measurement is a null result, not a pass.** The
ungrounded-number check produced no flags because the answer layer produced no answers, not because
it was verified. The instrument is sound and the deterministic core is suite-covered; the sample it
returned is empty. Answer fidelity stays **unmeasured** until F2/F4/F5 stop discarding the turn.

**Incidental:** a fresh test database needs `bash db/migrate.sh` before the first run — the pytest
conftest owns migrations, and a standalone script does not inherit them. Also, `infra/.env` cannot be
sourced into the shell: it carries `DATABASE_URL` pointing at the compose `db` service and poisons
the isolated test URL (`infra/test-db.sh:25-27`), which is why the harness reads only the provider
keys from that file.

## Acceptance criteria — result

1. `uv run pytest tests/unit/test_kb_fidelity.py` → **35 passed**, no network, no database, no
   `fastembed`.
2. `git diff --name-only -- app/ web/ db/ agent/ openspec/` → **empty**.
3. The harness ran end to end with the real provider and emitted per-query JSON for all 52 queries.
4. The report separates the three classes, the outcome kinds and the handoff layers, and reports the
   ungrounded-number flags.

All four met. The measurement's own result is F1.

## Applicable checks

- `uv run pytest tests/unit/test_kb_fidelity.py -q`
- `git diff --name-only -- app/ web/ db/ agent/ openspec/` → empty
- Real run: `eval "$(bash infra/test-db.sh env)" && uv run python scripts/kb_fidelity.py --json <path>`
- `git diff --check` → no whitespace errors

## Graph Check (Step 1 of the 5-Step Gate)

Consulted before writing: `run_conversation` (`app/chat/graph.py:254`), `ConversationState.from_db`,
the `respond` node and its `_answer_from_kb` call, `kb.retrieve` / `RetrievedChunk`, `KbVisibility`,
`research_triage`'s scoped retrieval, `openai_client`, `CANNOT_ANSWER_REPLY`, `HANDOFF_REPLY`, plus
the consumer edges `chat_harness.ensure_conversation` / `run_turn` / `inspect`. Dominant community for
this area: `services/kb.py` ↔ `nodes/respond.py` ↔ `subgraphs/research_triage.py`. The graph and the
`graphify query "knowledge base retrieval and calibration"` traversal (407 nodes, depth 2) are what
confirmed there is no third retrieval call site and that the assistant tool is the only unscoped one.
