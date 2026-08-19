# Exploration: Panel Real Design — recreate each panel page as Storybook story (page-first)

> Change: `2026-08-19-panel-real-design` · Project: LumatAgent · Phase: sdd-explore · Date: 2026-08-19
> Prior decision (cortex-session `panel-real-design`): page-first — recreate each panel PAGE as a Storybook story, iterate visually in Storybook, then implement in the real React frontend.
> Artifact store: hybrid (openspec file + engram).

## Context

The design-system FOUNDATION is done and archived (`openspec/changes/archive/2026-08-19-panel-design-system/`): 67 tokens (`web/src/tokens/tokens.css`), 10 primitives, AppShell, Storybook autodocs + viewports. The `web/src/app.tsx` is a **bare auth gate** (`loading → authed(AppShell) → anon/error stub`); no real views render — AppShell's `<main>` shows only "Vista {label} disponible en un batch posterior." The Jinja panel (`app/panel/templates/`) is the **source of truth** for what each page contains.

## What Each of the 8 Pages Contains

Derived from `app/panel/templates/*.html` + `app/panel/api/routes/*` + serializers (`app/panel/api/serializers.py`) + `web/src/types.ts`.

### 1. Dashboard — `dashboard.html` + `api/routes/dashboard.py` → `GET /panel/api/kpis`
- KPI grid (3 StatCards): `contacts`, `derived` (derived cases), `visit_requests`.
- Table: "Motivos" — `motivos: Array<[service, count]>` (Service / Cases).
- Muted caption: `KPI window: last {window_days} days ({window_start})`.
- Data type: `Kpis` in `types.ts`. Empty state: "KPI dashboard lands with Batch 5 completion (T5.5)" — template shows muted text.

### 2. Clientes (list) — `clients/list.html` + `GET /panel/api/clients?q=`
- Search form: `SearchInput`-style input (placeholder "Search by name or phone…") + Search button + **Export CSV** (secondary button → `/panel/export/clients.csv`).
- Table: Name (link→ficha) / Phone (`phone_e164`) / State (`state.value`) / Consent (yes/no) / Created (`created_at`).
- Empty: "No customers found."
- Response: `{clients: Customer[], query}`.

### 3. Clientes ficha (drill-down) — `clients/ficha.html` + `GET/ POST /panel/api/clients/{id}`
- **Card "Customer"**: PageHeader (title `Ficha: {name|phone}`), phone, state (strong), consent; muted line: email, comuna, address, created. Flash message on action.
- **State change form**: `<select>` (4 states: nuevo/activo/inactivo/bloqueado from `CustomerState`), "Change state" Button → POST `/clients/{id}/state`.
- **Card "Internal notes"**: list of `author · created_at: note`; textarea + "Add note" button → POST `/clients/{id}/notes`.
- **Card "History"**: 3 subtables — Conversations (`#`, state, summary, created→link to thread), Cases (`#`, service, priority, status, summary), Messages (`direction`, `msg_type`, text, media link, when).
- Response: `ClientFichaResponse` (`customer`, `history{conversations,cases,messages}`, `notes`, `states`).

### 4. Conversaciones (list) — **no dedicated Jinja list page exists**; only `conversations/thread.html`. But `AppShell` has it as a nav view. The **Conversations list is NOT in the current template set** — the Jinja app links to `/panel/conversations/{id}` only from the client ficha. So for a Storybook page story, the **Conversations list must be designed new** from `Customer`/`Conversation`/`Message` data (the SPA nav presumes it, B3/T3.1 covers the thread only).

### 5. Conversation thread (drill-down) — `conversations/thread.html` + `GET /panel/api/conversations/{id}`
- PageHeader: `# {id}`, muted: state / created / summary.
- **Thread (read-only)** table: When / Direction (inbound|outbound) / Type / Content (+ `media_url` as "📎 linked file" link).
- Footer note: "Replying from the panel is not available in H1 — answer via WhatsApp app" (HH-5).
- Response: `ConversationThread` (`conversation`, `messages`).
- **Visual design consideration**: a real chat-thread presentation (bubbles/alternating inbound/outbound) would differ from today's flat table — page story is the place to explore this.

### 6. Casos (list) — `cases/list.html` + `GET /panel/api/cases`
- PageHeader: "Cases (pending / escalated)". Flash on action.
- Table: `#`, Customer (name + muted phone), Service, Status, Summary, Emergency (⚠ emergency / acknowledged-by), Responsible (username), Actions.
- **Actions row**: inline `<select>` status (abierto/escalado/en_evaluacion/cerrado) + `<select>` responsible (from users) + "Update" button (POST `/cases/{id}/update`); if emergency & unanswered → "Acknowledge" button (POST `/cases/{id}/ack`).
- Data: `CasesResponse` (`cases[]` with embedded `customer`, `users[]`).

