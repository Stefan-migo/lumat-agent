# ODD: kb-triage-scope

**Make the `valores`/`postventa` KB reachable in production.**

## Objective

Remove the dead topical pre-filter that makes every question routed to the
`valores`/`postventa` intents miss the knowledge base, and replace the four test
workarounds that hid it with a test that exercises the production path.

## Problem

Found and measured by the sibling unit `odd/kb-answer-fidelity.md` (F2). The chain:

- `app/services/kb.py:359` filters chunks on `source_meta["category"]`.
- `research_triage` — the sub-graph that owns the `valores`/`postventa` intents
  (`app/chat/nodes/orchestrate.py:33,82-85`) — always passes
  `scope=["valores", "postventa"]` (`agent/registry.yaml:33`,
  `app/chat/subgraphs/research_triage.py:74,98`).
- **No production path writes that field.** The panel upload calls
  `ingest_document` with no `source_meta` (`app/panel/api/routes/kb.py:143-145`), and
  every new version is stored with `source_meta=None` (`app/services/kb.py:235`).

So the scoped filter returns zero chunks for every document a client can actually
upload, and every question routed to those intents escalates to a human regardless
of content. Measured end to end with the real provider: **5 of 30 answerable queries
where unscoped retrieval had the chunk above the gate and the scope filter threw it
away.**

The failure is **silent**. Nothing errors; the customer gets the ordinary handoff
message, which is indistinguishable from a genuine "we don't know". The suite hid it
because all four tests that need the scoped retrieval to work seed the category by
hand (`tests/integration/test_chat_capture.py:189`,
`tests/integration/test_memory_pipeline.py:67`, `tests/integration/test_chat_intent.py:383`,
`tests/integration/test_cost_guardrails.py:608`) — each with a comment admitting the
seed exists only to satisfy the filter.

## Why this fix

The scope mechanism has exactly one consumer in the whole repository: this call. Its
only measured effect, across 52 real queries, was to delete the correct chunk. It
cannot add recall — a pre-filter can only remove. And it fails without a signal.

`scope=None` is not a workaround: AO-7 states it "returns the unfiltered
active-version set (backward compatible)" and `agent/registry.yaml:8-12` already
documents `null` as "the intended 'no restriction' declaration". This is the
declaration the other entries already use.

## Scope

**In:** `agent/registry.yaml` (the `research_triage.kb_scope` value and the header
comment that describes its wiring), the four test workarounds, the registry
assertion that pins the old value, one new regression test, and this record.

**Out (explicitly):**

- **Deleting the `scope` filter.** `kb.retrieve(scope=...)` is spec'd by AO-7 and
  covered by `tests/integration/test_kb.py:421-460`. After this change no caller
  passes a non-null scope, so the capability is unused — recorded as a follow-up for
  a separate decision, not deleted here. Deleting it needs an AO-7 spec delta.
- **The `source_meta.category` axis and the panel upload.** Populating the category
  was the alternative fix and was rejected (D1). `category` stays unwritten.
- **F3 (bare `gas` weak emergency hit), F4 (capture routing), F5 (`unknown`
  classification).** Separate causes of the same measured unavailability, each its
  own decision. This unit fixes one of four.
- No change to `min_sim`, `top_k`, ranking, chunking, prompts, audience, or the
  sub-graph's flow.

## Spec constraints (binding — do not violate)

- `openspec/specs/agent-orchestration/spec.md` — **AO-7**. Its two scenarios still
  hold: `scope` filters when passed, and `scope=None` is unfiltered. The requirement
  text names research_triage as the example of a scoped sub-agent; with this change
  the roster has no scoped sub-agent, which the requirement permits (it says a
  sub-agent with `kb_scope` *may* only retrieve within it — none is required to have
  one).
- **AC-4** — the `agent:` block shape is frozen and asserted in
  `tests/unit/test_prompts.py:113-114`. Untouched: only a `sub_agents:` value moves.
