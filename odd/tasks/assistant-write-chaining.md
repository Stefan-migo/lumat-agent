# assistant-write-chaining (Unit 1) — approved writes chain inside the panel loop

**Objective**: let the panel assistant complete a multi-step write chain inside one user turn, where every business write is human-approved before it runs and the bounded autonomous class runs without per-step approval.
**Branch**: `odd/assistant-write-chaining` (cut from `main` = `97b63c00`).
**Delivery strategy**: `ask-on-risk` (default). Forecast ≈ 350 authored changed lines.
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

- [ ] T1 — Chain continues after an approved class-A write: `approve_plan`/`resume_thread` re-enter the graph instead of terminating. (S1, S2) — route: inline
- [ ] T2 — Sequential approval for step 2+: the chain can pause with a fresh approval per write and resume it. (S1, S2) — route: inline
- [ ] T3 — Regression pins: read-only chaining and the single-write path are unchanged. (S4) — route: inline
- [ ] T4 — Reject mid-chain aborts cleanly with an audit record. (S5) — route: inline
- [ ] T5 — Recovery/resume is exactly-once per approved write. (S6) — route: inline
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
