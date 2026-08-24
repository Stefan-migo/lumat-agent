# Archive Report: h2-router-langgraph

**Change**: `2026-08-24-h2-router-langgraph`
**Project**: LumatAgent
**Status**: CLOSED
**Date**: 2026-08-24
**Agent**: sdd-archive (`sdd-archive` skill, delegate executor)
**Artifact store**: hybrid (openspec files on disk + engram persistence)
**Delivery**: merged to `main` (PRs 1+2+3 landed in `398aa1a6..ee379d9e`)

## Executive Summary

Closed the h2-router-langgraph change (H2 slice-1): realized the multi-agent architecture declared in AC-4 — a sibling `sub_agents:` roster in `registry.yaml` (5 sub-agents × 7 fields, `agent:` orchestrator block byte-identical), a read-only startup reader (`app/agent_registry.py`, fail-fast validation), an `orchestrate` node dispatching on a pure `(intent, flags)` table (AO-3), and a KB research/triage sub-graph (AO-5) that reuses existing `respond`/`handoff` nodes with a bounded ≤1 retry (AO-8) and KB scope filtering on `source_meta.category` (AO-7). Implementation is 100% (14/14 tasks, phases 1–3, PRs 1+2+3). Verification PASS WITH WARNINGS at verify time (11/11 requirements, 20/20 scenarios, full suite 497 passed); the single WARNING (hardcoded `context="intent=valores"` on the postventa KB-miss path, introduced by `7e6de4f7`) was RESOLVED after verify by commit `ee379d9e` (dynamic `context=f"intent={state.intent}"`). Final state: 497 tests passed post-fix, zero open CRITICAL / WARNING / SUGGESTION. Delta specs synced to main specs: `agent-config` AC-4 MODIFIED (merge), `agent-orchestration` created (AO-1..AO-10). Change folder moved to `openspec/changes/archive/2026-08-24-h2-router-langgraph/`.

## Final-State Authority

The following facts describe the change AT CLOSE (highest-ranked sources):

- **Native review authority (`reviewGate`)**: structurally ABSENT — receipt-driven development is NOT enabled for this candidate (no kill switch, no discovered review artifact). Archive proceeds under ordinary repository policy; zero review code ran and nothing to read or block on. Per the Native Review Receipt Gate, absence is not a defect to investigate.
- **Persisted tasks artifact** (`openspec/changes/archive/2026-08-24-h2-router-langgraph/tasks.md`): **14/14 implementation tasks marked `[x]`** (1.1–1.4, 2.1–2.6, 3.1–3.4), zero `[ ]` boxes. Task Completion Gate passed without reconciliation.
- **Explicit final-state facts (orchestrator launch prompt)** — forward the authoritative final counts:
  - **WARNING REMEDIATED**: the verify WARNING (`research_triage.py:110` hardcoded `context="intent=valores"` on the miss→handoff path, H2-introduced by `7e6de4f7`) was FIXED after verify by commit `ee379d9e` — `context=f"intent={state.intent}"` (dynamic). Confirmed in the working tree (line 110 shows the dynamic form). The verify-report's WARNING entry is RESOLVED; the archived verify-report.md carries an explicit note to this effect.
  - **Post-fix full suite re-run**: `.venv/bin/pytest tests/` → **497 passed** (after `ee379d9e`). Also `.venv/bin/pytest tests/functional/test_conversation_flows.py tests/integration/test_chat_capture.py tests/integration/test_chat_intent.py` → **27 passed**.
  - **All other verify findings**: none. Zero open CRITICAL / WARNING / SUGGESTION remains.
  - **Registry AC-4 invariant holds**: `agent:` block byte-identical across all H2 commits (verified by `git log`/`git show` per commit — no `prompts.py`/`respond.py` touched; the `agent:` top-level block is IN TACT with `sub_agents:` added as a sibling).
- **Verify-report** (observation `sdd/h2-router-langgraph/verify-report`, id 2005, created 2026-08-24 19:06:07): an intermediate snapshot. Its WARNING entry is superseded by the higher-ranked final-state facts above; its compliance matrix (11/11 requirements, 20/20 scenarios, all tests) remains valid and is archived for the audit trail.

