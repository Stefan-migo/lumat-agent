# chatbot-intake-redesign

## Objective

Make the customer-facing WhatsApp intake **organic** instead of a rigid form:

- greet openly — no menu dump;
- **extract** from the client's free text whatever fields they already gave;
- ask only what is missing, grouped into 2–3 natural-language questions per turn;
- make the capture **interruptible**: the client may pivot to another intent at any turn
  (including mid-capture), the bot answers the deviation, and then resumes the agenda;
- keep visit **booking deterministic** (real slots, not LLM-invented);
- keep the data-storage **consent explicit and separate**.

Measured target: the happy path drops from **~10–11 inbound turns** to **~4–5**.

## Problem (verified from code)

| # | Finding | Evidence |
|---|---------|----------|
| 1 | First contact sends greeting **+ the 8-category menu in one message**, and it is **decorative**: there is no numeric parser; the LLM classifier already resolves free text. | `app/services/settings.py:53-56`, `app/chat/state.py:36-57`, `app/chat/nodes/receive.py:22-25` |
| 2 | Capture is **blind**: 8 fixed fields, one per turn; the whole message is stored verbatim as the pending field's value; no validation, no re-ask, no multi-field extraction. | `app/chat/nodes/capture.py:117-149` |
| 3 | **Mid-capture rigidity** (the core defect): `_flow_start` skips classification whenever `_pending` is set, so a pivot — e.g. `"Juan Pérez, Los Leones 1234. ¿Cuánto cuesta la visita?"` — is stored **as the `name` field**, never answered, never escalated. | `app/chat/graph.py:134-139`, `handoff_gate.py:99-111` (a price question is not media/persona/complaint) |
| 4 | The first `"hola"` is sent to the LLM classifier and usually yields `unknown`, **burning 1 of the 2 HH-3 attempts** (2 unknowns → human). | `app/chat/nodes/classify_intent.py:186-201` |
| 5 | The capture **asks for a photo** (`evidence`), but `handoff_gate` routes **any** media to a human. Asking for something that expels you. | `app/chat/nodes/handoff_gate.py:46-48,104-105` |
| 6 | `LumatRequest.md §1.5` requires **email** as identification data; the capture does not ask for it. | `LumatRequest.md:77` vs `capture.py:29-39` |

## Why

The owner confirmed **Option A** (organic intake + controlled capture), approved the **Calefont v2**
reference thread, and set **interruptible capture** as a hard requirement. Customer-facing copy must be
**neutral Chilean Spanish** (tú, no voseo). Tone polish is deferred to the testing stage.

An earlier READ-ONLY overview recorded the thread taxonomy and the menu's coverage in Engram
(`architecture/chatbot-thread-taxonomy`, `architecture/chatbot-capture-rigidity`).

## Scope

**In:** the customer WhatsApp path — `app/chat/graph.py`, `app/chat/state.py`,
`app/chat/nodes/{receive,classify_intent,capture,orchestrate}.py`, the messages in
`app/services/settings.py`, the classifier guidance in `app/services/prompts.py`, the measurement
harness `scripts/kb_fidelity.py` (it simulates the customer flow and consumes the greeting), the live
spec `openspec/specs/conversation-manager/spec.md`, their tests, and this document.

**Out:** `booking` / `manage` mechanics (reused), the emergency protocol content, the panel assistant
(`app/services/agent_chat.py`, `app/chat/assistant/`), the frontend, and KB content.

## Constraints

- Chat in Rioplatense Spanish; artifacts, code, comments, commits in **English**; customer-facing
  WhatsApp copy in **neutral Chilean Spanish** (`¿Cómo estás?`, `¿Me pasas?`, `¿Autorizas?` — no voseo).
- **Parallel worktrees:** `lumat-agent-odd-asistente-agentes-proyecto` (Asistente Lumat backend) and a
  Configuración frontend worktree are in flight. Keep changes scoped to the customer chat path;
  re-verify any shared `app/` file against `main` before merging.
