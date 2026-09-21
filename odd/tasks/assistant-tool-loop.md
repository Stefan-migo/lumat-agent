# ODD: assistant-tool-loop

**Branch**: `odd/assistant-tool-loop`
**Worktree**: `../lumat-agent-odd-assistant-tool-loop`
**Base**: `153c3275` (= `origin/main` at branch time)
**Status**: scoped — not started
**Reported by**: the owner, by hand, against the live dev panel (2026-09-21)

## Objective

Make the panel assistant answer after it runs a tool. Today, whenever the planner selects a tool, the
assistant produces **no language response at all** — the user sees the tool step and then silence. The
final answer is the literal string `Tool <name> completed.`

## Problem (verified against `153c3275`)

The reported symptom, reproduced live by the owner:

```
Administrador: hey chat tienes la memoria disponible ahora?
Agente Lumat: Tool memory.read completed.
Administrador: no me diste respuesta
Agente Lumat: Tool memory.read completed.
Administrador: respondeme sin usar la herramienta de memoria
Agente Lumat: Entendido. Te respondo solo con texto y sin usar la herramienta de memoria. ...
```

Asking for a text-only reply works, because that plan takes the other branch. Asking anything that
resolves to a tool produces silence.

### Root cause: the graph has no path back to the responder

`app/chat/assistant/graph.py` routes `guardrails` to exactly one of two nodes, and both are the **same
function** (`execute`) registered twice:

```
guardrails ──(plan.kind == "tool")──> execute_tool ──> evidence ──> END
            └─(otherwise)────────────> respond_stream ──> evidence ──> END
```

There is no edge from `execute_tool` back to `respond_stream`. The graph itself confirms it:

```
$ graphify path execute respond_stream
No directed path found between 'execute' and 'respond_stream'.
```

Inside `execute` (`app/chat/assistant/nodes.py:484-636`), the tool branch returns at line 560-565:

```python
return {
    "tool_result": result,
    "evidence": [make_evidence(tool=tool_name, status="completed", detail="Tool execution completed")],
    "response": f"Tool {tool_name} completed.",   # <- this is what the user reads
    "status": "completed",
}
```

The branch that actually calls the LLM in streaming mode lives at lines 566-636 and is reachable
**only** when `plan["tool"]` is falsy.

### Corroborating evidence: the prompt already declares the missing step

`agent/prompts/assistant_respond.md:7` declares:

```
<tool_evidence>{{tool_evidence}}</tool_evidence>
```

and `nodes.py:586` fills it with `str(state.get("tool_result") or "")`. But on the respond path
`tool_result` is still `None` — the node only sets it later, in its own return. **The prompt has a slot
for the tool result that can never be populated.** The design intended this loop-back and it was never
finished.

### Age and blast radius

- Introduced by `8f2bf7d6` (2026-09-09, `feat(assistant): gate automation tool execution`). It has never
  worked differently.
- **Not registered in any `odd/tasks/*.md`.** This is a new finding, not a re-open.
- **It affects every tool of the panel**, not only memory: `customers.search`, `customers.list`,
  `conversations.search`, `conversations.list`, `appointments.upcoming`, `cases.list`, `kb.retrieve`,
  `memory.read`, `memory.search`, `memory.write`, `dashboard.summary`, `web.search`, `project.*`,
  `automation.create_rule`.
- **It does NOT affect the WhatsApp bot**, which runs a different graph (`app/chat/nodes/respond.py`).
- It also explains why panel memory is a dead end: by decision D4 the panel reaches memory **only**
  through tool calls, and tool calls produce no answer.
- User-visible severity for the panel surface: **S1** (the operator cannot use any tool).

## Decisions (agreed — do not re-litigate)

| # | Decision |
|---|---|
| **D1** | The tool result is narrated by the **existing responder path**, not by a new ReAct planner loop. The `tool_evidence` slot already declares this intent, and the planner trust contract (`PlannerOutput`, `extra="forbid"`) stays untouched. |
| **D2** | The dispatch inside `execute` becomes **marker-based** (has a tool already run?), not plan-presence-based. Without this, re-entering the node re-runs the tool. |
| **D3** | **Only the success path gains the loop-back.** The `error` and `approval_pending` returns keep their current terminal responses. Minimal behavior change; narrating tool failures is a separate product decision. |
| **D4** | The evidence view renders `tool_result["result"]`, **not** the whole wrapper dict, as bounded human-readable text. `_plain()` (`registry.py:174`, applied at `registry.py:430-438`) already converts ORM rows, enums, datetimes, and nested containers to JSON-safe values, so the payload is already plain — reuse it, do not invent a second serializer. |
| **D5** | The prompt's tool statement must be **truthful in both states**. Today it says "this reply cannot invoke them", which is right with no tool and wrong once a tool has run. One prompt file, one slot carrying the correct statement for the current state. |
| **D6** | The DSML sanitizer (`ToolCallMarkupSanitizer`, decision D2/D3 of `dsml-responder-guard`) stays as-is. The new call is the same non-invoking, streaming call shape, so the same sanitization applies to the narration. |
| **D7** | The planner contract is **not** modified. No `PlannerOutput` field is added, and the planner prompt is untouched. |

## Authorized scope

- `app/chat/assistant/graph.py` — the routing edge.
- `app/chat/assistant/nodes.py` — the dispatch and the evidence rendering.
- `agent/prompts/assistant_respond.md` — the tool statement slot.
- `tests/unit/test_assistant_planner.py`, `tests/integration/test_assistant_harness_guardrails.py`,
  and one new focused test module — the RED/GREEN coverage.
