# ODD: assistant-responder-tool-inventory

## Objective

Give the panel assistant's response writer the same declared tool inventory the planner already
receives, so the assistant states the capabilities it actually has instead of denying them.

## Problem

An admin asked the panel assistant "hey chat que herramientas tienes disponible?" and the agent
answered that no executable tool was declared in that context, and that no memory tool was
available either. At the same time the panel's operational context sidebar reported
"Herramientas disponibles: 19" and "Memoria: Disponible", read from the same registry. The
configuration and the prompt the response writer receives disagree, and the user sees both.

## Why — root cause (verified, not inferred)

There are two independent read paths, and only one of them reaches the model that writes the reply.

1. The sidebar reads configuration, never the prompt. `GET /panel/api/assistant/capabilities`
   (`app/panel/api/routes/chat.py:241-261`) enumerates `registry.assistant.tools_whitelist` and
   derives `memory_available` with `any(name.startswith("memory."))`. The registry
   (`agent/registry.yaml:64-83`) declares 19 tools, including `memory.kpis` and `memory.read`. The
   panel renders those counts (`web/src/components/pages/AgentChat.tsx:849-853`). No LLM is
   involved, so a truthful sidebar cannot prove anything about the prompt.

2. The reply text is written by the `respond_stream` node, which is `execute()` in its
   respond branch (`app/chat/assistant/nodes.py:560-595`). Its user prompt is
   `agent/prompts/assistant_respond.md`, which declares exactly three slots — `user_input`,
   `tool_evidence` and `context` — and no `<available_tools>`. The replacement dictionary at
   `app/chat/assistant/nodes.py:567` supplies those three keys and nothing else. The writer never
   learns that any tool exists.

The planner does receive them: `app/chat/assistant/nodes.py:391` injects `available_tools` into
`agent/prompts/assistant_plan.md`, which declares the slot, and
`tests/unit/test_assistant_config.py:15` asserts it. But the planner only returns structured JSON
`{kind, tool, ...}`; for a capability question it correctly answers `kind: respond` (there is no
tool for self-listing) and leaves `response=None`
(`app/chat/assistant/nodes.py:421`). The text therefore comes from the responder, which has no
inventory.

The persona then produces the observed denial: `agent/personas/assistant.md` instructs
"Use only declared tools... never load or execute skills, modify registry files, or invent
undeclared capabilities". A model with no declared list plus a prohibition on inventing one denies
having any. The observed reply is close to a paraphrase of that constraint list.

Memory follows the same split: `_context_text()` (`app/chat/assistant/nodes.py:205-212`) appends
only `Conversation identity: scope=panel entity_id=thread:153`. That is why the agent could name
the scope and entity of its own thread and still deny having any memory tool: it sees the identity,
not the catalogue.

The previously merged work (`372a1b32` created the plan prompt with `available_tools`,
`a7abba4b` wired the production harness graph, `83eb25a5` gave the planner the memory identity)
feeds the planner only. Stale code was ruled out: the running `infra-api-1` container had been up
for three minutes on the current `main` when the reply was observed.

## Scope

**In:** declare the tool inventory as an `available_tools` slot of the responder prompt; inject the
declared `tools_whitelist` into that prompt at the respond boundary; add regression coverage that
fails without either half; record the implementation and the evidence.

