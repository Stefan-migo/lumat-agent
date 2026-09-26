# ODD: customers-search-pii

**Branch**: `odd/customers-search-pii`
**Worktree**: `/home/stefan/repos/lumat-agent-odd-customers-search-pii`
**Base**: `2a5c53dd` (= `main` = `origin/main` at branch time, PR #378)
**Status**: merged — PR #382 (`50bce481`, 2026-09-26). Worktree and test DB torn down.

## Objective

Stop `customers.search` and `customers.list` from sending customer contact and consent PII to the
assistant. Today both tools return raw ORM `Customer` rows, and `_plain` serializes **every** mapped
column, so the assistant receives `phone_e164`, `email`, `address`, `comuna`, `consent_status` and
`consent_at`. Project the search output to an explicit allowlist: **`id`, `name`, `state`**.

## Problem (verified)

- `TOOL_REGISTRY` registers both `customers.search` and `customers.list` on the **same** handler
  `_search_customers` (`app/chat/assistant/tools/registry.py:540-541`), which returns
  `customers.search_customers(...)` → `list[Customer]` ORM rows (`:256-257`).
- The generic dispatch applies `_plain` (`:659`), and `_plain`'s ORM branch serializes **all** columns
  (`:249-250`): `{column.name: _plain(getattr(value, column.name)) for column in value.__table__.columns}`.
- Result payload today: `{"tool":"customers.search","status":"completed","read_only":true,"result":[{…all
  Customer columns…}]}` — including `phone_e164`, `email`, `address`, `comuna`, `consent_status`, `consent_at`.
- The spec has **no** requirement about `customers.search` output fields. `AT-15`
  (`openspec/specs/assistant-tools/spec.md:329-346`) already forbids exactly those fields for the sibling
  tool `customers.operational_history`. This change extends the same boundary to the search tools.

## Decision (owner, 2026-09-26)

`customers.search` / `customers.list` return **`id`, `name`, `state`** only. Contact/consent/location PII
(`phone_e164`, `email`, `address`, `comuna`, `consent_status`, `consent_at`) is removed. `archived_at` and
`created_at` are dropped; `state` carries the archived distinction.

## Constraints (verified — do not violate)

- **Do NOT change the shared service** `customers.search_customers` (`app/services/customers.py:210-236`):
  the panel API calls it (`app/panel/api/routes/clients.py:106`). Project at the assistant handler only.
- **Do NOT narrow `_plain` globally**: it is shared (`registry.py` call sites 643, 645, 647, 653, 659) and
  narrowing it would change other tools. The fix projects in `_search_customers`, mirroring the existing
  pattern in `_operational_history` (`:288-289`, explicit field tuples).
- **Do NOT touch the argument schema, description, or catalog membership**: `_planner_tool_catalog`
  (`app/chat/assistant/nodes.py:484-492`) hashes name + description + arg schema. Output-shape changes do
  **not** move the pinned hash (`tests/unit/test_assistant_delegation.py:32-44`). Confirmed in code.
- **Bounds are bounds**: do not change `_TOOL_EVIDENCE_LIMIT`, `MAX_ASSISTANT_TOOL_STEPS`,
  `DELEGATION_SPAN_MAX_STEPS`, `MAX_ITEMS`. If a test shows they are insufficient, that is a finding for
  the owner, not a silent change.
- `uv run` rewrites `uv.lock`: run `git checkout -- uv.lock` before **every** commit.
- `pytest -q` never prints the final summary line in this repo: count progress marks and read the exit code.

## Test database

The worktree's derived test port collided with another actor (`clients-crud` also derives 5702). Use the
override:

```bash
export TEST_DB_PORT=5750
eval "$(bash infra/test-db.sh env)"   # DATABASE_URL=postgresql+psycopg://app:app@localhost:5750/lumat
```

## Strict TDD (ACTIVE)

`openspec/config.yaml` sets `strict_tdd: true`. Runner: `uv run pytest tests/`. You MUST observe RED
before the fix, then GREEN. Never invent evidence.

## Tasks

- [x] **T1 — RED.** Write a failing test that proves the current exposure. Two layers, because this repo
      already learned (PR #372) that `SimpleNamespace` stubs cannot prove real ORM field names exist:
      1. a unit test in `tests/unit/test_assistant_tools.py` (mirror the `customers.operational_history`
         key test at `:61-105`) asserting `customers.search`/`customers.list` result keys ==
         `{"id","name","state"}` and that no PII key is present;
      2. a real-database assertion in `tests/integration/test_assistant_harness_guardrails.py` (mirror the
         anti-PII projection at `:783-921`) proving the serialized search payload omits `phone_e164`,
         `email`, `address`, `comuna`, `consent_status`, `consent_at` while still returning the customer.
      Record the RED output verbatim.
- [x] **T2 — GREEN.** Project `_search_customers` (`registry.py`) to the `id`, `name`, `state` allowlist,
      using the `_operational_history` pattern. It must cover **both** `customers.search` and
      `customers.list`. Re-run the RED tests: green.
- [x] **T3 — Regression guard.** Prove other tools' output is unchanged: the `_plain` call sites for
      `project.*`, `memory.*` and the generic path still behave identically. Prove `customers.search` can
      still find by name and by phone digits (matching is server-side and must keep working) while not
      returning the phone.
- [x] **T4 — Verify.** Targeted suites, then the full suite. `git checkout -- uv.lock` before every commit.
- [x] **T5 — Commit (Conventional Commits, no `Co-Authored-By`), RDD assess.** Push/PR/merge remain the
      owner's decision.

## Acceptance criteria

1. `customers.search` and `customers.list` return only `id`, `name`, `state` per row.
2. No PII field (`phone_e164`, `email`, `address`, `comuna`, `consent_status`, `consent_at`) appears in
   either tool's result, proven against the **real database**, not only stubs.
3. Search still matches by name and by phone digits; `limit` still bounds the result.
4. No other tool's output changes; the pinned catalog hash and the whitelist assertion stay green.
5. The shared service, the panel API, `_plain`, the arg schemas and the bounds are untouched.
6. English artifacts; Conventional Commits; no `Co-Authored-By`, no AI attribution.

## Verification

```bash
export TEST_DB_PORT=5750
eval "$(bash infra/test-db.sh env)"
uv run pytest tests/unit/test_assistant_tools.py tests/unit/test_assistant_delegation.py tests/unit/test_agent_registry.py
uv run pytest tests/integration/test_assistant_harness_guardrails.py
uv run pytest tests/          # full suite
git status --short && git diff --check
```

## Progress

- 2026-09-26 — base verified at `2a5c53dd`; concurrency checked (`agenda-decision-hygiene`,
  `agenda-operator-technicians` do not touch the target files; PR #378 did not either). Worktree created
  with owner consent. Test port collision with `clients-crud` (both derived 5702) worked around with
  `TEST_DB_PORT=5750`.
- 2026-09-26 — decision recorded: return `id`, `name`, `state`.
- 2026-09-26 — T1 RED (verbatim):
  - Unit: `FF                                                                       [100%]`; `2 failed, 76 deselected in 0.67s`. Both parameter cases failed at `assert set(result[0]) == {"id", "name", "state"}`. The observed extra keys were `email`, `address`, `comuna`, `phone_e164`, `consent_status`, and `consent_at`.
  - Real DB: `1 failed, 34 deselected in 1.78s`. The actual serialized customer dictionary contained `phone_e164`, `email`, `comuna`, `address`, `consent_status`, `consent_at`, `archived_at`, and `created_at`, instead of only `id`, `name`, and `state`.
- 2026-09-26 — T2 GREEN: `_search_customers` now explicitly projects `id`, `name`, and enum/datetime-safe values, covering both registered tools. Focused tests: unit `2 passed, 76 deselected`; real DB integration `1 passed, 34 deselected`.
- 2026-09-26 — T3 regression evidence: real PostgreSQL test confirms name lookup, phone-digit lookup, and `limit=1`; existing project and memory behavior tests remained green. No schemas, catalog, shared service, `_plain`, or bounds changed.
- 2026-09-26 — T4 verification: targeted unit suites `119 passed`; guardrails integration `35 passed`; full `uv run pytest tests/` `1502 passed, 2 warnings in 252.61s (0:04:12)`.
- 2026-09-26 — Behavior commit: `280134f6` (`fix(assistant): limit customer search fields`).
- 2026-09-26 — Task record committed separately after implementation and verification.
- 2026-09-26 — Merged `origin/main` (`8e5a978a`, PR #380) into the branch: the update did not touch the
  target files; focused tests re-run green over the merged tree.
- 2026-09-26 — Opened **PR #382** against `main` (label `type:bug`, base `8e5a978a`).

## Next step

Delivered as **PR #382**. Native assess: `risk: medium` (`executable_change`), 196 changed lines / 4 paths,
`review_due: false` (`under_budget`). Merge is the owner's decision; CI (`tests.yml`) runs the backend and
panel jobs on the PR. Cleanup (worktree + test DB) follows the merge.
