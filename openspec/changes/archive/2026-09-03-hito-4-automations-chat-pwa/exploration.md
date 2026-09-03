# Exploration: Hito 4 Automations, Chat, and PWA

status: success

## Executive Summary

H1-H3 foundations are present: FastAPI/SQLAlchemy/PostgreSQL, a LangGraph
conversation flow with the H2 orchestrator and one runtime research subgraph,
durable appointments/calendar metadata, versioned notification templates, and
idempotent notification operations. The current operational processing model is
still request/startup driven: webhook recovery claims inbound rows and the
notification sweep runs from application lifespan and webhook background work.
There is no general event bus, automation registry, standalone worker, PWA
manifest/service worker, browser push subscription model, or production internal
owner/admin-to-agent chat.

The panel is a React 19 + Vite SPA with state-based navigation (no router), a
thin same-origin API client, and Storybook-driven visual references. `Dashboard`
currently exposes only four SQL aggregate KPI families. `ChatWithAgent` exists
only as a Storybook mock; `InboxThread` is also a Storybook reference while the
production conversation thread is the H2 messaging surface. Notifications have
authenticated backend listing/retry endpoints but no corresponding panel page.

## Current Architecture Map

### Graph Check consulted

- `graphify-out/GRAPH_REPORT.md`: 3,052 nodes, 6,389 edges, 233 communities;
  god nodes include `Message` (74 edges), `Conversation` (58), `Case` (40),
  `ConversationState` (39), `make_user()` (98), and `_post()` (44).
- Relevant communities/hubs: `ingest.py`, `services/kb.py`, `models.py`,
  `panel/deps.py`, `api/routes/auth.py`, `Conversation Manager
  Specification`, `Admin Panel`, `Dashboard.stories.tsx`,
  `ChatWithAgent.stories.tsx`, and `research_triage.py`.
- Queries consulted: backend architecture query; web panel/Storybook/PWA query.
  The directed path `app` → `web` returned no path, so no cross-module edge is
  inferred. The graph was built at commit `f09fba0b` and is stale relative to
  the current working tree; use it as structural context only.

### Key files and roles

- `app/main.py` — FastAPI factory; startup resets/reprocesses inbound rows and
  invokes the notification sweep.
- `app/webhook/ingest.py` — persist/claim/process inbound messages, Meta media
  retry, LangGraph invocation, outbound delivery, and emergency reminder hook.
- `app/chat/graph.py` — LangGraph state machine with deterministic emergency,
  cost, and handoff gates around the H2 orchestrator and research subgraph.
- `app/agent_registry.py`, `agent/registry.yaml` — validated five-agent
  declarative roster; only `research_triage` has runtime subgraph wiring.
- `app/services/scheduling.py` — local timezone-aware appointments, availability,
  conflict checks, lifecycle, and audit/history.
- `app/services/notifications.py` — durable idempotent channel operations,
  attempts, retries, advisory-locked bounded sweep.
- `app/services/notify.py` — emergency WhatsApp-template/email fallback,
  acknowledgement, and reminder escalation; safety-sensitive contract.
- `app/ops/sweep.py` — seven-line wrapper around `sweep_due_operations`; not a
  general worker or scheduler.
- `app/models.py`, `db/migrations/001..013` — customers, conversations,
  messages, cases/events/audit, appointments/calendar sync, templates, and
  notification operations/attempts. No automation/event-delivery or push tables.
- `app/panel/api/__init__.py` and `app/panel/api/routes/*.py` — authenticated
  JSON API, including appointments, templates, notifications, dashboard, and
  H2 conversation commands.
- `web/src/app.tsx`, `web/src/main.tsx` — auth gate and SPA bootstrap; no PWA
  registration.
- `web/src/components/domain/AppShell.tsx` — state-based view switcher, no URL
  router.
- `web/src/api.ts`, `web/src/types.ts` — thin fetch layer and typed contracts.
- `web/src/components/pages/Dashboard.tsx` — basic KPI page.
- `web/src/stories/pages/ChatWithAgent.stories.tsx` — mock internal agent chat;
  explicitly says production wiring is untouched.
- `web/src/stories/pages/InboxThread.stories.tsx` — H2 human inbox visual mock;
  not the internal agent chat.
- `web/package.json`, `web/index.html` — React/Vite/Vitest/Storybook setup;
  no PWA plugin, manifest, or service worker.

## H4 Gap Analysis

