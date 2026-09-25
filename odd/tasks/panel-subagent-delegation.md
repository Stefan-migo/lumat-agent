# ODD: panel-subagent-delegation

**Branch**: `odd/panel-subagent-delegation`
**Worktree**: `/home/stefan/repos/lumat-agent-odd-panel-subagent-delegation`
**Base**: `96ba8ca2` (= `main` at branch time, `docs(ops): record the v2026.09.6 deploy`)
**Status**: **not started** — scope, mechanism and worker are decided and recorded; no source change exists yet. T1–T8 below are all open.
**Origin**: `.rapsodia-code/sessions/archived/2026-09-24-panel-agency-and-web-grounding/` (decisions 6 and 7, open question *does U3 delegate through the existing `research_triage` pattern, or a new panel subgraph?*); Engram #4890, #4896.

This is **U3 of three**: U1 (bounded tool chaining) is merged; U2 (local reader `web.fetch`) is merged. U3 was recorded as *"Not ready — do not start yet"* because it needed two decisions. Both were resolved before this document existed, and the resolution is recorded under **Decisions** below.

## Objective

Give the panel assistant a **bounded, read-only delegation span**: within one turn, the planner can hand a narrow operational-gathering task to the already-declared `customer_records` sub-agent, which runs a small number of read-only tool calls against its own restricted whitelist and returns **evidence** — never an answer — into the existing grounding path.

The point is **agency and context narrowing**, not new data access. Today the panel planner must select from the assistant's full 23-tool catalog (~2,471 tokens/turn) on every turn. A delegated worker plans against 6 tools instead.

## Problem — measured, not inferred

Verified on `96ba8ca2`, not from memory:

| Claim | Evidence |
|---|---|
| Delegation is declared, not built | `{"sdb": "deferred", "panel_subagents": "not_implemented"}` (`app/chat/assistant/nodes.py:76`) |
| A gathering worker is already declared and inert | `customer_records` declares `persona: personas/customer_records.md` and `tools_whitelist: []` (`agent/registry.yaml:29-35`; empty list at `:32`) |
| Its persona already states the job | *"You organize customer-record context for the Lumat assistant. Use only authorized customer data, preserve uncertainty, and never invent a record or mutate data without an explicit approved tool call."* (`agent/personas/customer_records.md`, 1 line) |
| The declarative model is already modelled and validated | `SubAgent` dataclass (`app/agent_registry.py:49`), `Registry.sub_agents` (`:83-87`), `_build_subagent` validation (`:184-210`), registry refuses an empty `sub_agents:` block (`:243-247`) |
| What is missing is invocation, not declaration | `load_registry()` exposes `sub_agents`, but no runtime path consumes one on the panel side (`app/agent_registry.py:213,272`) |
| The assistant planner has no delegation kind | `PlannerOutput.kind: Literal["tool", "respond", "complex"]`, `extra="forbid"` (`app/chat/assistant/state.py:27-39`) |
| Guardrails validates against the **assistant** whitelist only | `whitelisted = tool_name in config.tools_whitelist` (`app/chat/assistant/nodes.py:589`) |
| The panel planner catalog is built from the assistant whitelist | `_planner_tool_catalog(config.tools_whitelist)` (`app/chat/assistant/nodes.py:471-479`, `:484`) |
| The loop cap is 2 steps | `MAX_ASSISTANT_TOOL_STEPS = 2` (`app/chat/assistant/nodes.py:40`) |
| Chaining is read-only end to end | guardrails refuses any non-read-only tool at `tool_steps >= 1` (`nodes.py:602-616`, decision `loop_write_refused`); `tool_loop_head` ends the turn on any write (`nodes.py:676-684`) |
| The operational read tools cannot drill down by customer | `customers.search`/`.list` and `conversations.search`/`.list` take `query?`+`limit` only; `appointments.upcoming` takes `limit` only and is pinned to a 30-day window; `cases.list` is open-only (`app/chat/assistant/tools/registry.py:50-73`, `:250-269`) |
| Only customer-scope memory supports per-entity reads | `_CustomerMemoryArgs` carries `scope: "customer"` + `entity_id` (`registry.py:100-125`) |

