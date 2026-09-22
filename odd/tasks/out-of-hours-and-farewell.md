# ODD: out-of-hours-and-farewell

## Objective

Give the customer-facing WhatsApp chat the two standard messages it does not have: a **farewell**
when the customer closes the exchange, and an **out-of-hours notice** when the business is closed.

Both are listed in the client checklist (`docs/solicitud-al-cliente-lumat.md:213-214`). SS-5 delivered
the greeting and the tone; these two have no path in the code.

## Problem

Measured on `base` = `d7a3c3aa`, not recited.

- **`rg -i "despedida|farewell|fuera de horario|off_hours|after_hours|horario de atencion|business_hours"`
  over `app/`, `agent/`, `web/src/` returns zero results.** The behavior does not exist.
- **The customer chat has no social path at all.** `receive` (`app/chat/nodes/receive.py`) sends the
  greeting + menu on **first contact only** (CM-1). From the second message on, a greeting, a thank-you
  or a farewell enters the normal flow: classify -> orchestrate -> capture/research/respond. A
  `"gracias, chau"` can therefore reach the knowledge-base miss and answer a farewell with
  *"Lo siento, no puedo responder con seguridad a eso. Un asesor de Lumat revisará tu consulta…"*.
- **The panel already has what the client lacks.** `_SOCIAL_WORDS`
  (`app/chat/assistant/nodes.py:42-48`) exempts short purely social turns, including `chau`, `adios`,
  `bye`, `hasta`, `luego`, `pronto`. The asymmetry runs the *opposite* way from the one fixed in
  `kb-retrieval-failure`: there the panel was the one missing the contract.
- **No business-hours concept exists.** No timezone setting and no schedule: `ZoneInfo` appears only in
  `app/services/calendar.py:35`, where `timezone_name` comes from `appointment.timezone` — a per-appointment
  field, not a system value.
- **`messages.<key>` holds exactly three keys** (`app/services/settings.py:47-61`, registered at
  `:122`-`149`: `messages.greeting`, `messages.cannot_answer`, `messages.clarification`). Adding a
  fourth **is a code change**, not a free-form KV write: the panel validates the section against a
  known-key set and `_KNOWN_SECTIONS` (`app/panel/api/routes/settings.py:223`) gates the sections.
- **The emergency gate is the graph entry point.** `builder.add_edge(START, "emergency_gate")`
  (`app/chat/graph.py:221`), with `emergency_gate` (`app/chat/nodes/emergency_gate.py`) classifying the
  raw text into `strong` / `weak` / `None` deterministically, before any LLM call, on **every** inbound
  message. This is what makes the emergency exemption below structural rather than a special case.

## Why

The customer checklist asks for these messages, and today the absence actively misleads: a customer who
says goodbye can be answered with a canned "I cannot answer that safely", and a customer who writes at
23:00 gets the full flow as if the business were open. Meanwhile a gasfitería's out-of-hours message is
the one place where being wrong is expensive — silence during a real emergency, or a promise of a visit
nobody will make until morning.

## Scope

**In:**

- A deterministic **out-of-hours gate** in the customer chat, fed by editable hours, that replaces the
  normal flow with the configured notice.
- A **farewell** for a customer's social close, mirroring the intent of the panel's social exemption
  from the client side.
- Two new keys in the existing `messages` section (`messages.farewell`, `messages.out_of_hours`) and a
  new `hours` section (timezone + schedule), both panel-editable, both added to `_KNOWN_SECTIONS`.
- The panel API and the "Mensajes"/new card in `Settings.tsx`.
- Spec coverage and the tests that never existed.

**Out:**

- **No change to the emergency path.** `emergency_gate` keeps its position, its classifier and its
  routing. The out-of-hours gate must never preempt it.
- **No deferred processing.** An out-of-hours message is *not* replayed in the morning. It is persisted
  (as every message is) and visible in the panel; the customer writes again when the business opens.
  A queue-and-replay mechanism is a different unit with a different failure mode: it would make the bot
  answer a 03:00 message at 09:00, out of context.
- **No `assistant.name`.** Maintainer decision: the greeting is already editable, so a name can be
  changed today with no code. Adding a key and a UI for it is speculative.
- **No panel-assistant changes.** The panel is internal and its operators work business hours;
  "out of hours" is meaningless there, and the panel already exempts short social turns.
- **No DB migration.** Settings are the KV surface; nothing about the schema changes.

## Authorized scope

Human-authorized in this session, per feature, before `rapso worktree create`. The five product
decisions, each answered by the maintainer:

| # | Question | Decision |
|---|---|---|
| 1 | When does the farewell fire? | On the **customer's social close** (farewell / thanks). |
| 2 | Where do the hours come from? | A **panel setting**, with an **explicit timezone**. |
| 3 | Does the notice replace or add to the flow? | It **replaces** the normal flow. |
| 4 | Emergency exemption | **Non-negotiable constraint**, not an option (see D1). |
| 5 | Does `assistant.name` exist? | **No** — the editable greeting suffices. |

Worktree `odd/out-of-hours-and-farewell`, base `d7a3c3aa`, one PR, one type label.

