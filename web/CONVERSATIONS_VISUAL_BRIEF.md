# Visual Brief: Conversaciones section UI/UX pass

Status: decided — compact row-cards, responsive by default
Scope: presentation only
Reference line: Dashboard (`web/src/components/pages/Dashboard.tsx`) + Concept/Gramática AI Agent (`web/src/stories/concept/AiAgentGrammar.stories.tsx`)

## Why this exists

The archived `panel-conversaciones-redesign` change delivered behavior (unified queue, tabs,
search, pagination, case-aware payloads, realtime refresh) but no visual work. Its specs encoded
zero visual requirements, so `16/16 compliant` passed while the section still renders a generic
`<table class="table">` and an unstyled right panel.

To avoid repeating that failure, the visual outcome is anchored to two concrete references that a
human can compare against, not to a test assertion.

## Goal

Make the Conversaciones section visibly match the Dashboard line by applying tokens and layout
patterns that already exist in the design system. No behavior change.

## Acceptance reference (the contract)

1. `web/src/stories/concept/AiAgentGrammar.stories.tsx` — the inspector, bubbles, header, composer,
   chips, and activity grammar. Target for the conversation workspace.
2. `web/src/components/pages/Dashboard.tsx` — section heads, row language, pill counts, hover,
   focus, urgent tint. Target for the queue.
3. `web/DESIGN_SYSTEM.md` sections "Conversaciones and human inbox" and "Casos" for copy and
   behavior rules (labels, read-only thread, disabled composer reasons, emergency surfacing).

Acceptance = a human renders the section and confirms it reads as the same product as the Dashboard,
on desktop, tablet, and mobile. Green tests are necessary but not sufficient.

## Non-goals (Ponytail guard)

- No backend, API, `types.ts`, `realtime.ts`, or routing changes. Those are already correct.
- No new dependency, state library, cache, or data.
- No KPI row (already rejected in the original design decisions).
- No big airy bento tiles. Row-cards are compact, like `.dashboard__row`, not `.dashboard__card`.
- No new component abstraction unless a second real consumer appears; inline is fine.
- No fixed `captured_data` schema.
- Do not keep the `<table>`. The queue becomes a semantic list of row-cards.

## Gap to close (current state)

| Location | Now | Problem |
|---|---|---|
| `ConversationsList.tsx` | Renders `DataTable` -> `<table class="table">` | Generic table; visually the same as pre-redesign |
| `ConversationThread.tsx:45,91` | `conversation-workspace` / `conversation-workspace__context` | **Zero CSS rules**; the "right panel" is an unstyled stacked `<aside>` |
| `primitives.css` | `.ai-agent-grammar__inspector`, `__detail`, `__chips`, `__chip`, `__actions` exist and are styled | Redesign invented an unstyled class instead of reusing these |
| `primitives.css` | `.ai-agent-grammar__filters` | Missing; the filter bar uses it with no styles |
| `primitives.css` | `.ai-agent-grammar__processing` | Missing (used by the concept story) |

## Component 1 — Queue (`ConversationsList.tsx`)

Target: a semantic list (`<ul>`) of compact operational row-cards, following the `.dashboard__row`
language. Not a table, not bento tiles.

Row anatomy (`.conversations-queue__row`), grid with `--space-3` padding, `1px` `--corp-border`,
`--radius-md`, `--brand-bg-elevated` background:

- **Leading rail**: a `--space-1` full-height bar. `--brand-lime` when selected; `--danger` when an
  unacknowledged emergency; transparent otherwise.
- **Identity** (primary open target): customer name (`--text-sm`/`--weight-semibold`) and phone
  (`--text-xs`, `--corp-fg-muted`).
- **Badges**: `StatusBadge` for conversation state; `StatusBadge status="escalated"` for a live
  emergency; case priority otherwise.
- **Summary**: single muted line, `text-overflow: ellipsis` with a bounded `max-width`.
- **Recency**: `.dashboard__row__time` treatment — primary color, `--text-xs`,
  `font-variant-numeric: var(--corp-value)`; show date + time, not a raw `slice(0,10)`.
- **Actions**: `Tomar` (primary when `state === "bot"`) and `Reconocer emergencia` (secondary) when
  applicable; the identity area opens the thread. Do NOT nest action buttons inside a clickable row.

Row states, mirroring the Dashboard:

- Hover: border-color `--primary-500`, subtle `--primary-700` tint, `--shadow-1`, `translateY(-1px)`.
- Selected (`aria-current="page"`): lime leading rail + `--primary-100` tint. Never color-only.
- Emergency/unacked: `--danger-tint` background + `--danger-border` and a `--danger` rail, mirroring
  `dashboard__row--urgent`.
