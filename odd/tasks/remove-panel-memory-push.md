# ODD: remove-panel-memory-push

## Objective

Remove the panel memory push channel. No memory row is injected into the assistant prompt any more:
the agent reaches memory only through explicit tool calls. Rewrite the two normative specs that
currently mandate the projection so they describe the pull contract instead.

This is decision **D4** plus its spec consequence **D4a** from the Tukulpan/Engram session
(`.cortex-sessions/ready-for-odd/2026-09-17-memoria-tukulpan-vs-engram/report.md:63-79`). The harness
compaction cue (**D5**) was split out of this work unit: reconnaissance proved its premise wrong, so it
needs its own design and its own unit.

## Problem

Every panel turn injects memory rows into the prompt before the model sees it:

- `assemble_context()` calls `load_panel_context(session, thread_id)` (`app/services/agent_chat.py:446`)
  and appends every returned row as a context item, pinned first (`:454-463`).
- The loader is `app/chat/assistant/nodes.py:112-125`: `list_for_entity(scope=memoria_scope,
  entity_id=f"thread:{thread_id}")`, split into `pinned` and `panel`.
- Rows that do not fit the injection budget are dropped **silently** and only flip
  `meta["truncated"]` (`:458-460`); `list_for_entity()` itself has no cap
  (`app/services/tukulpan.py:365-382`).

**Why this matters.** A pushed row lands in every future prompt unasked. That is what makes an
autonomous memory write dangerous: the blast radius of one bad row is not one answer, it is every
answer that thread will ever produce. Pull moves memory into the tool-result slot, which the persona
already treats as evidence. **Safe autonomy and full pull are the same decision** — which is why this
unit gates the memory-write work.

## Why — current state (verified by reconnaissance, not inferred)

- The panel push is the only memory path this unit touches. WhatsApp has an **independent** customer
  memory push (`app/chat/state.py:217-225` → `app/services/tukulpan.py:487-495` →
  `app/chat/nodes/respond.py:81-99`, a `<memory>` block). The original Tukulpan proposal explicitly
  scoped WhatsApp out (`openspec/changes/archive/2026-09-11-tukulpan/proposal.md:22-26`). **Out of
  scope here.**
- The pull path already works and was unblocked by work unit #1: `memory.read`
  (`app/chat/assistant/tools/registry.py:190-194`, bounded by `MemoryArgs.limit`, max 20) is
  read-only and now receives real argument schemas. Thread identity stays in `meta` (`scope`,
  `entity_id`, `agent_chat.py:508-509`), so the planner can still construct scoped arguments.
- The recap is **already** a memory row (`app/services/tukulpan.py:330-340`: `scope="panel"`,
  `entity_id=f"thread:{thread_id}"`, `MemoryType.SUMMARY`). It survives as a pullable row; only its
  automatic visibility is lost.
- `tukulpan_ids` in `meta` is consumed by nothing in production — only by tests and an archived design
  document. It exists solely to describe the projection being removed.

## Scope

**In:** stop assembling memory into panel context; delete the now-dead loader; drop `tukulpan_ids` from
the context metadata; rewrite `MEM-3` and `HL-1` to mandate explicit pull; update every test whose
contract no longer exists.