- **Emergencia stays instant and deterministic** (`emergency_gate` runs first).
- **Client input is untrusted:** extraction must not auto-execute actions; booking stays deterministic.
- Do not fabricate the Lumat business content (see Declared debt).

## Behavior spec (target)

1. **Open greeting.** First contact = greeting + open question, **no menu**:
   `"Hola, soy el asistente virtual de Lumat. ¿Cómo estás? ¿En qué te puedo ayudar?"`. With prior customer
   memory, the bot may open by acknowledging the known case.
2. **Extraction per turn.** Every turn, classify the intent and extract any capturable fields present
   in the free text (`name`, `comuna`, `address`, `equipment`, `failure`, `availability`, `email`).
3. **Ask only what is missing**, grouped into **2–3** questions per message, in natural language, no
   numbered lists. Hard cap: never more than 3 asks in one turn.
4. **Interruptible capture.** If the client pivots to another intent (`valores`, `consulta`, `persona`,
   `cancelar_visita`, `reagendar_visita`, …), the bot answers the deviation (KB or the matching flow)
   and then **resumes the agenda**, re-asking only the still-missing fields.
5. **Consent is its own explicit step**, before booking. Never auto-extracted.
6. **Booking unchanged**: deterministic slot offer; confirmation ends the flow.
7. **Bare greeting is not classified** (HH-3 fix): a greeting-only first message does not consume an
   `unknown` attempt.

## Golden threads (acceptance contract)

UI copy below is the contract of intent; the exact wording is finalized in the testing stage.

### Family 1 — Book a visit (`calefont`, `caldera`, `calefaccion`, `solicitar_visita`)

```
1  cliente: hola
   agente:  Hola, soy el asistente virtual de Lumat. ¿Cómo estás?
            ¿En qué te puedo ayudar?

2  cliente: tengo un problema con el calefont, no calienta
   agente:  Entiendo. Si quieres, te agendo la visita de un técnico.
            ¿Te parece?

3  cliente: ya, sí
   agente:  Perfecto. Para agendarla necesito tu nombre, correo y dirección.

4  cliente: Juan Pérez, Los Leones 1234. ¿Cuánto cuesta la visita?
   agente:  Perfecto, Juan. La visita de diagnóstico tiene un valor de $XX,
            que se descuenta si haces el trabajo.
            Para agendar me falta tu correo. ¿Y qué días u horarios te sirven?

5  cliente: juan@mail.cl, mañana en la tarde. Es un Junkers 2019
   agente:  Listo. ¿Autorizas que guardemos tus datos para gestionar la visita?

6  cliente: sí
   agente:  Tengo mañana 10:00 y 15:30. ¿Cuál te sirve?

7  cliente: 10:00
   agente:  Confirmado: mañana 10:00, Los Leones 1234.
            Te aviso cuando salga el técnico.
```

`caldera`, `calefaccion`, `solicitar_visita` share this engine; only the equipment copy differs.
**Turn 4 is exactly what the current code cannot do:** answer the pivot and resume the agenda.

### Family 2 — Resolve alone (KB)

```
── VALORES
1  cliente: ¿cuánto sale revisar un calefont?
   agente:  La visita de diagnóstico tiene un valor de $XX y se descuenta
            si haces el trabajo. ¿Quieres que te agende una?

── POSTVENTA / GARANTÍA
1  cliente: me instalaron hace 2 meses y quedó con una fuga
   agente:  Lamento eso. Los trabajos tienen 60 días de garantía.
            ¿Me pasas la dirección y la fecha del trabajo? Lo reviso.
```

### Family 3 — Always escalate to human

```
── EMERGENCIA (safety protocol, no conversation)
1  cliente: huelo a gas
   agente:  Por favor, corta la llave de gas, ventila y no enciendas nada.
            Ya avisamos a un técnico. ¿Estás en un lugar seguro?

── HABLAR CON UNA PERSONA
1  cliente: quiero hablar con alguien
   agente:  Listo, te derivo con una persona del equipo.
            En un momento te atienden.
```

### Family 4 — Threads the menu does not show

