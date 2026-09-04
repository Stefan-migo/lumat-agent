# Proposal: Panel SPA Production Delivery

## Intent

Make React a production surface at `/panel/app/` on `panel.lumat.cl`, without
changing UX or removing Jinja. Nginx owns static files and History API
fallback; FastAPI owns Jinja, `/panel/api/`, and `/panel/export/`.

## Scope

### In Scope
- Package `web/dist` into a custom nginx image, preserving read-only storage and
  tagged-checkout deployment.
- Serve `/panel/app/` with `index.html` fallback; proxy API, export, and legacy
  Jinja routes to FastAPI.
- Move Vite and PWA paths/scope to `/panel/app/`, retaining icons and UX.
- Document build, deploy, rollback, CI checks, and VPS smoke evidence.

### Out of Scope
- Visual redesign, dark mode, agenda/automation work, auth changes, or Jinja
  migration.
- SPA delivery on `agente.lumat.cl`; it remains webhook/API and Jinja-compatible.

## Capabilities

### New Capabilities
- `spa-delivery`: Nginx static delivery, fallback, host boundary, and artifact
  ownership.

### Modified Capabilities
- `panel-app`: `/panel/app/` is added while Jinja remains authoritative under
  `/panel/`.
- `pwa-shell`: manifest, worker, cache allowlist, start URL, and scope move to
  `/panel/app/`.

## Approach

Use a multi-stage `infra/nginx/Dockerfile` to build the frontend and copy it to
`/usr/share/nginx/html/panel/app/`. This avoids host mounts and volume
lifecycle, keeps bytes immutable per release, and works with `read_only: true`.
Add ordered API/export proxy locations, `/panel/app/` `try_files`, then the
legacy `/panel/` proxy. Build the SPA only on `panel.lumat.cl`.
Update `vite.config.ts`, `index.html`, `manifest.webmanifest`, `pwa.ts`,
`sw.js`, and brand delivery paths (PNG content unchanged). Keep API URLs and
auth unchanged.

Ponytail: no router, FastAPI static layer, runtime volume manager, or new
abstraction; native nginx `try_files` and existing npm/Vite/PWA mechanisms are
sufficient.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `infra/nginx/*`, `infra/docker-compose.prod.yml` | Modified/New | Image and route precedence |
| `web/vite.config.ts`, `web/index.html`, `web/public/*`, `web/src/pwa.ts` | Modified | Base and PWA paths |
| `docs/ops.md` | Modified | Build, deploy, smoke, rollback |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Fallback shadows backend routes | Med | Ordered proxy locations and nginx tests |
| PWA path drift | Med | Build assertions for manifest, scope, and cache paths |
| Agent unexpectedly needs SPA | Low | Confirm in smoke; retain proxy-only config |

## Rollback Plan

Restore the previous tag and run the documented compose rebuild. Previous nginx
configuration resumes proxying `/panel/` to FastAPI; no data rollback applies.

## Dependencies

- Existing Node/npm dependencies in `web/package.json`.
- VPS access and a known-good tag for smoke comparison.

## Success Criteria

- [ ] Build and nginx checks prove assets and deep-link fallback.
- [ ] Existing pytest suites preserve Jinja, API auth, and export contracts.
- [ ] Panel login, deep links, installability, and offline shell work; agent webhook/health remain green.
