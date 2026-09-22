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

- [x] **T1** — Pin: the exact gate placement (D1, D5), the `hours.schedule` encoding and its validation
      rule (D2), the unparseable-hours behavior (D8), and the client's social-close detector against
      real phrasings (D4). Route: inline + one delegated measurement pass. **Done — see "Pinned
      contract (T1)" below.** No source change was made.

### WU2 — the hours

- [x] **T2** — RED: the schedule/timezone reader and its validation, including the boundary cases.
      **Done — 8 of 11 unit tests RED, all three accessor tests RED, none on an import or fixture error.**
- [x] **T3** — GREEN: `app/services/settings.py` — the `hours.*` defaults and the reader; the pure
      `is_open_at` function. **Done.**
- [x] **WU2 commit**

### WU3 — the gates

- [x] **T4** — RED: an out-of-hours inbound produces the notice and does **not** reach classify/capture;
      a `strong` and a `weak` emergency both still reach their existing nodes; a `"gracias, chau"`
      produces the farewell; `"gracias, ¿cuánto sale?"` does not. **Done — 3 of 13 integration tests
      RED. The 10 that passed at RED are the regression guards (emergency, capture, in-hours, empty
      schedule), which pass trivially while the gate does not yet exist.**
- [x] **T5** — GREEN: the out-of-hours gate node and its routing in `app/chat/graph.py`, positioned per
      T1; the social-close detector and the farewell reply. **Done — module `app/chat/nodes/closure_gate.py`.**
- [x] **WU3 commit** — `5e0e1d6d`

### WU4 — the panel surface

- [x] **T6** — RED: the API returns the new `messages` keys and the `hours` section; a malformed
      `hours.schedule` is rejected with `400`. **Done — 3 of 54 functional tests RED. Declared weakness,
      since closed: see "The rejection tests at RED" below.**
- [x] **T7** — GREEN: `app/panel/api/routes/settings.py` — the `hours` handler, `_KNOWN_SECTIONS`, and
      the `messages` handler extended. **Done — this closes P13.**
- [ ] **T8** — RED/GREEN: `web/src/components/pages/Settings.tsx`, `web/src/types.ts`, the stories and
      the fixtures — the new messages and the hours card. **Not started; the whole frontend is one task.**
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

### The rejection tests at RED — a declared weakness, since closed

The six `POST /settings/hours` rejection cases passed at RED, and **not because the validator worked**:
while the `hours` section did not exist, the catch-all route (`_KNOWN_SECTIONS`) answered every
`hours` request with `400 unknown section 'hours'`, and nothing was persisted either. Both assertions —
`status_code == 400` and "the value is not in the database" — were satisfied by the absence of the
section, so they proved nothing.

That is now closed. The test also asserts
`"unknown section" not in resp.json()["detail"]`, and the catch-all's detail is
`f"unknown section {section!r} ({', '.join(sorted(_KNOWN_SECTIONS))})"`
(`app/panel/api/routes/settings.py`). So the strengthened test **fails** whenever the rejection comes
from a missing section rather than from the validator — verified by reading that exact source line, not
assumed. The non-persistence and no-audit-row assertions already made the test non-vacuous in GREEN
(a route that persisted the value would fail them); this assertion makes its RED meaningful too.

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

Recommendation: **one PR with `size:exception`**, on SS-5's argument.

**Decided**: one PR with `size:exception`, approved by the maintainer before the work started.

## Pinned contract (T1)

Measured on `d7a3c3aa`, read from the source, not recited.

**The router functions** (`app/chat/graph.py`):

| Router | Line | Logic |
|---|---|---|
| `_flow_start` | `:131-137` | `_pending` in `state.captured` -> `capture`; otherwise `classify_intent` |
| `_after_emergency_gate` | `:139-145` | `strong` -> `emergency`; `weak` -> `handoff`; otherwise `cost_gate` |
| `_after_cost_gate` | `:148-152` | `blocked` -> `handoff`; otherwise `handoff_gate` |
| `_after_handoff_gate` | `:154-157` | truthy `handoff_reason` -> `handoff`; otherwise `receive` |
| `_route_path` | `:159-161` | `state.next_step` or `respond` |
| `_after_capture` | `:163-166` | `next_step == "summary"` -> `summary`; otherwise `END` |
| `_after_respond` | `:168-170` | `escalate` -> `handoff`; otherwise `END` |

