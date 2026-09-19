# ODD: dsml-responder-guard

## Objective

Stop the panel assistant's response writer from leaking the model's native tool-call markup
(DeepSeek DSML) into assistant text, while preserving the declared-tool-inventory behavior added by
`assistant-responder-tool-inventory`.

## Problem (verified)

The no-tool responder path (`respond_stream` -> `execute()` in its respond branch,
`app/chat/assistant/nodes.py:565-628`) calls the LLM in streaming mode with **no** `tools=` /
`tool_choice` parameter, yet its prompt advertises the assistant tool inventory through the
`available_tools` slot (`app/chat/assistant/nodes.py:585`,
`agent/prompts/assistant_respond.md:3`).

A model that knows tool names but has no tool channel emits its native tool-call markup as plain
text. The markup reaches the user twice:

1. live, through `on_token(token)` for every streamed chunk (`nodes.py:607-610`), which
   `app/services/agent_chat.py:638-646` publishes as the live preview; and
2. persisted, because the response is the joined chunks (`nodes.py:613`) and
   `app/services/agent_chat.py:723-732` persists it as the assistant message.

Neither the persona (`agent/personas/assistant.md:1`) nor the prompt forbids emitting tool-call
markup from this non-invoking call, and no sanitization exists anywhere in `app/`.

### Markup grammar the guard must cover

Format per the DeepSeek V4 encoding README and the observed leak reports:

- Delimiter is the fullwidth vertical bar `U+FF5C` (`\uff5c`), observed as a single bar, a doubled
  bar (`\uff5c\uff5c`), a no-leading-bar variant, and an ASCII-pipe transcoding (`|`).
- Outer wrapper kinds: `tool_calls` (V4) and `function_calls` (V3.2, plural/singular), plus
  `tool_use_error`. Inner elements: `invoke name="..."`, `parameter name="..." string="true|false"`.
- Parameter values commonly contain literal newlines, so matching must be DOTALL.
- The START wrapper can be omitted at long context while a complete `invoke` block is still
  emitted, so the guard must also strip a bare invoke block and any leftover marker token.

### Constraint from the prior unit

`tests/integration/test_assistant_harness_guardrails.py:190-219`
(`test_responder_user_prompt_carries_the_declared_tool_inventory`) asserts every whitelisted tool
name appears in the responder prompt. The inventory MUST stay. Do not remove the `available_tools`
slot; disambiguate it instead.

## Decisions

- **D1 — Disambiguate, do not remove.** Keep `available_tools`; the responder prompt states these
  are capabilities the panel can run, that this call cannot invoke them, and that it must answer
  with text only and never emit tool-call markup.
- **D2 — Guard at the output boundary.** A bounded sanitizer strips DSML blocks and leftover marker
  tokens from the streamed text before it is emitted and persisted. It is defense in depth, not a
  replacement for D1.