### 7. Base de conocimientos (KB, admin) — `kb/list.html` + GET/POST `/panel/api/kb`
- PageHeader "Knowledge Base". Flash.
- **Card "Add document"**: Title input + File input (pdf/md/txt/csv) + "Add" button (multipart POST `/kb`).
- **Docs table**: `#`, Title, Format, Version (`{version} (active: {active_version})`), Active (yes/no), Provider/Model, Cost (USD, 6 decimals), Actions.
- **Actions (per active doc)**: inline `<details>` "Edit" accordion (title input + content textarea + "Save (new version)"); "Disable" button; if version>1 → Restore `<select>` (v1..v{n}) + "Restore" button.
- Data: `DocsResponse` (`docs: Doc[]`).

### 8. Configuración (admin) — `settings/index.html` + GET/POST `/panel/api/settings`
Six stacked form cards, each = a page section:
- **Scope rules (SS-1)**: textarea one rule per line `category=mode`, "Save scope rules".
- **Emergency keywords (SS-2)**: textarea one expression per line, "Save keywords".
- **Tone (SS-5)**: single-line text input, "Save tone".
- **Spend limits (SS-3)**: conversation_limit + daily_limit numeric inputs, "Save limits".
- **Meta pricing (SS-4)**: service_message_cost input, "Save pricing".
- **Current spend (SS-4)**: table `Day / Daily spend / Daily limit / % of limit / Mode` + muted conversation-percent line.
- Data: `Settings` (`scope_rules`, `keywords`, `tone`, `conversation_limit`, `daily_limit`, `meta_cost`, `snapshot`). All admin-only (403 for operador).

### 9. Login (bonus, not in the 8) — `login.html` + POST `/panel/api/login`
- Centered card "Lumat Panel": username + password + Login. Error state. **Not in the AppShell nav** — it's the pre-auth gate (currently an inline stub in `app.tsx`). Candidate for a `Login` page story.

## Existing Building Blocks (primitives + CSS-ready classes)

**10 TSX primitives** (`web/src/components/primitives/`, token-only):

| Component | Props | Key notes |
|---|---|---|
| `Button` | variant primary/secondary, href (→anchor), type, disabled | covers Search + Export CSV + Update + Save + Acknowledge |
| `Input` | label, size sm/md, error | `FieldShell` label+aria-describedby |
| `SearchInput` | onSearch, delay, aria-label | debounced search; used in Clientes list |
| `Select` | label, options, error | used for state/status/responsible/restore selects |
| `Textarea` | label, error | notes, KB content, settings textareas |
| `Card` | title, children | every form/panel block |
| `Badge` | tone neutral/success/warning/danger | status chips |
| `StatusBadge` | status bot/human/closed/pending/escalated | conversation status (does NOT map to the Jinja Case statuses: abierto/escalado/en_evaluacion/cerrado, nor Customer states) |
| `Avatar` | name, src | initials/image |
| `FieldShell` | private; label+error wrapper | not in public surface |

**Critical discovery — CSS-ready but NO TSX components**: `primitives.css` (imported by every primitive) already defines token-styled classes that were added in B7/B8 but **never consumed by any component**: `.table` (+`.table th/td`), `.spinner` (+`__indicator`, `@keyframes spin`), `.modal` (+`__title`, `__content`, `::backdrop`), `.flash-message` (--success/--warning/--danger), `.empty-state` (+`__title`, `__description`), `.pagination` (+`__button`, `[aria-current=page]`), `.kpi-grid`, `.kpi` (+`__label`, `__value`, `__delta`). **These are dead CSS waiting for consumers.** Page stories can use them directly in JSX (the classes are token-styled), or pattern components can wrap them.

## Gap Analysis

What page stores must compose vs. what must be created.

