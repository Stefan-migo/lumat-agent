# ODD: r3-deferred-warnings

**Branch**: `odd/r3-deferred-warnings`
**Worktree**: `../lumat-agent-odd-r3-deferred-warnings`
**Base**: `959e93a4` (= `main` at branch time)
**Status**: merged — PR #313 (`28b72cf4`). Native review approved (lineage `review-ec730c06ffe3d86e`).

## Objective

Close, in one work unit, the two non-blocking WARNINGs the native review left on the `memory.update` /
`memory.delete` unit (#311) and the `assistant.capabilities` unit (#312), both merged on 2026-09-23.

## Problem

### W1 — `review_after` is not recomputed when only `tipo` changes

`app/services/tukulpan.py`, `update()` (L589-612):

```python
content_changed = contenido is not None and contenido != row.contenido
if titulo is not None:
    row.titulo = titulo
if tipo is not None:
    row.tipo = tipo
if content_changed:
    row.contenido = contenido
    row.embedding = _embed([contenido])[0]
    row.normalized_hash = _normalized_hash(contenido)
    row.review_after = _review_after(row.tipo)   # <- nested in content-only branch
```

`row.review_after = _review_after(row.tipo)` sits inside the `content_changed` branch, so a change of
**only** `tipo` leaves the review schedule attached to the old type. `DECAYING_TYPES = {SUMMARY, SESSION,
DISCOVERY}` decay; `decision` / `pattern` / `preference` do not. Consequence: a `decision` promoted to
`summary` (or the reverse) keeps a schedule that contradicts its own type.

### W2 — `tool_count` can contradict the truncated text

`app/chat/assistant/tools/registry.py`, `_assistant_capabilities` (L444-456):

```python
return {
    "tool_count": len(whitelist),
    "capabilities": "\n".join(lines)[:CAPABILITIES_TEXT_LIMIT],
}
```

The handler truncates the joined text to `CAPABILITIES_TEXT_LIMIT = 4_000` chars but returns the full
`len(whitelist)`. If the truncation ever fires, `tool_count` asserts a completeness the text does not
have. Measured on this unit's base (`959e93a4`: 22 tools): **1,326 chars** against the 4,000-char
limit — **latent, not active**. AT-12 ("MUST preserve the exact tool count") is only safe while it
stays latent. (The 1,212 / 20-tool figure recorded here earlier was carried over from the capabilities
unit's own base, `d4b58554`, and never matched this branch.)

## Why this shape

- **W1**: the review schedule is a function of the type, and a content rewrite also resets the clock.
  The correct predicate is `tipo is not None or content_changed`. A title-only change must keep the
  current schedule untouched.
- **W2** (delete, do not add): the correct bound already lives in the right layer,
  `app/chat/assistant/nodes.py` → `_render_tool_evidence()`, which truncates with a visible ellipsis.
  Keeping a second, silent bound in the handler duplicates a concern and hides information. Removing
  `CAPABILITIES_TEXT_LIMIT` and the slice makes the handler complete by construction and makes AT-12
  true trivially.

## Correction to the handoff (#4732)

The handoff states that "a change of only title must not touch `review_after` ... there is a test that
covers it". **Verified false.** No test exercises `update()`'s `review_after` at all:
`tests/spec/test_memory_spec.py` covers `upsert` / rewrite / fold staleness but never `update()`, and
`tests/unit/test_assistant_tools.py:727` (`test_memory_service_update_reembeds_only_changed_content`)
only asserts the embedder was or was not called. So the title-only invariant is **assumed, not covered**,
and this unit adds it as a real assertion rather than merely avoiding a break.

## Scope (authorized)

- **IN**: W1 and W2, with their tests and the AT-12 wording change.
- **OUT (separate decisions, explicitly deferred by the human)**: W3 (the 22-vs-20 tool-count comment in
  `tests/integration/test_assistant_harness_guardrails.py:301` vs `odd/tasks/assistant-capabilities-tool.md`)
  and the `.opencode/tools/package-lock.json` hygiene (commit vs gitignore). Neither is touched here.

## Constraints

- Strict TDD: RED observed before the implementation, then GREEN, then refactor.
- One concern per commit.
- No push, no PR, no merge without an explicit request.
- Do not reopen or re-run review on the already-merged candidates; this is a new candidate with its own
  assessment and review.

## Resolved execution config

- **TDD**: ON — source `openspec/config.yaml:38` (strict TDD mode active).
- **Test runner**: `uv run pytest tests/`.
- **Graph Check** (mandatory, consulted before editing): nodes `update()` (`app/services/tukulpan.py:589`),
  `_review_after()` (`tukulpan.py:168`), `DECAYING_TYPES` (`tukulpan.py:61`), community `tukulpan.py`;
  `_assistant_capabilities` (`app/chat/assistant/tools/registry.py:444`), `ToolDefinition` (`registry.py:459`),
  `execute_tool()` (`registry.py:512`), community `unit/test_assistant_tools.py`; edge `registry.py` →
  `nodes.py` (`_render_tool_evidence`).

## Checklist

- [x] **T1 — RED, W1**: add a test asserting that changing only `tipo` recomputes `review_after`
      (non-decaying → decaying sets it; decaying → non-decaying clears it). Observe it fail.
- [x] **T2 — GREEN, W1**: change the predicate in `update()` to `tipo is not None or content_changed`.
- [x] **T3 — Guard, W1**: add a test asserting a title-only change does **not** touch `review_after`.
      This invariant has no coverage today (see correction above).
- [x] **T4 — RED/GREEN, W2**: delete `CAPABILITIES_TEXT_LIMIT` and the slice in `_assistant_capabilities`;
      delete `test_assistant_capabilities_bounds_text` and the now-unused import; keep
      `test_assistant_capabilities_reports_every_whitelisted_tool_without_truncation` green.
- [x] **T5 — Spec**: update AT-12 wording in `openspec/specs/assistant-tools/spec.md` so it no longer
      claims a handler-owned text limit; assert completeness + exact count instead.
- [x] **T6 — Verify**: full suite green on a real test DB.
- [x] **T7 — RDD**: assess the branch and follow the returned transition.

## Acceptance criteria

- A change of only `tipo` produces a `review_after` consistent with the new type.
- A change of only `titulo` leaves `review_after` untouched.
- A content change still re-embeds and recomputes `review_after`.
- `_assistant_capabilities` returns one line for every whitelisted tool and an exact `tool_count`, with
  no second silent bound in the handler.
- AT-12 reads consistently with the code.
- Full test suite passes.

## Verification evidence

- **RED (T1)**: `test_memory_service_update_recomputes_review_after_when_tipo_becomes_decaying` failed with
  `AssertionError: assert None is not None`; `..._clears_review_after_when_tipo_becomes_non_decaying`
  failed because the stale `review_after` survived. Observed before the predicate change.
- **GREEN (T6)**: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/` — 1297 passed, 2 warnings.
  Re-run by the parent after the doc commit: exit 0.
- **Commits**: `e726abfb fix(memory): recompute review schedule when type changes`,
  `ba300b91 fix(assistant): keep capability inventory complete`,
  `0e671cd7 docs(odd): record r3-deferred-warnings work unit`.
- **RDD (T7)**: candidate 5 files / 204 lines, tier `medium`, one lens `review-reliability`,
  correction budget 102. Result: **approved with zero findings**; authority burned via
  `review acknowledge-approved` (lineage `review-ec730c06ffe3d86e`, consumed revision
  `sha256:38ec480b99ef6efdc1f1e3fb5e740d906b999d141ce8dbce0bf2204b2a282949`).
- **Graph Check**: nodes listed under "Resolved execution config" were consulted before editing.

## Next step

Open the PR for `odd/r3-deferred-warnings` when the human asks. W3 and the `package-lock.json` hygiene
remain separate decisions and were not touched.
