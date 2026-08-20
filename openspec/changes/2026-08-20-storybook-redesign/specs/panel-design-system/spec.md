# Delta for Panel Design System — Storybook Redesign

## ADDED Requirements

### Requirement: DS-UI-LABELS — Approved Spanish status labels

`StatusBadge` and `toneMaps` MUST map raw conversation/customer/case/KB states to approved Spanish labels: `Agente atendiendo`/`Atención humana`/`Cerrada`; `Nuevo`/`Activo`/`Inactivo`/`Bloqueado`; `Abierto`/`En evaluación`/`Escalado`/`Cerrado`; `Activo`/`Deshabilitado`/`Procesando`/`Error`. Raw values MUST NOT appear on non-technical views; `category=mode`/provider/model MUST stay separated from ordinary controls.

#### Scenario: List renders approved state

- GIVEN a story renders a conversation state
- WHEN the label renders
- THEN it is approved Spanish, never raw `bot`/`human`/`closed`

#### Scenario: Map covers every domain state

- GIVEN a test iterating all `types.ts` states
- WHEN each resolves through the maps
- THEN every state gets a tone and a non-empty label

### Requirement: DS-UI-LINK — Accessible link color

Normal-size links on light surfaces MUST use `--primary-700` and MUST NOT use `--primary-600`.

#### Scenario: Customer link passes contrast

- GIVEN a ClientesList customer-name link
- WHEN its color is measured
- THEN it is `--primary-700` at ≥4.5:1

### Requirement: DS-UI-FRAME — Shared page shell and banner language

A shared titlebar shell (lime rail + forest tint) and `StateMessage` MUST be promoted into `_shared/` and consumed by all 9 old page stories. Loading/empty/stale/partial-error/fatal-error banners MUST pair a semantic color with a visible label and `role="status"|"alert"`, never color alone.

#### Scenario: Banners announce meaning

- GIVEN an error or stale state
- WHEN a banner renders
- THEN it pairs a visible label, semantic color, and `role="alert"|"status"`

#### Scenario: Dashboard unchanged

- GIVEN the shared frame is adopted
- WHEN Dashboard renders
- THEN its proven look and tests stay green

### Requirement: DS-UI-STATES — Complete domain-state matrix

Each page MUST cover the states relevant to its workflow: lists (loading/empty/stale/error/permission), KB (processing/error/disable-confirmation), Settings (saved/saving/validation/server-error/stale), Login (error preserves username), Ficha (saving/validation/disabled).

#### Scenario: Workflow matrix renders

- GIVEN a list, Settings, KB, Ficha, or Login story
- WHEN its states are inspected
- THEN the full workflow matrix renders

### Requirement: DS-UI-PRIMS — Token-correct focus and motion

`primitives.css` MUST use `--focus-ring-width`/`--focus-ring` for outlines, `--duration-*`/`--ease-*` for transitions, and a `--info` spinner top with a duration token, with no hard-coded hex or magic values.

#### Scenario: Tokens replace magic values

- GIVEN a focused control and a spinner
- WHEN their outline and motion are inspected
- THEN they use the tokens and the drift guard stays green

### Requirement: DS-UI-LOGIN — Lockup and Spanish auth

Login MUST render the full Lumat lockup with `Usuario`/`Contraseña`/`Iniciar sesión`, an inline non-destructive error preserving the username, and MUST NOT reveal whether a username exists.

#### Scenario: Failed login keeps the username

- GIVEN a failed login with a valid username
- WHEN the inline error renders
- THEN the username persists, no existence leak appears

### Requirement: DS-UI-TABLES — Tabular numerals and Spanish tables

DataTable/StatCard MUST render comparable numbers with tabular numerals/right alignment, Spanish empty/action labels (`No hay registros`, `Acciones`), and loading/stale variants.

#### Scenario: Numbers align in Spanish

- GIVEN a numeric column or KPI
- WHEN it renders
- THEN numbers have tabular/right alignment and Spanish empty/action text

### Requirement: DS-UI-TONEFIX — Correct case tone on ClientFicha

ClientFicha MUST render case statuses via `caseStatusTone`, never `customerStateTone`.

#### Scenario: Case status uses case map

- GIVEN ClientFicha case rows
- WHEN a case status renders
- THEN its tone comes from `caseStatusTone`

### Requirement: DS-UI-COPY — Neutral Chilean Spanish

No English or voseo MAY appear on any Storybook surface (pages, helpers, primitives, mock copy).

#### Scenario: Scan finds no English or voseo

- GIVEN any rendered story surface
- WHEN its copy is scanned
- THEN only approved labels appear

### Requirement: DS-UI-STORY — Storybook contract per story

Each story MUST state purpose/guidance and meaningful controls, render representative states, and be verified at 390/640/768/1024/1280px with honest production-shaped mocks.

#### Scenario: Viewports verified

- GIVEN a defined story layout
- WHEN rendered at 390/640/768/1024/1280 px
- THEN no critical content or action is clipped
