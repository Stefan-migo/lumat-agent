# Panel nits and repo-truth docs

**Worktree**: `/home/stefan/repos/lumat-agent-odd-panel-nits-and-docs`
**Branch**: `odd/panel-nits-and-docs` (base `main` @ `b43712dd`)
**Status**: in progress

## Objective

Close two small, verified panel/repo-truth items that were sitting in the panel
backlog, without touching any file owned by the concurrently running
`odd/planner-contract` worktree.

## Problem

Two defects are confirmed in `main` @ `b43712dd`:

1. **`ProjectsPage.tsx:22` builds DOM ids from an arbitrary entity string.**
   `id={`entity-${entity}`}` feeds both `aria-labelledby` and the `<h2>`. The
   entity key is `Memory.entity_id` (`app/panel/api/routes/projects.py:38`), an
   operator-visible name that may contain whitespace. An id containing
   whitespace is invalid HTML5, and `aria-labelledby` splits its value on
   whitespace — so `aria-labelledby="entity-Thread 4"` resolves to two
   nonexistent tokens and the `<section>` loses its accessible name. The
   existing test only uses `Requirements` / `Design`, so it never sees this.

2. **The artifact table shows the raw `topic_key` to the operator.** The
   `Identificador técnico` column renders `<small>{artifact.topic_key}</small>`
   — a machine key such as `sdb:project:spec`. `web/DESIGN_SYSTEM.md:415`
   forbids raw implementation labels unless the screen is explicitly an
   advanced technical view. This is the operator-facing Proyectos page, and no
   spec requires the column. The table already shows título, contenido, tipo
   and estado.

3. **`openspec/config.yaml` misdescribes the repository.** It claims
   `no source code — Hito 1 is greenfield` and declares every testing layer
   (`unit`, `integration`, `e2e`) and every quality gate (`linter`,
   `type_checker`, `formatter`) as `false`. Reality at `b43712dd`: 16 unit,
   45 integration, 23 functional, 1 injection and 6 spec Python suites, 77
   vitest files under `web/src`, and a Playwright spec under `web/playwright`.

## Why

All three are cheap, self-contained and independently verifiable, and none of
them shares a file with `odd/planner-contract` (which owns
`app/chat/assistant/nodes.py`, `app/chat/assistant/tools/registry.py`,
`agent/prompts/assistant_plan.md`, `openspec/specs/assistant-tools/spec.md`
and the two planner unit suites).

## Scope

In scope:

- `web/src/components/pages/ProjectsPage.tsx`
- `web/src/components/pages/ProjectsPage.test.tsx`
- `openspec/config.yaml`

Out of scope (explicitly):

- Anything under `app/chat/assistant/`, `agent/prompts/assistant_plan.md`,
  `openspec/specs/assistant-tools/spec.md`, or the planner unit suites — owned
  by `odd/planner-contract`.
- `web/DESIGN_SYSTEM.md` page-architecture sync — parked pending a scope
  decision (see T2).
- Any Python suite: `tests/` is not touched, and the integration suite is
  deliberately **not run** from this worktree (see Checks).

## Constraints

- **Database isolation.** The integration suite runs against a shared
  PostgreSQL instance (`postgresql+psycopg://app:app@localhost:5432/lumat`,
  cleaned up by `tests/conftest.py`) that the other ODD worktree may be using
  concurrently. This change runs **no pytest at all**, so it never opens a
  connection to that database.
- The TypeScript surface is verified with its own runner (vitest), which is
  jsdom-based and database-free.
- No refactor of unrelated code: the dense one-line JSX in `ProjectsPage.tsx`
  stays as it is. Only the two defects change.

## Tasks

- [x] **T1 — ProjectsPage nits (`web/src/components/pages/ProjectsPage.tsx`)**
  - [x] T1.1 RED: add a regression test that renders an entity containing
        whitespace (e.g. `Thread 4`) and asserts the section is reachable as an
        accessible region with that name. It must FAIL against the current id.
  - [x] T1.2 RED: assert the raw `topic_key` is not rendered.
  - [x] T1.3 GREEN: make the section id collision-safe and free of whitespace,
        without introducing a new helper or dependency.
  - [x] T1.4 GREEN: remove the `Identificador técnico` column.
  - [ ] T1.5 All web tests pass and `npm run build` (tsc + vite) passes.
