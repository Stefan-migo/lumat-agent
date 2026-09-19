# ODD: tool-name-honesty

## Objective

Delete the assistant tool names whose name misrepresents their handler, so the model-facing catalog
stops advertising capabilities that do not exist: `memory.kpis` (a dashboard-KPI reader wearing a
memory name, and an exact behaviour duplicate of `dashboard.summary`) and `appointments.list`
(advertises "appointments", can only ever return upcoming ones). The executable surface shrinks from
21 tools to 19.

## Problem

Verified read-only against `main` at `b38e33bd`.

**Defect class — the name lies about the handler (2 members).**

- `app/chat/assistant/tools/registry.py:338` registers
  `"memory.kpis": ToolDefinition("memory.kpis", KpiArgs, True, _kpis, "Read operational KPI totals.")`.
  `_kpis` (`registry.py:216-221`) delegates to `dashboard.compute_kpis(...)`, which returns contacts,
  motivos, derivados and visit_requests. It reads operational KPIs and never touches memory.
  `dashboard.summary` (`registry.py:342`) is the same handler with the same `KpiArgs` — two names for
  one behaviour, and the memory-flavoured one is false.
- `registry.py:335` registers
  `"appointments.list": ToolDefinition("appointments.list", AppointmentArgs, True, _upcoming_appointments, "List appointments.")`.
  `_upcoming_appointments` (`registry.py:202-205`) always computes `now`, fixes the range to
  `[today, today + 30d]`, filters `starts_at >= now` and truncates to `limit`. The name promises every
  appointment; the handler can only ever return upcoming ones. `appointments.upcoming`
  (`registry.py:334`) already exposes the same handler under an honest name.

**Consequence.** The planner receives `config.tools_whitelist` (`app/chat/assistant/nodes.py:402`)
and builds tool calls from the name plus a hand-written prompt hint. A `memory.kpis` entry tells the
model a memory-KPI capability exists. A plain `appointments.list` tells it past appointments are
reachable. Neither is true, and the model cannot see that from the catalog alone.

The same catalogue is also surfaced to administrators verbatim by
`GET /panel/api/assistant/capabilities` (`app/panel/api/routes/chat.py:246-254`), which serializes
`assistant.tools_whitelist` as `{name, description, read_only, write}`. The false entry was therefore
visible in the panel's assistant-capabilities view too, not only to the planner. (An earlier
reconnaissance note claimed no UI referenced these names; that was wrong — the names are not
hard-coded in `web/`, but they are serialized to the panel by this endpoint.)

### Not in this class (verified honest — leave them alone)

- `customers.search` / `customers.list` share `_search_customers` → `customers.search_customers`,
  documented "No query -> newest-first list" (`app/services/customers.py`).
- `conversations.search` / `conversations.list` share `_search_conversations` →
  `conversations.list_conversations`, which applies no filter when `query` is empty
  (`app/services/conversations.py`).

Their `.list` names are truthful aliases of a listing search, so they stay. Only the two names that
cross a domain or over-promise a scope are deleted.

## Why now

The `memory.kpis` misnomer is the next queued unit of the Tukulpan memory line (WU#8 in the WU#7
close-out). It is the smallest unit in that line, and it is a contract correctness problem rather
than a cosmetic one: the assistant can be told it has a memory-KPI tool that never reads memory. The
sibling `appointments.list` is the same defect class, costs two more lines, and was verified to have
no other consumer, so it is folded in rather than deferred to another chat.

## Binding constraints

- **AT-1** (`openspec/specs/assistant-tools/spec.md:9-11`) requires that the assistant "MUST NOT
  duplicate domain tools". `memory.kpis` duplicates `dashboard.summary`; deleting it moves the
  registry *toward* compliance. No spec text names either deleted tool (verified across
  `openspec/specs/`), so no spec delta is required — but the spec and integration suites must stay
  green.
- `app/agent_registry.py:31` derives `KNOWN_TOOLS = tuple(TOOL_REGISTRY)`, and the loader fails fast
  at `agent_registry.py:200-202` when a `tools_whitelist` entry is not in the known-tools set.
  `registry.py` and `agent/registry.yaml` MUST be edited together or every registry load raises.
- `agent/registry.yaml` `assistant.tools_whitelist` is the live executable surface and the source of
  the planner catalog. It is configuration, not documentation.
- Strict TDD is active (`openspec/config.yaml:38`, runner pytest). Observe RED before each source
  change; never invent RED evidence.

## Scope

**In:** `app/chat/assistant/tools/registry.py`, `agent/registry.yaml`, and the assistant tool tests.

