# ODD — panel-sidebar-refine

Base: `c58e91e1` (main). Worktree: `../lumat-agent-odd-panel-sidebar-refine`, branch `odd/panel-sidebar-refine`.
Sources: rendered visual review (this session) + owner's hands-on review of `npm run dev` on the main worktree.
References: `refs/Diseño Lumat/SideBar.png` (desktop expanded/collapsed), `refs/Diseño Lumat/headerShell.png` (shell header),
`refs/Diseño Lumat/mobileTablet/TabletPanelShell.png` (tablet rail + expanded menu), `refs/Diseño Lumat/mobileTablet/mobilePanelShell.png` (mobile nav + open menu).

## Objective

Bring the panel shell's sidebar and navigation surfaces to the reference design and fix the defects proven by rendering,
without rebuilding the design system and without inventing destinations, routes or tokens.

## Problem (all measured on `c58e91e1`)

1. **BLOCKER — tablet rail (640–1023) is unusable.** `PanelShell.tsx:163` renders `.panel-shell__nav-label` unless the React
   `collapsed` state is true, but the tablet tier is CSS-only (`primitives.css:1644`), so `collapsed` stays false and the
   label renders. `.panel-shell__nav-label` is declared exactly once (`primitives.css:1338`, only `min-width: 0` and
   `overflow-wrap: anywhere`) and is never visually hidden. Measured at 768: each label `0×224px`, each nav button `40×242px`,
   rail `scrollHeight 2197` inside a 900px viewport with `overflow: hidden` → destinations are unreachable.
2. **Double brand logo in the expanded sidebar.** `PanelShell.tsx:84-91` renders `lumat-logo.png` **and** `lumat-mark.png`
   when not compact; both are `display: block; width: 100%` inside a grid (`primitives.css:1064-1079`). Measured at 1440:
   both visible (176×64 and 40×38).
3. **Collapse/expand toggle lives in the wrong child surface, is oversized and shows the wrong glyph.** It renders inside the
   content header (`PanelShell.tsx:391-401`) as a 44×44 light-filled square, next to the separate back control, while the
   reference puts a small chevron control inside the sidebar header.
4. **Compact modes lose in-sidebar search.** JSX removes it when `collapsed` (`PanelShell.tsx:339`) and CSS hides it at
   tablet (`primitives.css:1644`). Measured at 768: `display: none`. The reference keeps a search icon control in the rail.
5. **No section separation in compact modes.** All three `.panel-shell__navigation-group` measure `border-top: 0px`; the shell
   relies on group titles (hidden when `collapsed`) plus a 16px margin. At 768 the titles are `display: none` → zero grouping.
   The reference uses a single divider line while keeping the same groups.
6. **Visible "Cerrar sesión" button in the sidebar footer.** `UserContext` (`PanelShell.tsx:113-124`) renders a full-width
   bordered button when `onLogout` is supplied; `primitives.css:1494` gives it `width: 100%`, a border and `--radius-sm`.
   The reference shows no logout control: it is reached only from the footer overflow menu.
7. **Mobile drawer header: brand not centered and no search field.** The drawer heading is `justify-content: space-between`
   (`primitives.css`) so the lockup sits left, and the drawer renders `<Navigation>` without search (`PanelShell.tsx:383`).
   The reference centers the lockup and shows a search field.
8. **Mobile bottom tab label truncates.** "Conversaciones" renders in a 68px span with `scrollWidth 91px`, so it clips to
   "Conversa…" (`primitives.css` gives the tab label `overflow: hidden; text-overflow: ellipsis; white-space: nowrap`).

## Adjudication rules applied

- **The archived canonical spec wins over the reference image.** Two consequences:
  - The reference mobile tab reads "Chats", but the canonical `DS-SHELL` requirement names the five destinations
    `Panel, Conversaciones, Asistente, Agenda, Clientes`. The destination set is not changed; only a mobile display label is
    introduced (S6), and that deviation is recorded here explicitly.
  - The reference header shows a single `<` control, but the canonical requirement lists a header "chevron". The owner has
    ruled that the reference is right for the toggle location. **Interpretation recorded:** the header "chevron" requirement
    is satisfied by the account control's own chevron; the collapse toggle belongs to the sidebar header. If a reviewer reads
    that requirement as the collapse control, this change must amend the canonical line rather than silently drop a control.
