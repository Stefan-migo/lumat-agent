# ODD: panel-memory-read-scope

**Branch**: `odd/panel-memory-read-scope`
**Worktree**: `../lumat-agent-odd-panel-memory-read-scope`
**Base**: `515b755b` (= `origin/main` at branch time)
**Status**: merged — PR #287 (`be84dd5a`). Implemented and verified end to end; native review approved and its authority burned.
**Source**: Engram #4598 (`handoff/panel-memory-read-scope`), the single entry point left by the session
that merged #279, #282, #284 and #286. This is the fifth defect of the same class.

## Objective

Make the `memory.read` / `memory.search` scope-and-entity contract **announced and enforced from the
same declaration**, so a read plan the planner can derive from the schema is also a plan `guardrails`
accepts.

## Problem (measured, not inferred)

A panel read cannot be satisfied by following the prompt. `agent/prompts/assistant_plan.md:7` orders the
model to send the thread identity:

> Tools reading memory for the current conversation use `scope="panel"` and `entity_id="thread:<thread id>"`; `<context>` states that identity.

`_MemoryScopeArgs.validate_scope_entity` (`app/chat/assistant/tools/registry.py:78-95`) rejects exactly
that. Measured with `MemoryArgs.model_validate`, on this worktree, before any edit:

| Case | Source | Verdict |
|---|---|---|
| `scope="panel"` + `entity_id="thread:158"` | what the prompt orders | **REJECTED** |
| `scope="agent"` without `entity_id` | what the model chose in thread 158 | **REJECTED** |
| `scope="panel"` without `entity_id` | | accepted |
| `scope="agent"` + `entity_id="agent:default"` | | accepted |

Both accepted shapes require disobeying the prompt or knowing `tukulpan.agent_memory_entity(WRITABLE_PROYECTO)`
= `agent:default`, a server-side constant that appears **nowhere** the planner can read. Measured: the
planner catalog advertises `entity_id` as, in full,

```json
{"anyOf": [{"maxLength": 100, "type": "string"}, {"type": "null"}], "default": null, "title": "Entity Id"}
```

No scope rule, no agent value, nothing. And the prompt itself contradicts the context text it is
rendered next to: `_context_text` (`nodes.py:226-235`) prints `scope=panel (the panel memory read target
is derived server-side)` and the compaction cue (`nodes.py:245`) already says `scope=panel and no
entity_id`. Two code paths tell the truth; the prompt template tells the opposite.

Live evidence for the same defect, recorded in the handoff: a real panel turn on thread 158 produced
`{"kind":"tool","tool":"memory.read","arguments":{"scope":"agent","topic":"agent:test-memoria-conversacion","limit":5}}`
and `guardrails` rejected it, leaving `planner.failure.reason = unsafe_plan`,
`stage = guardrails`, `guardrails = {"decision":"fallback","whitelisted":true,"arguments_valid":false}`.

## Decisions

**A — the rule moves into a discriminated union, so one declaration both enforces and advertises.**
Chosen by the human after the fork was brought with the evidence above. This is the "conditional JSON
Schema" that the sibling unit #286 named in its own decision E as the follow-up this class of defect
requires: a cross-field rule (`scope` + `entity_id`) cannot be expressed as a `pattern`, and a
`model_validator` never reaches `model_json_schema()`.

Measured in advance, before implementing:

```
MemoryArgs = RootModel[Annotated[Union[PanelRead, CustomerRead, AgentRead], Field(discriminator="scope")]]
-> schema: {"$defs": {...}, "discriminator": {"propertyName": "scope", "mapping": {...}}, "oneOf": [...]}
-> AgentRead.entity_id  : {"const": "agent:default"}
-> PanelRead.entity_id  : {"type": "null"}
-> CustomerRead.entity_id: {"pattern": "^(?:customer:\\d+|\\d+)$"}
-> MemoryArgs.model_validate({...}).model_dump() unchanged in shape: scope, entity_id, topic, limit
-> "panel"+entity rejected, "agent" without entity rejected, "agent"+"agent:other" rejected,
   "customer"+agent entity rejected, "customer"+42 accepted
```