| Pattern needed | Exists as TSX? | CSS-ready? | Missing piece / exact path |
|---|---|---|---|
| `DataTable` (columns, rows, sorted, actions cell) | ❌ | ✅ `.table` CSS | **No TSX component.** Pages need a way to render `Customer[]`, `Case[]`, `Doc[]`, motivos, messages rows. Either a `DataTable` pattern (under components) or per-page table JSX. |
| `PageHeader` (title + subtitle/meta + actions) | ❌ | ❌ | No CSS. Repeatable in `Card`/inline. Currently "Vista {label}" text in AppShell. |
| `StatCard` / KPI (`kpi-grid`/`kpi`) | ❌ | ✅ `.kpi-grid/.kpi` CSS | Dashboard needs 3 StatCards. CSS-ready. |
| `EmptyState` | ❌ | ✅ `.empty-state` CSS | All list pages ("No customers found", "No open cases", "No documents yet"). CSS-ready. |
| `ErrorState` | ❌ (inline in app.tsx) | ❌ (only `flash-message--danger`) | Auth gate has an inline retry block. Could reuse `.flash-message--danger` or design a proper ErrorState. |
| `LoadingState` / `Spinner` | ❌ | ✅ `.spinner` CSS | Auth gate uses inline "Cargando…". CSS-ready. |
| `Modal` / dialog | ❌ | ✅ `.modal` + `::backdrop` CSS | KB Edit is currently `<details>` accordion in Jinja — story could keep accordion or propose modal. |
| `Tabs` | ❌ | ❌ | Client ficha has subtables (Conversations/Cases/Messages); could be stacked sections (as Jinja does) or tabs — decision for design. |
| `FlashMessage` (toast/alert) | ❌ | ✅ `.flash-message` CSS | All mutating pages (ficha, cases, kb, settings) flash on success/error. CSS-ready. |
| `Accordion` (`<details>`) | ❌ (native `<details>` is fine) | ❌ | KB Edit uses native `<details>`. No new component needed. |
| `LoginForm` | ❌ (inline stub in app.tsx) | ❌ | auth page story. `Input` covers username/password. |
| `Breadcrumbs` | ❌ | ❌ | ficha (← Clientes) and thread (← Conversaciones) drill-down navigation. No CSS. |

**Pattern components vs pure page stories**: The session decision says Storybook-only changes limited to stories, helpers, fixtures/mocks, `.storybook` config. So new *patterns* should be **local-to-story helpers** (like `matrix.tsx`) OR shared helpers, NOT production `src/components/` changes (which the foundation explicitly kept out of scope). The CSS already exists in `primitives.css` — consuming `.table`, `.kpi-grid`, `.empty-state`, `.flash-message`, `.spinner`, `.pagination` directly from page-story JSX (via the `Card`/`Button` imports that pull `primitives.css` in) requires **zero new CSS**.

## Recommended Slice Shape

