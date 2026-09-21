# ODD: memory-write-topic-contract

**Branch**: `odd/memory-write-topic-contract`
**Worktree**: `../lumat-agent-odd-memory-write-topic-contract`
**Base**: `0e053d44` (= `origin/main` at branch time)
**Status**: implemented and verified; native review approved and its authority burned
**Source**: the measured follow-up from the planner root-cause work (Engram #4587) and the persona work
(Engram #4592). This is the last blocker for the owner's original scenario end to end.

## Objective

Make the `agent:` topic_key rule that `MemoryWriteArgs` enforces visible to the planner, so a memory
write plan is not rejected by a constraint the model has no way to learn.

## Problem (measured, not inferred)

`MemoryWriteArgs.validate_topic_namespace` (`app/chat/assistant/tools/registry.py:116-121`) requires
`topic_key` to start with `agent:`:

```python
    @field_validator("topic_key")
    @classmethod
    def validate_topic_namespace(cls, value: str) -> str:
        if not value.startswith("agent:"):
            raise ValueError("autonomous memory topic_key must start with agent:")
        return value
```

The planner never sees that rule:

- `_planner_tool_catalog` (`app/chat/assistant/nodes.py:421-429`) sends
  `{"name", "description", "arguments": definition.schema()}`.
- `ToolDefinition.schema()` (`registry.py:327-328`) returns `self.args_model.model_json_schema()`.
- A Pydantic `field_validator` **does not appear** in `model_json_schema()`. Measured:
  `"agent" in json.dumps(MemoryWriteArgs.model_json_schema())` is `False`, and `topic_key` is
  advertised only as `{"minLength": 1, "maxLength": 200, "type": "string"}`.
- Measured against the **real provider** with the owner's turn: 5 of 5 runs produced a `topic_key` of
  `test` or `test-memoria-panel`. `MemoryWriteArgs` rejects both, so the plan dies at `guardrails` as
  `unsafe_plan` and degrades to `bounded_fallback`.

And the prompt already points the model at the schema: `agent/prompts/assistant_plan.md:8` says to call
tools "with arguments satisfying their schema". The schema is the channel this contract is supposed to
travel through, and this rule is absent from it. `guardrails` therefore enforces a contract the planner
cannot learn.

## Decisions

**A — the rule moves into the field declaration as a `pattern`, replacing the `field_validator`.** One
declaration that both enforces and advertises, so the two cannot drift. Verified in advance:

```
topic_key: str = Field(min_length=1, max_length=200, pattern=r"^agent:")
-> schema: {"maxLength": 200, "minLength": 1, "pattern": "^agent:", "title": "Topic Key", "type": "string"}
-> "test" rejected, "agent:test" accepted
```

**B — no description change.** Repository convention: every tool description in `TOOL_REGISTRY` is a
single purpose sentence, and **no** tool states an argument constraint in prose. The argument contract
belongs in the schema. Restating it in the description would create a second source that can drift.

**C — no relaxation.** The `agent:` namespace stays required. This unit makes the rule learnable; it
does not remove it, and it does not widen what the assistant can write.

**D — the custom error message is knowingly lost.** The failure becomes a Pydantic pattern error instead
of "autonomous memory topic_key must start with agent:". Measured: no test pins the old message,
`execute_tool` wraps argument failures into `invalid arguments for {name}`, and `guardrails` swallows the
exception into `arguments_valid: False`. Nothing user-facing reads it.

**E — the sibling validator stays out of scope.** `_MemoryScopeArgs.validate_scope_entity`
(`registry.py:78-88`) is the same class of defect: it enforces scope/entity rules the schema cannot see.
It is a **cross-field** rule (`scope` + `entity_id`), so it needs conditional JSON Schema rather than a
pattern. Named here so it is not lost; not touched by this unit.

## Corroboration for the persona work (adjacent, not this unit)

The tool catalog already distinguished the autonomous write from the approval-gated ones:
`memory.write` is described as "Write memory to the current panel thread." while
`automation.create_rule` and the `project.*` writes say "**after approval**". The code and the catalog
agreed; only the persona contradicted them, which is what #284 fixed.

## Scope

- `app/chat/assistant/tools/registry.py` — the `topic_key` declaration.
- `tests/unit/test_memory_tool_axes.py` — the contract coverage.
- `odd/tasks/memory-write-topic-contract.md` — this record.

Nothing else. `_write_memory`, `guardrails`, the planner and responder prompts, the persona and the
other tools are out of scope.

## Authorized scope

- Human-approved on 2026-09-21: this unit and the worktree
  `../lumat-agent-odd-memory-write-topic-contract`.
- **Not in this unit:** the cross-field sibling rule, the `"type": "json_object"` leak, and handoff
  item 3 (the invalid plan disguised as a normal answer).

## Constraints

- Strict TDD is active (`openspec/config.yaml` -> `testing.strict_tdd: true`), runner `uv run pytest`.
  RED must be observed before implementation.
- RDD is ON (global). Every commit is a review candidate; the consent envelope is answered by the
  **human**. The lineage is bound to **this worktree**.
- Two commits: `fix(...)` then `docs(odd): record ...`. Conventional commits, no AI attribution.
- `pyproject.toml` sets `addopts = "-q"` — do not add a second `-q`.
- `.opencode/tools/package-lock.json` is untracked noise from `rapso worktree create`; never commit it.

## Acceptance criteria

1. `MemoryWriteArgs.model_json_schema()["properties"]["topic_key"]` advertises the `agent:` requirement.
2. A `topic_key` that does not start with `agent:` is still rejected.
3. A `topic_key` that starts with `agent:` is still accepted, including the `agent:fact` values the
   existing integration harness already writes.
4. The planner catalog actually carries it: the rendered catalog for a whitelist containing
   `memory.write` shows the constraint in the `topic_key` schema.
5. The full suite is green, with the baseline and final counts both reported.
6. Empirical: after the change, the planner against the real provider produces an `agent:`-prefixed
   `topic_key` for the owner's turn, where the baseline was 5 of 5 without the prefix.

## Checks

```bash
eval "$(bash infra/test-db.sh env)"
uv run pytest tests/unit/test_memory_tool_axes.py
uv run pytest tests/
git diff --name-only   # only registry.py, the axes test, and this record
```

## Baseline (measured before any edit, in this worktree)

```
uv run pytest tests/  ->  1108 passed, 2 warnings, exit 0, 147.03s
```

(`main` had moved past `53bbe320`; the baseline grew with the merge of #283.)

## Tasks

- [ ] **T1 — RED.** A test asserting the advertised contract: the `topic_key` schema in
      `MemoryWriteArgs.model_json_schema()` states the `agent:` requirement, and the rendered planner
      catalog carries it for `memory.write`. It must fail against the current declaration.
- [ ] **T2 — Declaration.** Move the rule into the field as a `pattern` and drop the `field_validator`.
- [ ] **T3 — Verify.** Focused file, then the full suite; counts reported.
- [ ] **T4 — Empirical re-check.** Run the planner against the real provider for the owner's turn and
      report the `topic_key` it now produces, compared against the 5-of-5 baseline without the prefix.
- [ ] **T5 — Review and record.** Native review, then the `docs(odd)` commit with the outcome.

## Progress

- [x] Graph Check before editing — `graphify query` on the memory write contract and the planner
      catalog resolved `MemoryWriteArgs` (`app/chat/assistant/tools/registry.py:108`, community
      `MemoryWriteArgs`) and `ToolValidationError` (`registry.py:32`, community `registry.py`).
      `graphify path "plan_llm()" "_planner_tool_catalog()"` -> **1 hop, `calls`**: the catalog is
      built inside `plan_llm`, so the unadvertised rule sits one hop from the prompt. `TOOL_REGISTRY`
      is a module-level mapping and is not a graph node.
- [x] Worktree created and provisioned: `uv sync`, `infra/.env` copied, test DB up.
- [x] Baseline measured (above).
- [x] **T1 — RED.** `test_memory_write_topic_key_contract_is_advertised_in_the_schema` and
      `test_planner_catalog_advertises_the_topic_key_contract` both failed with
      `AssertionError: assert None == '^agent:'`. The guard
      (`..._still_requires_the_agent_namespace`) passed before **and** after.
- [x] **T2 — Declaration.** The rule moved into the field as a `pattern`; the `field_validator` is
      gone and `field_validator` was removed from the `pydantic` import, since it had no other use in
      the module.
- [x] **T3 — Verify.** `uv run pytest tests/unit/test_memory_tool_axes.py` -> **6 passed**;
      `uv run pytest tests/` -> **1111 passed, 2 warnings** (baseline 1108, +3 new tests).
      `git diff --name-only` -> `app/chat/assistant/tools/registry.py` and
      `tests/unit/test_memory_tool_axes.py`.
- [x] **T4 — Empirical re-check.** Below.
- [x] **T5 — Review and record.** Below.

## Verification evidence — empirical re-check (T4)

The schema assertion proves the rule is advertised; it does not prove the model complies. Run against
the **real provider**, in this worktree, replaying the owner's turn with its real saved context:

The catalog the model receives now carries it:

```
{"maxLength": 200, "minLength": 1, "pattern": "^agent:", "title": "Topic Key", "type": "string"}
```

| | `topic_key` produced | Accepted by `MemoryWriteArgs` |
|---|---|---|
| Before (5 runs) | `test`, `test-memoria-panel` | **0 of 5** |
| After (5 runs) | `agent:test-memoria-panel` in 5 of 5 | **5 of 5** |

`plan.valid = true`, `kind = "tool"`, `tool = "memory.write"` in every run. The model derived the key
from the conversation and prefixed it on its own, which is what the schema constraint was supposed to
enable.

This closes the last blocker for the owner's original scenario: the write plan now validates at the
trust boundary **and** at `guardrails`, so it reaches `execute` instead of degrading to
`bounded_fallback`.

## Review outcome

- Native review lineage `review-1f54aa5dcf1f3e95`, one consolidated lens (`review-reliability`,
  order 0) because the candidate is `medium` risk: 2 changed files, 45 changed lines.
- Consent relayed to the human and `granted`; the review ran over the frozen candidate tree
  `741a23058450c6ad60c89914bdda14f425db84e5` with `--untracked-scope=exclude`.
- Result: **approved, zero findings**. The reviewer confirmed the namespace rule is preserved as a
  schema pattern and that the tests cover both advertisement and runtime acceptance/rejection.
- `authority: burned` on consumed revision
  `sha256:36552df20d54b8edc9d2966f6984a9d729ac9261fd332943b20391092fccd8c0`.
- The reviewed revision is the `fix(...)` commit below; this record is carried by the second commit.

## Follow-up, deliberately out of scope

`_MemoryScopeArgs.validate_scope_entity` (`app/chat/assistant/tools/registry.py:78-88`) is the same
class of defect: a cross-field rule (`scope` + `entity_id`) the planner cannot read from the schema.
It needs conditional JSON Schema rather than a pattern, so it is a different unit. Not measured this
session; named so it is not lost.

## Delivery

Human decision pending. The reviewed candidate is committed as the `fix(...)` commit; nothing has been
pushed and no pull request exists yet.
