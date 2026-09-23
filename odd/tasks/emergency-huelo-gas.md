# ODD: emergency-huelo-gas

**Close the safety gap where the first-person gas-smell phrasings do not escalate.**

## Objective

Make `"huelo gas"` and `"huelo a gas"` strong emergency keywords, so a customer reporting a gas
smell in the first person triggers the EM-3 safety protocol instead of falling through to the
commercial flow.

## Problem

`DEFAULT_EMERGENCY_KEYWORDS` (`app/services/settings.py:75-89`) carries `"olor a gas"` and
`"huele a gas"`, but **not** the first-person forms. The compiled pattern is literal and
word-bounded over accent-folded text, so `"huelo gas"` matches neither entry.

Measured on `0fe7ba5a` with the real classifier
(`compile_keywords(DEFAULT_EMERGENCY_KEYWORDS)` + `classify_emergency`):

| message | result today |
|---|---|
| `huelo gas en la cocina que hago` | **None** |
| `huelo a gas` | **None** |
| `huele a gas` | strong |
| `hay olor a gas` | strong |
| `siento olor a gas` | strong |
| `fuga de gas` | strong |

This is the asymmetry: the third person escalates, the first person — the same perceived risk —
does not.

**Why it matters.** The emergency gate runs on every inbound message **before** any LLM call and
before retrieval (`app/chat/nodes/emergency_gate.py`). A miss there does not degrade gracefully: the
message reaches commercial classification, and retrieval answers it. For the corpus query
`q-olor-gas` (`"huelo gas en la cocina que hago"`), the measured retrieval top-1 is a **wrong**
document at 0.5521, and after the title-vector experiment, still wrong at 0.8064. A gas smell
answered with the wrong catalogue entry is worse than a miss.

