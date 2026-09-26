# ODD: panel-subagent-delegation

**Branch**: `odd/panel-subagent-delegation`
**Worktree**: `/home/stefan/repos/lumat-agent-odd-panel-subagent-delegation`
**Base**: `96ba8ca2` (= `main` at branch time, `docs(ops): record the v2026.09.6 deploy`)
**Status**: **closed — all three slices merged.** Slice 1 (T1 + T2) = PR #359 (`d514d215`); slice 2 (T3 + T4) = PR #360 (`498e5346`); slice 3 (T5 + T6 + T7 + T8) = PR #364 (`fae7e0a9`), carrying a real native review receipt (lineage `review-7584730fa4dbaa68`, `approved`, authority burned — see *Review outcome — slice 3*). All eight tasks are implemented.
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
| `app/chat/assistant/delegation.py` (new) | the delegation-scope resolver: resolve a declared sub-agent for the panel span, expose its scope, and refuse a non-read-only scope |
| `app/chat/assistant/state.py` | `PlannerOutput`: `delegate` kind + the sub-agent selector field |
| `app/chat/assistant/graph.py` | the span node + its conditional route from `guardrails` |
| `app/chat/assistant/nodes.py` | guardrails validation branch for `delegate`; the bounded read-only span; evidence handoff; cost accounting for the span's LLM calls |
| `agent/prompts/assistant_plan.md` | how and when to emit a `delegate` plan — lands in the wiring slice (T5), never before the span exists |
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

- [x] **T1 — Registry: give the declared worker a real scope, RED + GREEN.** Non-empty read-only whitelist for `customer_records` (`customers.search`, `conversations.search`, `appointments.upcoming`, `cases.list`, `memory.read`, `memory.search`); runtime resolution of a declared sub-agent; its persona expanded into a gathering contract. RED was **import-level only** (the new module did not exist) — recorded honestly, no behavioural RED claimed. **Done** (`376d32ff`).
- [x] **T2 — Plan kind `delegate`, RED + GREEN.** Extend `PlannerOutput` (`extra="forbid"` already prevents sneaking fields); guardrails validates the named sub-agent as declared, read-only and non-empty. Until the span exists, a **valid** delegation terminates explicitly as `delegate_unavailable` and an invalid one as `delegate_refused` — both terminal, never a silent answer with no evidence. RED: both decisions absent, and a valid delegation routed to `respond_stream`. **Done** (`4ed428cf`, corrected in `2218cf7b`).
- [x] **T3 — The bounded read-only span, RED + GREEN.** The span runs scoped plan→execute read-only steps, refuses every write, and stops on its own cap. RED: cap observable at the boundary; a write at the span's first step is refused; a second read-only step is permitted. **Done** (`cbd6fda0`, corrected in `eb80186b`). RED was **seam-level only** (`AttributeError` on the still-absent `_delegation_plan`) — recorded honestly, no behavioural RED claimed. Contract #8 enforcement landed here: inside a customer-scoped span a `memory.read`/`memory.search` planned with `scope: "own"` is refused as `delegation_memory_scope_refused`, checked in the span before `execute_tool` runs.
- [x] **T4 — Evidence handoff, RED + GREEN.** The span's results enter `tool_results`/`evidence` with provenance and stay inside the existing tool-evidence budget. RED: `KeyError: 'evidence'` — the span had no evidence handoff field. **Done** (`9765992d`, corrected in `eb80186b`). The bound is structural rather than rendered: the evidence list cannot exceed the span's own cap.
- [x] **T5 — Graph wiring + unchanged normal turns, RED + GREEN.** Conditional route from `guardrails`; `tool_steps` advances by exactly one for the whole span; a non-delegating turn is byte-identical in shape and cost. **Done** (`2b819a77`, `8b1cd0d8`, `91dff2dd`, corrected in `bcfdb71c`). RED was behavioural and real here: the route assertions observed `'__end__' == 'delegation_span'` and the prompt assertion found `kind: "delegate"` absent. `delegate_unavailable` is gone entirely — invalid scopes stay terminal as `delegate_refused`. The gate caught that the required non-delegating-turn pin was missing on the first pass; it now exists as a live API turn that pins the persisted planner shape, `tool_steps == 0`, `cap_reached is False`, the absence of delegation state and the exact `planner`/`response` cost-call keys and values, and fails if the span is entered.
- [x] **T6 — Cost accounting, RED + GREEN.** The span's LLM calls are counted by the existing cost path; an unaccounted call is a test failure. RED: `assert 0 == 1` — no usage record was made. **Done** (`ebbd77d4`). `_delegation_plan` now calls the existing `_record_usage` helper with the key `delegation:<sub_agent>`, mirroring `plan_llm` — no second accounting path.
- [x] **T7 — Spec, AT-14.** Requirement with individually refutable scenarios. **Done** (`0d58ff1c`). `AT-14 — Bounded Read-Only Sub-Agent Delegation` in `openspec/specs/assistant-tools/spec.md`, seven GIVEN/WHEN/THEN scenarios, each falsifiable in isolation and matching the file's existing idiom. Honest note: the RED is only that the requirement did not exist (`git grep 'Requirement: AT-14'` exited 1) — there is no behavioural RED to claim for a spec. **No OpenSpec validation command exists in this repo**; nothing was invented to stand in for one.
- [x] **T8 — Harness and regression.** A real cross-domain turn (e.g. *which customers have open cases and an appointment in the next 30 days*) delegates, gathers, and answers citing evidence; full suite green; catalog invariance pinned. **Done** (`39216c0f`). The harness runs the real graph through `run_assistant` over seeded rows, executes the real read-only `cases.list` and `appointments.upcoming`, stubs four provider calls, and asserts the responder prompt carried both records and that the answer cites `[cases.list]` and `[appointments.upcoming]`. No behavioural RED is claimed: the first failure was a test-expectation mismatch, disclosed as such. Catalog invariance **was not** pinned by slice 1 (it checked contents, not bytes); it is now pinned by a serialized-catalog SHA-256 in `test_panel_planner_catalog_matches_pre_delegation_bytes`.

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

