# Apply Progress: panel-design-system-final — Slice 1

## Status

Complete — tasks 1.1 and 1.2 are implemented and verified. The parent-authorized single assertion update in the AppShell story test reconciles a stale palette expectation. Both work-unit commits were created after the full suite and build passed.

## Task completion

- [x] 1.1 — WU1 palette and token guard.
- [x] 1.2 — WU2 final design direction documentation.

## Completed work

### WU1 — task 1.1: palette and token guards

- Changed `web/src/tokens/tokens.test.ts`: exact canonical palette checks, alias/color-mix resolution with fail-closed unsupported color handling, resolved no-pure-white surfaces, measured contrast assertions and decorative dispositions, radius/depth assertions, and removal of obsolete palette spot checks.
- Changed `web/src/tokens/tokens.css`: approved canonical roles and adjusted muted/warning values; semantic surfaces and corp aliases remain indirections; existing primary scale preserved; radius values tuned; raised elevation disabled for flat cards; status/decorative comments updated.
- Changed `web/src/tokens/tokens.ts`: retained the spacing/radius/z-index mirror subset and synchronized the radius values to CSS (10px/14px).
- Parent-authorized change in `web/src/stories/domain/AppShell.stories.test.tsx`: renamed the v1 cream-bg test to approved sage-bg guidance and changed only its expected value to `#dbe1d6`; the separate `--header-gradient` assertion remains unchanged.
- Focused RED: after extending the guard and before production edits, `cd web && npm run test` failed on the new palette/surface/radius assertions (token test: 4 failures; full suite: 91 files passed, 1 failed; 873 passed, 4 failed).
- Focused GREEN: `cd web && npx vitest run src/tokens/tokens.test.ts` passed, 21/21 tests.
- Final full suite passes after the parent-authorized obsolete assertion update. This assertion is intentionally redundant with the canonical token guard; record consolidation as a Slice 3 Ponytail finding, not a current edit.
- Build: `cd web && npm run build` passed after removing one unused local, including `tsc -b`; Vite emitted its existing >500 kB chunk-size warning.
- Ponytail: the finite resolver only implements the declared CSS forms in use (aliases, supported sRGB `color-mix()`, and hex). No simpler form preserves the required resolve-and-fail-closed behavior. No dependency or extra abstraction introduced.
- Rollback boundary: revert `web/src/tokens/tokens.css`, `web/src/tokens/tokens.test.ts`, and `web/src/tokens/tokens.ts` together; the mirror file is paired with tuned CSS radii.

### WU2 — task 1.2: direction documentation

- Changed `web/DESIGN_SYSTEM.md`: replaced stale cream/white and old geometry guidance with final role values, measured contrast results/dispositions, flat card/radius/shadow rules, responsive shell direction, no-dark-mode statement, and committed logo asset references; removed the obsolete production-logo convergence item and low-resolution-JPG warning.
- RED: added document-to-token consistency checks to `tokens.test.ts`; `cd web && npx vitest run src/tokens/tokens.test.ts` failed against stale documentation (2 documentation assertions failed).
- GREEN: after updating the guide, `cd web && npx vitest run src/tokens/tokens.test.ts` passed, 23/23 tests.
- Final full suite and build pass. Parent-authorized shell-story assertion remains redundant with the token guard; consolidate during Slice 3 only.
- Ponytail: documentation now states each final role once in its palette table; the existing comprehensive component and workflow sections remain intact. No simpler documentation reduction identified without discarding requested guidance.
- Rollback boundary: revert `web/DESIGN_SYSTEM.md` only; token guard additions should remain paired with WU1.

## Verification evidence

| Command | Observed result |
|---|---|
| `cd web && npm run test` (base safety net) | Passed: 92 test files, 876 tests. |
| `cd web && npm run test` (WU1 RED) | Expected RED: token suite had 4 assertion failures; 91 files passed, 1 failed; 873 passed, 4 failed. |
| `cd web && npx vitest run src/tokens/tokens.test.ts` (WU1 GREEN) | Passed: 1 file, 21 tests. |
| `cd web && npm run test` (after WU1/WU2 changes) | Failed: 1 stale, out-of-scope assertion in `src/stories/domain/AppShell.stories.test.tsx` expects `--bg: #F1F1E8`; 91 files passed, 1 failed; 878 passed, 1 failed. |
| `cd web && npm run test` (final, after parent authorization) | Passed: 92 test files passed (92); 879 tests passed (879). |
| `cd web && npx vitest run src/tokens/tokens.test.ts` (WU2 RED) | Expected RED against stale docs: 1 file failed, 2 documentation assertions failed. |
| `cd web && npx vitest run src/tokens/tokens.test.ts` (WU2 GREEN) | Passed: 1 file, 23 tests. |
| `cd web && npm run build` | Passed: `tsc -b` and Vite production build. Vite reports a chunk larger than 500 kB. |
| `cd web && npm run build` (final) | Passed: `tsc -b` and Vite production build; Vite reported a chunk larger than 500 kB. |
| `git diff --check` | Passed: no whitespace errors. |

## Ponytail finding — defer to Slice 3

The exact `--bg` value is asserted both in `web/src/tokens/tokens.test.ts` (canonical token guard) and `web/src/stories/domain/AppShell.stories.test.tsx` (shell story guard). The story-test copy is why the stale value survived. Slice 3 should consolidate the redundant assertion; it was retained here as explicitly directed.

## Parent-authorized scope adjustment

The parent authorized exactly one additional source file for Slice 1: `web/src/stories/domain/AppShell.stories.test.tsx`. Only the stale cream assertion's test name and expected value were changed; the `--header-gradient` assertion and all other assertions remain unchanged. This was necessary to align an existing shell test with the newly approved canonical `--bg` palette value.

## Graph check

