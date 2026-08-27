# Tasks: Complete H2 Production Human Inbox

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 650–900 authored lines |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR1 schema → PR2 commands → PR3 delivery → PR4 SPA/E2E |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main; each PR depends on prior unit |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|---|---|---|---|---|---|
| 1 | Schema/domain contracts | PR1 | `pytest tests/integration/test_migrations.py` | H1 PostgreSQL migration | migration/models |
| 2 | Inbox commands/assignment | PR2 | `pytest tests/functional/test_api_conversations.py` | authenticated commands | service/routes |
| 3 | Operator delivery | PR3 | `pytest tests/integration/test_operator_messaging.py` | respx Meta success/failure/retry | outbound service/routes |
| 4 | Production SPA and proof | PR4 | `cd web && npm test -- --run` | browser-like command flow | production UI/API tests |

## Phase 1: Contracts and RED Tests

- [x] 1.1 **RED**, `tests/integration/test_migrations.py`, `tests/functional/test_api_conversations.py`: assert version/owner/outbound fields, filters, shape, and repeatable migration; acceptance: fail only for absent H2 contracts; dependency: archived H1 schema; forecast: 50–80 lines.
- [x] 1.2 **GREEN**, `db/migrations/010_h2_human_inbox.sql`, `app/models.py`, `app/panel/api/serializers.py`: add owner/version, delivery fields, constraints, indexes, serialization; acceptance: repeatable migration and readable legacy rows; dependency: 1.1; forecast: 100–150 lines.

## Phase 2: Inbox Commands

- [x] 2.1 **RED**, `tests/functional/test_api_conversations.py`: cover 401/403, legal/illegal commands, inactive owner, stale version, duplicate/mismatched request IDs, audit; acceptance: denials are JSON, audited, non-mutating; dependency: 1.2; forecast: 100–140 lines.
- [x] 2.2 **GREEN**, `app/services/conversations.py`, `app/chat/state.py`, `app/panel/api/routes/conversations.py`: implement locked commands, roles, assignment, filters/order, version/idempotency; acceptance: AP-9/AP-10/HH-5 pass; dependency: 2.1; forecast: 100–140 lines.

### PR2 Corrective Pass

- [x] Validator correction: audit mismatched request IDs and add focused command, audit, and concurrency contract coverage; no new feature scope.

## Phase 3: Operator Messaging

- [x] 3.1 **RED**, `tests/integration/test_operator_messaging.py`, `tests/integration/test_webhook_ingest.py`: cover rejection/window, commit-before-Meta, payload/no-token logging, duplicate races, 4xx failed, timeout unknown, failed-only retry, human/closed continuity; acceptance: OM/WH scenarios fail first; dependency: 2.2; forecast: 130–180 lines.
- [x] 3.2 **GREEN**, `app/services/send.py`, `app/panel/api/routes/conversations.py`, `app/services/audit.py`: lock claims, persist/audit before Meta, finalize statuses, retry failed only, retain WAMID/error/attempts, enforce latest inbound; acceptance: one durable operation/no duplicate send; dependency: 3.1; forecast: 130–180 lines.

## Phase 4: Production UI and Verification

- [ ] 4.1 **RED**, `web/src/{api.ts,types.ts}`, `web/src/components/pages/{ConversationsList,ConversationThread}.tsx`: test filters, controls, composer, loading, 401/403/409/422, delivery/retry, refresh; acceptance: no optimistic corruption; dependency: 2.2/3.2; forecast: 80–120 lines.
- [ ] 4.2 **GREEN**, same files plus `web/src/components/domain/AppShell.tsx`: wire typed commands/refetch without router/story changes; acceptance: PNL-APP-7/9 and frontend suite pass; dependency: 4.1; forecast: 90–130 lines.
- [ ] 4.3 **REGRESSION**, `tests/functional/`, `tests/integration/`, `web/src/**/*.test.*`: run backend/frontend, migration repeat, authenticated E2E; acceptance: AO-1..10, WH-1..8, HH-1..5, AP-9/10 green; dependency: 4.2; forecast: 40–70 lines.

## Graphify Scope Record

Nodes: `ConversationState`, `Conversation`, `Message`, `conversations.py`, `send.py`, `audit.py`, `ingest.py`, `AppShell`, `ConversationThread`, `types.ts`. Edges: `ConversationState→state.py→Conversation/Message`; `conversations.py→models.py←send.py`; `send_text()→Meta`; `AppShell→ConversationThread→api.ts`. Backend/frontend directed edge absent; verified from source.

## Ponytail Review

`shrink:` keep one command service and existing send primitive; no worker, router, provider, pagination, templates, media, or archived AO/UI changes. No further cut is safe: RED tasks preserve strict TDD and threat coverage.
