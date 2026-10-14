# ODD — chatbot-message-catalog

Feature: `chatbot-message-catalog` (Unidad A del handoff `chatbot-message-catalog-odd`)
Branch: `odd/chatbot-message-catalog` · Base: `main` = `870de162`

Source of truth for the design: `.rapsodia-code/sessions/ready-for-odd/2026-10-13-chatbot-message-system/report.md`
(Engram `#6506`). **Do not re-litigate the closed decisions.**

## Objective

Let the owner add **preset messages** from the panel Settings UI, and have the WhatsApp
bot **pick one** per turn and **fill it with real data** through deterministic slots. If
nothing in the list fits, the bot **escalates** (current behaviour). The bot's output stays
bounded to *approved templates + real data* — no room to invent.

## Problem / Why

Today the bot answers either KB-grounded text governed by `tone`, or one of 5 fixed
standard messages (`MESSAGE_DEFAULTS`). There is no way for the owner to add coverage for
situations the bot does not handle, without free-text writing by the LLM. This unit adds a
curated, owner-editable list the LLM **selects from** while the system renders the data.

## Scope

**In:** curated template list storage (settings KV) + admin-only API + Settings UI section +
selection by the bot's existing classifier call + deterministic render with slots +
anti-injection delimiting + test coverage.

**Out:** KB/retrieval (future migration, D10), free-text writing (D9), the panel assistant
(D14), removing `tone` (D7).

## Closed design decisions (do not re-litigate)

| D | Decision |
|---|---|
| D0 / D0b | Trigger is **coverage**. "Approved word in sensitive moments" was discarded |
| D1 / D2 | **Variant of mechanism 2** (LLM picks / system fills) + escalate on no match. **General**, not only high-risk. Not mechanism 1 nor 3 |
| D7 | The catalog **coexists** with `tone` — neither replaces nor removes it |
| D8 | The picked message **is adapted** and gains **real data** |
| D9 | No match → **escalate** with `cannot_answer` + handoff. **No free-text writing** |
| D10 / D12 | **Curated, expandable list**; KB is a future migration. Corpus separate from the KB |
| D13 | **LLM picks / system fills** via deterministic slots. The LLM does **not** rewrite |
| D14 | WhatsApp chatbot only. The bot pipeline LLM **is not** the Lumat Agent |

## T0 — implementation decisions (resolved)

- **D3** — How it picks: **reuse** `classify_intent`'s structured output — add the picked
  template id to the same JSON the classifier already returns (one LLM call per turn, no new
  node/call).
- **D4** — Where templates live: **settings KV** under `messages.templates` (a JSON list),
  reusing the generic KV surface + admin-only routes + audit. No new table (YAGNI — the
  report caps the list at *dozens*).
- **D5** — Anti-injection: injected templates are delimited/marked as **DATA** exactly like
  `<kb>`/`<user_input>`; validate on save.
- **D6** — Routes stay **admin-only** (`require_admin_json`), Settings precedent.

### Data shape (D4)

`settings` key `messages.templates` -> JSON list of `{"id": "<slug>", "text": "<template with
{{slots}}>"}`. Validation on save: `id` is a **unique slug**; `text` non-empty; every slot is
in the **allowed vocabulary** (pending below) so the bot can always fill it — otherwise
`prompts.render` would `KeyError` at send time.

### Integration point (design intent)

