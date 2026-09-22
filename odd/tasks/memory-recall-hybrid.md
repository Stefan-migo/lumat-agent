# ODD: memory-recall-hybrid

## Objective

Make `hybrid_search()` — and therefore `memory.search` / `memory.read` — recall a memory when the
query is a literal keyword or phrase that appears in its content, without weakening the existing
"an unrelated query returns an empty set" contract (MEM-3).

## Problem

The panel agent's memory is unreadable in practice. A user stores a memory and cannot get it back.

Reproduced on the local dev environment (2026-09-22). Thread 170 wrote a memory whose content is
`El administrador pidió guardar una memoria con la palabra clave «perro» en este hilo del panel.`
(stored at `scope=agent`, `entity_id=agent:default`, `proyecto=default`, `visibility=global`).
Thread 171 asked for it; `memory.search` returned empty. So did the earlier cross-thread test
(thread 168 wrote, thread 169 searched `cross-thread` and got nothing).

The write path is not the problem. The row is written correctly on the project-qualified agent axis
and `memory.read` lists it. **The search path is.**

Two independent dilutions, measured against the real embedder
(`paraphrase-multilingual-MiniLM-L12-v2`) and the real database:

| query | content | dense cosine | `similarity()` | fused (current) | gate |
|---|---|---|---|---|---|
| `perro` | …palabra clave «perro»… | 0.184 | 0.071 | **0.206** | 0.55 |
| `palabra clave` | …palabra clave «perro»… | 0.469 | 0.167 | **0.519** | 0.55 |
| `el administrador pidió guardar una memoria` | same row | 0.739 | 0.478 | 0.882 | 0.55 |

1. **The lexical channel is misapplied.** `fts_sim = func.similarity(Memory.contenido, query)` is
   whole-string pg_trgm similarity. For a long content the trigram union is dominated by the content
   length, so an exact keyword scores ~0.07. pg_trgm's whole-string `similarity()` answers "are these
   two strings globally alike?", not "does this content contain the query?".
2. **The dense channel is diluted too.** A one-word query against a long sentence embeds to ~0.18
   cosine. Not a model defect: unrelated sentence pairs measure −0.09…0.21, so the model is healthy;
   the query signal is simply spread across a long content embedding.

Measured recall on a 14-memory calibration corpus against the real embedder:

| query set | current code | after this change |
|---|---|---|
| 13 short keyword queries | **1/13** | 13/13 |
| 14 natural questions | 14/14 | 14/14 |
| 6 unrelated queries returning empty | 6/6 | 6/6 |

The current code scores 14/14 on natural questions and 6/6 on unrelated ones. That is exactly why
the suite stayed green: every memory recall test runs on the `fake_embedder` fixture, a bag-of-char-
trigrams hash whose geometry is the inverse of the real model's (shared substrings score ~1.0
instead of being diluted). The gate was never exercised against real geometry.

## Why — the collapsed threshold

The two channels fail in opposite directions, so one threshold cannot serve both:

- A terse keyword query needs a **low** gate: its dense cosine is 0.15–0.47.
- An unrelated natural query needs a **high** gate: its dense cosine reaches 0.42 (shared place
  names, shared register), and with the lexical term added it reaches 0.54.

Swept empirically, no single fused threshold separates both sets. `0.55` admits the unrelated
natural query; `0.45` recalls the keywords but leaks 13 unrelated rows and empties only 3 of 6
negative queries. The defect is the *fused-admission* shape, not just the constant.

## Scope

**In:**

- Replace the lexical term with a Spanish full-text match: `to_tsvector('spanish', contenido) @@
  plainto_tsquery('spanish', query)`. Token-based (no length dilution), and it folds accents and
  stems — so `calefon` matches `calefón` and `Maipu` matches `Maipú`, which trigram similarity loses
  (0.455 and 0.500).
- Admit a candidate when `dense >= MEM_MIN_SIM` **or** the lexical match holds; rank the admitted set
  by the existing fused score.
