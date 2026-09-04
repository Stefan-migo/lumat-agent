# Design: Panel SPA Production Delivery

## Context and Technical Approach

The existing edge proxies all `/panel/` to FastAPI (`panel.lumat.cl.conf:46-53`), while the API image deliberately excludes `web/` (`Dockerfile:26-28`). Build the frontend inside a new immutable nginx image, based on the current `nginx:1.27-alpine` production image (`docker-compose.prod.yml:65-66`). FastAPI remains the owner of Jinja, auth, `/panel/api/`, and `/panel/export/`.

## Architecture Decisions

| Decision | Alternatives | Rationale |
|---|---|---|
| Add `infra/nginx/Dockerfile` with Node 22.22.2 build stage and nginx runtime | FastAPI static files; host `dist` mount | Keeps static delivery at the TLS edge, preserves `read_only`, and makes bytes tag-reproducible. `npm ci` + existing `npm run build` are the only frontend build mechanisms. |
| Copy both host configs and `snippets/` into the image; remove nginx config bind mount | Runtime config mount; separate host images | The current mount (`docker-compose.prod.yml:89-92`) would hide image files. One image preserves the agent server block unchanged and avoids deployment-time drift. |
| Bound static subtree `/panel/app/`; explicit backend locations before legacy proxy | SPA at `/panel/` or agent host | Satisfies SPA-DEL-1 without stealing Jinja routes or changing auth/API contracts. |

## Nginx Precedence and Data Flow

`browser → panel.lumat.cl → nginx location → static image OR api:8000`

In `panel.lumat.cl.conf`, use these blocks (most specific behavior first):

```nginx
location = /panel/app { return 301 /panel/app/; }
location = /panel/api { include /etc/nginx/conf.d/snippets/proxy-pass.conf; }
location ^~ /panel/api/ { include /etc/nginx/conf.d/snippets/proxy-pass.conf; }
location = /panel/export { include /etc/nginx/conf.d/snippets/proxy-pass.conf; }
location ^~ /panel/export/ { include /etc/nginx/conf.d/snippets/proxy-pass.conf; }
location = /panel/app/index.html { add_header Cache-Control "no-cache" always; try_files $uri =404; }
location ^~ /panel/app/assets/ { try_files $uri =404; add_header Cache-Control "public, max-age=31536000, immutable" always; }
location ^~ /panel/app/ { try_files $uri $uri/ /panel/app/index.html; }
location /panel/ { include /etc/nginx/conf.d/snippets/proxy-pass.conf; }
```

Missing hashed assets return 404; only missing SPA documents fall back. `agente.lumat.cl.conf` and `proxy-pass.conf` remain unchanged, so the agent host stays proxy-only and headers/URI preservation remain intact.

## File Changes

| File | Action | Design |
|---|---|---|
| `infra/nginx/Dockerfile` | Create | `node:22.22.2-alpine`: copy lock/package, `npm ci`, copy web, `npm run build`; `nginx:1.27-alpine`: remove default config, copy both configs/snippet and `dist` to `/usr/share/nginx/html/panel/app/`; retain base entrypoint/CMD. |
| `infra/nginx/panel.lumat.cl.conf` | Modify | Locations and cache headers above; Jinja fallback remains last. |
| `infra/docker-compose.prod.yml` | Modify | nginx `build: {context: .., dockerfile: infra/nginx/Dockerfile}` and matching immutable image tag; remove config bind mount, retain cert volumes/read-only/tmpfs. |
| `web/vite.config.ts` | Modify | `base: '/panel/app/'`; API dev proxy stays `/panel/api`. |
| `web/index.html` | Modify | Manifest link `/panel/app/manifest.webmanifest`; retain theme color. |
| `web/public/manifest.webmanifest` | Modify | `start_url`, `scope`, and both unchanged brand icon URLs use `/panel/app/`. |
| `web/src/pwa.ts`, `web/public/sw.js` | Modify | Worker `/panel/app/sw.js`, scope/cache allowlist under `/panel/app/`; precache `/panel/app/`, exclude API, and delete old `lumat-shell-*` caches. |
| `tests/integration/test_panel_delivery.py` | Create | Assert Dockerfile/compose ownership and all built-source PWA paths; update `web/src/pwa.test.ts` expectations. |
| `docs/ops.md`, `docs/hardening.md` | Modify | Tagged nginx build/deploy, smoke evidence, rollback, and read-only nginx probes. |

API strings in `web/src/app.tsx`/`api.ts`, export links, Storybook, and tests remain `/panel/api` or `/panel/export`; they are backend contracts, not static asset paths.

## Contracts, Errors, and Verification

Same-origin `credentials: 'include'` and existing session cookies are unchanged. A missing `dist` fails `docker build` (no partially running release); `nginx -t` runs against the built image before deploy. Repo checks are `npm ci && npm run build && npm test`, the new invariant pytest, `docker compose config`, and `docker run --rm <nginx-image> nginx -t`. Existing auth, API, export, Jinja, and agent health/webhook pytest suites remain required. VPS smoke records login, deep link, asset 200, PWA install/offline shell, CSV export, agent health/webhook, and `monitor.sh`; rollback checks out the prior tag and repeats compose build.

## Threat Matrix

| Boundary | Status / response / RED test |
|---|---|
| Documentation-like paths | N/A: no executable-file classification. |
| Git repository selection | N/A: deploy documents, but does not implement, git selection. |
| Commit state | N/A: no commit automation. |
| Push state | N/A: no push automation. |
| PR commands | N/A: no PR automation. |
| Routing/process boundary | Applicable: `/panel/api/` and `/panel/export/` proxy; `/panel/app/` fallback; legacy and agent never fallback. RED assertions cover each path and fallback exclusion. |

## Rollout, Risks, and Open Questions

Deploy from a tagged checkout with the custom nginx image; no migration or feature flag. Main risks are location precedence and PWA path drift, mitigated by static assertions plus `nginx -t` and VPS smoke. No blocking open questions; rollback is tag reversal with no data rollback.