**Out:** `memory.read` and its contract; `hybrid_search()` (stays retained and test-only); the WhatsApp
customer memory push; the compaction rotation cue (that is D5, a separate unit); the memory schema,
relations, lifecycle, and write tools (work units #3 and #4); the `truncated` metadata that describes
history/attachment budget loss.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-remove-panel-memory-push`
- Branch: `odd/remove-panel-memory-push`
- Base: `5f6cc8cf`
- Files: `odd/tasks/remove-panel-memory-push.md`, `app/chat/assistant/nodes.py`,
  `app/services/agent_chat.py`, `openspec/specs/memory/spec.md`, `openspec/specs/harness-lumat/spec.md`,
  `tests/integration/test_assistant_harness_context.py`, `tests/unit/test_assistant_planner.py`

## Constraints

- **Strict TDD: ON** — source: `openspec/config.yaml` (`testing.strict_tdd: true`). Runner:
  `uv run pytest tests/`. Observe RED before the source change; never invent RED evidence.
- Integration commands require `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat`.
- **Delete, do not disable.** `load_panel_context` has exactly one production caller
  (`agent_chat.py:446`) plus a thin re-export (`agent_chat.py:283-285`). Removing the push leaves no
  caller, so the function goes rather than lingering as dead code.
- **Keep the identity keys.** `meta["scope"]` and `meta["entity_id"]` are how the planner builds scoped
  `memory.read` arguments. Removing them would break the pull path this change depends on.
- **Keep `meta["truncated"]`.** It describes history and attachment budget loss and stays meaningful
  after the projection is gone. It is **not** a history-rotation signal — that was the D5 premise
  error, and conflating them would introduce a false cue.
- **Specs are canonical, not deltas.** Rewrite the requirement text and its scenarios in place,
  preserving each file's requirement-ID and `#### Scenario:` conventions, and leave no scenario
  asserting a projection that no longer exists.
- Do not touch the WhatsApp path, migrations, Docker, or `registry.py`.
- Planning heuristic: ~400 authored changed lines. Reconnaissance estimated 105–205 for this slice.
- All artifacts are written in English.

## Tasks

- [ ] **T1 — RED.** Rewrite the affected tests to assert the pull-only contract: no memory content
      reaches `assemble_context()` items, `meta` carries no `tukulpan_ids`, and the loader no longer
      exists. Observe them fail against the current code.
- [ ] **T2 — GREEN.** Remove the projection from `assemble_context`, delete `load_panel_context` and its
      re-export, drop `tukulpan_ids` from the metadata, and rewrite `MEM-3` and `HL-1`.
- [ ] **T3 — Evidence.** Run the required checks, record exact RED/GREEN output and honest limits.

## Acceptance criteria

1. `assemble_context()` returns context items sourced only from history and attachments; no memory row
   content is ever auto-injected.
2. `meta` no longer carries `tukulpan_ids`, and still carries `scope`, `entity_id`, `message_ids`,
   `attachment_ids`, `estimated_tokens`, and `truncated`.
3. `load_panel_context` no longer exists in production code and nothing imports it.
4. `memory.read` is unchanged, still registered read-only, and still bounded by its validated `limit`.
5. No normative spec text still mandates the panel projection, pinned-first ordering, or automatic
   memory injection into panel context.
6. Each criterion fails against the pre-change code (RED observed) and passes after.
7. Only the authorized files change and the required suites meet the baseline.

## Checks

- `uv run pytest tests/integration/test_assistant_harness_context.py -q`
- `uv run pytest tests/unit/test_assistant_planner.py tests/unit/test_assistant_tools.py -q`
- `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/unit tests/integration/test_assistant_harness_guardrails.py tests/integration/test_assistant_harness_production.py tests/integration/test_assistant_chat.py tests/integration/test_assistant_harness_context.py tests/spec/test_memory_spec.py -q`
- `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/ -q`
- `rg -n "load_panel_context|tukulpan_ids" app/` returns nothing
- `git status --short`; `git diff --check`

Prerequisite for the integration commands: `docker compose -f infra/docker-compose.yml --profile test up -d db-test`
(the host port on 5432 is published by the `db-test` service). Never `down -v` — it deletes panel data.

## Decisions

- **Delete the loader instead of leaving it unreferenced.** One caller, one re-export; dead code that
  a future reader would mistake for a live contract is exactly what D4 exists to remove.
- **Drop `tukulpan_ids` with the projection.** It describes only the removed rows and has no production
  consumer.
- **Keep identity and `truncated`.** Identity is load-bearing for the pull path; `truncated` still
  describes real budget loss for history and attachments.
- **Rewrite both specs, not just `MEM-3`.** Reconnaissance found `HL-1`
  (`openspec/specs/harness-lumat/spec.md:9-23`) also mandates the projection, the pinned-first order,
  and the fixed injection budget. Leaving it would make the canonical contract contradict the code.
- **Split D5 out.** `meta["truncated"]` means budget loss; the rotation signal is
  `compaction["rotated"]` (`agent_chat.py:396/409/420`). Implementing D5 here would have shipped a cue
  that fires on the wrong event. Separate unit, separate design.
- **Leave the WhatsApp push alone.** Independent consumer, explicitly out of the original Tukulpan
  scope.

## Progress

- [x] Created this ODD record before the first source change.
- [x] T1 — RED observed after rewriting the projection contract tests.
- [x] T2 — GREEN implemented by deleting the projection and rewriting MEM-3/HL-1.
- [x] T3 — Evidence recorded below.
- [x] Native RDD review completed on this candidate (approved, burned).

## Verification evidence

RED (before the source change; `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/integration/test_assistant_harness_context.py -q`):

```text
____ test_context_keeps_history_in_created_order_without_memory_projection ____
E       AssertionError: assert 'tukulpan_ids' not in {'scope': 'panel', 'entity_id': 'thread:7', 'message_ids': [1, 2], 'attachment_ids': [], ...}
_________ test_assembly_ignores_panel_memory_rows_and_does_not_search __________
E       AssertionError: assert [{'source': '...', 'id': '1'}] == []
_____________________ test_panel_memory_loader_is_deleted ______________________
E       AssertionError: assert not True
```

GREEN and verification:

- `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/integration/test_assistant_harness_context.py -q`: 6 passed (quiet output: `...... [100%]`). The non-quiet equivalent reported `6 passed in 3.64s`.
- `uv run pytest tests/unit/test_assistant_planner.py tests/unit/test_assistant_tools.py -q`: 46 passed (quiet output: `.............................................. [100%]`). The non-quiet equivalent reported `46 passed in 0.32s`.
- `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/unit tests/integration/test_assistant_harness_guardrails.py tests/integration/test_assistant_harness_production.py tests/integration/test_assistant_chat.py tests/integration/test_assistant_harness_context.py tests/spec/test_memory_spec.py -q`: 219 passed (quiet output reached `[100%]`). The non-quiet equivalent reported `219 passed in 65.33s (0:01:05)`.
- `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/`: 874 passed, 2 warnings in `450.87s (0:07:30)`. Warnings: an unawaited `_publish_all` coroutine in `tests/integration/test_webhook_ingest.py::test_startup_sweep_reprocesses_received`, and the existing fastembed pooling warning in `tests/spec/test_projects_spec.py::test_project_slug_is_normalized_and_unique`.
- `rg -n "load_panel_context|tukulpan_ids" app/`: no output; no matches.
- `git status --short`: five modified authorized files plus this untracked task document. `git diff --check`: no output; passed.

An initial RED attempt without `TEST_ADMIN_DB_URL` was blocked during integration fixture setup by `psycopg.errors.InsufficientPrivilege: permission denied to alter role`; it was rerun with the required database URL and produced the decisive assertion failures above.

**Graph nodes consulted (Graph Check, Step 1):** worktree `graphify-out/GRAPH_REPORT.md` and
`graphify query "assemble_context panel memory projection load_panel_context agent_chat"`, with the
graph built from base `5f6cc8cf`. Nodes/edges: `assemble_context()` → `load_panel_context()` →
`list_for_entity()`; `assemble_context()` → `panel_cost_gate` → `plan_llm` → `execute`;
`registry.py` → `memory.read` → `list_for_entity()`; `compact_session()` → `flush_panel_session()` →
`write_recap()`; `tukulpan.py` → `hybrid_search()`. The directed path query from `assemble_context` to
`memory.read` reported no path; the undirected relationship was therefore treated as unverified rather
than inferred. The direct loader path query confirmed `load_panel_context()` calls `list_for_entity()`.

**Native RDD review.** The candidate was frozen with `--untracked-scope=exclude`, so this untracked
record is deliberately outside the reviewed scope: the candidate is exactly the five code and spec
files. Tier `medium`, 5 files, 146 lines, one lens (`review-reliability`), correction budget 73,
lineage `review-e076a36d9bb6bba1`, target identity
`sha256:d06f5138e6b87427a9449ab7cc5219cc9bdfdc1c8ed3e32746afae6d9c73b1bf`. Result: **approved**;
acknowledgement consumed (`gentle-ai.review-acknowledged/v1`, `authority: burned`). No correction round
was requested, so the frozen candidate bytes are exactly the bytes that were approved.

**Advisory finding (non-blocking, recorded verbatim in intent).** The reviewer raised one WARNING,
`R3-api-removal`, `app/services/agent_chat.py:283`, `evidence_class: inferential`:

> Removing the `agent_chat.load_panel_context` compatibility seam can cause runtime failures for
> unupdated callers that still import or invoke it.

The reviewer could only see the frozen candidate, so it could not check the repository for such
callers. Verified out of scope afterwards: a repository-wide search for `load_panel_context` before the
change found exactly one production caller (`agent_chat.py:446`, the same call this candidate removes)
plus the test file this candidate rewrites, and `rg -n "load_panel_context|tukulpan_ids" app/` now
returns nothing. The finding stays in the record as an honest advisory and needs no follow-up work unit.

## Recovery

Resume with `mem_context`, then the project-scoped `mem_search` for this feature, then
`mem_get_observation` for the full document, then read this file. Continue from the first unchecked
task.

## Next step

The work unit is implemented, verified, and reviewed (approved, authority burned). Nothing has been
committed, pushed, or opened as a PR, so delivery is the next human decision.

## Deferred to their own work units

- **D5** — render the compaction rotation cue, from `compaction["rotated"]`, never from
  `meta["truncated"]`.
- **Work unit #3** — `memory.search` (wire the already-built `hybrid_search`) and the write tool.
- **Work unit #5** — the `memory.kpis` misnomer.
- **Work unit #6** — the DSML leak in the responder (`nodes.py:566`).
