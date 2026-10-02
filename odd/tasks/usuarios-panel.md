# usuarios-panel

## Objective

Bring the `usuarios` section (`/panel/app/users`) in line with its references, implementing the
validated findings in `odd/analysis/usuarios/findings.md` (18 rows, validator PASS) that were not part
of the shared-primitive roll-up (PR #468, already merged).

## Problem

The section is functionally present but visually and behaviourally behind the reference: the list
shows the login `username` instead of the profile `name`, creation is an inline form instead of a
dialog, the list lacks the reference toolbar/cells/actions/footer, and the mobile breakpoint has no
card layout or action sheet.

## Why

The section references rule geometry; the owner ruled them right throughout. The machine
(`panel-section-analysis` v2) is image-first with the owner's visual analysis as the gate, and the
findings were validated before implementation.

## Scope

- In: `web/src/components/pages/UserManagement.tsx`, `web/src/components/pages/UserFicha.tsx`,
  their tests, and (only if required) `web/src/components/shared/DataTable.tsx`.
- Out: `web/src/tokens/tokens.css` (palette is settled; any change is a separate `token-palette`
  escalation), backend (the admin serializer already returns everything needed), and the other
  sections.

## Constraints

- Frontend-only. `infra-api-1` bind-mounts the **primary** worktree, so this worktree's backend code
  is not live; not needed here.
- References control geometry/layout, not palette. No white element backgrounds (owner advisory).
- Do not reopen palette or tokens.
- `username` is an immutable login identity; the UI displays the profile `name` with `username`
  fallback (owner decision). Identity comparisons (e.g. "is this me?") keep using `username`.
- Language: artifacts and comments in English; UI copy neutral Chilean Spanish.

## Authorized scope

`web/src/components/pages/UserManagement.tsx`, `web/src/components/pages/UserFicha.tsx`,
`web/src/components/shared/DataTable.tsx` (only if a shared change is genuinely required),
+ their tests. Analysis records under `odd/analysis/`.

## Slices (chained PRs)

Each slice is one reviewable work unit. `ask-on-risk` delivery: if a slice's forecast exceeds ~400
authored changed lines, split it before opening the PR.

- **Slice 1 — account name display** (`usuarios-001`): list + ficha show `name ?? username`.
- **Slice 2 — desktop/tablet list redesign** (`usuarios-002..013`, `usuarios-015`): create-user
  dialog, toolbar (search/filter/tabs), identity/role/status cells, actions menu, footer, and the
  `.data-region` card wrap.
- **Slice 3 — mobile** (`usuarios-014`, `usuarios-018`): card list + per-user action sheet.

## Checklist

- [x] `usuarios-001` — list and ficha display `name ?? username` (keep the "Usuario" header; keep
      identity comparisons on `username`). Route: inline (mechanical, 2 files, no design work).
      Checks: `web/src/components/pages/UserManagement.test.tsx`,
      `web/src/components/pages/UserFicha.test.tsx`, `npm run build`.
- [ ] `usuarios-002` — create-user form moves into a dialog (reuse `Dialog`).
- [ ] `usuarios-003` — search input in the list toolbar (`SearchInput`).
- [ ] `usuarios-004` — role filter (`Select`).
- [ ] `usuarios-005` — status tabs (`Tabs`).
- [ ] `usuarios-006` — avatar in the Usuario cell (`Avatar`).
- [ ] `usuarios-007` — "Tú" badge on the current account row (`Badge`).
- [ ] `usuarios-008` — role icon (`Icon`).
- [ ] `usuarios-009` — status pill (`StatusBadge`).
- [ ] `usuarios-010` — actions kebab menu (`Menu`).
- [ ] `usuarios-011` — own-account disabled-actions state.
- [ ] `usuarios-012` — result count in the footer.
- [ ] `usuarios-013` — pagination control in the footer.
- [ ] `usuarios-015` — wrap the table in `.data-region`.
- [ ] `usuarios-014` — mobile card layout.
- [ ] `usuarios-018` — mobile per-user action sheet.

## Acceptance criteria

- The section matches the reference geometry per breakpoint (owner visual gate).
- `npm run test` and `npm run build` pass; no regressions in the other sections that share the shell
  or the table primitive.
- Each finding's behaviour is observable (a test where the behaviour is assertable).

## Checks

- `cd web && npm run test`
- `cd web && npx tsc -b --noEmit`
- `cd web && npm run build` (the real type check)
- Re-capture and compare against the references for the owner's visual gate.

## Progress / verification

- `usuarios-001` — done at `6d328b99`. List (`UserManagement.tsx`), reset dialog, and ficha
  (`UserFicha.tsx` title + identity line) render `name ?? username`; identity comparisons still use
  `username`. Added two regression tests (name over username in both surfaces).
  Checks: `npm run test` → 956/956, `npm run build` → OK.
  Route: inline (4 files: two components + their tests; mechanical, no design work).

## Owner review — slice 2 (round 1)

Reference (desktop) governs. Fixes required:

- The search + role filter must live **inside the table card** (same card as the table). Remove the
  "Filtrar por rol" label — it is not in the reference and it breaks the filter.
- Buttons: the reference buttons are more square, less pill/oval.
- Tabs: the active indicator is greener (the reference lime).
- Usuario cell: avatar + name. Remove the raw `username` secondary line. The name must not render as a
  plain green HTML link. The avatar must look like the reference's initials circle, not a bare letter.
- Rol cell: the icon and the label have no spacing and look off/smaller than the reference.
- Estado: OK — add the dot to the badge.
- Acciones: the "…" kebab must be right-aligned; "Acciones no disponibles" must be centered.
- The actions popover (the "…" menu) is not designed — it needs the per-item icons and the
  design-system font.
- Footer: the "Mostrando X de X usuarios" legend is broken and the pagination is not styled like the
  reference and must be right-aligned (it sits next to the legend).
- The table treatment (card, toolbar, footer, status dot, tabs indicator, button shape) must be
  **shared**, so the other table sections inherit it.

Outcome:
- Applied (shared table vocabulary in `primitives.css` + `StatusBadge` dot + `.table__resource-name`
  plain, `DataTable` `.table__actions-cell`): toolbar inside the card with the label visually hidden,
  Usuario cell = avatar + name + "Tú" (no `username` line, no green link), Rol spacing, Estado dot,
  Acciones right-aligned and "Acciones no disponibles" centered, footer legend left + pagination
  right (`‹ 1 ›`), menu item icons. `Button` now forwards `aria-label` (was dropped though its type
  allowed it).
- **Escalated, not applied** (locked design-system contracts — the skill says do not reopen
  palette/tokens per section):
  - `.btn` border-radius is `var(--radius-pill)` and is asserted by `tokens.test.ts`. Making buttons
    "more square" is a global shape change affecting every button in the panel.
  - `.tabs__tab[aria-selected="true"]` uses `var(--chrome-950)` for a high-contrast active indicator,
    asserted by `Tabs.test.tsx`. The reference lime may not meet the contrast bar.
  Both were reverted after the refinement writer changed them and broke the contract tests. Pending
  the owner's decision on reopening the design system.

## Owner review — slice 2 (round 2)

Applied: filter icon moved INSIDE the select control and glyph changed to a sliders icon (closer to
the reference); "Acciones no disponibles" left-aligned (the reference keeps it left); `.menu__content`
now uses `var(--font-ui)` (the popover is portaled, so it was inheriting the body font); the avatar
now renders a visible circle.

Escalated further:
- Avatar fill. `.avatar` background is locked to `var(--surface-subtle)` by `Avatar.test.tsx`, but
  `--surface-subtle` resolves to the same value as `--surface`, so a filled circle was invisible.

Design-system reopen (owner decision, slice 2 round 2): the owner authorized reopening the three
locked contracts. Applied globally and the contract tests updated:
- `.btn` border-radius: `var(--radius-pill)` → `var(--radius-lg)` (10px, rounded-rect like the
  reference). Test: `tokens.test.ts`.
- `.tabs__tab[aria-selected="true"]` border-bottom-color: `var(--chrome-950)` → `var(--brand-lime)`
  (verified computed `rgb(171,195,51)`). Test: `Tabs.test.tsx`. Contrast note: lime on the light
  surface is below the WCAG 1.4.11 non-text 3:1 bar; the selected tab also switches text to
  `var(--text)`, but if AA is required use `--primary-700` instead.
- `.avatar` background: `var(--surface-subtle)` → `var(--border)` (visible filled circle). Test:
  `Avatar.test.tsx`.

This is a panel-wide design-system change, not usuarios-only: every button, tab and avatar changes.

## Slice 3 (mobile) + toolbar follow-up

Applied:
- Toolbar toolbar height: the role filter used `Select size="sm"` while the search control was md, so
  the filter was shorter. Changed the filter to the md control; both now match (owner review of the
  merged slice 2).
- `usuarios-014` / `usuarios-018`: below 40rem the list renders as cards (`.table-cards--mobile`) and
  the desktop table is hidden (`.table-card__desktop { display:none }`); each card carries the avatar,
  name (+ "Tú"), role, status pill and a kebab that opens a per-user action sheet (a `Dialog` styled as
  a bottom sheet on mobile) with "Restablecer contraseña", "Desactivar/Activar usuario" and "Cancelar".

Mobile refinements (owner rounds 3-5):
- Cards aligned: the `<ul>` kept the browser's default `padding-left`; reset `margin/padding/list-style`
  and restructured the card to two lines (name + "Tú" / role) with a larger avatar and the status pill
  + kebab in a trailing group.
- `PageHeader` shared rail moved from `.page-header::before` to `.page-header__copy::before`, so the
  lime rule covers only title/subtitle and the mobile action button sits outside it (matches the
  reference); mobile title bar stacks copy + full-width action.
- "Nuevo usuario" gained the `user-plus` icon (desktop + mobile).
- Action sheet matches the reference: drag handle, hidden dialog header (kept accessible via
  `aria-labelledby` with a clip-hidden header), the close X moved inside the user header row (same row
  as avatar + name), the status dot next to "Técnico · Activo/Inactivo" (green/amber), per-item
  chevrons, the deactivate icon in the warning tone, full-width "Cancelar".
- Toolbar: the role filter used the `sm` control; switched to md so both controls match height.

Border decision (owner): asked for an intermediate grey that keeps 3:1. There is no real room:
`--border-strong` (#7e858f) is ~3.1:1 on `--surface` and the WCAG test pins it (≥3 on `--surface`,
<3 on `--bg`). The control fill provides only ~1.09:1, so the border is the boundary. Kept the current
value; a visibly lighter border requires dropping below 3:1.

## Slice log

| Slice | Findings | Commit | PR | Status |
| --- | --- | --- | --- | --- |
| 1 | usuarios-001 | `6d328b99` | — | implemented, not pushed |

## Next step

Open the Slice 1 PR (pending the owner's go), then implement Slice 2.