**P1 — Gate placement: after `handoff_gate`, before `receive`, with an explicit `_pending` bypass (P2).**

Two insertion points were rejected on measured consequence:

- *After `emergency_gate`, before `cost_gate`*: `cost_gate` reads cost state and can audit or alert the
  owner (`app/chat/nodes/cost_gate.py:33-64`), so out-of-hours messages would silently stop being
  cost-audited.
- *After `cost_gate`, before `handoff_gate`*: `handoff_gate` is a pure reader with no DB side effect
  (`app/chat/nodes/handoff_gate.py:95-116`), so a 02:00 complaint would stop escalating to a human.

Inserting after `handoff_gate` preserves **all three** existing gates — emergency, cost and handoff — and
adds exactly one new behavior. It also sits before `receive`, so the first-contact greeting, `capture`
and `classify_intent` are all skipped for a closed message.

**P2 — D5: a capture in progress wins.** Capture progress persists in `Conversation.captured_data`
(`app/chat/nodes/capture.py:81-85`) and is rebuilt into state by `from_db`
(`app/chat/state.py:178-223`), so a new message genuinely can arrive mid-capture, and `_flow_start`
reads `_pending` for exactly that reason (`graph.py:131-137`). The gate therefore returns the notice
**only when no capture is pending**: a customer already mid-flow is not stranded, and a half-collected
case is not abandoned. This is the bypass the chosen insertion point requires.

**P3 — D2: the schedule is a validated list of entries.**
`hours.timezone` (string, default `America/Santiago`) and `hours.schedule` (a list). Each entry is
`{"days": [1..7], "open": "HH:MM", "close": "HH:MM"}` with ISO weekdays. Validated on write and
rejected with `400`: weekdays in `1..7`, **no weekday repeated across entries**, `HH:MM` well formed,
`open < close`. Precedent for a structured stored value already exists — `emergency.keywords` is a
stored `list[str]` (`app/services/settings.py:211-217`) and `scope_rules` a validated dict (`:199-208`).

Rejected: a single `open`/`close` pair — it cannot express a different Saturday, so the bot would lie
for a whole day, which is the failure class this session exists to remove. A hand-rolled string DSL was
rejected too: more code and more bug surface than a Pydantic list, for a worse UI.

**P4 — D8: unusable hours fail OPEN and are logged.** An unparseable stored schedule, or a timezone
`ZoneInfo` cannot resolve, makes the reader report **open** — precisely the pre-feature behavior — and
log a warning. Failing closed would have the bot telling real customers the business is shut because of
a typo in a setting; failing open degrades to today's behavior, which is the safe direction. Precedent:
`get_tone` returns the default for an unusable stored value (`app/services/settings.py:220-223`). Log
level `warning`, matching the convention for a degraded capability used by `kb-retrieval-failure`.
`app/services/settings.py` currently defines no logger, so the unit adds one.

**P5 — D4: the client gets its own closing detector, and it was corrected by measurement.**

Structural guards mirrored from `_is_conversational_turn` (`app/chat/assistant/nodes.py:528-534`):
casefold, reject empty, reject longer than 40 characters, reject any `?`, tokenize on Unicode words,
require **every** token to be allowed. Plus one rule the panel does not have: **diacritics are folded**
(`unicodedata.normalize("NFD", ...)` + `unicodedata.combining`) before tokenizing.

