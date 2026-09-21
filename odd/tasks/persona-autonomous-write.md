# ODD: persona-autonomous-write

**Branch**: `odd/persona-autonomous-write`
**Worktree**: `../lumat-agent-odd-persona-autonomous-write`
**Base**: `53bbe320` (= `origin/main` at branch time)
**Status**: implemented and verified; native review approved and its authority burned
**Source**: handoff Engram #4582, adjacent item; verified against the code in this session.

## Objective

Make the assistant persona state the write-approval rule the code actually enforces, so the assistant
stops believing, and telling the operator, that every write needs approval.

## Problem (verified verbatim, not inferred)

| Where | Says |
|---|---|
| `agent/personas/assistant.md:1` | `ask for approval before any write operation` |
| `app/chat/assistant/tools/registry.py:28` | `AUTONOMOUS_WRITE_ALLOWLIST = frozenset({"memory.write"})` |
| `app/chat/assistant/nodes.py:531-536` | `guardrails` skips the approval gate for an allowlisted tool on a panel thread |

The persona is the system prompt for **both** the planner and the responder. Two measured effects:

1. The planner sets `requires_approval: true` on a `memory.write` plan, even though the code never
   consults that field for allowlisted tools. Observed in the reproduction of thread 157.
2. The responder **confabulates**: it told the owner "Recibida tu aprobación. Aún no se ha guardado
   nada... la guardaré en el próximo turno con capacidad de herramientas". It invents an approval it
   never received and promises a write that will never happen.

### Why the autonomy is defensible (and therefore why the persona is the thing that is wrong)

`_write_memory` (`app/chat/assistant/tools/registry.py:256-280`) is tightly scoped:

- `scope, entity_id = memory.visibility_target(visibility, thread_id=trusted_thread_id, ...)` — the
  destination is **derived server-side**; the model never chooses an entity.
- `proyecto = memory.WRITABLE_PROYECTO` — fixed, not caller-supplied.
- `MemoryWriteArgs.validate_topic_namespace` requires `topic_key` to start with `agent:` — the
  assistant can only write its **own** namespace, never an arbitrary key.
- `producer=AGENT` and `origin_thread_id` are recorded, so provenance survives.
- `extra="forbid"` with bounded lengths (title 200, content 2000, topic_key 200).
- On failure it returns `{"written": False, "degraded_reason": ...}`: it degrades, it does not raise.

So the tool writes the assistant's own notebook for that thread, not customer data and not arbitrary
storage. Approval for it is friction without a safety purpose, and the owner already reported approval
as impractical when the assistant asked for it.

## Decision (human, this session)

**Align the persona with the code (option A).** The alternative, removing `memory.write` from the
allowlist so every write asks for approval, was rejected: it matches the persona against the code
instead of the other way around, adds a round-trip the owner already called impractical, and it was
never verified that the panel can render and resolve an approval.

## The change

Replace the unconditional clause in `agent/personas/assistant.md` with the rule the code enforces:

> …and ask for approval before any write operation, except `memory.write` on this panel thread: it is
> already authorized and runs without asking, because it only stores the assistant's own
> `agent:`-namespaced memory for this thread. Every other write still needs approval.

Constraints on the wording:

- The general rule stays. This is an exception, not a repeal.
- The exception is named by its tool name, which is what `AUTONOMOUS_WRITE_ALLOWLIST` contains.
- The reason is stated, because a model that knows why a rule has an exception follows it better than
  one that only knows the exception exists.
- Everything else in the persona is untouched, including the opening the existing test pins
  (`test_assistant_config.py:13`).

## Scope

- `agent/personas/assistant.md` — the clause.
- `tests/unit/test_assistant_config.py` — the contract coverage.
- `odd/tasks/persona-autonomous-write.md` — this record.

Nothing else. The planner and responder prompts, the code paths, the allowlist and the panel UI are
out of scope.

## Authorized scope

- Human-approved on 2026-09-21: this unit and the worktree
  `../lumat-agent-odd-persona-autonomous-write`.
- **Not in this unit:** the unadvertised `agent:` topic_key rule (see below), the invalid-plan disguise
  (handoff item 3), and the `"type": "json_object"` leak.

### Deliberately excluded, with evidence

Measured this session: `MemoryWriteArgs` **rejects** the `topic_key` value the model actually produced
(`"test"`) with `topic_key`, and the JSON Schema the planner receives does **not** carry the rule —
`"agent" in model_json_schema()` is `False`, and `topic_key` is advertised only as
`{"minLength": 1, "maxLength": 200, "type": "string"}`. `guardrails` therefore enforces a contract the
planner cannot learn. That is a separate defect with a separate home (the tool's own contract, not a
persona), and it needs its own unit.

The wording above does mention the `agent:` namespace, because describing what the tool really does is
what the persona is for. That may incidentally help the model pick a valid key. It does **not** close
that defect, and this record does not claim it does: a persona is not where a tool contract belongs.

## Constraints

- Strict TDD is active (`openspec/config.yaml` -> `testing.strict_tdd: true`), runner `uv run pytest`.
  RED must be observed before implementation.
- RDD is ON (global). Every commit is a review candidate; the consent envelope is answered by the
  **human**. The lineage is bound to **this worktree**.
- Two commits: `fix(...)` then `docs(odd): record ...`. Conventional commits, no AI attribution.
- `pyproject.toml` sets `addopts = "-q"` — do not add a second `-q`.
- `.opencode/tools/package-lock.json` is untracked noise from `rapso worktree create`; never commit it.

