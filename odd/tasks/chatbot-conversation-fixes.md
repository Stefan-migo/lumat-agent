# ODD: chatbot-conversation-fixes

**The WhatsApp chatbot must hold a coherent conversation: human-readable slots, a booking it
remembers, a closing it honours.**

## Objective

Fix the observed failure modes of the customer WhatsApp chatbot so a real conversation stays
coherent end to end, without redesigning the deterministic pipeline. Two work-unit slices:

- **Slice A (deterministic, low risk):** human-readable booking slots, farewells that close instead
  of escalate, and a clarification fallback that does not invent a menu.
- **Slice B (context):** the graph must know a booking exists, and the two LLM calls must see the
  recent conversation instead of only the current message.

## Problem

Measured on a real conversation (owner, 2026-10-13) against `main` = `2554af2` (`v2026.10.3`).

| # | message | intent | node | reply | defect |
|---|---------|--------|------|-------|--------|
| 5 | (booking) | — | `booking` | `1. 2026-10-13 13:23:10.986884 …` | raw datetime, microseconds |
| 7 | "cual es el precio?" | `valores` | `respond` | `$18.000 … ¿registro tu solicitud?` | re-suggests booking already made |
| 8 | "quiero confirmar que la visita esté agendada" | `consulta` | `respond` | "quedó escalado para gestión manual" | **fabricated** — text absent from repo |
| 9 | "ya agende una visita" | `unknown` | `respond` | clarification menu | contextual message, no history |
| 10 | "eso fue todo gracias" | `unknown` (2nd) | `handoff` | "Un asesor revisará tu caso" | closure escalated to a human |

Root cause, one sentence: **the LLM calls are blind to the conversation, and the graph does not
carry booking state.** `state.window` holds the last 10 messages (`app/chat/state.py:184-193`) but no
LLM call receives it; `ConversationState.from_db` (`app/chat/state.py:208-217`) never loads the
appointment. Evidence per defect:

- **Raw slots** — `app/chat/nodes/booking.py:43-47` renders `f"{slot['date']} {slot['time']}"` from
  `day.isoformat()` + `clock.isoformat()`; `time` carries microseconds. The confirmation path formats
  correctly (`booking.py:146`, `strftime("%d/%m/%Y a las %H:%M")`).
- **Farewell escalated** — `app/chat/nodes/closure_gate.py:46-52` requires *every* token in
  `CLOSING_TOKENS`; `"eso fue todo gracias"` → `["eso","fue","todo","gracias"]`, three tokens absent.
  Falls to `classify_intent` → `unknown` → 2nd unknown escalates (`classify_intent.py:200-219`).
- **Blind LLM** — `respond` (`app/chat/nodes/respond.py:88-99`) sends only `{{kb_text}}` +
  `{{user_input}}`; `classify` (`classify_intent.py:75-85`) sends only `{{user_input}}`.
- **No booking state** — only `_booking_offer` in `captured`, cleared on confirm
  (`booking.py:145`); the appointment table is never read into state.

## Why now

The bot cannot hold a conversation today. This is the owner's live blocker and precedes any
chatbot telemetry ("assistant optimizer") work, which would only measure a broken bot.

## Scope

**In:**

- `app/chat/nodes/booking.py` — human-readable slot offer.
- `app/chat/nodes/closure_gate.py` — recognise phrasal farewells/thanks without over-matching.
- `app/services/settings.py` — `MESSAGE_DEFAULTS["clarification"]` no longer references a menu.
- `app/chat/state.py` — load the customer's relevant appointment into `ConversationState`.
- `app/chat/nodes/respond.py` + `agent/prompts/respond.md` — receive the recent transcript and the
  booking status.
- `app/chat/nodes/classify_intent.py` + `agent/prompts/classify.md` (and `agent/personas/classify.md`
  if needed) — receive the recent transcript.
- `app/services/prompts.py` — keep `FALLBACKS` byte-identical to every edited `agent/*.md` (AC-3).
- `tests/unit/*`, `tests/integration/*` — RED/GREEN coverage for each behaviour.
- This record.

**Out (explicitly):**

- **The deterministic gates.** `emergency_gate`, `cost_gate`, `handoff_gate`, injection detection and
  the SH-4 input-as-data contract stay exactly as they are. The LLM never decides safety or cost.
- **The LLM as flow router (agentic dispatch).** Considered and rejected for this unit; the
  deterministic envelope is preserved. Reducing LLM responsibility is not the goal; giving the
  existing calls context is.
- **Tukulpan memory personalisation** (greeting by name, structured thread recap, memo on handoff).
  Real gap, deferred to its own unit — see Findings.
- **`analytics.chatbot_metrics` / assistant tooling.** Frente 2, separate ODD.
- **The classifier's intent vocabulary.** No new intent is added (no `confirmar_visita`); a booked
  customer is handled by carrying booking state, not by inventing a label.

