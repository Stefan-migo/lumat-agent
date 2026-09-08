# Proposal: Panel UI/UX Skeleton

## Intent

The panel is functional but has mediocre UX: the sidebar mirrors engineering routes, mobile is poor, and login lacks a framed brand entry. Establish calm control-room chrome and task-based IA without changing APIs, data models, or page bodies. Keep all functionality reachable.

## Scope

### In Scope
- Replace route-inventory navigation with eight destinations: Panel unificado, Asistente Lumat, Conversaciones (Conversaciones|Casos), Clientes, Agenda, Base de Conocimientos, Automatizaciones, Configuración.
- Move notifications to a header bell with center and unread badge; put push settings under Configuración; preserve `/cases` and `/advanced-dashboard` aliases.
- Add dependency-free icons, responsive split login (mobile stack), and mobile-first drawer/rail tiers at 640/1024/1280 with touch targets and inert/focus handling.
- Tokenize `LoginAuth`/`PageHeader`; add Storybook states for shell widths, header badge/menu, and login split. Preserve PWA boundaries.

### Out of Scope
- Dashboard metric unification, advanced-dashboard redesign, conversation/cases or notification-center redesign, automation UX, or broad inline-style removal.
- New unread/realtime backend behavior, dark mode, or icon/font/router/PWA architecture dependencies.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `panel-app`: shell IA, chrome, login, segments, and compatibility routing change; auth and page contracts remain intact.
- `notification-center`: existing center stays reachable from header and read-state behavior remains authoritative.
- `panel-design-system`: shell/login surfaces consume existing tokens and reference responsive breakpoints.

## Approach

Update `PanelShell`, `AppShell`, and native `panelRoutes`; add no router. Preserve role filtering and confirm `Asistente Lumat` remains `adminOnly`. Define the badge as fetch-on-mount plus mark-read through `api.ts`, without realtime. Mount `PushSettings` in `Settings`, preserve page ownership, and add tests/stories.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `web/src/components/domain/` | Modified | IA, chrome, segments, aliases |
| `web/src/components/pages/` | Modified | Login, push, notifications |
| `web/src/components/primitives/`, `tokens/`, `stories/` | Modified | Responsive review surfaces |
| `web/src/pwa.ts` | Verified | Preserve PWA boundary |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Deep links regress | Med | Route tests and aliases |
| Badge semantics mislead | Med | Bounded API contract; no realtime |
| Mobile or PWA regressions | Med | Stories, mobile checklist, cache verification |

## Rollback Plan

Revert shell/UI commits to restore prior navigation, dispatch, login, and styles. Existing aliases and contracts make rollback non-destructive; invalidate stale shell assets if needed.

## Dependencies

- Existing web tokens, API, Storybook, and PWA registration.

## Success Criteria

- [ ] Approved destinations appear; notifications are reachable with a truthful badge and push is under Settings.
- [ ] Login/shell states pass narrow/desktop review; `/cases` and `/advanced-dashboard` resolve.
- [ ] `uv run pytest tests/` and `cd web && npx vitest run` pass; RDD/review flow is followed.