**Out:** changing the planner prompt, the planner, the persona, the registry, or the tool
registry; touching `app/chat/nodes/respond.py` (the customer-facing WhatsApp responder is a
different flow with its own prompt contract); changing the capabilities endpoint or the sidebar;
adding a dedicated "list my tools" tool.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-assistant-responder-tool-inventory`
- Branch: `odd/assistant-responder-tool-inventory`
- Base: `10b49996`
- Files: `odd/tasks/assistant-responder-tool-inventory.md`,
  `agent/prompts/assistant_respond.md`, `app/chat/assistant/nodes.py`,
  `tests/integration/test_assistant_harness_guardrails.py`

## Constraints

- **Strict TDD: ON** — source: project configuration (`testing.strict_tdd: true`, runner
  `uv run pytest tests/`). Observe the new regression test fail before changing source, then
  observe it pass with no production edit beyond the two halves of the fix.
- Keep the fix to the responder boundary: one prompt slot and one injected value. Do not
  restructure the manual placeholder substitution, and do not extend it to the planner.
- The regression test must exercise the real prompt file and the real registry, so that either
  half going missing fails the test. Do not stub the responder prompt template.
- Do not touch the concurrent `odd/planner-validity-sentinel` worktree or its uncommitted changes.
- All artifacts are written in English.

## Tasks

- [x] **T1 — RED.** Add a regression test that drives the responder branch through `execute()` with
  a capturing fake client and asserts the declared `tools_whitelist` reaches the responder's user
  prompt. Observe it fail against the current source.
- [x] **T2 — GREEN.** Add the `<available_tools>{{available_tools}}</available_tools>` slot to
  `agent/prompts/assistant_respond.md` and inject
  `", ".join(config.tools_whitelist)` for it at the responder boundary. Observe the same test pass.
- [x] **T3 — Regression.** Run the assistant and prompt suites to confirm no other consumer of the
  responder prompt breaks.
- [x] **T4 — Evidence.** Record exact command output, the graph nodes consulted, and honest limits.

## Acceptance criteria

1. The responder's user prompt carries every name in the configured `assistant.tools_whitelist`.
2. The regression test fails when either the prompt slot or the injection is missing, and passes
   only when both are present.
3. No other prompt, registry entry, or tool definition changes.
4. Only the four authorized files change.
5. The assistant and prompt suites meet their established baseline.

## Checks

- `uv run pytest tests/integration/test_assistant_harness_guardrails.py -q`
- `uv run pytest tests/unit/test_assistant_config.py tests/unit/test_prompts.py -q`
- `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/unit tests/integration/test_assistant_chat.py tests/integration/test_assistant_harness_guardrails.py -q`
- `git status --short`
- `git diff --check`

## Decisions

- Fix the responder rather than teaching the planner to answer capability questions: the planner
  returns structured JSON and never writes prose, so its summary cannot answer the user. The
  inventory belongs where the answer is composed.
- Declare and inject the inventory explicitly instead of relying on the planner to relay it, so the
  responder's view of capabilities cannot drift from the registry the sidebar reports.
- Keep the existing manual placeholder substitution to hold this change to one concern; promoting it
  to the slot-checking `render()` helper is a separate refactor.
- Do not add a self-listing tool: YAGNI. The answer needs the inventory in context, not a new
  callable surface and a new approval path.

## Progress

- [x] Created this ODD record before the first source change.
- [x] T1 — RED observed and recorded.
- [x] T2 — GREEN applied: prompt slot plus injected inventory.
- [x] T3 — Regression: 194 passed, exit 0.
- [x] T4 — Evidence recorded.

## Verification evidence

| Check | Command | Result |
|---|---|---|
| RED (before the fix) | `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/integration/test_assistant_harness_guardrails.py -k tool_inventory` | **FAILED** — `AssertionError: assert 'customers.search' in '<user_input>which tools do you have</user_input>\n\n<tool_evidence></tool_evidence>\n\n<context></context>\n'` |
| GREEN (targeted) | `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/integration/test_assistant_harness_guardrails.py` | **PASSED** — 11 passed (10 pre-existing + the new regression) |
| Regression | `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/unit tests/integration/test_assistant_chat.py tests/integration/test_assistant_harness_guardrails.py tests/functional/test_api_assistant_capabilities.py` | **PASSED** — 194 passed, exit 0, wall time `75.37s` |
| Rendered prompt | `APP_SECRET=… DATABASE_URL=… uv run python -c "from app.services.prompts import load_assistant_config; …"` | Both halves agree: `<available_tools>` renders the 19 declared names, including `memory.kpis` and `memory.read`; the prompt declares all four slots |
| Working tree | `git status --short` | The three source files plus this record. Two untracked provisioning artifacts (`.opencode/tools/package-lock.json`, `.rapsodia-code/`) were left alone |
| Whitespace | `git diff --check` | **PASSED** — no output |

Honest limits:

- The regression test proves the inventory reaches the prompt. It does not measure the assistant's
  behaviour after the change; that needs a prompt-level check against a live provider, which was not
  run and is not claimed.
- `addopts = "-q"` in `pyproject.toml` means an extra `-q` on the command line produces `-qq` and
  suppresses the pass summary. The reported counts come from runs without the duplicate flag.
- The suite's autouse `clean_db` truncates the shared test DB before every test. The suites were
  pointed at `infra-db-test-1` (published on `localhost:5432`); the dev database the panel uses
  (`infra-db-1`) publishes no host port, so no panel data was touched.

**Graph nodes consulted (Graph Check, Step 1):** `assistant_respond prompt template`
(`agent/prompts/assistant_respond.md`), `Assistant Planner Prompt`
(`agent/prompts/assistant_plan.md`), `prompts.py` and `load_assistant_config()`
(`app/services/prompts.py`), `Assistant` and `load_registry()` (`app/agent_registry.py`),
`PlannerOutput` (`app/chat/assistant/state.py`), `assistant/state.py`, and the `Harness Lumat
Design` community. The BFS query also surfaced `respond()` in `app/chat/nodes/respond.py`, which
the graph distinguishes from the panel responder and which this change must not touch.

## Next step

The work unit is complete and verified on the branch. Not yet pushed and no PR opened: delivery is
the maintainer's call. The previously identified planner validity sentinel
(`app/chat/assistant/nodes.py`, `parse_planner_output` / `plan_llm`) is being handled separately in
the concurrent `odd/planner-validity-sentinel` worktree and is deliberately untouched here.