- Classifier: the same `_llm_classify` JSON gains the picked template id (`null` when none).
- Send path: if a template was picked -> render it with `prompts.render` from
  `captured`/`booking` and send it, **pre-empting** the KB path (this is what "freezes the
  voice" of what the catalog covers, D7). If none was picked -> the existing KB/`tone` path is
  **unchanged**; a KB miss still escalates with `cannot_answer` (D9). Keeps D7 coexistence and
  minimizes blast radius.

### Slot vocabulary (resolved, validated on save)

Owner-facing Spanish slots, all render-safe (the system always supplies them, `""` when
unknown):

| Slot | Source |
|---|---|
| `{{nombre}}` | `captured["name"]` |
| `{{comuna}}` | `captured["comuna"]` |
| `{{direccion}}` | `captured["address"]` |
| `{{equipo}}` | `captured["equipment"]` |
| `{{problema}}` | `captured["failure"]` |
| `{{disponibilidad}}` | `captured["availability"]` |
| `{{visita}}` | `booking["label"]` (`""` when no booking) |

- A `captured` value of `"unknown"` renders as `""`.
- Save validation rejects any `{{slot}}` outside this vocabulary (prevents a runtime
  `KeyError` from strict `prompts.render`).
- At send time only the slots present in the template text are passed (strict render).
- `booking` has **no** separate fecha/hora keys — it is `{service, label, status}` and
  `label` is already formatted (`state.py:248-256`); hence `{{visita}}`.

### Hook point (resolved)

- `classify_intent` (`app/chat/nodes/classify_intent.py:156`) returns **`template_id`** (the
  picked id, or `None`) from its existing LLM call.
- `orchestrate._dispatch` routes a **retrieval intent** (`consulta`/`valores`/`postventa`) with
  a picked `template_id` straight to `respond`, so a KB miss cannot hand it off; capture/manage
  flows are untouched. **T5 scope refinement** (owner decision 2026-10-13 — see Log): without
  this, the preset only ever surfaced when the KB already had the answer, making the feature
  inert.
- `respond` checks `state.template_id` **first** (ahead of the clarification and KB paths): if
  set and stored, render the template and return it as the reply. Otherwise the existing
  clarification / KB / `cannot_answer` flow is untouched (D7 coexistence, D9 fallback).
- `ConversationState` gains `template_id: str | None = None` (`app/chat/state.py`, near `:184`).
- `respond` is the only emit point for a bot answer (greeting is emitted by `receive`).

## Integration map (verified against code)

- **Classifier already runs one LLM call per turn**: `classify_intent` (`app/chat/nodes/classify_intent.py:156`)
  → `_llm_classify` (`:69`) → system prompt `personas/classify.md`, user `prompts/classify.md`,
  returns JSON `{intent, service, priority, status, injection, fields}` (`:100-108`).
  `orchestrate` has **no LLM**. The bot **has no tools** → this is **not** a `ToolDefinition`.
- **Settings KV is generic**: `MESSAGE_DEFAULTS` (`app/services/settings.py:53`), `get_message`
  (`:18`), scope/emergency/tone accessors alongside. Routes are **admin-only** via
  `require_admin_json` (`app/panel/api/routes/settings.py:36`); the GET exposes messages by
  **iterating** `MESSAGE_DEFAULTS` (`settings.py:178`) — the mechanism is already generic.
- **Render already exists**: `prompts.render(key, **vars)` (`app/services/prompts.py:143-160`),
  **strict** — `KeyError` if a variable is missing **or** unused. Data source:
  `ConversationState.captured` + `booking`.
- **Prompts `agent/*.md` are byte-coupled to `FALLBACKS`** (`app/services/prompts.py:37-116`)
  with a test asserting `FALLBACKS[key] == agent/file`. Touching them forces fallback + tests.
- **Frontend**: `web/src/components/pages/Settings.tsx` (`MESSAGE_TEMPLATES` at `:43`).
- **KB + tone path (for coexistence, D7)**: `app/chat/nodes/respond.py:85-88` (tone),
  `:120-167` (retrieve → `_answer_from_kb` → `kb_miss`).

### UI placement (decided by owner)

The catalog lives in the **same Settings tab "Mensajes"**, **below** the existing "Mensajes
del asistente" card, as **its own card**. Card title: **"Respuestas prediseñadas"**. The 5
fixed messages and `MessagesBody` stay as they are (low blast radius).

Card copy (product UI is Spanish — match the existing strings' register):

- Description: "Plantillas que el bot elige solo según lo que pregunta el cliente. Se envían
  con los datos reales ya cargados (nombre, comuna, equipo o la visita agendada)."
- Difference note: "A diferencia de los Mensajes del asistente de arriba —que son fijos y se
  disparan solos en momentos puntuales (saludo, derivación, fuera de horario)— estas
  respuestas las selecciona el bot en cada conversación."

Frontend delta: `MESSAGE_TEMPLATES` (`Settings.tsx:43-49`) stops being the source of truth —
the new card renders the backend list.

## Tasks

| ID | Task | Route |
|---|---|---|
| T0 | Design: resolve D3–D6; fix the template data shape and the exact integration point (node + prompt key) | inline (design) |
| T1 | RED+GREEN: curated template list accessor on the settings KV + save-time validation (D4/D5) | delegated (writer) |
| T2 | RED+GREEN: admin-only GET/PUT for the list (D6) | delegated (writer) |
| T3 | RED+GREEN: Settings → tab "Mensajes" → **new dedicated card** to manage the list, with copy explaining the difference vs the 5 fixed messages | delegated (writer) |
| T4 | RED+GREEN: `classify.md` + `_llm_classify` carry the picked template key (D3); update `FALLBACKS` + byte-coupling test | inline (no writer trigger: single understood unit, no parallelism, no context backstop) |
| T5 | RED+GREEN: bot renders the picked template via `prompts.render_text` with slots from `captured`/`booking`; no match → existing clarify/KB/`cannot_answer` untouched (D13/D9) | inline (no writer trigger: single understood unit) |
| T6 | Anti-injection delimiting for template text injected into the prompt (D5) — **absorbed into T4**: the `<templates>` DATA block *is* the injection mechanism | in T4 |
| T7 | Full checks (`uv run pytest tests/ -q` + targeted panel), close with verification evidence | inline |

Single writer. Each task closes with one work-unit commit (Conventional Commit).
Task shape may be refined after T0 — keep IDs stable.

## Constraints (verified)

- **Strict TDD ON** — `openspec/config.yaml:28` (`tdd: true`), `:38` (`strict_tdd: true`).
  Runner: `uv run pytest tests/`. RED before implementation.
- Settings routes are **admin-only** (`require_admin_json`).
- `agent/*.md` are **byte-coupled** to `FALLBACKS` — touching them forces fallback + tests.
- The bot has **no tools**; do not model this as a `ToolDefinition`.
- **Test DB per worktree**: `infra/.env` copied (done) + `eval "$(bash infra/test-db.sh env)"`.
- `node_modules` is **not** installed in this worktree yet — needed before the `panel` check
  (T3).
- **Pre-merge**: bring `origin/main` into the branch; ruleset requires `test` + `panel`;
  **auto-merge is not enabled** — merge by hand only when the PR is `CLEAN`, and verify the
  local HEAD matches GitHub's tested `headRefOid`.
- **RDD is on** (global). Threshold policy stays as-is (`under_budget` does not trigger
  review; run on request).

## Acceptance criteria

- AC-1: The owner can add/edit/remove preset messages from Settings; they persist in the
  settings KV and are exposed to the bot.
- AC-2: On a turn that matches the list, the bot sends the **picked** template with real
  slots filled from `captured`/`booking` (no LLM rewriting).
- AC-3: When nothing matches, the bot escalates with `cannot_answer` + handoff (no free text).
- AC-4: Injected template text is delimited/marked as DATA.
- AC-5: The routes are admin-only.
- AC-6: `uv run pytest tests/ -q` green.

## Checks

- `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/ -q`
- Targeted: classifier + settings + bot-node suites touching this change (exact list set in T0).
- Panel: `npm run build` + panel suite (T3).

## Graph nodes consulted

`classify_intent()` → `_llm_classify()` → `render()` (2 hops, extracted); `respond()`
(`respond.py:120`, community `chat/graph.py`); `_answer_from_kb()` (`:67`); `ConversationState`
(`state.py:137`, community `chat/graph.py`); `booking()` (`nodes/booking.py:91`); `build_graph()`
(`graph.py:250`); `Settings()` / `Settings.tsx`; `settings` accessors; `app/services/templates.py`
(checked — unrelated to this catalog). Ref: `graphify-out/GRAPH_REPORT.md`.

## Progress

- [x] T0 · [x] T1 · [x] T2 · [x] T3 · [x] T4 (absorbs T6) · [x] T5 · [ ] T7

### Evidence

- T0 — design closed in this doc (commits `ac2d9c77`, `36319971`).
- T1 — `9be75a52` `feat(settings): add message template validation`. Adds
  `ALLOWED_MESSAGE_TEMPLATE_SLOTS`, `MESSAGE_TEMPLATES_KEY` (+ default in `SETTINGS_DEFAULTS`),
  `get_message_templates` (defensive) and `validate_message_templates` in
  `app/services/settings.py`; unit + integration tests. Focused suite re-run by the parent:
  **40 passed**. Notes: the slot regex is **mirrored** from `prompts._SLOT_RE` because
  `prompts -> agent_registry -> tools.registry -> settings` is a real import cycle; existing
  `FakeSession` was widened to any key (verified it does not change prior assertions).
- T2 — `71f3f0b5` `feat(panel): add admin-only message template routes`. `GET /settings` gains a
  top-level `templates` key; new `POST /settings/message-templates` (`MessageTemplatesBody` +
  `_parse_message_templates` mapping `ValueError` -> 400) registered **before** the
  `/settings/{section}` catch-all. Tests cover 401/403, the strict GET key set, and the
  validate/persist/reject round trip. Parent spot check: **64 passed**. RED was assertion-level
  (GET payload lacked `templates`).
- T3 — `c0d2a8af` `chore(web): add templates to Settings type and fixtures` + `8d6ed414`
  `feat(panel): add preset answers card to Settings`. Adds `templates` to the `Settings` type and
  every literal (incl. the `SETTINGS_KEYS` guard in `mockData/settings.test.ts`), plus the
  "Respuestas prediseñadas" card (own card below "Mensajes del asistente") with add/edit/remove rows
  and save via `POST /settings/message-templates`; server 400s surface through the existing
  `saveErrorDetail`. Parent checks: `npm test` **1178 passed**, `npm run build` (tsc -b) green.
  Notes: one **flaky** `AgentChat.test.tsx` case seen by the writer under full-suite load (passes in
  isolation and in the parent run) — unrelated to this change; cosmetic 1-space indent drift on the
  adjacent card; template rows use index-based React keys.

- T4 (absorbs T6) — `0f3eafce` `feat(chat): let the classifier pick a preset message`.
  The catalog is read in `_llm_classify` via `session_scope()` + `get_message_templates` and
  injected into the **USER** message as an inert `<templates>- id=<id>: <text></templates>`
  DATA block (empty catalog → `(sin respuestas prediseñadas)`) — never the static system
  prompt (SH-4). `agent/prompts/classify.md` gains `{{templates}}`; `agent/personas/classify.md`
  gains the selection rule + `"template_id": string|null`; both `FALLBACKS` entries updated
  byte-identically (the `test_fallbacks_equal_agent_files` guard still passes).
  `_llm_classify` returns `template_id`, keeping it **only** when it is an offered id (D13,
  untrusted LLM output); `classify_intent` propagates it on the non-injection paths;
  `ConversationState` gains `template_id: str | None = None`.
  RED first (KeyError/AssertionError), then GREEN. Routed **inline** (no writer trigger fired).
  Parent checks: focused `tests/unit/test_prompts.py` + `tests/integration/test_realtime_writers.py`
  + `tests/integration/test_chat_intent.py` + `tests/injection/` → **69 passed**; full backend
  `uv run pytest tests/ -q` → **green**. Behaviour for an empty catalog is unchanged
  (`template_id=None`); T5 owns the render/send path.
- T5 — `5a948b02` `feat(chat): render the preset message the classifier picked`.
  `respond` renders `state.template_id` with the system-filled slots (D13); the final routing
  placement is in the refinement bullet below. The clarification / KB / `cannot_answer` flow
  stays intact when nothing was picked (D9).
  `respond._slot_values` maps `{{nombre}}`, `{{comuna}}`, `{{direccion}}`, `{{equipo}}`,
  `{{problema}}`, `{{disponibilidad}}` to `captured[...]` and `{{visita}}` to
  `booking["label"]`, rendering `"unknown"`/missing as `""`.
  A stale id (catalog changed) falls through to the normal path instead of crashing.
  Because owner text lives in settings, not under `agent/`, `prompts` gained
  `render_text(content, **vars)` + `placeholders(content)` (same strict `{{}}` rules) and
  `render(key, **vars)` now delegates to `render_text` — single source of truth.
  RED first, then GREEN. Routed **inline**. Parent checks: `tests/unit/test_prompts.py` 42
  passed; full backend `uv run pytest tests/ -q` → **1985 passed** (0 failures).
- T5 refinement — `08166f0f` `fix(chat): let a picked preset pre-empt the retrieval answer path`.
  While proving the seam end-to-end I found the T0 hook point was effectively inert: retrieval
  intents went to `research_triage`, and a KB **miss** handed off before `respond` ran, so a
  preset only surfaced on a KB **hit**. Owner chose to **pre-empt the whole answer path**
  (retrieval hit/miss + unknown), keeping capture/manage intact. Fix: `orchestrate._dispatch`
  routes a retrieval intent with `template_id` straight to `respond`; `respond` checks the
  preset ahead of the clarification branch too. Tests: routing table (+7), `respond` unknown
  (+1), e2e `test_preset_answer_preempts_the_kb_miss_path` over `run_conversation` (+1). Full
  backend → **1994 passed**.

## Next step

T5 done (the picked preset message is rendered and pre-empts the answer path). Start
**T7**: full checks (`uv run pytest tests/ -q` + panel) and close with verification
evidence. The greeting bug is a **separate** unit (`chatbot-first-turn-greeting`) —
do not mix it in.

## Log

- L1 (2026-10-13, owner, at the T5 review, verbatim): "Pre-empta el camino de respuesta
  (Recomendado)" — a picked preset must pre-empt the whole answer path (retrieval KB hit **or**
  miss, and `unknown`), not only the KB-hit path; capture/manage flows stay intact. This
  refines the T0 hook point (which the T5 spike showed was inert).