**B — the prompt line is corrected, not just the schema.** Announcing the rule while the prompt orders
the opposite shape would keep producing rejected plans. `assistant_plan.md:7` is rewritten to defer to
the schema and to state that panel reads omit `entity_id`.

**C — no relaxation.** Every rejection that exists today still rejects, and `panel` + any `entity_id`
still fails hard. Nothing is silently overridden. The rejected plan is not rescued; the plan the model
can now derive is accepted.

**D — the custom error messages are knowingly lost.** Pydantic emits a union tag mismatch instead of
"panel memory reads require the thread to be derived server-side". This is the same trade #286 took in
its decision D: `guardrails` swallows the exception into `arguments_valid: False` and `execute_tool`
wraps it into `invalid arguments for {name}`, so nothing user-facing reads the text.

**E — no prose in the schema, and no tool description change.** Repository convention from #286's
decision B: the argument contract belongs in the schema, and no tool states an argument constraint in
prose. The union carries the contract structurally; no `description` restates it.

**F — the prompt line must also name the axis mapping, and this was measured, not assumed.** The first
prompt rewrite stopped ordering the rejected shape but introduced a bias: with the real thread context,
the planner then read a **project-visible** memory as `scope="panel"` and got an empty result instead of
the entry. Measured against the real provider, 6 runs each, real context, same new schema:

| Line 7 wording | thread memory read | project memory read |
|---|---|---|
| first rewrite ("reads for the current conversation use `scope=panel`…") | panel 6/6 | **agent 4/6, panel 2/6** |
| candidate C1 (minimal, no mapping) | panel 6/6 | agent 4/6, panel 2/6 |
| candidate C2 (names the three axes) | panel 6/6 | **agent 6/6** |

The mapping *memory visibility -> read scope* was announced nowhere, so a valid plan could still land on
the wrong axis and return nothing. C2 announces it and is the shipped wording. Without this the fix
would trade a hard rejection for a silent empty read.

## Scope

- `app/chat/assistant/tools/registry.py` — the memory args declarations, the union, and the two handlers'
  attribute access.
- `agent/prompts/assistant_plan.md` — line 7.
- `tests/unit/test_memory_tool_axes.py` — the new contract coverage, and the `agent` canonical-entity
  message assertion.
- `tests/integration/test_assistant_harness_guardrails.py` — the read plan through `guardrails`.
- `tests/unit/test_assistant_tools.py`, `tests/unit/test_assistant_planner.py` — the two existing tests
  that pinned the flat schema (`properties.scope.enum`, `required == ["scope"]`, attribute access on the
  args model). They must move with the declaration: splitting them out would leave an intermediate commit
  with a red suite, and holding the prompt change back would leave a commit whose product is still broken.
  This is the one place this unit exceeds the repo's five-file commit guideline, by exactly one file.
- `odd/tasks/panel-memory-read-scope.md` — this record.

Nothing else. `guardrails`, the planner and responder prompts (other than line 7), the persona, the
tools other than `memory.read` / `memory.search`, and the write path are out of scope.

## Authorized scope

- Human-approved on 2026-09-21: option A of the fork, this unit and the worktree
  `../lumat-agent-odd-panel-memory-read-scope`.
- **Not in this unit:** handoff item 3 (an invalid plan disguised as a normal answer), the
  `"type": "json_object"` leak, and the write path.

## Constraints

- Strict TDD is active (`openspec/config.yaml` -> `testing.strict_tdd: true`), runner `uv run pytest`.
  RED must be observed before implementation.
- RDD is ON (global). Every commit is a review candidate; the consent envelope is answered by the
  **human**. The lineage is bound to **this worktree**.
