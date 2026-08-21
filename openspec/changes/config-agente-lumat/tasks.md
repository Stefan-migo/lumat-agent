# Tasks: LumatAgent "cerebro" layer (config-agente-lumat)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~415 (adds+deletes) |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (agent/ tree) → PR 2 (loader) → PR 3 (wire nodes) |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium

Resolution (design ordering note): `FALLBACKS` holds frozen **literal** prompt text
(not module-attr refs) — resolves the "captured at import" contradiction vs deleting
node `SYSTEM_PROMPT`. `tests/unit/test_prompts.py` asserts `agent/*.md == FALLBACKS[key]`.

### Suggested Work Units (stacked-to-main)

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Create `agent/` tree + equality tests vs untouched node constants | PR 1 | `pytest tests/unit/test_prompts.py::test_personas_static` | `pytest tests/integration/test_chat_intent.py -k unknown` | `rm -rf agent; rm tests/unit/test_prompts.py` — nodes untouched |
| 2 | `app/services/prompts.py`: `load()`+`render()`+literal `FALLBACKS`+unit tests | PR 2 | `pytest tests/unit/test_prompts.py` | N/A — pure dict/str function, no network/LLM | `rm app/services/prompts.py` (nodes not yet wired) |
| 3 | Wire respond/classify/summary to loader; delete node constants | PR 3 | `pytest tests/` | `pytest tests/functional/test_conversation_flows.py -k cannot_answer` (CM-4) + `-k handoff` | revert PR 3 → constants return, PRs 1-2 additive |

## Phase 1: agent/ tree (PR 1)

- [x] 1.1 Create `agent/personas/orchestrator.md`, `orchestrator_brief.md`, `classify.md`, `summary.md` = verbatim current `respond.SYSTEM_PROMPT`/`BRIEF_MODE_SUFFIX`, `classify_intent.SYSTEM_PROMPT`, `summary.SYSTEM_PROMPT` (AC-1, AC-3)
- [x] 1.2 Create `agent/prompts/respond.md` (`<kb>{{kb_text}}</kb>\n\n<user_input>{{user_input}}</user_input>`), `classify.md`, `summary.md` templates with `{{}}` slots (AC-1, AC-5)
- [x] 1.3 Create `agent/skills/{sdb,emergency,handoff,capture}.md` reference-only pointers; never loaded into prompts (AC-6)
- [x] 1.4 Create `agent/registry.yaml`: data-only, exactly `orchestrator`, fields per D-A7 schema (AC-4)
- [x] 1.5 Create `agent/README.md`: layout + D6 triggers prose (AC-7)
- [x] 1.6 Add `tests/unit/conftest.py` (DB-free) + `tests/unit/test_prompts.py` asserting file content equals node constants (RED-first, AC-3/AC-6) — plus registry assertion: `registry.yaml` parses to exactly 1 `orchestrator` per D-A7 schema, no runtime consumer (AC-4)

## Phase 2: Loader (PR 2)

- [x] 2.1 Create `app/services/prompts.py`: `load(key)` with `@lru_cache(32)` + literal `FALLBACKS` + `warning` on fallback (AC-2)
- [x] 2.2 Add `render(key, **vars)`: strict `{{var}}` substitute, raise on missing/unknown var, personastatic guarantee (AC-5)
- [x] 2.3 Extend `tests/unit/test_prompts.py`: fallback returns constant+warning (AC-2); render raises on missing var (AC-5); `agent/*.md == FALLBACKS[key]` (AC-3); `load()` returns file verbatim (AC-2)

## Phase 3: Wire nodes (PR 3)

- [ ] 3.1 `respond.py`: `_answer_from_kb` = `load("personas/orchestrator.md") + (load("personas/orchestrator_brief.md") if brief)` + `render("prompts/respond.md", ...)`; delete `SYSTEM_PROMPT`/`BRIEF_MODE_SUFFIX`; keep `CANNOT_ANSWER_REPLY`/`CLARIFICATION_REPLY` export (AC-3, AC-8)
- [ ] 3.2 `classify_intent.py`: `_llm_classify` = `load("personas/classify.md")` + `render("prompts/classify.md", user_input=text)`; delete `SYSTEM_PROMPT`; keep `_INJECTION_PATTERNS`/`is_injection` (AC-3)
- [ ] 3.3 `summary.py`: `generate_summary` = `load("personas/summary.md")` + `render("prompts/summary.md", name=..., phone=..., ...)`; delete `SYSTEM_PROMPT`; `_summary_context` computes slot values (AC-3)
- [ ] 3.4 Full `pytest tests/` green: CM-4/CM-5/SH-4/handoff/cost-guardrail suites unchanged; AC-3 equality proven end-to-end

## Phase 4: Docs / D6

- [ ] 4.1 Confirm `agent/README.md` states 3 D6 triggers + hybrid pattern; no DB change (AC-7)
- [ ] 4.2 Cleanup: no dead constants left; `CANNOT_ANSWER_REPLY`/`HANDOFF_REPLY` still importable (AC-8)
