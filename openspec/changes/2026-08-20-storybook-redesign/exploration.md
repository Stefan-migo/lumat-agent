# Exploration: Storybook Redesign — Full design-system adoption across all Storybook surfaces

## Current State

Lumat's Panel (web/React + Storybook 8) has a definitive design system contract (`web/DESIGN_SYSTEM.md`, 528 lines) with executable tokens in `web/src/tokens/tokens.css` (72 tokens: primary scale seeded `#143c2c`, neutrals, semantic pairs, brand lime/cyan/aqua/forest/graphite, `--info`, focus-ring `#256f51`, motion `--duration-*`/`--ease-*`, breakpoints, shadows). The visual thesis is a "calm service control room": forest = authority, cyan = info, lime = recognition/selection (never white-text button bg), graphite = grounding, WCAG 2.2 AA, light theme only, **neutral Chilean Spanish UI, English code/identifiers**.

The NEW design is implemented in only three surfaces today:
- `web/src/components/domain/PanelShell.tsx` (192px sidebar, deep-forest brand block + lime rail, responsive modal drawer `<1024px`, `--duration-*`/`--ease-*` motion, `--focus-ring` outlines, reduced-motion handling) and thin `AppShell.tsx`.
- `web/src/stories/pages/Dashboard.stories.tsx` (control-room style: titlebar = PageHeader inside a lime-rail + `--primary-100` forest-tint box; KPI StatCards with tabular numerals; Motivos table with cyan bar tracks; state banners loading/empty/stale/partial-error/fatal-error using semantic pairs via a **story-local** `StateMessage` component).
- `web/src/stories/pages/PanelEntry.stories.tsx` (composes `DashboardOverview` inside `PanelShell`, Desktop/Tablet/Mobile states).

Everything else — all 9 other page stories, the 5 `_shared/` helpers, all 9 primitives + `primitives.css`, and the primitives/domain/tokens stories — is still on the OLD basic look (flat tables, raw English status labels, English UI copy, plain headers, `--primary-600` links, hardcoded focus rings, bare `div.spinner` loading).

The Graph Check confirmed the panel surface lives in graphify Community C1 (ConversationThreadBubbles/Matrix/Story) and C26 (Tokens), C36 (app.test); god nodes are dominated by the Python backend (models.py, webhook). Cross-module graph edges verified: helpers → pages, StatCard → Dashboard → mockData/dashboard, StatusBadge/StatusBadge stories, primitives ↔ pages. Graph built from d8f26896; HEAD d396e3a3 differs only in graphify/config files, so the graph is current for web source.

Baseline verified green: `npx tsc --noEmit` (0 errors), `npm test` (36 files / 209 tests pass), `npm run build-storybook` (succeeds). Storybook glob `../src/stories/**/*.stories.tsx` already covers pages/primitives/domain/tokens — no config change needed for new stories.

### Prior archived change context
`openspec/changes/archive/2026-08-19-panel-real-design/` created the page-first workflow: 8 pages + Login as CSF stories, 5 story-local helpers under `_shared/` (DataTable, PageHeader, StatCard, EmptyState, FlashMessage) + toneMaps, and typed mocks. Its design (D1) explicitly documented the helpers as **"promotion to src/components/ is later"** — the current redesign is the natural follow-up. The archive's design also documents component contracts (D4 Case/Customer tone maps, D6 DataTable, D7 per-state variants) that the redesign must not regress.

## Graph Check Record
Nodes/edges consulted: `graphify query "storybook stories panel primitives helpers"` (BFS from PanelEntry.stories/PanelShell/Proposal → 99 nodes), `graphify path PageHeader DataTable` (4 hops: PageHeaderProps⊂PageHeader.tsx→CasesList.stories→DataTable→DataTable.test), `graphify path StatCard Kpis` (StatCard.tsx→Dashboard.stories→dashboard.ts→Kpis), `GRAPH_REPORT.md` god nodes/communities (C1, C12, C26, C36). Recorded in this artifact per project rule.

## Current-state Inventory (per surface)