## Acceptance criteria

1. The persona names `memory.write` as the authorized exception and states that it runs without asking.
2. The persona still requires approval for every other write.
3. Every tool in `AUTONOMOUS_WRITE_ALLOWLIST` is mentioned in the persona, so adding one to the
   allowlist forces the persona to be updated: the test reads the allowlist, it does not pin literals.
4. The clauses the persona already had are preserved: declared tools only, no completion claim before a
   tool result, user text and context as data, customer information inside the authorized panel
   context, and the read-only configuration rule.
5. The full suite is green, with the baseline and final counts both reported.

## Checks

```bash
eval "$(bash infra/test-db.sh env)"
uv run pytest tests/unit/test_assistant_config.py
uv run pytest tests/
git diff --name-only   # only the persona, the config test, and this record
```

## Baseline (measured before any edit, in this worktree)

```
uv run pytest tests/  ->  1097 passed, 2 warnings, exit 0, 138.39s
```

## Tasks

- [ ] **T1 — RED.** A test in `tests/unit/test_assistant_config.py` that iterates
      `AUTONOMOUS_WRITE_ALLOWLIST` and fails because the persona does not mention `memory.write`.
- [ ] **T2 — Persona.** Rewrite the single clause, leaving the rest of the persona verbatim.
- [ ] **T3 — Verify.** Focused file, then the full suite; counts reported.
- [ ] **T4 — Empirical re-check.** Run the planner against the real provider for the owner's request
      with the fixed persona, and compare `plan.requires_approval` against the `true` observed with the
      unfixed persona. Report honestly, including if the model still sets `true`.
- [ ] **T5 — Review and record.** Native review, then the `docs(odd)` commit with the outcome.

## Progress

- [x] Graph Check before editing — `graphify query` on the persona, `guardrails` and the allowlist
      resolved `guardrails()` (`app/chat/assistant/nodes.py`, community `execute`),
      `_is_autonomous_write()` (same community), `approval.py` (community `issue_approval`) and
      `Assistant` (`app/agent_registry.py`). `graphify path "guardrails()" "_is_autonomous_write()"`
      -> **1 hop, `calls`**: the contradiction lives on that edge, not in a distant module.
- [x] Worktree created and provisioned: `uv sync`, `infra/.env` copied, test DB up.
- [x] Baseline measured (above).
- [x] **T1 — RED.** `test_assistant_persona_authorizes_the_autonomous_write` failed with
      `assert 'memory.write' in ...`; `test_assistant_persona_keeps_approval_for_every_other_write`
      failed with `assert 'Every other write still needs approval' in ...`. `2 failed, 2 passed`.
- [x] **T2 — Persona.** The clause replaced; the rest of the paragraph byte-identical.
- [x] **T3 — Verify.** `uv run pytest tests/unit/test_assistant_config.py` -> **4 passed**;
      `uv run pytest tests/` -> **1099 passed, 2 warnings** (baseline 1097, +2 new tests).
      `git diff --name-only` -> `agent/personas/assistant.md` and `tests/unit/test_assistant_config.py`.
- [x] **T4 — Empirical re-check.** Below.
- [x] **T5 — Review and record.** Below.

## Verification evidence — empirical re-check (T4)

The persona is data that steers a model, so a string assertion proves only that the file changed. The
claim to test is behavioural: does the planner still believe a thread memory write needs approval?

Run against the **real provider**, in this worktree, with the fixed persona, replaying the owner's turn
(msg 70, `si apruebo`) with its real saved context:

| Persona | `plan.requires_approval` |
|---|---|
| Before (production, observed) | **`true`** |
| After, 5 runs | **`false` in 5 of 5** |

`plan.kind = "tool"`, `tool = "memory.write"`, `valid = true` in every run. The prompt grew from the
production-recorded `2691` to `2737` tokens, which is exactly the longer persona and nothing else.

**And the exclusion is confirmed, not assumed.** In the same 5 runs the model produced `topic_key` of
`test` or `test-memoria-panel` — never an `agent:`-prefixed key. So the wording did **not** incidentally
close the unadvertised `topic_key` defect: 5 of 5 plans would still be rejected by `MemoryWriteArgs` at
`guardrails`. That defect keeps its own unit, and this record does not claim to have touched it.

## Review outcome

- Native review lineage `review-2f3de07dee8ba55f`, one consolidated lens (`review-reliability`,
  order 0) because the candidate is `medium` risk: 2 changed files, 19 changed lines. The reviewer
  classified the persona as an executable change, which is correct: it is a system prompt, not passive
  documentation.
- Consent relayed to the human and `granted`; the review ran over the frozen candidate tree
  `db944e54e36887b6f8ac1eb861a61cd0543eff27` with `--untracked-scope=exclude`.
- Result: **approved, zero findings**. The reviewer confirmed the allowlist coverage and the preserved
  approval rule for other writes.
- `authority: burned` on consumed revision
  `sha256:01ee3d675efe276fdefc8f3aed305f947a6cf6b65eff09c54e29ecf2027bb7fa`.
- The reviewed revision is the `fix(...)` commit below; this record is carried by the second commit.

## Follow-up, deliberately out of scope

The unadvertised `agent:` topic_key rule stays open, and the empirical re-check measured it rather than
assuming it: 5 of 5 runs still produced a `topic_key` that `MemoryWriteArgs` rejects. The fix belongs in
the tool's own contract, not in a persona.

## Delivery

Human decision pending. The reviewed candidate is committed as the `fix(...)` commit; nothing has been
pushed and no pull request exists yet.
