# ODD: panel-sw-stale-shell

## Objective

Make it impossible for a panel deploy to strand a returning browser on a white
screen, while keeping the offline cache that is genuinely safe: the
content-hashed assets under `/panel/app/assets/`.

## Problem (verified in production, 2026-09-22)

After the `v2026.09.2` catch-up deploy (`10165a6d` → `cfbefcbd`), opening
`https://panel.lumat.cl/panel/app/` in a browser that had visited the panel
before rendered a **white screen**, with `app/assets/index-BFVxKv6R.js: 404`.

Measured, not inferred:

| Observation | Result |
|---|---|
| `index.html` served **now** references | `/panel/app/assets/index-jjOAEfG0.js` and `index-3iqjaBzb.css` → both **200** |
| The stranded browser requested | `index-BFVxKv6R.js` — a hash from a **previous** build → **404** |
| `git log 10165a6d..main -- web/public/sw.js` | **empty** — the worker did not change across the deploy |
| Same URL in a private window (no service worker) | loads correctly |
| Storage cleared / worker unregistered, then reload | loads correctly |

The build and the server were healthy the whole time. Only the cached shell was
stale.

## Root cause

Three facts compose into the failure.

1. **The server already does the right thing.** `infra/nginx/panel.lumat.cl.conf:93-105`
   serves `/panel/app/index.html` with `Cache-Control: no-cache`, and
   `/panel/app/assets/` with `public, max-age=31536000, immutable`. Nothing here
   needs fixing.
2. **The service worker overrides the server.** `web/public/sw.js` handled every
   cacheable request cache-first, including the shell document: it returned the
   previously cached `index.html` **without consulting the network**, even
   online. That is exactly the revalidation nginx asked for, discarded.
3. **The worker cannot update itself out of the defect.** `web/public/sw.js`
   lives in Vite's `publicDir`, which is copied byte-for-byte into `dist/`, then
   into the nginx image. Its bytes are identical across deploys, so a browser
   that already installed it never re-installs it. The defect is sticky by
   construction, not by accident.

Failure chain: the worker caches the shell → a deploy changes the asset hashes →
`sw.js` bytes are unchanged, so the browser does not update it → cache-first
serves the old shell HTML → that HTML requests a JS file that no longer exists →
404 → white screen.

A detail worth keeping: the `activate` handler **already** purges "obsolete"
caches, filtering on `key !== CACHE_NAME`. With a constant `CACHE_NAME` that set
is always empty, so the purge is dead code that reads like a safety net.

## Approach

**Only content-addressed URLs may be cache-first.**

- `/panel/app/assets/**` — Vite content-hashes these filenames and nginx marks
  them `immutable`. A given URL can never mean different bytes, so cache-first is
  both correct and valuable.
- Everything else cacheable has a **stable path** — the shell `/panel/app/`,
  `/panel/app/brand/**` (Vite copies `public/` verbatim, so those names do not
  change), and `manifest.webmanifest`. For these, cache-first *is* the bug. They
  become **network-first with a cache fallback**, so the offline shell still loads
  and a deploy is adopted on the next navigation.

### Rejected: versioning `CACHE_NAME` with a build hash

The backlog direction was "version `CACHE_NAME` per build (inject the Vite hash)".
Verified against the repository, that path is the expensive one and it solves
nothing this policy split does not:

- No build id reaches the panel image. `GIT_SHA` is wired only into the `api`
  service build (`infra/docker-compose.prod.yml:26-30`); the `nginx` service
  (`infra/nginx/Dockerfile`) takes no build args and no environment.
- `public/` is copied untransformed, so injecting a value into `sw.js` needs a
  Vite plugin **plus** Dockerfile and compose plumbing.

Three lines of cache policy beat a build-id pipeline. The version experiment can
come back the day a build id is actually plumbed to the panel image.

## What changes

| File | Change |
|---|---|
| `web/public/sw.js` | Split the fetch policy: `cache-first` for `/panel/app/assets/**` only; `network-first` with a cache fallback for the shell, `/panel/app/brand/**` and the manifest. Remove the inert `activate` purge and name the cache-growth ceiling with a `ponytail:` marker. |
| `web/src/pwa.ts` | Remove `isCacheableAsset` and `isObsoleteCache`. Both are **production-dead** (only the test imports them), they duplicate the worker's policy, and duplicated policy is what let the worker and the TS side disagree in the first place. |
| `web/src/pwa.test.ts` | Replace the source-substring assertions with a test that actually exercises the worker: a fake service-worker environment drives `install`/`activate`/`fetch` and reproduces the stranded-browser scenario. This is the regression guard the current tests are not — they assert that strings exist, not what the worker does. |
| `docs/ops.md` | One operational note in §2.1.2: browsers already stranded by the old worker need a **single reload** after the deploy that carries this fix, because a page that never renders cannot re-register its own worker. |
| `odd/tasks/panel-sw-stale-shell.md` | This record. |

