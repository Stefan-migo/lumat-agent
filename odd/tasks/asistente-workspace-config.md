# ODD: asistente-workspace-config

**Branch**: `odd/asistente-workspace-config`
**Worktree**: `/home/stefan/repos/lumat-agent-odd-asistente-workspace-config`
**Base**: `d94152f4` (= `main` = `origin/main` at branch time, merge of PR #482)
**Status**: in progress

## Objective

Slice 1 of the Asistente Lumat workspace (backend-only): give each project its own
assistant configuration (`instructions` + tool policy) and resolve an **effective**
configuration per turn, layered **global → project → thread**, that can only narrow what
the user's role already permits and keeps security non-overridable.

## Problem

The assistant has a single global config today: `agent/registry.yaml` (persona +
`tools_whitelist`) loaded by `load_assistant_config` (`app/services/prompts.py:146`,
`@lru_cache`). `Project` (`app/models.py:178`) has no configuration at all. Every project
namespace therefore behaves identically: same prompt, same tools. There is no way for a
project to scope the assistant's behavior or to opt into elevated tools.

## Design source

`.rapsodia-code/sessions/ready-for-odd/2026-10-05-asistente-lumat-workspace-multiagente/{session.md,report.md}`
and Engram `cortex-session/2026-10-05-asistente-lumat-workspace-multiagente/decision/*`.
Key decisions: **D7** (tiers), **D9** (skills live in git/DB — deferred), **D10/D11**
(additive instructions, project wins except security), **D12** (empty project inherits the
global prompt).

**Code-grounded correction to the report.** The report says `assemble_context` resolves
the effective config. In code, `assemble_context` (`app/services/agent_chat.py:434`) only
assembles bounded history + attachments. The real seam is the graph entry /
`assemble_context_node` (`app/chat/assistant/nodes.py:684`) plus the planner
(`nodes.py:615–635`) and response (`nodes.py:1050–1080`) consumers, with guardrails
re-checking at `nodes.py:707–788`.

## Scope

**In**

- `Project.config` JSONB column + migration (`db/migrations/040_project_config.sql`).
- A `ProjectConfig` model validating `instructions` + `tool_policy.opt_in_enabled`.
- **Tool tiers**: add `tier` (`default` | `opt_in`) to `ToolDefinition` and classify all 24
  tools.
- An effective-config resolver: layers global → project → thread for `instructions` and
  `tool_policy`; hard intersection with the role allowlist.
- Wire into the turn: effective system prompt (global persona + additive project
  instructions), planner tool catalog and guardrails consume the effective whitelist.
- Tests (unit + integration).

**Out (later slices — do not build here)**

- Skill registry, skill documents, lazy loading (**Slice 2**). No `skills` key yet.
- KB scope global/project (**Slice 3**). No `kb_binding` key yet.
- Planning mode (**Slice 4**), SDB loop + verify (**Slice 5**), project directory + UI
  (**Slice 6**). Slice 1 is backend-only: config is written by tests/services, not by a UI.
- Any change to the WhatsApp bot, Tukulpan memory scopes, or the 24-tool set itself.

**Ponytail note.** `skills` and `kb_binding` are deliberately absent from the JSONB config
in Slice 1: JSONB adds keys with **zero migration cost**, so defining keys nothing reads yet
is dead flexibility. They arrive with their slices. The cheapest correct slice is
`instructions` + `tool_policy`.

## Config shape (Slice 1)

```json
{
  "instructions": "additive project instructions (free text, may be empty)",
  "tool_policy": { "opt_in_enabled": ["web.search", "web.fetch"] }
}
```

- Missing / `{}` config → the project inherits the global prompt completely (D12).
- `instructions` are **additive**; they never replace the global persona (D10).
- `tool_policy.opt_in_enabled` selects which **opt-in** tools the project enables. A project
  can never enable a tool outside `global_whitelist ∩ role_allowlist` (D7/D11).
- Thread override reads `InternalChatThread.assistant_state["tool_policy"]` (a JSONB field
  that already exists) and overrides **only** the opt-in tier.

## Tier model (interpretation — see Assumptions)

`effective_tools = global_whitelist ∩ role_allowlist ∩ (default_tier ∪ (opt_in_tier ∩ enabled_opt_in))`

| tier | tools |
|---|---|
| `default` (always on) | `assistant.capabilities`, `customers.search`, `customers.list`, `customers.operational_history`, `conversations.search`, `conversations.list`, `appointments.upcoming`, `cases.list`, `kb.retrieve`, `memory.read`, `memory.search`, `memory.write`, `memory.update`, `memory.delete`, `dashboard.summary`, `project.list`, `project.find` (**17**) |
| `opt_in` (selectable) | `web.search`, `web.fetch`, `automation.create_rule`, `project.create`, `project.rename`, `project.archive`, `project.merge` (**7**) |

`memory.*` (including writes) is `default` per D7 ("memoria own"). Project admin = the
`SDB_WRITE_ALLOWLIST` set (`registry.py:27`). The two tiers partition all 24 tools.

## Assumptions

1. **A1 — default tier is not disableable. CONFIRMED by the owner (2026-10-06).** D7 says the
   safe default is "siempre on". So a project selects only among **opt-in** tools; it cannot
   turn a default tool off. No `disabled` list in the model.
2. **A2 — thread override reads existing `assistant_state`.** No new thread column; the key
   is read from the JSONB field that already exists.

## Constraints

- **Invariant**: a project can only narrow, never expand beyond the role. Enforced in
  **code** (the intersection), not in the prompt (D11). The prompt is defense in depth.
- `load_assistant_config` is `@lru_cache(maxsize=8)` — never mutate its returned object.
- **Migration number**: `040`. If the parallel `odd/clientes-panel` feature lands `040`
  first, renumber to `041` after merging `origin/main` (pre-PR merge-in surfaces it).
- **Strict TDD ON** (`openspec/config.yaml`): observe RED before GREEN.
  Runner: `uv run --no-sync pytest tests/` (`--no-sync` is mandatory or `uv.lock` is
  rewritten). Test DB: `eval "$(bash infra/test-db.sh env)"`; do **not** source
  `infra/.env` (it points at the compose host `db`, unresolvable from the host).
- Atomic commits, one concern each, ≤5 files; conventional commits; no `Co-Authored-By`.
- Preserve existing behavior when no project config exists: the resolved catalog and prompt
  must be identical to today's.

## Tasks

- [ ] **T1 (RED)** Model + migration. `Project.config` JSONB `NOT NULL DEFAULT '{}'`; a
      `ProjectConfig` Pydantic model (`instructions: str = ""`,
      `tool_policy.opt_in_enabled: list[str] = []`) that fails closed on unknown tool names.
      Tests: empty config resolves to global defaults; invalid tool name is rejected.
- [ ] **T2 (RED)** Tier metadata. Add `tier: Literal["default","opt_in"]` to
      `ToolDefinition`; classify all 24. Tests: every tool has a tier; `default` is exactly
      the 17 above; `default ∪ opt_in` == `TOOL_REGISTRY`.
- [ ] **T3 (RED)** Resolver `resolve_effective_config(session, thread, role) -> EffectiveConfig`
      (instructions + effective tool whitelist). Tests: global-only; project narrows opt-in;
      project cannot add beyond role; thread overrides opt-in only; empty project inherits
      global; a non-permitted opt-in tool stays out.
- [ ] **T4 (GREEN)** Wire into the turn: planner catalog uses the effective whitelist;
      system prompt = global persona + project instructions (appended, never replaced);
      guardrails enforce the effective set. Existing planner/guardrail tests stay green.
- [ ] **T5** Verify: full suite green; organizer spot check over directly affected files.

## Acceptance criteria

- **AC1** `Project.config` exists, defaults to `{}`, and a project with empty config yields
  byte-identical planner catalog and system prompt to today.
- **AC2** Every tool declares a tier; `default` = 17, `opt_in` = 7, union = 24.
- **AC3** A project config enabling an opt-in tool the role cannot use is still denied
  (intersection enforced in code, not by prompt).
- **AC4** A project config can never enable a tool outside
  `global_whitelist ∩ role_allowlist`; default-tier tools are always present.
- **AC5** Project instructions are appended after the global persona and never replace it;
  the resolved system prompt still carries the security baseline.
- **AC6** Full suite passes.

## Checks

- Graph nodes consulted (report `graphify-out/`, build `f8a4bf20`): `execute_tool` (60
  edges), `assemble_context` / `assemble_context_node`, `Registry`
  (`registry.py`), `nodes.py`, `models.py`, `services/projects.py`, and the
  context → cost gate → planner → execute flow.
- Strict TDD ON, runner `uv run --no-sync pytest tests/`.
- Test DB: `eval "$(bash infra/test-db.sh env)"`.

## Delivery

- Forecast: **~250–350 authored changed lines** across ~6 files (`models.py`, one migration,
  the resolver module, `registry.py`, `nodes.py`, tests) — under the ~400 budget → single PR.
  Re-forecast after T2; if it exceeds 400, apply chained PR.

## Progress

- **2026-10-06** — Worktree created from `main` `d94152f4`. Design read; harness mapped;
  storage decision **JSONB on `Project`** (owner). Migration number `040` reserved; no
  collision yet (both worktrees still at `039`). No code written yet.