## Spec constraints (binding)

- `openspec/specs/conversation-manager/spec.md` — CM-1 (greeting/resume), CM-2 (progressive capture),
  CM-3 (classification), CM-4 (grounded answers, never invent), CM-5 (summary), CM-7 (memory).
- `openspec/specs/agent-orchestration/spec.md` — AO-3 (deterministic dispatch stays LLM-free).
- CM-4 is the reason `respond` fabrication is a contract violation, not just a quality bug: the
  persona forbids inventing availability (`agent/personas/orchestrator.md`).
- Strict TDD (`openspec/config.yaml` `testing.strict_tdd: true`).

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-chatbot-conversation-fixes`
- Branch: `odd/chatbot-conversation-fixes`
- Base: `2554af2` (= `origin/main`, verified `git merge-base HEAD origin/main` before this record).
- Files: those listed in **In** above.

## Constraints

- **Strict TDD: ON** — runner `uv run pytest tests/`. RED before GREEN, evidence recorded.
- Fresh worktree has no `.venv`: `uv sync` first.
- Test DB: `eval "$(bash infra/test-db.sh env)"` before pytest; a fresh DB needs `bash db/migrate.sh`.
- `infra/.env` is gitignored; copied from main worktree (never committed).
- Known worktree artifact: `rapso worktree create` leaves `.opencode/tools/package-lock.json`
  untracked. Declare it to review; never commit it.
- `agent/*.md` prompts are byte-coupled to `FALLBACKS`; editing one means editing both and passing
  the identity test (`tests/unit/test_prompts.py`).
- No commit/push/PR from a delegated phase without orchestrator authorization. Work-unit commits on
  the feature branch are authorized; push/PR is a human decision.

## Delivery

- Strategy: `ask-on-risk`. Forecast: well under 400 authored lines.
- Slices: **A** (work-unit commit 1) → **B** (work-unit commit 2+).

## Decisions

- **D1 — Two slices, A first.** A is small, safe and independently mergeable; B carries the prompt
  coupling. Sequenced so a revert of B never drags A down.
- **D2 — Carry booking state, don't add an intent.** A `confirmar_visita` intent would fight the
  classifier's ASK/REPORT vocabulary. The graph knowing the appointment answers "is my visit booked?"
  honestly instead of hallucinating.
- **D3 — The transcript is DATA.** The conversation block passed to `classify`/`respond` is delimited
  and declared non-instructional, preserving SH-4 and CM-4.
- **D4 — Deterministic gates untouched.** No safety/cost decision moves to the LLM.

## Tasks

- [ ] **T1** — this record.
- [ ] **T2 (A1)** — RED: a booking-offer test expecting a readable slot label fails on the raw
      datetime; GREEN: `booking.py` formats slots like the confirmation.
- [ ] **T3 (A2)** — RED: `is_farewell("eso fue todo gracias")` is False and the flow escalates;
      GREEN: phrasal farewells recognised without over-matching questions.
- [ ] **T4 (A3)** — RED: the clarification copy references a non-existent menu; GREEN: neutral
      clarification copy in `MESSAGE_DEFAULTS`.
- [ ] **T5 (A)** — full suite green; work-unit commit 1.
- [ ] **T6 (B1)** — RED: a booked conversation's state has no appointment; GREEN:
      `ConversationState.from_db` loads the relevant appointment.
- [ ] **T7 (B2)** — RED: "is my visit booked?" fabricates; GREEN: `respond` receives the transcript +
      booking status and answers from them. Prompt + `FALLBACKS` + identity test.
- [ ] **T8 (B3)** — RED: a contextual follow-up classifies `unknown`; GREEN: `classify` receives the
      transcript. Prompt + `FALLBACKS` + identity test.
- [ ] **T9 (B)** — full suite green; work-unit commit(s) 2+.
- [ ] **T10** — verification: `uv run pytest tests/` observed; write Findings.

## Acceptance criteria

- **A1** — the slot offer shows a human-readable date/time (no microseconds); a unit test asserts the
  rendered text.
- **A2** — `"eso fue todo gracias"` (and close variants) closes with the farewell, does not increment
  `unknown_count`, does not escalate; a question containing a closing word is still not a farewell.
- **A3** — the clarification reply no longer instructs picking from a menu.
- **B1** — for a customer with a confirmed appointment, `ConversationState.from_db` exposes it.
- **B2** — asked about an existing booking, `respond` answers with the booking, never fabricates
  escalation/availability; a test with a mocked LLM asserts the booking context reaches the prompt.
- **B3** — a contextual follow-up with history present is not classified `unknown`; the transcript
  reaches the classification call.
- **All** — `uv run pytest tests/` passes; `FALLBACKS` identity test passes.