```
── CONSULTA
1  cliente: ¿atienden en La Florida?
   agente:  Sí, cubrimos La Florida. ¿Necesitas agendar una visita?

── CANCELAR VISITA
1  cliente: quiero cancelar mi visita
   agente:  Tengo tu visita del jueves a las 10:00. ¿La cancelo?

── REAGENDAR VISITA
1  cliente: necesito cambiar la hora de la visita
   agente:  Claro. Tengo jueves 10:00 y viernes 15:30. ¿Cuál te sirve?
```

## Guardrails

- **Emergencia** never becomes conversational; `emergency_gate` stays first and deterministic.
- **Consent** explicit, separate, and never inferred from free text (PII).
- **Untrusted input:** extraction fills fields; it never triggers actions. Booking/manage stay
  deterministic.
- **Prompt-question cap:** 2–3 asks per turn. The gain comes from extraction, not from stacking questions.
- **Validation at trust boundaries:** normalize `comuna`/`address`; the phone comes from WhatsApp.
- **Preserve** the existing gates (`emergency`, `cost`, `handoff`, `closure`) and `booking`/`manage`.

## Decisions (owner, 2026-10-08)

1. **Photo/evidence — RESOLVED.** Keep the evidence ask, framed as an **optional reference for the
   technician**: "¿tienes algo más para pasarle al técnico? (una foto, un audio…)". It is **not** a
   mandatory capture field. Consequence: `handoff_gate` MUST stop routing media to a human while the
   capture is active; media is stored as case evidence instead (CI-4).
2. **Email — RESOLVED.** Mandatory for booking; add it to the batched data request (CI-3).

## Declared debt (not blocking)

- **`VALORES` KB content is pending from Lumat.** The service quote format ("formato de cotización")
  must live in the KB; it is not confirmed to exist. Until then, useplaceholder test documentation
  with clearly-fake values so the thread can be tested without inventing business content. Track it as
  a Lumat-owned dependency.
- **Follow-up on an existing visit** ("¿cuándo viene el técnico?") has no dedicated intent; it falls to
  `consulta`. Out of scope for this change; recorded as a known gap.

## TDD resolution

**Strict TDD is ACTIVE** (`openspec/config.yaml`: `apply.tdd=true`). Runner: `pytest tests/`.
Follow RED → GREEN → REFACTOR; never fall back to standard mode. Test markers: `spec`, `integration`,
`functional`, `injection`. No linter / type checker / coverage configured.

## Delivery strategy

- Forecast: **> ~400 authored changed lines** (graph/state/capture/classify/orchestration changes +
  extraction + functional tests + this doc).
- `delivery_strategy`: `ask-on-risk`; `chain_strategy`: `stacked-to-main`. Confirm at the tasks gate.

## Work units (stable IDs)

### CI-1 — Open greeting + greeting not classified — DONE
- [x] Replaced the greeting+menu with the open greeting (`greeting()`); removed `MENU_CATEGORIES`.
- [x] A greeting-only first message no longer consumes an HH-3 `unknown` attempt (deterministic skip in
      `_flow_start`); greeting+content still classifies and routes.
- [x] RED→GREEN tests added (`tests/unit/test_chat_greeting.py`); stale menu assertions rewritten.
- [x] Kept **"asistente virtual"** (`LumatRequest §1.3` identification) — restored after the first pass
      dropped it.
- [x] Updated the live spec `openspec/specs/conversation-manager/spec.md` and the `scripts/kb_fidelity.py`
      consumer.
- Evidence: focused tests green; full suite `uv run pytest tests/` **EXIT=0** with the two known-flaky
  seed subprocess tests deselected (both pass in isolation). CI-1 commits `5800a099` (docs) and
  `76eaebec` (feat); PR #512 merged; review `review-359fcc5285c7a1b3` approved/acknowledged.

### CI-2 — Interruptible capture (core)
- [x] Remove the `_pending` blind skip; every turn re-classifies intent and extracts fields.
- [x] On a pivot, answer the deviation and resume the agenda.
- [x] Preserve emergency / handoff / cost / closure gates and booking/manage.