`CLOSING_TOKENS` is a **single** set. The two-set split originally pinned here, with a "must contain an
explicit closing token" requirement, was removed after measurement: the maintainer decided that a bare
thanks or acknowledgement should also receive the farewell, because today a bare `gracias` or `ok`
reaches classification, increments an unknown-intent count, and can be answered with the menu
clarification — the same absurdity this unit exists to remove. With the requirement gone the split had
no behaviour left, so it was deleted rather than kept as dead structure.

- `CLOSING_TOKENS` = {adios, bye, chao, chau, hasta, luego, nos, pronto, vemos, gracias, muchas, mucho,
  ok, bueno, dale, listo, perfecto, genial, excelente, ya, nada, bien}

A message is a farewell iff every token is in `CLOSING_TOKENS`.

The panel module is **not** imported: `app/chat/assistant/nodes.py:5-30` pulls in the assistant
approval, evidence, markup, tools, audit, KB, LLM and cost modules — a heavy, wrong-direction dependency
for the customer chat.

**Why the correction was necessary — the detector was measured, not read.** The first implementation
missed two real-world forms, both confirmed by running it:

| Input | First implementation | Cause |
|---|---|---|
| `chao` | **no** | the common Chilean spelling was not in the set at all |
| `adiós` | **no** | the correctly accented spelling of a word that *was* in the set — no folding |
| `¡Adiós!` | **no** | same |

This is the same defect class the panel's `_SOCIAL_WORDS` shipped with (`buenos` and `chau` missing
until it was measured). Folding diacritics kills the whole class, not just those two cases.

**Observed verdicts after the correction** (run, not reasoned):

```
FAREWELL  chau, chao, adiós, adios, ¡Adiós!, GRACIAS, CHAO, gracias chau,
          hasta luego, nos vemos, muchas gracias, ok gracias, gracias, ok,
          listo, bye, chau!
no        gracias, ¿cuánto sale la revisión anual?   (contains ?)
no        chau, pero antes dime los valores          (disallowed tokens)
no        hola, necesito una visita                  (disallowed tokens)
no        ¿cuánto cuesta?                            (contains ?)
```

**P6 — the baseline this unit changes.** A bare `chau` today reaches `classify_intent`, whose declared
vocabulary has no social or farewell intent: an unclassifiable text records an `unknown_intent` event
and increments a persisted count (`app/chat/nodes/classify_intent.py:186-201`), and orchestration sends a
first unknown to `respond` (`app/chat/nodes/orchestrate.py:92-94`), where a later turn answers with the
clarification. So a goodbye currently consumes an unknown-intent increment and can be answered with a
clarification — or, on another path, with the knowledge-base-miss refusal.

**P7 — a graph-check limitation, recorded rather than hidden.** `graphify path` between graph node
functions returns **no directed path** (`emergency_gate() -> respond()`, `receive() -> orchestrate()`,
`settings_messages() -> SETTINGS_DEFAULTS`). LangGraph wires nodes as `add_node` /
`add_conditional_edges` **strings**, so the node relationships are data, not call edges. The graph is
therefore not a usable source for this unit's flow topology; `app/chat/graph.py` is, and it was read
directly. This is a real limitation of the graph for graph-topology work, not a failure of the check.

**P8 — the farewell lives in the same new gate node; `app/chat/nodes/respond.py` is not touched.**
P1 already places a closure gate before `receive`, and the farewell is the same kind of pre-flow check,
so both live in that one node. Two consequences, both wanted: the unit does not touch `respond.py`,
which is already modified by the open PR #303 (`kb-retrieval-failure`) on this repository, so the two
units do not collide in code; and the capture bypass (P2) applies to the farewell too — a customer
mid-capture who says "gracias, chau" must not have their half-collected case replaced by a goodbye.

**P9 — an empty schedule is the OFF state, and the daily boundary is half-open.**
`hours.schedule` defaults to `[]`, and an empty schedule means the feature is **off**: the reader reports
open, the normal flow runs, and **no warning is logged**, because nothing is misconfigured. This is what
makes installing the unit behaviour-neutral until Lumat configures hours, and it is deliberately
distinguishable from P4's unparseable schedule, which does log. The daily interval is
`open <= local_time < close`, evaluated in `hours.timezone`: at exactly the opening minute the business
is open, at exactly the closing minute it is closed. Both boundaries are pinned by test.

