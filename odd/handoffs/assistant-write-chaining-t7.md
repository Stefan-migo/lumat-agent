# HANDOFF — assistant-write-chaining, continue with T7 (final slice)

**Feature**: `odd/tasks/assistant-write-chaining.md` (Unit 1 — approved writes chain inside the panel loop).
**Worktree**: `/home/stefan/repos/lumat-agent-odd-assistant-write-chaining` · **branch**: `odd/assistant-write-chaining-t7` (empty, cut from `main` = `3d442dd0`, upstream set to `origin/main` on purpose).
**Status**: T1 ✔ (#631) · T2 ✔ (#633) · T3 ✔ (#637) · T4 ✔ (#639) · T5 ✔ (#640) · T6 ✔ (#641). **T7 is the last task**, then the feature-end verifier.

## T7 — tests extended + docs/help updated (all specs)

**Goal**: close the feature's coverage and documentation. Extend the loop/harness suites for the chain and update the docs/help that describe the loop. Then run the **feature-end** independent verifier.

**Where to look (read the code, do not assume)**:
- `tests/unit/test_assistant_tool_loop.py`, `tests/integration/test_assistant_chat.py`, `tests/integration/test_assistant_harness_guardrails.py` — the focused suites the doc names for T7. The chain already has dedicated files (`test_assistant_write_chain*.py`, `test_t6_*`), so T7 extends the **named** suites with the gaps they still lack, not duplicates.
- Docs/help describing the loop: search for what documents the assistant tool loop and its bounds (the `MAX_ASSISTANT_TOOL_STEPS` bound, the approval-per-write chain, the class-A/class-B split). The S7 raise (2→4) and the T2/T4 behaviour changes must be reflected. `odd/tasks/assistant-tool-chaining.md` and `odd/tasks/asistente-lumat-config-layer.md` carry older statements of the cap (`MAX_ASSISTANT_TOOL_STEPS = 2`) — decide which are historical records (leave) and which are live docs (update).

### T7 also owns the panel-timeline advisory (from the T2 verifier)

When a resume pauses again, `_park_chain_on_next_approval` (`app/services/agent_chat.py`) appends only the **plan/approval** events, so the **earlier steps' `tool`/`evidence` events never reach the stream**. A chain shares one run id, so sequences must keep climbing (that is why `_events_for` takes a `sequence` offset). Decide whether a chain should emit its completed steps, and **pin the decision**. Consumer: `web/src/components/pages/AgentChat.tsx` (reads `assistant_state.approval` and the `approval` event; renders one collapsed activity block per run).

**Acceptance (T7 = all specs)**: the named suites cover the chain's behaviour, the docs/help match the shipped loop, and the timeline decision is pinned.

**Constraints / non-goals**: no new product behaviour beyond the timeline decision. Do not re-open approval binding, recovery, or the cap semantics — T2/T4/T5/T6 settled those.

## Feature end — independent verifier (MANDATORY)

After T7 is in, run **one** independent verifier over the **whole feature** (every S1–S7), not one per slice, and judge the S# verdicts. High risk: approval, recovery, audit. Baseline: the branch point `3d442dd0` (or `git merge-base main HEAD`).

## Where things stand (T1–T6, all merged and verified)

**T1** (#631, `7c80b456`) — the approval path re-enters the assistant graph (`run_assistant(resume_plan=…, resume_approval=…)`) instead of calling the bare `execute` node; a tool-less `legacy_compat` plan keeps `execute`.

**T2** (#633, `2514d9dc`) — the chain: `tool_loop_head` no longer ends the turn on a write (any step that opted into `follow_up` continues and clears the spent `approval`); `guardrails` issues a **fresh** approval per class-A plan at any step; the chain state (`tool_results`/`tool_steps`/`cap_reached`) survives the pause via `_persist_resumed_result`/`_park_chain_on_next_approval`.

**T3** (#637, `a9860e11`) — regression pins for S4 (read-only loop + single-write path), proven with a mutation check.

**T4** (#639, `a32df55f`) — rejecting a write is a **distinct terminal `rejected` state** (`stage`/`execution_status`/`live.status`, message `rejected`), audit `internal_chat.approval_rejected` for every tool, `_TERMINAL_RUN_STATUSES` gained `"rejected"`. S5.

**T5** (#640, `fa00bbc7`) — S6 pins, **no production change**: the exactly-once guarantee is the atomic `claim_execution` gate + `resume_thread` requiring `stage == "executing"` + a `processing` message. The handoff's "crash leaves `execution_status == 'running'`" was corrected: the claim shares one transaction with the write, so a crash rolls back to `pending` and recovery reclaims once; the `running`-persisted state is unreachable.

**T6** (#641, `3d442dd0`) — S7: `MAX_ASSISTANT_TOOL_STEPS` **2 → 4** (`app/chat/assistant/nodes.py`, the only production change). Cost measured first (3-step chain ≈$0.002 vs the $1.50 per-thread limit). Six pins updated deliberately; new pin `test_three_step_chain_completes_within_the_budget`.

**Merge commits on main**: `7c80b456` (#631), `2514d9dc` (#633), `a9860e11` (#637), `a32df55f` (#639), `fa00bbc7` (#640), `3d442dd0` (#641).

## Recorded advisories (not blockers; candidates for T7 or a follow-up)

- **Panel timeline** (from T2) — T7 owns it, above.
- **Planner cost under-billed within a run** (from T6) — every planner call uses cost key `{run_id}:planner` and `record_llm_cost` dedups by key, so only the **first** planner call of a chain is billed. Pre-existing; the raise widens the under-count 1→3 calls. Cost-accounting correctness; a dedicated follow-up should give each planner call a per-step key.
- **`resume_thread` claim leak** (from T5) — it claims **before** looking for the `processing` message and does not release the claim on the no-message path; a committed caller would persist `execution_status == "running"` and stick the thread. Latent: the precondition state has no producer. A one-line reorder (check the message before claiming) removes it.
- **`tool_loop_head` stops on `conservative`** (from T6) — it ends the loop on **any** non-normal cost mode, not only `blocked`. Pre-existing, out of slice.

## Environment bootstrap (already in place in this worktree)

```bash
cd /home/stefan/repos/lumat-agent-odd-assistant-write-chaining
ln -s /home/stefan/repos/lumat-agent/.venv .venv     # already present, gitignored
cp ../lumat-agent/infra/.env infra/.env              # already present, gitignored
PYTHON=/home/stefan/repos/lumat-agent/.venv/bin/python infra/test-db.sh up
eval "$(PYTHON=/home/stefan/repos/lumat-agent/.venv/bin/python infra/test-db.sh env)"
/home/stefan/repos/lumat-agent/.venv/bin/python -m pytest -q
```

The test-DB port derives from the worktree directory name. The `web/node_modules` symlink to the main repo is already there for the panel checks. Verifier scratch copies work under `/var/tmp` (**not** `/tmp`: its tmpfs quota is exhausted); a `.venv` symlink fails there — copy the venv and the fastembed cache.

## Route and discipline

- Parent implements **inline** on the branch; no writer trigger reason.
- Test-first where a runnable RED exists; for pure pins, a **mutation check** is what proves they bite (T3 precedent).
- Work-unit commit (`test(...)`/`docs(...)`), then a `docs(odd)` commit recording the id. Update the Engram mirror (`odd/assistant-write-chaining/tasks`) and the progress topic.
- Delivery is **`chained`** (owner decision): one PR per slice. T1 = #631, T2 = #633, T3 = #637, T4 = #639, T5 = #640, T6 = #641.
- **GitGuardian** stays **red** as an accepted false positive on PRs that merge `main` carrying the WU-E SMTP fixtures (the GitHub App ignores `.gitguardian.yaml`). `test` and `panel` are the required checks; merge with them green. Do **not** force-push to appease it.
- **Merge + cleanup gotcha**: `gh pr merge --delete-branch` fails the local delete when `main` lives in another worktree. Clean path: `gh pr merge <n> --merge` (no `--delete-branch`), then `git push origin --delete <branch>`, `git switch -c <next> origin/main`, `git branch -D <old>`.
- Graph Check before editing (`graphify query "<area>"`; the graph lives in `/home/stefan/repos/lumat-agent/graphify-out/`).
- Close every code change with a `Risk:` line. Push/PR are the owner's call; the owner merges.

## Resume pointers

- Read `odd/tasks/assistant-write-chaining.md` **in full** (specs S1–S7, tasks T1–T7, Log, advisories) before continuing.
- Engram: `odd/assistant-write-chaining/tasks` (doc mirror), `odd/assistant-write-chaining/progress` (per-slice detail), plus the merge/cleanup notes per slice.
- Previous handoffs: `assistant-write-chaining-t4-t7.md` (T4/T5/T6 detail), `assistant-write-chaining-t2.md`, `assistant-write-chaining-t1.md` (if present).
