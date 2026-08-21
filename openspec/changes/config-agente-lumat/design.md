# Design: LumatAgent "cerebro" layer (config-agente-lumat)

## Technical Approach

Behavior-preserving extraction (Approach B, exploration §Recommendation): move every LLM-facing prompt out of node constants into declarative files under `agent/`, loaded through one new loader (`app/services/prompts.py`) with a file→constant fallback. Canned customer-facing strings and deterministic gate lists stay in code. No framework, no DB, no runtime registry consumer (Fase-2 router owns enforcement). Maps AC-1..AC-8.

## Architecture Decisions

| # | Decision | Choice | Alternatives rejected | Rationale |
|---|----------|--------|------------------------|-----------|
| D-A1 | Loader scope | `prompts.load(key) -> str` + `prompts.render(key, **vars)` in ONE file | package `prompts/`; runtime registry reader | Report "one loader function, not a package"; registry has no consumer this iteration (Ponytail YAGNI) |
| D-A2 | File discovery | keys are relative paths resolved against `agent/` root (`"personas/orchestrator.md"`) | separate config index | Direct path = no indirection; `agent/` tree IS the index |
| D-A3 | Caching | `load()` decorated `@lru_cache(maxsize=32)` at boot | no cache; full boot read | Matches `app/config.py` convention (`get_settings` + `cache_clear`); bounded (32 keys > 10 files) |
| D-A4 | Fallback semantics | known-key→constant map; on missing file log `warning` + return constant verbatim | hard raise | Partial `agent/` trees and raw-node tests stay green (AC-2); equals pre-change constant (AC-3) |
| D-A5 | Brief mode | `BRIEF_MODE_SUFFIX` → `personas/orchestrator_brief.md`; node concatenates `load(base) + load(brief)` when `brief` | inline in base file; keep as code const | It is LLM identity text the LLM reads; two files preserve the exact conditional concatenation (AC-3) |
| D-A6 | Kernel surface | `CANNOT_ANSWER_REPLY`/`CLARIFICATION_REPLY`/`HANDOFF_REPLY` NEVER move | extract to loader, add compat module | They are canned copy (AC-3), not prompts; tests import from current modules → AC-8 satisfied trivially, no compat module (deletion over addition) |
| D-A7 | Registry | `registry.yaml` data-only; no runtime loader; validated by a test | runtime YAML reader module | AC-4/MUST NOT enforce; a reader is YAGNI until the H2 router |
| D-A8 | D6 doc | prose in `agent/README.md`, not a YAML comment | registry comment | Triggers are guidance (AC-7), prose reads better; YAML stays data-only |

## Data Flow

```
agent/registry.yaml ── validated by test (data-only, no runtime reader)
agent/personas/orchestrator.md ──┐
agent/personas/orchestrator_brief.md ──┤
agent/prompts/respond.md ──┼──► app/services/prompts.py ──► nodes ──► openai_client()
agent/prompts/classify.md ──┤         (load/render, lru_cache,      (llm.py unchanged)
agent/prompts/summary.md  ──┘          fallback map)
agent/skills/*.md ── never loaded into any prompt (AC-6)
agent/README.md ── D6 triggers (AC-7)
```

Nodes call `prompts.load("personas/orchestrator.md")` (system slot) and `prompts.render("prompts/respond.md", kb_text=..., user_input=...)` (user slot); `llm.py`/`openai_client()` unchanged.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/prompts.py` | Create | Single loader: `load()` (lru_cache + fallback map + warning), `render()` strict `{{}}` |
| `agent/personas/orchestrator.md` | Create | text of `respond.SYSTEM_PROMPT` verbatim |
| `agent/personas/orchestrator_brief.md` | Create | text of `respond.BRIEF_MODE_SUFFIX` verbatim |
| `agent/personas/classify.md` | Create | text of `classify_intent.SYSTEM_PROMPT` verbatim |
| `agent/personas/summary.md` | Create | text of `summary.SYSTEM_PROMPT` verbatim |
| `agent/prompts/respond.md` | Create | `<kb>{{kb_text}}</kb>\n\n<user_input>{{user_input}}</user_input>` |
| `agent/prompts/classify.md` | Create | `<user_input>{{user_input}}</user_input>` |
| `agent/prompts/summary.md` | Create | summary context f-string → `{{name}}/{{phone}}/{{conversation_id}}/{{turn}}/{{intent}}/{{case}}/{{captured}}/{{escalate}}/{{escalate_reason}}` |
| `agent/skills/sdb.md` | Create | declarative pointer to deterministic gates (never loaded) |
| `agent/skills/emergency.md` | Create | reference-only pointer to `emergency.py` gates |
| `agent/skills/handoff.md` | Create | reference-only pointer to `handoff_gate.py` rules |
| `agent/skills/capture.md` | Create | reference-only pointer to `capture.py` fields |
| `agent/registry.yaml` | Create | D4 schema, exactly `orchestrator` |
| `agent/README.md` | Create | layout guide + D6 triggers (AC-7) |
| `app/chat/nodes/respond.py` | Modify | delete `SYSTEM_PROMPT`/`BRIEF_MODE_SUFFIX`; `_answer_from_kb` loads personas + renders `prompts/respond.md`; keep `CANNOT_ANSWER_REPLY`/`CLARIFICATION_REPLY` + gate logic |
| `app/chat/nodes/classify_intent.py` | Modify | delete `SYSTEM_PROMPT`; `_llm_classify` loads `personas/classify.md` + renders `prompts/classify.md`; keep `_INJECTION_PATTERNS`/`is_injection` |
| `app/chat/nodes/summary.py` | Modify | delete `SYSTEM_PROMPT`; load `personas/summary.md` + render `prompts/summary.md`; `_summary_context` computes values, node renders |
| `tests/` | Modify | add loader/renderer/registry tests (new suite); existing suites stay green |

`agent/` hosts 4 persona files (orchestrator, orchestrator_brief, classify, summary), 3 prompt templates, 4 skill references.

## Interfaces / Contracts

```python
# app/services/prompts.py
def load(key: str) -> str:
    """Return agent/{key} verbatim. Fallback to FALLBACKS[key] constant + warning if missing."""