### CI-3 — Extraction + grouped questions

#### CI-3a — Mandatory email + separate consent — DONE
- [x] Add mandatory `email` to the capture order and persist it on the ficha.
- [x] Consent is now its own explicit step before booking (removed from `CAPTURE_FIELDS`).

#### CI-3b — Multi-field extraction + grouped questions — DONE
- [x] Extract multiple fields from one free-text message (same classifier LLM call).
- [x] Ask only missing fields, grouped 2–3, natural language, no numbered lists.

### CI-4 — Media as evidence (photo/audio for the technician)
- [ ] Stop `handoff_gate` from routing media to a human during capture; store media as case evidence.
- [ ] Add the optional "algo más para el técnico" ask; never a mandatory field.
- [ ] Keep the triggers that must still fire (persona, complaint, injection, emergency).

### CI-5 — Golden-thread functional tests
- [ ] One functional test per family (booking, KB, escalation, hidden) covering the contract above.

### CI-6 — Tone pass (owner, deferred)
- [ ] Owner corrects copy during manual testing; adjust messages only.

## Acceptance criteria

1. The happy path closes in ~4–5 inbound turns with the client's natural, free-text answers.
2. A mid-capture pivot (prices, persona, another intent) is answered and the agenda resumes — no
   silent data corruption.
3. Emergencia still escalates instantly; booking stays deterministic; consent stays explicit.
4. All existing behavior (gates, booking, manage, KB) is preserved; `pytest tests/` green.
5. Copy is neutral Chilean Spanish.

## Checks

- Runner: `pytest tests/` (Strict TDD). No linter/typechecker configured.
- Graph Check before editing (nodes consulted below); `graphify . --update` once at session close.
- Conventional Commits, no AI attribution; ≤5 files per work-unit commit where cohesive.
- RDD: `review assess` per work-unit commit; run the returned transition when `review_due`.

## Graph Check (consulted)

`graphify query "customer whatsapp chat greeting menu classification capture booking handoff orchestrator"`
on the worktree graph (`graphify-out/`, built from `fe81ba01`): `greeting_with_menu()`, `capture()`,
`booking()`, `handoff()`, `build_graph()`, `ConversationState`, `chat/graph.py`, `chat/state.py`,
`app/services/settings.py`, `app/services/scheduling.py`, `test_chat_capture.py`,
`test_chat_booking.py`, `test_chat_manage.py`, `test_handoff.py`, `test_chat_state.py`.
`graphify path capture classify_intent` → no directed path (both routed from `receive`/`_flow_start`).

## Progress log

- Worktree `../lumat-agent-odd-chatbot-intake-redesign` on `odd/chatbot-intake-redesign` from `main` =
  `23ff4cd1` (owner approved; two parallel worktrees noted by the owner). Design doc created; no code
  written yet. Owner to approve the design before CI-1 starts.
- **Design approved (2026-10-08).** Owner approved the design and both decisions: (1) keep the evidence
  ask as an optional technician reference and make media not force handoff (CI-4); (2) `email`
  mandatory (CI-3). CI-1 authorized to start.
- **CI-1 implemented (2026-10-08).** Open greeting + greeting-only skip + consumer/test/spec updates.
  The first pass dropped "virtual" from the greeting; **restored** because `LumatRequest §1.3` requires
  identifying as "asistente virtual de Lumat" and several tests assert it. Files: `app/chat/graph.py`,
  `app/chat/nodes/receive.py`, `app/chat/nodes/respond.py`, `app/chat/state.py`,
  `app/services/settings.py`, `scripts/kb_fidelity.py`, `openspec/specs/conversation-manager/spec.md`,
  `tests/unit/test_chat_greeting.py` (new), and 5 test files updated.
  Verification: focused tests green; full suite `uv run pytest tests/` **EXIT=0** with two known-flaky
  seed subprocess tests deselected (`test_seed_demo.py::test_demo_seed_populates_dashboard_windows_and_today`,
  `test_seed.py::test_seed_applies_cleanly_twice`) — both pass in isolation; the stall is the intermittent
  suite hang documented in `pyproject.toml`, not CI-1. CI-1 commits `5800a099` (docs) and `76eaebec`
  (feat); PR #512 merged; review `review-359fcc5285c7a1b3` approved/acknowledged.
