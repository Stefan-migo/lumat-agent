# ODD: asistente-sdb

**Branch**: `odd/asistente-sdb-service`
**Worktree**: `../lumat-agent-odd-asistente-sdb-service`
**Base**: `32ebb4b5` (= `origin/main`, PR #504 merge; contains slices 1–5 plus the clientes s09–s13 merges).
**Status**: Slices 1–5 **merged to main** (PR #489 spec; PR #490 gate + isolated verifier + loop wiring; PR #491 phase-subgraph removal). Slice 6 in progress (service-runner removal). Slices 7–8 pending (registry/config cleanup; wire the verifier into the approved service path). No DB migration expected.

## Objective

Refactor of the Asistente Lumat workspace (Slices 1–8): **SDB stops being a 7-phase subgraph and becomes the
normal loop plus one verification step** (`plan → execute → verify`). A deterministic gate decides
when an independent, **read-only verifier with fresh context** must confirm the outcome against an
**observable success criterion**. The optional Cortex→SDB handoff reuses the existing admin-only
`sdb_requested` flag.

## Problem

Today SDB is a separate seven-phase branch (`sdb_clarify → sdb_spec → sdb_plan → sdb_approve →
sdb_execute → sdb_verify → sdb_deliver`) that never reuses the normal pipeline:

- The phase subgraph is wired to a `sdb_trigger_gate` whose incoming edge is not declared from the
  normal path; the real approved execution lives in the **service layer**
  (`app/services/agent_chat.py`), and the graph's `sdb_execute` node only projects results.
- The normal loop (`plan_llm → guardrails → execute → tool_loop_head → respond`) has **no**
  verification step at all: an effect can be dispatched and reported without independent
  confirmation.
- A leftover `sdb_classification` field remains in `agent/registry.yaml` even though the
  classifier was deleted in Slice 4.
- The pattern that looked like a "sub-agent with fresh context" (`delegation.py`) does **not**
  isolate context: it injects `_context_text(state)` from the parent.

## Decisions (locked — do not re-open)

Recorded in Engram `cortex-session/2026-10-05-asistente-lumat-workspace-multiagente/decision/*`:

- **D3/D14** — SDB is no longer a 7-phase subgraph. It is the **normal loop + one verification
  step**: `plan → execute → verify`.
- **D4** — `verify` is a **separate read-only verifier with fresh context**. The orchestrator does
  plan + execute; the verifier inspects only the outcome. The existing `delegation.py` pattern does
  **not** isolate context, so a new isolation mechanism is required.
- **D15** — verify is triggered by a **deterministic gate**: a plan step whose tool mutates state
  (`memory.update`, `memory.delete`, `automation.create_rule`, `project.create`, `project.rename`,
  `project.archive`, `project.merge`), OR an explicit verify request, OR the admin handoff.
  **`memory.write` is exempt** (additive note-taking).
- **D6** — the Cortex→SDB handoff is **optional**, triggered by explicit admin action, never
  inferred from free text. Mechanism: reuse the existing admin-only `sdb_requested` flag; remove
  the `sdb_classification` remnant.

## Design decisions (agreed)

Both verifier forks below are owner-confirmed; the rest were carried in the approved scope.

- **Gate evaluation point**: evaluate **once after the execution loop finishes** and before the
  final response, over the set of effect tools actually dispatched this turn. Not per-step, and not
  the initial planner plan (the normal planner loops one tool per step).
- **Approval is orthogonal**: the gate is about *effects*, not approval. Autonomous writes (when
  the existing policy allows them) also trigger verify; approval requirements are unchanged.
- **Success criterion**: `PlannerOutput` gains `success_criterion: str`, required whenever the plan
  contains an effect step. If it is missing or not observable, verify returns `unverifiable` and
  the turn is qualified (never silently claimed as success).
- **Evidence boundary (isolation)**: the verifier receives ONLY the success criterion, the executed
  steps (tool + arguments) and their results/evidence. It must NOT receive conversation history,
  thread state, memory, or `_context_text`. Enforced by constructing a fresh message list.
- **Failed verification (LOCKED)**: the turn completes but the response is **qualified** — it
  reports that the effect ran and that verification flagged the discrepancy (`verification: failed`
  with a reason). No automatic retry (a retry of e.g. `project.create` could duplicate the effect);
  no silent success.
- **Verifier capability (LOCKED)**: the verifier may call **bounded read-only tools (≤2 steps)**,
  under the same read-only scope rules as delegation, so it can independently confirm the effect
  (e.g. re-query the created project) instead of re-reading the executor's own evidence.
- **Legacy threads**: no migration. Old `assistant_state.sdb` / `current_plan.sdb` keys are ignored
  on read and dropped on next write; pre-existing pending SDB runs are not resumed.

## Scope

**In**

- Collapse the 7-phase subgraph into normal loop + `verify`.
- Isolated read-only verifier sub-agent with an observable success criterion.
- Deterministic D15 gate.
- Handoff D6 via the existing `sdb_requested` flag; remove `sdb_classification`.
- Remove the now-dead SDB service machinery (runner, delivery, persistence, `_sdb_plan`,
  SDB-specific recovery) while keeping the normal approval/evidence path.
- Rewrite SDB tests and the `sdb-native` spec.

**Out (later slices — do not build here)**

- Project directory + UI and the Markdown preview of the planning report (Slice 6).
- Open follow-ups: R3-001 `load_skill_body` path containment, SDB-opt-in bypass (closed by this
  rewrite), `assistant.capabilities` over-declaration, full skills corpus, KB-scope UI,
  `project.merge`/`archive` not moving KB docs.

## Current code map (touch points)

| Area | Location |
|---|---|
| Graph | `app/chat/assistant/graph.py`: `build_assistant_graph` (111–130), `sdb_trigger_gate` edge (138–141), `_after_sdb_trigger_gate` (52–54), `_after_sdb_approve` (107–109) |
| Phase nodes | `app/chat/assistant/nodes.py`: `sdb_clarify` (266), `sdb_spec` (277), `sdb_plan` (286), `sdb_approve` (301), `sdb_execute` (306), `sdb_verify` (312), `sdb_deliver` (347) |
| Normal loop | `nodes.py`: `plan_llm` (552–624), `guardrails` (743–824), `tool_loop_head` (864–892), `execute` (965+) |
| State | `app/chat/assistant/state.py`: `PlannerOutput` (27–40), `SDBTrigger` (70–78), `SDBTask` (93–121), SDB fields (182–191), `normalize_sdb_trigger` (194–213) |
| Service | `app/services/agent_chat.py`: `_sdb_plan` (73–76), `_run_sdb_tasks` (105–235), `_sdb_delivery` (237–255), `persist_sdb_state` (278–345), `sdb_requested` path (567–575, 625–673), `_events_for` (818–846), `approve_plan` (962–1037) |
| Recovery | `app/chat/assistant/recovery.py`: generic `recover_events`/`claim_execution`/`is_recoverable` (12–33, 70–93) KEEP; SDB-specific resume/revalidation (36–67, 95–102) DELETE |
| Registry | `agent/registry.yaml`: `sdb_classification` (96–98) DELETE, `classify: prompts/assistant_classify.md` (65–68) audit, `sdb` orchestrator skill (5) audit; `agent/skills/sdb.md` (reference-only) rewrite/delete |
| Tool taxonomy | `app/chat/assistant/tools/registry.py`: `SDB_WRITE_ALLOWLIST` (27–34), catalogue (586–610), `execute_tool` (668+); `_effective_tools` `nodes.py` (653–678) |
| Spec | `openspec/specs/sdb-native/spec.md` (SDB-1..SDB-10) |

## Tasks

- [x] **S5-01 — Rewrite the `sdb-native` spec.**
  Replace the seven-phase requirements with: `plan → execute → conditional verify`; the D15 tool
  set + explicit/admin conditions; isolated verifier context; criterion/evidence contract. Preserve
  the still-valid tool-security, approval and project-boundary guarantees in the normal specs.
  Files: `openspec/specs/sdb-native/spec.md`. ~180 lines. Depends: none.

- [ ] **S5-02 — Collapse the graph and the SDB state types.**
  Remove the `sdb_*` nodes/edges, `sdb_trigger_gate`, `_after_sdb_trigger_gate`,
  `_after_sdb_approve`; remove `SDBTrigger`/`SDBTask`/`normalize_sdb_trigger`/SDB state fields and
  `PlannerOutput.classification`; add gate/verify state and routing (insert verify after the
  execution loop, before response/evidence). Files: `graph.py`, `state.py`. ~180 lines. Depends: S5-01.

- [x] **S5-03 — Add the success criterion and the isolated verifier.**
  `PlannerOutput.success_criterion` + planner prompt; new isolated verifier that builds its own
  fresh messages (no `_context_text`) and inspects the evidence bundle (and, if confirmed, bounded
  read-only tools). Files: `nodes.py`, planner prompt/config as needed. ~250 lines. Depends: S5-02.

- [ ] **S5-04 — Replace the SDB service runner with the normal path.**
  Delete `_run_sdb_tasks`, `_sdb_delivery`, `persist_sdb_state`, `_sdb_plan`, SDB-specific recovery
  and SDB constants/imports; keep the shared approval/evidence/event path; remove the `if
  plan.get("sdb")` dispatch in `approve_plan`; persist the verifier result and emit its event.
  Files: `agent_chat.py`, `recovery.py`. ~350 lines. Depends: S5-02, S5-03.

- [ ] **S5-05 — Registry/config cleanup.**
  Remove `sdb_classification`; audit and remove/rewrite `agent/skills/sdb.md` and
  `prompts/assistant_classify.md` (confirm no other consumers), and the orchestrator `sdb` skill
  reference. Files: `agent/registry.yaml`, `agent/skills/sdb.md`, `agent/prompts/assistant_classify.md`,
  loader/tests. ~100 lines. Depends: S5-02.

- [ ] **S5-06 — Replace the SDB test suites.**
  Delete/rewrite `tests/spec/test_sdb_{trigger,phases,recovery}.py` and
  `tests/integration/test_sdb_{persistence,api}.py`; add gate, isolation, criterion and
  failed-verification tests; update SDB wording in `test_assistant_extensions.py`, graph
  expectations in `test_assistant_tool_loop.py`/`test_cortex_session_loop.py`, and SDB references in
  `test_assistant_tools.py`, `test_assistant_tool_owner_isolation.py`,
  `test_assistant_harness_guardrails.py`. ~500+ lines — **split into chained PRs**. Depends: S5-03, S5-04.

- [ ] **S5-07 — Validate unrelated tool/approval/project behavior.**
  Confirm `test_projects_spec.py` / `test_api_projects.py` SDB references describe real contracts
  (keep) or obsolete assistant flow (update); run the cross-cutting suites. ~200 lines. Depends: S5-04..06.

Forecast: **~1,700 authored lines** → far above the ~400 budget. Delivery strategy must be chosen
before the first commit (chained PRs or maintainer-approved `size:exception`).

### Slice 5 boundary correction (2026-10-07, owner-confirmed)

The original S5-02 ("remove all `sdb_*` nodes + `SDBTask`/state + `classification`") is **not
green-separable**. Verified couplings:

- `app/services/agent_chat.py:16` imports `sdb_deliver`, `sdb_verify` from `nodes.py`, and
  `_sdb_delivery` (L237) uses them → removing them breaks the service import.
- `tests/integration/test_sdb_api.py` monkeypatches `run_assistant` and injects `sdb_phase`, so it
  exercises the **service** SDB path (kept for Slice 6), not the graph phase nodes.
- `PlannerOutput.classification` is coupled to `agent/prompts/assistant_plan.md` and
  `agent/registry.yaml` (`sdb_classification`), propagated by `app/agent_registry.py:84,171-187` and
  `app/services/prompts.py:110,158`. `PlannerOutput` is `extra="forbid"`, so dropping the field
  without the prompt makes the planner reject its own output.

Corrected Slice 5 scope:

- **Remove** (`graph.py`): `sdb_trigger_gate`, `_after_sdb_trigger_gate`, `_after_sdb_approve`, all
  seven SDB node imports/registrations/edges and the `stage_nodes` SDB labels. (`sdb_trigger_gate`
  is already orphaned — no incoming edge; the subgraph is dead in the normal path.)
- **Remove** (`nodes.py`): `sdb_clarify`, `sdb_spec`, `sdb_plan`, `sdb_approve`, `sdb_execute`,
  `resolve_sdb_item`, `SDB_SPEC_LIMIT`, `SDB_TEXT_LIMIT` (graph/test-only).
- **Remove** (`state.py`): `SDBTrigger`, `normalize_sdb_trigger`, fields `sdb_trigger`, `sdb_route`,
  `sdb_rejection`, `sdb_scope`.
- **Keep for Slice 6**: `sdb_verify`, `sdb_deliver`, `SDB_RESULT_LIMIT` (service imports);
  `SDBTask`, `sdb_phase`, `sdb_spec`, `sdb_tasks`, `sdb_result` (service contract).
- **Defer to Slice 7**: `PlannerOutput.classification` + `assistant_plan.md` + `sdb_classification`
  + `agent_registry.py`/`prompts.py` propagation (atomic, green).
- **Tests**: delete `tests/spec/test_sdb_trigger.py` (only removed symbols); rewrite
  `tests/spec/test_sdb_phases.py` (drop phase-node tests, preserve the DB-dependency block at
  L230–285). `test_sdb_recovery.py`, `test_sdb_api.py`, `test_sdb_persistence.py` stay (Slice 6).

### Slice 6 scope (2026-10-07, owner-confirmed)

Slice 6 = **removal only** (no new behaviour). Verified map:

- **Remove** (`app/services/agent_chat.py`): `_sdb_plan`, `_run_sdb_tasks`, `_sdb_delivery`,
  `persist_sdb_state`, `SDB_EVENT_LIMIT`/`SDB_EVENT_HISTORY_LIMIT`; the `result.get("sdb_phase")`
  branches (plan construction ~L677, persistence ~L703, `_events_for` SDB branch ~L818); the
  `if plan.get("sdb")` dispatch in `approve_plan` (~L1005) and in `resume_thread` (~L1160); the SDB
  approval imports (`canonical_sdb_digest`, SDB use of `arguments_digest`) and `sdb_deliver`/`sdb_verify`
  from the nodes import. **Keep** `execute`, `issue_approval`, `validate_approval`, `claim_execution`,
  `recover_events`, and the whole normal event/approval/response path.
- **Remove** (`app/chat/assistant/recovery.py`): `revalidate_sdb_resume`, `resumable_sdb_tasks` and
  their SDB imports. **Keep** `recover_events`, `claim_execution`, `is_recoverable`.
- **Remove** (`app/chat/assistant/nodes.py`): `sdb_verify`, `sdb_deliver`, `SDB_RESULT_LIMIT`.
- **Remove** (`app/chat/assistant/state.py`): `SDBTask`, and fields `sdb_phase`, `sdb_spec`,
  `sdb_tasks`, `sdb_result`. **Keep** `sdb_requested` (admin handoff consumed by `verify_effects`).
- **Approval hygiene** (`app/chat/assistant/approval.py`): remove the SDB-only shape
  (`canonical_sdb_payload`, `canonical_sdb_digest`, `_sdb_bindings`, the SDB conditional in
  `issue_approval`/`validate_approval`/`validate_execution`, the `_bound_tool_arguments` SDB
  fallback). **Keep** the generic `arguments_digest`, normal token/expiry/arguments validation, and
  `canonical_project_payload`/`canonical_project_digest` (normal `project.*` approvals).
- **Registry** (`app/chat/assistant/tools/registry.py`): rename `SDB_WRITE_ALLOWLIST` →
  `APPROVED_WRITE_ALLOWLIST` (**keep the check** at L703 — it gates normal approved
  `project.*`/`automation.*` writes); remove the `sdb_payload` branch at L714.
- **Tukulpan** (`app/services/tukulpan.py`): remove `persist_sdb_artifact`, `SDB_SPEC_LIMIT`,
  `SDB_CHECKPOINT_LIMIT`, `sdb:{run_id}:…` key formats (only caller was `persist_sdb_state`).
- **Keep** the `sdb_requested` handoff plumbing (service params/forwards + `chat.py` API field) — it
  feeds the general verifier.
- **Tests**: delete `tests/spec/test_sdb_recovery.py`, `tests/integration/test_sdb_api.py`,
  `tests/integration/test_sdb_persistence.py`; rewrite the SDB fixtures in
  `tests/unit/test_assistant_tools.py`, `tests/integration/test_assistant_tool_owner_isolation.py`,
  `tests/integration/test_assistant_harness_guardrails.py` (preserve their NON-SDB assertions), and
  trim the `sdb_verify`/`sdb_deliver`/`SDBTask` tests in `tests/spec/test_sdb_phases.py`.

**Known gap (→ Slice 8, NOT here).** `verify_effects` is a graph node (`nodes.py`); the service
`approve_plan` calls `execute` directly and never runs it, and `nodes.execute` does not set
`verification`. So approved `project.*`/`automation.create_rule` effects are not independently
verified. This is a pre-existing gap (the old SDB branch that verified is already dead), not a
regression introduced by Slice 6; Slice 8 wires the verifier into that path.

### Slice 7 scope (2026-10-07, owner-confirmed)

Slice 7 = cleanup only (no new behaviour): drop the `classification` planner contract, the
dead registry/skills remnants, and the orphaned project cross-checks. Owner-confirmed:
delete what no longer serves.

**A — `classification` removal (atomic; `PlannerOutput` is `extra="forbid"`):**

- `app/chat/assistant/state.py:33` remove `PlannerOutput.classification`.
- `agent/prompts/assistant_plan.md:14-16,26-27` remove the `classification` slot and the
  seven-phase instruction.
- `agent/registry.yaml:96-98` remove `sdb_classification`.
- `app/agent_registry.py:84,171-188` remove the `Assistant.sdb_classification` field, the
  declaration validation, and the constructor arg.
- `app/services/prompts.py:110,158` remove the `AssistantRuntimeConfig.sdb_classification` field
  and its projection.
- Tests: drop `classification` from the planner mock (`test_assistant_planner.py:121`) and the
  `sdb_classification` fixtures/assertions in `test_agent_registry.py`.

**B — registry / skills cleanup:**

- `agent/registry.yaml:5` drop the `sdb` orchestrator skill; `agent/registry.yaml:68` drop the
  unused `classify: prompts/assistant_classify.md` (not consumed at runtime — no
  `prompts["classify"]` reader exists). Delete `agent/prompts/assistant_classify.md` and
  `agent/skills/sdb.md`; update `agent/README.md`.
- `app/chat/assistant/nodes.py:80` `extension_hook_metadata()` drop the `"sdb": "deferred"` key
  (metadata-only, internal, no API consumer). Update `test_assistant_extensions.py`
  (`SDB_TERMINOLOGY_CONSUMERS` becomes obsolete), `test_assistant_planner.py:606`,
  `test_assistant_config.py:74`, `test_api_assistant_capabilities.py:110`,
  `openspec/specs/agent-config/spec.md`.

**C — projects cross-check (S5-07):**

- `app/services/projects.py:208-215` `_has_active_run` never returns `True` (nothing writes
  `assistant_state["sdb"]`/`["proyecto"]` since Slice 6). Delete it + the three
  `"active SDB run"` raises in `rename`/`archive`/`merge` + the `test_projects_spec.py` block.
- The project detail artifact browse is orphaned: `app/panel/api/routes/projects.py:42-50` lists
  `topic_key.like("sdb:%")` and no writer of `sdb:` keys survives. Owner chose option 1: delete
  the feature — backend query/response, `to_project_artifact_dict` (serializers), the
  `ProjectsPage` artifact render + "artefactos SDB" copy, `ProjectDetailResponse.artifacts` /
  `ProjectArtifact` types, and the backend + frontend tests.

**Out of Slice 7 (Slice 8):** wiring the verifier into `approve_plan → execute`.

## Acceptance criteria (slice)

1. No `sdb_*` phase node or edge survives; SDB runs through the normal loop.
2. Verify runs iff the gate says so (D15 effect set ∪ explicit ∪ admin handoff); `memory.write`
   alone does not trigger it.
3. The verifier runs with fresh context: no conversation history, thread, memory or parent context.
4. A plan with an effect step carries an observable success criterion; a missing/ambiguous one is
   reported `unverifiable`, never a silent success.
5. `sdb_classification` is gone; the admin handoff is the existing `sdb_requested` flag, admin-only.
6. Normal approval, evidence, events and the project boundary keep working.
7. Full `pytest tests/` green (not a subset); no DB migration.

## Checks

- Strict TDD ON. RED before GREEN. Runner: `uv run --no-sync pytest tests/` (full suite ~1777
  tests). Full suite at the spot-check — the Slice 4 `NameError` escaped a subset.
- Test DB: `bash infra/test-db.sh up` + `eval "$(bash infra/test-db.sh env)"`; never source
  `infra/.env`. The shared test DB deadlocks under two concurrent pytest runs → run sequentially.
- Frontend not expected in this slice; if `web/` is touched, `npm ci`, `npm test`, `npm run build`.
- Graph Check per repo AGENTS.md: `graphify query` / `graphify path` before each task; record the
  nodes consulted.
- 5-Step Gate: atomic commit (≤5 files), verify, finalize.
- RDD on: `gentle-ai review assess --base-ref <last boundary> --committed-only --json`; if
  `review_due`, run the returned transition verbatim. Commits conventional, no Co-Authored-By.
- PR: base `main`, one `type:*` label, no `Closes`.

## Delivery (chained PRs, stacked-to-main)

Owner-approved: chained PRs, stacked-to-main. Each slice is an independent, **green** PR
(additions + deletions counted). Boundary constraint: removing the SDB nodes breaks the old SDB
tests, so the removal and its test rewrite must land in the same slice; additive scaffolding lands
first while the old subgraph still exists.

| Slice | Work unit | Tasks | Size | State |
|---|---|---|---:|---|
| 1 | New `sdb-native` spec (contract only) | S5-01 | ~197 | ✅ merged #489 |
| 2 | Deterministic gate + `success_criterion` (additive) | S5-03a | ~100 | ✅ merged #490 |
| 3 | Isolated read-only verifier (additive) | S5-03b | ~230 | ✅ merged #490 |
| 4 | Wire verify into the loop + response qualification (additive) | S5-02 (routing) | ~110 | ✅ merged #490 |
| 5 | Remove the dead SDB phase subgraph + routing contract | S5-02 (removal, corrected) | ~330 | ✅ merged #491 |
| 6 | Remove the dead SDB service runner + `sdb_verify`/`sdb_deliver` + SDB state + SDB tests | S5-04 (removal) | ~400 | ✅ committed + review approved |
| 7 | `classification` + prompt + registry/skills cleanup + cross-check | S5-05, S5-07 | ~300 | |
| 8 | Wire the verifier into the approved service path (close D15 for `project.*`/`automation.*`) | S5-08 (new) | ~250 | |

Each slice: work-unit commit(s) on `odd/asistente-sdb`, conventional message, tests with the code,
rollback = the slice's own files. Slices 5 may approach the budget; if a cohesive split does not
fit after one honest pass, report the overage and recommend `size:exception` for that slice.
Push/PR creation remain the owner's decision per slice.

## Progress log

- Worktree `../lumat-agent-odd-asistente-sdb` created (consent granted) and provisioned:
  `uv sync --frozen`, `cp ../lumat-agent/infra/.env infra/.env`, graph `graphify-out/graph.json`
  present.
- **Slice 1 (S5-01) done** — commits `4ebd6ace` (task doc) + `c1335444` (spec). `sdb-native` rewritten
  to SDB-11..SDB-16 (normal loop + conditional isolated verification). Native RDD review
  `review-c781144a08c191f2` (lens `review-reliability`) **approved with zero findings**; authority
  burned. Boundary advanced to `c1335444`.
- **Slice 2 (S5-03a) done** — deterministic gate + success criterion, additive (old SDB untouched).
  `app/chat/assistant/verification.py` (new): `EFFECT_TOOLS` (memory.write excluded) and the pure
  `verification_required(*, dispatched_tools, explicit, handoff)` with precedence
  effect-tool → explicit → handoff → not-required. `state.py`: `PlannerOutput.success_criterion`
  (≤300, non-empty) + `verify_requested`/`sdb_requested` state fields. New tests 15; writer GREEN
  143 passed; parent spot-check 143 passed. Not yet wired into the loop (Slice 3).
- **Slice 3 (S5-03b) done** — isolated read-only verifier in `app/chat/assistant/verification.py`:
  `VerificationResult` + `build_verifier_messages` (fresh, context-free) + `run_verification`
  (configured model; ≤2 bounded read-only tool steps with results fed back for the final verdict;
  caller-supplied `tool_executor` required — no bogus default; never writes). New tests
  `tests/unit/test_assistant_verification_runner.py`; 49 passed in the focused set. Corrective pass
  fixed three defects (hardcoded model, missing verdict round, admin default executor). Still not
  wired into the loop (Slice 4). Doc/plan: delivery split into 7 slices.
- **Slice 4 (S5-02 routing) done** — `verify_effects` node in `nodes.py` (no-op unless the gate
  fires; binds a thread/owner/project read-only `tool_executor`; stores `state["verification"]` and
  evidence). `graph.py`: post-tool path `tool_loop_head → verify_effects → respond_stream`. Failed/
  unverifiable outcomes append a deterministic qualification (`verification: <status> — <reason>`),
  streamed via `on_token`; confirmed adds none. Tool results now carry dispatched arguments for the
  verifier. 109 added lines; 82 passed. In-turn effects are `memory.update`/`memory.delete` (the
  `project.*`/`automation.*` effects execute in the service → Slice 6).
- **Slices 1–4 merged to `main`** — PR #489 (spec) and PR #490 (verification feature).
  `main` = `9f2140a4`. Reviews: `review-c781144a08c191f2` (slice 1, 0 findings),
  `review-9d1562e7914d3b39` (slices 2–4, approved; advisory R3-001 deferred). Full suite green.
  A full-suite run caught a planner-dict baseline test (unchanged file, outside the reviewed diff);
  fixed in `e6ef38fb`. Working branch for the removal slices: `odd/asistente-sdb-removal`.
- **Slice 5 boundary corrected (owner-confirmed 2026-10-07)** — exploration found the service import
  coupling + the `classification` prompt/registry coupling; scope narrowed to the dead phase
  subgraph + routing contract, deferring `classification` to Slice 7 and `sdb_verify`/`sdb_deliver`
  to Slice 6. Details in "Slice 5 boundary correction" above. Graph Check done: `graphify query`
  over `build_assistant_graph`, `sdb_trigger_gate`, `sdb_{spec,plan,verify}`, `plan`, `tool_loop_head`,
  `execute`, `parse_planner_output`, `_context_text`; graph built from `10dbd301` (refresh at close).
- **Slice 5 done (committed, reviewed)** — commits `edfd06c8` (removal: dead SDB phase subgraph +
  routing contract; 5 files, +32/−373) and `d540ac9a` (odd doc). Full suite green (**1,791 passed**).
  RDD review `review-df7d94ae9c298b1c` (lens `review-reliability`, medium, 6 files/467 lines)
  **approved with 0 findings**; acknowledgement burned authority. Pushed as **PR #491**; CI green;
  **merged** (merge commit `5820a04f`). Branch + worktree cleaned up.
- **Slice 6 started (2026-10-07)** — new worktree `../lumat-agent-odd-asistente-sdb-service` on
  `odd/asistente-sdb-service` from `main` = `32ebb4b5` (owner approved continuing). Owner confirmed
  the split: Slice 6 = pure removal; a new **Slice 8** wires the verifier into the approved service
  path (the D15 gap above). Graph Check done on the service path.
- **Slice 6 done (committed, reviewed)** — work-unit commits `9cb9969c` (service runner/persistence),
  `7d7e8806` (nodes/state), `91510a22` (approval/registry/tukulpan), `477a3972` (test fixtures).
  18 files, +131/−1757. Full suite green (**1,755 passed**). Note: two writer stalls left the tree
  half-migrated; the work was finished in smaller bounded steps. The writer over-deleted one valid
  test (`test_rename_and_merge_reject_active_runs_before_changes`); it was restored (still green) —
  `projects.py::_has_active_run` still reads the legacy `sdb` namespace, which is **Slice 7 scope**.
  RDD review `review-93510db7179fc56b` (lens `review-reliability`, medium, 19 files/1870 lines)
  **approved with 0 findings**; acknowledgement burned authority.
- **Slice 7 started + done (2026-10-07)** — worktree `../lumat-agent-odd-asistente-sdb-classify` on
  `odd/asistente-sdb-classify` from `main` = `fe81ba01` (owner approved). Graph Check on the
  `classification`/registry cluster and the `projects`/artifacts cluster. Cleanup only:
  `classification` + `assistant_plan.md` + `sdb_classification` (registry/`agent_registry.py`/
  `prompts.py`); the unused `assistant_classify` prompt, the `sdb` orchestrator skill and
  `agent/skills/sdb.md`; the `"sdb": "deferred"` extension hook; the spec AC-11 guardrails
  classification declaration; the dead `_has_active_run` guard; and the orphaned SDB project-artifact
  browse (backend query + `to_project_artifact_dict` + `ProjectsPage` render/copy + types/tests).
  Owner-confirmed extra: `sdb_requested` is now admin-only (403 for a non-admin, SDB-16). Work-unit
  commits `445b8f04`…`30371b1f`. Full backend suite green (**1,754 passed**); frontend `npm test`
  1,032 passed (serialized) + `npm run build` green.

## Review (RDD)

- **Slice 5** — `review.start` published (lineage `review-df7d94ae9c298b1c`, target
  `sha256:56e9bab7…`), tier **medium**, 1 lens (`review-reliability`), 6 files / 467 lines,
  correction budget 200. Consent: owner **granted**. Capture **approved with 0 findings**;
  acknowledgement burned authority (`gentle-ai.review-acknowledged/v1`, action `acknowledged`,
  `authority: burned`). Reviewed boundary = candidate tree (commit `d540ac9a`). Merged as #491 (CI green).
- **Slice 6** — `review.start` published (lineage `review-93510db7179fc56b`), tier **medium**, 1 lens
  (`review-reliability`), 19 files / 1870 lines, budget 200. Consent: owner **granted**. Capture
  **approved with 0 findings**; authority burned (`gentle-ai.review-acknowledged/v1`, `authority: burned`).
- Slices 1–4: see progress log (`review-c781144a08c191f2`, `review-9d1562e7914d3b39`).

## Open questions

- Slice 8: wire the verifier into the approved service path (`approve_plan → execute`) so D15 covers
  `project.*`/`automation.create_rule`. Design TBD (reuse `verification.py`; read-only `tool_executor`
  bound to thread/owner/project).
- ~~Slice 7: locate the authoritative admin-only validation of `sdb_requested`; remove
  `PlannerOutput.classification` + `assistant_plan.md` + `sdb_classification` +
  `agent_registry.py`/`prompts.py` propagation.~~ **Resolved (Slice 7):** the `classification`
  contract and its registry/propagation are removed; `sdb_requested` had no admin gate, so
  `send_message` now returns 403 for a non-admin carrying the flag (SDB-16).
