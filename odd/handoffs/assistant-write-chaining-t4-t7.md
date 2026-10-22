# HANDOFF — assistant-write-chaining, continue with T4, T5, T6 and T7

**Feature**: `odd/tasks/assistant-write-chaining.md` (Unit 1 — approved writes chain inside the panel loop).
**Worktree**: `/home/stefan/repos/lumat-agent-odd-assistant-write-chaining` · **branch**: `odd/assistant-write-chaining-t4` (empty, cut from `main` = `a9860e11`, upstream unset on purpose — rename it per slice if you start with a different task).
**Status**: T1 ✔ merged (#631) · T2 ✔ merged (#633) · T3 ✔ merged (#637). **T4, T5, T6 and T7 are next** — four slices, each its own chained PR.

## T4 — rejecting mid-chain aborts cleanly, with an audit record (S5)

**Goal**: rejecting any write stops the chain with no further steps dispatched, records the rejection, and leaves **no dangling approval or pending run**.

**Where to look (read the code, do not assume)**:
- `app/services/agent_chat.py` → `approve_plan(..., reject=True)`: today it marks the message `rejected`, audits only the `skill.propose` case, and **returns early without settling the thread state**. So a chain rejected at step 2 leaves `stage="approval_pending"` and `execution_status="pending"` behind. That is the T2 verifier's first advisory, and it is the same shape the baseline had for a single-write reject.
- `app/panel/api/routes/chat.py` → the `stop` route (~L437-466) is the existing model for settling an `approval_pending` thread at a safe boundary: it revokes the pending approval, sets `stage`/`execution_status`/`live`, and appends a status event. Decide whether T4 settles a rejection the same way or records a distinct terminal rejected state — and keep the panel's approval card consistent.
- Audit: `record_audit(...)` in `app/services/audit.py`; the write path already audits `internal_chat.execution` and `internal_chat.execution_rejected`.

**Acceptance (S5)**: a functional test rejects at step N, asserts no later action ran and the thread is terminal, and that the rejection is recorded.

**Constraints**:
- Rejecting must still never execute the write (that already holds — pin it).
- Do not touch the approval binding or the chaining rules; T2 settled those.
- Class B never asks for approval, so there is nothing to reject there.

**Ordering**: T4 comes before T7 — T7 closes the feature's tests and docs, and it should not describe a chain that cannot reject cleanly.

## Where things stand (T1–T3, all merged and verified)

**T1** — the approval path re-enters the assistant graph (`run_assistant(resume_plan=…, resume_approval=…)`) instead of calling the bare `execute` node; a tool-less `legacy_compat` plan keeps `execute`.

**T2** — the chain itself:
- `app/chat/assistant/nodes.py` → `tool_loop_head` no longer ends the turn on a write: any step that opted into `follow_up` continues, and it **clears the spent `approval`** on continuation. The cap (`MAX_ASSISTANT_TOOL_STEPS = 2`) still ends the chain and records `cap_reached`.
- `app/chat/assistant/nodes.py` → `guardrails` replaced the `loop_write_refused` refusal with: a class-A write proceeds only with a consumed approval matching **that exact** plan (`validate_execution`), otherwise it issues a **fresh** approval — at any step. `PANEL_LOOP_WRITE_REFUSAL` and its decision are gone.
- `app/chat/assistant/graph.py` + `app/services/agent_chat.py` → the chain state survives the pause: `run_assistant` seeds `resume_tool_results`/`resume_tool_steps`; `_run_approved_plan` passes them; `_persist_resumed_result` writes the fresh approval (**assigned *after* the merge**), the new `current_plan` the next approval binds to, and `tool_results`/`tool_steps`/`cap_reached`; `_park_chain_on_next_approval` leaves the operator message pending with plan/approval events continuing the sequence.

**T3** — regression pins for S4 (read-only loop + single-write path), proven to bite by a mutation check.

**Verification so far**: independent verifier on T2 (`7c80b456..cb2cf13d`): no blockers; S1–S4 MET, S7 PARTIAL (the cap raise is T6). Its 9 probes are committed as `tests/integration/test_assistant_write_chain_verifier_probes.py`.

**Merge commits on main**: `7c80b456` (#631), `2514d9dc` (#633), `a9860e11` (#637).

## Environment bootstrap (already in place in this worktree)

```bash
cd /home/stefan/repos/lumat-agent-odd-assistant-write-chaining
ln -s /home/stefan/repos/lumat-agent/.venv .venv     # already present, gitignored
cp ../lumat-agent/infra/.env infra/.env              # already present, gitignored
PYTHON=/home/stefan/repos/lumat-agent/.venv/bin/python infra/test-db.sh up
eval "$(PYTHON=/home/stefan/repos/lumat-agent/.venv/bin/python infra/test-db.sh env)"
/home/stefan/repos/lumat-agent/.venv/bin/python -m pytest -q
```

Test DB port is **6188** (derived from the worktree directory name in `tests/_testdb.py`). The `web/node_modules` symlink to the main repo is already there for the panel checks.

## T5 — recovery is exactly-once per approved write (S6)

**Goal**: an interrupted chain that is resumed or reclaimed re-enters at the correct pending step and **never re-runs an already-consumed write**.

**Where to look (read the code, do not assume)**:
- `app/chat/assistant/recovery.py` → `claim_execution` is the atomic gate: it flips `execution_status` from `'pending'` to `'running'` in one `UPDATE ... WHERE assistant_state #>> '{execution_status}' = 'pending'`, so a second claimer loses. `recover_events` de-duplicates the persisted stream by `(run_id, sequence, type, task_id, tool)`.
- `app/services/agent_chat.py` → `resume_thread` (requires `stage == "executing"`, then claims) and `approve_plan` (claims after consuming the token); `_persist_resumed_result` / `_park_chain_on_next_approval` decide the post-resume state; `reap_stale_run` and `reap_orphaned_runs` (boot) fail closed on a run nothing can own, and both **skip** `stage == "executing"` with `execution_status == "pending"` as resumable.
- The approval side is what makes a repeat impossible: `consume_approval` requires `status == "pending"` and `validate_execution` requires `status == "consumed"` **and** a matching `arguments_sha256`.

**The reasoning to verify, not assume**: a crash *after* the write executed but *before* the state was persisted leaves `execution_status == "running"`, so `resume_thread`'s claim fails and the reaper fails the run — the write is **not** re-executed (fail closed). Confirm that end to end and pin it.

**Acceptance (S6)**: a recovery test simulates an interrupted chain and asserts exactly-once execution per approved write.

**Do not duplicate** (already covered — extend instead): `test_s6_parked_chain_survives_restart_and_second_approval` (in the verifier probes), `test_resume_responder_failure_degrades_without_rolling_back_the_write`, `test_tool_less_approval_keeps_the_single_node_execution_path`.

## T6 — the loop stays bounded and cost-gated (S7)

**Goal**: the chain is capped by an explicit iteration limit and stops when the per-turn cost gate blocks; the cap is **raised from today's `MAX_ASSISTANT_TOOL_STEPS = 2` to a value that fits a 3-step chain** (doc assumption A1 proposes 4, pending cost measurement).

**Where**: `app/chat/assistant/nodes.py:42` (`MAX_ASSISTANT_TOOL_STEPS`), `tool_loop_head` (the cap branch and the `loop_cost_stopped` branch), and the doc's A1.

**Careful — this is not a one-line bump**:
- Since T2, `tool_steps` is **cumulative across the approval pause**, so the cap now bounds the whole chain, not a single pass. Raising it to 4 means a chain can carry 4 writes through 4 approvals.
- It widens the **read-only** loop too, which is what the cap originally bounded.
- Pins that hardcode the old value must be updated **deliberately**: `test_graph_runs_step_two_class_b_write_in_loop` (asserts `tool_steps == 2`), `test_cap_refuses_a_third_execution`, `test_sessionless_normal_cost_mode_keeps_two_step_chain`. `test_s7_cap_bounds_chain_across_pause` and `test_write_chain_stops_at_the_iteration_cap` read the constant, so they follow.
- Measure the cost first (A1 says the raise is pending cost measurement); if the cost gate blocks typical chains, revisit.

**Acceptance (S7)**: a test asserts the cap terminates a runaway chain and that a blocked cost mode ends the turn; a 3-step chain completes.

## T7 — tests extended + docs/help updated (all specs)

**Goal**: extend `tests/unit/test_assistant_tool_loop.py`, `tests/integration/test_assistant_chat.py` and `tests/integration/test_assistant_harness_guardrails.py` for the chain, and update the docs/help that describe the loop.

**Also owns the panel-timeline advisory** (the T2 verifier's second one): when a resume pauses again, `_park_chain_on_next_approval` (`app/services/agent_chat.py`) appends only the plan/approval events, so the **earlier steps' `tool`/`evidence` events never reach the stream**. A chain shares one run id, so sequences must keep climbing (that is why `_events_for` takes a `sequence` offset). Decide whether a chain should emit its completed steps, and pin the decision. Consumer: `web/src/components/pages/AgentChat.tsx` (reads `assistant_state.approval` and the `approval` event).

## Feature end — independent verifier

The doc's task list ends with "independent verifier at the feature end (high-risk change)". Once T5–T7 (and T4, if taken) are in, run one verifier over the **whole feature** (every S1–S7), not one per slice, and judge the S# verdicts. High risk: approval, recovery, audit.

## Route and discipline

- Parent implements **inline** on the branch; no writer trigger reason. Each slice that touches approval/recovery/audit is **high risk** → independent verifier at the end of that slice.
- Test-first: one RED per rule, through `approve_plan`/`resume_thread` and the graph. T3 documented the exception: for pure regression pins there is no runnable RED, and a **mutation check** is what proves the pin bites.
- Work-unit commit (`feat(...)`/`test(...)`), then a `docs(odd)` commit recording the id. Update the Engram mirror (`odd/assistant-write-chaining/tasks`) and the progress topic.
- Delivery is **`chained`** (owner decision): one PR per slice. T1 = #631, T2 = #633, T3 = #637.
- Graph Check before editing (`graphify query "<area>"`; the graph lives in `/home/stefan/repos/lumat-agent/graphify-out/`).
- Close every code change with a `Risk:` line. Push/PR are the owner's call; the owner merges.
- Cleanup convention: the repo **deletes** `odd/*` branches when the PR merges (do it local + remote), and the worktree is left on an empty branch cut from the updated `main`.

## Resume pointers

- Engram: `odd/assistant-write-chaining/tasks` (doc mirror, #6661), `odd/assistant-write-chaining/progress` (T2 detail, #6666), the T3 note (#6679), the merge/cleanup note (#6673), and the session summaries (#6667, #6680).
- Read `odd/tasks/assistant-write-chaining.md` **in full** (specs S1–S7, tasks T1–T7, Log) before continuing — it carries the owner decisions and the advisories.
- Previous handoff: `assistant-write-chaining-t2.md` (T2 detail).