## Decisions (owner-confirmed, 2026-09-25)

**D1 — U3 is a delegation unit only; drill-down reads are a sibling unit.** The per-customer read gap is real and recorded (see *Follow-ups*), but it is a **visibility** concern, not an agency one. Adding tools here would merge two independently reviewable concerns and dilute the security review of new data-access surface. The delegation design also tells us *which* drill-down reads are actually worth adding; building them first would be guessing.

**D2 — Wire the already-declared `customer_records` worker; do not invent a new one.** Its persona already defines the read-only gathering job and `agent_registry.py` already validates it. Its `tools_whitelist: []` is why it is inert. This turns the `not_implemented` confession into a real, tested capability.

**D3 — Mechanism: a scoped span over the existing loop, not a second graph.** No nested compiled subgraph and no second planner runtime. The span reuses `parse_planner_output`, `get_tool`, `TOOL_REGISTRY`, `bounded_fallback` and `_planner_tool_catalog(whitelist)` with the sub-agent's persona and whitelist. The customer path's `_triage_node` wrapper exists solely to work around the `replies` reducer on the shared `ConversationState` (`app/chat/graph.py:176-202`); that workaround is customer-specific and MUST NOT be copied here.

**D4 — Read-only end to end.** A write inside the span is refused, consistent with U1's D3. A worker that needs to write is out of scope.

**D5 — The span returns evidence, not an answer.** Results land in the existing evidence path with provenance so the responder answers and cites. Nothing bypasses the grounding route.

**D6 — The delegation counts as ONE parent step.** `tool_steps` advances by one for the whole span, so `MAX_ASSISTANT_TOOL_STEPS = 2` keeps its meaning. The span has its own, smaller internal cap.

**D7 — The sub-agent whitelist MUST NOT grow the panel planner catalog.** Verified: the catalog comes from the assistant's `tools_whitelist` only. A test pins this.

**D8 — No new tools, no new dependency, no write-policy change, no bound raised.**

## Contract

1. A `delegate` plan kind routes one turn to the `customer_records` span; the span runs bounded read-only steps and returns structured evidence.
2. The span's tool scope is exactly the sub-agent's `tools_whitelist`. Tools outside it are refused as explicitly as a non-whitelisted tool is today.
3. Every write inside the span is refused with an explicit, testable decision — never silently executed.
4. The span is bounded: its step cap is observable, and an exhausted cap ends the span rather than looping.
5. A normal (non-delegating) turn is unchanged in cost and shape.
6. `assistant.capabilities` stays derived, and the assistant's own whitelist and tool count are unchanged.
7. The panel planner catalog is byte-identical before and after this unit.
8. Read-only memory reads inside the span honour the sub-agent's `memoria_scope: "customer"`.
9. No approval path, `resume_thread` or SDB behaviour changes.

## Scope

### In scope

| File | Change |
|---|---|
| `agent/registry.yaml` | real `tools_whitelist` for `customer_records`; roster comment updated to name the wired workers |
| `agent/personas/customer_records.md` | expand the one-line persona into a gathering contract that returns evidence |
| `app/agent_registry.py` | only if a resolver helper is needed; declaration/validation already exists |
| `app/chat/assistant/state.py` | `PlannerOutput`: `delegate` kind + the sub-agent selector field |
| `app/chat/assistant/graph.py` | the span node + its conditional route from `guardrails` |
| `app/chat/assistant/nodes.py` | guardrails validation branch for `delegate`; the bounded read-only span; evidence handoff; cost accounting for the span's LLM calls |
| `agent/prompts/assistant_plan.md` | how and when to emit a `delegate` plan |
| `openspec/specs/assistant-tools/spec.md` | new requirement AT-14 |
| `tests/unit/test_assistant_delegation.py` (new) | span bound, scope enforcement, write refusal, evidence shape, catalog invariance |
| `tests/integration/test_assistant_harness_guardrails.py` | a real cross-domain delegated turn end to end |
| `odd/tasks/panel-subagent-delegation.md` | this document |