**P10 — the hours logic stays in `app/services/settings.py`.**
`app/services/settings.py` already owns the `hours.*` keys, and the pure function is a short loop over
the entries. A new module for it would be a file for ~15 lines. If the implementer finds a better
existing home, the choice must be justified in the record — not assumed.

**P11 — a declared limitation, not a defended one: a naive `now` is interpreted as the process's local
time.** `is_open_at` requires an aware `datetime` but does not enforce it, and `datetime.astimezone()`
on a naive value silently assumes the system timezone. The production caller passes
`datetime.now(timezone.utc)`, so this is correct in practice; a future caller passing a naive value
would get a shifted answer. It is declared rather than guarded because the obvious guard — fail open
plus a warning — would hide a caller error in exactly the way P4 deliberately uses that shape only for
configuration errors.

**P12 — the closure router reads `state.replies`, which is an accumulator, and that is a declared
invariant rather than a defended one.** `replies` carries an `add` reducer (`app/chat/state.py:172-173`)
and six other nodes write it (`receive`, `respond`, `capture`, `handoff`, `emergency`, and this gate).
`_after_closure_gate` routes `END` when `state.replies` is non-empty, which is correct **only because
nothing before `closure_gate` in the chain writes it**: `from_db` does not set it (the `cls(...)` at
`state.py:215-222` does not pass it), and `emergency_gate`, `cost_gate` and `handoff_gate` do not write
it either. This is unlike the three sibling gates, which each read an explicit marker they themselves
set (`emergency_hit`, `cost_mode`, `handoff_reason`).

It was left as-is deliberately. Unlike `session=None`, whose failure was a crash, this assumption's
violation is benign: if an upstream node ever does reply, ending the turn is the right outcome anyway.
The invariant is declared here so a future change that inserts a replying node before `closure_gate`
sees it; it is not worth a new state field.

**P13 — the panel's write model is behind the read model until WU4.** `settings_get` builds the
`messages` section from `SETTINGS_DEFAULTS`, so it now returns **five** keys, while `MessagesBody` in
`app/panel/api/routes/settings.py:63-67` still accepts exactly **three**. `tests/functional/test_api_kb_settings.py`
was updated to the new read shape, which makes the inconsistency visible and asserted rather than
hidden. WU4 closes it by extending the model — the two new keys are readable but not yet writable.

## Graph check

Run from the main worktree root, because this worktree has no graph (`graphify-out/` is gitignored,
`.gitignore:24`) and the code for this area is identical there.

- `graphify query "customer chat gate routing emergency out of hours business hours"` — 506 nodes; the
  relevant hits were `emergency() [app/chat/nodes/emergency.py:69]`, the conversation pipeline
  hyperedge (`GRAPH_REPORT.md:708-711`), and `chat.py [app/panel/api/routes/chat.py]`.
- `graphify path "emergency_gate()" "respond()"`, `"receive()" "orchestrate()"`, and
  `"settings_messages()" "SETTINGS_DEFAULTS"` — **no directed path** in all three. See P7: LangGraph
  wires nodes as strings, so the flow topology is not in the graph.

Preliminary nodes for this unit, from the measurements above:
`emergency_gate() [app/chat/nodes/emergency_gate.py]`, `build_graph() [app/chat/graph.py]`,
`respond() [app/chat/nodes/respond.py]`, `receive() [app/chat/nodes/receive.py]`,
`MESSAGE_DEFAULTS / SETTINGS_DEFAULTS / get_message() [app/services/settings.py]`,
`settings_messages() / _KNOWN_SECTIONS [app/panel/api/routes/settings.py]`, `Settings.tsx`.

## Next step

T1 — pin the contract: gate placement (D1/D5), the schedule encoding (D2), the unusable-hours behavior
(D8), and the social-close detector (D4). No source changes before the contract section exists.