- Graph report is stale: `GRAPH_REPORT.md` identifies build commit `96a6f69b`; this worktree is at `29f79311ad1e9b4998dea5af72035c8ff31a3221`. Per instruction, no rebuild was run.
- WU1 query consulted `tokens.test.ts`, `cssVars`, `resolveColor()`, `contrast()`, `web/src/tokens/tokens.css`, `tokens.ts`, and `web/package.json`.
- WU1 graph path query `tokens.test.ts` to `cssVars`: `tokens.test.ts --contains--> cssVars`; no direct directed path was found between `tokens.test.ts` and `tokens.css`.
- WU2 reused the same token guard and documentation-consistency node family; no second path query was run because both are the same affected token/doc relationship.
- Resumed apply query consulted `AppShell.stories.test.tsx`, `AppShell.stories.tsx`, `AppShell()`, `AppShell.tsx`, `tokens.test.ts`, and `web/package.json`. No directed path was found from `tokens.test.ts` to `AppShell.stories.test.tsx`; graph report remained stale and was not rebuilt.

## Commits

- `765eb23c` — `feat(tokens): apply approved panel palette and guards`
- `06618293` — `docs(web): document final panel design direction`

No push or remote operation was performed.

## Next step

Slice 1 is ready for the orchestrator's next SDD phase. Slice 3 should consider consolidating the redundant `--bg` assertion in the shell story test with the canonical `tokens.test.ts` guard; do not consolidate during this slice.

---

# Apply Progress: panel-design-system-final — Slice 2 (PR 2)

## Status

Complete — assigned tasks 2.1, 2.2, and 2.3 are implemented and verified. Scope stayed within shared primitive styles and the seven named focused tests; tasks 2.4/2.5 and all shell/dashboard work remain untouched.

## Task completion

- [x] 1.1 — WU1 palette and token guard (prior Slice 1 record preserved).
- [x] 1.2 — WU2 final design direction documentation (prior Slice 1 record preserved).
- [x] 2.1 — WU4a Button/Input semantic roles, boundaries, and focus.
- [x] 2.2 — WU4b Select/Textarea/SearchInput boundaries, invalid state reinforcement, and keyboard focus.
- [x] 2.3 — WU4c Badge/StatusBadge/Tabs semantic roles, readable status, and focus.

## Completed work

### WU4a — task 2.1: Button and Input

- Restyled primary actions with the measured `--chrome-950` / `--text-on-dark` pair and `--chrome-900` hover; secondary actions use the light `--surface` and `--border-strong` boundary. Danger action boundaries use `--border-strong` rather than the decorative status border.
- Text inputs use `--surface` and `--border-strong`, preserve visible focus and disabled labels, and use `--surface-subtle` for disabled fill.
- Added focused role/focus assertions in `Button.test.tsx` and `Input.test.tsx`; component APIs and interactive behavior remain unchanged.
- RED: wrote assertions before production changes; focused run failed with 2 assertion failures (18 passed).
- GREEN: focused Button/Input tests passed, 2 files / 20 tests. Build passed (`tsc -b` and Vite; existing >500 kB chunk warning).
- Follow-up boundary check found the danger button was using `--border-strong` over `--danger-bg`, although that role is approved only on `--surface`. RED: its new focused assertion failed (1 failed, 13 passed). GREEN: moved the danger button fill/hover to `--surface` and retained the semantic `--danger` text; hover reinforces danger with `--danger` border. Focused Button tests then passed, 1 file / 14 tests.
- Refactor: no further simplification retained a better form; final full suite passed after the boundary correction.
- Runtime harness: React Testing Library rendered Button and Input states through the focused test command; 20/20 passed. No separate browser/visual Storybook inspection was run.
- Rollback boundary: revert `web/src/components/primitives/primitives.css`, `Button.test.tsx`, and `Input.test.tsx` together.

### WU4b — task 2.2: Select, Textarea, and SearchInput

- Applied the shared measured surface/control-boundary roles to native field controls and SearchInput. Invalid controls retain the strong boundary with the semantic danger-border as inset reinforcement; their visible error text and ARIA wiring are preserved.
- Added keyboard `:focus-visible` feedback to fields without dropping the existing `:focus` indicator contract; SearchInput retains its wrapper `:focus-within` indicator.
- RED: new Select/Textarea/SearchInput assertions failed in 2 tests (12 passed); SearchInput's already-shared surface/focus contract passed at RED.
- GREEN: focused suite passed, 3 files / 14 tests. Build passed (`tsc -b` and Vite; existing chunk warning).
- Full-suite intermediate run exposed one stale assertion in the newly updated `Input.test.tsx` expecting the original `:focus` outline; corrected CSS to preserve that behavior alongside the keyboard `:focus-visible` rule. No out-of-scope file was changed. The final full suite passes.
- Runtime harness: React Testing Library rendered and exercised Select option changes, Textarea/SearchInput typing, and their accessible/focus contracts; focused suite 14/14 passed. No separate browser/visual Storybook inspection was run.
- Rollback boundary: revert `web/src/components/primitives/primitives.css`, `Select.test.tsx`, `Textarea.test.tsx`, and `SearchInput.test.tsx` together.

### WU4c — task 2.3: Badge, StatusBadge, and Tabs

- Neutral badges use muted text on the approved subtle surface. Semantic status badges retain their existing foreground/tint pairs; an explicit stylesheet comment records that status borders are decorative reinforcement only.
- Tabs use muted inactive text, primary text plus dark chrome underline when selected, and tokenized visible focus. Existing Radix keyboard/selection behavior remains intact.
- Added focused semantic role/status/focus assertions in Badge, StatusBadge, and Tabs tests. StatusBadge coverage asserts visible `Escalado` text with its tone instead of relying on color alone.
- RED: added assertions failed in 2 tests (11 passed).
- GREEN: focused suite passed, 3 files / 13 tests. Final full suite passed (92 files, 888 tests); build passed (`tsc -b` and Vite; existing chunk warning).
- Refactor: no extra abstraction introduced; the small decorative-status comment preserves the required meaning of the border contract.
- Runtime harness: React Testing Library rendered status and tab states, checked visible status text, and exercised click/keyboard activation; focused suite 13/13 passed. No separate browser/visual Storybook inspection was run.
- Rollback boundary: revert `web/src/components/primitives/primitives.css`, `Badge.test.tsx`, `StatusBadge.test.tsx`, and `Tabs.test.tsx` together.

