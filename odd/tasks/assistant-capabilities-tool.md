# ODD: assistant-capabilities-tool

**Branch**: `odd/assistant-capabilities-tool`
**Worktree**: `../lumat-agent-odd-assistant-capabilities-tool`
**Base**: `d4b58554` (= `main` at branch time)
**Status**: in progress

## Objective

Give the panel assistant a read-only tool that reports its own declared capability inventory, so a
capability question ("que herramientas tienes disponible?") resolves as a normal `kind="tool"` turn with
deterministic evidence instead of the knowledge-base grounding refusal.

## Problem

The panel assistant cannot answer anything about itself. Measured on the running panel DB
(`infra-db-1`, `lumat`), thread 5, both turns:

```
31 | agent | No encontré evidencia suficiente en la base de conocimiento para responder con seguridad.
33 | agent | No encontré evidencia suficiente en la base de conocimiento para responder con seguridad.
```

Root cause, deterministic:

- `guardrails()` (`app/chat/assistant/nodes.py:551-553`): a plan whose `kind != "tool"` routes to
  `respond` only when `_is_conversational_turn()` is true, otherwise to `retrieve_kb`.
- `_is_conversational_turn()` (`nodes.py:534-540`) returns `False` for any text containing `?` or longer
  than 40 chars, so a capability question is always a "knowledge question".
- `retrieve_kb()` (`nodes.py:634-643`) finds no chunk about the assistant's own tools, sets
  `grounding_refusal`, and the graph ends at a static response (`graph.py:82-90`). **The responder node
  never runs.**

### This consequence was already declared and accepted — and the evidence it asked for now exists

