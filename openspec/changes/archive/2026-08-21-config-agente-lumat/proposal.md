# Proposal: LumatAgent "cerebro" layer (prompts / skills / registry)

## Intent

Lumat runs LLM calls with system prompts hardcoded as module constants in three
nodes (`respond.py`, `classify_intent.py`, `summary.py`) plus user-slot templates
in two. This makes the agent's "brain" un-editable without code deploy and blocks
the H2 multi-agent router, which must dispatch by agent configuration. This change
moves every prompt the LLM reads into declarative files under `agent/`, behind a
single loader — the base the future LangGraph router consumes (D4).

## Scope

### In Scope
- Create `agent/` structure: `personas/`, `skills/`, `prompts/`, `registry.yaml`
- New loader `app/services/prompts.py` (one function + strict `{{var}}` renderer)
- Extract 3 system prompts + 3 user-slot templates into files; delete node constants
- Registry: exact 1 agent (`orchestrator`); schema fields defined, data-only declaration
- `skills/` as declarative reference files only (pointers to deterministic nodes), never loaded into prompts
- Keep canned reply strings (`CANNOT_ANSWER_REPLY`, `HANDOFF_REPLY`, etc.) re-exportable for tests
- Document D6 DB-migration triggers (in design/specs, no DB work now)

### Out of Scope
- Tools-whitelist enforcement, KB/memoria scoping, LangGraph router (Fase-2, registry consumers)
- Loaded SDB prompt: deterministic gates stay the authoritative SDB; `skills/sdb.md` is reference-only
- 5 sub-agent placeholder personas (only orchestrator registered)
- Any UI / DB migration / new framework

## Capabilities

> Contract with specs phase. Researched `openspec/specs/`.

### New Capabilities
- `agent-config`: `agent/` layout, `registry.yaml` schema (1 orchestrator agent), skills as reference files, D6 migration triggers

### Modified Capabilities
None — pure behavior-preserving extraction. `conversation-manager` CM-4/CM-5 behavior (guidance, summary) is unchanged; tests keep passing on shape/static-ness of prompts.

## Approach

Approach B from exploration: single source of truth for all LLM prompts. Nodes call
`prompts.load("personas/orchestrator.md")` / `prompts.render("prompts/respond.md", **vars)`.
Loader reads files at boot with `lru_cache`; falls back to current constants (with
`warning` log) so partial `agent/` trees and unedited raw-node tests stay green.
No framework, no DB. Pony tail: one loader function, not a package.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `agent/` | New | personas/ + prompts/ + skills/ + registry.yaml |
| `app/services/prompts.py` | New | single loader + strict renderer |
| `app/chat/nodes/respond.py` | Modified | SYSTEM_PROMPT, BRIEF_MODE_SUFFIX, `<kb>/<user_input>` template → loader |
| `app/chat/nodes/classify_intent.py` | Modified | SYSTEM_PROMPT, `<user_input>` template → loader |
| `app/chat/nodes/summary.py` | Modified | SYSTEM_PROMPT, context f-string → loader |
| `tests/**` | Modified | expect green; re-export `CANNOT_ANSWER_REPLY`/`HANDOFF_REPLY` where imported |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Prompt drift after move | Med | strict `{{}}` renderer fails fast on typos; SH-4/CM-4 suites assert static-ness |
| Constant fallback masks missing file | Med | loader logs `warning` on fallback; tests assert loaded persona == file content |
| Test import coupling | Med | keep `CANNOT_ANSWER_REPLY`/`HANDOFF_REPLY` re-exportable; same-change import cleanup |
| Scope creep to "framework" | Med | registry data-only; enforcement deferred to Fase-2 |

## Rollback Plan

Revert commit: constants return to nodes, delete `agent/` and `prompts.py`.
Loader fallback already preserves behavior on missing files, so partial deploy degrades safely.

## Dependencies

- `llm.py` (`openai_client()`/`CHAT_MODEL`) — consumed, unchanged
- Deterministic gate nodes (`emergency`, `handoff_gate`, injection) — remain the SDB, unchanged

## Success Criteria

- [ ] All 3 system prompts and 3 user-slot templates read from `agent/` via loader; node constants deleted
- [ ] `pytest tests/` green (CM-4/CM-5, SH-4, cost-guardrail suites pass unchanged behavior)
- [ ] `registry.yaml` declares `orchestrator` only; no prompt loads a skill file
- [ ] Loader falls back to constants (warning log) when `agent/` file missing

## Proposal question round

Assumptions for user review (blocked from interactive ask — auto mode):
1. Single `orchestrator` agent is enough; no placeholder personas this iteration (Ponytail YAGNI).
2. `skills/sdb.md` ships as a declarative reference only, NOT loaded into any prompt — the graph gates remain the authoritative SDB.
3. Canned customer-facing strings stay in code; only "things the LLM reads" move to `agent/`.
