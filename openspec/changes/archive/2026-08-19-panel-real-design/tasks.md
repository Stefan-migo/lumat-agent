# Tasks: Panel Real Design — Page-First Storybook Workflow (LumatAgent)

> Change: `2026-08-19-panel-real-design` · Project: LumatAgent · Phase: sdd-tasks · Date: 2026-08-19
> Storybook-only additive Delta over the archived `panel-design-system` foundation: 8 pages + Login as CSF page stories under `web/src/stories/pages/`, story-local helpers under `_shared/`, typed mocks per page, zero new CSS and zero production changes.
> Task numbering: `T<batch>.<index>` (T1.x = B1 … T5.x = B5). 5 batches → 5 chained PRs, auto-chain, stacked to main. Verification per batch: `cd web && npm test` + `npm run build-storybook`.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines (total) | ~1550–1850 (authored, additions+deletions) |
| Estimated changed lines per batch | B1 ~380–420 · B2 ~250–300 · B3 ~300–350 · B4 ~350–400 · B5 ~380–430 |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | 5 PRs stacked to main, one per batch (B1→PR1 … B5→PR5) |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium

Rationale: total change is 1.5–1.9k lines, far above the single-PR budget, so chaining is mandatory. Each batch is a self-contained, independently reviewable slice (shared infra → paired pages) that stays green alone and reverts alone. B1 (helpers + mocks) and B5 (3 pages) sit near the 400 edge; auto-chain splits a batch into two stacked PRs if apply crosses the budget — no user decision (delivery auto-chain). Story-first repetition is low-complexity, Medium risk.

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| B1 | `_shared/` helpers + tone maps + mocks | PR 1 | `cd web && npm test` | N/A (no page yet); helpers compile via `build-storybook` | Delete `_shared/` dir (no story references it) |
| B2 | Dashboard + ClientesList | PR 2 | `cd web && npm test && npm run build-storybook` (2 pages in index) | `npm run storybook` → pages/Dashboard, pages/ClientesList | Delete the 2 `.stories.tsx` + `mockData/{dashboard,clients}.ts` |
| B3 | ClientFicha + ConversationThread | PR 3 | same; 2 drill-down pages in index | `npm run storybook` → ficha + thread | Delete the 2 `.stories.tsx` + `mockData/conversations.ts` |
| B4 | CasesList + ConversationsList | PR 4 | same; 2 pages in index | `npm run storybook` → cases + conversations | Delete the 2 `.stories.tsx` + `mockData/cases.ts` |
| B5 | KbList + Settings + Login | PR 5 | same; 3 pages in index | `npm run storybook` → kb + settings + login | Delete the 3 `.stories.tsx` + `mockData/{kb,settings}.ts` |

## Phase 1 — Shared infrastructure (B1, T1.x, PR 1)

Batch gate: `cd web && npm test` + `npm run build-storybook` green; diff web/-only; zero new CSS; `web/src/components/**` absent from diff.

- [x] **T1.1** Create `web/src/stories/pages/_shared/DataTable.tsx` — generic `Column<T>`/`DataTableProps<T>` per design D6; emits `.table`/`.table th/td` + tokenized `--space-3` gap; `emptyMessage` renders `.empty-state`; optional `actions` cell. Acceptance: typechecks; `src/components/**` untouched. [Reqs: R-PRD-PG-2 · Files: `_shared/DataTable.tsx` · Deps: —] <!-- sdd-owner: implementation -->
- [x] **T1.2** Create `_shared/PageHeader.tsx` (title + subtitle/meta + actions), `_shared/StatCard.tsx` (`.kpi`-class card), `_shared/EmptyState.tsx` (`.empty-state` wrapper), `_shared/FlashMessage.tsx` (`.flash-message--{tone}`). Acceptance: each emits the `primitives.css` class it documents. [Reqs: R-PRD-PG-2 · Files: the 4 files · Deps: —] <!-- sdd-owner: implementation -->
- [x] **T1.3** Create `_shared/toneMaps.ts` + `toneMaps.test.ts` — `caseStatusTone` (abierto→neutral, en_evaluacion→warning, escalado→danger, cerrado→success), `customerStateTone` (nuevo→warning, activo→success, inactivo→neutral, bloqueado→danger) per design D4; test iterates all `Case` statuses + `CustomerState` from `types.ts` asserting each maps to a valid `BadgeTone`, none unmapped. Acceptance: `npm test` green, all statuses/state covered (RED→GREEN). [Reqs: R-PRD-PG-4, R-PRD-PG-7 · Files: `_shared/toneMaps.ts`, `_shared/toneMaps.test.ts` · Deps: —] <!-- sdd-owner: implementation -->
- [x] **T1.4** Create `_shared/mockData/dashboard.ts` — `Kpis`-typed `{contacts, derived, visit_requests}` + `motivos: Array<[service,count]>` + `window_days`/`window_start`. Acceptance: shape matches `types.ts` + serializer dicts (snake_case, ISO dates). [Reqs: R-PRD-PG-3, R-PRD-PG-6 · Files: `_shared/mockData/dashboard.ts` · Deps: —] <!-- sdd-owner: implementation -->