## TDD Cycle Evidence

| Task | Test files | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 2.1 | `Button.test.tsx`, `Input.test.tsx` | Component/unit (RTL + stylesheet role contract) | Joint baseline for all 8 assigned focused-test files: 8 files / 38 tests passed | 2 failures / 18 pass; follow-up boundary assertion 1 failure / 13 pass | 2 files / 20 tests passed; follow-up Button suite 14/14 and final build passed | Different action variants, native disabled behavior, labels/errors and focus/surface contracts | Danger control now uses `--border-strong` only on `--surface`; final full suite confirms |
| 2.2 | `Select.test.tsx`, `Textarea.test.tsx`, `SearchInput.test.tsx` | Component/unit (RTL + stylesheet role contract) | 3 files / 11 tests passed | 2 failures / 12 pass | 3 files / 14 tests passed; build passed | Selection and text entry/search paths; invalid/disabled and keyboard focus paths | Preserved old `:focus` behavior while adding `:focus-visible`; final full suite confirms |
| 2.3 | `Badge.test.tsx`, `StatusBadge.test.tsx`, `Tabs.test.tsx` | Component/unit (RTL + stylesheet role contract) | 3 files / 10 tests passed | 2 failures / 11 pass | 3 files / 13 tests passed; final build passed | Multiple status tones, visible status labels, tab click and keyboard selection | No abstraction warranted; final full suite confirms |

## Verification

| Command | Observed result |
|---|---|
| `cd web && npm run test` (final, after WU4b focus and WU4a boundary corrections) | Passed: 92 test files, 889 tests. Existing React `act(...)` and jsdom navigation warnings were emitted; no test failed. |
| `cd web && npm run build` (final) | Passed: `tsc -b` and Vite production build; existing >500 kB chunk warning. |
| Focused WU4a command (`npm run test -- src/components/primitives/Button.test.tsx src/components/primitives/Input.test.tsx`) | Passed: 2 files, 20 tests. |
| Focused WU4b command (`npm run test -- src/components/primitives/Select.test.tsx src/components/primitives/Textarea.test.tsx src/components/primitives/SearchInput.test.tsx`) | Passed: 3 files, 14 tests. |
| Focused WU4c command (`npm run test -- src/components/primitives/Badge.test.tsx src/components/primitives/StatusBadge.test.tsx src/components/primitives/Tabs.test.tsx`) | Passed: 3 files, 13 tests. |
| `git diff --check` | Passed: no whitespace errors. |

## Graph check

- Read `graphify-out/GRAPH_REPORT.md`. Its report is stale (build commit `96a6f69b`) and freshness metadata is inconsistent; used only structurally, verified details against source, and did not rebuild.
- WU4a query consulted `Button()`, `Input()`, `SearchInput()`, their focused tests, `primitives.css`, and token consumers. Directed path query from `Button.test.tsx` to `primitives.css` found no directed edge; graph query surfaced both components and the shared stylesheet.
- WU4b query consulted `Select()`, `Textarea()`, `SearchInput()`, their tests, and `primitives.css`. Directed path query from `Select.test.tsx` to `primitives.css` found no directed edge.
- WU4c query consulted `Badge()`, `StatusBadge()`, `Tabs()`, their tests, and `primitives.css`. Directed path query from `Badge.test.tsx` to `primitives.css` found no directed edge.
- No graph edges were represented as direct dependencies absent source evidence. God nodes in the report include AppShell, Dashboard, and token/test hubs; the affected primitive nodes appear in the primitive/style community.
- Session-close incremental refresh was attempted once: `graphify /home/stefan/repos/lumat-agent-odd-design-system-primitives --update`. It exceeded the 120-second timeout after scanning 56 code and 36 documentation files; Graphify emitted a fail-closed warning about seven source files excluded from the current scan corpus, and skipped `tokens.css` as potentially sensitive. The command did not report successful completion; no second refresh or full rebuild was attempted.

## Commits

- `f24be2fe` — `feat(ui): restyle button and text input controls`
- `21c6ff0c` — `feat(ui): restyle selection and text entry controls`
- `947c75f5` — `feat(ui): restyle feedback and tabs`
- `7b91b186` — `fix(ui): keep danger action boundary on surface`

No push, PR creation, merge, branch, or worktree operation was performed.

## Next step

PR 2 is complete at tasks 2.1–2.3. Next slice is PR 3: tasks 2.4–2.5 only. This apply did not run independent browser Storybook visual review; review those controls at the supplied reference viewports before claiming rendered visual conformance.

---

# Apply Progress: panel-design-system-final — Slice 2 (PR 3)

## Status

Tasks 2.4 and 2.5 are complete and verified. The parent-authorized one-assertion correction reconciled the token guard with the approved flat-card contract; no token declarations or other assertions were changed.

## Task completion

- [x] 1.1 — WU1 palette and token guard (prior Slice 1 record preserved).
- [x] 1.2 — WU2 direction documentation (prior Slice 1 record preserved).
- [x] 2.1 — WU4a Button/Input.
- [x] 2.2 — WU4b Select/Textarea/SearchInput.
- [x] 2.3 — WU4c Badge/StatusBadge/Tabs.
- [x] 2.4 — WU4d Avatar/PageHeader/PageFrame/StatCard/EmptyState styles and shared contracts.
- [x] 2.5 — WU5 Card/DataTable/Dialog; flat non-white surfaces and dialog contract verified.

## Completed work and evidence

### WU4d — task 2.4