## Authorized scope

`web/public/sw.js`, `web/src/pwa.ts`, `web/src/pwa.test.ts`, `docs/ops.md`, this
work-unit record.

## Out of scope (reported, not decided)

- **Removing the service worker and the PWA registration entirely.** Reported as
  a finding: Playwright already blocks service workers
  (`web/playwright.config.ts:8`), production has no traffic, and an *offline
  admin panel* is of dubious value — removing it would be the smallest fix of
  all. It is not done here because it removes authorized offline behaviour and
  that call belongs to the owner.
- **Plumbing a build id into the panel image** to version the cache name. See
  "Rejected" above.
- **The nginx image build itself.** No Dockerfile change is needed; the image
  already copies `dist/` verbatim. Only a panel rebuild and redeploy.
- **Unbounded asset-cache growth.** Pre-existing and unchanged by this work unit
  (the purge was already inert). Named in the code with a `ponytail:` marker and
  the upgrade path; see Progress.

## Consequence to state plainly

This fix cannot repair a browser that is **already** stranded: the page that
would re-register the worker is the page that never renders. Those browsers need
one reload after the deploy (or clear site data), and the fixed worker then keeps
them current forever. `docs/ops.md` carries the note so the next operator is not
surprised by it.

## Verification

- `npm test` in `web/` — vitest, including the new worker-behaviour test.
- The new test must **fail** against the pre-fix `sw.js` and pass after it; that
  RED→GREEN is the evidence the test actually covers the defect.
- `npm run build` in `web/` — the panel still builds and emits `dist/sw.js`.
- Deploy-time (owner-authorized, not part of this work unit): rebuild the panel
  image and confirm a previously-stranded browser recovers with one reload.

Resolved TDD mode: **off** — the repository declares no TDD configuration and the
owner did not request it. Runner: `npm test` (vitest) in `web/`. Ordinary
functional checks apply; the bug fix is nevertheless written test-first.

Delivery forecast: ~130 authored changed lines (additions + deletions), well under
the ~400-line budget → strategy `ask-on-risk`, no chain needed, single PR.

## Route per task

| Task | Route | Trigger evidence |
|---|---|---|
| T1–T4 (implementation) | delegated writer | Writer trigger: 2+ non-trivial files (`sw.js`, `pwa.ts`, tests, docs) |
| Build-pipeline mapping (done) | delegated exploration | Mapping trigger: understanding required 4+ files |
| Verification | delegated writer self-check + parent spot check | RDD state read at verification time |

## Tasks

- [ ] **T1 — Reproduce the defect in a test (RED).** Add a fake service-worker
      environment to `web/src/pwa.test.ts`: a capture of `self.addEventListener`,
      a minimal `CacheStorage`/`Cache`, a stubbed `fetch`, and the worker source
      loaded from `public/sw.js`. Assert that with a stale shell already cached
      and the network serving a new shell, a navigation request returns the
      **new** shell. Must fail against the current worker.
- [ ] **T2 — Fix the fetch policy (GREEN).** In `web/public/sw.js`, keep
      `cache-first` only for `/panel/app/assets/**`; serve the shell,
      `/panel/app/brand/**` and `manifest.webmanifest` network-first with a cache
      fallback. Keep `/panel/api/**` and `*.html` out of the cache entirely.
- [ ] **T3 — Delete the dead policy code.** Remove the inert `activate` purge
      from `sw.js` and the production-dead `isCacheableAsset` / `isObsoleteCache`
      from `pwa.ts`; drop their now-meaningless assertions. Add a `ponytail:`
      marker in `sw.js` naming the asset-cache growth ceiling and its upgrade
      path (version the cache name once a build id reaches the panel image).
- [ ] **T4 — Document the one-reload consequence** in `docs/ops.md` §2.1.2.
- [ ] **T5 — Verify.** `npm test` and `npm run build` in `web/`, plus the
      Ponytail post-write pass over the diff. Record the observed results here.

## Progress

- [x] Root cause confirmed with production evidence and repository inspection
      (nginx cache headers, Vite `publicDir` copy, `sw.js` byte-identity across
      deploys) — see the table above.
- [x] Approach chosen; the build-hash variant rejected with verified reasons.
- [x] Worktree created: `../lumat-agent-odd-panel-sw-stale-shell`, branch
      `odd/panel-sw-stale-shell`.
- [ ] T1–T5 outstanding.
