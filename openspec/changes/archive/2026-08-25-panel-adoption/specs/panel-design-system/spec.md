# Delta for panel-design-system

## MODIFIED Requirements

### Requirement: R-PRD-PG-2 — Shared Story Patterns

The change MUST add DataTable, PageHeader, StatCard, EmptyState, FlashMessage as story-local helpers under `web/src/stories/pages/_shared/` (StateMessage, PageFrame, and toneMaps were added by later slices), MUST NOT define them under `src/components/**`, and MUST consume existing `primitives.css` classes (`.table`, `.kpi`, `.empty-state`, `.flash-message`, `.spinner`) with zero new CSS. `src/components/**` MAY import `_shared` helpers from `stories/` — the shipped precedent is `components/domain/ClientMemories.tsx`, which imports `DataTable` and `PageHeader` from `stories/pages/_shared`; the helpers MUST NOT be relocated out of `stories/` in this change.
(Previously: the boundary guard forbade any `src/components/**` import from `stories/pages/_shared/`. Panel adoption consumes the helpers from `components/pages/*` and the existing `ClientMemories` precedent, so the guard is amended to permit the import while keeping helpers defined in `stories/`.)

#### Scenario: Helper exists

- GIVEN a page component or story needs DataTable, PageHeader, StatCard, EmptyState, or FlashMessage
- WHEN it is implemented
- THEN it resolves from `stories/pages/_shared/`, and no helper is defined under `src/components/**`

#### Scenario: Components may import shared helpers

- GIVEN `src/components/**` consuming a page helper
- WHEN the imports are scanned
- THEN they reference `stories/pages/_shared/` (ClientMemories precedent) and no helper is redefined in components

#### Scenario: CSS reuse

- GIVEN the diff
- WHEN CSS is reviewed
- THEN no new CSS is added; helpers consume existing `primitives.css` classes

## Non-Goals

- Relocating `stories/pages/_shared/` into `components/` (cleanup slice later); token changes (palette frozen).