- Recalibrate `MEM_MIN_SIM` to the dense-channel gate (0.55 → 0.50), matching `kb.DEFAULT_MIN_SIM`.
- Amend MEM-3 to state per-channel admission and merged ranking.

**Out:**

- The embedding model. It is healthy; the dilution is intrinsic to short-query-vs-long-content.
- A `tsvector`/pg_trgm GIN index. The candidate prefilter is vector-only and bounded; memory corpora
  per entity are small. Registered as backlog if corpora grow.
- `unaccent`. The `spanish` text-search configuration already folds accents; no extension needed.
- Query-less recall (`memory.search` requires `query`) — separate backlog item.
- Slice 2, the web entry that binds a thread to a project. It is downstream of this.
- Customer scope behaviour, panel context assembly (stays pull-only).

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-memory-recall-hybrid`
- Branch: `odd/memory-recall-hybrid`
- Base: `0718257b`
- Files: `odd/tasks/memory-recall-hybrid.md`, `app/services/tukulpan.py`,
  `openspec/specs/memory/spec.md`, `tests/conftest.py`, `tests/spec/test_memory_spec.py`

## Constraints

- **Strict TDD: ON** — source: `openspec/config.yaml` (`testing.strict_tdd: true`). Runner:
  `uv run pytest tests/`. Observe RED before the source change; never invent RED evidence.
- Integration commands require `eval "$(bash infra/test-db.sh env)"` first.
- **Thread isolation must survive.** The change must not admit another thread's panel rows; admission
  still runs inside the existing `(proyecto, scope, entity_id)` filter.
- **Unrelated queries stay empty.** MEM-3 `Scenario: Empty result` is a contract, not a nicety.
- `similarity()` is not deleted globally: KB uses its own retrieval path and is untouched.

## Design decisions

**D1 — The lexical channel becomes a boolean full-text match, not a scored trigram.**
`to_tsvector('spanish', contenido) @@ plainto_tsquery('spanish', query)` is the correct tool for
"does the content contain the query's terms?". It needs no threshold, is immune to content length,
and folds accents and stems for free. Measured: 13/13 keyword recall, including the accented domain
words the trigram channel missed.

**D2 — Admission is per channel; ranking stays fused.** The dense channel and the lexical channel
answer different questions, so OR-ing their admissions is the honest model. A single global score
conflated a semantic judgement with a containment judgement and could not calibrate both.

**D3 — The dense gate is recalibrated to 0.50 and named for what it gates.** 0.50 is measured, not
borrowed: it keeps all 6 unrelated queries empty while admitting every natural question. It also
matches KB's `DEFAULT_MIN_SIM`, so the two retrieval paths read the same number.

**D4 — The ranking term keeps `strict_word_similarity`, for ordering only.** Ordering among admitted
rows still uses `dense + FTS_BOOST * lexical_score`; `strict_word_similarity` is used there because
it is less length-diluted than `similarity()`. Admission does not depend on it.

## Tasks

- [x] **T1** — RED: `tests/spec/test_memory_spec.py` — a memory whose content buries a literal
      keyword is recalled by `hybrid_search` from the same entity, under an uninformative dense
      channel (fails today: lexical term diluted, fused below the gate).
- [x] **T2** — RED: a query whose terms do not appear in any content and whose dense cosine is low
      returns an empty set under the new admission (locks `Scenario: Empty result`).
- [x] **T3** — GREEN: lexical admission via Spanish full-text match; fused ranking unchanged in shape
      (`app/services/tukulpan.py`).
- [x] **T4** — GREEN: `MEM_MIN_SIM` recalibrated to the dense-channel gate.
- [x] **T5** — Amend MEM-3 (`openspec/specs/memory/spec.md`): requirement text, `Threshold recall`
      scenario, plus a `Literal phrase recall` scenario.
- [x] **T6** — Verify against the real dev database with the real embedder: the three reproduced
      queries (`perro`, `palabra clave`, `cross-thread`) recall their rows; the unrelated ones stay
      empty.

## Verification

- `uv run pytest tests/spec/test_memory_spec.py`
- `uv run pytest tests/` (full suite)
- Real-corpus check against the dev database, described in T6.

## Acceptance criteria

1. A keyword query recalls the memory whose content contains it, from the same entity and project.
2. A query with no lexical overlap and low dense similarity returns an empty set.
3. Accent variants (`calefon`/`calefón`, `Maipu`/`Maipú`) do not break recall.
4. Another thread's panel rows remain invisible; customer rows remain client-gated.
5. The pre-existing threshold/ordering tests still pass unchanged in intent.

## Graph nodes consulted

`hybrid_search()` (`app/services/tukulpan.py:607`), `Memory` (`app/models.py:457`),
`upsert()` (`tukulpan.py:306`), communities `Panel Memory Persistence` and
`Similarity Score Thresholds`; `to_memory_dict()` (`app/panel/api/serializers.py:423`).

## Outcome

Closed. One work unit plus the record.

| Commit | Subject |
|---|---|
| `333c6084` | `fix(memory): recall literal phrases with per-channel admission` |

This record lands as its own `docs(odd)` commit on the same branch.

**What changed.** `hybrid_search()` now admits a candidate when `vector_sim >= MEM_MIN_SIM` (0.50,
recalibrated) **or** when `to_tsvector('spanish', contenido) @@ plainto_tsquery('spanish', query)`
holds, and ranks the admitted set by `vector_sim + FTS_BOOST * strict_word_similarity`. The
previous code used `similarity(contenido, query)` -- whole-string pg_trgm -- as both the lexical
term and part of a single fused gate.

**RED observed before the source change.** Two new MEM-3 tests, on a `flat_embedder` fixture whose
distinct texts are orthogonal (the real model's dilution on long content):

```
E       AssertionError: assert [] == ['agent:calefon']
E       AssertionError: assert [] == ['agent:keyword']
```

**Verification.**

- `uv run pytest tests/` -> **1209 passed, 0 failed** (132.30s), against the worktree test database.
  Baseline was 1207; the delta is the two new tests, with none removed.
- **Real-corpus check (T6).** The implemented function, run with the real embedder against a
  database seeded with the three reproduced agent-axis memories, returns exactly the expected row
  for `perro`, `palabra clave`, `cross-thread`, `LUMA-TEST-XTHREAD-7742` and a natural question, and
  an empty set for `clima en Santiago manana`, `receta de sopa de zapallo` and
  `como instalar un servidor linux` (`RESULT: ALL PASS`).
- No lint gate exists in this repo: `ruff` is not installed and `pyproject.toml` configures no
  linter. Declared rather than faked.

**Calibration basis (measured, not assumed).** Against 14 realistic memories and the real model:

| query set | before | after |
|---|---|---|
| 13 short keyword queries | 1/13 | 13/13 |
| 14 natural questions | 14/14 | 14/14 |
| 6 unrelated queries returning empty | 6/6 | 6/6 |

`0.50` was chosen from that sweep, and it matches `kb.DEFAULT_MIN_SIM`, so both retrieval paths read
the same number. The trade-off accepted: `0.50` admits ~3 near-miss rows across the natural set
where the old `0.55` admitted 1 -- the model's dense channel cannot separate those pairs -- while
keyword recall goes from 1/13 to 13/13 and every unrelated query still returns empty.

**Follow-up registered as backlog, not implemented here.** The candidate pre-filter is vector-only
(`order_by(distance).limit(candidate_limit)`), so on a corpus much larger than `4 * top_k` a keyword
match that is far in vector space would never become a candidate. It is harmless at current
per-entity corpus sizes and is the natural next unit if corpora grow; it would want a GIN index on
`to_tsvector('spanish', contenido)`.
