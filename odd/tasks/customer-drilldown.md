# ODD: customer-drilldown

**Branch (slice 1, merged and cleaned)**: `odd/customer-drilldown`
**Worktree (slice 1, cleaned)**: `/home/stefan/repos/lumat-agent-odd-customer-drilldown`
**Base (slice 1)**: `2a85b675` (= `main` at branch time, merge of PR #370 `odd/agenda-visit-dialog`)
**Branch (slice 2, live)**: `odd/customer-drilldown-chain`
**Worktree (slice 2, live)**: `/home/stefan/repos/lumat-agent-odd-customer-drilldown-chain`
**Base (slice 2)**: `120d34b9` (= `main`, merge of PR #371 `odd/customer-drilldown`)
**Status**: slice 1 delivered as **PR #371** (`odd/customer-drilldown` → `main`), CI green. Slice 2 delivered as **PR #372** (`odd/customer-drilldown-chain` → `main`), CI green; the merge is the owner's decision.
**Origin**: follow-up **#1** of `odd/tasks/panel-subagent-delegation.md` — the sibling unit for per-customer
drill-down reads. Owner scope decision taken 2026-09-26 (see *Decision*).

## Objective

Let the panel assistant answer a question about **one specific customer** — their cases (including closed
ones) and their visits (including past ones) — instead of only being able to correlate global lists.

## Problem — measured, not inferred

Verified on the branch base `2a85b675`, not from memory (the readings were taken at `3c179b5a`; PR #370
between them touched only `web/` and its own agenda record):

| Claim | Evidence |
|---|---|
| No per-customer read exists in the assistant registry | `customers.search`/`.list` take `query`+`limit` (`registry.py:50-53`); `conversations.*` the same (`:56-59`); `cases.list` takes `limit` only (`:71-73`); there is no `customers.get`/by-id tool |
| Cases cannot be read per customer | `_open_cases` calls `cases.list_open_cases` (`registry.py:268-269`), open-only via `case_is_open_expr()` (`services/cases.py:36-39`); no by-customer function exists in `app/services/cases.py` |
| Visits cannot be read per customer through the registry | `appointments.upcoming` is pinned to a fixed 30-day window (`registry.py:262-265`); but `scheduling.list_for_customer(session, customer_id)` **already exists** (`services/scheduling.py:137-139`) |
| A full ficha aggregate exists but is unusable raw | `customer_history(session, customer_id)` (`services/customers.py:224-319`) returns **unbounded** conversations, cases, messages (full `text` and `media_url`) and appointments — a panel view, far past the 4,000-char evidence budget |
| The worker's span is capped at 2 steps | `DELEGATION_SPAN_MAX_STEPS = 2` (`nodes.py:41`); the loop runs `while steps < cap` (`nodes.py:526`) |
| A worker-only tool is impossible | `tests/unit/test_agent_registry.py:285`: `assert set(reg.assistant.tools_whitelist) == set(TOOL_REGISTRY)` |
| The planner catalog is pinned by a literal hash | `tests/unit/test_assistant_delegation.py:31-43` — SHA-256 of `_planner_tool_catalog(config.tools_whitelist)`, which serializes name+description+args schema for every whitelisted tool (`nodes.py:484-492`) |
| Internal notes are staff-only and live apart | `customer_notes` table (`models.py:371-380`), deliberately kept out of the `customers` row (CR-4) |

## Decision

**Owner-confirmed scope (2026-09-26), option "operational + memo":** the drill-down exposes the customer's
cases (including closed) and appointments (including past). **No** phone/email/address/comuna, **no**
message text, **no** internal notes. The customer summary keeps coming from the existing `customer_memo`
via `memory.read` with `scope="customer"` (CR-7), which the worker already has.

Design consequences, each forced by a verified constraint or chosen with evidence:

- **One aggregate read, not two filters.** `DELEGATION_SPAN_MAX_STEPS = 2` leaves no room for
  `cases.list(customer)` **and** `appointments.upcoming(customer)` as separate calls. One tool that returns
  both lists fits the chain `customers.search → customers.operational_history` in exactly two steps.
- **A new tool is unavoidable, and it will be assistant-visible.** `set(assistant.tools_whitelist) ==
  set(TOOL_REGISTRY)` is asserted, so a worker-only tool cannot exist. The assistant gains the same
  capability; that is accepted, not hidden.
- **The tool takes `customer_id`, not a name.** No hidden resolution: `customers.search` already resolves a
  customer, and guessing between two matched people would be a correctness and privacy defect. The cost is
  that the chain uses both available steps.
- **Explicit projection, never `_plain` over ORM.** `_plain` maps **every** column of an ORM row
  (`registry.py:243-244`), which is how the existing handlers expose more than they name. This handler
  returns plain dicts with only the agreed fields.
- **No persona or planner-prompt change.** The worker's tools are injected into its planning prompt as a
  catalog keyed off `scope.tools_whitelist` (`_planner_tool_catalog`), so a new whitelist entry advertises
  itself. `agent/prompts/assistant_plan.md` does not enumerate tools.

### The tool

**`customers.operational_history`** — `read_only=True`.

- Args: `customer_id: int` (required, `> 0`); `limit: int` (default 10, `1..MAX_ITEMS`), applied per list.
- Returns exactly:
  - `cases`: `id`, `service`, `priority`, `status`, `summary`, `created_at`, `closed_at`
  - `appointments`: `id`, `service`, `status`, `starts_at`, `ends_at`, `local_start`, `timezone`
- Never returned: any customer field (name, phone, email, address, comuna, consent), any message content or
  `media_url`, any `customer_notes` row, any internal linkage column.

## Scope

### In scope

| File | Change |
|---|---|
| `app/services/cases.py` | `list_cases_for_customer(session, customer_id, limit)` — all statuses, including closed |
| `app/chat/assistant/tools/registry.py` | `OperationalHistoryArgs` + `_operational_history` handler + the `TOOL_REGISTRY` entry |
| `agent/registry.yaml` | the tool in the assistant whitelist and in the `customer_records` worker whitelist |
| `openspec/specs/assistant-tools/spec.md` | requirement `AT-15` with refutable scenarios |
| `tests/unit/test_assistant_tools.py` | args validation, the projection, the bound, the service seam |
| `tests/unit/test_assistant_delegation.py` | recompute the pinned catalog hash; the two-step chain fits the span cap |
| `tests/integration/test_assistant_harness_guardrails.py` | a real per-customer delegated turn |
| `odd/tasks/customer-drilldown.md` | this document |

### Out of scope

- Message text, contact/PII fields, internal notes — excluded by the owner's decision.
- **A pre-existing exposure found while scoping, deliberately not fixed here**: `customers.search` returns
  ORM `Customer` rows, and `_plain` maps every column, so the assistant already receives `phone_e164`,
  `email`, `address`, `comuna` and `consent_status` today. Recorded as a follow-up; changing it alters
  existing assistant behaviour and touches a file another actor is editing.
- The concurrent actor's unit (`odd/client-ficha-case-surface`, worktree `..-odd-client-ficha-case-surface`)
  also edits `app/services/cases.py` and `app/services/customers.py`; a rebase conflict on `cases.py` is
  possible and expected.
- Raising any bound: `_TOOL_EVIDENCE_LIMIT`, `MAX_ITEMS`, `MAX_ASSISTANT_TOOL_STEPS`,
  `DELEGATION_SPAN_MAX_STEPS` are all untouched.
- Tool-catalog cost hygiene; deep research; the duplicated `*.list` tool names.

## Delivery

Authored: service function + args + handler + registry entries + whitelists ≈ 120; spec ≈ 35; tests ≈ 200;
this record ≈ 130. **≈ 485 lines — above the ~400 review budget.**

**Strategy: chained PRs, `stacked-to-main`** (owner-confirmed 2026-09-26). Each slice merges to `main` in
order, and the next slice rebases onto the new `main` before its own PR.

| Slice | Content | Files |
|---|---|---|
| 1 | The read capability: the by-customer cases query, the tool, the whitelists, the unit tests, the recomputed catalog hash, this record | `app/services/cases.py`, `app/chat/assistant/tools/registry.py`, `agent/registry.yaml`, `tests/unit/test_assistant_tools.py`, `tests/unit/test_assistant_delegation.py`, `odd/tasks/customer-drilldown.md` |
| 2 | The delegated chain end to end: `AT-15`, the two-step chain test and the integration harness | `openspec/specs/assistant-tools/spec.md`, `tests/unit/test_assistant_delegation.py`, `tests/integration/test_assistant_harness_guardrails.py`, this record (updated) |

## Constraints

- **Strict TDD: ON** (`openspec/config.yaml:38`), runner `uv run pytest tests/`.
- One concern per commit, ≤5 files, Conventional Commits, **no `Co-Authored-By` and no AI attribution**.
- English artifacts. No test reaches the network.
- Bounds are bounds.

## Graph nodes consulted (Graph Check, Step 1)

- `graphify query "panel assistant delegated worker per-customer drill-down reads appointments cases conversations customer detail tool registry whitelist"` → `app/models.py:218` `Customer`, `:334` `Case`, `app/services/dashboard.py:225` `drilldown()`, `registry.py` `execute_tool`, `agent_registry.py` `Registry`, `test_delegated_customer_gathering_answers_with_cross_domain_evidence()`.
- Parent Graph Check: `graphify query "assistant delegation node worker span two step chain customers.search operational_history tool execution execute_tool planner"` → `execute_tool()` (`app/chat/assistant/tools/registry.py:546`), `resolve_delegation_scope()` (`delegation.py:22`), `DelegationScopeError` (`delegation.py:10`), `DelegationScope` (`delegation.py:15`), `plan()` (`nodes.py:223`), `_after_guardrails()` (`graph.py:76`), `run_assistant()` (`graph.py:172`), `get_tool()` (`registry.py:535`); communities `tests/unit/test_assistant_delegation.py` and `tests/integration/test_assistant_harness_guardrails.py`.
- A narrow read-only mapper produced the initial map; every decisive line above was re-verified by the
  orchestrator against the working tree.

## Progress

- **Slice 1 implemented** (`e248c036`): `list_cases_for_customer` in `app/services/cases.py`; `OperationalHistoryArgs`
  + `_operational_history` + the `TOOL_REGISTRY` entry in `registry.py`; the tool added to both whitelists in
  `agent/registry.yaml`; unit tests for args validation, the projection and its forbidden set, the bound, and
  the service seams. Strict TDD: the observed RED was
  `ToolValidationError: unknown assistant tool: customers.operational_history`.
- Planner catalog hash recomputed: `27bbace8…` → `e522ed87…` (recorded in the commit body).
- Verification: focused `151 passed` exit 0; full suite **`1484 passed`, exit 0** (320s). Parent spot check
  re-ran `test_assistant_tools.py` + `test_assistant_delegation.py` + `test_agent_registry.py`: exit 0.
- Native assessment of this range: `risk: medium` (`configuration_change`), 233 lines, 6 paths,
  **`review_due: false`** (`under_budget`). No review started.
- Noted, not fixed: the unit test's rows are `SimpleNamespace` stubs, so they cannot prove the real ORM field
  names; slice 2's integration harness runs the handler against the real database and closes that gap.
- **Slice 2 implemented** on `odd/customer-drilldown-chain`: appended AT-15 with closed/past inclusion,
  per-list and evidence bounds, private-data exclusions, and explicit error-state scenarios; added a real
  two-step delegation-cap test and a real-database `run_assistant` integration test for ORM fields and the
  forbidden projection. No production code or bounds changed.
- Strict TDD evidence: T2 initially failed at its final assertion because its recorded planner state kept
  the loop's subsequently-mutated result list (observed `Left contains one more item: ...customers.operational_history`);
  the test now records a list snapshot and passes. This was a test-observation defect, not a production RED.
  T3 passed on its first run (`1 passed, 33 deselected`), so it is explicitly a no-RED characterization/
  verification test; no failure was manufactured.
- Slice 2 focused verification: delegation `23 passed`; integration harness `34 passed`; tools + registry
  `94 passed`. Full suite: **`1486 passed`, exit 0** (234.18s), a measured delta of **+2 tests** from the
  slice-1 baseline of 1484. The full run reported two warnings: an unawaited `_publish_all` coroutine and
  the existing fastembed pooling advisory.
- Graph nodes/edges consulted for slice 2: `delegation_span()` calls `_delegation_plan()` with accumulated
  `tool_results`; `delegation_node()` calls the span with guardrail-validated scope; `run_assistant()` runs
  the real graph; `_after_guardrails()` routes delegated plans to the span; `execute_tool()` dispatches the
  scoped tools. The corresponding unit and integration test communities were consulted.
- Native assessment of the slice-2 range: `risk: medium` (`executable_change`, the spec path), **260 lines**,
  4 paths, **`review_due: false`** (`under_budget`). No review started — the same verdict as slice 1.
- Parent readback after the writer returned: 4 paths changed (spec, unit test, integration test, this record),
  commits `7e070ebe` · `f060ff70` · `f1b15dde` · `a0cbc6ba` · `88e8ac50`; `uv.lock` untouched at every commit.
  The header now names both the cleaned slice-1 branch/worktree and the live slice-2 ones.
- Parent spot check re-ran the delegation unit suite and the integration harness together: **`57 passed`, exit 0**.

## Next step

Slice 2 is delivered as **PR #372** (`odd/customer-drilldown-chain` → `main`), CI green and labelled
`type:chore` (spec + tests, no production behaviour change). The **merge is the owner's decision**; nothing
else is pending on this unit. Under `stacked-to-main`, once #372 merges the unit is closed and the branch and
its worktree can be cleaned up.
