# HANDOFF — assistant-write-chaining, continue with T2

**Feature**: `odd/tasks/assistant-write-chaining.md` (Unit 1 — approved writes chain inside the panel loop).
**Worktree**: `/home/stefan/repos/lumat-agent-odd-assistant-write-chaining` · **branch**: `odd/assistant-write-chaining` · **base**: `main` = `97b63c00`.
**Status**: T1 done + verified. T2 is next. T3–T7 pending.

## Where things stand (T1, done)

The approval path re-enters the assistant graph instead of calling the bare `execute` node:

- `app/services/agent_chat.py` → `_run_approved_plan(...)`: a plan that names a tool calls `run_assistant(resume_plan=…, resume_approval=…)`; a tool-less `legacy_compat` plan keeps the old `execute` node.
- `app/chat/assistant/graph.py` → `_after_memory_bootstrap` routes `memory_bootstrap → guardrails` when `state["resume"]` (skipping `plan_llm`, which would break the token's argument binding), and `run_assistant` seeds `plan`/`approval`/`planner`/`status`/`resume`. A missing `kind` is derived (`"tool"` if the plan names a tool).
- `app/chat/assistant/nodes.py` → the responder try/except is scoped to `state.get("resume")`: a provider failure after an executed write degrades the reply (bounded text + degraded evidence) instead of raising, so the write is never rolled back. Non-resume turns keep the original raise.
- `app/chat/assistant/state.py` → `resume: bool` added to `AssistantState`.

**Commits on the branch**: `d1c1c4be` (feature doc) · `77b5ad28` (T1 feat) · `17fdf1c9` (doc: T1 commit) · `9d837d77` (regression probes) · `37b2a3dc` (doc: verification outcome).

**Verification**: independent verifier over `97b63c00..77b5ad28` — no blockers. S2/S4 MET; S1 MET for T1's scope. Probes live in `tests/integration/test_assistant_write_reentry_probes.py` (7 tests; 3 fail at baseline). Full suite green.

## Environment bootstrap (the worktree has no venv)

```bash
cd /home/stefan/repos/lumat-agent-odd-assistant-write-chaining
ln -s /home/stefan/repos/lumat-agent/.venv .venv          # gitignored
cp ../lumat-agent/infra/.env infra/.env                    # gitignored
PYTHON=/home/stefan/repos/lumat-agent/.venv/bin/python infra/test-db.sh up
eval "$(PYTHON=/home/stefan/repos/lumat-agent/.venv/bin/python infra/test-db.sh env)"
/home/stefan/repos/lumat-agent/.venv/bin/python -m pytest -q
```
Test DB for this worktree is on port **6188**; its port derives from the worktree directory name (`tests/_testdb.py`).

## T2 — sequential approval for step 2+ (the real chain)

`odd/tasks/assistant-write-chaining.md`, T2, specs S1 + S2.

**Goal**: after an approved write, the chain continues to the next step; a step-2+ write pauses with its **own, fresh** approval and resumes. No batch/up-front multi-step approval (U1 rejected it: step 2's arguments depend on step 1's result).

**The three concrete blockers** (read the code, do not assume):

1. `app/chat/assistant/nodes.py` — `tool_loop_head` returns `{"status": "completed"}` for any non-read-only tool (`nodes.py:889-892`), so the loop never chains past a write. T2 must let an approved/autonomous write continue when the plan opted into `follow_up` (respect the cap; today `MAX_ASSISTANT_TOOL_STEPS = 2` — raising it is T6, coordinate).
2. `app/chat/assistant/nodes.py` — `guardrails` refuses a write at `tool_steps >= 1` with `loop_write_refused` (`nodes.py:779-787`). T2 must replace that refusal with a **fresh approval per write** for class-A tools (line 788-792 already issues an approval when no approval is present — reuse that path).
3. **The chain state does not survive the approval pause.** `_run_agent_turn_session` persists `tool_steps` but **not** `tool_results` into `thread.assistant_state` (`app/services/agent_chat.py`, the `merge_assistant_state` call around line 459-475). On resume, `run_assistant` seeds only `plan`/`approval` and starts with `tool_results: []`. T2 must persist the accumulated chain evidence on `approval_pending` and re-seed it on resume (`run_assistant` needs a `resume_tool_results` / `resume_tool_steps` seed, and `_run_approved_plan` must pass them). This is the load-bearing part of T2.

**Constraints to respect**:
- Class **B** stays exactly today's `AUTONOMOUS_WRITE_ALLOWLIST` and must run in-loop with no per-step approval; class **A** is every business/config write (see the doc's "Class A / Class B" section). B does not grow.
- The legacy `tool=None` path must keep its single-node execution (T1 established this).
- Re-entry must not re-run `plan_llm` for the pending plan (binding), but the continuation step **does** re-plan from accumulated evidence — that is the point of the chain.
- The T1 advisory (see the doc's "Follow-up") is T5's, not T2's: `resume_thread` with a tool plan and **no** approval yields a `NotNullViolation`.

**Acceptance (from the doc)**: with a write-capable tool present, the assistant reaches the second and later steps in the same turn, each class-A write pausing with its own approval; reject at any step aborts cleanly; recovery is exactly-once.

**Test-first**: one RED per rule, through `approve_plan`/`resume_thread` and the graph. Do not infer applicability from existing tests — observe RED.

## Route and discipline

- Parent implements **inline** on the branch; no writer trigger reason. High-risk change → **independent verifier at the end** (touches approval, recovery, audit).
- Work-unit commit with `feat(...)`/`test(...)`, then record the commit id in the feature doc. Update the Engram mirror (`odd/assistant-write-chaining/tasks`).
- Graph Check before editing (graphify is current in the main repo); run focused tests + the full suite.
- Close every code change with a `Risk:` line.
- Do not commit on the user's behalf beyond the work-unit commits; push/PR stay the owner's call.

## Resume pointers

- Engram: `odd/assistant-write-chaining/tasks` (doc mirror) and `odd/assistant-write-chaining/progress` (T1 progress, id `#6666`).
- Read `odd/tasks/assistant-write-chaining.md` in full (specs S1–S7, tasks T1–T7, Log) before continuing.
