# Tasks: H2 — Multi-Agent LangGraph Router (slice-1)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~620 (adds+deletes) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (registry+reader) → PR 2 (orchestrate+sub-graph) → PR 3 (integration/tone) |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

Slice-1 only: router + KB research/triage runtime. Other four sub-agents **data-only** (declared, no runtime). Cost thresholds $1.50/$5.00 unchanged. No checkpointer, panel endpoints, new tables, or `audit_log` dispatch entries.

### Suggested Work Units (stacked-to-main)

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | registry sibling + persona + reader | PR 1 | `.venv/bin/pytest tests/unit/test_agent_registry.py tests/unit/test_prompts.py` | `.venv/bin/pytest tests/integration/test_chat_intent.py -k unknown` (AC-4) | rm reader + tests; graph untouched |
| 2 | kb.retrieve(scope) + orchestrate + subgraph + wiring + table | PR 2 | `.venv/bin/pytest tests/unit/test_routing_table.py` | `.venv/bin/pytest tests/integration/test_chat_intent.py -k valores` | revert → linear route/respond returns |
| 3 | integration + tone regression + full suite + README | PR 3 | `.venv/bin/pytest tests/` | `.venv/bin/pytest tests/integration/test_chat_capture.py -k cannot_answer` | revert PR 3; PRs 1-2 independent |

## Phase 1: Registry + Reader (PR 1)

- [x] 1.1 `agent/registry.yaml`: add `sub_agents:` **sibling** — five sub-agents (research_triage, retrieval, customer_records, human_handoff, escalation), all fields `name/persona/tools_whitelist/kb_scope/memoria_scope/model/temperature`; `agent:` block byte-identical (D1, AO-1, AC-4)
- [x] 1.2 Create `agent/personas/research_triage.md`, no `{{}}` slots (AO-1)
- [x] 1.3 Create `app/agent_registry.py`: frozen `Agent`/`SubAgent` + `load_registry()`; fail-fast on missing field / unknown `tools_whitelist` / bad `temperature` / not-exactly-one orchestrator; NOT imported by `prompts.py`/`respond.py` (D2, AO-2, AC-4)
- [x] 1.4 RED-first `tests/unit/test_agent_registry.py`: full roster, invalid rejected, no reads in prompts/respond; existing `test_registry_*` green (AO-1/AO-2, AC-4)

## Phase 2: Orchestrate + Sub-Graph (PR 2)

- [x] 2.1 `app/services/kb.py`: `retrieve(..., scope: list[str]|None=None)` additive filter on `source_meta.category` (JSONB convention, no schema change) + test with fixtures that set `source_meta.category` (D6, AO-7)
- [x] 2.2 `state.py`: add `active_sub_agent`, `triage_retry` fields
- [x] 2.3 RED-first `tests/unit/test_routing_table.py`: pure `(intent, flags)` dispatch all combos, no LLM; escalate flags → handoff; persona/emergencia/injection → handoff; CAPTURE_INTENTS → capture; RETRIEVAL_INTENTS → research; unknown → respond; else → respond — full table in design.md (AO-3)
- [x] 2.4 Create `nodes/orchestrate.py`: pure `_dispatch` + whitelist assert-in-dispatch; non-whitelisted → log + handoff (D3/D5, AO-6)
- [x] 2.5 Create `subgraphs/research_triage.py`: `classify_intent`(reused) → `kb.retrieve(scope)` → `respond`(reused); miss → retry ≤1 → handoff (AO-5/AO-7/AO-8). No re-implementation
- [x] 2.6 Wire `graph.py`: `orchestrate` after `handoff_gate` replacing the `route` node (dispatch table); gate prefix stays outer envelope (AO-4)

## Phase 3: Integration + Regression (PR 3)

- [x] 3.1 Extend `test_chat_intent`: valores/postventa → research; miss → retry → handoff reaches END (AO-3/AO-8)
- [x] 3.2 Invisible-tone regression: KB reply copy/tone/format equals pre-H2 reply (AO-9)
- [x] 3.3 Full `.venv/bin/pytest tests/` green; `test_chat_intent`/`test_handoff`/`test_cost_guardrails`/`test_registry_*` unchanged (AO-10)
- [x] 3.4 `agent/README.md`: multi-agent roster + slice-1 runtime + four data-only; no new tables (AO-1; doc-only)

## Dependencies

```
1.1,1.2 → 1.3 → 1.4
1.3 → 2.1 → 2.3,2.4,2.5 → 2.6
2.4 → 2.5 → 2.6
2.6 → 3.1,3.2 → 3.3 → 3.4
```
Strictly ordered PR 1 → PR 2 → PR 3 (stacked-to-main).

## Out of Scope (NOT in this change)

- Other four sub-agents **runtime** (retrieval, customer_records, human_handoff, escalation) — data-only this slice
- Per-agent `memoria_scope` runtime wiring
- Checkpointer (D2 — per-message rebuild)
- Production panel inbox/chat endpoints; M2 web; M3 payments
- New DB tables
- `audit_log` entries for sub-agent dispatch
- Gate-envelope redesign; cost-threshold change
