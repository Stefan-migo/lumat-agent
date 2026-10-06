# ODD: asistente-planning

**Branch**: `odd/asistente-planning`
**Worktree**: `../lumat-agent-odd-asistente-planning`
**Base**: `10dbd301` (= `main` = `origin/main`, merge of PR #487)
**Status**: T1 in progress.

## Objective

Slice 4 of the Asistente Lumat workspace: **simplify planning (Cortex)**. Planning becomes a
**read-only business mode** that blocks write tools while allowing investigation (KB/web),
planning memory, and one final report. The heuristic per-turn classifier and the per-turn
decision ceremony are deleted. The SDB handoff and the Markdown preview are explicitly
deferred to later slices.

## Problem

Planning today is over-built for what the business needs:

- `classify_cortex_turn` (`app/chat/assistant/nodes.py`) heuristically classifies each turn
  (`question`/`research`/`decision`/`continue`/`close`) from text prefixes — brittle and it
  infers lifecycle changes from free text.
- `cortex_session_turn` writes a Tukulpan **decision memory per classified decision**, and
  `close` is coupled to a mandatory SDB handoff (`CortexHandoff` `pending/approved`).
- The close path (`app/services/agent_chat.py`) builds an approved-plan-shaped SDB handoff,
  issues approval, stores it in `thread.current_plan`, and calls `archive_report()`, which
  writes to **`panel`** scope (`app/services/tukulpan.py`) — not the planning `agent` scope.
- Planning has no read-only enforcement: the effective tool policy (project ∩ role ∩ tier) is
  applied only at guardrails; the execution boundary re-checks the **global** catalog.

## Decisions (locked — do not re-open)

Closed before this slice; recorded in Engram
`cortex-session/2026-10-05-asistente-lumat-workspace-multiagente/decision/*`:

- **D2/D16/D18** — Planning keeps **one artifact: the final report**. Report = Tukulpan memory
  scope **`agent`** as source of truth. The Markdown preview in the project directory is
  **deferred to Slice 6** (no project directory or artifact writer exists today).
- **Session model**: planning stays **1 session = 1 thread** (`/planning <topic>` opens,
  `/planning close` closes). Session lifecycle stays; only the classifier/ceremony is removed.
- **D6 handoff**: the SDB handoff is **deferred to Slice 5**. This slice only removes the
  mandatory handoff ceremony; `sdb_*` nodes stay untouched.
- **D16 read-only**: reuse the tool tier gate. Planning blocks writes **except** its own
  memory/report writes.

## Scope

**In**

- Delete the heuristic turn classifier and the per-turn decision ceremony (state fields,
  registry declarations, validation, tests).
- Delete the dead `parse_planning_command` parser (no caller in `app/`).
- Enforce planning read-only deterministically at **both** enforcement points (guardrails and
  execution), preserving `memory.write` for planning memory.
- One report at close, written to Tukulpan scope **`agent`**, decoupled from the SDB handoff.
- Remove the Cortex → SDB graph edge only.
- Retarget the affected lifecycle/API tests.

**Out (later slices — do not build here)**

- SDB = loop + verify (Slice 5) and the optional handoff trigger (Slice 5).
- Project directory, Markdown preview file, planning UI (Slice 6).
- Any migration — this slice touches no DB schema (`cortex_session` lives in
  `thread.assistant_state`, not a column).

## Current code map (touch points)

| Area | Location |
|---|---|
| Planning entry | `app/panel/api/routes/chat.py` open/list/close/reopen (`156–241`) writes `cortex_session` into `thread.assistant_state` |
| Cortex nodes | `app/chat/assistant/nodes.py`: `parse_planning_command` (93), `cortex_session_gate` (109), `classify_cortex_turn` (118), `cortex_session_turn` (133) |
| State | `app/chat/assistant/state.py`: `PlannerOutput.cortex_class` (34), `CortexHandoff`/`CortexSession` (81–105), `validate_cortex_session` (139) |
| Graph | `app/chat/assistant/graph.py`: gate/turn nodes + edges (58–60, 117–161) |
| Registry | `agent/registry.yaml` `cortex_session` (99–101); validation `app/agent_registry.py` (181–205) |
| Read-only gate | `app/services/project_config.py:61–109` (`resolve_effective_config`); guardrails `nodes.py:841`; execution `nodes.py:1039–1051` (passes **global** whitelist); `execute_tool` `app/chat/assistant/tools/registry.py:668–706` |
| Report / close | `app/services/agent_chat.py:89–115`; `app/services/tukulpan.py` `record_decision` (414), `archive_report` (440), `AGENT_SCOPE` (58); route close `chat.py:217–225` |
| Thread field | `app/models.py` `InternalChatThread.current_plan` (864–877) — generic; also used by SDB/approval |

## Tasks

- [ ] **T1 — Remove classifier and per-turn ceremony.**
  Remove `classify_cortex_turn`, `PlannerOutput.cortex_class`, `CortexHandoff`, the
  ceremony-only `CortexSession` fields (`decision_keys`, `last_class`, `next_decision`), the
  dead `parse_planning_command`, the `cortex_session` classes/commands in `agent/registry.yaml`
  and its validation in `app/agent_registry.py`. Keep the lifecycle fields
  (`slug`, `topic`, `status`, `opened_at`, `closed_at`, `report_key`). Confirm call sites
  before deleting any field.
  *AC*: no reference to `cortex_class`/`classify_cortex_turn`/`CortexHandoff` remains; the
  session still validates and the gate still routes active sessions to planning.

- [ ] **T2 — Deterministic planning read-only.**
  Derive the planning tool policy from the effective whitelist (project ∩ role ∩ tier) minus
  writes, **except** `memory.write`. Enforce it at guardrails **and** at execution by passing
  the effective/planning whitelist into `execute_tool`.
  *AC*: an active planning session refuses `memory.delete`, `project.create`, `automation.*`,
  etc.; `memory.write` and KB/web reads still work; normal (non-planning) turns are unchanged.

- [ ] **T3 — Single `agent`-scope report at close, decoupled from SDB.**
  Replace the close path's `archive_report` (`panel` scope) + mandatory handoff with one write
  to Tukulpan scope `agent`. Update `app/services/agent_chat.py`, `app/services/tukulpan.py`,
  and the close route.
  *AC*: close writes exactly one `agent`-scope report memory; no SDB handoff/approval is
  created by planning close; `sdb_*` nodes are untouched.

- [ ] **T4 — Remove the Cortex → SDB graph edge only.**
  *AC*: `graph.py` no longer edges Cortex into `sdb_trigger_gate`; every `sdb_*` node and its
  wiring is byte-unchanged otherwise.

- [ ] **T5 — Retarget lifecycle/API tests and verify.**
  Update `tests/unit/test_cortex_session_foundation.py`, `test_cortex_session_loop.py`,
  `tests/integration/test_cortex_session_runtime.py`, `tests/unit/test_agent_registry.py`,
  the `cortex_class` planner fixture in `tests/integration/test_assistant_chat.py`, and the
  report/handoff case in `tests/integration/test_sdb_persistence.py` (SDB-only cases stay).

## Acceptance criteria (slice)

1. Planning is read-only: write tools are refused in planning turns; KB/web investigation and
   planning `memory.write` still work.
2. No heuristic turn classification survives; no per-turn decision memory is written.
3. Closing a planning session writes exactly one `agent`-scope report and creates no SDB
   handoff.
4. The Cortex → SDB edge is gone; `sdb_*` nodes are otherwise untouched.
5. Full targeted suite green; no DB migration added.

## Checks

- Strict TDD ON. RED before GREEN. Runner: `uv run --no-sync pytest tests/`.
- Test DB: `bash infra/test-db.sh up` + `eval "$(bash infra/test-db.sh env)"`.
- Graph Check (per repo AGENTS.md): `graphify query` / `graphify path` before each task.
- 5-Step Gate: atomic commit (≤5 files), verify, finalize.
- RDD on: run the review transition after implementation.

## Progress log

- Provisioned worktree (`uv sync --frozen`, `cp ../lumat-agent/infra/.env infra/.env`), test DB up.

## Verification

_Pending implementation._
