# ODD — notificaciones-push-pwa

## Objective

Deliver real Web Push notifications on top of the merged in-app panel notifications v1 (PR #552,
merge `d796e556`): a real `send_push` adapter, a producer that enqueues push operations, the
browser subscription flow, and the service-worker push handlers.

## Problem

The v1 ships the in-app bell end-to-end, but browser push was left as a stub:

- `app/services/push.py:9-11` — `send_push(recipient, content)` raises `PushUnavailable`; no
  `pywebpush` dependency and no VAPID settings exist.
- `app/services/notifications.py:312-333` — `process_operation` already delivers `channel="push"`
  with retry/backoff and `_process_push_fallback` (WhatsApp/email), and this path is already
  tested (`tests/integration/test_h4_notifications.py`). **It must not be rebuilt.**
- `app/services/notifications.py:158-193` — `notify_admins` only creates the panel carrier and
  fans out `PanelNotification`; no producer ever emits `channel="push"` (grep: zero producers).
- `web/public/sw.js` — no `push` / `notificationclick` listeners.
- `web/src/components/pages/PushSettings.tsx` — only calls `Notification.requestPermission()`;
  it never runs `pushManager.subscribe()` nor POSTs the subscription the API already accepts.

Result: even when a browser user grants permission, no push is ever produced or delivered.

## Why

The owner wants the deferred push/PWA follow-up closed. The delivery machinery (sweep) already
exists and is tested; only the endpoints of the pipe are missing.

## Scope (authorized by the owner)

**In:**

- `app/services/push.py`: real `send_push` using `pywebpush`, resolving the subscription by
  `recipient` and signing with VAPID; raise `PushUnavailable` when unconfigured.
- `pyproject.toml`: add `pywebpush`.
- `app/config.py`: optional VAPID settings (`vapid_public_key`, `vapid_private_key`,
  `vapid_subject`); absent → `PushUnavailable`, never a boot failure.
- `app/services/notifications.py`: extend `notify_admins` to also enqueue one `channel="push"`
  operation per active `PushSubscription` of each admin, reusing the namespaced dedupe key.
- `app/panel/api/routes/notifications.py`: `GET /panel/api/push-config` returning the public key.
- `web/src/components/pages/PushSettings.tsx` and `web/src/api.ts`: register SW, fetch the public
  key, `pushManager.subscribe(...)`, POST/DELETE the subscription.
- `web/public/sw.js`: `push` (showNotification) and `notificationclick` (focus/open) handlers.
- Tests with the `deliver`/monkeypatch seam; this unit record.

**Out:** DB migrations (no new column; `recipient` carries the subscription id), per-channel /
priority preferences (D3 deferred), richer mobile UX, changes to the in-app realtime path.

## Decisions

- **D1 — Delivery via sweep.** Producer enqueues `channel="push"` operations as `pending`; the
  existing `sweep_due_operations` delivers with retry/backoff/fallback/audit. No immediate send.
- **D2 — One push operation per subscription.** `recipient` = subscription id (`String(255)` cannot
  hold an endpoint); `send_push` loads the `PushSubscription`. Fan-out lives in the producer, not
  in `send_push`.
- **D3 — Channel/priority preferences deferred.** v1 pushes exactly the panel event set.
- **D4 — Extend `notify_admins`** (no `channels=[...]` param) to enqueue the push operations.

Cross-cutting: optional VAPID config; `pywebpush` dependency; `GET /panel/api/push-config`; SW
handlers; `pushManager.subscribe` flow.

Source: `.rapsodia-code/sessions/ready-for-odd/2026-10-10-notificaciones-push-pwa/report.md`.

## Constraints

- No DB migration. The push operation's `recipient` is the subscription id, not the endpoint.
- Missing VAPID must degrade gracefully (raise `PushUnavailable`); it must never break boot.
- Do not hand-roll VAPID JWT or ECE encryption — use `pywebpush`.
- Panel push operations carry no `event_id`, so `_fallback_channel` returns `None`: WhatsApp/email
  fallback is intentionally inert for panel pushes (declared debt).
- Real push is not testable in CI (browser + VAPID + HTTPS): automated tests use the seam;
  delivery is verified manually (and iOS requires the PWA to be installed to the home screen).
- Operator-facing UI copy stays Spanish. Code, comments, task documentation, and commit messages
  are English.
- Do not push, open a PR, or merge; those are the owner's decisions.
- Commit as reviewable work units; keep tests with the code they cover.

## Graph check

Consulted `graphify-out/GRAPH_REPORT.md` and ran
`graphify query "panel notification operations push delivery admin fan-out sweep fallback"`.
Nodes consulted: `services/notifications.py::process_operation`, `create_operation`, `sweep.py`,
`PushSettings.tsx`, `NotificationCenter.tsx`, `api.ts`, `AppShell.tsx`, and the H4 integration
test nodes. Graph refresh runs once at session close.

## Tasks

| ID | Task | Route |
|----|------|-------|
| T1 | Real `send_push` (pywebpush) + `pywebpush` dep + optional VAPID settings. | delegated writer |
| T2 | Extend `notify_admins` to enqueue one push operation per active admin subscription. | delegated writer |
| T3 | `GET /panel/api/push-config` returning the VAPID public key. | delegated writer |
| T4 | Frontend: register SW, fetch public key, `pushManager.subscribe`, POST/DELETE subscription. | delegated writer |
| T5 | `web/public/sw.js`: `push` + `notificationclick` handlers. | delegated writer |
| T6 | Tests via the `deliver` seam + full backend/frontend checks. | delegated writer |

## Delivery

Single PR against `main`. Forecast ~250-350 authored changed lines (under ~400). No chained slices.

## Checks

- Backend focused: `uv run pytest tests/integration/test_h4_notifications.py -q` and any new tests.
- Backend suite: `uv run pytest -q`.
- Frontend tests: `npm --prefix web run test`.
- Frontend typecheck + build: `npm --prefix web run build` (`tsc -b` lives only inside `build`).
- TDD mode: not configured for this project — run ordinary functional checks.
- Manual: real push delivery with VAPID + HTTPS + installed PWA (owner or manual step).

## Progress / Evidence

- [x] T1 send_push real + dep + VAPID config — commit pending; evidence: adapter tests and `uv sync`.
- [ ] T2 notify_admins push producer
- [ ] T3 GET /panel/api/push-config
- [ ] T4 frontend subscribe flow
- [ ] T5 SW push/notificationclick handlers
- [ ] T6 tests + verification

Graph check for backend implementation: consulted `send_push()`, `PushUnavailable`,
`get_settings()`, `PushSubscription`, `notify_admins()`, `create_operation()`,
`NotificationOperation`, `require_user_json()`, and `routes/notifications.py`. Edges:
`notify_admins() --calls--> create_operation()` and
`send_push() <-contains- push.py --imports_from--> services/notifications.py
--imports_from--> db.py --imports--> get_settings()`.

## Next step

Implement T1-T6 in worktree `../lumat-agent-odd-notificaciones-push-pwa` on `odd/notificaciones-push-pwa`.