- `openspec/specs/knowledge-base/spec.md` — **KB-2** and **KB-5**. Untouched.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-kb-triage-scope`
- Branch: `odd/kb-triage-scope`
- Base: `01f8ceda` (= `origin/main` at branch time, includes PR #275). Verified with
  `git merge-base HEAD origin/main`. Note: `rapso worktree create` branches from the freshest
  `origin/main`, not from the local `main`, so the base recorded before the worktree existed was one
  merge behind.
- Files:
  - `odd/tasks/kb-triage-scope.md`
  - `agent/registry.yaml`
  - `tests/unit/test_agent_registry.py`
  - `tests/integration/test_chat_capture.py`
  - `tests/integration/test_memory_pipeline.py`
  - `tests/integration/test_chat_intent.py`
  - `tests/integration/test_cost_guardrails.py`
  - `tests/integration/test_kb_triage_scope.py` (new regression test)

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml` (`testing.strict_tdd: true`); runner
  `uv run pytest`.
- Test DB: `eval "$(bash infra/test-db.sh env)"` is required before pytest, or the
  migrations connect as the unprivileged `app` role and fail with a misleading
  password error (pre-existing harness quirk).
- `agent/registry.yaml` is parsed at import; a malformed edit fails boot.
- Known worktree artifact: `rapso worktree create` leaves
  `.opencode/tools/package-lock.json` untracked. Declare it to the review preflight,
  never commit it.
- No commit, push, or PR from a delegated phase unless the orchestrator authorizes it.

## Decisions

- **D1 — `kb_scope: null` on `research_triage`, not a populated category.** The
  alternative (collect a topic on upload, store it in `source_meta`, backfill
  existing documents) respects AO-7 as literally written and was rejected on three
  measured grounds: (a) it needs a topic vocabulary the client has not agreed to and
  a per-document operator decision on every upload; (b) its failure mode is the same
  silent one — a mis-categorized document simply never surfaces, and nothing
  reports it; (c) it buys no recall, because the filter can only remove candidates
  that relevance ranking already ordered. Recorded in
  `odd/kb-answer-fidelity.md` as the losing option.

- **D2 — The four seeded categories are REMOVED, not left in place.** A fixture that
  seeds `{"category": "valores"}` only to satisfy a filter the production path cannot
  satisfy is a false statement about production. Leaving them would keep the defect
  invisible after the fix. Removing them turns four existing tests into evidence that
  the unscoped path works — and if the scope ever returns, they fail.

- **D3 — The `scope` filter and its AO-7 tests stay.** `kb.retrieve(scope=...)` is a
  spec'd capability with its own coverage (`tests/integration/test_kb.py:421-460`).
  Removing it is a spec delta and a different decision from removing its only caller.
  After this change the capability has no production consumer; that is recorded here
  as the honest state, not silently cleaned up.

- **D4 — A dedicated regression test asserts the production path, not the fix's
  implementation.** The new test ingests a document **exactly as the panel does** (no
  `source_meta`) and asserts that a `valores`-classified message produces a grounded
  reply instead of a `kb_miss` handoff. Asserting `kb_scope is None` alone would pin
  the value and not the behaviour; the behaviour is what was broken.

## Tasks

- [x] **T1** — `odd/tasks/kb-triage-scope.md` (this record).
- [x] **T2** — RED: `tests/integration/test_kb_triage_scope.py`, written against the unfixed
      registry. Observed failure: both tests received
      `[greeting, greeting, HANDOFF_REPLY]` — the `kb_miss` handoff the fix removes.
- [x] **T3** — `agent/registry.yaml`: `research_triage.kb_scope` → `null`, plus the header note
      that claimed runtime wiring for a scope.
- [x] **T4** — Removed the four seeded categories and their now-false comments; the
      `test_agent_registry.py` assertion now pins `None`.
- [x] **T5** — GREEN plus the before/after measurement below.

## Findings

### The fix works, measured with the real provider on the same 52 queries

Before/after on the sibling unit's harness, same corpus, same threshold (`min_sim=0.50`),
same model (`deepseek/deepseek-flash`). The only difference is this one registry value.

| | before | after |
|---|---|---|
| `kb_miss` handoffs (all classes) | 8 | **2** |
| answerable queries that reached the answer layer | **0** | **4** |
| answerable `handed_off` | 14 | 10 |

The two remaining `kb_miss` are **correct**: they are the corpus's internal-only answerable
queries, which the `customer` audience filter must hide (the audience axis working as designed,
F6 of the retrieval slice).