**Out:** every other tool name and honest alias; the handler bodies (`_kpis`,
`_upcoming_appointments`); the surviving names `dashboard.summary` and `appointments.upcoming`; any
other module; the panel; the conversation brain; any spec text.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-tool-name-honesty`
- Branch: `odd/tool-name-honesty`
- Base: `b38e33bd`
- Files: `odd/tasks/tool-name-honesty.md`, `app/chat/assistant/tools/registry.py`,
  `agent/registry.yaml`, `tests/unit/test_assistant_tools.py`, `tests/unit/test_agent_registry.py`,
  `tests/functional/test_api_assistant_capabilities.py`

The last two were added to the authorized scope during implementation: both pinned the surface size
with a literal `21`, and both are a direct, mechanical consequence of this approved shrink. No other
file changed.

## Tasks

- [ ] **T1** — RED: in `tests/unit/test_assistant_tools.py`, add
  `test_memory_kpis_is_not_a_registered_tool`, `test_appointments_list_is_not_a_registered_tool` and
  `test_no_handler_is_shared_across_tool_domains`. All three must fail against the current code for
  the stated reason (the first two on the removed names, the third on `_kpis` carrying both the
  `memory` and `dashboard` domains). Record the observed failure output.
- [ ] **T2** — GREEN: delete the `memory.kpis` and `appointments.list` entries from
  `TOOL_REGISTRY` in `app/chat/assistant/tools/registry.py`.
- [ ] **T3** — GREEN: delete the `memory.kpis` and `appointments.list` entries from
  `assistant.tools_whitelist` in `agent/registry.yaml`. The registry must still load.
- [ ] **T4** — Run the focused suites, then the full suite. Record exact observed output.

## Acceptance criteria

1. `"memory.kpis"` and `"appointments.list"` are absent from both `TOOL_REGISTRY` and
   `assistant.tools_whitelist`.
2. `dashboard.summary` and `appointments.upcoming` remain registered, whitelisted and reachable
   through `execute_tool`.
3. The assistant registry still loads; the whitelist/known-tools fail-fast check passes.
4. Each deleted name has a regression test that fails against the pre-change code and passes after.
5. The full suite is green.
6. Only the authorized files change.

## Checks

- Focused: `eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/unit/test_assistant_tools.py tests/unit/test_agent_registry.py -q`
- Registry load: `eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/integration/test_assistant_harness_compatibility.py tests/integration/test_assistant_harness_guardrails.py -q`
- Full: `eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/ -q`
- `git status --short` / `git diff --check`

## Progress

- [x] Graph Check (Step 1): `graphify query "memory.kpis tool registry dashboard kpis"` →
  `Registry`, `registry.py`, `execute_tool()`, `get_tool()`, `ToolValidationError`,
  `unit/test_assistant_tools.py`, `agent_registry.py`. Edges walked: `registry.py → KpiArgs`,
  `registry.py → execute_tool()`, `agent_registry.py → Registry → load_registry()`.
- [x] Worktree created (`rapso worktree create tool-name-honesty`), `infra/.env` copied, `uv sync`,
  test DB up on host port `6369`.
- [x] T1 — added the three regression tests and observed the required RED failures below.
- [x] T2 — removed `appointments.list` and `memory.kpis` from `TOOL_REGISTRY`.
- [x] T3 — removed `appointments.list` and `memory.kpis` from `assistant.tools_whitelist`.
- [x] T4 — focused, integration and full suites green. Final full-suite result:
  `919 passed, 2 warnings in 482.91s (0:08:02)`. Base was 916 passing; the +3 is exactly the three
  new regression tests. The two literal count assertions were moved from 21 to 19.

## Evidence

### T1 RED

Command:

```text
eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/unit/test_assistant_tools.py tests/unit/test_agent_registry.py -q
```

Verbatim output:

```text
.FFF......................................................               [100%]
=================================== FAILURES ===================================
__________________ test_memory_kpis_is_not_a_registered_tool ___________________

    def test_memory_kpis_is_not_a_registered_tool():
