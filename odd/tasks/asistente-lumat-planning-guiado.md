# ODD: asistente-lumat-planning-guiado

**Branch**: `odd/asistente-lumat-planning-guiado`
**Worktree**: `../lumat-agent-odd-asistente-lumat-planning-guiado`
**Base**: `6d7988b2` (= `main` = `origin/main`, merge of PR #592)
**Delivery strategy**: `exception-ok` (repo convention: one PR per `odd/<slug>` branch, `size:exception` when > 400 authored lines)
**Test runner**: `uv run --no-sync pytest tests/` (strict TDD ON); frontend `npm test` + `npm run build`
**Status**: In progress. T1 done. Scope = guided core (WU1–WU6). SDB handoff (WU7) deferred to Slice 5.

## Objective

Turn the assistant's "Sesiones de planificación" (Cortex sessions) from a state toggle that closes
with a topic-only stub report into a **guided brainstorming session** facilitated by the chat agent,
in its own thread, with explicit capture of decisions/notes, a minimal closing checklist, and a
substantive session report in Tukulpan `agent` memory.

## Problem (verified against code, obs 6437 + explorer + parent spot-check)

The "planning mode" exists and works, but only as a read-only tool filter:

- `_effective_tools` (`app/chat/assistant/nodes.py:573-597`) already drops write tools for an active
  session (except `memory.write`) — D16 read-only **is implemented**.
- The heuristic turn classifier and `parse_planning_command` were deleted in the prior slice.
- **No guided experience**: no facilitator persona/overlay, no open/close/capture tools, no checklist.
- **The close is a stub**: `close_planning_session` (`app/panel/api/routes/chat.py:341-352`) writes
  `json.dumps({"topic": ...})` and `close_cortex_session` (`app/services/agent_chat.py:75`) persists
  it through `write_agent_report` (`app/services/tukulpan.py:443`, scope `agent`).
- **Not its own thread**: `open_planning_session` (`chat.py:286-316`) reuses the `thread_id` the
  frontend sends (`AgentChat.tsx:635,796`); no route creates a dedicated session thread by default.

Corrections to the prior record: `_sdb_plan` / `_run_sdb_tasks` **do not exist** today;
`odd/tasks/asistente-planning.md`'s "current code map" is historical. There is **no**
project-directory markdown writer — `artifact.save` (`registry.py:753`) is the only file writer.

## Decisions (locked — do not re-open)

From the planning session `.rapsodia-code/sessions/ready-for-odd/2026-10-13-asistente-lumat-planning`
(D1–D8) and the owner's closure answer:

- **D1/D2** — A **facilitator agent in chat** drives the session as a **guided brainstorming**; open
  topic (Lumat or not). No UI wizard.
- **D3** — The agent can **open/close** the session by **explicit user order** via tools, in addition
  to the UI button; on close it **offers** (never automatic).
- **D4/D16** — If the topic touches Lumat, the agent **reads** state with tools; it **never executes**
  business tools (read-only).
- **D5** — Capture with **explicit tools + confirmation** (`planning.record_decision` /
  `planning.record_note`); never save silently.
- **D6** — Handoff to the executor (SDB) only when Lumat + concrete action, user-confirmed → **WU7,
  deferred to Slice 5** (do not build here).
- **D7** — Free conversation with a **minimal closing checklist** (objetivo, decisiones, riesgos,
  próximos pasos); the agent does not offer to close before covering it.
- **D8** — **Each session opens its own thread.**
- **Closure contract (owner, 2026-10-14)** — **Minimum required + close always allowed**: the system
  assembles the report from captured items, requires the minimum (**objetivo + al menos una decisión**)
  and **flags missing items as gaps**; the user can ALWAYS close. The server never blocks.
- **D2/D18** — **One artifact: the final report**, written to Tukulpan scope **`agent`** as source of
  truth and rendered as markdown preview in the UI. The on-disk project-directory file is **out of
  scope (Slice 6)** — the preview is the substantial markdown content already exposed by the
  detail/close responses.

## Specs

Numbered requirements. Fragments in quotes are verbatim (never reworded).

- **S1 — Own thread per session (D8).** The observable trigger is: `El usuario pide por chat "abrimos
  sesión de planificación con <tema>" → se crea la sesión en un hilo propio.` Opening a session (by
  tool or by the UI command/button) creates a **dedicated thread** and the UI **switches to it**.
  *AC*: after opening, the persisted session lives on a thread whose id differs from the origin thread;
  the UI is showing the session thread.
- **S2 — Facilitator overlay (D1/D2/D7).** When a thread has an **active** planning session, the
  per-turn persona/prompt includes a **planning facilitator overlay**: ask before assuming, capture
  only with confirmation, **read-only**, and do not offer to close before the checklist is covered.
  *AC*: a planning turn's effective system prompt contains the overlay; a non-planning turn's does not.
- **S3 — Lifecycle tools (D3).** `planning.open` and `planning.close` exist as assistant tools the
  agent can call on explicit user order, in addition to the existing UI routes.
  *AC*: the planner catalog exposes both names for admin/operador; calling them mutates the session.
- **S4 — Capture tools (D5).** `planning.record_decision` and `planning.record_note` exist and store
  **structured** entries on the session; the agent calls them **only after the user confirms**.
  *AC*: recording appends a structured decision/note to the session; nothing is written without a call.
- **S5 — Read-only (D16).** In an active planning session the agent does not execute business tools.
  *AC*: `planning.*` and `memory.write` are allowed; other write tools are refused; reads still work.
- **S6 — Minimum + gaps (closure contract).** The close computes the checklist against the minimum
  `objetivo + al menos una decisión`; `riesgos` and `próximos pasos` missing are reported as **gaps**,
  not errors.
  *AC*: closing with objective + ≥1 decision succeeds and lists pending checklist items as gaps;
  closing with neither succeeds too and flags both as gaps.
- **S7 — Close always allowed.** The server never blocks a close.
  *AC*: `planning.close` / the close route returns success regardless of checklist coverage.
- **S8 — Substantial report (D2/D18).** Close writes **substantive markdown** (objective, decisions,
  risks, next steps, gaps) — not topic-only JSON — to Tukulpan scope `agent`, exposed by the detail and
  close responses and rendered in the UI.
  *AC*: the stored report content contains the captured objective and decisions; it is not
  `{"topic": ...}`.
- **S9 — SDB handoff (D6) — deferred.** Only if Lumat + concrete action, user-confirmed. Not built here.
- **S10 — No regression.** Existing planning lifecycle/API/frontend behavior (list/detail/reopen,
  thread-list exclusion, read-only filter) keeps working.

## Scope

**In**: S1–S8, S10. `planning.*` tools; facilitator overlay + read-only carve-out; own-thread-per-session
(server + UI switch); structured captures; substantive report + UI preview; hybrid close gate.

**Out (do not build here)**: S9 SDB handoff (Slice 5); on-disk project-directory markdown file (Slice 6);
any DB migration (`cortex_session` lives in `thread.assistant_state` JSONB).

## Current code map (touch points, verified)

| Area | Location |
|---|---|
| Read-only gate | `app/chat/assistant/nodes.py:573-597` `_effective_tools` (carve-out excepts `memory.write`) |
| Persona/prompt | `nodes.py:620` `_effective_persona`, `:646` `_responder_system_prompt`; `agent/prompts/` |
| Tool registry | `app/chat/assistant/tools/registry.py:722` `TOOL_REGISTRY`, `:761` `ROLE_TOOL_ALLOWLIST`, `:27-35` `AUTONOMOUS_WRITE_ALLOWLIST`, `:900-927` dispatch |
| Tool whitelist | `agent/registry.yaml:68-97` `assistant.tools_whitelist` |
| Session state | `app/chat/assistant/state.py:77-88` `CortexSession`, `:139` validate |
| Open/close routes | `app/panel/api/routes/chat.py:286-316` open, `:341-352` close, `:355-367` reopen, `:145-160` helpers |
| Close/report writer | `app/services/agent_chat.py:75` `close_cortex_session`; `app/services/tukulpan.py:443` `write_agent_report`; `tukulpan.py:417` `record_decision` |
| Threads | `app/services/agent_chat.py:264` `create_thread` |
| SSE events | `app/services/agent_chat.py:617-664`; frontend `AgentChat.tsx:492-504` `handleEvent` |
| Frontend | `AgentChat.tsx:112-119` command, `:631-646`/`:788-804` open/close, `:614-623` closeSession, `:1164` pill; `PlanningSessions.tsx`; `web/src/api.ts:315-319`; `web/src/types.ts:52-57,199` |

## Tasks

- [x] **T1 — Lifecycle tools `planning.open` / `planning.close`** (S3, S1 server side). Done — new
  `app/services/planning.py` (single source for the routes and the tools), route refactor, the two
  tools registered in `TOOL_REGISTRY` / `ROLE_TOOL_ALLOWLIST` (admin, operador) / `AUTONOMOUS_WRITE_ALLOWLIST`
  / `agent/registry.yaml`, dispatch branch with `trusted_thread_id`, and the `planning.*` read-only
  carve-out in `_effective_tools`. Route: inline. Evidence: `tests/functional/test_planning_tools.py`
  RED→GREEN; full `pytest tests/` green; commits `186597c7` (refactor) + `4bcea4b6` (feat);
  `review_due: false (under_budget)`.
- [ ] **T2 — Capture tools + structured session state** (S4). `planning.record_decision(title,
  content)` and `planning.record_note(kind, content)` with `kind ∈ {objective, risk, next_step,
  general}`; extend `CortexSession` + `validate_cortex_session` with the capture fields. Route: inline.
- [ ] **T3 — Own thread per session + UI switch** (S1). Open route/tool creates the thread; new SSE
  event carries the new `thread_id`; frontend switches via `onThreadOpened`; `/planning` command and
  button no longer reuse the current thread. Route: inline.
- [ ] **T4 — Facilitator overlay + read-only carve-out** (S2, S5). Add
  `agent/prompts/planning_facilitator.md`; inject it in `_effective_persona`/`_responder_system_prompt`
  when the session is active; carve `planning.*` into `_effective_tools`. Route: inline.
- [ ] **T5 — Substantive report + preview** (S7, S8). `close_cortex_session` builds markdown from the
  captures; detail/close responses expose it; UI renders "Informe de cierre". Route: inline.
- [ ] **T6 — Close gate: minimum + gaps** (S6). Close computes the checklist vs the minimum and returns
  `gaps`; overlay instructs not to offer close before the minimum; never blocks. Route: inline.
- [ ] **T7 — Frontend surfaces** (S1, S3, S4, S8). Session header/checklist in the planning thread,
  capture/close affordances, report card. Route: inline.
- [ ] **T8 — SDB handoff** (S9). **Deferred to Slice 5** — not this feature.

## Acceptance criteria (slice)

1. Opening a session (tool or UI) creates a dedicated thread and the UI shows it (S1).
2. An active planning turn uses the facilitator overlay; a normal turn does not (S2).
3. `planning.open` / `planning.close` exist and work by explicit order; the button still works (S3).
4. `planning.record_decision` / `planning.record_note` store structured entries after confirmation (S4).
5. Planning stays read-only for business tools; `planning.*` and `memory.write` are allowed (S5).
6. Close requires objective + ≥1 decision and flags missing riesgos/próximos pasos as gaps, but always
   succeeds (S6, S7).
7. Close writes a substantive markdown report to Tukulpan `agent` scope and the UI renders it (S8).
8. No regression on the existing planning lifecycle/API/UI (S10).

## Checks

- Strict TDD ON. RED before GREEN. Runner: `uv run --no-sync pytest tests/`.
- Test DB: `bash infra/test-db.sh up` + `eval "$(bash infra/test-db.sh env)"`.
- Graph Check (repo AGENTS.md): `graphify query` / `graphify path` before each task.
- 5-Step Gate: atomic commit (≤5 files), verify, finalize.
- Frontend: `npm test` + `npm run build` (includes `tsc -b`).
- RDD on: run the review transition after each work-unit commit; boundary advances only when
  `review_due: false` or the review is acknowledged.

## Progress log

- Base `6d7988b2`; worktree provisioned (`uv sync --frozen`, `infra/.env`, `web/ npm ci`, test DB up).
- Exploration done: `gentle-ai-explore` map + parent spot-check; corrections recorded in Problem.
- **T1 done** — lifecycle tools. New `app/services/planning.py`; routes refactored to it; `planning.open`/
  `planning.close` registered (roles admin/operador, autonomous write, whitelist) with the
  `trusted_thread_id` dispatch; `_effective_tools` preserves `planning.*` in a read-only session; the
  persona now names both tools as explicit-order writes. Touched exact-set/golden tests updated
  (`test_assistant_tools.py`, `test_tool_tiers.py`, `test_effective_config.py`, `test_assistant_delegation.py`).
  Commits `186597c7`, `4bcea4b6`.
- Engram mirror **pending** (the `mem_save` failed: multiple active runtime sessions for `lumat-agent`;
  no authoritative `session_id` available — not invented).

## Log

- **L1 (2026-10-14, verbatim)** — "hey chat quiero que continuemos con este handoff a odd
  /home/stefan/repos/lumat-agent/.rapsodia-code/sessions/ready-for-odd/2026-10-13-asistente-lumat-planning.
  dame un overview antes de continuar"
- **L2 (2026-10-14, verbatim)** — "ok vamos con el nucleo guiado"
- **L3 (2026-10-14, decision)** — Closure contract: "Mínimo + cierre siempre permitido". Minimum =
  `objetivo + al menos una decisión`; missing items flagged as gaps; close never blocked.
