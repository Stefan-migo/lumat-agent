# notificaciones-panel — notification surface, read state and push coverage

Feature branch `odd/notificaciones-panel` (worktree `../lumat-agent-odd-notificaciones-panel`), based on
`25c6f45a`. Authority: `web/DESIGN_SYSTEM.md`, `web/src/tokens/tokens.css`, and the code map recorded in
Engram (`notifications/overview`).

## Specs

**S1 — The mobile notification surface has no styling and must get a designed one.**
"en la version mobile no hay estilo para nada." / "el estilo en la version mobile de la notificaciones es
basico hay que mejorarlo."
Cause established by reading the code: below 64rem the desktop header (which owns the styled popover) is
`display: none`, and the mobile bell navigates to `web/src/components/pages/NotificationCenter.tsx`, which
renders bare `<label>/<ul>/<li>/<strong>/<p>/<small>/<button>` with zero classes and no stylesheet.
Required: the page follows the panel grammar (list rows with title, content, source/status meta and time;
unread indicated by more than colour), covers loading / empty / filtered-empty / error / permission
states, keeps 44px touch targets, and gets a `Notificaciones` entry in the `DESIGN_SYSTEM.md` page
architecture in the same change.

**S2 — Marking one notification read must update immediately.**
"el boton para marcarlas como leidas no funcion en el momento. no se actualiza."
Cause: `NotificationCenter` fires `void markNotificationRead(row.id)` and discards the response; the list
comes from `useAsyncData(fetcher, true, unread ? 1 : 0)`, so nothing refetches and the row keeps its
button. The shell unread badge is a separate state that only refreshes on mount, on a realtime
`notification` envelope or on mark-all.
Required: marking one row updates the row and the shell badge without a page reload; a failed POST puts
the row back and says so; "marcar todas" keeps working.

**S3 — Push must cover every type that notifies admins today (owner decision `1. b`).**
"he activado las notificaciones push en mi celular, hay algunas notificaciones que llegan. pero no
todas." — decision: extend push coverage, do not open subscriptions to non-admins.
Code map: `notify_admins()` (`app/services/notifications.py:182`) is the only panel-notification producer
and already enqueues one push per active admin subscription. Its only callers are four appointment events
(`scheduling.py`) and emergencies (`emergency.py:117`). The one admin notification that never reaches the
panel or push is the **cost alert** (`app/services/costs.py:294` → email only).
Required: cost alerts reach admins in the panel and by push, in addition to email; a notification
operation that ends `permanently_failed` becomes visible to admins instead of dying silently behind the
WhatsApp/email fallback. Out of scope: pushing customer-facing reminder/follow-up WhatsApp messages to
admins, and enabling non-admin subscriptions.

## Tasks

| ID | Spec | Route | Commit |
|---|---|---|---|
| T1 | S1 | delegated writer + parent review — styled page + design-system entry | `4281aa26`, `fba46ff5` |
| T2 | S2 | delegated writer + parent fix — optimistic read state + derived badge | `c316e770` |
| T3 | S3 | delegated writer + parent verification — cost alerts and failure visibility | `1095da04` |

## Log

**L1 (owner, original request, verbatim)**

> ok perfecto. quiero que nos movamos ahora. a trabajar en la notificaciones. necesito que revises con funcina el sistema de notificaciones actualemente.
>
> en la version mobile no hay estilo para nada.
> he activado las notificaciones push en mi celular, hay algunas notificaciones que llegan. pero no todas.
>
> el estilo en la version mobile de la notificaciones es basico hay que mejorarlo. y el boton para marcarlas como leidas no funcion en el momento. no se actualiza.
>
> puedes darme un overview de todo esto?

**L2 (owner decisions, verbatim)**

> 1. b
> 2. si autorizo#

`1. b` = S3 scope: extend push to every type that notifies today. `2.` = read-only VPS access authorized.

**L3 (blocker, prod access)**

The read-only VPS check could not run: `138.128.243.241:22` is filtered from this network and the
Tailscale host `t95-servidor` refuses `deploy`/`agent`/`stefan` public key auth (this machine's
`id_ed25519` and `t95_agent`). Public `https://agente.lumat.cl/health` answers 200, so production is up.
Pending: whether the `*/5` sweep cron is installed, and the `notification_operations` state in prod.
Nothing in T1–T3 depends on it; it only decides whether the outbox needs arming after deploy.

**L4 (evidence, T1–T3 done)**

Both writers returned `partial`: neither could run its gate (the worktree had no `web/node_modules` and
no `.venv`), so every check below was run by the parent.

- Backend: `bash scripts/test.sh quick` green; the db-backed regression sweep
  (`tests/integration/test_notifications.py`, `test_emergency_notify.py`, `test_cost_guardrails.py`,
  `test_send_costs.py`, `tests/functional/test_api_notification_operations.py`) green; the three new
  focused tests green. RED proved by stashing the two service files: the cost fan-out and the failure
  notice both failed before the implementation and passed after.
- Frontend: `npm run build` OK; `npx vitest run` 1408 tests / 121 files green.
- Browser check on an isolated stack (api `:8003`, seeded dev data, four panel notifications covering
  all four sources): mobile 390px and desktop 1280px render the designed surface; one click moved
  unread rows 3 → 2, the badge 3 → 2, and the specific row to `Leída`.
- Defect the browser check caught and the unit test did not: the shell badge decremented twice for one
  click (3 → 1), because the optimistic and reconciled callbacks both ran against the same render.
  Fixed by deriving the count from the list instead of incrementing a counter (`c316e770`).
- Slice boundary: 483 authored lines in four commits. Everything below belongs to the next batch and
  needs its own review slice.
