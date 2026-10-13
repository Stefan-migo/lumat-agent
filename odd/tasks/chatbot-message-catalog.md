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

## Open implementation decisions (resolved in T0)

- **D3** — How it picks: new field in `classify_intent`'s structured output (**reuses the
  call that already runs**) vs new node/call. *Report recommends: reuse.*
- **D4** — Where templates live: settings KV (`messages.templates`) vs own table, and
  validation on save.
- **D5** — How injected templates are delimited/marked as DATA (anti-injection).
- **D6** — Confirm admin-only with no extra approval (Settings precedent).

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

The catalog lives in the **same Settings tab "Mensajes"**, but as **its own card**, separate
from the existing "Mensajes del asistente" card (the 5 fixed system messages). The card copy
must explain the difference to the owner: the 5 fixed messages fire on their own in specific
code paths; the catalog templates are **chosen by the bot** per turn and sent filled with
real data.

Frontend delta: `MESSAGE_TEMPLATES` (`Settings.tsx:43-49`) stops being the source of truth —
the new card renders the backend list. The 5 fixed messages and `MessagesBody` stay as they
are (low blast radius).

## Tasks

| ID | Task | Route |
|---|---|---|
| T0 | Design: resolve D3–D6; fix the template data shape and the exact integration point (node + prompt key) | inline (design) |
| T1 | RED+GREEN: curated template list accessor on the settings KV + save-time validation (D4/D5) | delegated (writer) |
| T2 | RED+GREEN: admin-only GET/PUT for the list (D6) | delegated (writer) |
| T3 | RED+GREEN: Settings → tab "Mensajes" → **new dedicated card** to manage the list, with copy explaining the difference vs the 5 fixed messages | delegated (writer) |
| T4 | RED+GREEN: `classify.md` + `_llm_classify` carry the picked template key (D3); update `FALLBACKS` + byte-coupling test | delegated (writer) |
| T5 | RED+GREEN: bot renders the picked template via `prompts.render` with slots from `captured`/`booking`; no match → `cannot_answer` + escalation (D13/D9) | delegated (writer) |
| T6 | Anti-injection delimiting for template text injected into the prompt (D5) | delegated (writer) |
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

`classify_intent()` → `_llm_classify()` → `render()` (2 hops, extracted); `Settings()` /
`Settings.tsx`; `settings` accessors; `app/services/templates.py` (checked — unrelated to this
catalog). Ref: `graphify-out/GRAPH_REPORT.md`.

## Progress

- [ ] T0 · [ ] T1 · [ ] T2 · [ ] T3 · [ ] T4 · [ ] T5 · [ ] T6 · [ ] T7

## Next step

Run T0 (design + code map) in this worktree, resolve D3–D6, then start T1.
The greeting bug is a **separate** unit (`chatbot-first-turn-greeting`) — do not mix it in.
