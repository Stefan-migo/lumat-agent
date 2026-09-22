# ODD: retire-kb-scope-axis

## Objective

Retire the `kb_scope` / `source_meta.category` topic-scope axis completely: remove the retrieval
filter that never engaged, its registry declaration, and the requirements that describe it. After
this change no code path, no registry field, and no requirement claims a topic-scope capability that
no production writer feeds.

## Problem

Three separate halves of one mechanism are declared and none of them is live:

1. **The filter.** `kb.retrieve(..., scope=...)` filters chunks on `source_meta.category`
   (`app/services/kb.py:356-359`). `scope=None` is the only value production ever passes.
2. **The declaration.** Every entry in `agent/registry.yaml` declares `kb_scope: null` (7 of 7), so
   the one caller resolves to `None` and the filter never engages.
3. **The requirements.** AO-7 says the filter SHOULD exist (`spec.md:95-108`), AO-1 mandates the
   field on every sub-agent (`:11`), and KB-5 names AO-7 in its orthogonality clause
   (`openspec/specs/knowledge-base/spec.md`).

This is the same ghost-mechanism pattern the KB work already found three times: a capability declared
as if declaring it were enough. Here it also caused the project's worst defect — the scope returned
zero chunks in silence for every document uploadable from the panel, so every price or warranty
question escalated to a human unnoticed (`odd/tasks/kb-triage-scope.md`, PR #277). PR #277 set
`research_triage.kb_scope` to `null` to stop the bleeding but left AO-7 standing, so the spec still
claims a filter the code no longer engages.

## Why — current state (verified on `f031721b`, post #291)

- `kb.retrieve` signature carries `scope: list[str] | None = None` — `app/services/kb.py:327`.
- The filter: `if scope is not None:` → `scope=[]` returns `[]`; else
  `KbChunk.source_meta["category"].astext.in_(scope)` — `app/services/kb.py:356-359`.
- The only caller that passes a non-default scope is `research_triage._kb_check`
  (`app/chat/subgraphs/research_triage.py:74`, `:98`), and `_registry_kb_scope()` (`:56-65`) returns
  `None` because `sub.kb_scope` is falsy on all 7 registry entries.
- AO-7 says **SHOULD**, not MUST — `openspec/specs/agent-orchestration/spec.md:95-108`.
- AO-1 mandates all seven fields including `kb_scope`, and carries the orchestrator-shape clause —
  `:11`.
- KB-5's orthogonality clause names AO-7 explicitly — `openspec/specs/knowledge-base/spec.md`.
- The AO-7 tests seed `source_meta={"category": ...}` by hand
  (`tests/integration/test_kb.py:437,444,466,473,493,500`), which is itself the evidence that no
  production path writes that field. `tests/integration/test_kb_triage_scope.py` documents the same
  fact in its header.
- `agent/README.md:45` **lies**: the sub-agent table claims `research_triage` has
  `kb_scope: valores, postventa`, while the YAML has said `null` since #277. Same ghost pattern, in a
  doc.
- `memoria_scope`, the sibling axis, **is** consumed (`app/services/prompts.py:155`) — so this is not
  "the registry is full of dead fields". `kb_scope` is the one dead field in that family.

## Scope

**In:**

- Delete the `scope` parameter, the filter block, and the scope paragraph of the `retrieve`
  docstring (`app/services/kb.py`).
- Delete `_registry_kb_scope()`, the `scope = ...` binding, the `scope=scope` argument, and the
  scope lines of the module docstring (`app/chat/subgraphs/research_triage.py`).
- Delete `kb_scope` from the registry schema, the YAML, the README, and the tests
  (`app/agent_registry.py`, `agent/registry.yaml`, `agent/README.md`,
  `tests/unit/test_agent_registry.py`, `tests/unit/test_prompts.py`).
- Delete the three AO-7 tests and replace them with one guard test asserting `kb.retrieve` has no
  `scope` parameter (`tests/integration/test_kb.py`); drop the now-dangling monkeypatch
  (`tests/integration/test_realtime_writers.py`).
- Amend AO-1 (seven → six fields, and the orchestrator-shape clause), retire AO-7
  (`openspec/specs/agent-orchestration/spec.md`), and drop KB-5's reference to AO-7
  (`openspec/specs/knowledge-base/spec.md`).

**Out:**

- No change to the retrieval behaviour itself: the filter never engaged in production, so removing
  it cannot change any answer. `audience` (KB-5) is untouched and stays the only retrieval gate.
- No change to `memoria_scope`.
- No change to `source_meta` the JSONB column. It keeps `chunk_index` and stays available; only the
  `category` filter requirement goes.
- `tests/integration/test_kb_triage_scope.py` stays: it guards the #277 fix and remains valid.
- No change to `test_orchestrator_sub_agents_fields_frozen` (`tests/unit/test_agent_registry.py:239`).
  Despite its name it asserts fresh objects, not the field list — a name that lies, which is exactly
  the trap this project already paid for once.
- Historical records (`odd/tasks/*.md`, `openspec/changes/archive/*`) are not rewritten.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-retire-kb-scope-axis`
- Branch: `odd/retire-kb-scope-axis`
- Base: `f031721b`
- Files: `odd/tasks/retire-kb-scope-axis.md`, `app/services/kb.py`,
  `app/chat/subgraphs/research_triage.py`, `app/agent_registry.py`, `agent/registry.yaml`,
  `agent/README.md`, `tests/integration/test_kb.py`, `tests/integration/test_realtime_writers.py`,
  `tests/unit/test_agent_registry.py`, `tests/unit/test_prompts.py`,
  `openspec/specs/agent-orchestration/spec.md`, `openspec/specs/knowledge-base/spec.md`

## Constraints

- **Strict TDD: ON** — source: `openspec/config.yaml` (`testing.strict_tdd: true`). Runner:
  `uv run pytest tests/`. Observe RED before each source change; never invent RED evidence.
- Integration tests need `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:6421/lumat`
  (`eval "$(bash infra/test-db.sh env)"`).
- No production behaviour change beyond removing the filter.
- Conventional commits, no `Co-Authored-By`. One concern per commit, ≤5 files per commit.

## Design decisions

**D1 — Retire the field, not only the filter.** Deleting the consumer while keeping the declaration
would leave `kb_scope` with zero readers — a ghost *worse* than today, since today at least
`_registry_kb_scope` nominally reads it. Retiring the whole axis is the only coherent boundary.

**D2 — KB-5 loses its AO-7 reference; the audience axis stands alone.** KB-5's orthogonality clause
("the audience axis MUST remain independent of the AO-7 topic scope") loses its subject when AO-7
goes. The clause is rewritten so the audience gate stands on its own; the orthogonality statement is
not silently dropped, it is removed because there is no longer a second axis to be orthogonal to.

**D3 — The guard test replaces the AO-7 tests.** A retirement needs a regression guard, otherwise the
next person re-adds `scope` without re-adding AO-7. The guard asserts the absence of the parameter,
which is a real RED→GREEN against today's signature.

**D4 — `test_kb_triage_scope.py` stays untouched.** It asserts the *absence* of the silent-empty
behaviour and is the regression guard for PR #277. It passes before and after; its header's reference
to the old `kb_scope` is historical context, not a claim.

## Tasks

### WU1 — retire the filter behaviour

- [x] **T1** — RED: `tests/integration/test_kb.py` — a guard test asserting `kb.retrieve` has no
      `scope` parameter. Observe RED (the parameter exists).
- [x] **T2** — GREEN: `app/services/kb.py` — delete the `scope` parameter (`:327`), the filter block
      (`:356-359`), and the scope paragraph of the docstring (`:341-344`).
- [x] **T3** — GREEN: `app/chat/subgraphs/research_triage.py` — delete `_registry_kb_scope()`
      (`:56-65`), the `scope = _registry_kb_scope()` binding (`:74`), the `scope=scope` argument
      (`:98`), and the scope lines of the module docstring (`:13`, `:20-21`).
- [x] **T4** — GREEN: delete the three AO-7 tests (`test_kb_a7_scoped_retrieve_filters_by_category`,
      `test_kb_a7_scoped_retrieve_excludes_non_matching_category`,
      `test_kb_a7_unscoped_retrieve_unchanged`) and drop the dangling monkeypatch in
      `tests/integration/test_realtime_writers.py:94`.
- [x] **WU1 commit** — `refactor(kb): retire the retrieve topic-scope filter`

### WU2 — retire the registry declaration

- [x] **T5** — RED: `tests/unit/test_agent_registry.py` asserts six required fields and no `kb_scope`
      on `SubAgent`; `tests/unit/test_prompts.py` asserts `kb_scope` is absent from the `agent:`
      block. Observe RED.
- [x] **T6** — GREEN: `app/agent_registry.py` — delete `kb_scope` from `SUBAGENT_REQUIRED_FIELDS`
      (`:38`), from `SubAgent` (`:54`), `Agent` (`:66`), `Assistant` (`:77`), and from the three
      parse sites (`:119`, `:180`, `:213`).
- [x] **T7** — GREEN: `agent/registry.yaml` — delete the 7 `kb_scope: null` entries (`:24`, `:41`,
      `:49`, `:57`, `:65`, `:73`, `:105`) and the header block that documents the field
      (`:2-19`, plus the field list at `:29` and the axis note at `:32`).
- [x] **T8** — GREEN: `agent/README.md` — drop `kb_scope` from the field list (`:41`) and the table
      column (`:44-51`), which also removes the stale `valores, postventa` claim.
- [x] **T9** — GREEN: finish the test edits (`tests/unit/test_agent_registry.py:34,53,64` and the
      fixture YAMLs; `tests/unit/test_prompts.py:113`).
- [x] **WU2 commit** — `refactor(registry): drop the kb_scope field`

### WU3 — spec deltas

- [x] **T10** — `openspec/specs/agent-orchestration/spec.md`: amend AO-1 (seven → six fields; drop
      the `kb_scope` mention from the orchestrator-shape clause) and retire AO-7 (Requirement + its
      two scenarios).
- [x] **T11** — `openspec/specs/knowledge-base/spec.md`: rewrite KB-5's orthogonality clause so the
      audience axis stands alone, without the AO-7 reference.
- [x] **WU3 commit** — `docs(specs): retire the AO-7 topic-scope axis`

## Verification

- `uv run pytest tests/integration/test_kb.py tests/integration/test_realtime_writers.py`
- `uv run pytest tests/unit/test_agent_registry.py tests/unit/test_prompts.py`
- `uv run pytest tests/` (full suite)
- `git diff --name-only | grep '^app/'` — confirms only the two intended production files moved.

## Acceptance criteria

1. `kb.retrieve` has no `scope` parameter and no `source_meta.category` filter.
2. `research_triage` has no `_registry_kb_scope` and passes no `scope`.
3. No entry in `agent/registry.yaml` declares `kb_scope`; the schema rejects/ignores nothing
   silently — the field is gone from `SUBAGENT_REQUIRED_FIELDS` and the dataclasses.
4. AO-1 lists six fields; AO-7 no longer exists; KB-5 no longer references AO-7.
5. `agent/README.md` no longer documents `kb_scope` and no longer claims a scope for
   `research_triage`.
6. The full suite passes; no production behaviour change beyond removing a filter that never
   engaged.
7. The guard test fails if anyone re-adds `scope` to `kb.retrieve`.

## Follow-ups

- The `messages.<key>` override (SS-5) is the remaining declared-but-unconsumed mechanism; it is its
  own unit, not this one.
- `source_meta` keeps `chunk_index`; if a topic axis is ever needed again, it is a new requirement
  with a production writer, not a restored field.

## Execution evidence

- Graph Check: `graphify query "kb retrieve topic scope registry research triage agent orchestration"`; consulted `retrieve()`, `_kb_check()`, `SubAgent`, `Registry`, `agent_registry.py`, `services/kb.py`, `research_triage.py`, `test_kb.py`, `test_realtime_writers.py`, AO-1, AO-8, and KB-5 graph nodes. Directed paths between the queried endpoints were absent; the area query completed successfully against the base graph.
- WU1 RED: `eval "$(bash infra/test-db.sh env)"; uv run pytest tests/integration/test_kb.py -k test_kb_retrieve_has_no_scope_parameter` — **1 failed, 18 deselected**; failure showed `scope` in `inspect.signature(kb.retrieve).parameters`.
- WU1 GREEN: `eval "$(bash infra/test-db.sh env)"; uv run pytest tests/integration/test_kb.py tests/integration/test_realtime_writers.py` — **28 passed**.
- WU1 commit: `c064b381 refactor(kb): retire the retrieve topic-scope filter`.
- WU2 RED: `uv run pytest tests/unit/test_agent_registry.py tests/unit/test_prompts.py` — **1 failed, 47 passed**; failure showed `SUBAGENT_REQUIRED_FIELDS` still contained `kb_scope` and seven entries.
- WU2 GREEN: `uv run pytest tests/unit/test_agent_registry.py tests/unit/test_prompts.py` — **48 passed**.
- WU2 commit: `19574886 refactor(registry): drop the kb_scope field`.
- WU3 commit: `5e46008e docs(specs): retire the AO-7 topic-scope axis`.
- Full suite: `eval "$(bash infra/test-db.sh env)"; uv run pytest tests/` — **1149 passed, 2 warnings** in 145.64s.