## Phase 2 — Dashboard + Clientes list (B2, T2.x, PR 2)

- [x] **T2.1** Create `_shared/mockData/clients.ts` — `Customer[]` (Chilean names/phones, all 4 states), typed to `types.ts`. Acceptance: `npm test` + typecheck green. [Reqs: R-PRD-PG-3 · Files: `_shared/mockData/clients.ts` · Deps: T1.2, T1.3] <!-- sdd-owner: implementation -->
- [x] **T2.2** Create `pages/Dashboard.stories.tsx` — `meta.title: "pages/Dashboard"`, `Overview` story: 3 StatCards + Motivos `DataTable` + muted `KPI window: last {window_days} days ({window_start})` caption. Acceptance: page in built index. [Reqs: R-PRD-PG-1, R-PRD-PG-5, R-PRD-PG-6 · Files: `pages/Dashboard.stories.tsx` · Deps: T1.1, T1.2, T1.4] <!-- sdd-owner: implementation -->
- [x] **T2.3** Create `pages/ClientesList.stories.tsx` — `Default / Loading / Empty` stories: SearchInput-pattern search + Export CSV (secondary Button) + `DataTable` (Name→ficha link, phone, state `Badge`, consent, created) + "No customers found" empty. Acceptance: page in index; R-PRD-PG-6 fields render. [Reqs: R-PRD-PG-1, R-PRD-PG-5, R-PRD-PG-6, R-PRD-PG-7 · Files: `pages/ClientesList.stories.tsx` · Deps: T2.1, T2.2] <!-- sdd-owner: implementation -->

## Phase 3 — Ficha + thread (B3, T3.x, PR 3)

- [x] **T3.1** Create `_shared/mockData/conversations.ts` — `Conversation`-typed list + `messages[]` matching `ConversationThread`; Customer data. Acceptance: shape fidelity. [Reqs: R-PRD-PG-3 · Files: `_shared/mockData/conversations.ts` · Deps: —] <!-- sdd-owner: implementation -->
- [x] **T3.2** Create `pages/ClientFicha.stories.tsx` — `Default` story: customer Card (PageHeader `Ficha: {name|phone}`, phone, state `Badge`, consent, muted email/comuna/address/created, FlashMessage) + state-form Card (Select 4 states + Change) + notes Card (author·created_at + textarea + Add) + history Card (3 `DataTable`s: conversations/cases/messages). Acceptance: page in index. [Reqs: R-PRD-PG-1, R-PRD-PG-5, R-PRD-PG-6, R-PRD-PG-7 · Files: `pages/ClientFicha.stories.tsx` · Deps: T1.2, T1.3, T3.1] <!-- sdd-owner: implementation -->
- [x] **T3.3** Create `pages/ConversationThread.stories.tsx` — `Default` story (PageHeader `# {id}` + muted state/created/summary; read-only message `DataTable` When/Direction/Type/Content+📎; footer no-reply note HH-5) + bubble-variant story. Acceptance: page in index; bubble variant visible. [Reqs: R-PRD-PG-1, R-PRD-PG-5, R-PRD-PG-6 · Files: `pages/ConversationThread.stories.tsx` · Deps: T1.2, T3.1] <!-- sdd-owner: implementation -->

## Phase 4 — Cases + Conversations list (B4, T4.x, PR 4)

