# Proposal: Panel Operational Views

## Intent

Retire Jinja now that VPS delivery is SPA + API + WebSocket + CSV export. Dual-render maintenance and incomplete controls mislead operators. React becomes the panel: conversations, cases, client ficha, KB, settings, exports, and advanced KPIs.

## Scope

### In Scope
- Complete `ClientFicha`, `KbList`, and `ClientesList` against APIs.
- Wire `AdvancedDashboard` into `panelRoutes.ts` and `AppShell.tsx`.
- Delete server-rendered routes/templates and Jinja-only dependencies; migrate tests.
- Narrow nginx to SPA, `/panel/api`, `/panel/ws`, and `/panel/export/*.csv`.
- Keep SPA only on `panel.lumat.cl`; `agente.lumat.cl` remains API/webhook-only.

### Out of Scope
- New features beyond parity, redesign, or agent-host SPA expansion.
- API redesign, conversation replacement, or visual/accessibility changes.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `panel-app`: SPA-only delivery, operational parity, AdvancedDashboard reachability, and Jinja retirement.
- `spa-delivery`: remove broad legacy fallback while preserving API, WS, and export proxy ownership.

## Approach

Reuse JSON APIs and `api.ts`. Preserve cookie auth, `require_user` exports, KB validation, audited transitions, richer conversations/realtime, reduced-motion, and compact accessibility grammar. Redirect `/`, `/panel/`, and `/panel/login` to `/panel/app/`; remove broad `/panel/` proxy. Graph consulted: AppShell, PanelShell, panelRoutes, API hubs, deps, and nginx.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `web/src/components`, `api.ts` | Modified | Controls, exports, routing |
| `app/panel/routes`, `templates`, `deps.py` | Removed/modified | Retire Jinja; retain API/CSV |
| `infra/nginx`, tests, specs | Modified | Delivery and contracts |

## Slices (<=400 changed lines)

1. **Client ficha parity** — state/note controls, refresh, audit-safe errors. Roll back page changes.
2. **KB mutations** — upload, edit, disable, restore with validation. Roll back UI wiring.
3. **Client exports** — authenticated clients/cases CSV links. Roll back export UI.
4. **Advanced dashboard route** — expose summary/trend/drilldown. Roll back route wiring.
5. **Legacy test migration** — replace HTML/form contracts with SPA/API contracts. Roll back tests.
6. **Jinja retirement** — delete legacy routes/templates and unused dependency code. Restore deleted files to roll back.
7. **Nginx narrowing and specs** — redirects, proxy preservation, delivery assertions, deltas. Revert commit to prior delivery.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Retired path remains used | Med | Search, redirects, smoke checks |
| Auth or nginx drift | Med | Reuse APIs, audit coverage, static contracts |

## Rollback Plan

Revert slices in reverse order; restore the known-good nginx tag and Jinja files if smoke fails.

## Success Criteria

- [ ] Operators complete all listed workflows in the SPA; advanced KPIs are reachable.
- [ ] Jinja routes/templates are absent; API, WS, CSV, auth, and conversation behavior remain green.
- [ ] `uv run pytest tests/` and `cd web && npm run build` pass; nginx proves SPA/API/WS/export ownership.
