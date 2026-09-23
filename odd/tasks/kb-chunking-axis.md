# Task: kb-chunking-axis — measure the Layer-1 chunking axis

**Type**: measurement unit (harness only, no production change)
**Branch**: `odd/kb-chunking-axis`
**Created**: 2026-09-23
**Source**: refutation of Layer-1 F7 (`handoff/kb-f7-medicion`) + Layer-1 F8
(`odd/tasks/kb-retrieval-calibration.md:214-217`)

## Objective

Measure whether smaller (or differently overlapped) chunks improve Layer-1 retrieval
on the labeled corpus, and decide **on numbers** whether changing production chunking
is worth it.

## Problem

F7 ("document titles are not embedded") was measured and refuted (2026-09-21): recall
tied and `q-comunas` ("atienden en maipu") got **worse** (0.3047 -> 0.2923, rank 2 -> 5).
The diagnosed cause is **mean-pooling dilution on a long, heterogeneous chunk**
(`odd/tasks/kb-retrieval-calibration.md`), so the next candidate lever is the chunking
axis itself.

## Why it cannot be measured today

`chunk_text` binds its defaults at function-definition time
(`app/services/kb.py:95`: `chunk_size=CHUNK_SIZE`, `overlap=CHUNK_OVERLAP`) and
`_store_chunks` calls `chunk_text(doc.content)` with no arguments
(`app/services/kb.py:166`). Assigning `kb.CHUNK_SIZE` has **no effect**. There is no
runtime seam (Layer-1 F8). The calibration harness ingests through
`kb.ingest_document(...)`, so it inherits the fixed 500/50 chunking.

## Approach — harvest only, no production edit

`_store_chunks` resolves the name `chunk_text` from the module namespace at call time.
Replacing `kb.chunk_text` before `ingest_corpus` is therefore a complete seam, exactly
like the harness already overrides `kb._embedder` for `--model`
(`scripts/kb_calibration.py:645-649`). Production (`app/`, `web/`, `db/`, `agent/`,
`openspec/`) is never edited.

## Scope

- `scripts/kb_calibration.py`: add `--chunk-size` / `--chunk-overlap`; a pure,
  model-free chunker factory; wire the override in `run()`; report the **effective**
  size/overlap.
- `tests/unit/test_kb_calibration.py`: cover the factory without loading the model.

## Non-goals

- No change to `app/services/kb.py` or any shipped chunking parameter.
- No new dependency.
- No Layer-2 work (that spends provider tokens; Layer 1 is free).

## Constraints

- Measurement must run against the isolated test DB only (`infra/test-db.sh env`).
- Strict TDD is active (`pytest tests/`): RED before implementation.
- Ponytail: reuse the existing scoring core; the seam is the minimum code that works.

## Tasks

- **T1** — Add `--chunk-size` / `--chunk-overlap` to the harness, with a pure
  `make_chunker(chunk_text_fn, chunk_size, overlap)` factory and the override wired
  before ingest in `run()`. Report the effective chunking.
- **T2** — Unit test the factory with a fake `chunk_text_fn`: asserts it forwards
  `chunk_size`/`overlap` as keyword args and is not invoked at construction.
- **T3** — Verify: `uv run pytest tests/unit/test_kb_calibration.py -q` green and
  `git diff --name-only -- app/ web/ db/ agent/ openspec/` empty.
- **T4** — Run the harness at a size sweep against the isolated test DB (local
  embedder, zero provider cost) and capture one JSON per size.
- **T5** — Compare: separation margin, best absolute threshold, recall / false-accept,
  and the `q-comunas` case per size. Decide whether a production change is warranted.

## Acceptance criteria

1. The harness accepts explicit chunk sizes; the report records the **effective**
   `chunk_size` / `chunk_overlap` and chunk count.
2. `git diff --name-only -- app/ web/ db/ agent/ openspec/` is **empty** on the branch.
3. The unit suite passes **without** loading the model.
4. At least three sizes are measured on both audience modes with the same corpus and
   model, and the comparison names the `q-comunas` outcome per size.

## Checks

- `uv run pytest tests/unit/test_kb_calibration.py -q`
- `uv run pytest tests/unit/test_kb_calibration.py tests/integration/test_kb.py -q`
- `git diff --name-only -- app/ web/ db/ agent/ openspec/`
- Harness run per size (JSON captured under `local-notes/`).

## Progress

- [x] Unit opened: worktree `odd/kb-chunking-axis` created 2026-09-23.
- [x] T1 harness seam (`scripts/kb_calibration.py`)
- [x] T2 unit test (`tests/unit/test_kb_calibration.py`)
- [x] T3 verification
- [x] T4 size sweep
- [x] T5 comparison + decision