Per Final-State Authority, no stale pending/blocked claims from `apply-progress`/`verify-report` are echoed as current facts. The verify-report's single WARNING is reported as RESOLVED at close, with the fix commit cited.

## Verification Summary (Final)

- Native validator: `gentle-ai sdd-verify-validate` at verify time → verdict **pass_with_warnings**, `blockers: 0`, `critical_findings: 0`.
- Requirements: **11/11 COMPLIANT** (AC-4 modified + AO-1..AO-10).
- Scenarios: **20/20 COMPLIANT**.
- Tests (final, post-remediation): **497 passed** full suite `.venv/bin/pytest tests/` (exit 0); focused subset `.venv/bin/pytest tests/functional/test_conversation_flows.py tests/integration/test_chat_capture.py tests/integration/test_chat_intent.py` → **27 passed**.
- Warnings: **None open at close** — the single verify WARNING (hardcoded log context) was fixed by `ee379d9e`. Commit `ee379d9e`'s diff is exactly the intended one-line change (research_triage.py:110, static→dynamic).
- CRITICAL: **None**.
- Design coherence: D1..D7 all followed (D1 sibling sub_agents; D2 reader outside prompts/respond; D3 enforcement at dispatch; D4 thin sub-graph; D5 assert-in-dispatch; D6 additive KB scope; D7 ≤1 retry).
- Out-of-scope enforced: no checkpointer, no panel endpoints, no new DB tables/migrations, no audit_log dispatch entries, no gate-envelope redesign, no cost-threshold change.
- TDD compliance: 6/6 checks passed.

## Per-Capability Delta Sync

| Capability | Status in main specs | Action | Requirements |
|------------|----------------------|--------|--------------|
| `agent-config` | Existed | **MODIFIED** AC-4 merged into `openspec/specs/agent-config/spec.md` (multi-agent roster + enforcement at orchestrator dispatch boundary; `(Previously:)` history note updated to reflect H2 shipped); Boundary updated to point at `agent-orchestration` | AC-4 updated; AC-1,2,3,5,6,7,8 preserved intact |
| `agent-orchestration` | Did not exist | **Created** `openspec/specs/agent-orchestration/spec.md` (delta `## ADDED Requirements` → main-spec `## Requirements`; AO-1..AO-10 + Boundary byte-identical) | AO-1..AO-10 |

- **`agent-config` AC-4 (MODIFIED)**: replaced the matching AC-4 requirement block in the live spec (multi-agent schema + dispatch-boundary enforcement) and resolved the stale "until H2 / enforcement deferred to H2" language — the `(Previously:)` note now states enforcement happens at the orchestrator dispatch boundary. Two scenarios (Declarative-one-orchestrator, Reader-lives-outside-prompts/respond) carried from the delta; all other AC-* requirements untouched (matches requirement-by-name merge).
- **`agent-orchestration` (ADDED)**: new capability main spec created from the delta with the standard main-spec header (`## Requirements`). `diff -r` against the delta confirmed byte-identity of every AO-1..AO-10 requirement and the Boundary; the only diff line is the intended header normalization.
- **Destructive-delta warning (repo rule `Warn before merging destructive deltas`)**: the AC-4 merge is a MODIFIED requirement (semantic scope change, not a removal or large-section deletion — no requirement/scenario removed, data-only stance preserved, AO-10 unchanged). Warned the orchestrator per the launch prompt instruction; the merge was explicitly directed by the orchestrator and is recorded here as intentional. No REMOVED/RENAMED deltas existed, so no further destructive action.

## Mechanical Copy Contract (readback evidence)

1. **Archive move** — pre-move recursive snapshot (`mktemp` snapshot root, `cp -R openspec/changes/h2-router-langgraph`) vs `openspec/changes/archive/2026-08-24-h2-router-langgraph/`: **EMPTY `diff -r`** (byte-identical), PASS. Source directory confirmed absent after the move.
2. **Spec sync (agent-orchestration)** — delta `openspec/changes/h2-router-langgraph/specs/agent-orchestration/spec.md` copied to temp, single header transform via `sed`, then `mv` to `openspec/specs/agent-orchestration/spec.md`; `diff -r` vs the delta shows exactly one intended line (`## ADDED Requirements` → `## Requirements`), all requirement content byte-identical.
3. **Spec sync (agent-config AC-4)** — genuine requirement-block replacement (MODIFIED merge) composed and applied; verified by `git diff` showing the AC-4 block and Boundary changed, all other AC-* requirements preserved.
4. `archive-report.md` and `verify-report.md` are additive-only (did not exist in the source snapshot) and excluded from the move comparison.