- Focus: `--focus-ring-width` outline with `--focus-ring-offset`.

Semantics: `<ul role="list">` + `<li>`. The open target is a real `<button>` (or link) inside the
card, and action buttons are siblings — never nested inside it. `aria-current="page"` on the open
target of the selected row.

Header and toolbar:

- `PageFrame` title/meta stay; meta shows total count.
- Filter toolbar (`.ai-agent-grammar__filters` or a dedicated `conversations-queue__toolbar`): flex
  row, search grows, `Reintentar` secondary, Dashboard section spacing (`--space-3`).
- `Tabs`: keep. Render counts as the Dashboard pill count treatment (`--brand-bg-elevated`,
  `border-radius:999px`, `--text-xs`, `--weight-semibold`), danger variant on Emergencias when > 0.
- `pagination` primitive: align spacing and button height with the toolbar.

## Component 2 — Workspace (`ConversationThread.tsx`)

Target: a real two-column workspace: thread main area + styled inspector on the right.

- Wrapper `.conversation-workspace`: new rule
  `grid-template-columns: minmax(0,1fr) calc(var(--space-8) * 4.5); gap: var(--space-0)`.
  The app shell already owns the left rail, so do NOT use `.ai-agent-grammar__shell` (3-col).
  Collapse to a single column below `64rem` (the grammar inspector already hides at that width).
- Main area: reuse `ai-agent-grammar__main`, `__header`, `__title`, `__freshness`, `__window`,
  `__thread-area`, bubbles, `__handoff`, `__composer`, `__composer-hint`, `__composer-actions`,
  `__reason`. These are already styled and already used.
- Right panel: replace `conversation-workspace__context` with `ai-agent-grammar__inspector` and
  restructure into `<section><h2>…</h2><dl><div class="ai-agent-grammar__detail">…</div></dl>`
  blocks:
  - **Cliente**: name + phone_e164 (detail rows).
  - **Caso**: service, status, priority, responsible, emergency + ack state; emergency action uses
    `.emergency-action` (secondary).
  - **Datos capturados**: keep the collapsible `<details>`, render as `__detail` rows (key/value),
    not raw `<p>`.
- Empty/error/loading: keep existing primitives; ensure they render inside the workspace frame.

## Responsive — mobile and tablet

Breakpoints follow `DESIGN_SYSTEM.md`. Row-cards stack natively, so mobile needs no special markup.

**>= 1024px (desktop).** Row-card on a single horizontal grid: identity | badges | summary |
recency | actions.

**640-1023px (tablet).** Two-line layout: identity + badges + recency on the first line, summary on
the second, actions on the trailing edge. Reduce padding to `--space-2`.

**< 640px (mobile).** Fully stacked: identity, badges, summary, recency, then actions as a
full-width wrapping button group. Touch targets >= 44px (DESIGN_SYSTEM: 40px min, prefer 44px for
frequent/risky/touch actions).

Shared small-screen rules:

- Tabs scroll horizontally (`overflow-x: auto`), like the grammar nav at `40rem`.
- Toolbar and pagination stack vertically; search full width.
- The workspace inspector is already hidden below `64rem`, so the thread owns the full width.
- Hard rule from `DESIGN_SYSTEM.md`: never hide emergency, handoff, send, acknowledge, save, or
  retry actions to make a cleaner small-screen layout.

## Files to touch

| File | Action |
|---|---|
| `web/src/components/primitives/primitives.css` | Add the `.conversations-queue` row-card block, toolbar, `__processing`, workspace grid, and the mobile/tablet media queries |
| `web/src/components/pages/ConversationsList.tsx` | Replace the `DataTable` render with the `<ul>` row-card queue; remove the `DataTable` import; adjust recency formatting and truncation |
| `web/src/components/pages/ConversationThread.tsx` | Remap workspace wrapper + context to grammar classes and inspector structure |
| `web/src/components/pages/ConversationsList.test.tsx` | Replace the table-semantics assertion with row-card assertions; keep all behavior tests (tabs, search, pagination, actions) |
| `web/src/components/pages/ConversationThread.test.tsx` | Update only if the inspector structure changes existing assertions |

`DataTable.tsx` is not touched; other pages keep using it.

## Verification

- Human visual comparison against the two references above at desktop, tablet, and mobile widths
  (primary gate).