- Two commits: `fix(...)` then `docs(odd): record ...`. Conventional commits, no AI attribution.
- `pyproject.toml` sets `addopts = "-q"` — do not add a second `-q`.
- `.opencode/tools/package-lock.json` is untracked noise from `rapso worktree create`; never commit it.

## Acceptance criteria

1. The planner catalog advertises the whole contract: for a whitelist containing `memory.read` and
   `memory.search`, the rendered `arguments` schema states the per-scope `entity_id` rule (`const` for
   agent, null for panel, the customer pattern for customer).
2. A read plan derived from the announced contract passes `guardrails` and reaches `execute` — the test
   goes through `guardrails`, not only through the args model.
3. The shape the prompt used to order (`panel` + `entity_id`) is still rejected by the trust boundary.
4. Every rejection that existed before still exists: `agent` without the canonical entity, `agent` with
   a wrong entity, `customer` with a non-customer entity, and an unknown scope.
5. The prompt no longer orders a shape the validator rejects.
6. The full suite is green, with the baseline and final counts both reported.
7. Empirical: after the change, a real read turn through the panel returns the memory content, measured
   against the real provider. This is the criterion the previous session learned the hard way: the suite
   was green and the read was broken anyway.

## Checks

```bash
eval "$(bash infra/test-db.sh env)"
uv run pytest tests/unit/test_memory_tool_axes.py
uv run pytest tests/integration/test_assistant_harness_guardrails.py
uv run pytest tests/
git diff --name-only   # only the files in Scope, and this record
```

## Baseline (measured before any edit, in this worktree)

```
uv run pytest tests/  ->  1119 passed, 2 warnings, 149.25s
```

Matches the handoff's `main` baseline at `515b755b`.

## Tasks

- [ ] **T1 — RED.** Contract coverage that fails against the current declaration and the current prompt:
      the catalog advertises the per-scope rule, and a plan derived from it survives `guardrails`.
- [ ] **T2 — Declaration.** Replace the flat memory args models with the discriminated union and update
      the two handlers' attribute access.
- [ ] **T3 — Prompt.** Correct `assistant_plan.md:7` so it stops ordering the rejected shape.
- [ ] **T4 — Verify.** Focused files, then the full suite; counts reported.
- [ ] **T5 — Empirical re-check.** A real read turn through the panel against the real provider.
- [ ] **T6 — Review and record.** Native review, then the `docs(odd)` commit with the outcome.

## Progress

- [x] Graph Check before editing — `graphify query "assistant memory read scope entity validation and
      guardrails plan validation"` resolved `guardrails()` (`app/chat/assistant/nodes.py:515`),
      `get_tool()` / `tool_schemas()` (`app/chat/assistant/tools/registry.py:347,354`),
      `list_for_entity()` (`app/services/tukulpan.py:558`), `load_assistant_config()`
      (`app/services/prompts.py:144`) and `parse_planner_output()` (`nodes.py:171`). The community
      `test_assistant_planner.py` contains `guardrails()` and `plan()` together, which is the hop the
      unadvertised rule travels: `plan_llm` -> `_planner_tool_catalog` -> `definition.schema()`.
- [x] Worktree created and provisioned: `uv sync`, `infra/.env` copied, test DB up.
- [x] Baseline measured (above).
- [x] **T1 — RED.** Four new tests failed against the current declaration and prompt
      (`4 failed, 2 passed`): the schema advertisement in `test_memory_tool_axes.py`, the planner catalog
      advertisement, the prompt assertion, and the guardrails plan test, which failed with
      `AssertionError: the catalog announces no per-scope variant`. The two that passed are the
      fail-strong regression guard and the pre-existing `agent` canonical-entity test.
- [x] **T2 — Declaration.** `_MemoryScopeArgs` and its `model_validator` are gone; the read and search
      models are now `RootModel` wrappers over a discriminated union of three per-scope variants.
      `model_dump()` still returns the same flat dict, so approvals and downstream consumers are
      untouched; the two handlers read the fields through `args.root`.
