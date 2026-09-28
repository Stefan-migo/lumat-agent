# ODD Task: cases-route-alignment

Status: WU1 delivered and merged (PR #392 → 059a275a); WU2 delivered
Worktree: `../lumat-agent-odd-cases-route-alignment`
Branch: `odd/cases-route-alignment-wu2`
Base: `059a275a` (= `main` after the WU1 merge)
Depends on: nothing
Source: `.rapsodia-code/sessions/ready-for-odd/2026-09-25-clientes-crm/report.md` (U4 `cases-page`)
Delivery strategy: `ask-on-risk`
Chain strategy: `stacked-to-main` (owner decision 2026-09-27) — PR 1 = WU1 (navigation and
durability), PR 2 = WU2 (remove the retired surface and reconcile the specs)

## Why this unit exists

U4 of the Clientes campaign was written as "mount `CasesList` as a real page and resolve its
placement against decision #2683", with an open question Q1 (sidebar item / replace the
current filter tab / reachable only from the ficha and the dashboard).

**That premise is superseded by a later, live spec.** The owner confirmed on 2026-09-27:
follow the live spec, do not revise it.

`openspec/specs/panel-app/spec.md:162-169` — requirement **PNL-APP-21 — Unified Cases
Compatibility Route** (introduced by the archived change `2026-09-10-panel-conversaciones-redesign`):

> The Conversations destination MUST be the unified operational section; `/panel/app/cases`
> MUST soft-redirect or resolve to it with the `Casos` tab active. `CasesList` MUST no longer
> be the rendered owner of that route, while existing case mutation semantics remain available
> from the unified workspace. (Previously: a `Conversaciones|Casos` segment rendered
> `CasesList` as a separate surface and the alias preserved that ownership.)

> **Scenario: Bookmarked cases route** — GIVEN an authenticated user opens `/panel/app/cases`
> WHEN the SPA parses the path THEN the unified conversations view renders with `Casos`
> selected and no standalone `CasesList` page is mounted.

Every Q1 option (sidebar item, replacing the tab with a case table, or a standalone page)
would mount `CasesList` as its own surface and therefore contradicts PNL-APP-21. The decision
#2683 sidebar IA ("Conversaciones, segmento Conversaciones|Casos") agrees.

So this unit does **not** mount a cases page. It closes the gap between the live spec and the
code, and removes the surface the spec already retired.

## Objective

1. The dashboard "Casos" entry lands on the **Casos tab of the unified conversations queue**,
   as `advanced-dashboards/spec.md:55` already requires ("cases to Casos").
2. `/panel/app/cases` is **durable**: a bookmarked or shared URL renders the Casos tab and
   survives a reload instead of decaying to "Todas".
3. Case mutation semantics stay reachable from the unified workspace, and that is **pinned by
   a test** instead of assumed.
4. The retired `CasesList` surface and its dead weight are removed, and the living specs that
   still name it are reconciled in the same change.

## Problem (verified at base `e8717201`)

### B1 — the dashboard "Casos" entry renders Configuración

`Dashboard.tsx:131-138` maps the "Casos" shortcut card (and every "Casos urgentes" row,
`Dashboard.tsx:180-187`) to `navigate("cases")`. `AppShell.tsx:87-91` then sets
`route = { view: "cases" }` and pushes `pathForView("cases")`, which returns
`/panel/app/conversations` (`panelRoutes.ts:44-47`).

`AppShell.tsx` has **no page-dispatch branch for `view === "cases"`**: `grep -n cases
AppShell.tsx` returns only `:106` (the `shellView` alias) and `:119` (the `conversations`
branch). The dispatch chain `AppShell.tsx:114-127` therefore falls through to its final
`: <Settings />`.

Observed consequence by code reading: clicking "Casos" highlights **Conversaciones** in the
sidebar and renders **Configuración**; after a reload the URL parses to
`{ view: "conversations" }` and the user lands on "Todas".