- Avatar initials and image APIs remain unchanged; initials now use the semantic `--surface-subtle` fill and `--text` foreground. PageHeader's decorative accent uses `--lime-700`; PageFrame structure and responsive action behavior are unchanged. StatCard/EmptyState markup and state behavior were untouched; their existing owning tests remain in place.
- RED: focused assertions failed on the old Avatar and PageHeader role declarations: 3 test files failed, 3 assertions failed, 5 passed.
- GREEN: `npm run test -- src/components/primitives/Avatar.test.tsx src/components/shared/PageHeader.test.tsx src/components/shared/PageFrame.test.tsx` passed, 3 files / 8 tests.
- REFACTOR: no behavior-preserving simplification remained; no new abstraction or component API change was introduced.
- Work Unit Evidence: focused command/result as above. Runtime harness: React Testing Library rendered initials/image and the shared page header/frame; no browser/Storybook runtime was used. Rollback boundary: revert commit `b4df9bc0` (stylesheet and its three paired tests) without touching the other unit.

### WU5 — task 2.5 (complete)

- Card and `.data-region` now use `--surface` with decorative `--border` hairlines and no material shadow. Dialog uses the non-white `--surface`, `--radius-xl` (~14px), decorative `--border`, and `--shadow-3`. DataTable semantics/API and dialog accessible name, modal semantics, close behavior, and controlled lifecycle remain unchanged. The existing DataTable-focused test did not pin an obsolete color/surface assumption, so it was not modified.
- RED: new focused Card/Dialog visual-role assertions failed before CSS changes: 2 files failed / 2 assertions failed; the pre-existing content and dialog behavior tests passed (5 passed).
- GREEN: `npm run test -- src/components/primitives/Card.test.tsx src/components/primitives/Dialog.test.tsx` passed, 2 files / 7 tests.
- REFACTOR: no extra abstraction added; styles remain token-only. Initial full suite identified a stale guard, resolved below under the exact parent authorization; final full suite and build pass.
- Work Unit Evidence: focused command/result as above. Runtime harness: React Testing Library rendered the Card and native Dialog and exercised modal/name/close lifecycle; no browser/Storybook inspection was run. Rollback boundary: revert commit `e005f226` (stylesheet and its two paired tests).

## TDD Cycle Evidence

| Task | Test files | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 2.4 | `Avatar.test.tsx`, `PageHeader.test.tsx`, `PageFrame.test.tsx` | Component/unit (RTL + stylesheet role contracts) | Passed: 3 files / 6 tests (included in initial five-file baseline) | 3 files failed, 3 failed / 5 passed | 3 files / 8 tests passed | Initials and source image; title/action layouts and PageFrame action fit | No API/state changes; focused, full suite, build passed before WU5 changes |
| 2.5 | `Card.test.tsx`, `Dialog.test.tsx`, `tokens.test.ts` | Component/unit (RTL + stylesheet role contracts) | Passed: 2 files / 5 tests (initial baseline) | 2 failures / 5 passed; later stale token guard RED 1 failure / 22 passed | Focused: 2 files / 7 tests; final full suite 92 files / 893 tests | Card surface vs Dialog surface/radius/shadow; existing Dialog modal name/close lifecycle retained | Parent-authorized single assertion updated to require no Card box-shadow; no token declarations changed |

## Verification

| Command | Observed result |
|---|---|
| `cd web && npm run test` (after WU4d, before WU5 CSS) | Passed: 92 test files, 891 tests. Existing React `act(...)` / jsdom navigation warnings; no failed tests. |
| `cd web && npm run build` (after WU4d, before WU5 CSS) | Passed: `tsc -b` and Vite build; existing >500 kB chunk warning. |
| `cd web && npm run test` (after WU5) | Failed: 91 files passed, 1 failed; 892 passed, 1 failed. Exact failing assertion: `web/src/tokens/tokens.test.ts:211` expects `.card` to set `box-shadow: var(--elevation-raised)`, contradicting the approved flat-card contract. Not edited because the assigned scope forbids token guard edits. |
| `cd web && npm run build` (after WU5) | Passed: `tsc -b` and Vite build; existing >500 kB chunk warning. |
| `cd web && npm run test` (parent-authorized assertion RED) | Failed as expected: `tokens.test.ts` 1 failed / 22 passed on the obsolete `.card` shadow expectation. |
| `cd web && npm run test` (final) | Passed: 92 test files, 893 tests. Existing React `act(...)` and jsdom navigation warnings; no failures. |
| `cd web && npm run build` (final) | Passed: `tsc -b` and Vite production build; existing >500 kB chunk warning. |
| `git diff --check` | Passed before WU5 commit. |
| `git diff --check` (authorized correction) | Passed. |

## Graph check

- Read the stale `graphify-out/GRAPH_REPORT.md`; build commit listed as `96a6f69b`, freshness metadata inconsistent. Used structurally and verified source directly; no graph rebuild.
- WU4d query surfaced `Avatar()`, `PageHeader()`, `PageFrame()`, `StatCard()`, `EmptyState()`, their named tests, and `primitives.css`; path query Avatar → stylesheet returned no directed edge (ambiguous source/target match warning).
- WU5 query surfaced `Card()`, `DataTable()`, `Dialog()`, their focused tests, and `primitives.css`; path Card → Dialog returned no directed edge (ambiguous target warning).
- Graph structure consulted: Avatar and Avatar.test in ConversationThread community; PageHeader, PageFrame, StatCard and EmptyState in shared component community; Card/DataTable in shared/toneMaps community; Dialog and Dialog.test in Dialog community; `primitives.css` as the shared stylesheet node. The relevant relationship is confirmed directly in component imports/tests and stylesheet class selectors.

## Commits

- `b4df9bc0` — `feat(ui): restyle shared page primitives`
- `e005f226` — `feat(ui): flatten panel surfaces and dialogs`
- `6cec4b22` — `fix(test): align card guard with flat-card contract`

No push, PR creation, merge, branch, or worktree operation was performed.

