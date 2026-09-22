# ODD: assistant-grounding-gate

## Objective

Give the panel assistant (`app/chat/assistant/`) the grounding contract it does not have: an
answer to a knowledge question must be founded on retrieved knowledge-base evidence. When there is
no evidence, the turn ends in a deterministic clarification instead of a synthesized answer.

This mirrors the contract the customer-facing WhatsApp chat already enforces.

## Problem

Measured on `main` = `e340266d`, not recited:

- `guardrails` (`app/chat/assistant/nodes.py:523-524`) routes to `respond_stream` as soon as
  `plan.kind != "tool"`. **A `respond` turn never touches the knowledge base.**
- `agent/prompts/assistant_respond.md` is a pure template (`<user_input>`, `<available_tools>`,
  `<tool_statement>`, `<tool_evidence>`, `<context>`). It states no requirement of citation,
  evidence, or refusal.
- `agent/personas/assistant.md` says "evidence-driven plan" — declarative and undefined. The only
  explicit evidence rule concerns not claiming an *action* completed before its tool result exists.
- `rg -i "CANNOT_ANSWER|cannot_answer|no_evidence|ungrounded|insufficient|clarification"
  app/chat/assistant/` returns **nothing**. There is no coverage gate.
- `collect_evidence()` (`nodes.py` ~731) emits, when no tool ran,
  `make_evidence(tool=None, status="completed", detail="Assistant response generated")`. That is an
  execution marker, not factual support.
- `kb.retrieve` (`app/chat/assistant/tools/registry.py:396`) is described as "Retrieve grounded
  knowledge-base results" but is planner-selected and optional, runs with `audience=None`, and is
  only `read_only=True`. Its output is injected as text into `<tool_evidence>` with no entailment
  check.

**Contrast — the contract that exists.** `app/chat/nodes/respond.py` performs mandatory retrieval
before answering (`:129-137`) and takes a deterministic refusal/escalation path on a KB miss
(`:138-150`, `escalate=True`, reason `kb_miss`). Only non-empty chunks reach `_answer_from_kb`.

**Structural corroboration.** The knowledge graph has no directed path
`kb.retrieve -> collect_evidence`; the only link is module containment (`contains` / `imports_from`),
not a call. Retrieval and evidence never meet.

**Not the same as the repo's "declared with no consumer" pattern** (`kb_scope`,
`source_meta.category`, `messages.<key>`). Here the mechanism *is* consumed; what is unenforced is
its semantic relationship to the answer. That distinction is why this is a contract change and not a
deletion.

## Why

An internal operator can currently receive a confident factual answer about Lumat with zero
retrieved evidence behind it, and nothing in the system notices or refuses. The panel assistant is
the surface where staff ask the agent about the business; an ungrounded answer there is
indistinguishable from a grounded one.

## Authorized scope

Human-authorized in this session, per feature, before `rapso worktree create`:

- Contract: **hard gate, mirror of the customer chat** (not an uncertainty label, not "leave as is").
- Mechanism: **mandatory retrieval on the `respond` path + deterministic refusal on the miss**, with
  an explicit and narrow conversational exemption.
- Worktree `odd/assistant-grounding-gate`, one PR, one type label.

Rejected alternatives, with their evidence:

| Rejected | Why |
|---|---|
| New field on `PlannerOutput` | `extra="forbid"` plus the planner's history: Engram #4574 documents the panel planner never produced a valid plan in production. A mis-satisfied required field would degrade every turn. |
| Deterministic pre-gate by patterns | P9 measured that word triggers are brittle (`\breclamo\b` produced a false positive). |

## Design decision (the contract)

Flow on the non-tool path:

```
guardrails
  -> kind == "tool"          -> execute_tool          (unchanged, OUT OF SCOPE)
  -> conversational turn     -> respond_stream        (exempt, unchanged)
  -> otherwise               -> retrieve_kb
        chunks present       -> respond_stream with a <kb> block
        chunks empty         -> deterministic clarification, no LLM answer
```

- **Retrieval discipline** mirrors `app/chat/nodes/respond.py:129-137`: same similarity threshold
  source, same "only non-empty chunks reach the answer" rule. `audience=None` (internal operator sees
  the whole KB), matching what the `kb.retrieve` tool already does.
- **The refusal is deterministic**: no model call decides it.
- **Declared soft spot — the conversational exemption.** It is the only soft part of the gate and the
  only place this unit trades strictness for usability. Bound it narrowly and declare it: a *short,
  purely social* message (greeting / thanks / farewell / acknowledgement). The length bound is what
  keeps it from exempting a real question. Test **both directions**:
  - a greeting is exempt and is not refused;
  - a real knowledge question is never exempt, including one that opens with a greeting.
- **Out of scope, declared:** tool turns (`kind == "tool"`) keep their current behavior even when the
  tool result is empty. This unit closes the measured gap — a `respond` turn that never reaches the
  KB — and nothing more.