The existing test does not catch it: `Dashboard.test.tsx:42` asserts
`onNavigate` was called with `"cases"` and never inspects what the shell renders.

### B2 — `/panel/app/cases` is not durable

Parsing is correct: `panelRoutes.ts:102-106` maps the path to
`{ view: "conversations", conversationTab: "cases" }` and `AppShell.tsx:119` renders
`ConversationsList` with `initialQueueTab="case"`. But `conversationTab` is **not encoded in
any path**: `pathForRoute` -> `pathForView("conversations")` -> `/panel/app/conversations`.
The normalization effect (`AppShell.tsx:68-74`) therefore rewrites the URL immediately and the
tab is lost on reload, bookmark or share.

### B3 — the retired surface is still in the tree

`CasesList` (`web/src/components/pages/CasesList.tsx`) is mounted by no application surface:
only its story, its story test and `PanelLinks.test.tsx:7,38` import it. It carries the design
debt the report named — a module-level `columns` whose responsible cell is built with an empty
users array (`CasesList.tsx:23-26`) and then remapped by a nested conditional in the render
(`CasesList.tsx:83-84`).

Live specs still name it:

- `openspec/specs/panel-app/spec.md:61` — extraction list including `CasesListView`;
- `openspec/specs/panel-design-system/spec.md:742` — "`CasesList` MUST retain control-room
  `DataTable`, KPI, `Badge`, filter, and state primitives";
- `openspec/specs/corp-components/spec.md:21` — `DataTable` consumer list.

Its capabilities are not lost by deleting it: `CaseActions` stays reachable through
`ClientFicha.tsx:323` with real `updateCase`/`acknowledgeCase` handlers
(`ClientFicha.tsx:135-142`), and the backend `GET /panel/api/cases` keeps a live consumer in
`AgendaPage.tsx:160`.

## Scope

**In:** `web/src/components/domain/panelRoutes.ts`, `web/src/components/domain/AppShell.tsx`,
`web/src/components/pages/ConversationsList.tsx`, `web/src/components/pages/Dashboard.tsx`
(only if a code change is genuinely needed), their tests, the removal of
`web/src/components/pages/CasesList.tsx` + `web/src/stories/pages/CasesList.stories.tsx` +
`web/src/stories/pages/CasesList.stories.test.tsx` + the references in
`web/src/components/pages/PanelLinks.test.tsx` and `web/src/components/style-boundary.test.ts`,
the `CasesList` CSS section in `web/src/components/primitives/primitives.css`, and the three
`openspec/specs/*` references above.

