# ODD: r3-deferred-warnings

**Branch**: `odd/r3-deferred-warnings`
**Worktree**: `../lumat-agent-odd-r3-deferred-warnings`
**Base**: `959e93a4` (= `main` at branch time)
**Status**: in progress

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
have. Measured: 1,212 chars with 20 tools, against a 4,000-char limit — **latent, not active**. AT-12
("MUST preserve the exact tool count") is only safe while it stays latent.

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

- [ ] **T1 — RED, W1**: add a test asserting that changing only `tipo` recomputes `review_after`
      (non-decaying → decaying sets it; decaying → non-decaying clears it). Observe it fail.
- [ ] **T2 — GREEN, W1**: change the predicate in `update()` to `tipo is not None or content_changed`.
- [ ] **T3 — Guard, W1**: add a test asserting a title-only change does **not** touch `review_after`.
      This invariant has no coverage today (see correction above).
- [ ] **T4 — RED/GREEN, W2**: delete `CAPABILITIES_TEXT_LIMIT` and the slice in `_assistant_capabilities`;
      delete `test_assistant_capabilities_bounds_text` and the now-unused import; keep
      `test_assistant_capabilities_reports_every_whitelisted_tool_without_truncation` green.
- [ ] **T5 — Spec**: update AT-12 wording in `openspec/specs/assistant-tools/spec.md` so it no longer
      claims a handler-owned text limit; assert completeness + exact count instead.
- [ ] **T6 — Verify**: full suite green on a real test DB.
- [ ] **T7 — RDD**: assess the branch and follow the returned transition.

## Acceptance criteria

- A change of only `tipo` produces a `review_after` consistent with the new type.
- A change of only `titulo` leaves `review_after` untouched.
- A content change still re-embeds and recomputes `review_after`.
- `_assistant_capabilities` returns one line for every whitelisted tool and an exact `tool_count`, with
  no second silent bound in the handler.
- AT-12 reads consistently with the code.
- Full test suite passes.

## Verification evidence

- (pending) T1 RED output, final full-suite run, RDD assess transition.

## Next step

Implement T1 → T5, then run the full suite and the RDD assessment.