## Next step

PR 3 tasks 2.4–2.5 are complete. Do not touch slice 3/4 work, especially `style-boundary.test.ts`, or consolidate its duplicate `--bg` assertion here.

---

# Apply Progress: panel-design-system-final — Slice 3 (PR 4)

## Status

Task 3.1 (WU6, desktop shell) is complete. Scope is limited to the desktop sidebar/header presentation and paired behavioral tests; tablet/mobile/drawer behavior and deferred story/token assertions remain untouched.

## Task completion

- [x] 1.1 — WU1 palette and token guard (Slice 1 record preserved).
- [x] 1.2 — WU2 direction documentation (Slice 1 record preserved).
- [x] 2.1 — WU4a Button/Input.
- [x] 2.2 — WU4b Select/Textarea/SearchInput.
- [x] 2.3 — WU4c Badge/StatusBadge/Tabs.
- [x] 2.4 — WU4d shared page primitives.
- [x] 2.5 — WU5 cards, tables and dialogs.
- [x] 3.1 — WU6 desktop shell.
- [ ] 3.2 — WU7 tablet/mobile surfaces and modal drawer.
- [ ] 3.3 — WU8 shell stories and boundary guard.
- [ ] 4.1 — WU9 dashboard consumer.
- [ ] 4.2 — WU10 dashboard stories and responsive regression coverage.

## WU6 — task 3.1 evidence

- The sidebar search filters only role-authorized entries derived from `NAVIGATION`; those same entries are presented in General, Operación and Administración sections. Search is not shown in the compact rail state. Existing brand assets, expanded/collapsed navigation and user footer are preserved.
- Desktop header now includes a browser-history back action, existing route breadcrumb, notification surface, avatar/account menu and chevron. Account menu uses the existing identity/role and logout contract. Existing route bridge, notification behavior, role logic and `panelRoutes.ts` remain unchanged.
- RED: baseline focused tests passed (2 files / 34 tests); then full `cd web && npm run test` failed on both new expectations (missing in-sidebar search and missing Volver action): 1 failed file, 91 passed; 2 failed tests, 893 passed. No production code had changed at RED.
- GREEN: first focused cycle exposed an interaction with a pre-existing assertion that the account trigger is absent while the notifications popover is open; kept that established behavior by suppressing the account trigger while notifications are open. Focused result: 2 files / 36 tests passed.
- REFACTOR: retained local grouping/filtering in the existing `Navigation` renderer and made account/notification overlap mutually exclusive without touching their existing contracts. Re-ran focused tests and the full suite after the final implementation; both passed.
- Work Unit Evidence: focused `npm run test -- src/components/domain/PanelShell.test.tsx src/components/domain/AppShell.test.tsx` — 2 files / 36 tests passed. Runtime harness: same RTL component tests exercised search input, role-filtered groups, history back, notification availability, account menu, and logout callback; no browser/Storybook visual session was performed (visual conformance remains unclaimed). Rollback boundary: revert `PanelShell.tsx`, `PanelShell.test.tsx`, the desktop additions in `primitives.css`, and the 3.1 task/apply-progress records together.

## TDD Cycle Evidence

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 3.1 | `PanelShell.test.tsx` | React Testing Library component/runtime | 2 files / 34 tests passed | Full suite: 2 tests failed on absent search and back control (91 files passed, 1 failed; 893 tests passed, 2 failed) | Focused: 2 files / 36 tests passed | Operator role omits admin group; search returns matching existing entry; back action and account/logout exercised | Preserved notification/account mutual exclusion; focused and complete suite passed |

## Verification

| Command | Observed result |
|---|---|
| `cd web && npm run test` (RED) | Expected failure: 91 files passed, 1 failed; 893 passed, 2 failed. Both failures were new desktop-shell acceptance assertions. |
| `cd web && npm run test -- src/components/domain/PanelShell.test.tsx src/components/domain/AppShell.test.tsx` (GREEN) | Passed: 2 files, 36 tests. |
| `cd web && npm run test` (final) | Passed: 92 files, 895 tests. Existing React `act(...)` and jsdom navigation warnings were present; no failures. |
| `cd web && npm run build` (final) | Passed: `tsc -b` and Vite production build; Vite emitted its existing >500 kB chunk warning. |

## Graph check

- Read `graphify-out/GRAPH_REPORT.md`; its recorded source commit is stale (`96a6f69b`) and freshness metadata inconsistent. Used structurally and verified exact behavior against source; no rebuild.
- Queried the desktop `PanelShell` sidebar/search/grouping/header surface; graph surfaced `PanelShell()`, `NAVIGATION`, `AppShell.tsx`, shell test, and shared stylesheet nodes.
- Path checks confirmed `AppShell.tsx --imports_from--> PanelShell.tsx` and `PanelShell.tsx --references--> panelRoutes.ts`. `panelRoutes.ts` remains read-only. Relevant additional consulted nodes: `PanelShell.test.tsx`, `AppShell.test.tsx`, `primitives.css`, `NAVIGATION`, and the `PanelShell()` component.

## Scope and delivery

- Stacked-to-main PR 4 boundary: existing desktop `AppShell` → `PanelShell` through expanded/collapsed sidebar, search, grouped authorized navigation, footer and desktop header; PR 5 responsive surfaces remain pending.
- Changed files remain within the ≤5-file ceiling including the OpenSpec task/progress records. No AppShell route bridge, Dashboard, panelRoutes inventory, story, token test, logo asset, tablet/mobile surface or drawer lifecycle was changed.
- No push, PR creation, merge, branch or worktree operation was performed.

## Parent-authorized scope adjustment — WU5 correction