### Page stories (10) — `web/src/stories/pages/*.stories.tsx`
| Story | Design state | Copy issues | Token/label violations | Missing states |
|---|---|---|---|---|
| **Dashboard** | **NEW** (reference) | Spanish, correct | Titlebar/KPI/bar-track/banner language | Complete (ready/loading/empty/stale/partial-error/fatal-error) |
| **ClientesList** | OLD | title "Clientes" ok; meta `N clientes` ok; **Empty "No customers found" English** | link `--primary-600` (banned; must be 700); state Badge renders raw `c.state` ("nuevo"/"activo"…) | only Default/Loading/Empty via bare `div.spinner`; no stale/error/banner |
| **CasesList** | OLD | live **English** title "Cases (pending / escalated)"; empty "No cases found"; FlashMessage Spanish | link `--primary-600`; Badge renders raw `c.status`; emergency "⚠ Reconocido por" raw | Default/Empty only; **no Loading**; no banner language |
| **ConversationsList** | OLD | title "Conversations" (English); empty "No conversations found"; filter label ok | link `--primary-600`; StatusBadge raw en state; "Actions" EN table header via DataTable; rowStyle warning bg only highlight (design says warning-tinted leading, not color only) | Default/FilterByState/Empty; no loading; no banner |
| **ClientFicha** | OLD | Spanish but raw labels | **`customerStateTone` misused for Case statuses** (should be `caseStatusTone`); Badge raw `customer.state`; raw conversation state `c.state`; raw message `direction`/`msg_type`; English-independent content mostly ok | Default only; no saving/validation/disabled/recovery states for state-form |
| **ConversationThread** | OLD | English-independent; raw conv.state in meta | raw `conv.state`; ⚠️ emoji note w/o semantic banner; flat DataTable for a chat | Default + BubbleVariant only; no loading/empty |
| **InboxThread** | OLD | **voseo** "Escribí tu respuesta" placeholder; **"Bot pausado"** (design: use only when bot is actually paused — here state=bot means active); meta raw `state` | raw state; `--warning-bg` row highlight not used here; disabled composer reason "Fuera de la ventana" ok | ComposerEnabled/Disabled×2/OutsideWindow; no stale/loading |
| **ChatWithAgent** | OLD | **English** "Agent is thinking…", "Agent idle" (from `mockData/chat.ts` `agentStatus`); voseo "Escribí tu mensaje"; aria "admin message"/"agent message" EN | raw role labels; English aria | Default + AgentThinking only |
| **KbList** | OLD | near-total **English**: "Knowledge Base", "Add document", "Title", "File (pdf/md/txt/csv)", "Add", "Edit", "Save (new version)", "Disable", "Restore", "Cost (USD)", "Provider / Model", "No documents yet" | raw provider/model + `category=mode` (`settings.scope_rules` in Settings also) on a non-technical view (design: keep advanced syntax separated/explained); raw format | Default/Empty only; no processing/error/disable-confirmation states |
| **Settings** | OLD | near-total **English**: "Settings", "Scope rules", "Save scope rules", "Emergency keywords", "Tone", "Spend limits", "Conversation limit (USD)", "Save limits", "Meta pricing", "Service-message cost (USD)", "Save pricing", "Current spend", "Day/Daily spend/% of limit/Mode" | `category=mode` advanced syntax exposed without the "separated/explained" treatment; manual flat `<table>` for spend (no tabular-nums, no semantic pairs) | Default only; **no saved/saving/validation/server-error/stale states** (design §Configuración requires them) |
| **Login** | OLD | **English**: card "Lumat Panel" (no lockup), "Username", "Password", "Login", error "invalid credentials" | Card title instead of Lumat lockup | Default + Error only; no loading |

### Shared helpers — `web/src/stories/pages/_shared/`
- **PageHeader** (`35` lines): plain inline-style header, **no titlebar box language**. Dashboard bypasses it by wrapping it in `.dashboard-shell__titlebar`. Gap: helpers don't own the lime-rail/forest-tint titlebar, so every page reimplements or misses it.
- **DataTable** (`66`): flat `.table`, **no state banner integration**, EN defaults `"No data"` (empty) and `"Actions"` (header), no loading/stale/partial-error rendering, no tabular-num guidance enforcement.
- **EmptyState** (`14`): basic `.empty-state` box, no banner/action retry semantics.
- **StatCard** (`25`): `.kpi` + optional top rail; **tabular numerals only added via Dashboard's scoped `DASHBOARD_STYLES`**, not in the helper core.
- **FlashMessage** (`13`): `.flash-message--{tone}` basic; no role/alert semantics (unlike Dashboard `StateMessage` which sets `role="status"|"alert"`).
- **toneMaps.ts** (`caseStatusTone`, `customerStateTone`): fine; used correctly by Clientes/Cases lists but **misused by ClientFicha** (case status fed into `customerStateTone`).
- **helpers.test.tsx / DataTable.test.tsx**: assert EN placeholder copy ("No customers found", "Edit Ada", "Dashboard", "last 30 days") — need updating with Spanish.