**Rejected alternatives, with their reasoning:**

| Rejected | Why |
|---|---|
| Hours in `app/config.py` (env, like `obs_no_reply_hours`) | Cheaper now, but a wrong business-hours value is customer-facing: with the value in env, a schedule change makes the bot tell customers "we are closed" during business hours until the next deploy. The checklist groups these messages with the ones the panel already edits. |
| Reusing `messages.cannot_answer` for the notice | Same defect class as `kb-retrieval-failure`: it would tell the customer the business tried and could not answer, when the truth is that nobody is there. |
| Importing the panel's `_SOCIAL_WORDS` into the client | Wrong-direction dependency (client -> assistant internals), and the set is panel-shaped: it exempts *greetings* too, which the client must not treat as a close. |
| A single `hours.open` / `hours.close` pair | It cannot express a gasfitería's real week (different Saturday hours), so it would make the bot lie for a whole day. See D2. |
| Queueing out-of-hours messages for replay | See Out of scope. |
| A new `hours` section vs. adding keys to `messages` | `messages.*` is text; hours are not text. Mixing them would put a validated schedule inside a section the panel treats as free strings. |

## Constraints

- **Strict TDD: ON.** Source: `openspec/config.yaml` (`testing.strict_tdd: true` at `:38`,
  `apply.tdd: true` at `:28`). Runner `uv run pytest tests/`. Observe RED before each source change;
  never invent RED evidence.
- Frontend: `npm --prefix web run test` (Vitest) and `npm --prefix web run build` (tsc). The worktree
  gets `node_modules` from `rapso worktree create`.
- Integration tests need `eval "$(bash infra/test-db.sh env)"`. This worktree's test DB port: **5497**.
- **Run the FULL suite before freezing**, not the subset this unit touches.
- Panel UI copy is **Spanish**, plain register (matches `Settings.tsx`).
- Conventional commits, no `Co-Authored-By`. One concern per commit, <=5 files.
- `ruff` is not installed and this project configures no linter, type checker or formatter — declare
  that, never fake it.
- Graph Check before each task (see "Graph check" below).

## Design decisions

**D1 — Out-of-hours is a deterministic gate, positioned so `emergency_gate` always wins.**
The entry point is `emergency_gate` (`graph.py:221`) and it classifies before any LLM call. The new gate
must run **after** it in the flow (current chain: `emergency_gate -> cost_gate -> handoff_gate ->
receive`) and act only when `emergency_hit` is `None`. A `weak` hit (which escalates to a human, EM-5)
must not be swallowed either. This makes the exemption structural: an emergency never reaches the
notice because the graph never routes it there. **Exact placement is pinned in T1**, with the constraint
above as the acceptance test — not as an implementation preference.

**D2 — The hours are a validated weekly schedule plus an explicit IANA timezone.**
`hours.timezone` holds an IANA name (`America/Santiago`), resolved through `ZoneInfo` — the module
already used at `app/services/calendar.py:35`. `hours.schedule` holds the week. A single open/close pair
was rejected because it cannot express a different Saturday, and would therefore make the bot lie for a
whole day — the exact failure class this session exists to remove. The schedule is **validated at write
time** and a malformed value is rejected with `400`, mirroring SS-5's decision that the tone is a
validated list rather than free text (a free-form value here would be parsed on every inbound message).
**The exact encoding is pinned in T1**; the constraint is that the panel must reject an invalid value
rather than store one the reader has to guess about.

**D3 — Off-hours messages are not replayed.** See Out of scope. The notice is the response; the message
is persisted and visible.

**D4 — The client needs its own narrow social-close detector.**
It must be narrower than the panel's: a **short message that is only** a closing or thanks formula. The
test must cover **both directions**, exactly as the grounding unit learned to: `"gracias, chau"` is a
close; `"gracias, ¿cuánto sale la revisión?"` is not, and must not be answered with a farewell. The
panel's false-negative lesson (`buenos`/`chau` missing from `_SOCIAL_WORDS`) applies: measure the
detector against real phrasings, do not trust the list.

**D5 — The farewell must not swallow an in-progress capture.**
If the bot is mid-capture (`capture` sub-flow) and the customer says "gracias, chau", the capture state
is the thing that matters. Placement is pinned in T1 alongside D1.

**D6 — The two new message keys join the existing `messages` section.**
`messages.farewell` and `messages.out_of_hours` follow `SETTINGS_DEFAULTS` (`settings.py:122`) and
`MESSAGE_DEFAULTS` (`:47-61`), and the panel's `messages` handler (`settings.py:171` in the routes
file) gains them. Adding a message key stays a code change, which SS-5 made deliberate.

**D7 — Hours live in their own `hours` section, not in `messages`.**
`_KNOWN_SECTIONS` (`routes/settings.py:223`) gains `hours` with a typed handler: the section is
validated, not free strings. `messages.*` stays text-only so its validation stays a string list.

**D8 — Degrade, never lie, when the hours are unusable.** A stored schedule that cannot be parsed, or a
timezone `ZoneInfo` cannot resolve, must **not** put the chat into a permanent "closed" state, and must
not silently disable the feature either. The chosen behavior, and its evidence, are pinned in T1; the
constraint is that the failure is visible (logged) and does not misinform the customer.