- Parent authorized exactly one assertion change in `web/src/tokens/tokens.test.ts`: replaced the `.card` `box-shadow: var(--elevation-raised)` required-match with a negative assertion that `.card` does not declare `box-shadow`.
- This follows design.md lines 45, 48–49 and 143 plus CST-PRIM-9 / DS-TKN-7. No other assertion in `tokens.test.ts` changed. `--elevation-raised: none`, `--elevation-overlay: var(--shadow-3)`, and all `--shadow-1..3` declarations remain unchanged.
- Strict TDD: focused RED observed 1 failed / 22 passed on the obsolete assertion; after replacing that single expectation, final full suite passed 92 files / 893 tests. Build passed.

---

# Apply Progress: panel-design-system-final — Slice 3 (PR 5, task 3.2 only)

## Status

Task 3.2 (WU7) is complete for PR 5. Parent split task 3.3/WU8 into PR 6 because the combined change approached the 400-line review budget. No task 3.3 work or `--bg` consolidation is included here.

## Scope and changed files

- WU7 shell implementation is in `web/src/components/domain/PanelShell.tsx` and `web/src/components/primitives/primitives.css`; focused behavior is tested in `PanelShell.test.tsx`. It adds the tablet icon rail, dark mobile header, exactly five approved tabs, and a native modal drawer, retaining route/role authority and handling focus, inertness, scroll restoration, Escape, navigation, resize, reduced motion, and 44px targets.
- Authorized query reconciliation: `AppShell.test.tsx` scopes all 12 duplicate-prone drawer-trigger queries to `.panel-shell__mobile-bar`. Its stale footer assertion now checks the ordered labels Panel, Conversaciones, Asistente, Agenda, Clientes, retains active/primary styling assertions, and opens/closes the header notifications dialog. `app.test.tsx` scopes its logout-flow trigger to the same mobile header.
- `PanelEntry.stories.test.tsx` changes only four drawer-trigger queries (original lines 72, 148, 173, 221) to a helper scoped within `.panel-shell__mobile-bar`; no story fixture or visual assertion changed.
- `web/src/test/setup.ts` provides jsdom defaults: `showModal()` sets `open`, `close()` removes `open`; configurable/writable descriptors preserve local spy overrides. Removed the unused resize-test mock bindings from `PanelShell.test.tsx`.
- No route authority, token tests, Dashboard, story content, or production code for the harness was changed. No style-boundary assertion was needed; no new shell source was introduced.

## TDD / verification evidence

| Evidence | Observed result |
|---|---|
| Initial focused RED: `npm run test -- src/components/domain/PanelShell.test.tsx src/components/domain/AppShell.test.tsx` | Failed: 11 failures / 31 passed; includes the old footer destinations and ambiguous tier trigger selectors. |
| Native dialog RED before shared setup: same focused command after the authorized query/footer fixes | Failed on jsdom `dialog.showModal is not a function` when AppShell tests opened the drawer. |
| Focused GREEN: `npm run test -- src/components/domain/PanelShell.test.tsx src/components/domain/AppShell.test.tsx src/components/primitives/Dialog.test.tsx` | Passed: 3 files / 47 tests after the shared setup methods were added. |
| Story-query GREEN: `npm run test -- src/stories/pages/PanelEntry.stories.test.tsx` | Passed: 1 file / 16 tests after the four queries were scoped to the mobile header. |
| `cd web && npm run test` | Passed: 92 files / 901 tests. Existing React `act(...)` and jsdom navigation warnings remain; no failures. |
| `cd web && npm run build` | Passed: `tsc -b` and Vite production build; existing >500 kB chunk warning. |

## Browser / graph / rollback

- Native browser support is evidenced by `web/playwright.config.ts` (`channel: "chrome"`, installed `@playwright/test`). The shared setup is a jsdom-only harness, not a production fallback or dependency.
- Graph check consulted `PanelShell()`, `NAVIGATION`, `AppShell.tsx`, `AppShell.test.tsx`, `PanelShell.test.tsx`, `PanelEntry.stories.test.tsx`, `setup.ts`, `primitives.css`, and `panelRoutes.ts`; confirmed `AppShell.tsx --imports_from--> PanelShell.tsx` and `PanelShell.tsx --references--> panelRoutes.ts`. `panelRoutes.ts` remains read-only. Graph report is stale at `96a6f69b`; no rebuild was performed.
- Rollback boundaries: responsive behavior — `PanelShell.tsx`, `PanelShell.test.tsx`, `primitives.css`; shared dialog shim and associated shell test reconciliations — `setup.ts`, `AppShell.test.tsx`, `app.test.tsx`, `PanelEntry.stories.test.tsx`; task record — `tasks.md` and this apply-progress section.
- PR boundary is PR 5 = task 3.2 only; PR 6 = task 3.3. No push, PR creation, merge, branch, or worktree operation was performed.

## Completion state

- [x] 1.1–1.2, 2.1–2.5, 3.1 (prior records preserved).
- [x] 3.2 — WU7 complete and verified.
- [ ] 3.3 — deferred to PR 6; no task 3.3 implementation is included here.
- Tasks 4.1 and 4.2 remain pending.

---

# Apply Progress: panel-design-system-final — Slice 3 (PR 6, task 3.3 only)

## Status

Task 3.3 (WU8) is complete. The existing responsive shell is represented by named Storybook states at all requested widths; no production shell code or boundary rules needed modification.

## Task completion

- [x] 1.1–1.2, 2.1–2.5, 3.1–3.2 — prior completed records preserved.
- [x] 3.3 — WU8 shell stories, responsive states and redundant token assertion consolidation.
- [ ] 4.1–4.2 — remain pending and untouched.

## WU8 — task 3.3 evidence

