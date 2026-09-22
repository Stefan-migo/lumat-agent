# LumatAgent `agent/` — declarative cerebro layer

This directory is the single source of truth for everything the LLM reads. It
is the base the H2 multi-agent router consumes. No DB change in this iteration
(no new tables: the roster lives here in `registry.yaml`).

## Layout

```
agent/
├── personas/            # system prompts (static, never {{}})
│   ├── orchestrator.md          # system persona (loaded via prompts.load)
│   ├── orchestrator_brief.md    # short-mode persona (SS-3, appended when brief)
│   ├── classify.md              # classification persona
│   ├── summary.md               # summary persona
│   └── research_triage.md       # slice-1 KB research/triage sub-agent persona
├── prompts/             # user-slot templates ({{var}} placeholders)
│   ├── respond.md               # <kb>{{kb_text}}</kb> / <user_input>{{user_input}}</user_input>
│   ├── classify.md              # <user_input>{{user_input}}</user_input>
│   └── summary.md               # summary context slots
├── skills/              # reference-only pointers (AC-6) — NEVER loaded
│   ├── sdb.md                   # deterministic gates / guardrails reference
│   ├── emergency.md             # → app/services/emergency.py
│   ├── handoff.md               # → app/chat/nodes/handoff*.py
│   └── capture.md               # → app/chat/nodes/capture.py
├── registry.yaml        # declarative agent registry (data-only, AC-4)
└── README.md            # this file
```

- **Personas are static**: they must never contain `{{}}` placeholders (AC-5).
  The strict renderer only fills slots in `prompts/`.
- **Skills are documentation**: no skill file is ever loaded into a prompt
  (AC-6). The deterministic gate nodes are the Lumat
  `Gates deterministas / Guardrails` surface.

## Multi-agent registry (H2, slice-1)

`registry.yaml` declares the roster as data (AC-4 data-only): a top-level
`agent:` block — the orchestrator, **byte-identical to before H2** (AC-4
invariant, one top-level orchestrator) — plus a `sub_agents:` sibling with five
sub-agents, each carrying `name/persona/tools_whitelist/memoria_scope/
model/temperature`:

| Sub-agent | Slice-1 runtime | Tools whitelist |
|-----------|-----------------|-----------------|
| `research_triage` | ✅ **live** — KB research/triage sub-graph | `kb.retrieve` |
| `retrieval` | data-only (no runtime) | — |
| `customer_records` | data-only (no runtime) | — |
| `human_handoff` | data-only (no runtime) | — |
| `escalation` | data-only (no runtime) | — |

- **Slice-1 runtime**: only `research_triage` runs. A KB retail intent
  (`valores`/`postventa`) dispatches from the `orchestrate` node to the
  research sub-graph, which runs `kb.retrieve` and reuses the `respond`/
  `handoff` nodes. A miss retries ≤1 then hands off (AO-8). The other four
  sub-agents are declared data-only this slice: they have no dispatched runtime.
- **Reader**: `app/agent_registry.py` reads `registry.yaml` once (cached via
  `get_registry`) and validates it fail-fast at boot (exactly one
  orchestrator, all six fields, known tools, numeric temperature). It is NOT
  wired into `prompts.py`/`respond.py` (AC-4 no-runtime-consumer).
- **No new tables**: the roster lives in `registry.yaml`.

## Editing workflow

All files under `agent/` are editable without a code deploy. After editing:

- Run `pytest tests/unit/ -q` — asserts every persona byte-matches its frozen
  `FALLBACKS` literal in `app/services/prompts.py` (AC-3), templates carry the
  right slots, and the registry stays as exactly one `orchestrator` (AC-4).
- Do not put customer-facing copy into `agent/`; canned replies stay in code
  (`CANNOT_ANSWER_REPLY`, `CLARIFICATION_REPLY`, `HANDOFF_REPLY`).
- Do not modify the `agent:` block's bytes: `test_registry_declares_exactly_one_
  orchestrator` + `test_registry_has_no_runtime_consumer` enforce the AC-4
  invariant.

## D6 migration triggers

Move a piece of agent behavior out of `agent/` and into the database (Fase =
DB field) when ANY of these triggers applies:

1. **Runtime editing by non-developers** — operations or support staff must
   change prompts/skills without a deploy.
2. **Multi-tenancy** — different customers/tenants need different personalities,
   skills, or tools whitelists.
3. **Frequent production content changes** — prompt copy or skill definitions
   churn often enough that deploys become a bottleneck.

**Hybrid pattern**: until those triggers fire, keep the declarative default in
`agent/` and overlay only the DB-driven deltas (e.g., a tenant override applied
*on top of* the file baseline). This keeps the file as the baseline while the
DB supplies the moving parts. No DB migration is included in this iteration
(AC-7).