### Primitives — `web/src/components/primitives/` + `primitives.css` + stories
CSS violations (`primitives.css`, real production file):
- `.btn { transition: background-color 120ms ease }` — hardcoded `120ms`/`ease`; must use `var(--duration-base)`/`var(--ease-out)` (motion tokens).
- `.btn:focus-visible`, `.field__control:focus`, `.search-input:focus-within` — `outline: 2px solid var(--primary-500)`; **must be `var(--focus-ring-width) solid var(--focus-ring)`** (`--focus-ring` = `--primary-700 #256f51`; `--primary-500` #47c291 → 2.85:1 fails AA focus on `--surface`/`--bg`).
- `.spinner__indicator` border top `var(--primary-800)` + `animation: spin 1s linear` — 1s hardcoded; PanelShell/Dashboard prefer `--info` top + duration token; consider consistency.
- No `color-mix`/brand misuse otherwise; primitives otherwise token-correct.

Primitives TSX:
- **StatusBadge** renders raw status labels (`bot`/`human`/`closed`/`pending`/`escalated`); design §Status badge requires approved labels `Agente atendiendo`/`Atención humana`/`Cerrada` and says do not expose raw values. This is a shared primitive → adding a Spanish label map fixes all consumers at once.
- **SearchInput** default `aria-label="Search"` (English).
- Button/Card/Badge/Avatar/Input/Select/Textarea/FieldShell: token-correct, no hex.

Primitives stories (`web/src/stories/primitives/*.stories.tsx`): high quality docs + Matrix variants, already mostly Spanish, but:
- `StatusBadge.stories.tsx` renders raw EN statuses in matrix + argTypes/summary.
- `SearchInput.stories.tsx` placeholder "Search clients" (EN).
- `Badge.stories.tsx` / `Card.stories.tsx` example copy EN ("Pending", "Client").
- Button story docs already document the correct `--focus-ring*` token contract — **CSS doesn't honor it yet** (drift between doc and `primitives.css`).
- Each story needs the viewport/width state checks per Storybook contract (Contextual: only a few set `layout`/viewport).

### Domain + tokens stories
- `AppShell.stories.tsx`: NEW look (Admin/Operador/Matrix). Good.
- `Tokens.stories.tsx`: NEW look (lime-rail forest header, grouped token cards). Good; depends on `tokens.css?raw` + `groupToken`.
- **Discovery**: `AppShell.tsx` (production) still renders **placeholders** ("Vista {X} disponible en un batch posterior") for every non-dashboard view — it does not compose the real page components. Redesign scope decision: whether to wire AppShell to render the actual page stories (worth proposing) or keep it decoration-only.

### Tests that will need updating (design-churn)
- English copy encodings: `ClientesList.test` (“No customers found”), `CasesList.test` (“Cases…”, “No cases found”), `ConversationsList.test` (“No conversations found”), `KbList.test` (“Knowledge Base”, “Edit”, “Disable”, “Restore”, “No documents yet”), `Settings.test` (“Settings”), `Login.test` (“Lumat Panel”, “Username”, “Password”, “Login”, “invalid credentials”), `helpers.test` (“No customers found”, “Edit Ada”), `DataTable.test` (“No customers found”, “Edit Ada”).
- Raw-state assertions: `ClientFicha.test` (`["nuevo","activo","inactivo","bloqueado"]` Select options + `customerStateTone` badge), `CasesList.test` (status option text), `ConversationsList.test`, `StatusBadge.stories` (raw statuses).
- SearchInput default `aria-label="Search"`: `SearchInput.test.tsx` line 10 asserts `getByRole("searchbox", {name:"Search"})`.
- No primitive test asserts `primitives.css` focus/motion values → **CSS token swaps won't break primitive tests**, but `tokens.test.ts` "no hardcoded hex" guard scans all `.ts/.tsx/.css` outside stories; only `primitives.css` changes, no new hex added, safe.
- `Dashboard.test`, `Tokens.stories.test`, mockData tests: stable (Dashboard Spanish copy preserved).

## Design-System Gap Summary (what the redesign must change)

1. **Copy**: eliminate every English/voseo string (page list above) to neutral Chilean Spanish; approved labels (§Content).
2. **Link color**: replace all `--primary-600` links with `--primary-700` (3.38:1 → 6.05:1 AA).
3. **Status labels**: stop rendering raw `state`/`status`/`direction`/`msg_type`/`provider/model`/`category=mode`; use approved Spanish labels (ideal: extend `StatusBadge` + `toneMaps` with Spanish maps).
4. **State model**: every list page needs the Dashboard banner language (loading/empty/stale/partial-error/fatal-error + retry, using `role="alert|status"` + colored rail, never color alone); KB needs processing/error/disable-confirmation; Settings needs saved/saving/validation/server-error/stale.
5. **Focus rings**: `primitives.css` must use `--focus-ring*` tokens (not `--primary-500`), and motion must use `--duration-*`/`--ease-*` (not `120ms`/`1s`).
6. **Titlebar/page-shell language**: promote the Dashboard titlebar/bar-track/StatCard-tabular/banner composition so every page gets the same "control room" frame — otherwise each page reimplements scoped CSS.
7. **Login**: use the Lumat lockup + Spanish `Usuario`/`Contraseña`/`Iniciar sesión`, inline non-destructive error that preserves the username.

## Shared-Helper Consolidation Opportunity
Today the helpers are thin "extraction candidates" (archived design D1) and Dashboard already pivots them into the new look through a **page-scoped `DASHBOARD_STYLES` block** plus a story-local `StateMessage`. The redesign should promote that surfaced pattern into the helpers so ALL pages share one language:
- **PageHeader**: optional `chromed`/titlebar variant (lime rail + `--primary-100` tint) so Dashboard and every page use the same header shell.
- **StateMessage** (currently story-local in Dashboard): promote to `_shared/StateMessage.tsx` with `tone`/`role`/`title`/`detail`/`spinner` — one loading/empty/stale/error banner reused across all pages, replacing the scattered `div.spinner` + `EmptyState` + `FlashMessage` usages.
- **DataTable**: add `loading`/`stale`/`emptyMessage`(Spanish) states and a configurable `actionsHeader` (Spanish "Acciones"), tabular-num helper for numeric columns.
- **StatCard**: fold the tabular-num value + context into the core (not Dashboard-scoped CSS).
- Keep helpers under `_shared/` for this change; promoting to `src/components/` is a separate later change (multiple production consumers needed first, per design §Non-goals / §Storybook contract). A **shared `pageFrame`/`PageShell` composition** (titlebar + banner slots + content region, echoing PanelShell) would give every page the control-room frame with minimal per-page CSS — the strongest consolidation lever.

## Approaches Compared

**Approach A — Promote shared helpers + one page-shell composition, then restyle every page to use it.**
Consolidate `PageHeader`/`DataTable`/`StatCard`/`EmptyState`+`FlashMessage`→`StateMessage`, add a `PageFrame`/titlebar, promote tabular-num + banner language into helpers, fix `primitives.css` focus/motion + `StatusBadge` labels + toneMaps, then restyle each page story to compose the shared frame.
- Pros: single source of truth for titlebar/banner/table language (no per-page scoped CSS drift like today's `DASHBOARD_STYLES`); every page automatically consistent; fixes the raw-label problem at the `StatusBadge`/`toneMap` root for all consumers; minimal long-term churn.
- Cons: largest surface touched in one change (helpers + primitives + all pages); higher test churn (helper tests + every page test that asserts EN copy); risk of regressing the currently-good Dashboard if the shared helpers drift from its proven local styles.
- Effort: High.

**Approach B — Per-page story-local restyle (each page re-implements the Dashboard pattern locally, no shared promotion).**
Copy the Dashboard `DASHBOARD_STYLES`/`StateMessage` pattern into each of the 9 old pages as a page-scoped block.
- Pros: additive, low-risk to existing helpers/primitives; Dashboard stays untouched; small isolated diffs per page.
- Cons: duplicates the titlebar/bar-track/banner CSS 9× (today's drift gets worse, not better); shared `StatusBadge` raw labels still leak unless also changed; fails the consolidation opportunity; more total lines.
- Effort: Medium (per-page small) but compounding maintenance debt.

**Approach C — Hybrid (recommended): promote the shared layer (helpers + StateMessage + PageFrame) and `primitives.css`/`StatusBadge`/toneMaps label fixes in one slice, then restyle each page to consume it in per-page slices.**
- Pros: captures the consolidation value (A) with the incremental, reviewable, ≤400-line increments of (B); fixes raw labels + focus rings once at the root; Dashboard becomes a consumer of the shared frame (or keeps its proven styles only until the frame proves out); per-page restyle (B) is trivial once helpers carry the language.
- Cons: two-phase; requires the shared-frame slice to prove the look before pages adopt it (Dashboard as the proving ground first).
- Effort: High overall but sliced into review-safe batches.

Recommendation: **Approach C**. It directly fulfills the mission (remove old basic design completely) while avoiding both the drift trap (B) and the big-bang risk (A). The shared frame slice is validated against Dashboard, then pages adopt it in reviewable batches.

## Recommended Slice Boundaries (chained PRs, ≤400 added+deleted lines each)
1. **S1 — Foundation/tokens**: `primitives.css` focus-ring (`--primary-500`→`--focus-ring*`) + motion (`120ms`→`--duration-base`/`--ease-out`, `1s`→`--duration-slow`or token) + spinner. Green: `npm test`, `tsc`, `build-storybook`. (~1 file / low churn; no primitive tests break.)
2. **S2 — Label maps + shared StateMessage/PageFrame**: add Spanish maps (StatusBadge labels, translate raw `state`/`status`/`direction`/`provider/model` via toneMaps or new maps), promote `StateMessage` from Dashboard to `_shared/`, extend `DataTable` (Spanish empty/actions, loading/stale) + `StatCard` tabular-num, add `PageFrame`/titlebar. Update `helpers.test`/`DataTable.test`/`SearchInput`/`StatusBadge` tests + stories.
3. **S3 — List pages**: ClientesList + CasesList restyle to shared frame (fix `--primary-600`, Spanish empty, add loading/stale/error banners).
4. **S4 — Conversations + Inbox + Thread**: ConversationsList (Spanish, filter, banner), InboxThread (fix voseo + "Bot pausado", raw state), ConversationThread (banner, Spanish state).
5. **S5 — Ficha + ChatWithAgent + Login**: ClientFicha (fix `customerStateTone`→`caseStatusTone`, Spanish labels, saving/validation states), ChatWithAgent (translate `agentStatus` + voseo + aria), Login (lockup + Spanish + inline error preserving username).
6. **S6 — KB + Settings**: full Spanish translation, `category=mode`/provider-model separation, KB processing/error/disable-confirmation, Settings saved/saving/validation/stale states, tabular-num spend.
Each slice keeps `npm test` + `tsc` + `build-storybook` green; auto-chain stacked-to-main.

## Risks
- **Scope size**: 9 pages + 5 helpers + 9 primitives + CSS + ~15 test files. Mitigated by 6 slices under the 400-line guard.
- **Test churn**: every EN-copy and raw-state assertion (Clientes/Cases/Conversations/Kb/Settings/Login/helpers/DataTable/SearchInput/StatusBadge) must be updated; high but mechanical.
- **Copy consistency**: risk of inconsistent Spanish while converting; rely on approved label glossary (§Content + §Status badge + Preferred terms) and the shared maps; avoid voseo.
- **Visual regression without a browser**: no rendered snapshot baseline; "new look" is validated by reusing Dashboard's proven pattern + review. Recommend the shared frame be proven against Dashboard before broad adoption.
- **`primitives.css` production impact**: it's the real shared stylesheet importable by production `src/components/**`; changing focus-ring/motion affects real controls. Low risk (token-equivalent swaps, no test asserts values), but must be flagged and verified.
- **Existing tests encoding old design**: 10+ tests assert EN copy/raw states; they will fail until each slice updates them. Budget for test edits in every slice (never leave a slice red).
- **Dashboard regression**: if shared helpers change noticeably (e.g. PageFrame), Dashboard must keep its proven look or adopt the frame carefully; keep Dashboard tests green as the sentinel.
- **AppShell wiring scope creep**: `AppShell` still renders placeholders; wiring real pages is a scope decision the proposal must make explicit (recommend deferring to keep this change Storybook-focused, or a separate slice).

## Ready for Proposal
Yes. The orchestrator should tell the user: the old basic design is fully inventoried and the target is defined by Dashboard/design system; the recommended approach is a hybrid (promote the shared frame/StateMessage + fix primitives.css focus/motion + StatusBadge/toneMap labels, then restyle each of the 9 pages to consume it) delivered in 6 chained ≤400-line slices. Confirm whether AppShell should also start composing real page components (currently placeholder) — recommend deferring to a separate slice to hold Storybook scope.
