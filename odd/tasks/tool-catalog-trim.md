# ODD: tool-catalog-trim

**Branch**: `odd/tool-catalog-trim`
**Worktree**: `/home/stefan/repos/lumat-agent-odd-tool-catalog-trim`
**Base**: `059a275a` (= `main` = `origin/main` at branch time, merge of PR #392)
**Status**: merged — PR #394 (`ed88ae43`, 2026-09-28). Worktree and branches cleaned.

## Objective

Cut the per-turn token cost of the assistant planner tool catalog by removing the
presentation-only `title` keys from the JSON Schema each tool advertises, without removing or
weakening a single announced argument rule.

## Problem

The catalog sent to the planner costs ~2.647 tok/turn (10.587 chars, 24 tools; measured
2026-09-27 at `7b205ea6` and re-confirmed unchanged at `059a275a`). Pydantic emits a `title`
key for every property, every `$defs` entry and the model itself. No validator reads `title`:
it is presentation metadata that ships on every turn.

## Why — the trim must not become the flat-schema change

`b597f3da` ("fix(assistant): declare the memory read scope contract in the tool schema",
2026-09-21) introduced the discriminated union precisely because a rule expressed in a
`field_validator`/`model_validator` **does not appear in `model_json_schema()`**, and that
schema is what `_planner_tool_catalog` sends to the planner. Before that fix, `panel` with
`entity_id="thread:158"` was rejected and `agent` without the canonical entity was rejected
too; only two shapes worked.

Flattening the union into a single object plus a validator — the shape first measured as
"option A" — would hide the `scope`/`entity_id` rule again and resurrect exactly that bug.
The safe form of the same cut is to strip presentation only.

Measured with the same method (`_planner_tool_catalog(list(TOOL_REGISTRY))`, `chars / 4`):

| shape | chars | tok/turn | delta |
|---|---|---|---|
| baseline | 10.587 | ~2.647 | — |
| **strip `title`** | **8.851** | **~2.213** | **−434 (−16.4%)** |
| + `additionalProperties` | 8.069 | ~2.017 | −630 total |
| + `discriminator` | 7.807 | ~1.952 | −695 total |
| + `$defs`/`oneOf` | 6.099 | ~1.525 | breaks the announced contract |

The strip preserves the announced contract exactly: `$defs`, `oneOf`, `discriminator`,
per-scope `const`, the customer `entity_id` `pattern`, the `null` own `entity_id`, and every
`required` list.

## Scope

**In**
- `app/chat/assistant/nodes.py` — `_planner_tool_catalog` stops emitting `title` keys.
- Unit coverage that the announcement loses no rule and gains no restatement.
- The pinned catalog hash in `tests/unit/test_assistant_delegation.py` is re-baselined.

**Out**
- `app/chat/assistant/tools/registry.py` — the argument models and their declared contract are
  untouched. `ToolDefinition.schema()` and `model_json_schema()` keep returning the full schema.
- `additionalProperties: false` (it is contract: "send no extra keys"), `discriminator` (a
  useful hint for 65 tok) and `description` (prose the planner reads).
- Removing any tool; the whitelist invariant; delegation semantics; approval digests; bounds.

## Constraints

- Bounds are bounds: `_TOOL_EVIDENCE_LIMIT` (4.000), `MAX_ASSISTANT_TOOL_STEPS` (2),
  `DELEGATION_SPAN_MAX_STEPS` (2), `MAX_ITEMS` are unchanged.
- The trim lives at the presentation boundary only, so nothing that validates a plan changes.
- Merge commits, exactly one `type:*` label, no `Co-Authored-By` and no AI attribution.

## Tasks

- [x] **T1 (RED)** Unit test: the serialized catalog carries no `title` key at any depth, and
      `memory.read` still announces both scope variants with their exact rules.
      RED observed: `AssertionError` at `assert "title" not in value`, first offender
      `title: 'CapabilitiesArgs'`.
- [x] **T2 (GREEN)** Implement the recursive `title` strip in `_planner_tool_catalog`.
      Implemented as a nested `without_titles` helper; `registry.py` untouched.
- [x] **T3** Re-baseline the pinned catalog hash in `tests/unit/test_assistant_delegation.py`.
      `e522ed87…1eb9f6` → `7d967c04…e58f0ab`, recomputed independently by the orchestrator and
      matching the implemented value.
- [x] **T4** Verify: full suite green, and re-measure the catalog end to end.

## Acceptance criteria

- **AC1** `json.loads(_planner_tool_catalog(list(TOOL_REGISTRY)))` contains no `title` key at
  any depth.
- **AC2** Every existing assertion about the announced per-scope contract still holds
  unchanged: `$defs` present, `const` per scope, customer `pattern`, own `null`, `required`.
- **AC3** The re-measured catalog is ≤ 8.900 chars (~2.225 tok), i.e. the −434 tok trim is real
  end to end, not just in the prototype.
- **AC4** The full suite passes; the only test that changes meaning is the pinned catalog hash.

## Checks

- Graph nodes consulted: `Planner Tool Catalog` (`odd/tasks/planner-tool-schemas.md`),
  `Registry` / `Assistant` (`app/agent_registry.py`), `ToolValidationError` and `registry.py`
  (`app/chat/assistant/tools/registry.py`), `unit/test_assistant_tools.py`,
  `test_assistant_harness_guardrails.py`.
- Strict TDD ON (declared by the assistant-closeout handoff), runner `uv run --no-sync pytest tests/`.
- Test DB: `eval "$(bash infra/test-db.sh env)"`. Do **not** source `infra/.env` — it exports
  `DATABASE_URL` pointing at the compose host `db`, which is unresolvable from the host and
  breaks `migrated_db`.
- `--no-sync` is mandatory: `uv run` without it rewrites `uv.lock`.

## Delivery

- Forecast: ~60–80 authored changed lines across 3 files — far below the ~400-line budget.
  Single PR, no chaining.

## Progress

**Implementation** — `dc5049b1` `perf(assistant): drop presentation-only schema titles from the
planner catalog` (3 files, +46 / −3).

**Acceptance criteria — verified by the orchestrator, not only by the writer**

- **AC1** pass. `"title"` appears nowhere in the serialized catalog; the new unit test walks the
  parsed structure asserting no `title` key at any depth.
- **AC2** pass. `$defs`, `oneOf` and `discriminator` are still present, both scope variants are
  announced, the customer `entity_id` keeps `pattern` `^(?:customer:\d+|\d+)$`, the own
  `entity_id` keeps `type: null`, and the new test asserts the advertised per-scope `required`
  lists equal the registry model's own. Every pre-existing assertion about the announced
  contract still passes unchanged.
- **AC3** pass. Re-measured independently: `24 8851 2213` (`tools chars tok`), i.e. 8.851 ≤ 8.900
  and −434 tok/turn (−16.4%) versus the `24 10587 2647` baseline.
- **AC4** pass. Full suite: 1.534 tests, 0 failures, exit code 0. Orchestrator spot check over
  the five directly affected files: 191 passed.

**Native review (RDD on, global)** — two lineages, both `approved` with zero findings, both
authority burned by acknowledgement:

- `review-3a87733c0eba3a00` — the implementation candidate, base `059a275a`, tier `medium`, lens
  `review-reliability`, correction budget 78 and unused (no findings).
- `review-ad7d576beb3d6c0b` — the merged tree, base `97deffc1`, tier `medium`, lens
  `review-reliability`, correction budget 94 and unused (no findings).

The second review was required, not redundant. Bringing `origin/main` into the branch for this
repo's pre-merge discipline moved the base, and the native authority returned `unrelated` /
`fresh_target_ready` for the new tree even though its `paths_digest` was identical to the first.
Consent is per candidate and does not carry over. Doing the base merge-in **before** the first
review would have saved a whole cycle.

**Delivery** — PR #394 (`odd/tool-catalog-trim` → `main`, label `type:refactor`), merged as
`ed88ae43` on 2026-09-28T00:38:51Z. CI on the merged tree (run 36362788581): `test` pass 1m57s,
`panel` pass 2m43s, GitGuardian pass. Test DB brought down; worktree, local branch and remote
branch cleaned; local `main` synced to `ed88ae43`.

**Closed** — nothing pending. This docs-only PR exists solely to correct this record.
