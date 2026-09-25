# ODD: panel-section-headers

**Branch**: `odd/panel-section-headers`
**Worktree**: `/home/stefan/repos/lumat-agent-odd-panel-section-headers`
**Base**: `96ba8ca2` (= `main` at branch time)
**Status**: implemented — pending native review and owner visual acceptance

## Objective

Standardize every panel section header to one shared contract:

1. Every page header carries the **green left rail** (`--brand-lime`).
2. Every page header has a **title**.
3. Every page header has a **subtitle**, and the subtitle is **never inside a badge/pill**.
4. Typography is the one selected by the latest `DESIGN_SYSTEM.md` modification: **Inter via
   `--font-ui`**, page title at `--text-2xl` / `--weight-bold` / `letter-spacing: -0.02em`.

## Problem

The reference the owner pointed at (Dashboard) is a **local opt-in**, not a shared rule. Audit
on `96ba8ca2`:

- The rail lives only in `.dashboard-header::before` (`primitives.css:787-789`) and only three
  pages pass `headerClassName="dashboard-header"`: Dashboard (`Dashboard.tsx:156`),
  ConversationsList (`ConversationsList.tsx:69`), ConversationThread (`ConversationThread.tsx:90`).
  The other **26 `PageFrame` consumers have no rail**.
- The subtitle of the reference is itself a **badge**: `.dashboard-meta` is a pill with padding,
  border, background and `border-radius: 999px` (`primitives.css:790`). Five call sites put a
  pill or a `<Badge>` in the subtitle: Dashboard, ConversationsList, ConversationThread
  (`dashboard-meta`), ProjectsPage detail (`ProjectsPage.tsx:20`) and PlanningSessions detail
  (`PlanningSessions.tsx:54`).
- Four pages have **no subtitle at all**: `AutomationRuleDetailPage`, `KbDocumentDetail`,
  `PushSettings`, and `AdvancedDashboard` (which does not even use `PageFrame`: it renders a bare
  `<h2>` at `AdvancedDashboard.tsx:24`).
- In roughly ten pages the subtitle is `meta={data ? <copy> : undefined}`, so it **disappears**
  while loading, on error, and on empty states.

Typography is **already** compliant and needs no change — verified, not assumed:

- Inter is loaded by `tokens.css:1-4` (`@fontsource/inter` 400/500/600/700) and defined as
  `--font-ui: Inter, var(--font-sans)` (`tokens.css:198`).
- `.page-frame` applies `font-family: var(--font-ui)` (`primitives.css:760`).
- `.page-frame__titlebar h1` already sets `font-weight: var(--weight-bold)` and
  `letter-spacing: -0.02em` (`primitives.css:812-815`), so every `PageFrame` page already renders
  the Dashboard title treatment. `.page-header h1` already uses `--text-2xl`.

## Authority

- Latest `DESIGN_SYSTEM.md` typography change: `556743b5 docs(panel): amend visual foundation
  contract` — replaced the system stack with Inter through `--font-ui`.
- Owner-approved scope and subtitle copy (2026-09-25). Owner decision recorded in this session:
  standardization covers **all `PageFrame` consumers**, including the compatibility routes
  (Casos, Notificaciones, Notificaciones push, Dashboard avanzado).

## Scope

**In scope:**

- `web/src/components/primitives/primitives.css` — the shared rail and the removal of the
  `dashboard-header` / `dashboard-meta` rules.
- All page components under `web/src/components/pages/` that render a header, for the
  subtitle changes described below.
- `web/src/components/shared/PageHeader.test.tsx` — extend the CSS contract.

**Out of scope:**

- Any typography/token change. Inter, `--text-2xl`, `--weight-bold` and `-0.02em` are already in
  place; this unit only stops the per-page opt-in and flattens the subtitles.
- Dark mode, the 200% text-zoom reflow units (`odd/conversation-workspace-text-zoom`,
  `panel-text-zoom-reflow`), the parked 403 unit, and the `Asistente Lumat` / `Agente Lumat` nav
  label duplication.