## Acceptance criteria

1. A non-conversational `respond` turn retrieves from the KB before answering.
2. An empty retrieval produces a deterministic clarification; the responder is not called and no
   factual answer is synthesized.
3. A non-empty retrieval reaches the responder as a bounded evidence block, and the prompt requires
   the answer to come from it.
4. A short purely social message is exempt: answered as today, not refused.
5. A real knowledge question is never exempt, including one that opens with a greeting.
6. Tool turns are behaviorally unchanged.
7. The canonical spec carries the grounding requirement.

## Applicable checks

- **Strict TDD mode: ACTIVE.** Source: `openspec/config.yaml` (`testing.strict_tdd: true`,
  `apply.tdd: true`) and topic `sdd/lumat-agent/testing-capabilities`. Cycle is RED -> GREEN ->
  REFACTOR; observed RED is required before implementation.
- Test runner: `uv run pytest` (backend). `testpaths = ["tests"]`, `addopts = "-q"` — read the exit
  code and the pass count, not a suppressed count line.
- Integration tests need the test DB:
  `bash infra/test-db.sh up` (wait `healthy`) then `eval "$(bash infra/test-db.sh env)"`.
- Baseline on the clean base `e340266d`: **98 assistant unit tests + 113 assistant integration tests
  = 211 green.** Any new failure is ours.
- Graph Check (project Step 1) before editing: `graphify query` / `graphify path`, and record the
  nodes consulted below.

## Checklist

- [x] **T1** — Pin the mirrored retrieval contract. Route: inline (2 files, read to decide).
      **Done — see "Pinned contract" below.**
- [x] **T2** — RED. Route: delegated writer. Observed RED before implementation: 5 failed, 1 passed
      on `tests/unit/test_assistant_grounding_gate.py`.
- [x] **T3** — GREEN: the retrieval step, the gate, the state keys, the graph wiring, the prompt
      rewrite. Route: delegated writer (same writer as T2).
- [x] **T4** — Persona and prompt contract: `agent/personas/assistant.md` and
      `agent/prompts/assistant_respond.md`.
- [x] **T5** — Spec delta: **IAC-14 — Grounded Knowledge Responses** in
      `openspec/specs/internal-agent-chat/spec.md`, with three scenarios.
- [x] **T6** — Verify. See "Verification evidence" below.
- [x] **T7** — Record committed (`b0464fc3`), branch pushed, **PR #299** open against `main` with the
      single label `type:feature`; CI green (`test` + GitGuardian). **The merge remains the human's
      decision.**

## Pinned contract (T1)

Mirrored from `app/chat/nodes/respond.py:129-150`, read directly:

- **Retrieval call**: `kb.retrieve(session, text, top_k=kb.DEFAULT_TOP_K, min_sim=kb.DEFAULT_MIN_SIM, audience=None)`
  - `kb.DEFAULT_TOP_K = 5`, `kb.DEFAULT_MIN_SIM = 0.50` (`app/services/kb.py:39-40`).
  - `audience=None` — an internal operator sees the whole KB. This matches what the existing
    `kb.retrieve` tool already passes (`app/chat/assistant/tools/registry.py:241`).
- **Only non-empty chunks reach the answer** — the customer chat's rule, kept verbatim.
- **On the miss**: deterministic, no LLM call. The customer chat additionally calls `log_unresolved`
  and sets `escalate=True` with reason `kb_miss`. The panel has no human escalation queue on this
  path, so the panel path stops at the deterministic clarification and does **not** set `escalate`.
  The missing-evidence fact is still recorded through the existing evidence channel.
- **Copy decision**: the customer `cannot_answer` default (`app/services/settings.py:52-55`) is
  customer-register — "Un asesor de Lumat revisará tu consulta y te contactará" — and is wrong for an
  operator panel. Decision: a panel-specific declared constant in neutral Spanish, operator register.
  Making it configurable through the `messages.<key>` surface is a **declared follow-up**, not part of
  this unit.

## Outcome

The panel assistant now grounds knowledge answers on retrieved evidence. A non-social `respond` turn
retrieves from the knowledge base before answering; an empty retrieval ends the turn in a
deterministic clarification with no model call; a non-empty retrieval reaches the responder as a
bounded `<kb>` block that the prompt requires it to answer from. Tool turns and short social messages
keep their previous behavior. The canonical spec carries the contract as IAC-14.

Four commits on `odd/assistant-grounding-gate`, unpushed:

| Commit | Subject | Scope |
|---|---|---|
| `6551750c` | `feat(assistant): gate knowledge answers on panel retrieval` | gate, state keys, graph wiring, unit tests, the three pre-existing suites the contract required |
| `5189a192` | `docs(assistant): declare panel grounding contract` | prompt and persona |
| `74afcbb7` | `test(assistant): cover grounded respond plans` | integration coverage |
| `a7f05065` | `docs(spec): require grounded panel answers` | IAC-14 |