No file content passed through the model Read/Write path for byte-identical copy operations (`cp -R` / `mv` / `sed` / `git mv` were the mechanisms). `git` detects `tasks.md` as a rename (`R`) into the archive.

## Task Completion Gate

- Persisted tasks artifact inspected **before** spec sync / archive move: **14/14 `[x]`**, zero `[ ]` boxes. No stale unchecked implementation tasks. No orchestrator-approved reconciliation needed. The archived audit trail contains NO stale unchecked implementation tasks for completed work.

## Delivery State

- **Commits included (H2 merge to main, `398aa1a6..ee379d9e`)**: `ee379d9e` fix(router): dynamic intent in unresolved log context; `4181c47b` chore(graphify): refresh after PR 3; `f09fba0b` docs(sdd): mark tasks 3.1-3.4; `8ebf8ecf` docs(agent): H2 roster + slice-1 runtime README; `393d9f17` test(router): research miss/handoff + AO-9 tone; `3c7e2d1b` feat(registry): cache load_registry; `437dd54d` docs(sdd): mark tasks 2.1-2.6; `012bcdda` test(router): KB-retail fixtures; `7e6de4f7` feat(router): wire research_triage sub-graph; `34b1e6e1` feat(router): orchestrate node; `1254c634` feat(state): active_sub_agent + triage_retry; `cc3f220e` feat(kb): additive scope filter; `933bb3f9` chore(graphify): refresh after registry reader; `edd18692` feat(agent-registry): multi-agent roster + reader.
- Archive commit: `git mv` + spec sync + additive reports committed locally to `main` as the repo's archive convention (message style `docs(sdd): archive h2-router-langgraph + sync agent-config/agent-orchestration specs`). NOT pushed, no PR created (per orchestration — delivery gates run separately; RDD active).

## Graph Notes (cortex 5-Step Execution Gate, Step 1)

- Graph present and effectively fresh (built at `f09fba0b`; HEAD `4181c47b` at verify was a graphify-refresh-only commit — no code change, so the graph covers the H2 code). No refresh run this session (per cortex, update runs once per session close).
- Queries consulted: `graphify query "orchestrate"` (81 nodes), `graphify query "research_triage"` (153 nodes) + `graphify-out/GRAPH_REPORT.md` (3052 nodes, 6389 edges, 233 communities). Nodes/edges: orchestrate(), _dispatch(), is_tool_whitelisted(), research_triage.py, build_research_triage_subgraph(), _kb_check(), get_registry(), graph.py build_graph(), ConversationState, kb.retrieve, gates, agent_registry.py.

## Risks / Notes

- **No open CRITICAL / WARNING / SUGGESTION at close.** Status: **CLOSED** (no partial archive).
- The verify-report's WARNING is resolved by `ee379d9e`; a future reader must not treat the archived verify-report.md's WARNING as open (it carries an explicit archive note).
- Other four sub-agents (retrieval, customer_records, human_handoff, escalation) remain **data-only** this slice — no runtime behavior. Future H2 slices extend the roster to full runtime.
- No checkpointer, no panel endpoints, no new DB tables, no audit_log dispatch entries (out-of-scope enforced).
- Branch is ahead of `origin/main` by 15 commits; archive not pushed (delivery per orchestration).

## Engram Persistence

Archive report + final-state facts persisted to Engram observation `sdd/h2-router-langgraph/archive-report` (`mem_save`, capture_prompt=false, scope=project lumat-agent). Observation IDs read for traceability: proposal `sdd/h2-router-langgraph/proposal` (1957), spec (1959), tasks (1969), design (1967), apply-progress (1987), verify-report (2005).

## Audit Trail Note

The archived folder is immutable per archive policy — no future edits to `openspec/changes/archive/2026-08-24-h2-router-langgraph/`; further changes go through a new SDD change.