- `cd web && npx tsc -b` passes.
- `cd web && npm test` passes after the queue assertions are updated; no behavior regression.
- Existing a11y preserved: `aria-current` on the selected row's open target, `role="status"` /
  `role="alert"`, `aria-label` on regions and actions. List semantics, not fake table semantics.
- Responsive pass at 375px, 768px, 1280px: no clipped content, no hidden critical actions, touch
  targets >= 44px on mobile.

## Slicing (review budget)

Estimated 350-450 changed lines. Two natural slices if the budget is exceeded:

1. Queue visual pass: `primitives.css` (queue block) + `ConversationsList.tsx` + its test.
2. Workspace visual pass: `primitives.css` (workspace grid) + `ConversationThread.tsx` + test.

Each slice is independently revertible and does not touch the backend.

## Resolved decision

The queue becomes a semantic list of compact operational row-cards. This matches the Dashboard line,
handles mobile and tablet natively with no reflow hack, and avoids the duplicate-label accessibility
problem of a CSS-reflowed table. Density tradeoff accepted: a card is taller than a table row, which
is fine at `limit 20` on a prioritization surface.

## Wave 2 — shell, page chrome, filters, and row actions

Reported from a real panel capture. All items are presentation plus the shell dead-code removal; no
backend change (the queue API already supports `responsible_id`, `q`, `limit`, `offset`, `counts`).

### 2.1 Remove the dead section tabs (this also fixes the giant gap)

Root cause: `.panel-shell__content-area` (`PanelShell.tsx:424`) is
`grid-template-rows: auto minmax(0, 1fr)` but has **three** direct children:
`.panel-shell__header-row`, `.panel-shell__conversation-tabs`, and `.panel-shell__content`. The tabs
div lands in the `1fr` row and stretches to the remaining viewport height, producing a ~350px empty
band and pushing the page into an implicit third row.

- Remove the `.panel-shell__conversation-tabs` block (`PanelShell.tsx:469-482`).
- The tabs are also functional dead code: `conversationTab` is only used for their `aria-pressed`,
  and is never passed to `ConversationsList`. Remove the now-unused `conversationTab` /
  `onConversationTabChange` props from `PanelShell` and their wiring in `AppShell`.
- There is no `.panel-shell__conversation-tabs` CSS; do not add any.
- Preserve the `/cases` deep link: pass the parsed conversation tab into `ConversationsList` as its
  **initial queue tab** (`cases` -> `case`, otherwise `all`). Update `AppShell.test.tsx` and any
  `PanelShell` test that passes the removed props.

### 2.2 Page header matches the Dashboard

The Dashboard header treatment lives in the page-scoped `<style>` inside `Dashboard.tsx`
(`.dashboard-header` lime rail + `.dashboard-meta` pill + title typography), so it is not reusable.

- Promote that header treatment into `primitives.css` as shared classes, keep `Dashboard.tsx` using
  the shared class (remove the duplicated rules), and apply it to `ConversationsList`.
- ConversationsList keeps its own title/meta text, with correct singular/plural
  (`1 conversación` / `N conversaciones`).

### 2.3 Tighten the vertical rhythm

- The gap between the title block and the first content block is too large
  (`.page-frame { gap: var(--space-5) }` plus titlebar padding). Reduce it for this page without
  regressing other pages: prefer a scoped modifier/class over changing the shared `PageFrame`
  contract.

### 2.4 Style the realtime status message

- The bare `<p role="status">` ("Conexión en tiempo real: desconectada…") is unstyled and reads too
  large. Render it as a subtle banner: `--text-xs`/`--text-sm` muted text with a small icon and an
  info tone. Keep the existing conditional rendering and `role="status"`. Apply the same treatment to
  the equivalent message in `ConversationThread.tsx`.

### 2.5 Search toolbar and assignment filter (approved)

- Toolbar: `SearchInput` grows, plus an assignment filter, plus the secondary `Reintentar`.
- Assignment filter: `Todas` / `Asignadas a mí`. It maps to the existing `responsible_id` query
  param. `ConversationsList` receives the current user id via a new prop from `AppShell`
  (`user.id` is optional — only render the "Asignadas a mí" option when it is present).
- Do NOT duplicate the queue tabs' estado/emergencia/caso segmentation as filters.
- Reset `offset` to 0 on filter change and on search.

### 2.6 Row-card quick actions and references

- Show the conversation `#id` as a visible reference on the card.
- Keep the always-available open affordance and the `Tomar` / `Reconocer emergencia` actions.
- When the conversation has a case, expose a light reference to it (a chip or a "Ver caso" action);
  avoid new routes if possible.

### 2.7 Pagination