| Capability | Exists today | Missing | Natural build blocks |
|---|---|---|---|
| Automations / event bus | `ConversationEvent` records conversation transitions; webhook and services execute synchronously; durable notification operations are downstream work records. | No domain event contract, event publication/consumption, automation definitions, trigger conditions, deduplication, or event-to-operation linkage. | Define a small persisted event/outbox contract; publishers around message/case/appointment transitions; deterministic automation rules; enqueue existing notification operations rather than bypassing them. |
| Deterministic worker | `sweep_received()` claims inbound rows with `FOR UPDATE SKIP LOCKED`; `sweep_due_operations()` uses an advisory transaction lock; startup and webhook background execution invoke both paths. | No continuously runnable/cron-owned worker, unified bounded job loop, lease/heartbeat, metrics, or explicit deployment entrypoint. | Extract bounded jobs behind `app/ops`; preserve claim/lock semantics; add deterministic clock/limit processing and a single worker command/trigger; keep emergency guarantees isolated and tested. |
| PWA installability + push | Responsive SPA foundation, same-origin cookie auth, Vite build, and tokenized UI exist. | No `manifest`, service worker, registration, offline shell/cache strategy, push subscription persistence, VAPID/provider delivery, permission UX, or push retry/audit policy. | Add minimal manifest and service worker; define authenticated subscription API/storage; choose push provider/browser support policy; connect selected notification events to push operations without treating push as a replacement for WhatsApp/SMTP. |
| Chat-with-agent | Storybook mock has admin/agent bubbles, idle/processing states, suggestions, composer, and tests; LangGraph backend can answer customer conversations. | No internal chat entity/thread, owner/admin authorization boundary, API, persistence, streaming/polling protocol, agent context policy, or production AppShell view. | Define internal thread/message model and role policy; reuse LangGraph/service boundary with an explicit internal context; add authenticated commands and typed SPA page; decide synchronous response vs polling/streaming. |
| Advanced dashboards | `compute_kpis()` provides contacts, grouped cases, derived cases, and visit requests over configurable windows; SPA and Jinja views exist. | No trends/time series, operational funnel, appointment/calendar metrics, notification health, automation outcomes, filters/drill-down, or export contract beyond existing CSV export. | Extend aggregate service/API with bounded, indexed queries; define metric semantics and time windows; add small native visualizations or tables before introducing a chart dependency. |
| Notifications polish | Versioned templates, WhatsApp/SMTP adapters, idempotency, attempt history, retryable/permanent failure, audit, emergency ack/reminders, and authenticated operation list/retry API exist. | No web notification center/page, read/unread UX, push channel, event-driven fan-out, richer statuses/filters, or unified user-facing delivery preferences. | Treat existing operations as the durable core; add notification read model/preferences only if needed; expose a panel page and push adapter; preserve emergency fallback and audit semantics. |

## Persistence Findings

Migrations stop at `013_h3_notifications.sql`. H3 already supplies the durable
building blocks most likely to be reused: `appointments`,
`appointment_calendar_sync`, `notification_template_versions`,
`notification_operations`, and `notification_attempts`. `ConversationEvent` is
an append-only conversation event log, not a general queue/outbox. There are no
automation definitions/runs, worker leases/jobs, push subscriptions, internal
agent threads, or notification read-state tables.

## Recommended Change Boundaries

Keep `hito-4-automations-chat-pwa` as **one SDD milestone change with multiple
capability specs**, matching the repository convention used by H1 and H3, but
deliver it as chained reviewable slices. The areas share real seams: event
publication should feed the existing notification operation model and the
worker; notification health feeds advanced dashboards and polish; the PWA push
channel is another notification adapter; the internal chat shares auth,
messages, LangGraph execution, and AppShell/API patterns. Splitting into
unrelated changes would duplicate contracts and make event/worker/notification
ordering ambiguous.

Recommended capability slices/specs are: (1) event/outbox and deterministic
worker foundation, (2) automation rules over existing domain events, (3)
notification center/push integration, (4) internal agent chat, (5) dashboard
expansion, and (6) PWA shell/installability. Order the work so the worker and
notification contracts land before automation and push consumers; keep chat
and dashboard slices independently reviewable under the 400-line budget.

Do not create a new general messaging provider, LangGraph checkpointer, chart
framework, or broad workflow engine without a product/scale requirement. The
existing code explicitly chose bounded sweeps for tens of conversations/day;
H4 should replace that trigger deliberately, not grow two competing workers.

## Risks / Unknowns

- Product must define which events and automations are allowed, whether rules
  are owner-configurable, execution ordering, cooldowns, and whether retries
  may produce customer-visible duplicate messages.
- Product must define dashboard metrics, comparison windows, timezone, retention,
  and who can see notification/automation health.
- Internal chat needs a decision on one-to-one vs multi-user threads, admin vs
  operador access, agent memory scope, transcript retention, and synchronous
  response versus streaming/polling.
- WhatsApp business-initiated messages remain constrained by approved templates
  and customer-service windows; automation must route through the existing
  policy-aware template/delivery path.
- Browser push support, permission prompts, iOS/Safari behavior, installed-mode
  differences, VAPID/provider operations, and HTTPS requirements need explicit
  support and fallback decisions. PWA installability does not guarantee push on
  every mobile browser.
- External delivery remains non-transactional. Outbox/event deduplication must
  not weaken the existing notification idempotency, emergency safety reply, or
  audit guarantees.
- The graph is stale and the working tree has unrelated dirty web changes;
  proposal/apply must re-run graph checks and isolate H4 artifacts and commits.

## Next Recommended

propose — write the H4 proposal with the capability-spec breakdown above,
explicit event/worker ownership, product decisions, and chained delivery
boundaries before design.

## Skills Resolution

- `/home/stefan/.config/opencode/skills/graphify/SKILL.md`
- `/home/stefan/.config/opencode/skills/sdd-explore/SKILL.md`
