# ODD — pi-migration

- Status: done (steps 1-7 applied; verification below)
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
| T3 | S1, S4 | Run `rapso adopt --dry-run` with the 1.1.0 CLI and review the plan | inline | done: `Removed (20)` / `Leftover (2)` on the first run, after the classifier fix (rapsodia-code PR #63) |
| T4 | S1 | Keep `openspec/` as is | inline | done: untouched, still reported as `Leftover` |
| T5 | S4 | Apply `rapso adopt --yes` and remove the retired surface the plan proves is Rapsodia's | inline | done: `14bf03d4`, `452a12a2` |
| T6 | S4 | Rewrite this project's `AGENTS.md` for Pi (its own contract, not the template's) | inline | done: `c83f078e` |
| T7 | S5 | Verify with this project's gates (`pyproject.toml`, pytest) and close out | inline | done: see the verification section |

## Verification

No application code changed, so the suites that need services are not the relevant proof; a doc and
config migration is verified by what it leaves behind.

1. `adopt --dry-run` before applying: `Created (3)`, `Removed (20)` (the whole `.opencode/` tree),
   `Leftover (2)` (`.planning`, `openspec`), `Injected (1)` (`.gitignore`), `Skipped (4)`.
2. `adopt --yes`: created `.agents/skills/{design-system,rapso-session}` and
   `.pi/extensions/rapsodia-context.ts`; injected `.gitignore` (dropped the dead
   `.opencode/tools/node_modules/` ignore); deleted nothing.
3. The retired surface is gone from the working tree and the index: `.opencode/` removed with
   `git rm -r` plus the ignored `node_modules` directories; `git status` clean afterwards.
4. Live references to the retired runtime: a tracked-file search for `rapso-persona`, `ponytail-*`,
   `/sdd-*` and `.opencode/` outside history finds nothing in `AGENTS.md` or the project docs. The
   hits that remain are historical: `.rapsodia-code/` session records (gitignored), `.planning/` and
   `openspec/` (kept on purpose), and `.atl/` (a generated skill-registry cache).
5. `AGENTS.md` keeps the three headings `engine/adopt.ts` injects by exact text (`### 5-Step
   Execution Gate (MANDATORY)`, `## ODD Worktrees`, `## Reporting Rapsodia Defects`), so a future
   `adopt` run stays idempotent.
6. The project's own skills survived: `.agents/skills/` holds `component-adapter`,
   `design-agent-lead`, `panel-section-analysis` plus the two Rapsodia skills.
7. The new runtime works end to end: `rapso context` in this project builds a 13.4 KB prelude from
   Engram plus the Graphify graph in 2.1 s, and a real `gentle-shell --approve -p` session with an
   aged prelude rewrote it (the `**Generated**` line advanced), which proves the installed
   `.pi/extensions/rapsodia-context.ts` ran `rapso context` through the 1.1.0 CLI on PATH.

## Log

- **L1** (original request, verbatim): "primero merge y limpieza (si aplica). luego arranca. para el
  punto 4. dejalo ahi como vestigio de decisiones previas de construcicon."
- **L2** (order decided earlier): finish the running OpenCode session and `rapso close` there, then
  commit the pending work, then migrate, then resume `ready-for-odd`
  (`2026-09-24-harness-audit-y-cobertura-panel`) in Gentle Shell.
- **L3** (this branch so far): T1 and T2 done. The 1.1.0 CLI is the merged `main` build of
  `rapsodia-code` (`node ../rapsodia-code/cli/dist/index.js`); the globally installed `rapso` is
  still 1.0.3 and must not be used for this migration.
- **L4** (applied): `adopt --yes`, then `.opencode/` retired, then `AGENTS.md` rewritten
  (`14bf03d4`, `452a12a2`, `c83f078e`). Before applying, `adopt`'s classifier was fixed upstream
  (rapsodia-code PR #63) because it labelled 12 of the project's own 13 leftovers as the project's
  when they were the pack's.
- **L5** (not touched): `.planning/` keeps the GSD-era plan files and `openspec/` stays as a vestige
  of earlier construction decisions, per S1. `.codex/skills/frontend-design` belongs to another agent
  surface and is out of scope.
- **L6** (delivery): branch pushed and PR #659 opened against `main`. The old OpenCode session
  `2026-09-23-archify-eval` was archived (moved from `sessions/open/` to `sessions/archived/`);
  `2026-09-29-clausulas-ip-reutilizacion` is still open and was left alone.