>       assert "memory.kpis" not in TOOL_REGISTRY
E       AssertionError: assert 'memory.kpis' not in {'customers.search': ToolDefinition(name='customers.search', args_model=<class 'app.chat.assistant.tools.registry.Sear...d_only=True, handler=<function _search_conversations at 0x7f494d9aaae0>, description='List panel conversations.'), ...}

tests/unit/test_assistant_tools.py:37: AssertionError
_______________ test_appointments_list_is_not_a_registered_tool ________________

    def test_appointments_list_is_not_a_registered_tool():
>       assert "appointments.list" not in TOOL_REGISTRY
E       AssertionError: assert 'appointments.list' not in {'customers.search': ToolDefinition(name='customers.search', args_model=<class 'app.chat.assistant.tools.registry.Sear...d_only=True, handler=<function _search_conversations at 0x7f494d9aaae0>, description='List panel conversations.'), ...}

tests/unit/test_assistant_tools.py:42: AssertionError
________________ test_no_handler_is_shared_across_tool_domains _________________

    def test_no_handler_is_shared_across_tool_domains():
        handler_domains = {}
        for name, definition in TOOL_REGISTRY.items():
            handler_domains.setdefault(definition.handler, set()).add(name.split(".", 1)[0])

>       assert all(len(domains) == 1 for domains in handler_domains.values())
E       assert False
E        +  where False = all(<generator object test_no_handler_is_shared_across_tool_domains.<locals>.<genexpr> at 0x7f494d9aaae0>)

tests/unit/test_assistant_tools.py:51: AssertionError
=========================== short test summary info ============================
FAILED tests/unit/test_assistant_tools.py::test_memory_kpis_is_not_a_registered_tool
FAILED tests/unit/test_assistant_tools.py::test_appointments_list_is_not_a_registered_tool
FAILED tests/unit/test_assistant_tools.py::test_no_handler_is_shared_across_tool_domains
```

### T4 GREEN focused result

The focused command completed with one unrelated count assertion failure:

```text
...................................................F......               [100%]
=================================== FAILURES ===================================
_________ test_valid_registry_resolves_assistant_runtime_configuration _________

>       assert len(reg.assistant.tools_whitelist) == 21
E       AssertionError: assert 19 == 21
E        +  where 19 = len(('customers.search', 'customers.list', 'conversations.search', 'conversations.list', 'appointments.upcoming', 'cases.list', ...))
E        +    where ('customers.search', 'customers.list', 'conversations.search', 'conversations.list', 'appointments.upcoming', 'cases.list', ...) = Assistant(name='assistant', persona='personas/assistant.md', prompts={'plan': 'prompts/assistant_plan.md', 'respond': ...=('question', 'research', 'decision', 'continue', 'close'), planning_commands=('/planning <topic>', '/planning close')).tools_whitelist
E        +      where Assistant(name='assistant', persona='personas/assistant.md', prompts={'plan': 'prompts/assistant_plan.md', 'respond': ...=('question', 'research', 'decision', 'continue', 'close')) = Registry(orchestrator=Agent(name='orchestrator', persona='personas/orchestrator.md', skills=('sdb', 'emergency', 'hand...('question', 'research', 'decision', 'continue', 'close')).assistant

tests/unit/test_agent_registry.py:280: AssertionError
```

The two new registry tests passed. The count assertion is not pre-existing: at base `b38e33bd`,
`tests/unit/test_agent_registry.py` asserts the same expected count of 21 and the base registry
contains 21 whitelist entries and 21 `ToolDefinition` entries. The assertion now needs the intended
19-tool surface, but that existing test is outside the authorized three-test addition.

### T4 integration result

Command:

```text
eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/integration/test_assistant_harness_compatibility.py tests/integration/test_assistant_harness_guardrails.py -q
```

Verbatim result:

```text
..........................                                               [100%]
```

### T4 full-suite result (verification of record)

Command:

```text
eval "$(infra/test-db.sh env)" && uv run pytest tests/
```

Verbatim final line:

```text
919 passed, 2 warnings in 482.91s (0:08:02)
```

Base `b38e33bd` was 916 passing; the three new regression tests account for the difference exactly.
Two warnings are pre-existing and unrelated (a `_pytest.stash` coroutine warning and a fastembed
mean-pooling warning).

## Deviations and honest notes

- **Two additional test files entered scope.** `tests/unit/test_agent_registry.py:280` and
  `tests/functional/test_api_assistant_capabilities.py:36` each pinned the assistant surface with a
  literal `21`. Both were bumped to `19`. The reconnaissance missed them because the earlier search
  covered the tool *names*, not derived counts. They are a mechanical consequence of the approved
  shrink, not a change in behaviour.
- **Both counts are brittle by construction.** Any future addition or removal of an assistant tool
  will break the same two assertions. Not fixed here — that is a test-quality concern outside this
  unit's scope, recorded so it is not rediscovered from scratch.
- **The first full-suite attempt was aborted by host resource pressure, not by the code.** The
  delegated writer's run hit a 900000 ms wall-clock timeout, and a later run was killed outright with
  no traceback while the host had 14 GiB of 15 GiB in use with swap fully consumed. The suite is
  green on an unloaded host; neither `.venv` nor the test DB was implicated.
- **No spec delta.** AT-1 already requires that the assistant MUST NOT duplicate domain tools, and no
  spec text names either deleted tool. This change moves the registry toward that existing
  requirement rather than amending it.

## Next step

Human decisions, in order: authorize the commit, run the native RDD review on the committed
candidate, then push and open the PR. Nothing is committed, pushed or opened. The review switch
(`gentle-ai review mode status`) reads `on`, decided globally.

## Recovery

Resume with `mem_context`, then the project-scoped `mem_search` for this feature, then
`mem_get_observation` for the full document, then read this file.

## Status

Complete and verified. Implementation, regression tests and the full suite are green. The two
deletions are in place in both the registry and the whitelist. Awaiting the human commit decision.