- Section-level headings **inside** a page (`<h2>` region titles). This unit is about the page
  header only.

## Constraints (verified facts)

- **Strict TDD is ON** (`openspec/config.yaml:38`). Web runner: `cd web && npm test` (vitest run,
  `web/package.json:15`). RED before implementation, GREEN after, no invented evidence.
- Static gate: `cd web && npm run build` (`tsc -b`). No linter, no formatter in this repo.
- **CI gates pytest only.** The web suite is local evidence.
- UI copy is **Spanish**; code, identifiers, tests, comments and docs are **English**.
- Conventional commits, no `Co-Authored-By`, merge commits (not squash).
- CSS contract tests read the stylesheet with `readFileSync` — house pattern, precedent at
  `PageHeader.test.tsx:7-8` and `Dashboard.test.tsx:99-105`.
- `jsdom` has no layout: a vitest test cannot prove visual spacing. The rail's **presence and
  tokens** are asserted in CSS; the visual result is an owner acceptance step.

## Design decisions

- **D1 — The rail belongs to the base header.** Move it from the Dashboard-only class to the base
  `.page-header` rule (`primitives.css:761`), so inheritance replaces per-page opt-in. The three
  `headerClassName="dashboard-header"` props are removed and the dead rules deleted. The copy
  rules (`page-header__copy`, `page-header__actions`, responsive wrap) are untouched.
- **D2 — The subtitle is plain text.** `.dashboard-meta` (pill) and the inline `<Badge>` in
  subtitles are removed. The subtitle keeps the existing `.page-header p` treatment
  (`--text-sm`, `--corp-fg-muted`). Where the pill carried an inline icon (Dashboard), the icon
  may stay inline next to the text; it is not a badge.
- **D3 — Never absent, without churning the ready state.** The existing ready-state copy stays
  byte-identical (tests such as `AgendaPage.test.tsx:80` and `ClientesList.test.tsx:79` assert
  it). Only the `undefined` branches gain a stable fallback descriptor, so the subtitle renders
  in loading, denied, error and empty states too.
- **D4 — The four headerless pages get a subtitle**, and `AdvancedDashboard` is converted to
  `PageFrame` so it inherits the shared contract.

## Subtitle copy (owner-approved)

| Surface | Ready state (unchanged) | Fallback when data is absent |
| --- | --- | --- |
| Dashboard | `Actividad de los últimos N días · Desde X` | `Actividad reciente del negocio` |
| Clientes | `N clientes` / `1 cliente` | `Clientes del negocio` |
| Cliente ficha | `<phone> · Estado: <state>` | `Datos del cliente` |
| Agenda operativa | `N visitas` | `Visitas de la agenda` |
| Agenda técnica | freshness stamp | `Visitas asignadas` |
| Conversaciones | `N conversaciones` | `Cola de conversaciones` |
| Conversación | `#id · nombre · fecha` | `Detalle de la conversación` |
| Base de Conocimientos | `N documentos` | `Documentos de la base de conocimientos` |
| Documento de KB | — | `Contenido y versiones del documento` |
| Automatizaciones | `N reglas` | `Reglas de automatización` |
| Regla de automatización | — | `Define el evento y las acciones de la regla` |
| Casos | `N casos abiertos · M emergencias sin reconocer` | `Casos abiertos y emergencias` |
| Notificaciones | `N notificaciones` | `Notificaciones del panel` |
| Notificaciones push | — | `Avisos del navegador para este dispositivo` |
| Indicadores operacionales | `{start} – {end} · {timezone}` | `Indicadores operacionales del período` |
| Usuarios | `Administra el acceso al panel` | same (already static) |
| Configuración | `Preferencias globales del asistente` | same (already static) |
| Proyectos | `Explora los artefactos SDB` | same (already static) |
| Proyecto (detalle) | `{propósito} · {estado}` (sin badge) | `Detalle del proyecto` |
| Sesiones de planificación | `Trabajo de planificación durable de Cortex` | same (already static) |
| Sesión (detalle) | `Hilo N · {estado} · …` (sin badge) | `Detalle de la sesión` |