- **D3 — Streaming-safe.** Markup can span chunks, so the guard holds back a bounded tail that
  could be a partial marker and flushes at end of stream. The live preview and the persisted
  response must both be clean.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-dsml-responder-guard`
- Branch: `odd/dsml-responder-guard`
- Base: `d78336b8` (`origin/main`)
- Files: `odd/tasks/dsml-responder-guard.md`, `agent/prompts/assistant_respond.md`,
  `app/chat/assistant/nodes.py`, `app/chat/assistant/markup.py` (new),
  `tests/unit/test_assistant_markup.py` (new),
  `tests/integration/test_assistant_harness_guardrails.py`

## Out of scope

The planner path, the customer-facing WhatsApp responder (`app/chat/nodes/respond.py`), native
function-calling for the responder, the persona, the registry, and any change to the assistant
declared surface.

## Constraints

- **Strict TDD: ON** — source: project configuration (`openspec/config.yaml`, runner
  `uv run pytest tests/`). Observe RED before each source change.
- Test DB: `eval "$(infra/test-db.sh env)"` first; this worktree derives port 5868.
- Artifacts in English.
- No commit, push, or PR without orchestrator authorization.

## Tasks

- [x] **T1** — `agent/prompts/assistant_respond.md`: state that the listed tools are panel
      capabilities, that this reply cannot invoke them, and that no tool-call markup may be
      emitted. RED: a guardrail test asserting the responder prompt carries the non-invocation
      instruction fails before the prompt edit.
- [x] **T2** — `app/chat/assistant/markup.py`: `strip_tool_call_markup(text)` covering the
      wrapper kinds, both delimiter widths, the ASCII variant, DOTALL bodies, the omitted-START
      invoke block, and leftover marker tokens; plus a bounded streaming sanitizer that holds back
      a partial-marker tail and flushes. RED/GREEN in `tests/unit/test_assistant_markup.py`.
- [x] **T3** — `app/chat/assistant/nodes.py`: route the streamed chunks and the joined response
      through the sanitizer so neither the live `on_token` output nor the persisted response
      carries markup. RED/GREEN: an integration test whose fake client streams a DSML block split
      across chunks and asserts the emitted tokens and the persisted response contain no marker.
- [x] **T4** — Verification: focused tests, `tests/unit`, `tests/integration`, and the guardrail
      test proving the declared inventory is still present.

## Acceptance criteria

1. The responder prompt still carries every declared tool name (existing test stays green) and
   states that this call cannot invoke tools and must emit no tool-call markup.
2. `strip_tool_call_markup` removes complete DSML blocks (both wrapper kinds, single/double/ASCII
   delimiters, multiline parameter bodies) and leftover marker tokens, and leaves ordinary text
   untouched.
3. A streaming DSML block split across chunks never reaches `on_token` as raw markup.
4. The persisted assistant response contains no marker.
5. Full focused suites green; only authorized files changed.

## Checks

- `eval "$(infra/test-db.sh env)" && uv run pytest tests/unit/test_assistant_markup.py -q`
- `eval "$(infra/test-db.sh env)" && uv run pytest tests/integration/test_assistant_harness_guardrails.py -q`
- `eval "$(infra/test-db.sh env)" && uv run pytest tests/unit tests/integration -q`
- `git status --short` / `git diff --check`

## Progress

- [x] ODD record created before the first source change.
- [x] Worktree created (`rapso worktree create dsml-responder-guard`, base `origin/main` `d78336b8`).
- [x] Provisioned: `infra/.env` copied, `uv sync`, test DB up (port 5868).
- [x] Graph Check: `graphify-out/GRAPH_REPORT.md` read (built from `d78336b8`) and
      `graphify query "assistant responder stream on_token available_tools prompt"` run. Nodes
      consulted: `execute()` (`nodes.py`), `respond_stream` (`graph.py:62,90`), `available_tools`
      slot (`agent/prompts/assistant_respond.md`), `load_assistant_config` (`prompts.py:135`),
      `agent_chat.py` streaming/persistence edges, `test_assistant_harness_guardrails.py`.
- [x] T1-T3 implemented: clarified the text-only responder prompt, added DSML stripping with
      bounded streaming sanitization, and routed live plus persisted responder output through it.
- [x] T4 verification completed: focused markup, guardrail, unit, and integration suites passed;
      `git diff --check` passed.
- [x] Corrected the sanitizer and tests to use the real DSML grammar after gate reproduction:
      wrapper tags are `tool_calls`/`function_calls`/`function_call`/`tool_use_error`, closes have
      a leading slash, and single/double fullwidth plus ASCII delimiters are covered.
- [x] Fixed native-review defects: suppression now retains a bounded split-close tail, and
      unterminated wrapper/invoke constructs strip their bodies through end of input.

## Review (native RDD)

_Not started. Filled in at the delivery boundary._

## Next step

All tasks complete. Nothing committed, pushed, or opened as a PR.
