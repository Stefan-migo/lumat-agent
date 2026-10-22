# ODD — pi-migration

- Status: in progress (steps 5-7 pending)
- Branch: `odd/pi-migration`
- Base: `fd2e4341` (origin/main)
- Created: 2026-10-22

## Objective

Move this project from Rapsodia-on-OpenCode to Rapsodia-on-Pi (Gentle Shell), keeping this project's
own skills, its ODD history and its `openspec/` tree intact.

## Specs

- **S1 — Where this started.** The maintainer's words: "primero merge y limpieza (si aplica). luego
  arranca. para el punto 4. dejalo ahi como vestigio de decisiones previas de construcicon." Point 4
  was the `openspec/` decision, so `openspec/` stays in the repository as a vestige of earlier
  construction decisions. It is not deleted, not archived, and not migrated.
- **S2 — Pending work is recovered first.** 50 untracked files (45 session handoffs under
  `odd/handoffs/`, the assistant capabilities knowledge base, three client references) were the work
  in progress when the runtime switch was decided. They are committed before anything else changes.
- **S3 — This project keeps its own skills.** `component-adapter`, `design-agent-lead` and
  `panel-section-analysis` are the project's, not Rapsodia's. They move to `.agents/skills/`, which
  is where Pi reads project skills. Nothing may delete them.
- **S4 — Retire only what Rapsodia shipped.** `.opencode/agents/rapso-*.md`, the retired pack skills
  (`bootstrap`, `graphify`, `rapso-persona`, `ponytail-*`), `.opencode/tools`, `.opencode/plugins`,
  `.opencode/mcp-template.json`, `.opencode/package.json`, `opencode.json` and `scripts/setup.sh`
  leave once `rapso adopt --dry-run` proves they are Rapsodia's. `.planning/` goes with them.
- **S5 — Engine owning the session.** `gentle-engram` owns the Engram session; `rapso` only produces
  the context prelude. The current OpenCode session is finished and closed with the old CLI before
  the switch, so exactly one runtime owns the session at a time.

## Tasks

| ID | Spec | Task | Route | Status |
|----|------|------|-------|--------|
| T1 | S2 | Commit the 50 untracked files (handoffs, capabilities KB, references) | inline | done: `46423677`, `3e23d755`, `5cc43452` |
| T2 | S3 | Move the three project skills from `.opencode/skills/` to `.agents/skills/` | inline | done: `6d1badf2` |
| T3 | S1, S4 | Run `rapso adopt --dry-run` with the 1.1.0 CLI and review the plan | inline | in progress |
| T4 | S1 | Keep `openspec/` as is | inline | decided (no work) |
| T5 | S4 | Apply `rapso adopt --yes` and remove the retired surface the plan proves is Rapsodia's | inline | pending |
| T6 | S4 | Rewrite this project's `AGENTS.md` for Pi (its own contract, not the template's) | inline | pending |
| T7 | S5 | Verify with this project's gates (`pyproject.toml`, pytest) and close out | inline | pending |

## Log

- **L1** (original request, verbatim): "primero merge y limpieza (si aplica). luego arranca. para el
  punto 4. dejalo ahi como vestigio de decisiones previas de construcicon."
- **L2** (order decided earlier): finish the running OpenCode session and `rapso close` there, then
  commit the pending work, then migrate, then resume `ready-for-odd`
  (`2026-09-24-harness-audit-y-cobertura-panel`) in Gentle Shell.
- **L3** (this branch so far): T1 and T2 done. The 1.1.0 CLI is the merged `main` build of
  `rapsodia-code` (`node ../rapsodia-code/cli/dist/index.js`); the globally installed `rapso` is
  still 1.0.3 and must not be used for this migration.