## Tasks

### WU1 — pin the contract

- [ ] **T1** — Pin: the exact gate placement (D1, D5), the `hours.schedule` encoding and its validation
      rule (D2), the unparseable-hours behavior (D8), and the client's social-close detector against
      real phrasings (D4). Route: inline + one delegated measurement pass. Deliverable: the pinned
      contract section appended to this record, before any source change.

### WU2 — the hours

- [ ] **T2** — RED: the schedule/timezone reader and its validation, including the boundary cases
      (exactly at opening, exactly at closing, a day with no hours, an invalid stored value).
- [ ] **T3** — GREEN: `app/services/settings.py` — the `hours.*` defaults and the reader; the pure
      "is it open at this instant" function, isolated so it is testable without a graph.
- [ ] **WU2 commit**

### WU3 — the gates

- [ ] **T4** — RED: an out-of-hours inbound produces the notice and does **not** reach classify/capture;
      a `strong` and a `weak` emergency both still reach their existing nodes; a `"gracias, chau"`
      produces the farewell; `"gracias, ¿cuánto sale?"` does not.
- [ ] **T5** — GREEN: the out-of-hours gate node and its routing in `app/chat/graph.py`, positioned per
      T1; the social-close detector and the farewell reply.
- [ ] **WU3 commit**

### WU4 — the panel surface

- [ ] **T6** — RED: the API returns the new `messages` keys and the `hours` section; a malformed
      `hours.schedule` is rejected with `400`.
- [ ] **T7** — GREEN: `app/panel/api/routes/settings.py` — the `hours` handler, `_KNOWN_SECTIONS`, and
      the `messages` handler extended.
- [ ] **T8** — RED/GREEN: `web/src/components/pages/Settings.tsx`, `web/src/types.ts`, the stories and
      the fixtures — the new messages and the hours card.
- [ ] **WU4 commit(s)**

### WU5 — spec

- [ ] **T9** — Spec deltas: the closure messages and the out-of-hours behavior, and the emergency
      exemption as an explicit scenario. Exact target files pinned in T1.
- [ ] **WU5 commit**

### WU6 — verify and deliver

- [ ] **T10** — Verify: the focused tests, the full Python suite, and the web suite. Record RED and
      GREEN evidence.
- [ ] **T11** — Record committed, branch pushed, PR open with a single type label. **The merge remains
      the human's decision.**

## Verification

- `uv run pytest tests/` — the full suite, before freezing.
- `npm --prefix web run test` and `npm --prefix web run build`.
- The emergency exemption is verified by test, not by reasoning: a `strong` and a `weak` hit during
  out-of-hours hours must both still reach their nodes.

## Acceptance criteria

1. An inbound message outside the configured hours replies with the configured notice and does not
   reach classify, capture, research or respond.
2. A `strong` emergency during those same hours still runs the safety protocol; a `weak` one still
   escalates. Neither is affected by the gate.
3. A short purely-social close replies with the configured farewell; a message that merely *starts*
   with a greeting or thanks and asks something is not treated as a close.
4. Hours and timezone are editable from the panel; a malformed schedule is rejected, not stored.
5. Unusable hours (bad timezone, unparseable schedule) never silently disable the feature nor
   permanently close the chat; the chosen behavior is declared and logged.
6. All three existing `messages.*` keys keep working byte-identically when unset.
7. The full Python and web suites pass.

## Delivery forecast

Estimated **~600-750 changed lines** across ~15 files, of which ~280 are this record — similar in shape
to SS-5, which was `~620` lines and shipped as one PR with a maintainer-approved `size:exception`.
Above the 400-line review budget, so a delivery strategy decision is required before `apply`:

- **One PR with `size:exception`**: the unit fulfills the checklist item only as a whole — a
  backend-only PR would leave Lumat unable to set the hours.
- **Two chained PRs**: hours + gates + spec first (the behavior), then the panel surface (the editing).
  The first PR leaves the feature configurable only in the database.

Recommendation: **one PR with `size:exception`**, on SS-5's argument. **Not yet decided** — to be
confirmed by the maintainer before apply, per the delivery-strategy rule.

## Graph check

To be recorded per task. This worktree has no graph (`graphify-out/` is gitignored, `.gitignore:24`), so
queries run against the main worktree root, whose code for this area is identical.

Preliminary nodes for this unit, from the measurements above:
`emergency_gate() [app/chat/nodes/emergency_gate.py]`, `build_graph() [app/chat/graph.py]`,
`respond() [app/chat/nodes/respond.py]`, `receive() [app/chat/nodes/receive.py]`,
`MESSAGE_DEFAULTS / SETTINGS_DEFAULTS / get_message() [app/services/settings.py]`,
`settings_messages() / _KNOWN_SECTIONS [app/panel/api/routes/settings.py]`, `Settings.tsx`.

## Next step

T1 — pin the contract: gate placement (D1/D5), the schedule encoding (D2), the unusable-hours behavior
(D8), and the social-close detector (D4). No source changes before the contract section exists.
