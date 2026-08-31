# Proposal: Complete H2 Production Human Inbox

## Intent

Make H2 production-complete: authenticated operators can own human WhatsApp conversations, perform legal state actions, and send attributable Meta replies. Archived router/UI work is dependency evidence; the current SPA/API is read-only.

## Scope

### In Scope
- Human inbox list/thread, persisted assignment, filters, and legal take/return/close transitions.
- Operator text replies with persistence, Meta delivery, latest-customer-inbound 24-hour enforcement, failure/retry semantics, and request/concurrency idempotency.
- Server authorization/audit, migrations, typed UI/API wiring, and end-to-end/regression proof.

### Out of Scope
- Reimplementing archived AO-1..AO-10 or archived Storybook UI.
- H4 internal chat/PWA, roadmap items, new router/provider, or unrelated uncommitted branding changes.

## Capabilities

### New Capabilities
- `operator-messaging`: authenticated replies, 24-hour policy, delivery state, and outbound idempotency.

### Modified Capabilities
- `admin-panel`: production inbox commands, assignment, filters, and contracts beyond read-only AP-9.
- `human-handoff`: H2 panel response/ownership extension to HH-5; preserve inbound continuity.
- `panel-app`: production inbox controls, composer, permission/error/loading states, and refresh.
- `whatsapp-webhook`: regression contract for human-owned inbound continuity.

## Approach

Use the recommended thin command layer over `set_conversation_state()`, existing auth/serializers, `send_text()`/`deliver_outbound()`, audit, and webhook guard. Add only required schema fields/migrations. Design/spec MUST decide whether ownership is conversation-level or deliberately reuses `Case.responsible_id`, and define the outbound idempotency key/status model across Meta’s non-transactional boundary. The backend calculates the 24-hour window from the latest customer inbound. Deliver in chained slices under the 400-line budget.

Ponytail check: reject a worker subsystem, frontend router, pagination/search platform, and speculative templates/media; keep durable state and commands required for production safety.

Graphify: consulted `ConversationState`, `Message`, `send_text()`, `AuditLog`, `ingest.py`, `types.ts`, `ConversationThread`; confirmed the audit/send edge.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `app/panel/api/routes/conversations.py`, `app/chat/state.py` | Modified | Commands and transitions |
| `app/services/send.py`, `app/services/audit.py`, `app/models.py`, `db/migrations/` | Modified | Durable outbound/audit state |
| `web/src/components/pages/`, `web/src/api.ts`, `web/src/types.ts`, `tests/` | Modified | UI wiring and proof |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Meta side effect races/fails after commit | High | Claim/idempotency/status contract and reconciliation tests |
| Wrong owner or reply-window timestamp | Med | Resolve in design; query latest inbound and test migration |
| Regression or branding contamination | Med | Preserve archived contracts; isolate H2 files/commits |

## Rollback Plan

Disable/revert command routes and UI controls, leaving read-only inbox and inbound webhook behavior. Roll back additive schema only after pending outbound records are recovered; retain messages/audit rows.

## Success Criteria

- [ ] Authorized operators assign, transition, and reply; illegal/unauthorized actions are rejected and audited.
- [ ] 24-hour policy, duplicates/concurrency, Meta failures, retries, and persistence are proven.
- [ ] SPA, migrations, API contracts, and regression suites are green without changing AO-1..AO-10 or branding work.