- [x] **T4.1** Create `_shared/mockData/cases.ts` — `CasesResponse`-typed `cases[]` (embedded `customer`) + `users[]`, all 4 statuses incl. emergency. Acceptance: shape fidelity. [Reqs: R-PRD-PG-3 · Files: `_shared/mockData/cases.ts` · Deps: T1.3] <!-- sdd-owner: implementation -->
- [x] **T4.2** Create `pages/CasesList.stories.tsx` — `Default / Empty` stories: PageHeader "Cases (pending / escalated)" + FlashMessage + `DataTable` (#, Customer, Service, Status `Badge` tone per `caseStatusTone`, Summary, Emergency ⚠/acknowledged-by, Responsible, Actions) + Actions row (inline Select status + Select responsible + Update; Acknowledge button if unanswered emergency). Acceptance: page in index; D4 tones correct. [Reqs: R-PRD-PG-1, R-PRD-PG-5, R-PRD-PG-6, R-PRD-PG-7 · Files: `pages/CasesList.stories.tsx` · Deps: T1.1, T1.3, T4.1] <!-- sdd-owner: implementation -->
- [x] **T4.3** Create `pages/ConversationsList.stories.tsx` — `Default / Empty` stories, NEW design from `Customer`/`Conversation` shapes (design D5): DataTable (#, Customer name+muted phone, State, Summary, Last message `last_message_at`, Created). Flag `GET /conversations` list endpoint as a backend gap in the apply notes. Acceptance: page in index; flags gap. [Reqs: R-PRD-PG-1, R-PRD-PG-5, R-PRD-PG-6 · Files: `pages/ConversationsList.stories.tsx` · Deps: T1.1, T3.1] <!-- sdd-owner: implementation -->

## Phase 5 — KB + Settings + Login (B5, T5.x, PR 5)

- [x] **T5.1** Create `_shared/mockData/kb.ts` (`Doc[]`, 6-decimal USD cost, versions/active) + `_shared/mockData/settings.ts` (`Settings` incl. `snapshot`). Acceptance: shape fidelity. [Reqs: R-PRD-PG-3 · Files: `_shared/mockData/{kb,settings}.ts` · Deps: —] <!-- sdd-owner: implementation -->
- [x] **T5.2** Create `pages/KbList.stories.tsx` — `Default / Empty` stories: add-doc Card (Title Input + File input + Add) + docs `DataTable` (#, Title, Format, Version, Active, Provider/Model, Cost) + per-doc native `<details>` Edit accordion + Disable + Restore Select. Acceptance: page in index. [Reqs: R-PRD-PG-1, R-PRD-PG-5, R-PRD-PG-6 · Files: `pages/KbList.stories.tsx` · Deps: T1.1, T5.1] <!-- sdd-owner: implementation -->
- [x] **T5.3** Create `pages/Settings.stories.tsx` — `Default` story: 6 form Cards (scope rules textarea, emergency keywords, tone input, spend limits, meta pricing, current spend table + muted % line) + PageHeader + FlashMessage. Acceptance: page in index. [Reqs: R-PRD-PG-1, R-PRD-PG-5, R-PRD-PG-6 · Files: `pages/Settings.stories.tsx` · Deps: T1.1, T5.1] <!-- sdd-owner: implementation -->
- [x] **T5.4** Create `pages/Login.stories.tsx` — `Default / Error` stories: centered "Lumat Panel" auth Card (username + password + Login) + error state. Acceptance: page in index. [Reqs: R-PRD-PG-1, R-PRD-PG-5 · Files: `pages/Login.stories.tsx` · Deps: T1.2] <!-- sdd-owner: implementation -->

## Lifecycle Gates (parent-owned — after implementation work)

- [x] Bounded review on each batch PR (B1→PR1 … B5→PR5) before chaining the next. <!-- sdd-owner: parent -->
- [x] Archive gate (sdd-archive mandatory): run `graphify . --update` after apply and record the re-balanced web/ communities. <!-- sdd-owner: parent -->

## Traceability: Spec Requirements → Tasks

| Spec | Req → Tasks |
|------|-------------|
| panel-design-system | R-PRD-PG-1 → T2.2, T2.3, T3.2, T3.3, T4.2, T4.3, T5.2, T5.3, T5.4 |
| panel-design-system | R-PRD-PG-2 → T1.1, T1.2 (helpers under `_shared/`; never from `src/components/`) |
| panel-design-system | R-PRD-PG-3 → T1.4, T2.1, T3.1, T4.1, T5.1 (typed mocks) |
| panel-design-system | R-PRD-PG-4 → T1.3 + all batch gates (`npm test` green) |
| panel-design-system | R-PRD-PG-5 → T2.2, T2.3, T3.2, T3.3, T4.2, T4.3, T5.2, T5.3, T5.4 (build green, all 9 pages in index) |
| panel-design-system | R-PRD-PG-6 → T2.2, T2.3, T3.2, T3.3, T4.2, T4.3, T5.2, T5.3 (Jinja authority fields) |
| panel-design-system | R-PRD-PG-7 → T1.3, T2.3, T3.2, T4.2, T5.4 (tone maps + coverage test) |

Every requirement ID maps to ≥1 task. Test strategy is test-guarded (tone-map RED test) and additive; TDD config (`strict_tdd`) targets pytest for backend — this change is web/vitest-only.

## File Changes Coverage

| Design entry | Tasks |
|--------------|-------|
| `_shared/DataTable.tsx` | T1.1 |
| `_shared/{PageHeader,StatCard,EmptyState,FlashMessage}.tsx` | T1.2 |
| `_shared/toneMaps.ts` + `.test.ts` | T1.3 |
| `_shared/mockData/{dashboard,clients,cases,kb,settings,conversations}.ts` | T1.4, T2.1, T4.1, T5.1, T3.1 |
| `pages/{Dashboard,ClientesList,ClientFicha,ConversationsList,ConversationThread,CasesList,KbList,Settings,Login}.stories.tsx` | T2.2, T2.3, T3.2, T4.3, T3.3, T4.2, T5.2, T5.3, T5.4 |
| `web/src/components/**`, `.storybook/main.ts` (untouched) | All batch gates (R-PRD-PG-1 guard) |

## Ponytail Task Review (applied after writing — cuts)

1. Helpers merged 5→2 tasks (T1.1 one table, T1.2 all four trivial wrappers) — one reviewable surface, no dead weight.
2. Mocks split per page (design D3) — no `mockData.ts` blob; each batch owns its fixtures.
3. No modal — KB edit stays native `<details>` (T5.2); no Accordion task exists.
4. No router task — AppShell already switches via state; page stories render content directly.
5. No new deps / zero new CSS — enforced in every batch gate.
6. Login rides B5 (no separate batch).

## Risks / Notes

- **Conversations list backend gap (High)**: no Jinja/API list endpoint, only thread GET. B4/T4.3 designs the list from `Customer`/`Conversation` shapes (design D5) and flags `GET /conversations` for a future endpoint — confirm acceptance before B4 apply.
- **Mock typing drift (Med)**: mocks pinned to `web/src/types.ts` mirroring serializer shapes (snake_case, ISO, nullables); sealed by `npm test` + typecheck per batch.
- **B1/B5 budget (Med)**: near 400-line edge; auto-chain splits a batch into two stacked PRs at apply if authored diff crosses 400 — no user decision.
- **Helper boundary (Low)**: helpers live under `stories/pages/_shared/`, never imported by `src/components/**` (R-PRD-PG-2); diff guard enforces.
- **Thread bubble variant (Low)**: design D7 keeps flat `.table` canonical, bubble secondary — no component/backend change.

## Graph Check (mandatory per AGENTS.md — recorded)

Knowledge graph: `graphify-out/` (built from commit `5d5c6103`; 2117 nodes · 172 communities). Nodes consulted: `web/src/types.ts` types (`Customer`, `Case`, `Conversation`, `Doc`, `Settings`, `Kpis`, `CustomerState` — god nodes Customer 64 / Conversation 63 / Case 46), `StatusBadge`/`statusTone`, `AppShell` (community 38), backend serializer nodes (`to_customer_dict`, `to_case_dict`, `to_doc_dict`, `to_conversation_dict`), hyperedge "Admin Panel Jinja Template Set" + "Panel Design System SDD Change Cycle". Web/ area still under-represented (community 68 thin); archive gate MUST run `graphify . --update`.