- `AppShell.stories.tsx` now has named mobile states at 390px and 640px, tablet at 768px, desktop at 1024px and 1280px, and a 1280px collapsed desktop state. `PanelEntry.stories.tsx` includes mobile header/tabs and drawer-open states, tablet rail/drawer states, and expanded/collapsed desktop states at 1024px/1280px. Existing story state fixtures were extended rather than duplicated.
- The `--bg` exact value check was removed from `AppShell.stories.test.tsx`; `tokens.test.ts` remains the canonical value guard. The separate no-`--header-gradient` check remains.
- No `style-boundary.test.ts` update was appropriate: no newly introduced shell source exists; the current shell source is already covered for inline SVG and the source-wide style-tag guard. No `dependency-boundary.test.ts` change was needed because no production-to-story import risk was introduced.
- Safety net: focused existing suite passed 3 files / 37 tests before changes. The authored story-coverage test RED failed because the new story exports were absent (1 expected failure); an intermediate failure after removing the duplicate fixture also caught its accidental coupling to the separate header-gradient check, which was preserved by retaining the token file read. No production behavior changed.
- GREEN: focused suite passed 3 files / 36 tests after removing the redundant `--bg` assertion and adding the named story exports. REFACTOR: no redundant new fixtures remained; the final full suite and build passed.
- Work Unit Evidence: `cd web && npm run test` passed 92 files / 900 tests; `cd web && npm run build` passed including `tsc -b` and Vite. Runtime harness: N/A — this work unit changes Storybook configurations only; existing RTL tests already exercise shell behavior, and no standalone Storybook/browser runtime was launched. Rollback boundary: revert only the two story files, `AppShell.stories.test.tsx`, this record and the task checkbox as one unit.
- Visual review limitation: stories configure the requested viewport/state combinations, but no browser screenshot inspection was run; rendered visual conformance is not claimed.

## TDD Cycle Evidence

| Task | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 3.3 | `AppShell.stories.test.tsx`, `PanelEntry.stories.test.tsx`, `style-boundary.test.ts` | Story module/guard unit tests and existing RTL | 3 files / 37 tests passed | New story export checks failed before story changes; no boundary assertion was applicable | Focused: 3 files / 36 tests passed | Named cases cover both desktop widths/states and mobile/tablet surfaces across 390/640/768/1024/1280 | Removed duplicate token assertion; retained the independent header-gradient guard; full suite/build passed |

## Verification

| Command | Observed result |
|---|---|
| `cd web && npm run test` (focused safety net) | Passed: 3 files, 37 tests. Existing React `act(...)` warnings. |
| `cd web && npm run test -- src/stories/domain/AppShell.stories.test.tsx` (RED) | Failed as expected on missing new responsive story export; an unrelated broken-reference failure from removing the shared token-source read was fixed by retaining that read for the independent header-gradient guard. |
| `cd web && npm run test -- src/stories/domain/AppShell.stories.test.tsx src/components/style-boundary.test.ts src/stories/pages/PanelEntry.stories.test.tsx` (GREEN) | Passed: 3 files, 36 tests. |
| `cd web && npm run test` (final) | Passed: 92 files, 900 tests. Existing React `act(...)` and jsdom navigation warnings. |
| `cd web && npm run build` | Passed: `tsc -b` and Vite production build; existing >500 kB chunk warning. |

## Graph check

- Read the stale `graphify-out/GRAPH_REPORT.md`; it identifies AppShell and shared story/test hubs; its source commit is `96a6f69b`, so it was used structurally and not rebuilt.
- Graph query surfaced `AppShell.stories.tsx`, `PanelEntry.stories.tsx`, `AppShell()`, `PanelShell()`, `style-boundary.test.ts`, and story test nodes. Path queries found no directed edge between AppShell and PanelEntry stories or from AppShell stories to the style boundary; no directed path was found from the AppShell story test to `tokens.test.ts`.
- Direct source confirms AppShell composes PanelShell; PanelEntry imports the Dashboard story and PanelShell. Both story modules are presentation consumers; the existing source-wide style-tag check, shell SVG check, and current dynamic style exception list were verified directly.

## Scope and delivery

- PR 6 boundary: task 3.3 only, stacked-to-main; no push, PR, merge, branch, or worktree operation.
- Changed project files are limited to two requested story modules, their existing AppShell story test for responsive exports and token assertion consolidation, and the OpenSpec task/progress records (5 files total). `style-boundary.test.ts`, `dependency-boundary.test.ts`, production shell, and Dashboard are unchanged.
- Authored changed-line count: 129 additions plus deletions (≤400); changed files: 5. Commits: `ff734a2b` (`test(shell): cover responsive story states`), `8c3be353` (`docs(sdd): record responsive story apply evidence`).
- No push or remote operation was performed.

---

# Apply Progress: panel-design-system-final — Slice 4 (PR 7, tasks 4.1–4.2)

## Status

Tasks 4.1 (WU9) and 4.2 (WU10) are complete and verified. This is the final assigned slice; prior slice records above remain intact. The dashboard shortcut to Casos is removed per the explicit owner override, while urgent cases remain in Hoy and the separate Casos queue route is unchanged.

## Task completion

- [x] 1.1–1.2, 2.1–2.5, 3.1–3.3 — prior completed records preserved.
- [x] 4.1 — WU9 dashboard behavior and visual consumer.
- [x] 4.2 — WU10 dashboard stories and responsive regression coverage.

## Completed work and TDD evidence

### WU9 — task 4.1

- Removed only the `Casos` item from dashboard quick-access destinations; urgent-case rows still navigate to the existing Casos queue. Existing API data, role-conditioned automation shortcut, Hoy entries, KPI/trend/motivo content, and loading/empty/error/denied/stale/partial states remain covered and unchanged.
- Dashboard styles now use flat non-white surfaces, semantic foregrounds, strong boundaries for interactive rows/cards, a dark semantic assistant card, and a two-column KPI layout at mobile widths. Urgent status remains explicit in text and icon; color is not its only signal. Obsolete per-destination accent styles were removed.
- RED: revised Dashboard/AppShell expectations first, then `cd web && npm run test` failed exactly on the two old `Abrir Casos` card renderings; 90 files passed, 2 failed; 897 passed, 2 failed (899 total). No production code had changed at RED.
- GREEN: `npm run test -- src/components/pages/Dashboard.test.tsx src/components/domain/AppShell.test.tsx src/stories/pages/Dashboard.stories.test.tsx` passed 3 files / 49 tests after implementation. Urgent-row routing remains to Casos; the bookmarked separate route/queue tests still pass.
- REFACTOR: removed the now-unused Case shortcut icon, destination accent map and inline accent styles; no extra abstraction or dependency added. Final full suite and build passed.
- Work Unit Evidence: focused command/result as above. Runtime harness: RTL rendered dashboard records and exercised urgent-case navigation into the real existing Casos queue; no browser/Storybook session was run. Rollback boundary: revert commit `8929476a` and its four files (`Dashboard.tsx`, `primitives.css`, `Dashboard.test.tsx`, `AppShell.test.tsx`) together.