**Out:** mounting any standalone cases surface; revising PNL-APP-21 or decision #2683; adding
case status/responsible controls to the conversation queue; the backend `cases` routes; any new
dependency; `tokens.css` values; Q4 (lifecycle vs operational status, tasks/reminders).

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-cases-route-alignment`
- Branch: `odd/cases-route-alignment`
- Base: `e8717201`
- Files: as listed in Scope.

## Constraints

- **Strict TDD: ON.** Backend runner `uv run pytest tests/`; frontend runner
  `cd web && npm run test`. Observe RED before each production change; never invent RED.
- No linter/formatter/type checker in Python — the suite is the verification. In `web/` run
  `npx tsc -b --noEmit` and `npm run build`.
- Artifacts in English. Conventional Commits, no AI attribution. Merge commits, never squash.
  Exactly one `type:*` label per PR.
- UI copy stays neutral Chilean Spanish; no raw backend identifier reaches the surface
  (`web/DESIGN_SYSTEM.md`).
- Push, PR and merge require explicit owner authorization.
- Graph Check (Rapsodia Step 1) runs before each task; record consulted nodes in Progress.
  `graphify-out/` is gitignored and absent from this worktree: query it from
  `/home/stefan/repos/lumat-agent`.
- A docs-only commit can push a range past the review budget: measure with
  `gentle-ai review assess` before declaring a slice closed, and freeze the review candidate
  **after** the docs commits it should cover.

## Decisions

- **D1 — Fix the dashboard entry by routing `cases` to the unified route, not by adding a
  render branch.** `AppShell.navigate("cases")` resolves to
  `{ view: "conversations", conversationTab: "cases" }`. Rejected: a `view === "cases"` branch
  that mounts `CasesList` (contradicts PNL-APP-21) or a second `ConversationsList` instance
  (a second definition of the same destination).
- **D2 — `/panel/app/cases` becomes the durable canonical spelling of the Casos tab.**
  `pathForRoute({ view: "conversations", conversationTab: "cases" })` and `pathForView("cases")`
  return `/panel/app/cases`. The route keeps resolving to the Conversations *destination*
  (PNL-APP-21), only the spelling differs, and the normalization effect stops stripping the
  tab. Rejected: a `?tab=casos` query parameter — a second encoding of a state that already has
  a documented, bookmarked path.
- **D3 — The queue tab is encoded in the URL for every tab (corrected 2026-09-27).** Selecting
  Casos pushes `/panel/app/cases` (its canonical spelling, D2); every other tab is a query
  parameter — `all` -> `/panel/app/conversations`, `human` / `emergency` / `closed` ->
  `/panel/app/conversations?tab=<id>`. The route's tab is the single value the queue renders, so
  the sync effect becomes idempotent instead of fighting the user's click. **Why corrected:** the
  first implementation exposed only `case | all`, and the parent's readback measured the
  consequence — leaving the Casos tab fired the change callback twice, producing **two
  `pushState` calls for one click** (history pollution) and a URL that disagreed with the visible
  tab (Casos -> Humanas left `/panel/app/conversations` on screen, so a reload landed on Todas).
  The lossy channel, not the effect, was the defect. The earlier ceiling ("tabs other than Casos
  are not individually encoded") is withdrawn: it was the cause, not an accepted limit.
- **D4 — Case mutation stays where it is, and gets pinned.** The queue keeps its
  `acknowledgeCase` action ("Reconocer emergencia", `ConversationsList.tsx:91`); case
  status/responsible edits stay on the ficha through `CaseActions`
  (`ClientFicha.tsx:323`). Recorded interpretation of PNL-APP-21's "existing case mutation
  semantics remain available from the unified workspace": ack is available in the queue and the
  full case surface is one click away on the ficha. Recorded ceiling: if the owner wants case
  status/responsible editing inside the queue, that is a follow-up, not this unit.
- **D5 — Delete the retired `CasesList` and reconcile the specs that name it.** PNL-APP-21
  forbids it owning the route and no surface mounts it; keeping a component nothing renders is
  dead weight (Rapsodia/Ponytail). Behaviour is preserved through `CaseActions` + `ClientFicha`
  and the backend route keeps its `AgendaPage` consumer. The three spec references are amended
  in the same change so no living spec describes a surface that no longer exists.
- **D6 — No new dependency, no new primitive.** The work reuses `Tabs`, `PageFrame` and the
  existing routing helpers.
- **D7 — The dashboard component is not changed unless a test proves it must be.** The reported
  defect lives in the shell's handling of the `cases` view, not in the dashboard's mapping. If
  `Dashboard.tsx` stays untouched, the change is smaller and the bug is fixed at its real
  source.
- **D8 — the `.cases-list__actions` rule is renamed to `.case-actions`, not deleted (owner decision 2026-09-27).** The plan said to drop the `CasesList` CSS section, but the rule is live: `CaseActions.tsx:43` is its only consumer and `ClientFicha.tsx:323` mounts that component. Deleting it would silently break the case action layout in the ficha, and no test covers the class (`CaseActions.test.tsx` does not assert it). The rename removes the stale `CasesList` name while preserving the rule for its real owner. `CaseActions.tsx` is added to the authorized files for this rename only. Recorded gap: after the rename, `.case-actions` has no test pinning it — if the owner wants it covered, that is a follow-up.

## Tasks

Forecast: **~220 added / ~370 deleted ≈ 590 changed lines** (code + tests + spec deltas), over
the ~400 review-focus budget. Deletions dominate; the removal is one coherent unit and would be
hard to review split by file. Proposed slices below; the chain strategy is the owner's call.

### WU1 — navigation and durability (T1, T2, T3) — DELIVERED on the branch

- [x] **T1** — the dashboard "Casos" entry lands on the Casos tab. `AppShell.navigate("cases")`
  resolves to `{ view: "conversations", conversationTab: "case" }`; no dispatch branch for a
  standalone `cases` view was added (D1). Pinned by a rendered-output test covering both the
  shortcut card and an urgent-case row. Commit `fecead6d`.
- [x] **T2** — `/panel/app/cases` is durable: `pathForView("cases")` and
  `pathForRoute({ view: "conversations", conversationTab: "case" })` return `/panel/app/cases`, so
  the normalization effect no longer rewrites the tab away. Commit `134333b7`.
- [x] **T3** — the queue tab is encoded for every tab (D3, corrected): `conversationTab` widened to
  `all | human | emergency | case | closed`; `case` -> `/panel/app/cases`, `all` ->
  `/panel/app/conversations`, the rest -> `?tab=<id>`, with unknown or malformed values falling
  back to `all`. The emergency acknowledgement test pins `POST /panel/api/cases/{id}/ack` (D4).
  Commit `a3c4b53b`.
- [x] **WU1 verification of record** — `cd web && npm run test` -> **91 files / 837 tests passed**,
  exit 0 (baseline 821; +16 tests); `npx tsc -b --noEmit` -> exit 0; `npm run build` -> exit 0;
  `git diff --check` clean. The orchestrator re-ran the full frontend suite itself and observed the
  same **837 passed**. **The backend suite was not run for WU1:** `git diff --stat e8717201..HEAD`
  touches only `web/` files, so it cannot differ from the `1533 passed` baseline; CI runs it on the
  PR.
- [x] **WU1 readback** — found two real defects and disproved one orchestrator hypothesis. Recorded
  in Progress, "WU1 readback record".
- [ ] **WU1 review measurement** — `gentle-ai review assess --cwd . --agent opencode
  --base-ref e8717201 --committed-only --json`; route only from its `next_transition`.

### WU2 — remove the retired surface (T4, T5)

- [x] **T4** — RED first: assert the app tree mounts no `CasesList` (the surface is retired) and
  that the destructive test edits fail on the current tree; then delete
  `components/pages/CasesList.tsx`, `stories/pages/CasesList.stories.tsx`,
  `stories/pages/CasesList.stories.test.tsx`, the `PanelLinks.test.tsx` import/render and the
  `style-boundary.test.ts` entry. The live action CSS was renamed to `.case-actions` under D8.
  Commit `c93f786f` (removal); class rename commit `d5cffdc1`.
- [x] **T5** — Reconcile the three living specs that name it (`panel-app/spec.md:61`,
  `panel-design-system/spec.md:742`, `corp-components/spec.md:21`) so they describe the tree
  that exists after the removal. Commit `a9c1dcb9`.
- [x] **WU2 verification of record** — `cd web && npm run test` → **90 files passed / 822 tests
  passed**, exit 0; the flaky `ConversationsList` test did **not** appear. `npx tsc -b --noEmit` →
  exit 0 (no output); `npm run build` → exit 0 (Vite built successfully; existing >500 kB
  chunk warning); `git diff --check` → clean. Count fell by **15** (837 − 822), matching the
  prediction exactly (14 story tests + 1 PanelLinks test).
- [x] **WU2 readback** — `.case-actions` has no test asserting its class name (D8); the focused
  `CaseActions.test.tsx` passed but does not pin the class, so coverage remains an explicit
  follow-up if the owner wants it. `rg -n "CasesList" openspec/specs/` returned only
  `panel-app/spec.md:164` and `:169`, preserving PNL-APP-21. Out-of-scope stale references in
  the unarchived `panel-grammar-global` change remain a flagged follow-up.
- [ ] **WU2 review measurement** — same command with `--base-ref` at the WU1 boundary.

## Acceptance criteria

1. The dashboard "Casos" entry (card and urgent rows) opens the Conversations destination with
   the Casos tab selected; it never renders Configuración.
2. `/panel/app/cases` renders with the Casos tab selected after a reload, a bookmark or a share.
3. No standalone `CasesList` surface is mounted anywhere (PNL-APP-21's scenario).
4. Case mutation semantics remain reachable: the queue acknowledges emergencies and the ficha
   exposes case status/responsible/ack.
5. `CasesList` and its story/tests/CSS are gone from the tree, and no living spec names it.
6. Only the authorized files change; no new dependency.
7. `cd web && npm run test`, `cd web && npx tsc -b --noEmit`, `cd web && npm run build` pass,
   and `uv run pytest tests/` stays at its baseline (**1533 passed**).

## Checks

- `cd web && npm run test`
- `cd web && npx tsc -b --noEmit`
- `cd web && npm run build`
- `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/`
- `git diff --check`

## Progress

- [x] Graph Check for WU2 from `/home/stefan/repos/lumat-agent`: queried
      `CasesList CaseActions primitives.css table__link panel specs`; consulted `CasesList()`;
      `CasesList.stories.tsx`; `CasesList.stories.test.tsx`; `PanelLinks.test.tsx`;
      `.table__link`; `CaseActions()`; `CaseActions.test.tsx`; `AppShell.tsx`;
      `pathForRoute()`; `ConversationsList()`; and `Corporate Components Capability`.
      `CaseActions.tsx` is in the `ClientFicha.tsx` community; `.table__link` is in the
      DS-UI-LINK link contract community. Directed paths from `CasesList()` to `CaseActions()`
      and from `CaseActions()` to `.cases-list__actions` were not found; the CSS-class consumer
      relationship is not a code edge, as the orchestrator verified by grep. Read
      `graphify-out/GRAPH_REPORT.md` (graph built from `7b205ea6`, before this WU2 base).
- [x] **WU2 recon (2026-09-27)** — The plan's CSS claim was disproved: `.cases-list__actions`
      has a live consumer (`CaseActions.tsx:43`), so the rule is renamed, not deleted (D8).
      Baseline on the clean tree at `059a275a`: `cd web && npm run test` → **91 files / 837
      tests**, with **1 pre-existing flaky failure** in `ConversationsList.test.tsx`
      (`it('requests search and page changes and renders empty state as a DOM row')`) that passes
      3/3 in isolation. Expected WU2 count: **822** (837 − 14 story tests − 1 PanelLinks test).
      Out-of-scope observation: the unarchived change
      `openspec/changes/panel-grammar-global/specs/panel-design-system/spec.md:16,37` still names
      `CasesList`. T5's authorized scope covers only the three `openspec/specs/*` files; if that
      change is archived later it could re-introduce the name. Flagged as a follow-up.

- [x] Worktree created (`rapso worktree create cases-route-alignment --yes`), provisioned
      (`uv sync`, `npm ci`), test DB up on `:5657`
      (project `lumat-test-lumat-agent-odd-cases-route-alignment`).
- [x] Baseline on the untouched worktree at `e8717201`: `uv run pytest tests/` →
      **1533 passed** (220.55s), exit 0; `cd web && npm run test` → **91 files / 821 tests
      passed**, exit 0.
- [x] Graph Check (Step 1) at plan time, from `/home/stefan/repos/lumat-agent`:
      `graphify query "panel navigation cases tab ConversationsList dashboard shortcut AppShell
      routes"`. Nodes consulted: `NAVIGATION` (`PanelShell.tsx:38`), `AppShell()`
      (`AppShell.tsx:41`), `ConversationsList()` (`ConversationsList.tsx:30`), `Dashboard()`
      (`Dashboard.tsx:110`), `Tabs.tsx`, `AppShell.tsx`, `Dashboard.tsx`,
      `ConversationsList.tsx`, `panelRoutes.ts`, `CasesList` (`CasesList.tsx`, community
      `ClientFicha.tsx`), `routes/conversations.py`, `services/cases.py`, `serializers.py`,
      `useAsyncData()`. Edges: `AppShell.tsx imports_from Dashboard.tsx`,
      `AppShell.tsx references panelRoutes.ts`, `AppShell.tsx imports_from ConversationsList.tsx`.
      Communities: `AppShell.tsx`, `Dashboard.tsx`, `ConversationThread.tsx`,
      `CasesList.stories.tsx`, `ClientFicha.tsx`.
- [x] **WU1 implementation** (writer sub-agent, bounded to the authorized files): commits
      `134333b7` (`fix(panel): preserve canonical cases route`), `fecead6d` (`fix(panel): align
      cases navigation with queue state`), `a3c4b53b` (`fix(panel): make queue tab URLs lossless`).
      `Dashboard.tsx` was **not** touched (D7 held): the defect was in the shell's handling of the
      `cases` view, not in the dashboard mapping. One test file outside the original list was
      touched and declared: `web/src/pwa.test.ts` asserts the `parsePanelPath('/panel/app/cases')`
      contract and had to follow the canonical tab id; no production file outside the authorized
      list changed.
- [x] **WU1 readback record — one hypothesis disproved, two defects confirmed.**
      The orchestrator's first readback hypothesised that leaving the Casos tab reset the queue to
      Todas, because `initialQueueTab` can only express `case | all`. **That hypothesis was false.**
      A throwaway reproducer (built, run, deleted; tree verified clean) showed Humanas stays
      selected. The writer had already been asked to reproduce it first and to stop if it did not
      fail — it did not fail, and it stopped without inventing a fix. That instruction is what kept
      a wrong diagnosis out of the branch.
      A second, measured readback then found the real defects:
      1. **Duplicate history write.** With a `pushState` spy, one click on Cerradas from the Casos
         tab produced **2 calls** (from `/panel/app/conversations`, Humanas and Casos each produced
         **1**). Leaving Casos changed the prop `case -> all`, the sync effect set the tab to `all`,
         Radix re-activated the clicked trigger and the handler fired again — so Back needed two
         presses. Fixed by the corrected D3 and pinned by a test that asserted `1` and observed `2`
         before the fix (`expected "pushState" to be called 1 times, but got 2 times`).
      2. **URL and visible tab diverged.** From Casos, clicking Humanas left
         `/panel/app/conversations` on screen while Humanas was selected, so a reload landed on
         Todas. The lossy channel was the cause; D3 now encodes every tab and this is pinned by a
         test that asserts the selected tab after the click and again after a fresh mount at that
         URL.
      A third item was a test-truth problem: the original
      `updates the queue tab from browser history and writes tab changes to the URL` asserted only
      the pathname after the clicks and its back/forward assertions passed for an incidental jsdom
      ordering reason. It was rewritten to drive explicit URLs and `popstate` events and to assert
      the selected tab at each step.

## Recovery

- Worktree: `/home/stefan/repos/lumat-agent-odd-cases-route-alignment`,
  branch `odd/cases-route-alignment`, base `e8717201`.
- Test DB: `bash infra/test-db.sh up|down|env`, project
  `lumat-test-lumat-agent-odd-cases-route-alignment`, port `5657`.
- On resume: read this file and reconcile the checkbox state against `git log` before
  continuing.
- Source of record: `.rapsodia-code/sessions/ready-for-odd/2026-09-25-clientes-crm/report.md`
  (U4 row) — read together with PNL-APP-21 in `openspec/specs/panel-app/spec.md:162-169`, which
  governs this unit.
