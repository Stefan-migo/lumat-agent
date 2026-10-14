# ODD — chatbot-conversation-inspection

Feature: `chatbot-conversation-inspection` (Frente 2, unit 2)
Branch: `odd/chatbot-conversation-inspection` · Base: `main` = `36c57d29`
Delivery: single PR · Test runner: `uv run pytest tests/`

## Objective

Give the panel assistant the **read** half it is missing: not just *how much* the WhatsApp
bot is failing (unit 1 metrics) but *which* conversations to look at, and the bounded
transcript of each. Two new **read-only** tools: `analytics.chatbot_conversations`
(find candidates by failure signal) and `conversations.transcript` (read one conversation).

## Specs

**S1 — `analytics.chatbot_conversations` finder (read-only).**
Args model `ChatbotConversationsArgs`, `extra="forbid"`:
`window_days: int` (default `7`, `ge=1`, `le=31`), `signal: Literal["escalation",
"unknown_intent", "kb_miss", "any"]` (default `"any"`), `limit: int` (default `10`, `ge=1`,
`le=MAX_ITEMS`). Read-only, tier `default`, roles ADMIN + OPERADOR. Handler defers the
service import (`from app.services import analytics`), mirroring `_chatbot_metrics`.

**S2 — `conversations.transcript` reader (read-only).**
Args model `ConversationTranscriptArgs`, `extra="forbid"`: `conversation_id: int` (`gt=0`),
`limit: int` (default `MAX_ITEMS` = 20, `ge=1`, `le=MAX_ITEMS`). Read-only, tier `default`,
roles ADMIN + OPERADOR.

**S3 — Service layer (read-only, no writes).**
`app/services/analytics.py::chatbot_conversations(session, window_days, signal, limit)` and
`app/services/conversations.py::conversation_transcript(session, conversation_id, limit)`.
Window mirrors `chatbot_metrics`: `start = now(utc) - timedelta(days=window_days)`.

**S4 — Signal semantics (exact, from persisted `ConversationEvent`).**
`escalation` → `event == "escalation"`; `unknown_intent` → `event == "unknown_intent"`;
`kb_miss` → `event == "escalation"` AND `cause == "handoff:kb_miss"`; `any` → union of the
three. Never invent event names.

**S5 — Finder output.**
```
{"window_days": int, "signal": str, "conversations": [
  {"conversation_id": int, "customer_id": int, "wa_phone": str, "state": str,
   "last_message_at": iso|None,
   "signals": {"escalation": int, "unknown_intent": int, "kb_miss": int}}]}
```
Ordered by most recent matching event desc, then `conversation_id` desc; bounded by `limit`.

**S6 — Transcript output.**
```
{"conversation": {"id", "customer_id", "wa_phone", "state", "summary",
                  "last_message_at", "closed_at"},
 "messages": [{"direction", "msg_type", "text", "created_at"}],   # last `limit`, chronological
 "messages_total": int,
 "events": [{"event", "cause", "created_at"}]}                    # oldest first, bounded
```
`direction`/`msg_type`/`state` are their `.value` strings. Unknown `conversation_id` raises a
runtime error surfaced as `status:"error"` (never a fabricated empty conversation).

**S7 — Wiring.**
Both tools in `TOOL_REGISTRY`, `ROLE_TOOL_ALLOWLIST` (ADMIN + OPERADOR only, never TECNICO),
`agent/registry.yaml` `assistant.tools_whitelist`, and the `DEFAULT_TOOLS` sets in
`tests/unit/test_tool_tiers.py` **and** `tests/unit/test_effective_config.py`.

**S8 — Empty window / no data.** Empty windows return empty lists and zero counts; never
`null`-fabricated rows. Rates/avgs are unit 1's concern, not this unit.

## Tasks