### Where do pattern-helpers live?
- **Page stories**: `web/src/stories/pages/{Dashboard,ClientsList,ClientFicha,ConversationsList,ConversationThread,CasesList,KbList,Settings}.stories.tsx` — one file per page, following the `stories/**/*.stories.tsx` glob (`main.ts` untouched).
- **Shared page-story helpers**: `web/src/stories/pages/_shared/` (e.g. `DataTable.tsx`, `PageHeader.tsx`, `StatCard.tsx`, `EmptyState.tsx`, `FlashMessage.tsx`, `mockData.ts`) — these are **story-local compose helpers**, mirroring how `matrix.tsx` is a story helper. Keeps production `src/components/**` untouched (matches the session scope decision).
- **Mock data**: `web/src/stories/pages/_shared/mockData.ts` — typed with `web/src/types.ts` interfaces, seeded for each page (customers, cases, docs, kpis, thread, notes, settings). Single source for all page stories.
- **Keep the `.table/.kpi/.empty-state/.flash-message/.spinner` CSS** as the styling (they're already in `primitives.css`; no new CSS file). Story helpers emit these class names + tokenized inline styles (like `AppShell.tsx` does).

### Page components (under `src/components/`) vs story-local?
**Recommendation: story-local helpers for this phase**, per session decision #2 (changes limited to stories/helpers/fixtures/.storybook). Extracting to `src/components/` happens in a later phase when the approved design gets promoted to production. Do NOT pre-emptively create `web/src/components/domain/{DashboardPage,ClientsPage,...}` yet.

### Reviewable batches (each ≤400 changed lines, auto-chain)

8 pages + login → **4 batches of 2 pages each**, each ~300-380 lines (page story ~150-190, shared helpers land in an early slice, mocks ~long):

- **B1 — Shared page infrastructure** (~250-330 lines): `_shared/mockData.ts` (all 8 pages' fixtures), `_shared/DataTable.tsx`, `_shared/PageHeader.tsx`, `_shared/StatCard.tsx`, `_shared/EmptyState.tsx`, `_shared/FlashMessage.tsx`. Cross-cutting, tiny surface per helper; enables all pages. (No stories yet or a single smoke story.)
  - Risk: mockData.ts could balloon past 400 lines on its own. **Split mocks per page** (`_shared/mockData/dashboard.ts`, `clients.ts`, `cases.ts`, `kb.ts`, `settings.ts`, `conversations.ts`) so each batch owns its fixtures.
- **B2 — Dashboard + Clientes list** (~320 lines): Dashboard story (KPIs + Motivos + window caption) + ClientesList story (search + export + table) + their mocks.
- **B3 — Cliente ficha + Conversation thread** (~360 lines): ficha (customer card + state form + notes card + history table) + thread (header + message table + no-reply note). Drill-downs share DataTable/PageHeader.
- **B4 — Cases list + Conversations list** (~360 lines): cases (emergency highlights + inline update/ack actions) + conversations list (new page design: customers/threads table; no Jinja template — first-time design).
- **B5 — KB + Settings (+ Login)** (~400 lines): KB (add-doc card + docs table + edit accordion + restore) + Settings (6 form cards + spend snapshot). Login card can ride this batch.

Each batch: `npm test` + `npm run build-storybook` green, web-only diff, independent story files (B1 helpers shared).

## Graph Check Record (mandatory — AGENTS.md Step 1)

Knowledge graph: `graphify-out/graph.json` **built 2026-08-19 16:48** (fresh, includes the archived panel-design-system change cycle). `.graphify_root` = repo root.

- **Queries run**: `graphify query "panel"` (275 nodes BFS depth 2) and `graphify query "web AppShell"` (59 nodes).
- **Nodes consulted**: `AppShell()`, `app.tsx`, `AppShellProps`, `NAV`, `NavEntry`, `View`, `apiFetch()`, `ApiError`, `types.ts`, `web/package.json` (+ scripts/storybook/test), `Matrix()`/`matrix.tsx`, `AppShell.stories.tsx`, `AppShell.test.tsx`, `app.test.tsx`, `api.test.ts`; backend: `api/routes/{dashboard,clients,conversations,cases,kb,settings,auth}.py`, `compute_kpis()`, `to_customer_dict()`, `to_case_dict()`, `to_doc_dict()`, `to_conversation_dict()`, `to_message_dict()`, `to_user_dict()`, `to_note_dict()`, `Customer`, `Conversation`, `Message`, `Case`, `KbDocument`, `User`, `customer_history()`, `list_open_cases()`, `spend_snapshot()`.
- **Edges / communities**: `app.tsx` community (Community 38 — AppShell/api/types/app node cluster); `types.ts` community (47); `matrix.tsx` community; hyperedge **"Admin Panel Jinja Template Set (base + 8 views)"** (the template files that now compose into the new pages); hyperedge **"Panel Design System SDD Change Cycle"** (the archived foundation this slices from). God nodes relevant: `Message` (77), `Customer` (64), `Conversation` (63), `Case` (46), `User` (45) — all feed the page mocks.
- **Observation**: web/ area still under-represented; the previous archived design noted graph staleness for `web/` (community 68 thin). After batches land, `graphify . --update` should re-balance.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Page stories drift from production constraints (API shape, Jinja fields) | Approved designs may need adaptation at implementation | Mocks typed to `web/src/types.ts`; helpers thin; API surface already mirrors templates (serializers are the contract) |
| Conversations **list page has NO Jinja/API list endpoint** — only the thread GET exists | Design has no backend source of truth for the list; the SPA nav presumes it | Design from `Customer`/`Conversation` data shape; flag as a backend gap (a `GET /conversations` list endpoint may be needed later) |
| Story-local helpers become production imports by accident | Scope creep into `src/components/` outside the approved phase | Session decision #2: helpers stay under `stories/pages/_shared/`; PR review guard for the `components/` boundary |
| Dead `.table/.spinner/.modal/.empty-state/.kpi` CSS conflicts (classes exist but no components) | Consumers or drift tests may not know the classes are already styled | Reuse existing classes in story helpers; document the "CSS-ready" inventory in design |
| mockData.ts bloat crossing the 400-line budget | Oversized single diff | Mocks split per page under `_shared/mockData/{page}.ts` |
| StatusBadge maps conversation statuses (bot/human/closed/pending/escalated), NOT Case statuses (abierto/escalado/en_evaluacion/cerrado) nor Customer states | Wrong badge tone mapping in cases/clients | Design must map Case statuses + Customer states to Badge tones explicitly; may need a caseStatusTone/customerStateTone map in story helpers |

## Next Recommended

`sdd-propose` for `2026-08-19-panel-real-design`, using this exploration + the archived foundation + the cortex-session decisions. The proposal should: (1) scope strict Storybook-only (stories + `stories/pages/_shared/` helpers + mocks), (2) define the 5-batch slice shape, (3) pin mock data typing to `types.ts`, (4) flag the Conversations-list backend gap as an open question, (5) record the new pattern/CSS inventory.

**Ready for Proposal**: Yes.
