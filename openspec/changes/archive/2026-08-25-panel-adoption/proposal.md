# Proposal: Panel Adoption — Real SPA consumes the design system + JSON API

## Intent

Design system complete; real SPA (`web/`) still a bare auth gate. Make the panel look like the design and render live data: adopt all NAVIGATION views against the real JSON API.

## Scope

### In Scope
- Extract 10 story page components → `components/pages/`; thin wrappers preserve exports (R7).
- AppShell view switch → real pages (D7 state routing, no router).
- LoginForm, logout, 403 handling on admin pages (kb/settings).
- Dashboard renders real `compute_kpis` counts on designed cards.
- `GET /panel/api/conversations` (read-only, no assignee) + inbox/thread views.

### Out of Scope
- Designed dashboard metrics (autonomy %, response time, deltas) — follow-up.
- Activity feed; Asignado column; InboxThread composer/controls (HH-5); ChatWithAgent.
- react-router (D7); `_shared` relocation; token changes (palette frozen).

## Capabilities

### New Capabilities
- `panel-app`: production SPA pages (Login, Dashboard, Clientes, Cases, Conversations, KB, Settings), shell wiring, logout, 403 handling.

### Modified Capabilities
- `admin-panel`: ADD read-only `GET /panel/api/conversations` requirement.
- `panel-design-system`: MODIFY R-PRD-PG-2 — components MAY import `stories/pages/_shared` (ClientMemories precedent).

## Approach

Auto-chain, stacked-to-main, ≤400 lines/slice, native RDD review per slice:

| Slice | Boundary | Lines |
|-------|----------|-------|
| S1 Auth + gate | LoginForm, logout, api.ts, app.tsx | 400 |
| S2 Shell + Dashboard | AppShell map, Dashboard→Kpis | 380 |
| S3a/b Clientes | list+search, ficha drill-down | 450 |
| S4 Cases | list + update/ack refetch | 350 |
| S5 Conversations | endpoint + thread + inbox | 420→split |
| S6a/b KB + Settings | admin pages, 403, saves | 430 |

Order: auth → pages → views → endpoint.

## Affected Areas

`web/src/{app,api,types}.tsx|ts`, `components/domain/{AppShell,PanelShell}.tsx`, `components/pages/*` (new), `stories/pages/*.stories.tsx` (wrappers), `app/panel/api/routes/conversations.py`, tests.

## Risks

| # | Risk | Mitigation |
|---|------|------------|
| R1 | Dashboard mock↔API drift | Real counts; metrics follow-up |
| R2 | No conversations endpoint | Thin additive endpoint |
| R3 | Thread interactions unsupported | Read-only thread |
| R4 | No router → inert hash links | onClick drill-downs |
| R5 | `_shared` coupling deepens | R-PRD-PG-2 delta |
| R6 | 403 on admin views | ApiError 403 → denied |
| R7 | Story tests import views | Preserve exports |
| R8 | Budget >400 | Stacked slices; S5 splits |

## Rollback Plan

Per slice: revert its commit — each lands independently; wrappers keep Storybook/tests intact. Endpoint additive: drop route + tests. No token changes.

## Dependencies

- Archived design system + stories; live JSON API (auth/kpis/clients/cases/kb/settings).
- No new npm/Python deps; router NOT added (D7).

## Success Criteria

- [x] All 6 NAVIGATION views render live data — AppShell D7 routing now mounts the live clients, conversations, cases, KB, and settings pages.
- [x] Operador sees 403 on kb/settings.
- [x] Story tests green (exports preserved).
- [x] Backend tests for conversations endpoint.
- [ ] RDD review per slice; no token changes — pending final verification/review.