| ID | Task | Specs | Route |
|---|---|---|---|
| T1 | RED+GREEN: `analytics.chatbot_conversations` + `tests/integration/test_analytics.py` cases | S1,S3,S4,S5,S8 | inline |
| T2 | RED+GREEN: `conversations.conversation_transcript` + transcript tests | S2,S3,S6,S8 | inline |
| T3 | Register both tools in `TOOL_REGISTRY` + handlers + args models | S1,S2,S5,S6 | inline |
| T4 | Wire `ROLE_TOOL_ALLOWLIST` + `agent/registry.yaml` + both `DEFAULT_TOOLS` test sets + typed/bounded/whitelist unit tests | S7 | inline |
| T5 | Checks: targeted suites + full `uv run pytest tests/ -q` | — | inline |

Single writer; each task closes with one work-unit commit (≤5 files).

## Constraints (verified)

- **Strict TDD ON** — `openspec/config.yaml:28` (`tdd: true`), `:38` (`strict_tdd: true`).
  RED before implementation. Runner: `uv run pytest tests/`.
- Adding a tool breaks **two** exact-tier sets: `tests/unit/test_tool_tiers.py` and
  `tests/unit/test_effective_config.py`. Both must list the new tools.
- `tests/unit/test_assistant_tool_roles.py` derives ADMIN/OPERADOR from `TOOL_REGISTRY` and
  asserts `set(ROLE_TOOL_ALLOWLIST) == set(TOOL_REGISTRY)`; keep both new tools mapped.
- Tool must be in `TOOL_REGISTRY` **and** `assistant.tools_whitelist` or the catalog drops it.
- Keep panel-coupled imports deferred inside handlers (`_search_conversations`, `_kpis`).
- `realtime.activity_events(conversation_id)` already bounds activity rows for one conversation.
- Test DB: `bash infra/test-db.sh up` + `eval "$(bash infra/test-db.sh env)"`.

## Acceptance criteria

- AC-1: finder returns the right conversations for each signal and `any`, ordered + bounded.
- AC-2: transcript returns last-`limit` messages chronological + `messages_total` + events.
- AC-3: both tools appear in `tool_schemas()`, are `read_only`, tier `default`, in the
  assistant whitelist; ADMIN+OPERADOR allowed, TECNICO denied.
- AC-4: `uv run pytest tests/ -q` green.

## Checks

- `uv run pytest tests/integration/test_analytics.py tests/unit/test_assistant_tools.py tests/unit/test_tool_tiers.py tests/unit/test_effective_config.py tests/unit/test_assistant_tool_roles.py -q`
- `uv run pytest tests/ -q`

## Graph nodes consulted

`execute_tool()`, `get_tool()`, `ToolValidationError`, `Registry`, `Assistant`,
`test_assistant_tool_roles.py`, `agent_registry.py`, `conversations`, `metrics_at()` —
communities `registry.py` / `agent_registry.py` / `unit/test_assistant_tools.py`.

## Log

**L1 (user, 2026-10-14, verbatim):** "si vamos con eso." — tras elegir el alcance **B**:
finder de conversaciones problemáticas **+** lector de transcript (dos tools read-only).

**L2 (user, 2026-10-14):** la Unidad 2 del Frente 2 es "inspección de conversaciones ←
arrancar acá: que el asistente lea conversaciones reales (bounded) para diagnosticar"
(handoff `odd/handoffs/chatbot-assistant-optimizer.md`).

**L3 (evidence, 2026-10-14):** T1–T5 done in `odd/chatbot-conversation-inspection`.
RED→GREEN observed for T1 (`ImportError: cannot import name 'chatbot_conversations'`) and T2
(`ImportError: cannot import name 'conversation_transcript'`). Full suite `uv run pytest tests/`
exit 0. Added tools changed the pinned planner-catalog SHA-256; verified the only delta is the two
new tools (reduced whitelist reproduces the old hash `fcad2ba6…`), then updated the baseline.

## Progress

- [x] T1 — `36d0e1c7` feat: `chatbot_conversations` finder (+5 tests)
- [x] T2 — `17a22c29` feat: `conversation_transcript` (+4 tests)
- [x] T3+T4 — `0014f8ef` feat: register both tools (+ typed/whitelist tests); `4867f6b0` test: pin roles
- [x] T5 — `2aa818f4` test: planner catalog baseline hash; full suite green (exit 0)

## Next step

Unit 2 complete. Do NOT start unit 3 (N1-2 approval loop) without a fresh owner conversation.
