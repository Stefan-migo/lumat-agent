# Proposal: H4 — Automations, Chat, and PWA

## Intent

Deliver the final milestone by turning H1–H3’s foundations into an automation platform with an owner/admin workspace. H4 closes the contracted scope and reduces manual follow-up.

## Scope

### In Scope
- Durable events/outbox and a bounded deterministic worker.
- Deterministic automation rules enqueueing policy-aware notifications.
- Notification center, read state, and browser push with WhatsApp/SMTP fallback.
- Owner/admin ↔ agent chat with internal context.
- Operational dashboards with trends and drill-downs.
- Installable React/Vite PWA shell and service worker.

### Out of Scope
- M2 website expansion; M3 payments, catalog, or agenda.
- Rebuilding the H2 WhatsApp human inbox/reply channel (`operator-messaging`).
- External broker, workflow engine, chart framework, new provider, or staging VPS without proven need.
- Offline-first editing, universal push guarantees, or owner-authored code.

## Capabilities

### New Capabilities
- `event-outbox`: durable events, deduplication, and operation linkage.
- `deterministic-worker`: bounded processing and entrypoint.
- `automation-rules`: safe triggers, conditions, cooldowns, and audit.
- `notification-center`: read model, filters, and push.
- `internal-agent-chat`: role-bound threads, persistence, and panel view.
- `advanced-dashboards`: aggregates, trends, and drill-downs.
- `pwa-shell`: manifest, service worker, installability, and cache policy.

### Modified Capabilities
- `notifications`: add event fan-out, push delivery, read state, and preserve retry/audit guarantees.

## Approach

Build on notification services, webhook claims, H2 auth/LangGraph, and React/Vite `AppShell`. Use deterministic rules before LLM decisions, idempotency, leases, bounds, audit logs, and no heavy infrastructure. Graph nodes validated: `lifespan()`, `sweep_received()`, `process_message()`, `send_emergency_notification()`, `Message`, `Conversation`, `Case`, `panel/deps.py`, `AppShell`, `ChatWithAgent`. The directed ops-to-services path was unavailable; preserve existing seams.

Delivery remains one change, `hito-4-automations-chat-pwa`, with six stacked slices: worker; rules; notification center/push; chat; dashboards; PWA. Each slice must be testable, reviewable, and rollbackable under auto-chain.

## Decisions to Confirm in Design

| Area | Confirm |
|---|---|
| Events/worker | Schema, lease, limits, ownership |
| Automations | Triggers, cooldowns, retries, duplicates |
| Product surfaces | Push support/provider, chat roles/context, dashboard metrics/visibility |

## Affected Areas

- `app/`, `db/migrations/`, `tests/`: backend capabilities and coverage.
- `web/src/`, `web/public/`: panel and PWA.
- `infra/`, `docs/`: worker operations.

## Risks

- Unsafe notifications: enforce idempotency, cooldowns, and audit.
- Worker stalls: use leases, bounds, and health visibility.
- Push incompatibility: publish a support matrix and fallback.
- Review overload: six slices, each ≤400 lines.

## Rollback Plan

Disable automation/push, stop the worker, and retain existing sweeps temporarily. Revert code/migrations by slice; preserve events and attempts for audit.

## Dependencies

- Product decisions, HTTPS/push credentials, H1–H3 migrations, and panel auth.

## Success Criteria

- [ ] Processing is idempotent and preserves emergency guarantees.
- [ ] All planned capabilities pass strict backend/web tests.
- [ ] Slices are independently reviewable and rollbackable.