Estimated ~400–550 authored lines, at or above the ~400-line review budget.

**Delivery strategy: chained PRs — `stacked-to-main`** (owner-confirmed 2026-09-25). Each slice merges to `main` in order; the next slice's PR opens only after the previous one merges, and each slice rebases onto the new `main` before its PR.

| Slice | Tasks | What it delivers |
|---|---|---|
| 1 | T1 + T2 | The trust boundary: the worker's real scope + the `delegate` plan kind validated in guardrails |
| 2 | T3 + T4 | The mechanism: the bounded read-only span + the evidence handoff |
| 3 | T5 + T6 + T7 + T8 | Wiring, cost accounting, spec AT-14 and the cross-domain harness |

**Delivery record**: slice 1 → **PR #359** (`odd/panel-subagent-delegation` → `main`, merged as `d514d215`). Slice 2 → **PR #360** (`odd/panel-subagent-delegation-slice2` → `main`, merged as `498e5346`). Slice 3 → **PR #364** (`odd/panel-subagent-delegation-slice3` → `main`), branched from `498e5346`.

## Review outcome — slice 1

**The native review could not reach a terminal outcome, and no receipt, approval or authority was produced.** This is recorded plainly, because this slice ships with a broken review rather than a passed one.

- The preflight froze the candidate cleanly (`status/v9`, `fresh_target_ready`, 9 paths matching the diff), but the first invocation failed with `operation_failed` / `fresh target START runtime lacks immutable review transport` (`retry_safe: true`); one retry succeeded.
- Consent was relayed and granted; `review start --consent granted` created the transaction: lineage `review-fbbdf054020eb792`, state `reviewing`, one frozen lens slot (`review-reliability`), correction budget 200.
- Every subsequent eligibility check refused with `immutable_review_transport_unsupported` (`retry_safe: false`, `next_action: stop`, `mutation_outcome: not_started`): the provider-issued lineage-bound STATUS (twice), the captured candidate-scoped decline invocation (once), and the selectorless STATUS against a second worktree.
- **The supported-runtime list is not stable within one session and one repository**: one invocation reported `claude-code, opencode, codex`, a later one reported `claude-code, codex`. That contradiction is the strongest single piece of evidence. It was reported upstream as an occurrence on the canonical open tracker (`Gentleman-Programming/gentle-ai#4805`), confirmed by the created comment identity; no labels were changed on that issue.
- The prescribed fallback (`review assess --base-ref 96ba8ca2 --committed-only --json`) returned `risk: high`, reason `unassessable`, `changed_paths: 0`.
- `gentle-ai review mode disable` was **not** run; RDD remains enabled and untouched.