- **References control geometry and layout, not palette.** Colour differences against the reference are not treated as defects.
- Owner decision recorded: the expanded sidebar keeps its **named** section separators as they are today (no change).
- Owner confirmed both interpretations on 2026-09-30: the mobile tab gets a short **display** label while the destination set and
  the sidebar/drawer labels stay canonical; and the header "chevron" requirement is read as the account control's own chevron,
  so the collapse toggle may move into the sidebar header without dropping a control.
- Owner decision recorded: the toggle is a small explicit chevron control, **not** the brand logo made clickable (the brand is
  `role="img"` with accessible name "Lumat, panel operativo"; making it a button would pollute that name).

## Scope

**In:** brand rendering, collapse/expand toggle placement and size, compact (desktop collapsed + tablet rail) navigation,
in-sidebar search affordance in compact modes, section separation in compact modes, sidebar footer user block, mobile drawer
header, mobile bottom tab labels.

**Out:** palette and tokens, other primitives, other pages, the canonical specs, the archived change artifacts, the fixed-width
collapse behaviour, the desktop expanded section separators (owner accepted as-is).

## Constraints

- Files authorized: `web/src/components/domain/PanelShell.tsx`, `web/src/components/primitives/primitives.css`,
  `web/src/components/domain/PanelShell.test.tsx`, `web/src/components/domain/AppShell.test.tsx` (only if its bridge breaks),
  `web/src/stories/domain/AppShell.stories.tsx`, `web/src/stories/pages/PanelEntry.stories.tsx`.
- No new dependency, no new destination, route or parallel navigation model. Every destination and role filter keeps deriving
  from `NAVIGATION` and `panelRoutes`/`pathForRoute()`.
- The compact rail must keep every destination reachable and every control must carry an accessible name
  (canonical: "compact sidebar navigation with accessible names"). Visually hide the text; never remove the name.
- Verification for every task: `cd web && npm run test` and `cd web && npm run build`
  (the build is the only type-check path; a green Vitest suite does not prove the tree type-checks).
- Artifacts and code comments in English; user-facing UI copy in neutral Chilean Spanish.
- One work-unit commit per task, tests and docs alongside the behaviour, no AI attribution.

## Tasks

- [x] **S1 — single brand per state.** Expanded renders the lockup only; compact renders the mark only. Removes problem 2.
- [ ] **S2 — toggle into the sidebar header.** Small explicit chevron control inside the sidebar header (`«` expanded,
  `»` collapsed), keyboard reachable, focus-visible token ring; remove the oversized control from the content header.
  Removes problem 3. `aria-expanded`/`aria-controls` preserved.
- [x] **S3 — compact rail is icon-only (BLOCKER).** Visually hide `.panel-shell__nav-label` whenever the rail is compact
  (desktop collapsed **and** tablet tier), keeping the accessible name; assert no vertical text and no viewport overflow.
  Removes problem 1.
- [ ] **S4 — one divider between groups in compact modes.** Keep the expanded grouping, replace reliance on hidden titles with
  a single separator line. Removes problem 5. Must not change the expanded named separators.
- [ ] **S5 — search affordance in compact modes.** Icon-only control styled like the other rail icons (no button frame),
  reachable and named, per owner instruction. Removes problem 4.
- [ ] **S6 — mobile display label.** Mobile bottom tab renders a short display label so all five fit without clipping;
  sidebar and drawer keep the canonical `NAVIGATION` label. Removes problem 8. Owner decision; canonical line noted above.
- [ ] **S7 — sidebar footer.** Remove the visible "Cerrar sesión" button; expose logout from a footer overflow menu
  (reusing the existing account-menu treatment) with focus return to the trigger. Removes problem 6.
- [ ] **S8 — mobile drawer header.** Center the lockup and add the search field, matching the expanded sidebar behaviour.
  Removes problem 7.

## Acceptance criteria

- At 768: the rail is icon-only, every nav control has an accessible name, rail content fits the viewport, all nine authorized
  destinations are reachable, and the drawer still shows labelled navigation.
- No state renders two brand assets at once.
- The toggle is inside the sidebar header, small, with the correct glyph per state, and is the only collapse control.
- Compact modes show one divider between groups and no group titles.
- No visible logout button in the sidebar footer; logout is reachable from the footer menu and focus returns to its trigger.
- The mobile drawer header centers the lockup and shows a search field.
- All five mobile tabs fit without clipping.
- `npm run test` and `npm run build` pass; no canonical requirement is silently dropped.

## Debt recorded (NOT part of this unit)

