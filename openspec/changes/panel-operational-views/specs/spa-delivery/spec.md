# Delta for spa-delivery

## MODIFIED Requirements

### Requirement: SPA-DEL-1 — SPA-only bounded routing

On `panel.lumat.cl`, the system MUST redirect `/`, `/panel/`, and `/panel/login` to `/panel/app/`, serve the SPA below `/panel/app/`, and NOT serve a broad legacy `/panel/` fallback. `/panel/api/`, `/panel/ws`, and `/panel/export/` MUST remain backend routes and MUST bypass the SPA fallback. `agente.lumat.cl` MUST remain API/webhook proxy-only without SPA static or fallback behavior.
(Previously: `/panel/app/` was the only SPA subtree while Jinja retained authority elsewhere under `/panel/`.)

#### Scenario: Entry paths redirect to the SPA
- GIVEN a request to `/`, `/panel/`, or `/panel/login` on panel.lumat.cl
- WHEN nginx receives it
- THEN it redirects to `/panel/app/`

#### Scenario: SPA deep link is served
- GIVEN a built SPA and a deep link below `/panel/app/`
- WHEN the URL is requested directly
- THEN the response is the SPA `index.html` with a success status

#### Scenario: Backend prefixes bypass fallback
- GIVEN a request below `/panel/api/`, `/panel/ws`, or `/panel/export/`
- WHEN nginx receives it
- THEN it proxies to FastAPI and never returns SPA `index.html`

#### Scenario: Agent host remains proxy-only
- GIVEN a request to agente.lumat.cl
- WHEN nginx receives it
- THEN no SPA static or fallback behavior is selected

### Requirement: SPA-DEL-3 — Immutable reproducible delivery

The production build MUST produce an nginx-owned, read-only-compatible artifact from a tagged checkout. The repository MUST verify the frontend build, nginx configuration validity, redirect/proxy scope and cache URL invariants, SPA-only/Jinja retirement assertions, and API/WS/CSV/auth pytest suites.
(Previously: verification covered frontend build, nginx validity, manifest/scope/cache invariants, and Jinja/API/export suites without the SPA-only routing assertions.)

#### Scenario: Release checks pass
- GIVEN a tagged checkout with required dependencies
- WHEN production build and delivery checks run
- THEN the artifact is reproducible, nginx is valid, scope assertions pass, and required suites are green