- `odd/tasks/assistant-tool-loop.md` — this record.

## Out of scope (do not touch)

- The WhatsApp bot graph (`app/chat/nodes/`, `app/chat/graph.py`). Different product surface.
- The planner prompt or `PlannerOutput`.
- `_plain()`, `execute_tool()`, or the tool registry.
- Narrating tool **failures** (D3).
- Any frontend change: the panel already renders the response message and the tool step ("Actividad del
  agente"); it needs no change to display a real answer.
- Any test that currently pins the `Tool <name> completed.` string — **check first**; if one exists it is
  pinning the defect and must be corrected, not preserved.

## Implementation contract

1. **Exactly one tool execution per traversal.** A test asserts the handler side effect occurs once.
2. **The tool result reaches the model.** The narration LLM call receives the rendered tool evidence.
3. **The narration is the final `response`.** No intermediate placeholder may survive into the state
   returned by the graph or into the persisted message.
4. **Bounded evidence.** A large tool payload must not be passed through unbounded; the renderer caps it.
5. **No recursion.** There must be no path that can loop; the structure of the fix must make looping
   impossible, not merely unlikely.
6. **The no-tool path is unchanged.** Same prompt content, same sanitization, same behavior for
   `kind != "tool"`.
7. **Cost honesty.** This adds one LLM call per tool request (previously the tool path made none). Note
   it in the record; do not silently change the cost model.

## Tasks

- [ ] **T1 — RED.** Failing tests that encode acceptance 1-6 before any production edit:
      - the graph routes a completed tool to the responder;
      - the tool handler runs exactly once;
      - the final `response` is not `Tool <name> completed.`;
      - the rendered evidence is non-empty, human-readable, and bounded;
      - the responder prompt carries the correct tool statement in both states.
- [ ] **T2 — Dispatch + edge.** Marker-based dispatch in `execute`; the graph edge
      `execute_tool -> respond_stream`, terminal only for `error` / `approval_pending`.
- [ ] **T3 — Evidence rendering.** Bounded, readable rendering of `tool_result["result"]` into the
      `tool_evidence` slot (D4). Verify against a payload whose rows are ORM-derived.
- [ ] **T4 — Prompt slot.** The tool statement is correct with and without a tool result (D5).
- [ ] **T5 — Verify.** Focused tests, then the full suite; counts measured and reported.

## Acceptance criteria

1. Given a plan with `kind="tool"` whose tool completes, the final state's `response` is
   model-generated text reflecting the tool result, **not** `"Tool <name> completed."`.
2. The tool executes **exactly once** — no duplicate side effects and no duplicate audit rows.
3. `tool_evidence` is non-empty, human-readable, and bounded for a real read tool (verified against a
   payload derived from ORM rows; no `<... object at 0x...>` and no raw wrapper dict).
4. The responder prompt states the tool situation truthfully in **both** states.
5. No path can loop; a test proves a single traversal.
6. The existing no-tool respond path is unchanged, including DSML sanitization.
7. The full suite is green; the baseline is measured **before** any edit and both counts are reported.

## Checks

```bash
export PATH="$HOME/.local/bin:$PATH"
eval "$(bash infra/test-db.sh env)"
uv run pytest tests/                              # full suite
uv run pytest tests/integration/test_assistant_harness_guardrails.py tests/unit/test_assistant_planner.py
```

`pyproject.toml` sets `addopts = "-q"` — do not add a second `-q`. No linter, type checker, or formatter
exists; the tests are the verification.

## Baseline (measured before any edit)

```
uv run pytest tests/  ->  1046 passed, 2 warnings, exit 0, 102.25s
```

## Progress

- [x] Graph Check before editing — `graphify query` on the assistant area; `graphify path execute
      respond_stream` returns **"No directed path found"**, corroborating the root cause; `GRAPH_REPORT.md`
      god nodes read.
- [x] Worktree created and provisioned; `uv sync`; `infra/.env` copied; test DB up and migrated
      (through `029`); `.opencode/tools/package-lock.json` removed.
- [x] Baseline measured (above).
- [ ] T1-T5.

## Notes for the executor

- **Strict TDD is ON** (`openspec/config.yaml` → `testing.strict_tdd: true`), runner `uv run pytest`.
  RED must be observed before implementing.
- **RDD is ON (global).** Every commit is a review candidate. The consent envelope is answered by the
  **human**, never by the agent. The lineage is bound to **this worktree** — run review commands with
  process cwd = this worktree.
- `rapso worktree create` branched from `origin/main`, not the local `main`. Verify the base before
  writing it anywhere.
- The environment is already provisioned in this worktree. If starting fresh:
  `cp ../lumat-agent/infra/.env infra/.env` (it is gitignored), `uv sync` **before**
  `infra/test-db.sh env` (without a `.venv`, the suite reports ~791 false errors), and
  `infra/test-db.sh up` — `env` does **not** start the database.
- The review candidate **excludes untracked files**, so this record is deliberately outside the frozen
  bytes. Commit the code before the review preflight.
- Commits: conventional, **no AI attribution**. The repo separates the `fix(...)` from the
  `docs(odd): record ...` commit.
- Do not merge `main` into this branch before the PR if it breaks byte-identity with the reviewed
  candidate.