def render(key: str, **vars) -> str:
    """Substitute {{name}} placeholders; raise KeyError on missing/unknown var (AC-5)."""
FALLBACKS = {
    "personas/orchestrator.md": (respond_module, "SYSTEM_PROMPT"),   # captured at import
    "personas/orchestrator_brief.md": (respond_module, "BRIEF_MODE_SUFFIX"),
    "personas/classify.md": (classify_module, "SYSTEM_PROMPT"),
    "personas/summary.md": (summary_module, "SYSTEM_PROMPT"),
    "prompts/respond.md": (respond_module, "_RESPOND_USER_TEMPLATE"),
    "prompts/classify.md": (classify_module, "_CLASSIFY_USER_TEMPLATE"),
    "prompts/summary.md": (summary_module, "_SUMMARY_CONTEXT_TEMPLATE"),
}
```
`registry.yaml` (data, D4): `agent: { name: orchestrator, persona: personas/orchestrator.md, skills: [sdb, emergency, handoff, capture], tools_whitelist: [], kb_scope: null, memoria_scope: null, model: deepseek-chat }` — enforcement deferred to Fase-2.

## Node Refactor Mapping

| Node | Moves out (→ file) | Stays (code) | Import surface |
|------|--------------------|--------------|----------------|
| `respond.py` | base persona→`personas/orchestrator.md`; brief→`orchestrator_brief.md`; user slot→`prompts/respond.md` | `CANNOT_ANSWER_REPLY`, `CLARIFICATION_REPLY`, KB-miss gate, escalation | `CANNOT_ANSWER_REPLY` still exported (tests) |
| `classify_intent.py` | persona→`personas/classify.md`; user slot→`prompts/classify.md` | `_INJECTION_PATTERNS`/`is_injection`, unknown-intent counter, scope escalation | — |
| `summary.py` | persona→`personas/summary.md`; context→`prompts/summary.md` | `_summary_context` computes values; persistence logic | `generate_summary` shared w/ handoff unchanged |
| `handoff.py` (unchanged) | none | `HANDOFF_REPLY`, deriva bundle, state transition | `HANDOFF_REPLY` still exported (tests) |

## Testing Strategy

| Layer | What to test | Approach |
|-------|-------------|----------|
| Unit (new) | `load()` returns file verbatim when present; falls back + `warning` when missing | `tests/unit/test_prompts.py` (or collocate) — assert content equality with pre-change constants |
| Unit (new) | `render()` substitutes all `{{}}`; raises on missing/unknown var | strict-render test, AC-5 |
| Unit (new) | registry parses to exactly 1 `orchestrator`, no runtime consumer | YAML parse assert, AC-4 |
| Integration (stay green) | SH-4 injection, CM-4 KB-grounded/cannot-answer, CM-5 summary, unknown-intent, handoff, cost-guardrails, conversation flows | `tests/integration/test_chat_intent.py`, `test_chat_capture.py`, `test_handoff.py`, `test_cost_guardrails.py`, `tests/injection/test_injection_suite.py`, `tests/functional/test_conversation_flows.py` |
| E2E (stay green) | full webhook → graph run | `tests/functional/` flows |

**RED-first (apply.tdd):** write `test_prompts.py` (fallback warning, strict render raise, file→constant equality) + registry test before wiring nodes; existing suites prove no behavior drift.

## Threat Matrix

`N/A` — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary changes. Pure in-process config extraction.

## Migration / Rollout

No DB migration. Rollout: merge `agent/` + `prompts.py` + node edits as one work unit; fallback keeps partial deploys safe (AC-2). Rollback: revert commit → constants return, delete `agent/`/`prompts.py`. Fase-2 adds the router/registry-enforcement consumers.

## Open Questions

- [ ] Collocate new loader tests in `tests/unit/` (new) vs an existing suite — no unit dir today; tasks to confirm placement.