## Verification evidence

- **Full suite, run by the orchestrator after the writer's scoped runs missed the blast radius**:
  `uv run pytest tests/` -> **1194 passed, 0 failed** (~2m40s).
- Independent measurement of the exemption, run by the orchestrator against the real function:
  **19 short social messages exempt, 11 knowledge questions not exempt, 0 failures** — including
  `buenos dias`, `muchas gracias` and `chau` (all three were false negatives in the first delivery)
  and `hola, cuales son las tarifas`, `gracias, dame las tarifas` and `cual es el guion para responder
  un reclamo` (the P9 false positive) on the not-exempt side.
- Commits verified one by one with `git show --stat`: each message matches its content.

### Corrections applied during the unit

1. **Exemption false negatives.** The first delivery's `_SOCIAL_WORDS` held `"buenas"` but not
   `"buenos"`, `"adios"` but not `"chau"`, `"gracias"` but not `"muchas"` — so `buenos dias`,
   `muchas gracias` and `chau` hit the refusal. Caught by measuring the function against real
   phrasings, not by reading the tests. The lexicon was broadened and table tests added in both
   directions.
2. **Blast radius the scoped run missed.** `uv run pytest tests/` found 3 failures the assistant
   suites did not: `test_h4_chat.py::test_admin_thread_and_message_are_persisted_and_audited`,
   `test_agent_chat_realtime.py::test_internal_chat_uses_sse_preview_instead_of_realtime_tokens`,
   `test_agent_chat_realtime.py::test_token_delivery_failure_does_not_change_persisted_post_contract`.
   All three exercised streaming, delivery, persistence and audit while relying on the old ungrounded
   synthesis. Fixed by seeding retrieval evidence, exactly as `test_assistant_chat.py` already did;
   none of their real assertions were weakened. **Lesson: a green scoped subset is not evidence that
   the branch is green.**

## Declared consequences (accepted by the human)

**The gate is KB-only, and it classifies every non-social `respond` turn as a knowledge question.**
The panel assistant also answers questions whose evidence is not in the knowledge base — most
notably questions about its own declared capabilities and tools (the `<available_tools>` inventory
delivered by PR #4056) and questions about the thread or panel state.

Consequence, measured: `_is_conversational_turn("que herramientas tenes")` is `False`, so the turn
runs `guardrails -> retrieve_kb -> empty -> grounding_refusal -> END`. In production a capability
question therefore gets the deterministic refusal unless the knowledge base happens to hold a
matching chunk.

- No chat-level test covers that question, which is why the suite did not catch it. It was found by
  measuring the exemption against real phrasings and reading the gate path.
- The human accepted this cost on 2026-09-22 with the evidence above, rather than re-scoping the unit.
  The alternatives were exhausted: a planner-declared signal was rejected on the #4574 evidence (the
  panel planner never produced a valid plan in production), and pattern-based detection was rejected
  on the P9 evidence (word triggers are brittle).
- **This is the item to revisit first if the panel assistant starts refusing questions it should
  answer.** The evidence needed is real usage: which turns hit the refusal, and which of those an
  operator expected an answer to.

## Process deviations

- The gate commit holds **7 files**, above the project's `<=5` guidance. It is one concern, and
  splitting it would leave a commit with a red suite, which is worse for bisect than a slightly wide
  commit.
- The delegated writer ran a full graph rebuild mid-unit; the project policy is `--update` once at
  session close. `graphify-out/` is gitignored, so it does not affect the artifact.

## Progress

- 2026-09-22 — unit opened. Worktree `odd/assistant-grounding-gate` created from `origin/main`
  `e340266d` with explicit human consent. Environment provisioned (`infra/.env`, `uv sync`, test DB
  healthy on `localhost:5741`). Baseline measured: 211 green.
- 2026-09-22 — T1-T6 complete. Full suite 1194 green. Two corrections applied. Consequence declared
  and accepted. Four commits on the branch, unpushed.

## Graph nodes/edges consulted

- `assistant/graph.py` (graph node, `GRAPH_REPORT.md:94`)
- Panel flow edge: `assemble_context -> panel_cost_gate -> plan_llm -> execute -> record_usage`
  (`GRAPH_REPORT.md:711`)
- `graphify query "panel assistant grounding"` — 183 nodes, truncated at 59
- `graphify query "assistant evidence tool result responder"` — 204 nodes, truncated at 37
- `graphify path "kb.retrieve" "collect_evidence"` — **no directed path**; undirected path exists
  only through `contains` / `imports_from` (module containment, not a call)
- `graphify path "respond_stream" "collect_evidence"` — **no directed path**

## Next step

Delivery is complete up to the PR: **#299** is open, CI green, reviewed and acknowledged. The merge
is the human's decision under ordinary repository policy. If the panel assistant starts refusing
questions it should answer, revisit the declared consequence above first.
