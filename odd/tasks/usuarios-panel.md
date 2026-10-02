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

- [ ] `usuarios-001` — list and ficha display `name ?? username` (keep the "Usuario" header; keep
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

- (empty)

## Next step

Implement Slice 1 (`usuarios-001`).
