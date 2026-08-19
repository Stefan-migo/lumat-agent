# Delta for panel-design-system

## ADDED Requirements

### Requirement: R-PRD-PG-1 — Page Stories

The change MUST add a CSF story per page under `web/src/stories/pages/*.stories.tsx` (Dashboard, Clientes list/ficha, Conversations list/thread, Cases, KB, Settings, Login), composed from shared patterns and real content per exploration, and MUST NOT modify any file under `web/src/components/**`.

#### Scenario: Glob unchanged

- GIVEN `web/.storybook/main.ts`
- WHEN it is reviewed
- THEN the stories glob `../src/stories/**/*.stories.tsx` is unchanged

#### Scenario: Components untouched

- GIVEN the diff
- WHEN it is reviewed
- THEN no file under `web/src/components/**` is modified

### Requirement: R-PRD-PG-2 — Shared Story Patterns

The change MUST add DataTable, PageHeader, StatCard, EmptyState, FlashMessage as story-local helpers under `web/src/stories/pages/_shared/`, MUST NOT import them from `src/components/**`, and MUST consume existing `primitives.css` classes (`.table`, `.kpi`, `.empty-state`, `.flash-message`, `.spinner`) with zero new CSS.

#### Scenario: Helper exists

- GIVEN a page story needs DataTable, PageHeader, StatCard, EmptyState, or FlashMessage
- WHEN it is implemented
- THEN it resolves from `stories/pages/_shared/`, never from `src/components/**`

#### Scenario: Boundary guard

- GIVEN the applied change
- WHEN `src/components/**` imports are scanned
- THEN none reference `stories/pages/_shared/`

#### Scenario: CSS reuse

- GIVEN the diff
- WHEN CSS is reviewed
- THEN no new CSS is added; helpers consume existing `primitives.css` classes

### Requirement: R-PRD-PG-3 — Typed Mocks

The change MUST provide per-page mocks at `web/src/stories/pages/_shared/mockData/{dashboard,clients,cases,kb,settings,conversations}.ts`, typed against `web/src/types.ts` and matching serializer shapes.

#### Scenario: Typechecks

- GIVEN `web/src/types.ts`
- WHEN typecheck runs
- THEN mocks conform to `Kpis`, `Customer`, `Case`, `Doc`, `Settings`, `Conversation`

#### Scenario: Shape fidelity

- GIVEN serializer shapes in `app/panel/api/serializers.py`
- WHEN a mock is compared
- THEN field names and types match (snake_case, ISO dates, nullables)

#### Scenario: Per-page isolation

- GIVEN `_shared/mockData/`
- WHEN a page mock is loaded
- THEN it imports only its own mock module, no cross-page coupling

### Requirement: R-PRD-PG-4 — Tests Green

The change MUST keep `npm test` (vitest) green in `web/`, including story-helper tests.

#### Scenario: Suite green

- GIVEN the applied change
- WHEN `npm test` runs in `web/`
- THEN all tests pass, including helper and tone-map specs

### Requirement: R-PRD-PG-5 — Storybook Build Green

The change MUST keep `build-storybook` green, and the built index MUST include all 8 pages and Login.

#### Scenario: Build green

- GIVEN the applied change
- WHEN `npm run build-storybook` runs
- THEN it completes without errors

#### Scenario: Pages present

- GIVEN the built Storybook
- WHEN its navigation is inspected
- THEN all 9 page stories appear in the index
### Requirement: R-PRD-PG-6 — Page Content Fidelity

Each page story MUST render its Jinja authority fields: Dashboard (3 KPIs + Motivos + window caption); Clientes list (search + export CSV + table); ficha (customer card + state form + notes + history); thread (header + messages + no-reply note); Cases (table + inline update + acknowledge); KB (add-doc + docs table + disable/restore); Settings (6 form cards + spend snapshot); Conversations list (from `Customer`/`Conversation` types).

#### Scenario: Dashboard and lists fields render

- GIVEN the Dashboard and ClientesList stories
- WHEN they render
- THEN KPI cards, Motivos, window caption, search, export CSV, and the customer table appear

#### Scenario: Drill-down fields render

- GIVEN the ficha and thread stories
- WHEN they render
- THEN customer card, state form, notes, history, message table, and no-reply note appear

#### Scenario: Remaining pages render

- GIVEN the Cases, KB, Settings, and ConversationsList stories
- WHEN they render
- THEN their required fields appear

### Requirement: R-PRD-PG-7 — StatusBadge/Case Tone Maps

The change MUST define tone maps for Case statuses (abierto/escalado/en_evaluacion/cerrado) and Customer states (nuevo/activo/inactivo/bloqueado) to `Badge` tones; a test MUST assert the map covers every status.

#### Scenario: Map covers every status

- GIVEN the tone-map module in `_shared/`
- WHEN a test iterates all Case statuses and Customer states from `types.ts`
- THEN each maps to a valid `Badge` tone, none unmapped
