# Proposal: Panel Real Design — Page-First Storybook Workflow

## Intent

The panel foundation (67 tokens, 10 primitives, AppShell) is archived but renders no real screen — `app.tsx` is a bare auth gate, AppShell shows placeholders. This change recreates all 8 panel pages as Storybook page stories, visible and editable before production implementation. Production `src/components/**`, routes, and API wiring stay untouched.

## Scope

**In**: 8 page stories (CSF) + Login — Dashboard, Clientes list/ficha, Conversations list/thread, Cases, KB, Configuración. 5 story-local patterns at `web/src/stories/pages/_shared/`: DataTable, PageHeader, StatCard, EmptyState, FlashMessage. Typed mocks at `_shared/mockData/{dashboard,clients,cases,kb,settings,conversations}.ts` pinned to `web/src/types.ts`. Reuse dead-but-styled classes in `primitives.css` (`.table`, `.kpi`, `.empty-state`, `.flash-message`, `.spinner`) — zero new CSS.

**Out**: `web/src/components/**`, backend, API wiring, react-router, new dependencies, dark mode, Tabs, extra primitives.

## Capabilities

**Recommendation: reuse `panel-design-system` as a delta** — a composition layer over the archived foundation; a new capability would fragment the contract. **New**: None. **Modified**: `panel-design-system` — page-story workflow, 5 story-local patterns, typed mocks.

**Handoff (delta requirements for sdd-spec)**:
- R-PRD-PG-1 — 8 pages + Login under `web/src/stories/pages/*.stories.tsx`, via unchanged glob.
- R-PRD-PG-2 — Helpers under `_shared/`, never imported by `src/components/**`.
- R-PRD-PG-3 — Mocks typed to `types.ts`.
- R-PRD-PG-4 — Zero new CSS; `npm test` green.
- R-PRD-PG-5 — `npm run build-storybook` green.

## Approach

Auto-chain, stacked-to-main, ≤400 lines/batch, 5 batches: B1 `_shared/` helpers + mocks; B2 Dashboard + Clientes list; B3 ficha + thread; B4 Cases + Conversations list; B5 KB + Settings (+ Login). Each green on `npm test` + `build-storybook`; web-only diff.

## Open Decisions

1. **Conversations list** has no Jinja/API list endpoint — design from `Customer`/`Conversation` shapes; `GET /conversations` flagged as future gap.
2. **StatusBadge tones** cover conversation statuses, not Case statuses or Customer states — explicit tone maps in design.
3. **Story helpers are extraction candidates**; promotion to `src/components/` is later.

## Affected Areas

`web/src/stories/pages/*.stories.tsx` — New (9). `web/src/stories/pages/_shared/*.tsx` — New (5 + mocks). `web/src/components/**`, `app/**` — untouched guard.

## Risks

- Drift from production constraints (Med) — mocks typed to `types.ts`.
- Conversations list lacks backend source (High) — flag endpoint gap.
- Helpers leak into `src/components/` (Low) — PR guard.
- mockData bloat (Med) — mocks per page.

## Rollback Plan

Additive-only: new stories + helpers + mocks; no production file touched. Revert = delete batch commits or `stories/pages/`. Safe mid-batch.

## Dependencies

Archived `panel-design-system` foundation. No new npm dependencies.

## Success Criteria

- [ ] 8 pages + Login render in `build-storybook`.
- [ ] `npm test` + `build-storybook` green after every batch.
- [ ] No changes under `web/src/components/`, `app/`, `db/`, `infra/`.
- [ ] Typed mocks render in ≤400-line diffs.
- [ ] Each dead CSS class consumed by ≥1 story.