**Where this came from.** The gap surfaced while measuring the title-as-own-vector axis (Layer-1
F9, Engram #4762, refuted). That experiment also produced the finding that the safety case is not a
ranking problem but a keyword-coverage gap (Engram #4763).

### The gap was not declared

`odd/tasks/emergency-gas-weak-marker.md` (D2) pinned the residual gap after removing bare `gas` as
a weak marker, but the pinning test `test_leak_phrasings_without_a_strong_keyword_are_not_detected`
(`tests/integration/test_emergency.py:145-153`) only covers `"se escapa el gas"` and
`"me esta saliendo gas"`. `"huelo gas"` was never recorded as a hole: it is an undeclared gap on the
safety path.

## Why

The customer is **Lumat's end user**, possibly standing in a kitchen that smells of gas. The value is
that the safety path is reached from the phrasing people actually use, not only from the phrasing
the keyword list happened to enumerate.

## Scope

**In:**

- `app/services/settings.py` — `"huelo gas"` and `"huelo a gas"` join `DEFAULT_EMERGENCY_KEYWORDS`.
- `tests/integration/test_emergency.py` — two rows in `EMERGENCY_SENTENCES`, so
  `test_strong_hit_each_default_keyword` pins them like every other default keyword.

**Out (explicitly):**

- **The weak markers.** Untouched. This unit adds strong keywords only.
- **The already-pinned residual gap** (`"se escapa el gas"`, `"me esta saliendo gas"`). Left exactly
  as the previous unit decided; the panel (SS-2) remains its mitigation.
- **Negation handling** (`"no huelo gas"` also matches). Pre-existing for `"huele a gas"`; declared
  below rather than silently inherited as a new claim.
- **Retrieval and ranking.** No chunking, embedding, threshold, or reranker change. That axis is
  closed by F7/F8/F9.
- **The spec.** No delta — see D3.
- **The panel surface.** The strong list is already panel-configurable (SS-2); no new mechanism.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-emergency-huelo-gas`
- Branch: `odd/emergency-huelo-gas`
- Base: `0fe7ba5a` (= `origin/main`; verified with `git rev-parse` before creating the worktree)
- Files:
  - `odd/tasks/emergency-huelo-gas.md`
  - `app/services/settings.py`
  - `tests/integration/test_emergency.py`

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml` (`testing.strict_tdd: true`); runner
  `uv run pytest`. Observe RED before the source change; never invent RED evidence.
- Test DB: `eval "$(bash infra/test-db.sh env)"` (this worktree derives its own port) and a fresh
  database needs `bash db/migrate.sh` first.
- A fresh worktree has no `.venv` and no `infra/.env`: `uv sync` and copy `infra/.env` first.
- Known worktree artifact: `rapso worktree create` leaves `.opencode/tools/package-lock.json`
  untracked. Declare it to the review preflight; never commit it.
- This is the **safety path**. Every keyword added must be covered by a test, and the boundaries left
  uncovered must be stated rather than implied.
- Conventional commits, no `Co-Authored-By`. One concern per commit, <=5 files per commit.
- No commit, push, or PR unless the orchestrator authorizes it.

## Design decisions

**D1 — Strong, not weak.** A perceived gas smell is exactly what EM-3 exists for, and `"huele a
gas"` — the third person of the same perception — is already strong. Routing the first person to a
mere handoff would be an internal inconsistency in the safety net. Decided by the maintainer.

**D2 — Two literal phrases, not a regex.** The existing pair is literal (`"olor a gas"`,
`"huele a gas"`). A new pattern matching a verb family would be a second mechanism with its own
drift, and the previous unit already rejected narrowing-by-regex for that reason. Two literals mirror
the existing shape exactly.

**D3 — No spec delta.** EM-1 already requires detecting Spanish expressions for *olor a gas*; the
shipped default list already exceeds the spec's enumeration (the spec does not name `"huele a gas"`
either). This change closes a gap between the requirement and its implementation, it does not change
the requirement. The reasoning is recorded here so the absence of a delta is a decision, not an
oversight.

**D4 — The negation boundary is declared, not fixed.** `"no huelo gas"` will match strong. That is
already true today for `"no siento olor a gas"` via the `"olor a gas"` fragment. Negation-aware
detection is a different change with its own false-negative trade-offs, and on a safety path the
existing bias (escalate a harmless message rather than miss a real one) is the correct one. Pinned by
a test so it stays visible.

## Tasks

### WU1 — the first-person gas smell escalates

- [x] **T1** — RED: `tests/integration/test_emergency.py` — add
      `("huelo gas", "huelo gas en la cocina que hago")` and `("huelo a gas", "huelo a gas")` to
      `EMERGENCY_SENTENCES`, plus the D4 negation assertion; run the emergency suite and observe
      exactly the three new failures.
- [x] **T2** — GREEN: `app/services/settings.py` — add the two phrases to `DEFAULT_EMERGENCY_KEYWORDS`
      (and its comment).
- [x] **T3** — GREEN: re-run the focused set and the full suite; confirm the pinned residual gap
      (`"se escapa el gas"`, `"me esta saliendo gas"`) is still `None`.
- [x] **WU1 commit** — the test and the source together, one work unit (`b4a87254`).
- [x] **T4** — the record: `odd/tasks/emergency-huelo-gas.md` (`5516fc95`, committed before the
      source change).

## Verification

- `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/integration/test_emergency.py tests/integration/test_settings.py -q`
- `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/ -q` (full suite)
- `git diff --name-only` — only the authorized files plus the known untracked artifact.
- `git diff --check` — no whitespace errors.

## Acceptance criteria

1. RED observed before the source change: exactly the two new `EMERGENCY_SENTENCES` rows fail.
2. `"huelo gas en la cocina que hago"` and `"huelo a gas"` classify as `strong`.
3. Every pre-existing default keyword still classifies as `strong`
   (`test_strong_hit_each_default_keyword`).
4. The benign list still classifies as no-hit, and the pinned residual gap
   (`"se escapa el gas"`, `"me esta saliendo gas"`) stays `None`.
5. `"no huelo gas"` is pinned as `strong` (D4), so the boundary is explicit.
6. `get_emergency_keywords` returns the new defaults when nothing is stored, and a stored override
   still wins.
7. Full suite passes.

## Delivery forecast

Estimated well under 100 changed lines across 3 files: 2 lines of source, 2 test rows, and this
record. Comfortably inside the 400-line review budget — no chain, no exception. One PR.

**Result**: +2 lines in `app/services/settings.py`, +11 in `tests/integration/test_emergency.py`
(the two `EMERGENCY_SENTENCES` rows with their comment, and the D4 negation test), plus this record.

## Execution evidence

### RED (observed before the source change)

`eval "$(bash infra/test-db.sh env)" && uv run pytest tests/integration/test_emergency.py -q`

Three failures, all new, all `assert None == 'strong'`:

- `test_strong_hit_each_default_keyword[huelo gas-huelo gas en la cocina que hago]`
- `test_strong_hit_each_default_keyword[huelo a gas-huelo a gas]`
- `test_negated_first_person_gas_smell_is_still_strong`

The pre-existing tests passed at RED, so the three failures are exactly the new coverage.

### GREEN

- Focused: `uv run pytest tests/integration/test_emergency.py tests/integration/test_settings.py -q`
  — pass.
- Full suite: `uv run pytest tests/ -p no:warnings` — **1302 passed in 137.98s**, exit 0.
- Classifier evidence after the change (`compile_keywords(DEFAULT_EMERGENCY_KEYWORDS)`):

| message | result |
|---|---|
| `huelo gas en la cocina que hago` | **strong** |
| `huelo a gas` | **strong** |
| `huele a gas` | strong (unchanged) |
| `se escapa el gas` | `None` (pinned gap, unchanged) |
| `me esta saliendo gas` | `None` (pinned gap, unchanged) |
| `no huelo gas, era el vecino` | strong (D4 boundary, pinned) |

- `git diff --name-only` → `app/services/settings.py`, `tests/integration/test_emergency.py`.
- `git diff --check` → no whitespace errors.

### Commits

- `5516fc95` — `docs(odd): open the emergency-huelo-gas record`
- `b4a87254` — `fix(emergency): escalate the first-person gas-smell phrasings (EM-1)`

### Deviations

- **The D4 negation test is an extra assertion** beyond the two `EMERGENCY_SENTENCES` rows. It was
  written into the RED (it also failed before the source change) and exists to keep D4's boundary
  visible, which is what D4 promises. It is not new scope: it changes no source behaviour.
- **No spec delta** (D3), reasoning recorded above.
- **No RDD review for this unit**: `gentle-ai review mode status` reports
  `off (decided by clone_local)`. Delivery follows ordinary repository policy. Recorded so the
  absence is a fact, not an omission.

## Graph check (Step 1 of the 5-Step Gate)

Consulted before writing: `classify_emergency()` and `compile_keywords()` (`app/services/emergency.py`),
`emergency_gate` (`app/chat/nodes/emergency_gate.py`), `get_emergency_keywords` and `get_setting`
(`app/services/settings.py`), `KeywordsBody` (`app/panel/api/routes/settings.py`), and the emergency
integration suite (`tests/integration/test_emergency.py`). `graphify query "emergency keyword gate
detect classify_emergency compile_keywords"` (depth 2, 270 nodes) confirmed the gate runs before
classification and retrieval, with no other consumer of the keyword list.
