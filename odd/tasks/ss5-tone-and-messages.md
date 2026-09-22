# ODD: ss5-tone-and-messages

## Objective

Make SS-5 real: the owner edits the bot's standard messages and tone from the panel, and the bot
actually uses them. Today the storage half exists and the effect half does not — the panel offers a
tone field that changes nothing, and the standard messages cannot be edited at all.

## Problem

`openspec/specs/settings-scope-limits/spec.md:73` — **SS-5**: *"The system MUST let the owner adjust
the bot's tone, standard messages, and response rules through the panel without code changes."*
Its scenario is explicit: *"GIVEN the owner edits a standard bot message or tone setting… THEN
subsequent bot replies use the edited content."*

Measured on `85db481a` (post #292/#293):

- **`get_message` has zero production callers.** It exists (`app/services/settings.py:202`) and
  resolves `messages.<key>` correctly, but nothing in `app/` calls it except its own docstring.
- **The standard messages are module constants**, used directly:
  - `CANNOT_ANSWER_REPLY` — `app/chat/nodes/respond.py:112` (empty-completion fallback) and `:147`
    (KB miss).
  - `CLARIFICATION_REPLY` — `app/chat/nodes/respond.py:128`.
  - `GREETING_HEADER` — `app/chat/state.py:59` (`greeting_with_menu()`), called from
    `app/chat/nodes/receive.py:21`.
- **There is no panel surface for messages.** The API knows exactly
  `_KNOWN_SECTIONS = {scope, keywords, tone, limits, meta}` (`app/panel/api/routes/settings.py:190`);
  any other section is a 400. The web Settings page has no message editor.
- **The tone is saved, audited, displayed — and never applied.** `get_tone`'s only caller is the
  panel GET route (`:104`), for display. No chat node, prompt, or persona reads `tone.style`
  (grep over `agent/` is empty). The owner saves a tone, the UI confirms, an audit row is written,
  and the reply is byte-identical.
- **`SETTINGS_DEFAULTS` registers no `messages.*` key** (`:102-130`), only `tone.style`.
- The original comment already planned this: `app/chat/state.py:49` — *"Standard replies (SS-5 will
  make them configurable in T4.1; constants here)"*. It was planned, half-built, and never closed.
- The Hito-1 `verify-report.md` declared SS-5 *"COMPLIANT (view; behavior B4)"* with *"reply effect
  proven B4"*. What the tests prove is that the value is **saved and audited**
  (`tests/functional/test_api_kb_settings.py:751`), not that a reply changes.