### Out of scope

- **Drill-down reads** (per-customer appointments, cases, conversations) — sibling unit, see *Follow-ups*.
- The duplicate tool names `customers.list` / `conversations.list` (same handlers as `.search`) and the duplicated `SearchArgs`/`QueryArgs`/`CapabilitiesArgs` shape — tool-catalog hygiene lane.
- `appointments.upcoming` being pinned to a 30-day window with no filter — data lane.
- Porting the `research_triage` pattern wholesale; a nested panel subgraph.
- Lazy tool loading (already rejected 2026-09-17) and the schema-trim A/B — their own lane.
- Any write capability for a delegated worker.
- Deploying to production.

## Tasks (strict TDD — observed RED before each source change)

- [ ] **T1 — Registry: give the declared worker a real scope, RED + GREEN.** Non-empty read-only whitelist for `customer_records` (`customers.search`, `conversations.search`, `appointments.upcoming`, `cases.list`, `memory.read`, `memory.search`); runtime resolution of a declared sub-agent; its persona expanded into a gathering contract. RED: the resolver returns the declaration and its scope; a write tool in the whitelist is rejected.
- [ ] **T2 — Plan kind `delegate`, RED + GREEN.** Extend `PlannerOutput` (`extra="forbid"` already prevents sneaking fields); guardrails validates the named sub-agent as declared, read-only and non-empty before routing. RED: an unknown sub-agent and an empty-scope sub-agent are each refused with an explicit decision.
- [ ] **T3 — The bounded read-only span, RED + GREEN.** The span runs scoped plan→execute read-only steps, refuses every write, and stops on its own cap. RED: cap observable at the boundary; a write at the span's first step is refused; a second read-only step is permitted.
- [ ] **T4 — Evidence handoff, RED + GREEN.** The span's results enter `tool_results`/`evidence` with provenance and stay inside the existing tool-evidence budget. RED: evidence shape, provenance and bound.
- [ ] **T5 — Graph wiring + unchanged normal turns, RED + GREEN.** Conditional route from `guardrails`; `tool_steps` advances by exactly one for the whole span; a non-delegating turn is byte-identical in shape and cost.
- [ ] **T6 — Cost accounting, RED + GREEN.** The span's LLM calls are counted by the existing cost path; an unaccounted call is a test failure. RED.
- [ ] **T7 — Spec, AT-14.** Requirement with individually refutable scenarios.
- [ ] **T8 — Harness and regression.** A real cross-domain turn (e.g. *which customers have open cases and an appointment in the next 30 days*) delegates, gathers, and answers citing evidence; full suite green; catalog invariance pinned.

## Acceptance criteria

1. A delegated turn gathers over the operational domain and answers from the returned evidence with citations.
2. The span's scope is exactly the sub-agent's whitelist; an out-of-scope tool is refused explicitly.
3. Every write inside the span is refused with an explicit decision.
4. The span cap is observable and terminates the span.
5. A normal turn is unchanged in cost and shape, and the panel planner catalog is byte-identical before and after.
6. `panel_subagents` no longer reports `not_implemented` for `customer_records`.
7. Full suite green; no bound raised; the approval path, `resume_thread` and SDB behaviour untouched.

## Checks

```bash
cp ../lumat-agent/infra/.env infra/.env
uv sync
bash infra/test-db.sh up
eval "$(bash infra/test-db.sh env)"

uv run pytest tests/unit/test_assistant_delegation.py
uv run pytest tests/unit/test_agent_registry.py tests/unit/test_assistant_planner.py
uv run pytest tests/unit/test_assistant_tools.py tests/unit/test_assistant_config.py
uv run pytest tests/integration/test_assistant_harness_guardrails.py tests/integration/test_assistant_chat.py
uv run pytest tests/

git status --short
git diff --check
```