- [ ] **T2 — `web/DESIGN_SYSTEM.md` page architecture** — *parked, scope decision
      pending.* The reported gap was Proyectos + Sesiones de planificación, but
      the real gap is larger: `## Page architecture` covers only Panel,
      Clientes, Conversaciones, Casos, Base de conocimientos, Configuración and
      Login, while `### Navigation` lists 6 destinations and the shipped app
      (PNL-APP-1) exposes 10. `Asistente Lumat`, `Agenda`, `Automatizaciones`,
      `Usuarios`, `Proyectos` and `Sesiones de planificación` have no section.
      Do not execute until the scope is chosen.
- [x] **T3 — `openspec/config.yaml` truth**
  - [x] T3.1 Replace the `Existing:` line with the shipped repository reality.
  - [x] T3.2 Set `testing.layers` from the measured suites and keep `e2e`
        honest about the single Playwright spec.
  - [x] T3.3 Leave `quality.*` false and say why in `notes` (no linter, type
        checker or formatter is configured in `pyproject.toml` or `web/`);
        `npm run build` type-checks through `tsc -b` only.
  - [x] T3.4 Rewrite `notes` — it currently claims there is no test
        infrastructure.

## Acceptance criteria

1. An entity name containing whitespace or punctuation yields a section whose
   `aria-labelledby` resolves to exactly one element.
2. The Proyectos detail tables no longer render `topic_key`.
3. `openspec/config.yaml` `testing`/`context` blocks match measurable facts at
   `b43712dd`, with no claim that cannot be checked with a command.
4. No file owned by `odd/planner-contract` is modified.

## Checks

| Check | Command | Expected |
| --- | --- | --- |
| Web unit suite | `cd web && npm run test` | all pass |
| Type check + bundle | `cd web && npm run build` | exit 0 |
| Overlap guard | `git diff --name-only b43712dd` | only the three in-scope paths plus this doc |
| Python suites | **not run** | shared database is isolated from this worktree |

TDD: enabled for this project (`openspec/config.yaml` → `testing.strict_tdd:
true`, runner `pytest`). The changed surface is TypeScript, whose runner is
vitest; RED is required before the fix on that surface. No pytest suite is
involved, so no Python runner is exercised.

## Progress

- T1 RED: `npx vitest run src/components/pages/ProjectsPage.test.tsx` failed as
  intended with `Unable to find role="region" and name "Thread 4"`; the DOM
  showed `aria-labelledby="entity-Thread 4"`, and the raw topic keys were still
  rendered.
- T1 GREEN: the same targeted run passed with 4 tests; the section now uses
  `entity-${index}` for both `aria-labelledby` and `id`, and the technical
  identifier column is removed.
- Full web suite: `npm run test` reported 76 passing files / 565 passing tests
  and 1 failing pre-existing `AppShell.test.tsx` test (`renders live data pages
  for every navigation view`, 5000 ms timeout). The failure is outside the
  changed files, so T1.5 remains unchecked.
- Build: `npm run build` passed (`tsc -b` and Vite build; 332 modules).
- Repository measurements used for `openspec/config.yaml`: 16 unit, 45
  integration, 23 functional, 1 injection, 6 spec Python files; 77 Vitest
  files under `web/src`; 1 Playwright file (`command-center.spec.ts`).
- Graph check consulted `ProjectsPage()`, `ProjectsPage.test.tsx`, `DataTable()`,
  `web/src/components/pages/ProjectsPage.tsx`,
  `web/src/components/pages/ProjectsPage.test.tsx`, `shared/DataTable.tsx`,
  `routes/projects.py`, and `web/package.json`; the direct path query was
  ambiguous, so the relevant directed path query returned no path.

## Next step

T1 RED, then T1 GREEN, then T3. T2 waits for the scope decision.
