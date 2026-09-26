# ODD: delegation-scope-guard

**Branch**: `odd/delegation-scope-guard`
**Worktree**: `/home/stefan/repos/lumat-agent-odd-delegation-scope-guard`
**Base**: `cf5f8171` (= `main` at branch time, `refactor/case-status-public-name`)
**Status**: implemented, verified, full suite green. Delivered as **PR #369** (`odd/delegation-scope-guard` → `main`). Merge is the owner's decision.
**Origin**: follow-up **#4** of `odd/tasks/panel-subagent-delegation.md` (`R3-001`), an advisory
`review-reliability` WARNING from the slice-3 native review of that unit; Engram handoff
`handoff/panel-subagent-delegation-r3-001` (#5054).

## Objective

Remove the window where a delegation could throw out of the turn instead of ending it. The panel's
delegation node must run on the read-only scope `guardrails` already validated, never re-resolve it.

## Problem — measured, not inferred

Verified on the branch base `cf5f8171` (read on this worktree), not from memory:

> Base note: the R3-001 handoff named `main = fae7e0a9`. `main` advanced to `cf5f8171` (PR #368,
> `refactor/case-status-public-name`) by branch time — another actor is working this repo concurrently.
> The branch is cut from that base and the full suite below was measured on it.

| Claim | Evidence |
|---|---|
| The node re-resolves the scope with no guard | `delegation_node` calls `resolve_delegation_scope(...)` bare (`app/chat/assistant/nodes.py:586`) |
| Guardrails already resolved the same scope | `guardrails` resolves inside a `try/except DelegationScopeError` (`nodes.py:693-708`) |
| The carried scope was **incomplete** | Guardrails stores only `{key, persona, tools_whitelist}` (`nodes.py:710`); `DelegationScope` has a fourth field, `memoria_scope` (`delegation.py:14-19`) |
| Re-resolving was how the node recovered the missing field | The span enforces `scope.memoria_scope` (`nodes.py:546-548`), which the carried projection dropped |
| The graph has no router after the delegation node | `builder.add_edge("delegation_span", "respond_stream")` is unconditional (`graph.py:163`); `delegation_span` has one inbound edge, from `_after_guardrails` (`graph.py:162`) |
| `delegate_refused` already terminates via the guardrails router | `_after_guardrails` maps it to `END` (`graph.py:84`) |

**The window**: guardrails resolves successfully and returns the `delegate` decision. Between that node
and the next, the registry or the persona file can stop resolving. The node resolves again, raises
`DelegationScopeError`, and the exception escapes the turn instead of producing the explicit refusal the
system already knows how to make. The review called it `inferential` and `introduced`, and declined to
block because the window is one in-turn step.

## Decision — thread the validated scope; do not route a new refusal

Owner-confirmed option, chosen with evidence, not by habit:

**The node consumes `state["delegation"]` instead of resolving again.** This *deletes* the window rather
than handling it, and it is the smaller change.

- **Rejected: add a conditional edge after `delegation_span` plus a router and a refusal consumer.** The
  edge is unconditional today and `delegate_refused` terminates only through `_after_guardrails`, which
  runs *before* the delegation node. Reusing it would mean a new router function, a new edge, and a new
  consumer for a window that the chosen option removes entirely.
- **Required complement**: completing the carried projection with `memoria_scope` is not optional. The
  projection dropped it, which is *why* the node re-resolved; consuming an incomplete scope would silently
  lose the worker's memory-scope enforcement (Contract #8 of the parent unit).
- **No new state key.** `ASSISTANT_STATE_KEYS` is pinned verbatim (`tests/unit/test_assistant_harness.py:14`),
  so the complete scope reuses the existing `delegation` key. `delegation_span` still overwrites that key
  with its run summary after the node consumes the scope — pre-existing behaviour, out of scope here.
- **Reachability of the removed failure, checked not assumed**: `delegation_span` has exactly one inbound
  edge, from `_after_guardrails`, which returns it only for the `delegate` decision — set in the same
  branch that writes the carried scope. The carried scope is therefore always present at the node.

This is the parent handoff's explicitly sanctioned smaller alternative ("borra la ventana en lugar de
manejarla"), and it is **a new change, not a re-run of the slice-3 review**.

## Scope

### In scope

| File | Change |
|---|---|
| `app/chat/assistant/nodes.py` | `delegation_node` consumes the carried scope; `guardrails` carries a complete one |
| `tests/unit/test_assistant_delegation.py` | three tests: the RED pair and the regression guard |
| `odd/tasks/delegation-scope-guard.md` | this document |

### Out of scope

- Re-running or reopening the slice-3 native review. This is its own change with its own review.
- The pre-existing reuse of the `delegation` state key by two different shapes.
- Any change to the delegation span, the registry, the router or `delegate_refused`.
- Per-customer drill-down reads, deep research, tool-catalog hygiene — separate lanes.

## Tasks (strict TDD — observed RED before the source change)

- [x] **T1 — RED.** `test_guardrails_carries_a_complete_scope_including_memory_scope` and
  `test_delegation_node_uses_the_guardrail_validated_scope_without_re_resolving`. Both failed for the
  right reason: the first on the missing `memoria_scope`, the second with `DelegationScopeError` escaping
  `nodes.py:586` — the exact R3-001 failure. **Done.**
- [x] **T2 — GREEN.** `delegation_node` reconstructs `DelegationScope(**state["delegation"])`; `guardrails`
  carries `memoria_scope`. **Done.**
- [x] **T3 — Regression guard.** `test_delegation_node_preserves_the_customer_memory_scope_from_carried_state`
  proves the carried scope still refuses a customer worker's `scope: "own"` read end to end. Recorded
  honestly: this test passed **before** the change too (the old path resolved a complete scope), so it is a
  guard for the new mechanism, not a RED-driven test.
- [x] **T4 — Regression.** Focused suites and the full suite green. **Done.**

## Acceptance criteria

1. The delegation node never calls `resolve_delegation_scope`; a resolver that breaks after guardrails
   cannot escape the turn.
2. The scope carried from guardrails is complete, `memoria_scope` included.
3. The span's memory-scope enforcement still holds through the carried scope.
4. No new state key, no new graph edge, no new router decision, no raised bound.

## Checks

```bash
cp ../lumat-agent/infra/.env infra/.env
uv sync
bash infra/test-db.sh up
eval "$(bash infra/test-db.sh env)"

uv run pytest tests/unit/test_assistant_delegation.py
uv run pytest tests/unit/test_agent_registry.py tests/unit/test_assistant_planner.py \
  tests/unit/test_assistant_tools.py tests/unit/test_assistant_config.py
uv run pytest tests/integration/test_assistant_harness_guardrails.py tests/integration/test_assistant_chat.py
uv run pytest tests/

git status --short
git diff --check
```

Measured on this branch: delegation suite `22 passed` · focused set `125 passed` · integration pair
`88 passed` · full suite **1479 passed, exit 0** (4m51s; baseline 1476 + 3 new tests). No linter,
formatter, typechecker, pre-commit or hooks exist. **The tests are the verification.**

## Constraints

- **Strict TDD: ON** (`openspec/config.yaml:38`), runner `uv run pytest tests/`.
- One concern per commit, ≤5 files, Conventional Commits, **no `Co-Authored-By` and no AI attribution**.
- English artifacts.
- No test reaches the network.
- Bounds are bounds; the evidence budget and the span cap are untouched.

## Graph nodes consulted (Graph Check, Step 1)

- `graphify query "assistant delegation node guardrails resolve_delegation_scope delegate_refused routing"` →
  `resolve_delegation_scope()` (`delegation.py:22`), `delegation_node()` (`nodes.py:582`),
  `guardrails()` (`nodes.py:683`), `DelegationScopeError` (`delegation.py:10`), `AssistantState`
  (`state.py:160`), `build_assistant_graph()` (`graph.py:117`), `test_assistant_delegation.py`,
  `test_assistant_harness_guardrails.py`.
- A narrow read-only mapper produced the initial map; every decisive line above was re-verified by the
  orchestrator against the working tree before the decision was made.

## Progress

- Decision made with `file:line` evidence; the incomplete projection `memoria_scope` gap was found during
  verification and is the reason the node re-resolved.
- T1 RED observed (two tests, both for the right reason) → T2 GREEN → T3/T4 green.
- Route: direct inline. The change is a two-site, already-understood edit in one production file plus its
  test; no research or unresolved design remained after the map. No durable task artifacts were required
  by ODD, but the repo's PR-bound units carry a task doc, so this one does.

## Next step

Delivered as **PR #369** (`odd/delegation-scope-guard` → `main`, one `type:bug` label). What remains is
the owner's merge decision. No native review is due for this range (`medium`, `under_budget`).