**Verification actually achieved.** The tier for an unassessable outcome is writer self-verification plus an independent verifier:

| Evidence | Result |
|---|---|
| Writer self-verification (focused suites) | `test_assistant_delegation.py` 13 passed · registry/planner/config 54 passed · assistant tools 71 passed · harness guardrails 32 passed |
| Independent verifier (static inspection + diff integrity) | Integrity confirmed (9 paths, commits match, planner prompt clean, worktree clean, `git diff --check` clean); two findings raised, both fixed |
| Parent-resolved full suite | `uv run pytest tests/` — **1,455 tests, 0 failures** (all progress marks, no `F`/`E`, no failure summary), **exit 0** |

**Independent-verifier findings, both fixed in `715c380e`:**
- The declared `memoria_scope: "customer"` was dropped from the resolved scope even though Contract #8 requires the span to honour it. It is now carried (`app/chat/assistant/delegation.py:19,47`) and pinned by a test. Enforcement stays in T3 — this slice exposes, it does not enforce.
- The roster comment claimed `customer_records` had no runtime behaviour. It now states precisely what is wired (declaration, resolution, guardrail validation) and what is not (no executable delegation span).

**Preserved state at slice close**: lineage `review-fbbdf054020eb792` remains `reviewing` with its single slot uncollected; no reviewer result, receipt, correction or approval exists; the candidate and working tree are unchanged; nothing is pushed.

## Review outcome — slice 2

**No native review was started, and native assessment says none was due.** The preflight ran and the provider offered a fresh candidate; the committed-work assessment then measured it as under budget.

- Selectorless preflight (`review status --cwd <worktree> --contract gentle-ai.review-integration/v2 --agent opencode --next-transition`) → `applicability: unrelated`, next transition `execute` with reason `fresh_target_ready`, 2 paths (`app/chat/assistant/nodes.py`, `tests/unit/test_assistant_delegation.py`), target `sha256:1fa8983e…`, lineage `review-45ea91538dfb59bb` minted. **The returned START was not invoked, so nothing was frozen** — no transaction, no slot, no consent envelope.
- `review assess --cwd <worktree> --base-ref cc783af0 --committed-only --json` → `risk: medium` (`executable_change` on `app/chat/assistant/nodes.py`), **`review_due: false`, `review_due_reason: under_budget`**. Measured at `changed_paths: 2`, `changed_lines: 160` on the implementation commits, and `3` / `216` once the correction, the coverage test and this record landed — the same verdict both times.
- Under the committed-work rule, `review_due: false` keeps the boundary pending and the work continues. Forcing a START instead would have burned a lineage in the environment whose immutable review transport is already known broken (*Review outcome — slice 1*), for a candidate native assessment had just measured as not due. `review mode status` reads `on (decided by global)`; nothing was disabled and RDD was not touched.

**Verification achieved.** Tier `medium` on a full-size model, so writer self-verification is the verification of record:

| Evidence | Result |
|---|---|
| Writer self-verification (focused suites) | `test_assistant_delegation.py` 16 passed · tool-loop/planner/registry 76 passed · harness guardrails 32 passed |
| Parent-resolved full suite | `uv run pytest tests/` — **1,458 tests, 0 failures, exit 0** (1,458 progress marks, no `F`/`E`; the summary line does not render under this repo's `-q` config, the marks do) |
| Parent adversarial readback of the diff | Two defects found and corrected in `eb80186b`: the span returned the router-consumed `status` value (pre-deciding `_after_execute`'s routing at `graph.py:94-95`), and it hand-rolled the evidence dict instead of reusing `make_evidence` (`app/chat/assistant/evidence.py:6`) |
| Parent coverage check | Contract #2 (out-of-scope tool refused) was implemented but unpinned; the parent added one characterization test in `17a44e4b` — **no RED claimed**, that refusal path already existed |

## Review outcome — slice 3

**This slice carries a real native review receipt.** Unlike slices 1 and 2, the transaction reached `approved` and its authority was burned.

- The first `review assess --cwd <worktree> --base-ref 498e5346 --committed-only --json`, taken before this record existed, returned `risk: medium`, 365 lines, **`review_due: false` / `under_budget`**. This record's own lines pushed the committed range to **405 lines across 11 paths**, and the same assessment then returned **`review_due: true`, `review_due_reason: slice_budget_reached`** — so the review became due and was taken.
- The preflight (`review status --base-ref=498e5346 --committed-only=true --next-transition=true`) offered a fresh candidate; `review start --consent=relay` returned the typed `gentle-ai.review-integration.consent/v3` envelope (risk `medium`, 11 files, 405 lines, reason `executable_change` on `agent/prompts/assistant_plan.md`). It was relayed losslessly and the owner answered `granted`.
- The transaction froze cleanly: lineage **`review-7584730fa4dbaa68`**, state `reviewing`, revision `sha256:4c0731b0…`, one selected lens (`review-reliability`, order 0), correction budget 200, `lenses_required: true`.
- The lens capture returned **`approved`**: no BLOCKER or CRITICAL findings, and **one advisory WARNING, deliberately non-blocking** — `R3-001` (`app/chat/assistant/nodes.py:579`, `inferential`, `introduced`): `delegation_node` resolves the worker scope without catching a scope-resolution failure, so a worker that became unresolvable between guardrail validation and the node would raise instead of producing the existing explicit refusal. The closure explicitly states that advisory findings open no correction and **must never reopen this review**; it is recorded below as follow-up work.
- Acknowledgement ran exactly once: **`gentle-ai review-acknowledged/v1`, action `acknowledged`, `authority: "burned"`**, consuming revision `sha256:79eeab74…`. The lifecycle then stops — delivery is a separate human decision.
- **Scope of the receipt**: it covers target `sha256:8e9a069c…` (11 paths, 405 lines). This record was edited *after* the acknowledgement to state the outcome truthfully, so the docs-only commits that follow are, by the ordering rule, outside that receipt. Measured against the reviewed boundary (`4391599f`, the last commit the receipt covers), that delta assesses as **`risk: passive`, `review_due: false`, `review_due_reason: passive`** — one path, 18 lines, documentation only.
- `review mode status` reads `on (decided by global)`; RDD was never disabled.

**Verification achieved.** Tier `medium`, and the native review above is the independent check:

| Evidence | Result |
|---|---|
| Writer self-verification (focused suites) | `test_assistant_delegation.py` 19 passed · tool-loop/planner/config/extensions 67 passed · harness + chat 88 passed |
| Parent-resolved full suite | `uv run pytest tests/` — **1,464 tests, 0 failures, exit 0** (1,464 progress marks, no `F`/`E`) |
| Parent adversarial readback of the diff | Three findings raised on the T5/T6 pass and all corrected in `bcfdb71c`: the required non-delegating-turn pin was missing, `PANEL_DELEGATION_UNAVAILABLE` survived as a dead constant now stating the opposite of the truth, and `panel_subagents` was derived from a declaration rather than from the span being executable |
| Native review | **approved**, authority burned, one non-blocking advisory finding (`R3-001`) |

## Graph nodes consulted (Graph Check, Step 1)

- `graphify query "panel assistant subgraph delegation orchestrate research_triage context handoff"` → `orchestrate()` (`app/chat/nodes/orchestrate.py:102`), `_dispatch()` (`:46`), `app/chat/subgraphs/research_triage.py:54` (`_kb_check`), `app/chat/graph.py:204` (`build_graph()`), `app/chat/state.py:136` (`ConversationState`), `app/agent_registry.py:69` (`Assistant`), `:44` (`RegistryError`).
- `graphify query "assistant graph state schema panel_cost_gate tool_loop bounded iteration"` → `build_assistant_graph()` (`app/chat/assistant/graph.py:114`), `run_assistant()` (`:167`), `plan_llm()` (`nodes.py:482`), `guardrails()` (`:574`), `execute()` (`:756`), `tool_loop_head()` (`:657`), `panel_cost_gate()` (`:439`), `parse_planner_output()` (`:195`), `retrieve_kb()` (`:706`), `bounded_fallback()` (`:163`), `AssistantState`, `app/services/costs.py:148,241`.
- `graphify-out/GRAPH_REPORT.md`; hubs: `nodes.py`, `assistant/state.py`, `research_triage.py`, `agent_registry.py`, `test_routing_table.py`.
- **Delegation output is a lead, not a fact.** A delegated mapper in this repo previously reported a file as non-existent that did exist. Every claim in *Problem* above was re-verified by the orchestrator with `file:line` before this document was written.
- Slice 2 queries (`graphify query "assistant bounded tool loop guardrails tool_results evidence budget"`, `graphify query "assistant delegation customer_records sub-agent whitelist memory scope"`, `graphify path "guardrails" "tool_loop_head"`) → `resolve_delegation_scope()` / `DelegationScope` / `DelegationScopeError` (`app/chat/assistant/delegation.py:10,15,22`), `_after_guardrails()` (`app/chat/assistant/graph.py:75`), `_after_execute()` (`:94`), `_after_tool_loop()` (`:98`), `guardrails()` / `tool_loop_head()` / `parse_planner_output()` / `bounded_fallback()` / `_context_text()` / `_render_tool_evidence()` (`app/chat/assistant/nodes.py`), `_read_memory()` / `_search_memory()` / `_owned_agent_memory_or_raise()` (`app/chat/assistant/tools/registry.py:285,327,395`), `TOOL_REGISTRY` / `get_tool()` / `execute_tool()` (`:535,546`), `_build_assistant()` (`app/agent_registry.py:128`), `make_evidence()` (`app/chat/assistant/evidence.py:6`), `customer-records Sub-agent` (`agent/registry.yaml`), `collect_evidence()` / `plan_llm()` / `execute()` (`nodes.py`). `graphify path "guardrails" "tool_loop_head"` returns **no directed path** — the two are joined through `execute`, not directly.
- The graph was refreshed once for this session (`graphify /home/stefan/repos/lumat-agent --update` → 7,939 nodes / 16,529 edges, then 7,957 / 16,576 at delivery close). `GRAPH_REPORT.md` still names an older commit as its build base while `graph.json` is newer; the report is advisory, the graph is what was queried.
- Slice 3 queries (`graphify query "assistant graph conditional edges route guardrails tool_loop_head tool_steps cap_reached"`, `graphify query "assistant cost accounting llm call record cost path services costs"`, `graphify path "guardrails" "execute"`) → `guardrails()` (`app/chat/assistant/nodes.py:666`), `tool_loop_head()` (`:781`), `execute()` (`:880`), `_record_usage()` (`:298`), `record_llm_cost()` (`app/services/costs.py:57`), `test_a_chained_read_only_turn_persists_tool_steps_and_cap_state()` (`tests/integration/test_assistant_chat.py:622`), `AT-13` (the neighbouring requirement used as the idiom model) and `assistant-tools Specification`. Both `graphify path "guardrails" "tool_loop_head"` and `graphify path "guardrails" "execute"` return **no directed path** — they join through the conditional-edge map, not directly.

## Follow-ups (not this unit)

1. **Per-customer drill-down reads** — the sibling unit. `appointments.upcoming` has no customer filter and a fixed 30-day window (`registry.py:262-265`); `cases.list` is open-only (`:268-269`); `customers`/`conversations` are query+limit only. A read-only gather worker can correlate across global lists but cannot assemble one customer's dossier except from customer-scope memory.
2. **Tool-catalog duplication** — `customers.search`/`customers.list` and `conversations.search`/`conversations.list` are two names each for one handler (`registry.py:510-513`, `:250-259`); `SearchArgs`, `QueryArgs`, `CapabilitiesArgs` are one shape repeated (`:50-64`). ~224 tokens/turn of pure duplication at the measured ~112 tokens/tool.
3. **Catalog schema trim** — measured ~2,471 tokens/turn at the U1 baseline; there is still no post-U2 measurement. Decide before the whitelist grows again (`Engram #4899`, `#4901`).
4. **`R3-001` — unguarded scope resolution at the delegation node** (`app/chat/assistant/nodes.py:579`, native review WARNING, `inferential`). `delegation_node` calls `resolve_delegation_scope` bare: a registry or persona that became unresolvable between guardrail validation and the node raises out of the turn instead of producing the existing explicit `delegate_refused`-style refusal. The window is one in-turn step, which is why the review declined to block, but the fix is cheap (resolve defensively and return the refusal) and belongs to a later change — **never to a re-run of this review**.

## Progress (condensed)

- Exploration completed **before** this document existed: both U3 pre-decisions (delegation mechanism, context handoff) were resolved with `file:line` evidence, and the owner confirmed the worker (`customer_records`) and the delegation-only scope on 2026-09-25.
- **Slice 1 (T1 + T2) implemented** on `odd/panel-subagent-delegation`: `376d32ff`, `4ed428cf`, corrected in `2218cf7b`. Files: `agent/registry.yaml`, `agent/personas/customer_records.md`, `app/chat/assistant/delegation.py` (new), `app/chat/assistant/state.py`, `app/chat/assistant/nodes.py`, `app/chat/assistant/graph.py`, `tests/unit/test_assistant_delegation.py` (new), `tests/unit/test_agent_registry.py`.
- **Gatekeeper caught a real integration failure in the first attempt**, and it is worth keeping: the first pass shipped the `assistant_plan.md` delegation instruction while nothing executed a delegation, and `_after_guardrails` did not know the `delegate` decisions — so a validated delegation fell through to `respond_stream` (an answer with zero gathered evidence, forbidden by contract #1) and the `delegate_refused` refusal was silently discarded. One corrective round fixed all four findings: the prompt change moved to the wiring slice, both delegate decisions became terminal, the orphan `delegating` status was removed, and the refusal became a named constant.
- **Lesson for the remaining slices**: a trust-boundary slice must not make the planner aware of a capability the graph cannot execute, and every new decision a node returns must have a consumer in the router.
- **Slice 1 verified as far as this environment allows**: focused suites green, an independent verifier confirmed diff integrity and raised two findings (both fixed in `715c380e`), and the parent-resolved full suite is **1,455 tests / 0 failures / exit 0**. The native review receipt does not exist — see *Review outcome — slice 1*.
- **Slice 2 (T3 + T4) implemented** on `odd/panel-subagent-delegation-slice2` off `cc783af0`: `cbd6fda0` (span), `9765992d` (evidence provenance), corrected in `eb80186b`, plus the parent's characterization test in `17a44e4b`. Files: `app/chat/assistant/nodes.py`, `tests/unit/test_assistant_delegation.py`. **158 authored lines** across the implementation commits — well inside the ~400-line review budget, which is exactly why native assessment measured it `under_budget`.
- **The gate caught two real defects the writer missed**, and they are worth keeping: the span returned `status: "completed"`, a value the router already consumes (`_after_execute` routes `completed`/`degraded` into `tool_loop_head`), so an unwired span was pre-deciding the parent's routing; and it re-invented the `{tool, status, detail}` evidence shape instead of calling `make_evidence`. The same lesson as slice 1, one level down: **a component must return only what it owns.**
- **The worker's REDs were honest but weak**: `AttributeError` on the absent `_delegation_plan` for T3 and `KeyError: 'evidence'` for T4. Neither demonstrates the behaviour failing, only the seam being absent. It is recorded as such rather than dressed up.
- **Contract #8 is now enforced, not merely exposed**: `delegation.py` still only carries `memoria_scope`, but the span refuses a customer-scoped worker's `scope: "own"` memory read before execution (`delegation_memory_scope_refused`).
- **Slice 3 (T5 + T6 + T7 + T8) implemented** on `odd/panel-subagent-delegation-slice3` off `498e5346`: `2b819a77` (advertise the executable capability), `8b1cd0d8` (wire the span), `91dff2dd` (capability metadata test), `ebbd77d4` (cost accounting), corrected in `bcfdb71c`, then `0d58ff1c` (AT-14) and `39216c0f` (the cross-domain harness). Files: `agent/prompts/assistant_plan.md`, `app/chat/assistant/graph.py`, `app/chat/assistant/nodes.py`, `app/chat/assistant/state.py`, `openspec/specs/assistant-tools/spec.md` and four test files. **365 authored lines**, inside the ~400 budget.
- **The wiring decisions, recorded so they are not re-litigated:** the adapter `delegation_node()` resolves the scope from `plan.sub_agent` at the LangGraph boundary and keeps the standalone span signature intact; the route is an unconditional edge `delegation_span → respond_stream`, so the responder answers and cites from the gathered evidence; the whole span advances `tool_steps` by exactly one (D6) and `delegate_unavailable` disappears entirely, leaving `delegate_refused` as the only terminal delegation decision; `delegation` is declared in `AssistantState` while the dead `ASSISTANT_STATE_KEYS` was deliberately left alone.
- **Third gate catch, same family as the first two**: the first pass left `PANEL_DELEGATION_UNAVAILABLE` behind as a constant with zero references, now asserting the opposite of the truth ("Delegation is not available yet."), and reported the capability as `implemented` from a bare declaration instead of from the span being resolvable. Both fixed in `bcfdb71c`, the latter pinned by a declared-but-inert-worker test.
- **Catalog invariance was NOT actually pinned before this slice.** The unit doc's D7 note claimed "a test pins this"; slice 1 only checked catalog *contents*. The byte-level pin now exists (`test_panel_planner_catalog_matches_pre_delegation_bytes`, a serialized-catalog SHA-256) — but as a literal hash it fails opaquely, so a future legitimate tool addition will need the hash recomputed rather than showing a diff. Recorded as a maintainability note, not fixed here.
- **Slice 3's REDs were mixed and are recorded as such**: T5's route and prompt failures were genuinely behavioural; T6's was `assert 0 == 1`; T7's and T8's were not — the spec simply did not exist, and the harness's first failure was the writer's own expectation mismatch (the real tools expose the customer id, not the customer name), disclosed rather than dressed up.

## Next step

**The unit is complete.** All eight tasks are implemented and all three slices are merged, including PR #364 (`fae7e0a9`), which carries the unit's only native review receipt. Post-merge housekeeping remains: graph refresh at close, and the Rapsodia cleanup gap (the worktree's test DB container is not removed by `rapso worktree cleanup`; run `docker compose -p lumat-test-<worktree-basename> -f infra/docker-compose.yml --profile test down -v` by hand).

**Open after U3:** `R3-001` (unit follow-up #4), the sibling unit for per-customer drill-down reads, the duplicated `*.list` tool names and the catalog schema trim.