- **CI-2 implemented (2026-10-08).** Every non-greeting turn now classifies; retrieval deviations
  use research triage and resume the unchanged pending capture question after a KB hit. Mid-capture
  `unknown` does not consume HH-3 attempts; deterministic emergency/handoff/cost/closure gates remain
  ahead of classification. Cancellation/rescheduling mid-capture deliberately remains a field answer
  for CI-2. Files: `app/chat/state.py`, `app/chat/graph.py`,
  `app/chat/nodes/{orchestrate,classify_intent,capture}.py`,
  `tests/unit/test_routing_table.py`, `tests/integration/test_chat_capture.py`.
  RED: new dispatcher cases failed before implementation with `TypeError: _dispatch() got an
  unexpected keyword argument 'mid_capture'` (8 failures). GREEN: `uv run pytest
  tests/unit/test_routing_table.py -q` **27 passed** and `uv run python -m compileall -q app/chat`
  exited 0. Requested focused integration command blocked during migration with PostgreSQL
  `password authentication failed for user "app"` on port 5830; the broader suite has the same
  database setup failure. Requested second command also reports missing
  `tests/functional/test_triage_reply_duplication.py` (the file is under `tests/integration/`).
  CI-2 code commit: `229c732f`. This progress-log change is delivered by the accompanying
  `docs(odd): record CI-2 review state and CI-1 delivery in the task` commit.
- **CI-3a implemented (2026-10-08).** `email` added to the capture order (name, email, comuna,
  address, …) and persisted on the ficha; `consent` removed from `CAPTURE_FIELDS` and asked as its
  own explicit step after the data fields and before booking (a deviation on the consent step
  re-asks it). Files: `app/chat/nodes/capture.py`, `scripts/kb_fidelity.py`,
  `tests/integration/test_chat_capture.py`, `tests/functional/test_conversation_flows.py`,
  `tests/integration/test_handoff.py`, `tests/integration/test_out_of_hours_and_farewell.py`.
  RED: 7 capture/flow tests failed before implementation (email missing, consent still a field).
  GREEN: focused `uv run pytest tests/integration/test_chat_capture.py
  tests/functional/test_conversation_flows.py tests/integration/test_chat_booking.py
  tests/unit/test_kb_fidelity.py` **63 passed**; full suite `uv run pytest tests/` **EXIT 0** with
  the two known-flaky seed tests deselected. CI-3a code commit: `1a94d6a5`.
- **CI-3b (next):** multi-field extraction (reuse the single classifier LLM call — add a `fields`
  object to `agent/personas/classify.md`) plus grouped 2–3 questions replacing the single `_pending`
  model.
- **CI-3b implemented (2026-10-08).** The classifier now returns a `fields` object
  (`agent/personas/classify.md`, with the byte-identical `prompts.FALLBACKS` mirror), so one LLM
  call both classifies and extracts; `classify_intent` surfaces it as `state.extracted`. `capture`
  merges the extracted fields and asks the next 2–3 MISSING fields in one natural-language message,
  replacing the single-field `_pending` pointer with a batch list. A free-text answer that extracted
  nothing is attributed to the first asked field still missing. Files: `app/chat/state.py`,
  `app/chat/nodes/classify_intent.py`, `app/chat/nodes/capture.py`, `agent/personas/classify.md`,
  `app/services/prompts.py`, `tests/integration/test_chat_capture.py`,
  `tests/functional/test_conversation_flows.py`. Focused `uv run pytest` (capture/flows/booking/
  handoff/out-of-hours/prompts) **110 passed**; full suite **EXIT 0** with the two known-flaky seed
  tests deselected. New `test_cm3_extracts_multiple_fields_from_one_message` proves multi-field
  extraction from a single message. CI-3b code commit: see the accompanying `feat` commit.