- The `Button variant="secondary"` currently overrides `.pagination__button`, so pagination reads as
  plain text. Restyle so it reads as a real control: proper button chrome, emphasized current page,
  clear disabled state, and >= 44px on mobile. Reuse the `.pagination` primitive and resolve the
  class conflict.

### 2.8 Constraints and verification

- No backend/API/`types.ts`/`realtime.ts`/routing changes beyond the shell prop removal and the
  `/cases` -> initial queue tab wiring.
- `cd web && npx tsc -b` and `cd web && npm test` must pass; update only the assertions affected by
  the removed tabs and new props.
- No commits.
- Human visual gate: re-capture the Conversaciones page at desktop and mobile and confirm the giant
  gap is gone, the header reads like the Dashboard, the status banner is subtle, and the pagination
  reads as a control.

## Wave 3 — identity plumbing, pagination, and card definition

Reported after a second capture: the gap, header, and status banner are fixed; the assignment filter
never rendered, the row-cards still lack a defined style and quick actions, and the pagination looks
worse than before.

### 3.1 Current-user identity (DONE — root cause of the missing filter)

The assignment filter could not work because the SPA never learned the current user's id: both
`GET /panel/api/me` and `POST /panel/api/login` returned only `{username, role}`. The queue API
supported `responsible_id` filtering, but the client had no id to send.

Fixed:
- `app/panel/api/routes/auth.py`: `/me` and `/login` now return `id`.
- `web/src/types.ts`: `LoginResponse` gained `id`.
- `web/src/app.tsx`: `login()` keeps `id`.
- `tests/functional/test_api_auth.py`: exact-shape assertions updated to include `id`.

### 3.2 Pagination redesign

The current `.pagination__current` is filled with `--corp-primary` (a dark block that reads like a
button) and the whole control looks raw.

- Remove the dark fill on the current page. Render the page indicator as restrained muted text
  (`--corp-fg-muted`, `--text-sm`, `--weight-medium`, `--corp-value`), optionally "Página X de Y"
  when `total` and `limit` are known.
- `Anterior` / `Siguiente` keep the secondary button chrome, matching the toolbar's `Reintentar`.
- Right-align the control group, consistent gap and heights; >= 44px targets on mobile.
- Delete the `.pagination .pagination__button[aria-current="page"]` primary-fill rule.

### 3.3 Row-card: defined style and quick actions

The cards read flat and, for a human-owned conversation without an emergency, show no action at all.

- Give the card a defined resting chrome: border, `--radius-md`, `--brand-bg-elevated`, and a subtle
  `--shadow-1`; keep the existing hover lift, selected rail, and urgent tint.
- Strengthen hierarchy: customer name dominant (`--text-md`/semibold); phone and `#id` muted
  (`--text-xs`); summary muted.
- Group the badges with the identity instead of a detached center column.
- Always expose a primary open action: when `onOpenThread` exists, render a visible `Abrir` action in
  the card's actions group. Keep `Tomar` (bot) and `Reconocer emergencia` (unacked emergency)
  alongside it, so every applicable card carries at least one action.

### 3.4 Verification

- `cd web && npx tsc -b` and `cd web && npm test` pass.
- `uv run pytest tests/functional/test_api_auth.py -q` passes.
- No commits. Human visual gate: re-capture at desktop and confirm the filter appears, the page
  indicator no longer looks like a button, and each card reads as a defined control with a visible
  action.

## Wave 4 — card re-design and small-screen fixes

Reported after a third capture: the cards feel cramped (name, phone, `#id`, and badge stacked in a
narrow column), and below 640px the Tabs row shows a scrollbar and the pagination stretches full
width.

### 4.1 Row-card re-design

- Anchor the card with an `Avatar` (existing primitive) on the left.
- Body column with `gap: var(--space-1)`:
  - **headline**: customer name as the open target, with the badges **inline after it** (not stacked
    underneath).
  - **meta**: phone and `#id` on one muted line.
  - **summary**: muted, single line, ellipsis.
- Trailing column (`align-items: flex-end`, `justify-content: space-between`): time on top, actions
  at the bottom. Every applicable card carries a visible action.
- Chrome: `--shadow-1` at rest, `--radius-md`, `--space-4` padding, `--space-3` gap between rows.

### 4.2 Small screens

- Tabs: `overflow-x: auto; overflow-y: hidden;` plus a hidden scrollbar; tabs `flex: 0 0 auto`. No
  vertical scrollbar.
- Pagination: horizontal and compact (centered, normal gaps, 44px targets, buttons NOT full width).
- Card stacks: avatar + headline, meta, summary, then actions.