`odd/tasks/assistant-grounding-gate.md:201-221` (merged as PR #299, `5f7d9033`) declared it in writing:

> The gate is KB-only, and it classifies every non-social `respond` turn as a knowledge question. ... In
> production a capability question therefore gets the deterministic refusal unless the knowledge base
> happens to hold a matching chunk. ... **This is the item to revisit first if the panel assistant starts
> refusing questions it should answer. The evidence needed is real usage.**

That document also recorded why the obvious alternative was rejected: a new field on `PlannerOutput`,
because "the panel planner never produced a valid plan in production" (Engram #4574). **That premise is
stale.** It described a specific bug — the model emits `"arguments": null` for a `respond` plan and the
model rejected it — whose root cause was found and fixed (`app/chat/assistant/state.py:47-53`,
`empty_arguments_for_null`). The same DB shows the planner executing valid tool plans today: threads 1-4
ran `memory.read`, `memory.write` and `project.find`.

So the option is now open, but this unit deliberately does **not** take it. See below.

## Why this shape

Add the inventory as a tool, not as a second evidence source in the gate:

- **The registry already exists for exactly this.** `ToolDefinition` is the declared statement of what the
  assistant can do; an inventory question is the registry's own subject matter.
- **The gate is untouched.** No reopening of the contract PR #299 just settled, no second evidence
  channel, no new exemption in `_is_conversational_turn()`, no new classifier.
- **Nothing new must be taught to the planner.** `_planner_tool_catalog()` already injects every
  whitelisted tool with its description into the planner prompt on every turn (`nodes.py:440-450`,
  `:457`). One accurate `description` is the only lever needed.

Rejected alternatives, with their evidence:

| Rejected | Why |
|---|---|
| Reopen the gate with a second authoritative source | It reopens a contract settled one day earlier and creates a new boundary to reason about: which questions the catalog may answer versus which remain KB-only. Not warranted while a tool solves it inside the existing mechanism. |
| Seed the catalog into the KB as a generated document | Retrieval is similarity-based (`hybrid_search`). "que herramientas tenes" does not reliably match a generated capability document, so the exact symptom returns intermittently. A deterministic source needs a deterministic route. |

### Accepted residual risk (declared)

The route depends on the planner choosing the tool. If the planner still plans `kind="respond"`, the turn
refuses exactly as today. There is **no** guarantee at the gate level, and this unit does not add one.
That is the honest cost of not touching the gate. The mitigation is the tool `description`, which is the
same lever every other tool relies on.

## Contract

### Tool entry

```
name:        assistant.capabilities
read_only:   True
args:        CapabilitiesArgs  (no fields, extra="forbid")
description: must state that it lists the assistant's own declared tools, so the planner selects it for a
             capability question. This string is the only steering the planner gets.
```

### Handler

Reads the **same** whitelist the planner sees — `load_assistant_config().tools_whitelist` — and, for each
name, `TOOL_REGISTRY.get(name)` -> name, description, and whether it is read-only.

**Return shape is pinned to avoid a silent truncation trap.** `_plain()`
(`app/chat/assistant/tools/registry.py:224-226`) truncates every dict to `MAX_ITEMS` items and every list
to `MAX_ITEMS` items, and `MAX_ITEMS = 20` (`registry.py:21`).

Measured on this branch's base (`d4b58554`, `main`): the assistant whitelist holds **19** entries before
this change and **20** after — so at exactly 20 a list shape would *not* truncate yet, and the trap is
**latent** here, not active. It becomes immediate one merge away: the sibling branch
`odd/memory-correction-tools` adds `memory.update` and `memory.delete` (21 entries on its own), and this
change on top of it makes 22. A 22-element list would silently drop two tools — the same class of
under-reporting bug this unit exists to fix. The handler therefore never returns a list, and the unit test
models the post-merge count by monkeypatching the whitelist past the bound rather than asserting against
today's 20.

Therefore the handler returns:

```python
{
    "tool_count": <int>,                       # exact number of whitelisted tools
    "capabilities": "<one line per tool>",     # newline-joined text
}
```

Two top-level entries, so no dict truncation; `_plain` passes a `str` and an `int` through unchanged. The
text is bounded inside the handler by a handler-owned constant
`CAPABILITIES_TEXT_LIMIT = 4_000`, matching `_TOOL_EVIDENCE_LIMIT` (`nodes.py:37`).

Line format: `name — description (read-only|write)`.

The whitelist is the visibility boundary, so the handler filters by it: a registry entry that is not
whitelisted must not appear in the output.

### Persona

`agent/personas/assistant.md` currently says knowledge answers come only from `<kb>` and that the assistant
must never "invent undeclared capabilities". Under an unqualified reading, that rule refuses a capability
answer that arrives as tool evidence. Add a **narrow, explicit** allowance: the assistant may describe the
tools it actually declares, and only those — sourced from the tool result, not from memory. This is not a
loosening of the KB rule for business questions.

**Do not disturb the phrases `tests/unit/test_assistant_config.py` pins**:
`already authorized and runs without asking`, `ask for approval before any write operation`,
`Every other write stays`/`Every other write still needs approval`, `except`. The previous unit in this
series lost one of these to a persona rewrite and only the full suite caught it.

## Scope

### In scope

| File | Change |
|---|---|
| `app/chat/assistant/tools/registry.py` | `CapabilitiesArgs`, `_assistant_capabilities`, `CAPABILITIES_TEXT_LIMIT`, the `ToolDefinition` entry |
| `agent/registry.yaml` | `assistant.capabilities` in `assistant.tools_whitelist`, appended last (19 -> 20 on this base) |
| `agent/personas/assistant.md` | the narrow declared-capability allowance |
| `openspec/specs/assistant-tools/spec.md` | new requirement **AT-12** (AT-1..AT-11 are taken) |
| `tests/unit/test_assistant_tools.py` | args model, completeness, non-truncation, whitelist filtering, bound |
| `tests/integration/test_assistant_harness_guardrails.py` | read-only turn needs no approval; the stale tool-count comment (`:296-302`) |
| `odd/tasks/assistant-capabilities-tool.md` | this document |

### Out of scope

- Any change to `guardrails()`, `retrieve_kb()`, `_is_conversational_turn()`, `PANEL_GROUNDING_REFUSAL`,
  `graph.py`, or the refusal contract.
- Any change to `MAX_ITEMS` or to `_plain()`. The handler works within the existing bound instead.
- The catalog payload format and lazy/on-demand loading. Measured separately: of the 9,670-char catalog,
  **8,156 chars (84%, ~2,039 tokens) are argument JSON Schemas** and only 1,514 chars (~378 tokens) are
  names plus descriptions. That is a cost lever, not this unit's concern, and it carries a real
  argument-accuracy tradeoff that must be measured before it is adopted.
- A human surface in the panel for the inventory.
- Guaranteeing the planner picks the tool.

## Tasks

- [x] **T1 — RED.** Failing tests first: `CapabilitiesArgs` rejects any field; the handler returns one line
  per whitelisted tool; `tool_count` equals `len(whitelist)`; the output is **not** truncated at
  `MAX_ITEMS` (assert the count is greater than 20 and equals the whitelist length, never a hardcoded
  number); a registry entry absent from the whitelist is excluded; the text respects
  `CAPABILITIES_TEXT_LIMIT`; the harness executes the tool without approval because it is read-only.
  *Check:* exact command and verbatim failure output recorded.
- [x] **T2 — GREEN.** Args model, handler, registry entry, whitelist.
  *Check:* the RED tests pass; every other tool is unchanged.
- [x] **T3 — Persona.** The narrow declared-capability allowance, with the pinned phrases intact.
  *Check:* `tests/unit/test_assistant_config.py` passes unedited.
- [x] **T4 — Spec.** `AT-12` in the file's existing shape (RFC 2119, `#### Scenario:` GIVEN/WHEN/THEN).
  *Check:* scenarios cover completeness (no truncation), whitelist filtering, the read-only/approval
  behaviour, and that the KB rule for business questions is unchanged.
- [x] **T5 — Full suite.** `1282 passed, 2 warnings`.

## Constraints

- **Strict TDD** (`openspec/config.yaml:38`). Observed RED before implementation, then GREEN.
- One concern per commit, work-unit commits on `odd/assistant-capabilities-tool`. Conventional commits.
  No `Co-Authored-By` and no AI attribution.
- English artifacts.
- Do not weaken any existing assertion to make the change fit.
- Ponytail after the code exists: report findings, never remove authorized behaviour.

## Checks

```
cp ../lumat-agent/infra/.env infra/.env
bash infra/test-db.sh up
eval "$(bash infra/test-db.sh env)" && uv run pytest tests/    # derived port, not 5432
```

- Focused: `uv run pytest tests/unit/test_assistant_tools.py tests/unit/test_assistant_config.py`
- Harness: `uv run pytest tests/integration/test_assistant_harness_guardrails.py`
- Full suite: ~2 minutes; pass an explicit long timeout to the shell.
- The repo has no linter, typechecker, pre-commit or hooks. The tests are the verification.

## Acceptance criteria

1. The assistant has a read-only tool that reports every tool in its own declared whitelist.
2. The report is complete: `tool_count` equals the whitelist length, and nothing is lost to the
   `MAX_ITEMS` bound.
3. A capability question can resolve as a `kind="tool"` turn with deterministic evidence, with the gate,
   the refusal contract and every other tool behaviourally unchanged.
4. The persona permits describing declared tools without loosening the KB rule for business questions,
   and the pinned persona phrases survive.
5. Spec `AT-12` carries the contract and the full suite is green.

## Production evidence

Read from the running panel DB on 2026-09-22 (`infra-db-1`, `lumat`), threads 1-5 by user `1`:

| Thread | Observed |
|---|---|
| 5 | `que herramientas tienes disponible?` twice; both answered with the KB grounding refusal |
| 3, 4 | further refusals on non-tool turns (`id=14`, `id=20`) |
| 1-4 | tool turns answer correctly from tool evidence with an empty `<kb>` — so the responder is not the blocker, the routing is |

## Declared considerations

### Whitelist position is prompt position (corrected)

`_planner_tool_catalog()` iterates `config.tools_whitelist`, so the YAML order **is** the order of the
catalog injected into the planner prompt on every turn. The first delivery appended the new tool at the
top of the list, which reorders the planner prompt for **every** turn to lead with a cheap, universal,
no-argument tool — a plausible source of over-selection, and a larger behavioural delta than the change
needs. Corrected: `assistant.capabilities` is appended **last**, which keeps the existing tool grouping
intact and minimises the prompt delta. `TOOL_REGISTRY`'s own dict position is irrelevant: the catalog is
built from the whitelist, and every consumer of the registry either looks up by name or sorts.

### The responder prompt was deliberately not changed

`agent/prompts/assistant_respond.md` carries the same "answer only from `<kb>`" rule as the persona, and it
was **not** given the capability allowance — only the persona was. This is deliberate, not an omission:
on a tool turn the responder receives the tool statement *"A panel tool has already run for this request.
Use its evidence to answer with text only"*, which already directs it to the tool result. Production
confirms it: threads 1-4 answered correctly from tool evidence with an empty `<kb>` (for example thread 3
returned a memory table). If a capability turn ever refuses despite the tool evidence, this is the second
place to look — and that would be measured, not assumed.

## Verification evidence

The worktree started without `infra/.env`, so the same recipe as the sibling unit applied:
`cp ../lumat-agent/infra/.env infra/.env`, `bash infra/test-db.sh up`, then
`eval "$(bash infra/test-db.sh env)" && uv run pytest tests/`.

- **Focused (delegated writer):**
  `uv run pytest tests/unit/test_assistant_tools.py tests/unit/test_assistant_config.py tests/unit/test_agent_registry.py`
  -> `67 passed in 0.68s`.
- **Full suite (delegated writer):** `1282 passed, 2 warnings in 133.91s`.
- The registry-derived tests (`tests/unit/test_agent_registry.py`,
  `tests/functional/test_api_assistant_capabilities.py`) needed **no** edit and passed without changes.
- The truncation test does not assert against today's 20 entries. It monkeypatches the whitelist to 21 by
  registering a synthetic tool, which models the post-merge count and would fail against a list-shaped
  return. That is the honest way to cover a latent bound.

### RED limitation (declared)

The observed RED was import-level, not behavioural:

```
ImportError: cannot import name 'CAPABILITIES_TEXT_LIMIT' from 'app.chat.assistant.tools.registry'
```

Same honest floor as its sibling unit: for a new public symbol the test module cannot execute at all
before the symbol exists. No behavioural RED is claimed because none was observed.

### Correction applied during the unit

1. **Whitelist position** — moved from first to last, with the reasoning recorded above.
2. **My own error in this document**, found by the writer and corrected here: the contract originally
   claimed the whitelist went 21 -> 22. That was wrong. This worktree's base is `main`, which does **not**
   yet carry `odd/memory-correction-tools`, so the real count is 19 -> 20. The writer refused to invent a
   tool to satisfy the claim and reported it as `partial` instead. That is the correct behaviour and the
   design conclusion (never return a list) survives intact — the bound becomes active at 21.

## Progress

- 2026-09-22 — root cause measured and reported; the declared consequence in `assistant-grounding-gate`
  was confirmed as this exact item, and its rejected alternative was shown to rest on a stale premise.
- 2026-09-22 — route chosen by the human: a read-only tool (option A), not a gate change.
- 2026-09-22 — worktree created with explicit human consent:
  `../lumat-agent-odd-assistant-capabilities-tool`, branch `odd/assistant-capabilities-tool`, base
  `d4b58554`.
- 2026-09-23 — T1-T5 by the delegated writer: `9443de8d` (RED), `b739900f` (tool + whitelist),
  `4909882a` (persona, AT-12, this document), `c285052e` and `e507a173` (bound coverage and cleanup).
  Full suite green. Writer reported `partial` for the count discrepancy rather than papering over it.

## Next step

Delivery is not taken. Nothing pushed, no PR. Commit, push and PR are the human's decisions under
ordinary repository policy.

## Graph nodes/edges consulted

- `graphify query "assistant tool registry planner catalog injected every turn"` — `TOOL_REGISTRY`,
  `_planner_tool_catalog()`, `ToolDefinition`, `execute_tool()`
- `graphify query "panel assistant grounding refusal gate"` — `guardrails()`, `retrieve_kb()`,
  `PANEL_GROUNDING_REFUSAL`, `graph.py`
- Edge: `plan_llm` -> `_planner_tool_catalog` -> `TOOL_REGISTRY`; edge: `guardrails` -> `retrieve_kb` ->
  `grounding_refusal` -> `END`
- Writer recon: `registry.py` (`TOOL_REGISTRY`, `ToolDefinition`, `execute_tool`, `plan_llm`,
  `load_assistant_config`); `registry.yaml` (`Assistant`, `load_registry`, `load_assistant_config`);
  `guardrails -> retrieve_kb` returned **no directed path**.