No linter, typechecker, pre-commit or hooks exist. **The tests are the verification.**

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml:38`; test command `uv run pytest tests/` (`:29`); runner `pytest` (`:40`).
- One concern per commit, ≤5 files per commit, Conventional Commits.
- **No `Co-Authored-By` and no AI attribution in commits.**
- English artifacts (code, identifiers, comments, tests, docs).
- No test may reach the network.
- Bounds are bounds: `_TOOL_EVIDENCE_LIMIT` and `MAX_ASSISTANT_TOOL_STEPS` are not raised to make this fit.
- Ponytail after the code exists: report findings, never remove authorized behaviour.

## Delivery forecast

Estimated ~400–550 authored lines, at or above the ~400-line review budget. If it exceeds the budget, this ships as **chained PRs**; the chain strategy and slice boundaries are the owner's call and are recorded here before the first slice opens.

## Graph nodes consulted (Graph Check, Step 1)

- `graphify query "panel assistant subgraph delegation orchestrate research_triage context handoff"` → `orchestrate()` (`app/chat/nodes/orchestrate.py:102`), `_dispatch()` (`:46`), `app/chat/subgraphs/research_triage.py:54` (`_kb_check`), `app/chat/graph.py:204` (`build_graph()`), `app/chat/state.py:136` (`ConversationState`), `app/agent_registry.py:69` (`Assistant`), `:44` (`RegistryError`).
- `graphify query "assistant graph state schema panel_cost_gate tool_loop bounded iteration"` → `build_assistant_graph()` (`app/chat/assistant/graph.py:114`), `run_assistant()` (`:167`), `plan_llm()` (`nodes.py:482`), `guardrails()` (`:574`), `execute()` (`:756`), `tool_loop_head()` (`:657`), `panel_cost_gate()` (`:439`), `parse_planner_output()` (`:195`), `retrieve_kb()` (`:706`), `bounded_fallback()` (`:163`), `AssistantState`, `app/services/costs.py:148,241`.
- `graphify-out/GRAPH_REPORT.md`; hubs: `nodes.py`, `assistant/state.py`, `research_triage.py`, `agent_registry.py`, `test_routing_table.py`.
- **Delegation output is a lead, not a fact.** A delegated mapper in this repo previously reported a file as non-existent that did exist. Every claim in *Problem* above was re-verified by the orchestrator with `file:line` before this document was written.

## Follow-ups (not this unit)

1. **Per-customer drill-down reads** — the sibling unit. `appointments.upcoming` has no customer filter and a fixed 30-day window (`registry.py:262-265`); `cases.list` is open-only (`:268-269`); `customers`/`conversations` are query+limit only. A read-only gather worker can correlate across global lists but cannot assemble one customer's dossier except from customer-scope memory.
2. **Tool-catalog duplication** — `customers.search`/`customers.list` and `conversations.search`/`conversations.list` are two names each for one handler (`registry.py:510-513`, `:250-259`); `SearchArgs`, `QueryArgs`, `CapabilitiesArgs` are one shape repeated (`:50-64`). ~224 tokens/turn of pure duplication at the measured ~112 tokens/tool.
3. **Catalog schema trim** — measured ~2,471 tokens/turn at the U1 baseline; there is still no post-U2 measurement. Decide before the whitelist grows again (`Engram #4899`, `#4901`).

## Progress (condensed)

- Exploration completed **before** this document existed: both U3 pre-decisions (delegation mechanism, context handoff) were resolved with `file:line` evidence, and the owner confirmed the worker (`customer_records`) and the delegation-only scope on 2026-09-25.
- No source change yet. T1 is the first implementation task.

## Next step

Start at **T1** with strict TDD: observe RED on the registry scope/resolution before touching `agent/registry.yaml`.