This is the third declared-but-unconsumed mechanism, alongside `kb_scope` and
`source_meta.category` (retired in #292). It is the only one that **lies directly to an admin**: the
panel offers the control and confirms the save. SS-1 (scope) and SS-2 (keywords) come from the same
service and era and **are** wired (`app/chat/nodes/classify_intent.py:215`,
`app/chat/nodes/emergency_gate.py:43`) — the pattern was demonstrated twice; SS-5 got only the
storage half.

## Why

The owner is **Lumat**. Today, changing what the bot says means calling the developer, editing code
and redeploying. SS-5's point is that Lumat should not have to. That is the value: client autonomy
over the bot's customer-facing voice.

## Scope

**In:**

- The three standard messages become configuration: `messages.greeting`, `messages.cannot_answer`,
  `messages.clarification` gain built-in defaults and the chat resolves them.
- The tone becomes a short validated list (`cercano`, `formal`, `directo`), each with an exact
  instruction injected into the customer chat's system prompt.
- The panel API gains a `messages` section (GET + POST) and validates the tone against the list.
- The panel UI gains a "Mensajes" card and turns the tone input into a selector.
- A chat-level test proving the reply changes (SS-5's scenario) — the test that never existed.

**Out:**

- No change to the deterministic paths' behaviour when nothing is overridden: the defaults are
  byte-identical to today's constants.
- No change to SS-1 (scope) or SS-2 (keywords): both stay wired as they are.
- The tone applies to the customer chat's LLM answer only. The deterministic replies (greeting,
  clarification, cannot-answer) are not LLM output, so the tone does not shape them.
- No tone applied to the internal panel assistant; it has its own persona.
- `source_meta` / KB audience untouched.
- No DB migration: the legacy stored tone value is normalized at read time, mirroring
  `get_scope_mode`'s documented "invalid mode → default" behaviour.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-ss5-tone-and-messages`
- Branch: `odd/ss5-tone-and-messages`
- Base: `85db481a`
- Files: `odd/tasks/ss5-tone-and-messages.md`, `app/services/settings.py`,
  `app/chat/nodes/respond.py`, `app/chat/state.py`, `app/chat/nodes/receive.py`,
  `app/panel/api/routes/settings.py`, `openspec/specs/settings-scope-limits/spec.md`,
  `tests/integration/test_settings.py`, `tests/integration/test_ss5_overrides.py` (new),
  `tests/functional/test_api_kb_settings.py`, `tests/unit/test_prompts.py`,
  `web/src/components/pages/Settings.tsx`, `web/src/types.ts`,
  `web/src/stories/pages/Settings.stories.tsx`, `web/src/stories/pages/Settings.stories.test.tsx`,
  `web/src/stories/pages/_shared/mockData/settings.ts`,
  `web/src/stories/pages/_shared/mockData/settings.test.ts`

## Constraints

- **Strict TDD: ON** — source: `openspec/config.yaml` (`testing.strict_tdd: true`). Runner:
  `uv run pytest tests/`. Observe RED before each source change; never invent RED evidence.
- Frontend runner: `npm --prefix web run test` (Vitest) and `npm --prefix web run build` (tsc).
- Integration tests need `eval "$(bash infra/test-db.sh env)"`.
- Panel UI copy is **Spanish**, plain register (matches `Settings.tsx`).
- Conventional commits, no `Co-Authored-By`. One concern per commit, ≤5 files per commit.

## Design decisions

**D1 — The message defaults move to the settings service; the node constants become aliases.**
`MESSAGE_DEFAULTS` in `app/services/settings.py` is the single source; `SETTINGS_DEFAULTS` registers
`messages.*` from it. `respond.py`/`state.py` keep their public constant names as aliases
(`CANNOT_ANSWER_REPLY = MESSAGE_DEFAULTS["cannot_answer"]`) so the five test files that import them
keep working, and the panel reads the defaults from settings instead of importing chat internals.
Alternative rejected: keeping the copy in the nodes and importing the node constants into the panel —
that adds a panel→chat edge and leaves the config split across two owners.

**D2 — The tone is a validated list, not free text.** `TONE_STYLES = ("cercano", "formal",
"directo")` with `TONE_DIRECTIVES` mapping each to an exact instruction. A free-text tone cannot be
verified and is a prompt-injection surface: the admin could write arbitrary instructions into the
system prompt. The list keeps the directive owned by the code and the choice owned by the owner.

**D3 — The legacy tone value is normalized at read time.** `get_tone` returns the stored value only
when it is in `TONE_STYLES`, else the default — mirroring `get_scope_mode`'s documented behaviour.
No DB migration, and a stale `warm-professional` row degrades to the default instead of reaching the
prompt.

**D4 — `greeting_with_menu` keeps its signature.** It gains an optional `header` parameter defaulting
to `GREETING_HEADER`, and `receive` resolves the override and passes it. This keeps the module-level
call in `tests/integration/test_triage_reply_duplication.py:38` working.

**D5 — `messages.greeting` overrides the header only.** The 8-category menu is generated from
`MENU_CATEGORIES` and is not owner-editable. The panel label must say so, or the owner will think
they edited the menu.

**D6 — The tone reaches the system prompt, and the test asserts the injection, not the vibes.**
`_answer_from_kb` appends the directive to the system message. The behavioural effect of a tone on an
LLM is not deterministically testable; what is testable — and what the test must pin — is that the
directive reaches the prompt. The record states this limit instead of claiming a proven "reply
effect", which is the mistake the Hito-1 verify report made.

## Tasks

### WU1 — the standard messages become configuration

- [ ] **T1** — RED: `tests/integration/test_ss5_overrides.py` — with `messages.cannot_answer` set,
      a KB-miss turn replies with the override, not the constant. Run the graph; observe RED.
- [ ] **T2** — GREEN: `app/services/settings.py` — add `MESSAGE_DEFAULTS` (the three texts, moved
      verbatim), register `messages.*` in `SETTINGS_DEFAULTS`, and make `get_message` fall back to
      the built-in default when the caller passes none.
- [ ] **T3** — GREEN: `app/chat/nodes/respond.py` — alias the two constants from `MESSAGE_DEFAULTS`,
      resolve the override at `:112`, `:147` and `:128` (the clarification path needs a session).
- [ ] **T4** — GREEN: `app/chat/state.py` + `app/chat/nodes/receive.py` — `greeting_with_menu(header=...)`
      and the resolve-and-pass in `receive`.
- [ ] **WU1 commit** — `feat(settings): make the standard messages configurable (SS-5)`

### WU2 — the tone becomes a list and reaches the prompt

- [ ] **T5** — RED: `tests/integration/test_settings.py` — `get_tone` returns the default for an
      unknown stored value; the directive mapping is exact.
- [ ] **T6** — GREEN: `app/services/settings.py` — `TONE_STYLES`, `TONE_DIRECTIVES`,
      `DEFAULT_TONE_STYLE = "cercano"`, the read-time guard, and `get_tone_directive(session)`.
- [ ] **T7** — RED/GREEN: `app/chat/nodes/respond.py` — `_answer_from_kb` appends the directive to
      the system message; `tests/unit/test_prompts.py` pins that the directive reaches the prompt.
- [ ] **WU2 commit** — `feat(settings): replace the free-text tone with a validated list (SS-5)`

### WU3 — the panel API

- [ ] **T8** — RED: `tests/functional/test_api_kb_settings.py` — GET returns the `messages` section
      (and the exact-key assertion is updated); POST `/settings/messages` saves and audits;
      POST `/settings/tone` rejects a value outside `TONE_STYLES` with 400.
- [ ] **T9** — GREEN: `app/panel/api/routes/settings.py` — the `messages` section (GET + POST),
      the tone validation, and `_KNOWN_SECTIONS`.
- [ ] **WU3 commit** — `feat(panel): expose the messages section and validate the tone (SS-5)`

### WU4 — the panel UI

- [ ] **T10** — RED: `Settings.stories.test.tsx` — the tone selector renders the current value and
      saves a chosen one; the Mensajes card renders the three messages and saves an edit.
- [ ] **T11** — GREEN: `web/src/types.ts`, `mockData/settings.ts` + its test, `Settings.tsx`
      (tone `Input` → `Select`; new Mensajes card), `Settings.stories.tsx`.
- [ ] **WU4 commit** — `feat(panel): add the Mensajes card and a tone selector (SS-5)`

### WU5 — spec

- [ ] **T12** — `openspec/specs/settings-scope-limits/spec.md` — SS-5 gains the tone list and a
      scenario for an out-of-list tone being rejected; the requirement text stays otherwise intact
      (it already covers tone + messages + rules).
- [ ] **WU5 commit** — `docs(specs): pin the SS-5 tone list and its validation`

## Verification

- `uv run pytest tests/integration/test_ss5_overrides.py tests/integration/test_settings.py`
- `uv run pytest tests/functional/test_api_kb_settings.py tests/unit/test_prompts.py`
- `uv run pytest tests/` (full suite)
- `npm --prefix web run test` and `npm --prefix web run build`
- `git diff --name-only | grep '^app/'` — only the five intended production files.

## Acceptance criteria

1. With `messages.cannot_answer` set, a KB-miss turn replies with the override; unset, the reply is
   byte-identical to today's constant.
2. The same holds for `messages.clarification` and `messages.greeting` (the greeting header only; the
   menu still renders).
3. The panel API's GET returns the effective `messages`; POST `/settings/messages` saves and audits.
4. `POST /settings/tone` accepts only `cercano`/`formal`/`directo` and rejects anything else with 400.
5. The customer chat's system prompt carries the directive for the stored tone; an unknown stored
   tone degrades to the default.
6. The panel UI shows a Mensajes card and a tone selector, both saving through the API.
7. A chat-level test fails if the wiring is removed (the guard for the SS-5 scenario).
8. Full Python and web suites pass.

## Delivery forecast

Estimated ~620 changed lines across ~17 files, of which ~210 are this record. Above the 400-line
review budget. Two coherent boundaries:

- **One PR with `size:exception`** (as #292): the unit fulfills SS-5 only as a whole — a backend-only
  PR would leave the panel still unable to edit anything.
- **Two chained PRs**: backend + record first (~410), then the panel surface (~230). The first PR
  does not, by itself, fulfill SS-5.

Recommendation: one PR with `size:exception`, on the same argument as #292.

## Follow-ups

- The `messages.<key>` namespace now has exactly three keys. Adding a fourth is a code change (the
  panel section validates against a known-key set), not a free-form KV write — deliberate.
- `source_meta` and the KB audience are untouched by this unit.