- **User profile page does not exist.** The footer overflow menu should eventually offer it; do not add a dead entry.
- **Storybook stories do not pass `onLogout`**, so any prop-dependent chrome is invisible to Storybook-based visual review.
  This is why the visible logout button escaped the first rendered pass. Stories should supply the full prop surface.
- **Per-story `parameters.viewport.{width,height}` is inert config** in Storybook 8 (the addon reads `viewports` /
  `defaultViewport`), so story names like `TabletRail` / `MobileDrawerOpen` do not control the rendered width.
- **System-level decision pending:** the active mobile tab renders `--lime-500` 12px on `--primary-700` = 3.73:1
  (WCAG 1.4.3 fail); the pair recurs wherever a control is active on dark chrome, so it belongs to a system decision.
- From the rendered review, still open and out of this unit: `.kpi` carries `--shadow-1` and `--radius-md` (8px);
  raw unstyled `<button>Reintentar` in `Dashboard.tsx:104`; several in-scope controls compute `Arial` instead of Inter;
  `.dialog__close` is 28×30 (below 44px).

## Route decisions

| Task | Route | Trigger evidence |
| --- | --- | --- |
| S3 (blocker) | inline | one CSS rule + one JSX guard in files already read; no research needed |
| S1, S2, S7 | inline | single-component edits in already-read code |
| S4, S5, S6, S8 | inline, delegated verification per task | each touches one or two files with tests alongside |

## Progress and evidence

**S1 — single brand per state. DONE.**
Solution: CSS only, in `primitives.css`. The mark cannot be dropped from the JSX because the tablet rail swaps lockup→mark
through CSS (the tier is CSS-only), so the fix separates the shared declaration into an explicit
`.panel-shell__brand-image { display: block }` / `.panel-shell__brand-mark { display: none }` pair and restores the mark with
`display: block` in the collapsed sidebar rule, which previously set only its width.
Checks: `npm run test` → 92 files / 901 tests passed. `npm run build` → `tsc -b` + vite build OK.
Rendered verification (fresh `build-storybook`, Chrome, `iframe.html`):

| State | Viewport | Visible brand |
| --- | --- | --- |
| desktop expanded | 1440 | lockup only |
| desktop expanded | 1024 | lockup only |
| desktop collapsed | 1440 | mark only |
| tablet rail | 768 | mark only |
| tablet rail | 640 | mark only |

Before: desktop expanded rendered both (`lumat-logo.png` 176×64 **and** `lumat-mark.png` 40×38).

**S3 — compact rail is icon-only. DONE.**
Solution: CSS only, in the tablet media block of `primitives.css`. The label is visually hidden with the same sr-only
pattern already used by `.panel-shell__logout-label` (`position: absolute; 1px; overflow: hidden; clip; clip-path`), scoped
to `.panel-shell__sidebar` so the drawer keeps its readable labels. The scoping matters: the tablet tier is CSS-only, so the
drawer (which renders the same `Navigation` without `collapsed`) must not inherit the hidden treatment. The compact rail
button became a 44px square to meet the stated 44px touch-target contract while staying inside the 64px rail.
Guard added: `PanelShell.test.tsx` asserts all nine rail controls keep a non-empty accessible name, which fails if someone
deletes the label text to stop the wrapping.
Checks: `npm run test` → 92 files / 901 tests passed. `npm run build` → OK. Targeted `PanelShell.test.tsx` → 15 tests passed.
Rendered verification (fresh `build-storybook`, Chrome):

| State | Sidebar labels | Drawer labels | `railScrollHeight` | Rail button |
| --- | --- | --- | --- | --- |
| desktop expanded 1024 / 1280 / 1440 | 9 visible (102×16, `static`, no clip) | closed | 900 | 215×44 |
| desktop collapsed 1440 | none in the DOM (JSX omits them) | closed | 900 | 40×44 |
| tablet rail 640 / 768 | 9 hidden (1×1, `position: absolute`, `clip-path: inset(50%)`) | closed | **900 (was 2197)** | **44×44** |
| tablet drawer open 768 | 9 hidden | 9 visible (102×16) | 900 | 44×44 |

`everyBtnNamed` true in every state. The rule does not leak into the expanded desktop (labels report `static` + no clip).

Known remaining detail, folded into S4: the collapsed-desktop rail button is 40px wide while the tablet rail button is now
44px, so the two compact rails are slightly different sizes. Height is 44 in both.