### 4.3 Filter visibility (operational, not code)

The assignment filter is correct in code but did not appear because the API runs in a container
without `--reload` (`infra-api-1`). Restart it to load the `/me` identity change:
`docker compose -f infra/docker-compose.yml restart api` (or `docker restart infra-api-1`).

## Wave 5 — narrow-screen horizontal overflow (root cause found)

Reported at very narrow widths: the whole page scrolled horizontally and several elements (banner,
search, tabs, cards) were cut off, plus the bottom nav labels overlapped.

**Root cause (found by rendering the component to static HTML and probing the DOM in headless
Chromium):** the `Tabs` primitive's `.tabs` element had a **min-content of ~609px**. Because `.tabs`
is a grid item of `.page-frame__content` (a grid with an implicit `auto` track), its automatic
minimum size (`min-width: auto`) forced the track — and therefore the whole page — wider than the
viewport. The tablist's own `overflow-x: auto` did not help, because the forcing element was the
`.tabs` wrapper, not the tablist.

Fix: `.tabs { min-width: 0 }` in `primitives.css`. This lets the wrapper shrink; the tablist then
scrolls internally as intended, and nothing forces the page wide. The banner (min-content ~109px)
and toolbar (~101px) already shrank correctly.

Also fixed: `.panel-shell__footer-nav button span` now truncates
(`min-width: 0; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap`),
so the five labels no longer overlap at phone widths.

Verification: rendered the real component markup with the real `tokens.css` + `primitives.css` at
320px in headless Chromium — the only remaining internal overflow is the tablist's intended
horizontal scroll. `npx tsc -b` and `npm test` (70 files / 513 tests) pass.

**Debug technique worth reusing:** generate static markup with `react-dom/server` via `vite-node`,
wrap it with the real CSS, then load it in headless Chromium and dump the DOM with a probe that
lists elements whose `scrollWidth > clientWidth`. No Playwright needed.

## Wave 6 — conversation detail page (`/panel/app/conversations/:id`)

Goal: make the opened conversation read like the Storybook concept (`AiAgentGrammar.stories.tsx`,
WhatsApp-style) and use the Dashboard header treatment.

### 6.1 Page header

- `PageFrame` uses `headerClassName="dashboard-header"` and a `dashboard-meta` pill.
- Title: `Conversación` (stable). Meta pill: `#{id} · {customer name} · {date}`.
- The customer name is NOT the title (it would duplicate the per-bubble author label and break
  `getByText` exact-match assertions).

### 6.2 Compact back button

- `Volver a conversaciones` moved into `.conversation-back` (`display: flex`), so it no longer
  stretches to full width inside the grid-based page frame.

### 6.3 Workspace matches the concept

- `.conversation-workspace` now has a bounded height
  (`clamp(30rem, calc(100dvh - 15rem), 46rem)`) and the thread area scrolls internally.
- **The composer moved OUT of `.ai-agent-grammar__thread-area`** into
  `.ai-agent-grammar__composer-zone` (a direct child of `.ai-agent-grammar__main`), so it pins to the
  bottom like the concept instead of scrolling with the messages.
- Live activity renders as centered `.ai-agent-grammar__activity` chips (concept grammar), not a
  plain `<h3>` + `<p>`.
- Conversation state actions (`Tomar` / `Devolver` / `Cerrar`) moved into the inspector's new
  **Acciones** section, matching the concept. The reply composer keeps only `Enviar respuesta`.

### 6.4 Responsive

- At `<= 63.99rem` the workspace collapses to a single column with `height: auto` and the thread area
  stops scrolling internally; the grammar inspector already hides there.
- At `< 40rem` the workspace is `display: block` with `height: auto` and `overflow: visible`.

### 6.5 Tests updated

- `ConversationThread.stories.test.tsx` and `AppShell.test.tsx` asserted the old `# {id}` heading;
  updated to the new `Conversación` title + id-in-pill.

### 6.6 NoReplyNote condition (resolved)

- `NoReplyNote` renders **only when the thread is read-only** (`!interactive`). In the production
  detail view `AppShell` always passes `interactive`, so the note no longer appears there.
- Rationale: the note is a leftover from the H1 read-only panel. HH-5 ("Human Response Channel")
  actually states that during `human` authorized operators MAY respond, so showing "no respondas" in
  an interactive conversation was both misleading and contrary to the requirement.
- Existing coverage already encodes this: the story test "loads a read-only thread from the thread
  endpoint" renders without `interactive` and asserts the note is present.