## Tasks

| ID | Task | Route |
| --- | --- | --- |
| **T1** | CSS contract test (RED): assert `.page-header` declares the rail (`::before` with `var(--brand-lime)`) and the base `.page-header p` declares no pill (`border-radius: 999px`, `background`). Extend `PageHeader.test.tsx`. | delegated writer |
| **T2** | Move the rail into base `.page-header` (`primitives.css:761`); remove `headerClassName="dashboard-header"` from Dashboard, ConversationsList, ConversationThread; delete the `.dashboard-header` and `.dashboard-meta` rules. | delegated writer |
| **T3** | Flatten the five badged subtitles: Dashboard, ConversationsList, ConversationThread, ProjectsPage detail, PlanningSessions detail. | delegated writer |
| **T4** | Always-present subtitle: add the fallback descriptor in every `meta={data ? … : undefined}` site, and add the subtitle to the four headerless pages; convert `AdvancedDashboard` to `PageFrame`. | delegated writer |
| **T5** | RED test per page family for the always-present subtitle on the loading branch (at minimum Dashboard, Clientes, Agenda, Conversaciones, KB, Automatizaciones), then GREEN. | delegated writer |
| **T6** | Full gate: `cd web && npm test` and `cd web && npm run build`, both green. Owner visual acceptance at 1366×768. | orchestrator |

## Acceptance criteria

- `.page-header` (not a per-page class) declares the `--brand-lime` rail; no page passes
  `headerClassName="dashboard-header"`; `.dashboard-meta` no longer exists.
- No subtitle anywhere is rendered inside a `Badge` or a pill.
- Every `PageFrame` consumer renders a subtitle in loading, ready, denied, error and empty states.
- Ready-state subtitle copy is unchanged where it already existed.
- `cd web && npm test` and `cd web && npm run build` are green.

## Verification evidence

Orchestrator-run at `4ac76faa`:

| Check | Command | Result |
| --- | --- | --- |
| Web suite (of record) | `cd web && npx vitest run` | **87 files / 745 tests passed** (94.9s) |
| Build / typecheck | `cd web && npm run build` | **built in 6.74s** (`tsc -b` + vite, existing >500 kB chunk warning only) |
| Leftover opt-in classes | `grep -rn "dashboard-meta\|dashboard-header" web/src` | no matches |
| Badge in a subtitle | `grep -rnE "meta=\{[^}]*<Badge" web/src/components/pages/*.tsx` | no matches |
| Every `PageFrame` has a subtitle | AST-lite scan of `<PageFrame>` opening tags | 20 page components, **every tag carries `meta`** |
| Raw `<h1>` outside `PageHeader` | `grep -rn "<h1" web/src/components/pages/*.tsx` | no matches |
| Components without `PageFrame` | scan of `web/src/components/pages/*.tsx` | only `AssistantTabs.tsx` (tab nav) and `LoginAuth.tsx` (login screen) — neither is a panel section |

TDD evidence: the CSS contract test was observed RED on `.page-header` missing `position: relative`
before the rail moved to the base. The per-page loading-subtitle tests were observed RED
(5 failed / 83 passed across the six covered files) before the fallbacks landed; the
`AutomationRulesPage` assertion was tightened after its first version matched the page title
instead of the subtitle.

Known suite-load flakes (NOT caused by this unit, verified by isolation runs): `AgendaPage >
creates an appointment from the agenda and refreshes the visible period` and `AppShell (T6.4) >
renders live data pages for every navigation view` can exceed the 5s per-test timeout under
full-suite load. Both pass in isolation, and the orchestrator's full-suite run above was green.

## Open items

- The rail's visual weight at narrow widths and with long titles is an owner visual-acceptance
  item (jsdom cannot measure it).
- `AdvancedDashboard` was a bare `<h2>`/`StateMessage` component with no `PageFrame`; converting
  it changes its DOM from a `<section>` to a `<main>`. Confirm no route nests it inside another
  `main`.
