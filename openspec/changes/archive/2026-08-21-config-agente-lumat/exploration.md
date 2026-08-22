# Exploration: config-agente-lumat — LumatAgent "cerebro" layer (prompts/skills/registry)

> SDD change: `config-agente-lumat` · Source: `.cortex-sessions/2026-08-19-arquitectura-agente-lumat/report.md` (CLOSED, D1-D7)
> Post-apply TDD: pytest · Artifact store hybrid (openspec + engram)

## Current State

The conversation graph (LangGraph StateGraph over `ConversationState`) runs
LLM calls with **system prompts hardcoded as module constants** in three nodes,
plus a hardcoded user-slot template in two. All LLM calls go through
`app/services/llm.py` (`openai_client()`, `CHAT_MODEL`, multi-provider deepseek/
openrouter). There is a **second config surface already in place**: the `settings`
KV table (`app/services/settings.py`) drives emergency keywords, safety protocol
content, scope rules, tone and message overrides — but the persona/system prompts
have deliberately stayed outside it ("Message content defaults live in the chat
nodes … callers pass their constant as `default`", `settings.py:194-198`).

### LLM system prompts (extractable)

| Location | Constant | Size | Usage |
|---|---|---|---|
| `app/chat/nodes/respond.py:41` | `SYSTEM_PROMPT` | ~8 sentence-lines | static system slot; `+ BRIEF_MODE_SUFFIX` concatenated when conservative mode |
| `app/chat/nodes/respond.py:54` | `BRIEF_MODE_SUFFIX` | 1 line | appended (concatenation, not a slot) |
| `app/chat/nodes/classify_intent.py:56` | `SYSTEM_PROMPT` | ~16 lines | static system slot; returns JSON schema in text |
| `app/chat/nodes/summary.py:22` | `SYSTEM_PROMPT` | ~6 lines | static system slot |

### Hardcoded user-slot templates (extractable, typed `{{}}` candidates)

| Location | Template | Placeholders |
|---|---|---|
| `respond.py:101` | `<kb>{kb_text}</kb>\n\n<user_input>{text}</user_input>` | kb_text, text |
| `classify_intent.py:93` | `<user_input>{text}</user_input>` | text |
| `summary.py:31-39` | `Cliente: … Conversacion … (f-string)` | name, phone, conversation_id, turn, intent, case, captured, escalate, escalate_reason |

### Canned/deterministic reply strings (NOT system prompts)

- `respond.py:30` `CANNOT_ANSWER_REPLY`, `respond.py:35` `CLARIFICATION_REPLY`
- `state.py:48-51` `GREETING_HEADER` + `MENU_CATEGORIES` (CM-1), consumed by `greeting_with_menu()`
- `handoff.py:40` `HANDOFF_REPLY`
- `capture.py:26-35` `CAPTURE_FIELDS` (8 question strings) + `COMPLETION_REPLY`
- `emergency.py` safety protocol — **already settings-driven** (`get_setting`), defaults in `settings.py` — NOT a target

### Deterministic rule lists (NOT prompts)

`classify_intent.py:_INJECTION_PATTERNS` (SH-4), `handoff_gate.py:_PERSONA_PATTERN/_COMPLAINT_WORDS`,
`emergency.py:WEAK_MARKERS`, `route.py:CAPTURE_INTENTS/RETRIEVAL_INTENTS`. These are
deterministic gates, the SDB-in-graph structure the report already decided to keep
in code (D, no textual skill needed).

### Test coupling (extraction is test-safe)

Tests assert the **shape/static-ness** of system prompts, never their exact content:
- `test_chat_intent.py:202` — "system prompt is static: no user text leaked into it"
- `test_chat_capture.py:201` — "KB content never in the system prompt"
- `test_chat_intent.py` respx mock inspects the **user slot** (`<user_input>`), not system content; classify result is driven by user text only

So extracting text out of the nodes into `prompts.load(...)` does not break the
integration/injection suites. Only `CANNOT_ANSWER_REPLY` / `HANDOFF_REPLY` are
imported by tests (`test_chat_capture.py:22`, `test_injection_suite.py:39`,
`test_cost_guardrails.py:440/451`), so those must remain importable (or tests
updated to read from the loader).

## Affected Areas

- `app/chat/nodes/respond.py` — `SYSTEM_PROMPT` + `BRIEF_MODE_SUFFIX` + `<kb>/<user_input>` template → `personas/orchestrator.md` + `prompts/respond.md`
- `app/chat/nodes/classify_intent.py` — `SYSTEM_PROMPT` + `<user_input>` template → `prompts/classify.md`
- `app/chat/nodes/summary.py` — `SYSTEM_PROMPT` + `_summary_context` f-string → `prompts/summary.md`
- `app/services/llm.py` — unchanged; loader consumes openai_client/CHAT_MODEL
- `app/services/prompts.py` — **new** loader (single file, reads `agent/` at boot, resolves `{{var}}` slots)
- `agent/personas/*.md`, `agent/prompts/*.md`, `agent/registry.yaml` — new declaration files
- `tests/integration/test_chat_intent.py`, `test_chat_capture.py`, `test_cost_guardrails.py`, `test_injection_suite.py`, `test/functional/test_conversation_flows.py` — must keep passing (coupling via `CANNOT_ANSWER_REPLY`/`HANDOFF_REPLY` imports)
- `openspec/specs/` — no main-spec changes expected this phase (declarative only; behavior preserved)

## Approaches

### A. Extract only the orchestrator core (respond + classify), keep summary/handoff inline
- Pros: smallest diff; touches the two persona prompts the report explicitly flags; low test churn
- Cons: partial extraction leaves two sources of truth (files + constants); the SDB-vs-text question stays unresolved; handoff/capture canned strings remain in code
- Effort: Low

### B. Extract ALL LLM system prompts + user-slot templates to `agent/`, leave canned reply strings in code
- Pros: one source of truth for every thing the LLM sees; canned replies stay close to the deterministic logic that emits them (they are user-facing copy, not prompts); matches "prompts = data" (D2) without over-reach
- Cons: 3 persona files + 3 prompt templates + loader; needs the `{{}}` typing discipline
- Effort: Medium

### C. Extract prompts + canned replies + rule lists into one wholesale `agent/` config blob
- Pros: maximal configurability (OWUI-parity)
- Cons: over-engineering on this iteration (violates Ponytail YAGNI #1); the deterministic gates are SDB **structure**, not copy — pulling `_INJECTION_PATTERNS`/`WEAK_MARKERS` into files adds indirection with zero runtime value; JSON-schema prompts must never become regex lists
- Effort: High

**Recommendation: Approach B**, scoped down by these answers to the open questions (below). Canned customer-facing strings and deterministic rule lists stay in code — they are not prompts.

## Open Questions Resolved

1. **All prompts or just respond/classify?** — ALL LLM prompts (respond + classify + summary). Three files, all "things the LLM is told." Summary is 6 lines but is a real persona; partial extraction (report Q1) creates two sources of truth. Canned reply strings stay in code.
2. **Registry: 1 agent or 5 placeholders?** — Registry of exactly **1 agent today** (`orchestrator`). The other four (whatsapp/calendar/automation/…) are Fase-2 sub-agents behind a not-yet-built router; placeholders are YAGNI. Registry schema/fields defined now (D4), only orchestrator registered.
3. **MVP skills?** — `sdb` documented as a skill file this iteration BUT not force-loaded; `emergency.md`/`handoff.md`/`capture.md` as **declarative references only** (pointers to the deterministic nodes), not executable protocols. The real SDB for Lumat is the deterministic graph (gates), which stays in code. Do NOT port the PersonalAgent 7-phase SDB protocol into a prompt this iteration — it would add a prompt the model can ignore while the gates already enforce.
4. **SDB as skill or graph?** — Graph (deterministic gates) stays authoritative. `skills/sdb.md` may exist as the declarative reference file, but the runtime does NOT load it into any LLM prompt in this change. This honors the report's "SDB doble" without making a decorative prompt.
5. **Typed `{{}}` variables — scope?** — Only the **user-slot templates** need variables: `{{kb}}`, `{{user_input}}` (respond), `{{user_input}}` (classify), and the summary context block. System persona files are static (no variables) — they are the fixed identity. Introduce a minimal `render(template, **vars)` that replaces `{{name}}` and is strict (raises on missing var) so a typo in a prompt fails fast. Do not build a general templating engine.
6. **Filesystem read vs constants fallback?** — Loader reads files at boot with `lru_cache`; **fallback to the current constants** when a file is missing, so a partially-specified `agent/` tree (and any env without files mounted) still boots and tests that construct a raw node unedited still pass. Fallback keeps the diff green without wiring filesystem fixtures into every test.

## Recommendation

Approach B with registry=1 agent, skills as declarative references only, SDB as graph (not a loaded prompt), typed `{{}}` only on user-slot templates, and a file→constant fallback loader. This is a config-extraction change, not a framework: one new loader file, three persona files, three prompt-template files, one registry YAML, delete the constants from the three nodes. Canned reply strings and deterministic gate lists remain in code.

**Ponytail guard on the whole change**: every "skill" file must be justified as copy the LLM reads. If it is not loaded into a prompt, it is either a declarative reference (fine as a comment/pointer) or YAGNI (drop it). The loader must be one function + strict renderer, not a package.

## Risks

- **Prompt drift / degradation**: exact wording moves out of the nodes; mitigated by conftest mock only driving off user text (SH-4 isolation tests keep passing — they check the system prompt stays static, not its content), and by the strict `{{}}` renderer failing fast on typos.
- **Fallback masking**: a constant fallback can hide a missing file silently. Mitigate: loader logs a `warning` when it falls back, and the registry/tests assert the loaded persona equals the expected file content.
- **Test import coupling**: `CANNOT_ANSWER_REPLY`, `HANDOFF_REPLY` are imported by several suites; either keep them importable as thin re-exports from the loader or update those imports in the same change (keep with `work-unit-commits`).
- **Scope creep toward a "framework"**: registry schema, tools whitelist, KB scoping, memoria scoping are all Fase-2 consumers of this declaration — do NOT implement their enforcement now. Registry is data-only (D4 "declaration"), runtime enforcement is future.

## Ready for Proposal

**Yes.** The proposal should: adopt Approach B, register exactly 1 agent (orchestrator), keep the deterministic gates as the SDB (no loaded SDB skill prompt), tighten "skills" to declarative references + drop unused ones, and scope typed `{{}}` to the three user-slot templates.

**Graph nodes consulted**: `graphify query "prompts system prompt hardcoded nodes"` → 232 nodes; key nodes/communities — `respond.py` (`record_audit` community), `classify_intent.py` (`get_or_create_case`), `summary.py`, `state.py`, `graph.py`, `node ./checkpoints`, `services/settings.py` (`get_setting`), `Message` god node, `ConversationState`, `set_conversation_state()`, `emergency()`, `_protocol_replies()`, `test_chat_intent.py`, `test_chat_capture.py`, `test_cost_guardrails.py`, `test_handoff.py`. Graph `GRAPH_REPORT.md` hubs confirm: `state.py`, `graph.py`, `get_setting`, `trackers: test_chat_intent/test_chat_capture`. Graph current at commit `d8f26896` (refreshed 2026-08-20).
