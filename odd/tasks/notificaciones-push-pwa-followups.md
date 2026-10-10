# notificaciones-push-pwa-followups

## Objective

Close the two non-blocking WARNING follow-ups left by the RDD review of the shipped
push/PWA feature (PR #556, merge `c3dacdcd`): deactivate a dead Web Push subscription on a
terminal push-service failure (R3-001), and make the browser subscribe flow reuse an
existing subscription / recover after a failed save (R3-002). Hardening of reliability; the
happy path already works.

## Problem

1. **R3-001 — `app/services/push.py:25-38`.** `webpush(...)` (L33) can raise
   `WebPushException` when the push service answers 404/410 (endpoint expired or
   unregistered). The exception propagates and the `PushSubscription` row stays `active=True`.
   The notification sweep keeps retrying the same dead endpoint on every future event, and
   dead subscriptions accumulate.
2. **R3-002 — `web/src/components/pages/PushSettings.tsx:18-39`.** `enable()` runs
   `pushManager.subscribe()` (L28) then `POST /push-subscription` via `savePushSubscription`
   (L34). If the browser subscribe succeeds but the POST fails, the `catch` (L36-38) only sets
   `error=true` and leaves the browser subscription installed. Retrying calls `subscribe()`
   again; in Chromium that can raise `InvalidStateError` when an existing subscription is
   present with a different `applicationServerKey`.

## Why

The RDD review approved the feature but flagged both as reliability WARNINGs. The owner
wants them closed as their own small ODD change. No behavior change on the happy path.

## Scope

**In:**
- `app/services/push.py` and its test in `tests/integration/test_h4_notifications.py`.
- `web/src/components/pages/PushSettings.tsx` and `web/src/components/pages/PushSettings.test.tsx`.

**Out:** no new dependency, no migration, no new endpoint, no signature change to public
service functions, no UI copy change beyond what the fix requires.

## Decisions (closed)

- **R3-001:** catch `WebPushException` in `send_push`; when
  `exc.response is not None and exc.response.status_code in (404, 410)`, set
  `subscription.active = False` **in the same `session_scope()`** (the subscription is read
  there) and **re-raise** so the notification op still follows its retry/fallback. Leave the
  row in place (no delete) — deactivation is auditable and reversible.
- **R3-002 (final):** before subscribing, call `registration.pushManager.getSubscription()`;
  if one exists, reuse it and re-POST instead of calling `subscribe()` again (kills the
  `InvalidStateError` path). Additionally, do NOT mark `permission` as `"granted"` until
  `savePushSubscription` succeeds — so after a failed POST the activation button stays
  available (JSX unchanged) and an in-place retry reuses the subscription and re-saves.
  No `unsubscribe()` cleanup and no JSX change: reuse is strictly better than destroying a
  possibly-valid subscription on a transient failure, and an orphaned subscription the user
  never retries is benign.

## Work units (stable IDs)

### WU1 — R3-001 backend: deactivate subscription on 404/410
- [x] RED: a test where `webpush` raises `WebPushException` with `response.status_code == 410`;
      assert `send_push` re-raises and the `PushSubscription` row ends `active is False`.
- [x] GREEN: guard the `webpush` call, deactivate on 404/410, re-raise.
- [x] No regression: existing `test_send_push_uses_stored_subscription` and the
      inactive/missing cases stay green.

### WU2 — R3-002 frontend: reuse existing subscription / recover after failed POST
- [x] RED: a test where `pushManager.getSubscription()` resolves an existing subscription and
      `subscribe()` must NOT be called again (the existing one is re-POSTed); plus a case where
      the first POST rejects and the flow recovers to a consistent state.
- [x] GREEN: reuse `getSubscription()` before subscribing; recover on save failure.
- [x] No regression: existing `PushSettings.test.tsx` cases stay green.

## Acceptance criteria

1. Each new test fails before its fix (observed RED) and passes after (observed GREEN).
2. Backend full suite green: `eval "$(infra/test-db.sh env)" && uv run pytest tests/`.
3. Frontend type check green: `npm --prefix web run build` (`tsc -b`); touched Vitest files green.
4. Conventional commits, one work unit per commit, ≤5 files each; no AI attribution.
5. Branch contains current `main` head before any merge (manual, pre-merge check).

## Checks

- Backend targeted: `eval "$(infra/test-db.sh env)" && uv run pytest tests/integration/test_h4_notifications.py -q`.
- Backend full: `eval "$(infra/test-db.sh env)" && uv run pytest tests/`.
- Frontend build: `npm --prefix web run build`.
- Frontend tests: `npm --prefix web test -- PushSettings`.
- Graph Check done: nodes `send_push()` (`app/services/push.py:14`), `PushSubscription`
  (`app/models.py:870`), `PushUnavailable` (`app/services/push.py:10`), `session_scope()`
  (`app/db.py:27`), `test_h4_notifications.py` community; frontend `PushSettings.tsx` ↔
  `api.ts` `savePushSubscription`.
- RDD: `review assess` per work-unit commit; run the returned transition verbatim when `review_due`.

## Env / setup

- Worktree `../lumat-agent-odd-notificaciones-push-pwa-followups`, branch
  `odd/notificaciones-push-pwa-followups`, base `main` = `576b07ef`.
- `uv sync`; `cp <primary>/infra/.env infra/.env`; `infra/test-db.sh up`; tests need
  `eval "$(infra/test-db.sh env)"` first. Frontend: `npm ci` in `web/`.
- strict_tdd: true; backend runner `uv run pytest tests/`.

## Progress log

- Worktree created from `main` = `576b07ef`. Baseline
  `uv run pytest tests/integration/test_h4_notifications.py` → 15 passed.
- WU1 — `15e35141` `fix(push): deactivate subscription on terminal push-service failure`.
  New `test_send_push_deactivates_subscription_on_gone_response` observed RED (row stayed
  `active=True`), then GREEN. Targeted `tests/integration/test_h4_notifications.py` → 16 passed
  (parent spot check re-ran → 16 passed). Full backend `uv run pytest tests/` → 1894 passed.
  Note: `session_scope()` rolls back on exception, so the handler does an explicit
  `session.commit()` before re-raising.
- RDD assess (`--base-ref 576b07ef --committed-only`) after WU1 → `medium` /
  `under_budget`, `review_due: false`; boundary stays pending until WU2.
- WU2 — `588ea784` `fix(web): reuse existing push subscription and recover after failed save`.
  New "reuses and saves an existing browser subscription" + "reuses the browser subscription
  when retrying after a failed save" observed RED (2 failed / 4 passed), then GREEN
  (`npm test -- PushSettings` → 6 passed). Updated the existing "subscribes and saves" test
  mock to provide `getSubscription`. Decision detail: `setPermission("granted")` moved to
  after a successful save so the activation button stays visible for an in-place retry; JSX
  untouched.
- Verification (parent spot check): backend `eval "$(infra/test-db.sh env)" && uv run pytest tests/`
  → **1894 passed, 2 warnings** (pre-existing); frontend `npm run build` (`tsc -b && vite build`)
  → success (pre-existing chunk-size warning); `npm test -- PushSettings` → 6 passed.
