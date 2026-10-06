# ODD: asistente-skills

**Branch**: `odd/asistente-skills`
**Worktree**: `/home/stefan/repos/lumat-agent-odd-asistente-skills`
**Base**: `1b689229` (= `main` = `origin/main`, merge of PR #484)
**Status**: slice 2 complete (T1–T7). PR1 = T1–T2 (reviewed, authority burned); PR2 = T3–T6 + test alignment (under budget). Pending push/PR (owner decision).

## Objective

Slice 2 of the Asistente Lumat workspace: give the assistant a **skill registry with
index-first lazy loading**. A skill is a Markdown knowledge document (per section or
foundational) that tells the agent what a section is, its rules, and which tool to use for
what. The **index** (name + one-line description) is always cheap and visible to the
planner; the **body** is loaded only when selected. Layers `global → project`, project wins
by name. Selection is explicit: the planner declares the skills to load for the turn.

## Problem

The assistant's `skills` is declarative-dead: `agent/registry.yaml:61` sets
`assistant.skills: []`; `agent_registry.py` stores it as an unvalidated tuple;
`load_assistant_config` (`prompts.py:146`) explicitly loads "without loading skill files";
nothing consumes `.skills`. `agent/skills/*.md` holds four WhatsApp-roster stubs that
declare *"NEVER loaded into any LLM prompt"*. There is no index, no loader, no selection,
no project layer. The whole system is greenfield.

## Design source

`.rapsodia-code/sessions/ready-for-odd/2026-10-05-asistente-lumat-workspace-multiagente/{session.md,report.md}`
and Engram `cortex-session/2026-10-05-asistente-lumat-workspace-multiagente/decision/*`.
Key decisions: **D5** (skills per section, not sub-agents), **D8** (explicit planner
selection; semantic retrieval deferred), **D9** (global = git, project = DB, override by
name). Prior art `.rapsodia-code` validated lazy loading of **skill documents** (not tool
schemas — do not re-litigate).

## Scope

**In**

- A `skills` layer in the global registry and in `Project.config` (JSONB — **no migration**).
- Global skill index declared in `agent/registry.yaml` under `assistant.skills` as
  structured entries (`name`, `description`, `path`); bodies in `agent/skills/assistant/`.
- Project skill layer `Project.config.skills` = inline `{name, description, body}`.
- `resolve_skill_index(session, thread)`: global + project, dedup by name, **project wins**,
  global order preserved, project-only entries appended.
- Lazy body loading: only the selected skills' bodies are read.
- Planner contract: `PlannerOutput.skills: list[str]`; the planner prompt carries the
  **index** (name + description), never bodies.
- Guardrails: declared skills are intersected with the effective index (fail-closed:
  unknown names dropped).
- Responder injection: system prompt = persona + project instructions + **bodies of the
  declared/validated skills only**. Planner system prompt stays body-free.
- One seed foundational skill (`memoria-tukulpan`) to prove the path end to end.
- Unit + integration tests.

**Out (later slices — do not build here)**

- The full per-section skill corpus (agenda, clients, conversations, KB, cases, config,
  dashboard) — content authoring lands incrementally after the mechanism.
- Semantic retrieval of skills (**D8, deferred**).
- Thread-level persistent skill policy (Slice 2 selection is **per-turn**, not stored).
- Planner-loop injection (bodies into the *next* planner call of a multi-step turn) —
  follow-up; Slice 2 injects into the responder.
- Any change to the WhatsApp `agent.skills` roster or the four existing stub files.
- SKILL.md-style YAML frontmatter: the index lives in the registry manifest, not in file
  frontmatter.

## Model

```
effective_skills = dedup_by_name(global_index + project_index)   # project wins
```

| layer | where | shape |
|---|---|---|
| global (git) | `agent/registry.yaml` `assistant.skills` | `[{name, description, path}]`; body at `agent/{path}` |
| project (DB) | `Project.config.skills` (JSONB) | `[{name, description, body}]` inline, editable via UI (Slice 6) |
| thread | — | none in this slice; selection is per-turn by the planner |

- The **index** carries `name` + `description` + `scope` (+ file `path` for global, body for
  project). Bodies are **not** loaded with the index.
- `load_skill_body(defn)`: returns the inline project body, or reads the global file on
  demand; a missing global body file fails closed.
- **Override by name** is total: a project skill with the same `name` replaces the global
  one (description + body). Different names coexist.
- Project `skills` unknown/malformed entries fail validation (`ProjectConfig`), the same
  fail-closed discipline as `tool_policy`.
- Security: skill names are never used as paths directly; global bodies resolve only from
  the registry-declared `path`. Project bodies are inline data.

## Assumptions

1. **A1 — global assistant skills live in the shared `agent/skills/` tree, namespaced under
   `agent/skills/assistant/`.** The registry `path` field is authoritative, so the
   directory is a convention, not a resolution rule. The four WhatsApp stubs stay untouched
   and out of `assistant.skills`.
2. **A2 — the index description lives in the registry manifest** (git, reviewable, one
   source for the planner-visible summary) rather than in YAML frontmatter of the body file.
3. **A3 — the responder is the primary consumer of skill bodies in this slice.** The
   planner gets index-only by design (D8: it *declares* skills; it does not need bodies to
   declare them). Bodies also reach the next planner call in a multi-step turn only if that
   is added later (out of scope).
4. **A4 — no thread-layer skill policy.** D8 makes selection per-turn; persisting a thread
   skill policy would be state nothing in this slice needs.

## Constraints

- **Strict TDD ON** (`openspec/config.yaml`): observe RED before GREEN.
  Runner: `uv run --no-sync pytest tests/` (`--no-sync` is mandatory or `uv.lock` is
  rewritten). Test DB: `eval "$(bash infra/test-db.sh env)"`; do **not** source
  `infra/.env`.
- **No migration**: `Project.config` is JSONB; the `skills` key costs zero migration.
- **Graph Check** (rapso-persona): queries run before this design; nodes recorded under
  Checks.
- `load_assistant_config` is `@lru_cache` — never mutate its returned object.
- Atomic commits, one concern each, ≤5 files; conventional commits; no `Co-Authored-By`.
- Preserve WhatsApp behavior: `agent.skills`, the four stub files, and
  `test_registry_declares_exactly_one_orchestrator` / `test_skill_reference_files_exist`
  must stay green.
- Directive (documentation-only) line budget ~400 authored changed lines is advisory;
  re-forecast after T2 and apply the delivery strategy (`ask-on-risk`).

## Tasks

- [x] **T1 (RED)** Global skill index. Change the registry schema: `assistant.skills` becomes
      a structured list (`AssistantSkill` = `name` + `description` + `path`), validated with
      non-empty strings, known-shape extras ignored; `agent.skills` (orchestrator) stays a
      `list[str]`. New `app/services/skills.py`: `SkillDefinition(name, description, scope,
      path, body)` + `global_skill_index(config)` (no body read) + `load_skill_body(defn)`.
      Tests: index order/descriptions; body loads on demand; missing body file fails closed;
      a WhatsApp stub is never part of the index.
- [x] **T2 (RED)** Project layer + effective index. `ProjectSkill(name, description, body)`
      on `ProjectConfig.skills`; `EffectiveConfig.skills_index`;
      `resolve_skill_index(session, thread)` = global + project, project overrides by name,
      dedup, order preserved. Tests: global-only; project adds; project overrides global by
      name; malformed project skill rejected.
- [x] **T3 (RED)** Planner contract + prompt. `PlannerOutput.skills: list[str] = []` (extras
      still forbidden); `plan_llm` passes the effective index as `<available_skills>`
      (name + description, **no bodies**); `agent/prompts/assistant_plan.md` instructs the
      field. Tests: plan accepts `skills`; unknown key still rejected; planner prompt
      contains the index and not any body.
- [x] **T4 (RED)** Guardrails. Declared skills filtered against the effective index
      (unknown dropped, fail-closed); result carried forward in state. Tests: known kept,
      unknown dropped, no index → empty.
- [x] **T5 (GREEN)** Responder injection. `_skill_context(state)` returns the bodies of the
      declared/validated skills; appended to the **responder** system prompt only. Tests:
      declared body present in the responder prompt; absent from the planner prompt; the
      whole corpus is never injected.
- [x] **T6** Seed skill `agent/skills/assistant/memoria-tukulpan.md` + registry declaration.
      Content: Tukulpan scopes, when to read/write, correct argument shapes.
- [x] **T7** Verify: full suite green; spot check over affected files; RDD assessment.

## Acceptance criteria

- **AC1** `assistant.skills` is a validated structured index; the index is built without
  reading any body file.
- **AC2** `Project.config.skills` exists and validates; the effective index = global +
  project with project overriding by name.
- **AC3** The planner receives only the index and declares `skills` per turn; the plan
  contract validates it and still rejects unknown fields.
- **AC4** Guardrails drop declared skills outside the effective index (fail-closed).
- **AC5** Only declared+validated skill bodies reach the responder prompt; the full corpus
  is never injected.
- **AC6** Global body loading is lazy; a missing body file fails closed.
- **AC7** WhatsApp skills behavior is unchanged; full suite passes.

## Checks

- Graph nodes consulted (report `graphify-out/`, worktree build): `load_assistant_config()`
  (`prompts.py:146`), `AssistantRuntimeConfig` (`prompts.py:99`), `Registry`/`Agent`/
  `_build_assistant`/`load_registry` (`agent_registry.py`), `plan_llm` (`nodes.py:615`),
  `guardrails` (`nodes.py:729`), `execute` (`nodes.py:927`), `_run_sdb_tasks`
  (`agent_chat.py:125`), `execute_tool` (`tools/registry.py:664`), `PlannerOutput`
  (`state.py:27`), `resolve_effective_config` (`project_config.py:36`).
- Strict TDD ON, runner `uv run --no-sync pytest tests/`.
- Test DB: `eval "$(bash infra/test-db.sh env)"`.

## Delivery

- **Decision (owner, 2026-10-06): `stacked-to-main`.**
  - **PR1** = `odd/asistente-skills` (T1–T2: global index + project layer). 8 paths / 455 lines;
    reviewed by the `review-reliability` lens (`review-fba9ba3a8f530dfe`, approved, authority
    burned).
  - **PR2** = `odd/asistente-skills-turn` (T3–T6 + test alignment: planner/guardrails/responder +
    seed). 12 paths / 381 lines, under budget.
  - Push and PR creation are the owner's decision under ordinary repository policy.
- Forecast (superseded): ~450–600 authored lines across ~9 files; the actual split landed at the
  review boundary.

## Progress

- **2026-10-06** — Worktree `../lumat-agent-odd-asistente-skills` created from `main`
  `1b689229` (branch `odd/asistente-skills`). Graph Check run; harness mapped via read-only
  exploration. Design documented here. `75d0ff00` commits this plan.
- **2026-10-06** — **T1 complete.** `23a2aeac` turns `assistant.skills` into a structured,
  validated index (`AssistantSkill` = `name` + `description` + `path` in `agent_registry.py`;
  `agent.skills` stays `list[str]`) and adds `app/services/skills.py` (`SkillDefinition`,
  `SkillError`, `global_skill_index` — reads no bodies, `load_skill_body` — fails closed on a
  missing file). New `tests/unit/test_skills.py` (5 tests). **Verify:** focused suite
  (`test_skills` + `test_assistant_config` + `test_agent_registry` + `test_prompts`) → exit 0,
  59 tests; independent spot check re-ran it green. Strict TDD RED (module missing; malformed
  entry unvalidated) → GREEN. `agent/registry.yaml` and the four WhatsApp stubs untouched.
- **2026-10-06** — **T1 RDD assessment:** `assess --base-ref 1b689229 --committed-only` →
  `review_due: false`, `under_budget` (5 paths / 351 lines, medium). Boundary stays `1b689229`;
  T1 accumulates until the slice budget is reached.
- **2026-10-06** — **T2 complete.** `cab70481` adds the project skill layer and the merge:
  `ProjectSkill` + `ProjectConfig.skills` (non-empty fields, unique names, fail closed),
  `EffectiveConfig.skills_index`, and the merge in `resolve_effective_config` (global order
  preserved; a project skill with the same name **replaces in place**; project-only entries
  appended). Tests: `tests/unit/test_effective_config.py` (+3), `tests/unit/test_project_config.py`
  (+2). **Verify:** focused suite (`test_effective_config` + `test_skills` + `test_project_config`)
  → exit 0, 20 tests; independent spot check re-ran it green. Strict TDD RED (`skills_index` /
  `ProjectConfig.skills` missing; blank/duplicate not rejected) → GREEN.
- **2026-10-06** — **Slice-budget review approved.** `assess --base-ref 1b689229 --committed-only`
  → `review_due: true` (`slice_budget_reached`, 8 paths / 455 lines, medium). Native selected the
  `review-reliability` lens (lineage `review-fba9ba3a8f530dfe`); **state: approved**,
  acknowledgement `authority: burned`, correction budget 200 unused. One **advisory** finding
  (non-blocking) recorded under Follow-ups.
- **2026-10-06** — **T3 complete.** `99c497a6` gives the planner the effective skill index:
  `PlannerOutput.skills: list[str]`, `assemble_context_node` carries `skills_index` (name,
  description, scope, path, body) in `state["effective"]`, `_effective_skill_index` reconstructs
  it (fallback = global index), and `plan_llm` substitutes `<available_skills>` (name +
  description only — **no bodies**). `agent/prompts/assistant_plan.md` documents the field.
  `test_assistant_config.py` updated to the new intent. **Verify:** 43 tests, exit 0.
- **2026-10-06** — **T4 complete.** `620a0859` adds `_validated_skills` and intersects the
  declared skills with the effective index in `guardrails` (fail-closed: unknown dropped,
  order preserved, duplicates collapsed), carried in `guardrails["skills"]`. **Verify:** 77 tests.
- **2026-10-06** — **T5 complete.** `64329e59` adds `_skill_context` (loads the bodies of the
  validated skills via `load_skill_body`, skips a `SkillError` instead of crashing the turn) and
  appends them to the **responder** system prompt only; the planner prompt stays body-free.
  **Verify:** 47 tests.
- **2026-10-06** — **T6 complete.** `d5b531a3` seeds `agent/skills/assistant/memoria-tukulpan.md`
  (own vs customer axis, scopes, argument shapes, gotchas — code-grounded) and declares it under
  `assistant.skills`. Adds the **end-to-end override** test through the real
  `resolve_effective_config` (closes the T2 follow-up). **Verify:** 20 tests.
- **2026-10-06** — **T7 complete.** Full suite `uv run --no-sync pytest tests/` → **exit 0**.
  Two integration tests needed alignment with the new shape (`aed9e897`): the serialized planner
  dict now carries `skills: []`, and one `load_assistant_config` test double lacked `skills`.
  No lint/typecheck tooling is configured (CI runs `pytest` + frontend `npm run build`; the
  frontend is untouched by this slice).
- **2026-10-06** — **Second-range RDD assessment:** `assess --base-ref cab70481 --committed-only`
  → `review_due: false`, `under_budget` (12 paths / 381 lines, medium). PR2 stays under the
  400-line budget, so no additional review is due.

## Follow-ups (post-Slice-2, non-blocking)

- **R3-001 (WARNING, advisory)** — `app/services/skills.py:34-39`: `load_skill_body` joins the
  registry-declared `path` to `_AGENT_DIR` without constraining the resolved path to that tree, so
  a `..` component could read outside it. The registry is git-controlled (trusted), so impact is
  low; the project layer carries inline bodies, not paths. Harden by resolving and asserting the
  path stays under `_AGENT_DIR` when this module is next touched (needs its own reviewed commit).
</content>
