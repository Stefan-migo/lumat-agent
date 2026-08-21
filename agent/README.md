# LumatAgent `agent/` — declarative cerebro layer

This directory is the single source of truth for everything the LLM reads. It
is the base the future H2 multi-agent router consumes. No DB change in this
iteration.

## Layout

```
agent/
├── personas/            # system prompts (static, never {{}})
│   ├── orchestrator.md          # respond.SYSTEM_PROMPT (AC-3)
│   ├── orchestrator_brief.md    # respond.BRIEF_MODE_SUFFIX (SS-3 short mode)
│   ├── classify.md              # classify_intent.SYSTEM_PROMPT
│   └── summary.md               # summary.SYSTEM_PROMPT
├── prompts/             # user-slot templates ({{var}} placeholders)
│   ├── respond.md               # <kb>{{kb_text}}</kb> / <user_input>{{user_input}}</user_input>
│   ├── classify.md              # <user_input>{{user_input}}</user_input>
│   └── summary.md               # summary context slots
├── skills/              # reference-only pointers (AC-6) — NEVER loaded
│   ├── sdb.md                   # deterministic gates remain the authoritative SDB
│   ├── emergency.md             # → app/services/emergency.py
│   ├── handoff.md               # → app/chat/nodes/handoff*.py
│   └── capture.md               # → app/chat/nodes/capture.py
├── registry.yaml        # declarative agent registry (data-only, AC-4)
└── README.md            # this file
```

- **Personas are static**: they must never contain `{{}}` placeholders (AC-5).
  The strict renderer only fills slots in `prompts/`.
- **Skills are documentation**: no skill file is ever loaded into a prompt
  (AC-6). The deterministic gate nodes are the authoritative SDB.
- **Registry is data**: `registry.yaml` is validated by a test but has no
  runtime reader until Fase-2 (D-A7 / AC-4). It does not enforce tools,
  KB scope, or memory scope.

## Editing workflow

All files under `agent/` are editable without a code deploy. After editing:

- Run `pytest tests/unit/ -q` — asserts every persona byte-matches its node
  constant (AC-3), templates carry the right slots, and the registry stays as
  exactly one `orchestrator` (AC-4).
- Do not put customer-facing copy into `agent/`; canned replies stay in code
  (`CANNOT_ANSWER_REPLY`, `CLARIFICATION_REPLY`, `HANDOFF_REPLY`).

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
