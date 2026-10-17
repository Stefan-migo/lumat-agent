# assistant-write-chaining (Unit 1) — approved writes chain inside the panel loop

**Objective**: let the panel assistant complete a multi-step write chain inside one user turn, where every business write is human-approved before it runs and the bounded autonomous class runs without per-step approval.
**Branch**: `odd/assistant-write-chaining` (T1; cut from `main` = `97b63c00`, synced with `origin/main` = `bc36318c`, merged as PR #631) → `odd/assistant-write-chaining-t2` (T2; cut from `main` = `7c80b456`, merged as PR #633) → `odd/assistant-write-chaining-t3` (T3; cut from `main` = `2514d9dc`, merged as PR #637) → `odd/assistant-write-chaining-t4` (T4; cut from `main` = `a9860e11`, merged as PR #639) → `odd/assistant-write-chaining-t5` (T5; cut from `main` = `a32df55f`).
**Delivery strategy**: `chained` (owner decision, 2026-10-15). Slices: **PR #631** = T1; **PR #633** = T2; **PR #637** = T3; **PR #639** = T4; `odd/assistant-write-chaining-t5` = T5. The ≈350-line forecast was exceeded by T1 alone (619 authored lines), which is what triggered the chain.
**Test runner**: `pytest` (backend). Focused: `tests/unit/test_assistant_tool_loop.py`, `tests/integration/test_assistant_chat.py`, `tests/integration/test_assistant_harness_guardrails.py`.

## Specs

**S1 — A write chain completes across one user turn, with approvals interleaved.**
Authorized example: search a customer → reschedule an appointment → reply to the customer.
Acceptance: with a write-capable tool present, the assistant reaches the second and later steps in the same turn instead of stopping after the first write; the final response reflects the whole chain.
Check: functional test drives a two-write chain through the graph and asserts both effects were dispatched in order.

**S2 — Every business write (class A) is human-approved before it executes.**
Acceptance: a class-A write never executes without a matching, unconsumed approval; the approval is issued with the plan's real arguments the human can see at that step.
Check: a chain pauses at each class-A write with `status: approval_pending`; execution happens only after `approve_plan` validates the token.

**S3 — The bounded autonomous class (class B) runs in-loop without per-step approval, and is exactly today's list.**
Acceptance: class-B tools execute inside the chain with no approval prompt; the class-B set is unchanged from `AUTONOMOUS_WRITE_ALLOWLIST`; new operational writes are never added to it implicitly.
Check: a chain using only class-B writes completes with zero approval prompts; a test pins the class-B membership.

**S4 — Read-only chaining and the single-write approval path do not regress.**
Acceptance: the existing read-only loop and the existing one-write-one-approval turn behave exactly as before.
Check: the existing `test_assistant_tool_loop` suite stays green; the single-write approval test is unchanged and passes.

**S5 — Rejecting an approval aborts the chain cleanly.**
Acceptance: rejecting any write stops the chain with no further steps dispatched, records the rejection, and leaves no dangling approval or pending run.
Check: functional test rejects at step N and asserts no later action ran and the thread is terminal.

**S6 — Recovery never double-executes an approved write.**
Acceptance: an interrupted chain that is resumed or reclaimed re-enters at the correct pending step and never re-runs an already-consumed write.
Check: recovery test simulates an interrupted chain and asserts exactly-once execution per approved write.

**S7 — The loop stays bounded and cost-gated.**
Acceptance: a chain is capped by an explicit iteration limit and stops when the per-turn cost gate blocks; the cap is raised from today's `MAX_ASSISTANT_TOOL_STEPS = 2` to a value that fits a 3-step chain.
Check: test asserts the cap terminates a runaway chain and that a blocked cost mode ends the turn.

## Class A / Class B (decision, verbatim)

**Class B (bounded, autonomous, no per-step approval) — exactly today's list, unchanged:**
`memory.write`, `memory.update`, `memory.delete`, `artifact.save`, `planning.open`, `planning.close`, `planning.record_decision`, `planning.record_note`.

**Class A (business/config, human-approved per write):** `settings.update`, `automation.create_rule`, `skill.propose`, `project.create`, `project.rename`, `project.archive`, `project.merge`, and **all** new operational writes (`appointments.*`, `cases.*`, `customers.*`, `kb.*`, `conversations.*`).

B does not grow when domains are added. `memory.delete` is the only B entry that deletes data; it stays because the handler restricts it to agent-authored memory.

## Tasks

- [x] T1 — Chain continues after an approved class-A write: `approve_plan`/`resume_thread` re-enter the graph instead of terminating. (S1, S2) — route: inline — commit `77b5ad28`
- [x] T2 — Sequential approval for step 2+: the chain can pause with a fresh approval per write and resume it. (S1, S2) — route: inline — commit `cb2cf13d`
- [x] T3 — Regression pins: read-only chaining and the single-write path are unchanged. (S4) — route: inline — commit `7dbca10f`
- [x] T4 — Reject mid-chain aborts cleanly with an audit record. (S5) — route: inline — commits `b56a1c87` (behavior + tests), `4391178b` (verifier probes)
- [x] T5 — Recovery/resume is exactly-once per approved write. (S6) — route: inline — commits `b0e1dfc6` (pins), `3d6609c1` (verifier probes)
- [ ] T6 — Iteration cap raised + per-iteration cost gate honored. (S7) — route: inline
- [ ] T7 — Tests extended (`tool_loop`, `chat`, `harness_guardrails`) + docs/help updated. (all) — route: inline
- [ ] — independent verifier at the feature end (high-risk change). (all)

## Non-goals

- Unit 2: new operational write tools (`appointments.*`, `cases.*`, `customers.*`, `kb.*`, `conversations.*`). This unit makes writes chainable; it does not add the domain tools.
- Unit 3: the `agent/registry.yaml` split and retiring the data-only sub-agents. Separate lane, no dependency.

## Assumptions (validate before/while implementing)

- A1 — The `MAX_ASSISTANT_TOOL_STEPS` cap rises from 2 to a bounded value that fits a 3-step chain (proposed 4), pending cost measurement. If the cost gate blocks typical chains, revisit.
- A2 — "Sequential approval" is the shape: each class-A write pauses with its own approval; there is no batch/up-front multi-step approval (rejected by U1: step 2's arguments depend on step 1's result).
- A3 — The post-approval re-entry reuses the existing `run_assistant` graph; no new runtime is introduced.

## Log

- **L1 (verbatim, user, 2026-10-15)** — "hey chat necesito que trabajemos en este handoff ready for odd que ha quedado ahi. lo vi hace muy poco. /home/stefan/repos/lumat-agent/.rapsodia-code/sessions/ready-for-odd/2026-09-24-harness-audit-y-cobertura-panel. necesito que lo analices y tambien revises el estado del codigo. el codigo y el repo completo deben haber avanzado un monton desde que se creo ese rapso session. entonces necesito que lo leas, lo revises y lo reevaluemos. De que se trata? aun esta como deuda? hay que reestructurar el plan?"
- **L2 (verbatim, user, 2026-10-15)** — "cadenas estaria bueno"
- **L3 (verbatim, user, 2026-10-15)** — "si. y cuales herramientas entrarian dentro de B acotada?"
- **L4 (verbatim, user, 2026-10-15)** — "si perfecto! vamos con eso"

**Re-evaluation of the handoff (2026-09-24) against the code at `97b63c00`.** The handoff's hard precondition (U1 tool chaining) is satisfied: `assistant-tool-chaining` merged (PR #339/#343), U2 `web.fetch` merged (#348/#349/#352), U3 delegation merged (#359/#360/#364), and `tool-catalog-trim` merged (#394). The catalog grew 22 → 38 tools (23 read / 15 write). The handoff's specific target — operational write coverage — is still zero, and remains Unit 2.

**Why Unit 1 changed shape.** U1 chose "the loop is read-only end to end" (`nodes.py:889-892`): any write ends the turn. The handoff's carry-in ("re-issue approval per iteration") was explicitly rejected by U1. The owner has now overridden that with "cadenas estaría bueno", which reopens the read-only-loop decision. Verified: `approve_plan` (`agent_chat.py:790`) and `resume_thread` (`:973`) call the `execute` node directly (`nodes.py:1008`) and never re-enter the graph, so an approval path cannot currently drive a second step. That is the work, not adding tools.

**Decision (owner, 2026-10-15).** "A + B acotada": class A (all business/config writes) is human-approved per write; class B (bounded autonomous) is exactly the current `AUTONOMOUS_WRITE_ALLOWLIST` and does not grow. `skill.propose` was verified to write the project config directly (`registry.py:716`) despite its name, so it stays in A.

**Next step.** Implement T1–T7 inline on this branch; independent verification at the end (high-risk: touches approval, recovery, audit).

**T1 — implemented (2026-10-15).** `approve_plan`/`resume_thread` no longer call the bare `execute` node; `_run_approved_plan` re-enters the assistant graph via `run_assistant(resume_plan=…, resume_approval=…)`. The graph routes `memory_bootstrap → guardrails` on resume (skipping `plan_llm`, which would break the token's argument binding), executes the write inside the graph, then continues `tool_loop_head → verify_effects → respond_stream → evidence`. Two decisions made during implementation:
  - **Re-entry is scoped to a plan that names a tool.** The `legacy_compat` pre-planner approval carries `tool: None`; re-entering the graph there grounds-refuses, so that degenerate path keeps the original `execute` node. Verified: `test_approved_plan_route_records_execution_audit`, `test_approved_plan_stream_replays_complete_execution_sequence`, `test_stopping_approval_pending_revokes_approval_and_prevents_execution` stay green unchanged.
  - **Resume-scoped responder resilience.** The responder runs on the resume path to narrate the executed write; a provider failure there now degrades the reply and records a degraded evidence entry instead of raising, because by then the write has already executed and must not be rolled back. Non-resume turns keep the original raise.
  - The seeded plan derives `kind` when missing (a persisted plan may predate it), so guardrails routes it as a tool plan.
  - Evidence: RED observed (`tool settings.update completed.` ≠ responder text) → GREEN; `tests/integration/test_assistant_settings_write.py::test_approved_write_reenters_the_graph_and_responds`; full suite green.

**T1 — independent verification (2026-10-15).** Verifier on `97b63c00..77b5ad28`: **no blockers**. S2 (binding) and S4 (no regression / legacy path) MET; S1 MET for T1's scope — the second-step chaining is T2 by design (`tool_loop_head` ends a non-read-only tool). Probes: exactly-once, `plan_llm` not called on resume, tampered args refused, unconsumed approval never writes, resume responder failure degrades and keeps the write, non-resume responder failure still raises, tool-less plan still uses the `execute` node once. Committed as `9d837d77` (`tests/integration/test_assistant_write_reentry_probes.py`, 7 probes; 3 fail at baseline). Full suite green.

**Follow-up (advisory, not a T1 blocker).** `resume_thread` on an *executing tool-plan with no approval at all* makes guardrails issue a fresh approval (`status=approval_pending`, `response=None`), and the caller then inserts an agent message with `content=None` → `NotNullViolation`, where baseline raised `PermissionError`. Only reachable from internally inconsistent persisted state; no normal path produces it, and no write occurs either way. Fold the guard into **T5** (recovery), which owns `resume_thread`.

**Session paused (2026-10-15).** T1 is done and verified; T2 is next. Resume from `odd/handoffs/assistant-write-chaining-t2.md` (main repo). The next task's load-bearing work is persisting the chain's accumulated `tool_results`/`tool_steps` across the approval pause, so a resumed chain keeps prior evidence.

**Main sync + merged-tree verification (2026-10-15).** The branch was 18 commits behind `origin/main` (`97b63c00` → `bc36318c`, which brought PR #629 `automation-uninstall` and PR #630 `panel-tecnico-wu8`). `origin/main` was merged into the branch as `23fbb7ed`: textually clean, with **zero shared files** — the branch touches only `app/chat/assistant/{graph,nodes,state}.py`, `app/services/agent_chat.py`, this document, and `tests/integration/test_assistant*.py`, while main's 24 changed files are all under `web/`, `app/panel/`, `db/migrations/` and the unrelated `automation-*` tests. Merged-tree evidence, run on the merged tree and not on the pre-merge branch: backend `pytest` **2293 collected, no failures**; panel `npm run build` (`tsc -b` + vite) exit 0; panel `npm test` (vitest) **109 files / 1244 tests pass**. The branch is pushed and tracked as PR (draft) so T1 is reviewable while T2–T7 continue.

**Delivery strategy (owner, 2026-10-15).** T1 alone authored 619 changed lines against a ≈350 forecast, so the owner chose `chained` over one growing PR: **PR #631** (T1) was marked ready, merged into `main` as `7c80b456`, and T2 starts on `odd/assistant-write-chaining-t2` cut from that merge.

**T2 — implemented (2026-10-15).** The chain now continues past a write and pauses on each class-A write. The three blockers, all closed:
  - **`tool_loop_head`** (`nodes.py`) no longer ends the turn for a non-read-only tool: any step that opted into `follow_up` continues — the read-only-only rule (D3) is reversed by the owner's decision — and it clears `approval` on continuation, so the next plan can never inherit the spent token. The cap (`MAX_ASSISTANT_TOOL_STEPS`, still 2; raising it is T6) still ends the chain and records `cap_reached`.
  - **`guardrails`** (`nodes.py`) replaces the `loop_write_refused` refusal with the invariant it actually needs: a class-A write proceeds only with a consumed approval matching *this exact* plan (`validate_execution`), and otherwise a fresh approval is issued — at any step. `PANEL_LOOP_WRITE_REFUSAL` and the decision are gone, and `_after_guardrails` drops its terminal entry.
  - **The chain state survives the pause.** `run_assistant` seeds `resume_tool_results`/`resume_tool_steps`; `_run_approved_plan` passes the accumulated evidence; `_persist_resumed_result` writes the fresh approval (assigned *after* the merge — merging a new token over a spent one would leave the spent token's fields on it), the new `current_plan` the next approval binds to, and `tool_results`/`tool_steps`/`cap_reached`; `_park_chain_on_next_approval` leaves the operator message pending with the plan/approval events continuing the sequence, because a chain shares one run id and a repeated sequence would be de-duplicated away.
  - **Deliberate updates to earlier pins.** `test_autonomous_write_turn_does_not_chain` → `..._chains_in_loop` (S3); `test_step_two_write_plan_is_refused_by_guardrails` and `test_graph_refuses_step_two_write_before_execution_or_approval` → the fresh-approval contract (S1/S2), split into its class-A and class-B cases. The verifier probe `test_resume_with_pending_approval_refuses_execution` keeps its invariant — no write without a consumed approval — but the enforcement changed from a hard `PermissionError` to parking behind a fresh approval, and the probe now asserts that shape. That also closes the T1 advisory: the `NotNullViolation` came from `approve_plan`/`resume_thread` building a reply out of a `None` response on `approval_pending`, and both now park instead of replying.
  - **Evidence.** RED observed first: 8 failures — 6 new rules plus the 2 rewritten pins — while the 2 regression pins (a write without `follow_up` still ends the turn; a resume with its own consumed approval still executes without a new prompt) passed at baseline. Then GREEN. New coverage in `tests/integration/test_assistant_write_chain.py`: a two-write chain driven through `approve_plan`, the continuation planner seeing step 1's evidence, and a reject at step 2 leaving it unexecuted. Full suite green (2293 collected).

**T2 — independent verification (2026-10-15).** Verifier on `7c80b456..cb2cf13d`: **no blockers**. S1, S2, S3 and S4 MET. S7 PARTIAL by design — the cap and the per-turn cost gate still bound a chain, and `tool_steps` is now cumulative across the pause so the cap holds across it, but the spec's "raised to fit a 3-step chain" belongs to T6. It independently reproduced the binding properties: a spent token cannot authorize the next plan, the fresh token carries the new plan's `arguments_sha256`, an unconsumed approval never writes, a tampered `current_plan` is refused, and a chain parked on its second approval survives `reap_stale_run` and the boot `reap_orphaned_runs` and still approves. Its probes are committed as `tests/integration/test_assistant_write_chain_verifier_probes.py`.

**T2 — advisories (recorded, not blockers).**
  - Rejecting a mid-chain approval leaves the thread at `stage=approval_pending` / `execution_status=pending`. Pre-existing at the baseline for the single-write reject; **T4** owns that cleanup.
  - When a resume pauses again, `_park_chain_on_next_approval` appends only the plan/approval events, so the earlier steps' `tool`/`evidence` events never reach the stream. A new situation, and no spec item requires them; **T7** owns the panel timeline — decide there whether a chain should emit its completed steps.
  - The verifier could not finish the whole backend suite inside its scratch copy (a tmpfs quota blocked the embedding-model download, and the scratch copy has no `.git` for the deploy-script test). The full suite was run green in the worktree instead: 2293 collected, no failures.

**T3 — implemented (2026-10-15).** Regression pins for S4. T2 reopened the read-only-only loop (D3) on purpose, so S4's two protected behaviours are exactly what the chain must not have changed. The broad shapes were already covered (~10 read-only-loop pins and ~7 single-write pins in `tests/unit/test_assistant_tool_loop.py`, `tests/integration/test_assistant_settings_write.py` and `test_assistant_write_reentry_probes.py`), so T3 adds **only the gaps the chain could have opened, and no others**:
  - `tests/integration/test_assistant_write_chain_regressions.py` — a single class-A write with `follow_up: False` still asks for **one** approval, executes **once**, completes, and triggers **no** re-plan and **no** fresh approval. This is the pin that stops the chain from quietly turning every write into a chain.
  - `tests/unit/test_assistant_tool_loop.py` — `guardrails` at step 0 still pauses a class-A write with exactly one pending approval, and a read-only turn still issues **no** approval, at any step.
  - **No meaningful runnable RED** (the ODD test-first exception): these characterise behaviour that already exists, so they pass at baseline — and they do. What makes them trustworthy is the mutation check, not a red run.
  - **Mutation check.** Ignoring `follow_up` in `tool_loop_head` (so every write chains) makes the single-write pin fail on `planner_calls == []`: the pin bites instead of passing vacuously. The mutation was reverted; `nodes.py` is clean.
  - **S4 evidence.** `git diff 7c80b456..HEAD -- tests/integration/test_assistant_settings_write.py` is **empty** — the single-write approval test is literally unchanged and passes. Of the `tool_loop` tests that did change since the baseline, the three are exactly the ones that pinned the reversed D3 decision (`loop_write_refused` at step 2, and "an autonomous write does not chain"); none of them pins S4's protected behaviours.
  - Full suite green with T3's 3 new tests.

**T4 — implemented (2026-10-16).** Rejecting a chain write is now terminal and audit-recorded (S5). Before this, `approve_plan(reject=True)` marked the message `rejected`, audited only `skill.propose`, and **returned early without settling the thread** — so a chain rejected at step 2 was left at `stage=approval_pending` / `execution_status=pending` / `live.status=approval_pending`, the T2 verifier's first advisory (and the baseline's single-write shape).
  - **Design decision: a distinct terminal `rejected` state, not the `cancelled` settle.** `stop` settles to `cancelled`; reusing it here would make the persisted thread disagree with the UI, whose rejection vocabulary is "Rechazado" (the operator message and the plan card both use `rejected`), and would record a rejection as a cancellation. So a rejection settles `stage`/`execution_status`/`live.status` to `"rejected"` and keeps `message.status = "rejected"`. Verified safe against every consumer before writing: `resume_thread` requires `stage == "executing"` (not resumable); `reap_stale_run`/`reap_orphaned_runs` act only on `live.status == "running"` (never touched); `/chat/active-runs` filters `live.status == "running"` (excluded); the panel reads `state.approval.status` (already `rejected`, so `isRunActive` is false); no frontend enum enumerates `stage` exhaustively.
  - **One new terminal status, one guard.** `_TERMINAL_RUN_STATUSES` gains `"rejected"` so `_EventCursor` ends any stream on a rejected run instead of polling to the 300 s timeout. Nothing else needed a change: `validate_approval` already requires `status == "pending"`, so a second approve/reject with the spent token returns `None` → HTTP 409.
  - **Audit for every tool.** A new `internal_chat.approval_rejected` entry (`{run_id, tool, reason: "operator_rejected", step}`) is recorded for any rejected plan; the pre-existing `skill.propose.rejected` entry is kept for `skill.propose` (its unit pin was updated to expect both actions and its stub `Session` gained a `flush` no-op).
  - **RED observed first.** `test_chain_rejecting_the_second_write_leaves_step_two_unexecuted` (extended) and the new `test_rejecting_a_single_write_settles_the_thread` failed on `assert 'approval_pending' == 'rejected'` before the change, then passed. Full backend suite green (exit 0); the verifier independently reproduced the RED at baseline (`assert None is not None` on `completed_at`, plus the stage assertion).

**T4 — independent verification (2026-10-16).** Verifier on `a9860e11..b56a1c87`: **no blockers, S5 MET.** It ran its probes in a fresh `/var/tmp` scratch copy (`/tmp` is unusable: its per-user tmpfs quota is exhausted, so `cp -a` fails — a hard environment limit, reported not worked around). It confirmed from a fresh session and raw SQL: terminal `rejected` persistence, the rejected step never runs, no agent reply appended, the spent token cannot approve or reject again (HTTP 409), `reap_stale_run`/`reap_orphaned_runs` leave it alone, and `resume_thread` refuses it. A positive control approves the same pending write cleanly, so the reject probes are not vacuous. Its 5 probes are committed as `tests/integration/test_assistant_write_chain_reject_verifier_probes.py`. Per-S# for the slice: S1–S4 MET, S5 MET, S6/S7 unimplemented by design (T5/T6).
  - Advisory (pre-existing, not change-caused): a rejected thread carries `recoverable: True`, like the baseline pending state and like `cancelled`/`failed`. **Checked and inert:** the panel's "Ejecución recuperable" notice is driven by a local state set on stream/watch failure, not by `assistant_state.recoverable`, so no rejected thread renders it.

**T5 — implemented (2026-10-16).** Pins for S6 (recovery is exactly-once), **no production change** — the exactly-once guarantee already holds, by two independent mechanisms this slice pins directly. The handoff asked to confirm that a crash *after the write executed but before the state persisted* leaves `execution_status == "running"` (so `resume_thread`'s claim fails and the reaper fails the run). **The code shows a different, safer mechanism:**
  - `claim_execution` (`recovery.py`) flips `execution_status` from `pending` to `running` in one `UPDATE ... WHERE ... = 'pending'`, so only the first caller wins — the atomic gate.
  - That `UPDATE` runs in the **same transaction** as the write and the final `_persist_resumed_result`. Nothing commits mid-execution in the assistant/tool path: `approve_plan`/`resume_thread` contain no `commit()`, the resume path passes no `on_stage` (so `publish_live` — the only mid-flight committer — is never called), and `get_db` commits only at request end. So a crash **rolls the claim back to `pending`**, and a later `resume_thread` reclaims it and runs the write exactly once. The `running`-persisted crash state the handoff describes is **not reachable**.
  - During an approved execution `live.status` stays `approval_pending` (nothing writes `live` between the claim and the final persist), so the reapers — which act only on `live.status == "running"` — would not touch it anyway.
  - **Pins** (`tests/integration/test_assistant_write_chain_recovery.py`, 3): a chain interrupted mid-execution is reclaimed exactly once with step 1's evidence intact; recovery **never** resumes a chain that still awaits the operator's approval (the human gate holds across recovery); and an already-claimed execution is never reclaimed again — it is failed closed.
  - **No runnable RED** (the ODD test-first exception): these characterise behaviour that already exists, so they pass at baseline — and they do. **Mutation checks** prove they bite: removing the `= 'pending'` guard from `claim_execution` makes the claimed-execution pin fail (`resume_thread` returns `True`); relaxing `resume_thread`'s `stage` guard *and* dropping its `processing`-message filter makes the approval-gate pin fail. Both mutations were reverted; `app/` is byte-identical to the baseline.

**T5 — independent verification (2026-10-16).** Verifier on `a32df55f..b0e1dfc6`: **no blockers, S6 MET.** Its falsification attempt on the crash finding **failed** — it could not make `execution_status == "running"` persist: instrumenting `Session.commit` and `publish_live` around `resume_thread` recorded **0 commits and 0 publishes**; a real mid-execution crash (raise + rollback) left `execution_status == "pending"`, the effect unapplied, and a later resume ran the write once; a crash inside the real `approve_plan` transaction rolled back consumption **and** the claim together (approval stayed `pending`, retry committed once). It also confirmed the atomic claim under a two-thread race and that the boot reaper leaves a resumable execution for recovery. Its probes are committed as `tests/integration/test_assistant_write_chain_recovery_verifier_probes.py` (7; the two that characterise unreachable/hazard states were left out deliberately, see advisories). Per-S# for the slice: S1–S5 MET, S6 MET, S7 NOT MET by design (T6).

**T5 — advisories (recorded, not blockers; both latent, neither change-caused, no producer in current code).**
  - `resume_thread` claims **before** it looks for the operator's `processing` message, and on the no-message path returns `False` **without releasing the claim**. A caller that then commits persists `execution_status == "running"`, and the thread is stuck (the spent claim is refused, and the reaper ignores `live.status == "approval_pending"`). Unreachable today: the precondition state (`stage=executing` with `execution_status=pending` committed) has no producer — every write of `stage="executing"` shares the claim's transaction and is overwritten by `_persist_resumed_result`. A one-line hardening (check the message before claiming) would remove the hazard; left as a follow-up rather than expanding this pins-only slice.
  - The state T5's first pin seeds (`stage=executing`, `execution_status=pending`, a consumed approval) is therefore **synthetic**: the reclaim-and-write branch is currently defensive/vacuous. The pin documents the intended invariant in case a future path ever produces that state.