### WU10 — task 4.2

- Added named `Desktop` (1280×900), `Tablet` (768×1024), and `Mobile` (390×844) Dashboard stories, reusing the existing Overview fixture and state stories. Story assertions verify the three viewports, no dashboard Casos shortcut, and the urgent Rosa row. No reference-driven Casos card was reintroduced.
- RED: added the responsive story contract first; `npm run test -- src/stories/pages/Dashboard.stories.test.tsx` failed because the named viewport exports were absent (1 failed / 7 passed). This was the deliberately stale expectation; not inferred.
- GREEN: the same story test passed 1 file / 8 tests; final full suite and build passed.
- REFACTOR: shared Overview story setup is reused directly; no additional fixture or component wrapper was needed.
- Work Unit Evidence: focused command/result above. Runtime harness: story module/RTL contract exercised via the focused Vitest command; no standalone Storybook/browser viewport rendering was run. Rollback boundary: revert commit `928ae00f` and the two Dashboard story files only.

## Contrast evidence and limitations

Measured exact semantic token pairs used by the revised dashboard stylesheet using WCAG 2.x sRGB relative luminance (normal text threshold 4.5:1; control boundary threshold 3:1):

| Actual role pairing | Ratio | Result / disposition |
|---|---:|---|
| `--text` on `--surface` | 14.40:1 | Pass |
| `--text-muted` on `--surface` | 5.04:1 | Pass |
| `--text-on-dark` on `--chrome-950` / `--chrome-900` | 12.70:1 / 10.58:1 | Pass |
| `--primary-200` assistant subcopy on `--chrome-950` | 11.36:1 | Pass; existing semantic brand text retained |
| `--danger` on `--danger-bg` (urgent label hover) | 5.74:1 | Pass |
| `--danger` on `--danger-tint` (urgent count/icon) | 6.01:1 | Pass |
| `--info` on `--info-tint` | 4.79:1 | Pass |
| `--border-strong` on `--surface` / `--danger-tint` urgent row | 3.09:1 / 3.40:1 | Pass as interactive boundary |
| `--focus-ring` on `--surface` | 5.02:1 | Pass for non-text focus indicator |

These are token-pair measurements, not a browser-computed audit of every rendered pixel, text size, state, or composited surface. No Storybook/browser screenshot review or assistive-technology run was performed; rendered WCAG conformance and visual-reference fidelity are therefore not claimed. No unresolved measured pair was found among the listed revised roles; unmeasured inherited combinations remain unverified.

## Verification

| Command | Observed result |
|---|---|
| `cd web && npm run test` (WU9 RED) | Expected RED: 90 files passed, 2 failed; 897 passed, 2 failed (899 total). Both failures were the new no-Casos-card assertions. |
| `cd web && npm run test -- src/components/pages/Dashboard.test.tsx src/components/domain/AppShell.test.tsx src/stories/pages/Dashboard.stories.test.tsx` | Passed: 3 files, 49 tests. |
| `cd web && npm run test -- src/stories/pages/Dashboard.stories.test.tsx` (WU10 RED) | Expected RED: missing responsive story export; 1 test failed, 7 passed. |
| `cd web && npm run test` (final) | Passed: 92 files, 900 tests. Existing React `act(...)` and jsdom navigation warnings remain. |
| `cd web && npm run build` | Passed: `tsc -b` and Vite production build. Existing >500 kB chunk-size warning remains. |
| `git diff --check` | Passed before commits; no whitespace errors. |

## Graph check

- Read the stale `graphify-out/GRAPH_REPORT.md` (built from `96a6f69b`; current branch was newer); used only structurally and verified details against source. No rebuild or refresh performed.
- Dashboard query consulted `Dashboard()`, `Dashboard.tsx`, `Dashboard.stories.tsx`, and nodes for Hoy urgent cases/data states. Path query established `Dashboard() <--imports-- Dashboard.stories.tsx`.
- Initial `Dashboard` → `primitives.css` path query found no directed path and reported ambiguous matches; a narrower area query surfaced Dashboard, Dashboard stories and urgent-case nodes, without evidence of a direct graph edge to the stylesheet. Source directly confirmed `.dashboard*` selectors in `primitives.css` style Dashboard.
- AppShell/Dashboard query consulted `AppShell()`, `Dashboard()`, `AppShell.test.tsx`, `Dashboard.test.tsx`, dashboard API and route nodes. No route inventory or route implementation node was edited. The separate Casos queue is verified by existing deep-link and navigation tests.

## Scope and delivery

- PR 7 boundary: tasks 4.1 + 4.2, stacked-to-main; no push, PR creation, merge, branch or worktree operation.
- Authored implementation diff: 47 additions + 43 deletions = 90 changed lines in six code/test/story files (≤400). Two OpenSpec bookkeeping artifacts are updated separately; total apply-record additions do not change the review-slice implementation budget.
- Commits: `8929476a` (`feat(dashboard): apply final system and remove Casos shortcut`), `928ae00f` (`test(dashboard): cover responsive states and owner override`); apply-progress/task bookkeeping commit follows.
- Skill resolution: `paths-injected`; no ponytail-review skill read was attempted.
- No push or remote operation was performed.