**The four answers are faithful, and this is the first fidelity sample the KB has ever produced.**
The ungrounded-number check is empty on all four, and the numbers match their chunks:

- "cuanto cuesta la mantencion del calefont" → "45.000 pesos", matching
  `Mantención de calefón: 45.000 pesos` at similarity 0.6814.
- "cuanto cobran por instalar un calefont" → "$95.000", matching
  `Instalación de calefón: 95.000 pesos` at similarity 0.6852.
- "los trabajos tienen garantia" → "6 meses de garantía de mano de obra y 1 año de garantía en
  los repuestos", matching its chunk at 0.5868.
- "como puedo pagar el trabajo" → the payment methods, matching its chunk at 0.516.

### F9 (new, out of scope) — every `research_triage` turn duplicates the replies accumulated before it

Measured: **8 of 8** `kb_miss` turns in the before run returned
`[greeting, greeting, HANDOFF_REPLY]` — three replies where the customer should get two. `receive`
was instrumented and ran **once**, so the duplication is not node execution: the sub-graph shares
`ConversationState` as both its input and its output schema, and `replies` carries an `add`
reducer (`app/chat/state.py:175`, `Annotated[list, add]`). Merging the sub-graph's final state back
into the parent re-adds the parent's already-accumulated replies.

This change makes F9 **more visible, not less**: after the fix the duplicate greeting appears on
the `valores`/`postventa` *hits* too (7 of 52 turns, of which 5 are now answers). Before, it only
showed on the misses. The fix for it is a graph-wiring change — give the sub-graph explicit
input/output schemas so `replies` is not merged twice — and it is a separate unit. Recorded here
because this unit's evidence is where it surfaced, and because leaving it unrecorded would let the
next person read the duplicate menu as a prompt problem.

### Honest caveat on the outcome classifier

The `answered` bucket contains both grounded answers and **free-text refusals**. One `near_miss`
turn ("cuanto sale instalar un tanque de agua") came back as prose declining to answer —
"No puedo responderte eso con seguridad: en la información que manejo no aparecen precios ni el
servicio de instalación de un tanque de agua" — which is the CM-4 prompt contract working through
the model, not a fabrication. Its `ungrounded` list is empty, which supports that reading. The
deterministic classifier cannot separate the two, so `answered_rate` is an upper bound on real
answers; separating them needs the `--judge` pass or a human. This is the same gap decision D1 of
the KB backlog recorded: a free-text refusal sets neither `escalate` nor `log_unresolved`.

## Acceptance criteria — result

1. The regression test failed before T3 (both tests, `HANDOFF_REPLY` present) and passes after.
2. The seven focused suites → **96 passed**.
3. `uv run pytest tests/` → **exit 0, 100% reached** (~1050 tests, no failures or errors). Note:
   `pyproject.toml` sets `addopts = "-q"`, so adding `-q` on the command line suppresses the final
   count line — read the exit code and the progress percentage, not a summary string.
4. `git status --short` shows only the authorized files plus the known untracked
   `.opencode/tools/package-lock.json`.
5. Before/after recorded above with the real provider.

## Applicable checks

- `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/integration/test_kb_triage_scope.py -q`
- `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/unit/test_agent_registry.py -q`
- `git diff --name-only` → only the authorized files
- `git diff --check` → no whitespace errors
- Re-measurement: the sibling worktree's `scripts/kb_fidelity.py` with the same
  corpus and provider, with and without this change applied to its registry.

## Graph Check (Step 1 of the 5-Step Gate)

Consulted before writing: `research_triage._kb_check` and `_registry_kb_scope`, the
`orchestrate` router (`RETRIEVAL_INTENTS`, `RESEARCH_TRIAGE`), `kb.retrieve`'s scope
filter, `kb.ingest_document` / `_store_chunks`, the panel upload call site,
`get_registry` / the `SubAgent` shape, and the four integration fixtures that seed
`source_meta.category`. `graphify query "knowledge base retrieval and calibration"`
(depth 2, 407 nodes) is what confirmed the scope mechanism has exactly one consumer
and that no third `kb.retrieve` call site exists.