## Evidence

### Verification

- `uv run pytest tests/unit/test_kb_calibration.py -q` -> **37 passed** (writer: RED first —
  `AttributeError: module 'kb_calibration' has no attribute 'make_chunker'` — then GREEN).
- `uv run pytest tests/unit/test_kb_calibration.py tests/integration/test_kb.py -q` -> **56 passed**.
- `git diff --name-only -- app/ web/ db/ agent/ openspec/` -> **empty** (production untouched).

### Environment gotcha (cost a writer round-trip)

`infra/test-db.sh` derives the compose project **and port** from the worktree directory name, so
this branch's isolated DB is `lumat-test-lumat-agent-odd-kb-chunking-axis` on port **5697**, not
main's 5986. The worktree also needs `infra/.env` copied from main. The writer's first integration
run failed on `localhost:5697` connection refused for exactly this reason — the port came from the
worktree, the container did not exist yet.

### Sweep (local embedder, zero provider cost; same corpus 24 docs / 52 queries; unscoped audience)

| chunk_size/overlap | chunks | best-abs recall | best-abs false-accept | relative balanced | relative recall | relative false-accept |
|---|---|---|---|---|---|---|
| 200/20 | 64 | 0.833 | 0.273 | 0.803 | 0.833 | 0.227 |
| 300/30 | 44 | 0.800 | 0.227 | 0.821 | 0.733 | 0.091 |
| 400/40 | 30 | 0.933 | 0.318 | 0.905 | 0.900 | 0.091 |
| 500/50 (shipped) | 27 | 0.900 | 0.318 | 0.882 | 0.900 | 0.136 |
| 750/75 | 25 | 0.900 | 0.273 | 0.855 | 0.800 | 0.091 |

Customer audience agrees on the ranking: 400 is the only size that beats 500 on the relative rule
(0.884 vs 0.848), and 200/300 are worse (0.807 / 0.830).

### The mechanism — `q-comunas` ("atienden en maipu", relevant doc `comunas-cobertura`)

| size | chunks | `comunas-cobertura` score(s) | best_relevant_rank | top distractor |
|---|---|---|---|---|
| 200 | 64 | 0.3691 | 2 | `tarifas-instalaciones` 0.6552 |
| 300 | 44 | 0.3691, 0.2898 | 2 | `catalogo-calefont` 0.5752 |
| 400 | 30 | 0.3047 | 1 | `tarifas-mantencion` 0.3003 |
| 500 | 27 | 0.3047 | 2 | `tarifas-mantencion` 0.3626 |
| 750 | 25 | 0.3047 | 2 | `tarifas-mantencion` 0.3498 |

The **relevant** chunk's score does not improve with smaller chunks — it is flat at 0.3047-0.3691,
always below the 0.50 gate. What moves is the **distractor**: at 200/300 an irrelevant document
jumps to 0.65/0.58. So q-comunas "accepted at 0.50" under 200/300 is a **false accept on the wrong
document**, not a rescue. Smaller chunks do not fix dilution of the target; they amplify
coincidental matches in distractors. This refutes the mechanism F7's refutation pointed at.

### Safety case (Layer-1 F5, `q-olor-gas`)

Best relevant rank: **6** (500) -> **8** (400) -> **7** (300) -> **13** (200). Smaller chunks make
the gas-leak ranking **worse**, not better.

## Decision

**The chunking axis does not pay. Production stays at 500/50 — `app/services/kb.py` is not changed.**

- Below 400 is strictly worse: lower recall and more false accepts, and it makes the safety case
  worse.
- 400 vs 500 is within the resolution of a 52-query corpus (30 vs 27 chunks; +1 grounded answerable,
  -1 false accept). It does not fix the flagged case (`q-comunas` still declined) or the safety case
  (rank 8 vs 6). Re-indexing every customer document is not justified by that.
- 750 is worse on the relative rule and wrongly declines 4 of the 6 problem queries.
- Honest limits: synthetic corpus (24 docs); only 3 documents exceed 500 chars, so the axis moves
  few files; the thresholds are derived from the same 52 queries and are therefore optimistic. This
  is a lever screen, not a verdict for all corpora.

## Next step

The unchased lever is the **ranking**, not the chunk size: `q-olor-gas` never reaches rank 1 at any
size (best 6), which is exactly what Layer-1 F5 recorded. A reranker (or a title-as-own-chunk index)
targets that. Layer 1 measurement stays free; Layer 2 spends provider tokens.
