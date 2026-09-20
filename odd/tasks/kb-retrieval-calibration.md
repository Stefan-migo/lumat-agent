# ODD: kb-retrieval-calibration

**Slice 1 of the retrieval-calibration unit — the benchmark. No production number moves here.**

## Objective

Build a reproducible, labeled benchmark that measures KB retrieval quality against the **real**
embedding model, so the recall/threshold decision of the next slice is made from a measured
distribution instead of from a single hand-picked similarity score.

## Problem

`min_sim=0.65` (`app/services/kb.py:40`) rejects queries it should answer. Measured end-to-end with
the real model against one seeded three-line document:

| Query | Similarity | vs `0.65` |
|---|---|---|
| `cuanto cuesta la mantencion del calefont` | 0.6237 | below — miss |
| `instalacion cocina a gas` | 0.5491 | below — miss |
| `mantencion anual calefont` | 0.5070 | below — miss |
| `receta de empanadas` (unrelated control) | 0.1935 | below — correct |

That is a **signal, not a benchmark**: one document, four queries, no chunk-boundary study, and one
single unrelated control. It does not tell us where a threshold should sit, and it cannot compare
rule *shapes*. Three things are missing and all three are structural, not incidental:

- **No labeled set exists.** The repo has no KB corpus at all — `db/seed.sh` seeds settings and the
  admin user only. There is nothing to measure against, so there is nothing to calibrate against.
- **No measurement harness.** The only tuning surface is `GET /panel/api/kb/search` and moving
  `min_sim` by hand, one query at a time. That endpoint accepts `top_k` and `min_sim` **without any
  range validation** (`app/panel/api/routes/kb.py:78-93`; review advisory R3-001, never corrected), so
  manual tuning is both slow and unguarded.
- **The suite structurally cannot catch this.** `tests/integration/test_kb.py:269-282` asserts the
  relevant case with the query **identical** to the document and `similarity >= 0.99`. On a
  bi-encoder, identical text scores ~1.0 with any model — so the test encodes "relevant = ~1.0" and
  `0.65` looks safe. The production case is **asymmetric** (a colloquial customer question against a
  descriptive passage), where the same model lands at 0.4–0.6. The suite was never measuring the
  product's actual input distribution.

### Verified during this slice (corrects the handoff)

`fastembed` resolves the configured model id
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` to HF repo
`qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q` — the **quantized** ONNX build. So "try the
quantized ONNX variant" is not a candidate: it is what already runs in production. The quantized
build is the **baseline**, and the only meaningful question about it is whether full precision shifts
the absolute score distribution.

Also verified: the earlier measurement cannot be explained by chunking. A three-line document fits
in a single 500-character chunk, so no chunk boundary existed to hurt it.

## Scope

**In:** the labeled corpus fixture; the calibration harness; the pure scoring/rule-comparison core;
model-free tests for the corpus schema and the scoring math; the measured matrix and the findings
record.

**Out (explicitly — this slice is the benchmark and nothing else):** any change to
`DEFAULT_MIN_SIM`, `DEFAULT_TOP_K`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, the retrieval query, the ranking,
the embedding model, or the chunking strategy; the R3-001 range validation; the R3-002 frontend
asserts; `web/`; `db/migrations/`. The rule decision is a **separate slice with its own PR**, made
from this matrix.

## Spec constraints (binding — do not violate)

- `openspec/specs/knowledge-base/spec.md` — **KB-2**: retrieval with configurable `top-k` and
  threshold. This slice must not change the spec; it produces the evidence the next spec change is
  argued from.
- `openspec/specs/knowledge-base/spec.md` — **KB-5**: document audience. The benchmark MUST exercise
  the audience axis rather than assume it (see D5/D6).
- `agent/registry.yaml` / **AO-7**: the topic `scope` axis is orthogonal to audience and is not part
  of this slice.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-kb-retrieval-calibration`
