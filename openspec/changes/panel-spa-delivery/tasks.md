# Tasks: Panel SPA Production Delivery

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 450–550 lines |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Split | PR 1 PWA; PR 2 nginx/Compose; PR 3 docs/verification |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Move Vite/PWA URLs to `/panel/app/` | PR 1 | `cd web && npm ci && npm test -- src/pwa.test.ts && npm run build` | HTTPS shell and offline check | `web/vite.config.ts`, `web/index.html`, `web/public/`, `web/src/pwa.ts` |
| 2 | Deliver immutable SPA without route capture | PR 2 | `pytest tests/integration/test_panel_delivery.py && docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml config` | Build, `nginx -t`, curl API/export/Jinja/deep link | `infra/nginx/Dockerfile`, panel conf, prod Compose, invariant test |
| 3 | Document release, smoke, hardening, rollback | PR 3 | `pytest tests/` plus web build/test | VPS smoke; N/A locally for public DNS | `docs/ops.md`, `docs/hardening.md` |

## Phase 1: RED Tests / Contracts

- [x] 1.1 **Objective:** define delivery boundary. **Files:** `tests/integration/test_panel_delivery.py`. **Done:** RED assertions cover Dockerfile/Compose ownership, agent config, and API/export/legacy/app precedence. **Verify:** `pytest tests/integration/test_panel_delivery.py` (GREEN: 5 passed).
- [x] 1.2 **Objective:** lock PWA paths. **Files:** `web/src/pwa.test.ts`. **Done:** RED assertions cover `/panel/app/` metadata, worker/scope, allowlist, API exclusion, and old-cache replacement. **Verify:** `cd web && npm test -- src/pwa.test.ts` (RED).

## Phase 2: Production Implementation

- [x] 2.1 **Objective:** own immutable bytes. **Files:** `infra/nginx/Dockerfile`. **Done:** Node `22.22.2-alpine` builds and nginx `1.27-alpine` serves `dist` at `/usr/share/nginx/html/panel/app/`. **Verify:** `docker build -f infra/nginx/Dockerfile -t lumat-nginx:panel-spa-delivery .` (success).
- [x] 2.2 **Objective:** enforce routing. **Files:** `infra/nginx/panel.lumat.cl.conf`; do not change `agente.lumat.cl.conf`. **Done:** ordered API/export proxy, app headers/static/fallback, final Jinja proxy. **Verify:** `docker run --rm lumat-nginx:panel-spa-delivery nginx -t` with temporary `api` DNS/cert harness (success).
- [x] 2.3 **Objective:** wire production ownership. **Files:** `infra/docker-compose.prod.yml`. **Done:** custom nginx build replaces config bind while cert volumes, `read_only`, tmpfs, and hardening remain. **Verify:** `docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml config` (success).
- [x] 2.4 **Objective:** relocate shell/PWA. **Files:** `web/vite.config.ts`, `web/index.html`, `web/public/manifest.webmanifest`, `web/src/pwa.ts`, `web/public/sw.js`. **Done:** base, scope, precache, cleanup, and registration use `/panel/app/`; API is excluded. **Verify:** `cd web && npm ci && npm run build && npm test`.

## Phase 3: Documentation / Verification

- [ ] 3.1 **Objective:** make operations reproducible. **Files:** `docs/ops.md`, `docs/hardening.md`. **Done:** tagged build/deploy, nginx/read-only probes, panel login/deep-link/asset/PWA/offline/export/agent smoke evidence, manual limits, and previous-tag rollback are documented. **Verify:** review commands against the documented VPS smoke procedure.
- [ ] 3.2 **Objective:** prove the release. **Files:** test/build outputs only. **Done:** all invariants and existing suites pass; VPS-only checks are explicitly unexecuted when DNS/credentials are unavailable. **Verify:** `cd web && npm ci && npm run build && npm test`; `docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml config`; `docker run --rm <nginx-image> nginx -t`; `pytest tests/`.

## Graph Nodes Consulted

`pwa.ts`, `pwa.test.ts`, `vite.config.ts`, `Prod nginx reverse proxy (TLS)`, `LumatAgent Prod Compose Override`, `panel/deps.py`, `panel/routes/export.py`, `test_infra.py`, and `Ops Runbook`.
