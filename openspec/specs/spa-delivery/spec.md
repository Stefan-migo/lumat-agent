# SPA Delivery Specification

## Requirements


### Requirement: SPA-DEL-1 — Bounded routing

On `panel.lumat.cl`, the system MUST serve the SPA only below `/panel/app/` and MUST preserve Jinja route authority everywhere else under `/panel/`. `/panel/api/` and `/panel/export/` MUST remain backend routes and MUST NOT be handled by the SPA fallback. `agente.lumat.cl` MUST remain proxy-only.

#### Scenario: Deep link serves the shell
- GIVEN a built SPA and a deep link below `/panel/app/`
- WHEN the URL is requested directly
- THEN the response is the SPA `index.html` with a success status

#### Scenario: Backend prefixes bypass fallback
- GIVEN any request below `/panel/api/` or `/panel/export/`
- WHEN nginx receives it
- THEN it proxies to FastAPI and never returns the SPA `index.html`

#### Scenario: Legacy panel remains intact
- GIVEN a Jinja URL below `/panel/` outside the SPA subtree
- WHEN it is requested on `panel.lumat.cl`
- THEN the FastAPI HTML/redirect behavior is preserved
- AND `agente.lumat.cl` has no SPA static or fallback behavior

### Requirement: SPA-DEL-2 — Same-origin authenticated entry

The SPA MUST use the existing same-origin panel API and session cookie contract without CORS or authentication changes.

#### Scenario: Login succeeds under the SPA prefix
- GIVEN an unauthenticated user at `/panel/app/`
- WHEN valid credentials are submitted
- THEN the login API sets/updates the session cookie and the authenticated shell loads

### Requirement: SPA-DEL-3 — Immutable reproducible delivery

The production build MUST produce an nginx-owned, read-only-compatible artifact from a tagged checkout. The repository MUST verify the frontend build, nginx configuration validity, manifest/scope/cache URL invariants, and Jinja/API/export pytest suites.

#### Scenario: Release checks pass
- GIVEN a tagged checkout with the required dependencies
- WHEN the production build and checks run
- THEN the artifact is reproducible, nginx configuration is valid, and all required assertions and existing suites pass

### Requirement: SPA-DEL-4 — Operational recovery

Operations documentation MUST specify build, tagged deploy, VPS smoke checks, manual evidence limits, and rollback by restoring a known-good tag. Rollback MUST restore full `/panel/` proxy behavior without data rollback.

#### Scenario: Rollback restores the legacy surface
- GIVEN a failed SPA release
- WHEN the operator deploys the previous known-good tag
- THEN nginx again proxies all `/panel/` requests to FastAPI and the documented smoke checks can confirm recovery