- Branch: `odd/kb-retrieval-calibration`
- Base: `a57b353e` (merge-base with `main`, verified with `git merge-base HEAD main`)
- Files:
  - `odd/tasks/kb-retrieval-calibration.md`
  - `scripts/kb_calibration_corpus.yaml`
  - `scripts/kb_calibration.py`
  - `tests/unit/test_kb_calibration.py`

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml` (`testing.strict_tdd: true`); runner `uv run pytest`.
  Observe RED before each artifact; never invent RED evidence.
- Test DB for this worktree: `infra/test-db.sh up` → host port **6100**, project
  `lumat-test-lumat-agent-odd-kb-retrieval-calibration`. `eval "$(bash infra/test-db.sh env)"` is
  required before pytest or migrations connect as the unprivileged `app` role and fail with a
  misleading password error (pre-existing harness quirk).
- **The harness MUST NOT run inside `pytest tests/`.** It loads the real model and is not
  deterministic. Only the model-free parts are suite-covered; the real run is an explicit manual
  invocation and its output is recorded by hand.
- **No production file may change.** Check before committing:
  `git diff --name-only -- app/ web/ db/ agent/ openspec/` must be **empty**.
- Artifacts in English. The **corpus bodies and queries are Chilean Spanish** — that is the
  product's real input distribution and the measurement's substance, not a documentation language
  choice. YAML keys and comments stay English.
- No commit, push, or PR from a delegated phase unless the orchestrator authorizes it.

## Decisions

- **D1 — The fixture is one YAML file, not a directory of documents plus a parser.** `load_corpus`
  is a `yaml.safe_load` and a schema check. Fewest moving parts, reviewable as a diff, and no
  parsing framework to maintain. Rejected: markdown files per document (needs a parser and a
  title/id convention), JSON (worse to review and edit by hand).
- **D2 — The corpus topology mirrors the client document request, not invented categories.**
  `docs/solicitud-al-cliente-lumat.md:204-214` lists exactly which documents Lumat will load:
  services catalogue, current tariffs, coverage communes, warranties, common procedures/deadlines,
  FAQ, emergency protocols, business hours and emergency contacts, assistant tone, standard
  messages. The fixture uses those as its document classes, so the benchmark measures the corpus the
  client is actually going to hand us.
- **D3 — Three label classes, and emergencies are excluded from the retrieval labels.** Classes are
  `answerable`, `out_of_domain`, `near_miss`. Emergency phrasing ("tengo olor a gas") is **not** a
  retrieval label: escalation is the job of the deterministic emergency gate
  (`app/chat/nodes/emergency*.py`), which runs before retrieval. Labeling it as "must miss" would
  push the threshold up to compensate for a different layer, and labeling it "must hit" would
  pretend retrieval owns a decision it does not. Conflating the two axes breaks both.
- **D4 — The harness retrieves once with `min_sim=0.0` and a large `top_k`, then sweeps thresholds
  in Python.** One call returns the complete ranked score list per query, so the entire
  absolute/relative/margin comparison costs zero extra embeddings and zero DB round-trips. This is
  also the deliberate answer to R3-001: **`min_sim` is never moved by hand** during calibration.
- **D5 — Every query is measured twice, `audience=None` and `audience="customer"`.** Same embeddings,
  two runs. This separates "the model scores badly" from "the audience filter hides the right
  document" — the failure mode that would otherwise be misread as a threshold problem.
- **D6 — One `internal` document is designed to win an unscoped retrieval.** So the audience filter's
  effect is *observable* in the matrix rather than assumed to work.
- **D7 — The harness takes `--model`.** The model axis (handoff suspects #2/#3) then needs no
  rewrite. Slice 1 reports the default production model only; the axis exists, unexplored.
- **D8 — The chunking axis is deferred, and deliberately not faked.** `chunk_text`'s parameters are
  bound at function-definition time (`app/services/kb.py:94`), and `_store_chunks` calls
  `chunk_text(doc.content)` with no arguments — so overriding `kb.CHUNK_SIZE` at runtime has **no
  effect**. Exercising chunking needs a real seam, which is a production change and therefore out of
  this slice. Recorded as a finding instead of a half-working flag.
- **D9 — Baseline quantization is documented in the report.** The measured numbers are from the
  `-onnx-Q` build. Any future full-precision comparison must be labeled as such, and no absolute
  threshold derived here may silently be assumed to transfer to a different build.

## Tasks

- [x] **T1** — `odd/tasks/kb-retrieval-calibration.md` (this record).
- [x] **T2** — `tests/unit/test_kb_calibration.py`: the corpus **schema** contract and the **scoring
      core** contract (20 tests). RED observed: `ModuleNotFoundError: No module named
      'kb_calibration'` — a collection error, since neither the fixture nor the harness existed yet.
      Both halves were written before their artifacts so the single RED covers both; every scoring
      assertion has an expected answer fixed by construction, not by a recorded run.
- [x] **T3** — `scripts/kb_calibration_corpus.yaml`: 24 documents across the 10 D2 classes
      (21 `customer`, 3 `internal`) and 52 labeled queries — 30 `answerable` (2 of them
      internal-only), 10 `near_miss`, 12 `out_of_domain`.
- [x] **T4** — `scripts/kb_calibration.py`: the pure core (`load_corpus`, `accept_absolute`,
      `accept_margin`, `accept_relative`, `metrics_at`, the three sweeps, `summarize`,
      `compare_rules`, `rank_of_best_relevant`) plus the I/O shell (isolated test DB, real embedder,
      full-ranking retrieve). GREEN: **20 passed**.
- [x] **T5** — Real-model run, both audience modes, against the isolated test DB.
- [x] **T6** — Findings recorded below. Report artifact: `/tmp/kb-calibration.json`.

## Findings (the matrix)

Model resolved to `qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q` (384d, quantized — D9).
24 documents → 27 chunks (so the corpus does exercise multi-chunk documents). `min_sim` was never
moved by hand; every number below comes from one full-ranking retrieve per query.

| audience | answerable top-1 | irrelevant top-1 | separation | best absolute | margin rule | relative rule |
|---|---|---|---|---|---|---|
| unscoped | 0.3626 – 0.8277 (n=30) | ≤ 0.6976 (n=22) | **−0.335** | 0.4752 → balanced 0.791 | 0.797 | **0.882** |
| customer | 0.3626 – 0.8277 (n=28) | ≤ 0.6976 (n=24) | **−0.335** | 0.4752 → balanced 0.801 | 0.804 | **0.848** |

Balanced accuracy is `(answerable_recall + specificity) / 2`.

**F1 — The ranking is right; the absolute threshold is what is wrong.** 24 of 30 answerable queries
(80%) have the correct document at **rank 1**, and the relevant document is present in the ranking for
**30 of 30**. Of the 20 answerable queries the shipped threshold declines, **15 have the correct
document ranked first**. The model retrieves the right passage and `min_sim=0.65` throws it away.

**F2 — No absolute threshold can work on this corpus, and that is a structural result, not a tuning
miss.** The highest-scoring **irrelevant** query (`q-medidor-gas`, "cuanto cobran por revisar el
medidor de gas natural", 0.6976) outscores **24 of the 30 answerable queries**. Accepting those 24
requires a threshold below 0.6976; rejecting that one requires a threshold above it. The two
requirements are mutually exclusive. The overlap is produced entirely by the `near_miss` class:
`out_of_domain` tops out at 0.4554 (well separated), `near_miss` reaches 0.6976.

**F3 — The current setting is wrong in both directions at once.** At 0.65 the system declines
**20 of 30** answerable queries (17 of 52 overall accepted while 30 should have been answered) *and*
accepts **3 of 10** `near_miss` queries (0.6976, 0.6777, 0.6735). A single absolute number is being
asked to both accept and reject, which is the mechanism behind F2.

**F4 — The rule shape matters more than the number.** The relative rule (top-1 ≥ floor **and** top-1 ≥
ratio × mean of the ranking) cuts false accepts from 0.318 to 0.136 at **unchanged** recall of 0.900
(unscoped). The margin rule barely helps (0.797), because on a real corpus the top-2 gap does not
separate the classes. Honest caveat: the ratio grid is derived from the observed ratios, so 0.882 is
optimistic on 52 queries — the *direction* is the finding, not the third decimal.

**F5 (safety-relevant) — The gas-leak protocol is ranked 6th.** "huelo gas en la cocina que hago"
puts `tarifas-instalaciones` first at 0.5521; `protocolo-fuga-gas` does not appear in the top 5. On
this evidence retrieval is **not** a safety backstop for emergency phrasing. Product impact is
mediated by the deterministic emergency gate, which runs before retrieval (D3), but the ranking
weakness is real and separate from the threshold question.

**F6 — The audience filter is verified, not assumed.** Both internal-only queries reach their internal
document at rank 1 unscoped (0.6448, 0.6802) and are correctly hidden as `customer` (0.4428, 0.4218,
not accepted). D6 did its job: this is the check that would have caught a threshold "fix" papering
over a broken filter.

**F7 — Document titles are not embedded.** `_store_chunks` embeds `chunk_text(doc.content)` only
(`app/services/kb.py:159`), so the title never reaches the vector. Many real customer questions are
phrased like a title — `q-plazos` ("en cuanto tiempo responden un mensaje") vs. the document
"Plazos de respuesta", `q-comunas` ("atienden en maipu") vs. "Comunas y zonas de cobertura" — and all
of them are in the wrongly-declined set. **Untested hypothesis, highest-value lead for the next
slice:** prepending the title to the embedded text is a far cheaper experiment than changing the
model, and this harness can measure it in one run.

**F8 — `chunk_text`'s parameters cannot be overridden at runtime.** They are bound at
function-definition time (`app/services/kb.py:94`) and `_store_chunks` calls `chunk_text(doc.content)`
with no arguments, so assigning `kb.CHUNK_SIZE` has no effect. The chunking axis needs a real seam
(D8); this slice did not fake one.

**Incidental:** `app/agent_registry.py:26` imports `yaml` without it being a declared direct
dependency of `pyproject.toml` (it arrives transitively). Pre-existing; not touched here.

## Acceptance criteria

1. `uv run pytest tests/unit/test_kb_calibration.py` passes, and the corpus fixture is validated by
   the suite **without** loading the model.
2. `git diff --name-only -- app/ web/ db/ agent/ openspec/` is empty on the branch: this slice
   changed no production behavior.
3. The harness runs end-to-end against the isolated test DB with the real model and emits a JSON
   matrix containing, per query, both audience modes: the ranked scores, the rank of the best
   relevant document, and whether the shipped 0.65 accepts it.
4. The matrix carries the numbers the next slice decides from: the answerable and irrelevant top-1
   distributions, the best achievable absolute threshold, and each rule shape at its own best
   configuration on identical outcomes.

## Result

All four met. `uv run pytest tests/unit/test_kb_calibration.py tests/integration/test_kb.py -q` →
**40 passed**. `git diff --name-only -- app/ web/ db/ agent/ openspec/` → **empty** (four new files:
the record, the corpus, the harness, the test). The matrix and F1–F8 are above; the raw report is
`/tmp/kb-calibration.json` (regenerate with the command below — it is not committed, the corpus is).

**The slice does what it was scoped to do and nothing more:** no production number moved. The
decision it enables is now evidence-backed, and the decisive evidence is F2 — the overlap is
structural, so "lower the threshold" is not a sufficient answer and a rule-shape change is on the
table.

## Applicable checks

- `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/unit/test_kb_calibration.py tests/integration/test_kb.py -q`
- `git diff --name-only -- app/ web/ db/ agent/ openspec/` → empty
- Real-model run: `eval "$(bash infra/test-db.sh env)" && uv run python scripts/kb_calibration.py --json <path>`
- `git diff --check` → no whitespace errors

## Graph Check (Step 1 of the 5-Step Gate)

Consulted before writing: `retrieve()`, `RetrievedChunk`, `chunk_text()`, `_store_chunks()`,
`embed_texts()`, `_embed_cost()`, `KbChunk`, `KbDocument`, `KbVisibility`, `DocumentFormat`, plus the
consumer edges `respond()` and `_kb_check()` (`research_triage`). Dominant community for this area:
`services/kb.py` ↔ `test_kb.py` ↔ `KbVisibility`. The graph is what surfaced the consumer set and
confirmed there is no third retrieval call site.