- [x] **T3 — Prompt.** Line 7 rewritten. The first rewrite was corrected after the measurement in
      decision F.
- [x] **T4 — Verify.** `uv run pytest tests/` -> **1124 passed, 2 warnings** (baseline 1119, +5 tests).
- [x] **T5 — Empirical re-check.** Below.
- [x] **T6 — Review and record.** Below.

## Verification evidence

**The contract, before and after** (same measurement that opened the unit):

| Case | Before | After |
|---|---|---|
| `panel` + `entity_id="thread:158"` | REJECTED | REJECTED (fail-strong kept) |
| `agent` without `entity_id` | REJECTED | REJECTED (fail-strong kept) |
| `agent` + `entity_id="agent:other"` | REJECTED | REJECTED, now naming `agent:default` |
| `panel` without `entity_id` | accepted | accepted |
| `agent` + `entity_id="agent:default"` | accepted, value unknowable | accepted, value announced as `const` |
| `customer` + `42` / `customer:42` | accepted | accepted |
| `customer` + `agent:default` | REJECTED | REJECTED |

The advertised `entity_id` schema for the agent variant is now `{"const": "agent:default"}`, for panel
`{"type": "null"}`, and for customer `{"pattern": "^(?:customer:\\d+|\\d+)$"}`.

**End to end, real panel turns on thread 158 against the real provider** (`ASSISTANT_CHAT_MODEL`
= `deepseek-flash`). The dev volume carried the exact scenario from the handoff: memory id 1 written by
the agent at 21:57, and the failing read at 21:58.

| Turn | Result |
|---|---|
| 21:58, before the fix | plan `scope="agent"` with no `entity_id`, rejected, `unsafe_plan`. The responder refused honestly: "no voy a inventar ni reconstruir lo que diría la memoria" |
| 22:26, after the fix | planner produced `scope="panel"`, no `entity_id`; `guardrails.decision = "execute"`; evidence `memory.read completed` with `context_meta.entity_id = "thread:158"`; the reply quotes memory id 1 verbatim with its metadata |
| project axis, natural phrasing | "Recuperá lo que guardaste sobre la preferencia de facturación por email." -> returned memory id 2 (`scope: agent`, `entity_id: agent:default`, `visibility: project`) verbatim |

**Planner against the real provider, isolated, 3 runs each**: thread memory -> `scope=panel` 3/3;
project memory -> `scope=agent` + `entity_id=agent:default` 3/3. The second invisible rule is gone: the
model derives the canonical entity from the schema.

**Adjacent observation, not this unit.** After a successful turn, `assistant_state.planner.failure`
still holds the previous failed turn's diagnosis (stale key from the state merge) while `valid: true` and
`guardrails.decision: "execute"` describe the current one. The panel's own diagnostics therefore show a
failure that no longer applies. Same family as handoff item 3; not touched here.

## Review outcome

- Native review lineage `review-9d68348c050bbb3c`, one consolidated lens (`review-reliability`, order 0)
  because the candidate is `medium` risk: 6 changed files, 213 changed lines, correction budget 107.
- The consent envelope was relayed to the human and answered `granted`; the review ran over the frozen
  candidate tree `9b11b00c57ee6f7d523e0b5ef7e04d85b99d4ea2` with `--untracked-scope=exclude`, which keeps
  this record and the worktree's `package-lock.json` out of the reviewed bytes.
- Result: **approved, zero findings**.
- `authority: burned` on consumed revision
  `sha256:ba5a518f2aaff8f27958bd0deff72e49526d4e10eca7d131cc485dcb7af7ee8a`.
- The reviewed revision is the `fix(...)` commit below; this record is carried by the second commit.

## Delivery

Pending: push the branch, open the pull request, and wait for CI (`tests.yml`). No branch protection in
this repository, so CI is the gate. The dev stack (`infra-api-1`, `infra-db-1`) and the test DB container
are still up from the verification and must be torn down before the worktree is cleaned up.
