# ODD: asistente-skills

**Branch**: `odd/asistente-skills`
**Worktree**: `/home/stefan/repos/lumat-agent-odd-asistente-skills`
**Base**: `1b689229` (= `main` = `origin/main`, merge of PR #484)
**Status**: slice 2 in progress (T1 done; T2–T7 pending)

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
- [ ] **T2 (RED)** Project layer + effective index. `ProjectSkill(name, description, body)`
      on `ProjectConfig.skills`; `EffectiveConfig.skills_index`;
      `resolve_skill_index(session, thread)` = global + project, project overrides by name,
      dedup, order preserved. Tests: global-only; project adds; project overrides global by
      name; malformed project skill rejected.
- [ ] **T3 (RED)** Planner contract + prompt. `PlannerOutput.skills: list[str] = []` (extras
      still forbidden); `plan_llm` passes the effective index as `<available_skills>`
      (name + description, **no bodies**); `agent/prompts/assistant_plan.md` instructs the
      field. Tests: plan accepts `skills`; unknown key still rejected; planner prompt
      contains the index and not any body.
- [ ] **T4 (RED)** Guardrails. Declared skills filtered against the effective index
      (unknown dropped, fail-closed); result carried forward in state. Tests: known kept,
      unknown dropped, no index → empty.
- [ ] **T5 (GREEN)** Responder injection. `_skill_context(state)` returns the bodies of the
      declared/validated skills; appended to the **responder** system prompt only. Tests:
      declared body present in the responder prompt; absent from the planner prompt; the
      whole corpus is never injected.
- [ ] **T6** Seed skill `agent/skills/assistant/memoria-tukulpan.md` + registry declaration.
      Content: Tukulpan scopes, when to read/write, correct argument shapes.
- [ ] **T7** Verify: full suite green; spot check over affected files; RDD assessment.

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

- Forecast: **~450–600 authored changed lines** across ~9 files (`skills.py` new,
  `project_config.py`, `agent_registry.py`, `state.py`, `nodes.py`,
  `agent/prompts/assistant_plan.md`, `agent/registry.yaml`, the seed skill, tests) — likely
  **over the ~400 budget → chained PR or a scoped split**. Re-forecast after T2; apply the
  cached `ask-on-risk` strategy (no delivery strategy cached yet — ask once if the forecast
  holds).

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
</content>
