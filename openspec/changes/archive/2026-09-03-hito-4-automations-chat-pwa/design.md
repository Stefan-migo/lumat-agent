# Design: H4 Automations, Chat, and PWA

## Technical Approach

Extend PostgreSQL, SQLAlchemy, FastAPI JSON-API, signed sessions, notifications, webhook, and LangGraph. Transitions publish transactional outbox rows; a bounded worker evaluates rules and advances operations. The panel adds notification, chat, and aggregate models. React/Vite stays router-free; PWA is a versioned shell. Graph consulted: `AppShell`, `ChatWithAgent.stories.tsx`, `panel/api/deps.py`, `app/chat/graph.py`, `sweep_received()`, `send_emergency_notification()`, `NotificationOperation`, `Message`, `Conversation`, `Case`.

## Architecture Decisions

| Decision | Choice | Alternative / rationale |
|---|---|---|
| Event transport | PostgreSQL `domain_events` outbox with stable `dedupe_key` | No broker: one API/database; transactional durability matters more than throughput. |
| Worker mode | `python -m app.ops.worker`, bounded cycle by default; optional bounded loop | One-shot is cron/container friendly; every loop cycle remains capped. Existing sweeps remain compatibility paths. |
| Rule model | JSON conditions plus allow-listed event/channel/template values | No user-authored code or workflow engine; deterministic evaluation is auditable and safe. |
| Chat transport | Persist-then-poll (`POST`, then `GET`) | Streaming adds infrastructure and failure modes; processing state and retryable messages provide recovery. |
| Dashboards | SQL aggregates over indexed tables/events | No chart framework or warehouse; bounded queries meet current scale. |
| Push | Web Push adapter behind `NotificationChannel`; VAPID credentials are deployment secrets | Push is optional and never replaces WhatsApp/SMTP fallback; unsupported browsers remain fully usable. |

## Data Flow

```text
transition ─→ domain_events ─→ worker lease ─→ rule evaluation ─→ notification_operations
                                               └──────────────→ panel_notifications ─→ push/fallback
panel user ─→ internal_chat_messages ─→ LangGraph boundary ─→ persisted response
```

## Data Model / Migration

Create `db/migrations/014_h4_automations_chat_pwa.sql`. Add indexed nullable `event_id` and `user_id` FKs to `notification_operations`. Create: `domain_events(id, event_type, entity_type, entity_id, payload JSONB, occurred_at, status, attempts, available_at, leased_until, lease_owner, processed_at, error, dedupe_key UNIQUE)`; `automation_rules(id, name, event_type, conditions JSONB, channel, template_event, cooldown_seconds, enabled, created_by, timestamps)`; `automation_executions(id, rule_id, event_id, execution_key UNIQUE, outcome, reason, operation_id FK, created_at)`; `panel_notifications(id, user_id FK, operation_id FK, title, content, source, status, read_at, created_at)`; `push_subscriptions(id, user_id FK, endpoint UNIQUE, p256dh, auth, user_agent, active, created_at, updated_at)`; `internal_chat_threads(id, user_id FK, status, created_at, updated_at)`; and `internal_chat_messages(id, thread_id FK, author, content, status, error, created_at, completed_at)`. Channel is exposed by joining `panel_notifications.operation_id` to `notification_operations.channel`. FKs, indexes, grants, and ORM mappings follow 012–013.

## Backend and Contracts

Add `app/services/{events,automation,push,agent_chat,dashboard}.py` (`publish_event`, `evaluate_event`, `send_push`, `submit_message`, `operational_summary`) and `app/ops/worker.py` (`run_cycle(limit=50, owner="...")`, `health_counts()`, `main()`). A handler transaction reuses execution/operation by stable key and marks the event complete in one commit; failures retain retry eligibility and exhaust at the limit. Reclaimed leases cannot repeat success. Extend `notifications.py`; preserve `notify.py` fallback.

Add JSON routers: `GET /panel/api/notifications`, `POST /panel/api/notifications/{id}/read`, `POST/DELETE /panel/api/push-subscription`; owner/admin-only chat routes; and authenticated dashboard summary/trend/drilldown routes. Existing roles have no owner value, so H4 maps “owner” to `admin`; `operador` is denied via `require_admin_json`. Thread creation and sends call `record_audit` (`internal_chat.thread_created`, `internal_chat.message_sent`) in the same transaction. Register routers in `app/panel/api/__init__.py`. Reuse `app/chat/graph.py` with constrained `ConversationState`; no new tools.

`dashboard.py` validates start/end and timezone, rejects invalid or over-bounded periods before SQL, returns contacts/cases/appointments/notification-health/automation outcomes plus period metadata, fills time buckets with zeros, and applies the same metric/time filter to drill-down rows.

Publish seams: `app/webhook/ingest.py` persists inbound `Message`; `app/services/cases.py` creates/updates cases; `app/services/scheduling.py` books/cancels appointments. Each publishes after mutation but before caller commit; rollback emits nothing.

## File Changes

Create migration, `app/services/events.py`, `automation.py`, `push.py`, `agent_chat.py`, `dashboard.py`, `app/ops/worker.py`, API/page/PWA files. Modify `app/models.py`, `notifications.py`, publishers, router registry, `AppShell`, `Dashboard`, `main.tsx`, `index.html`, and fixtures.

## Web, Testing, and Threat Matrix

Add `NotificationCenter.tsx`, `AgentChat.tsx`, `AdvancedDashboard.tsx`, `PushSettings.tsx`, API helpers, and tests. Extend `PanelShell`/`AppShell` and `Dashboard`; wire ChatWithAgent. Add manifest, versioned `sw.js`, icons, explicit registration. Cache hashed assets only; never `/panel/api` or session HTML. Use native Web APIs.

Strict TDD adds backend tests for publication, dedupe, lease/retry/exhaustion, rules, push audit, role isolation, chat recovery, bounded aggregates, and migration. Vitest covers states, navigation, permission fallback, and API non-cache behavior.

| Boundary | Applicability / safe and failure behavior | RED test |
|---|---|---|
| Documentation-like paths | N/A: no executable-file classification | None |
| Git repository selection | N/A: no Git automation | None |
| Commit state | N/A: no commit automation | None |
| Push state | N/A: no VCS push automation; browser push failures fall back | Push adapter failure preserves fallback |
| PR commands | N/A: no PR automation | None |

## Slice Sequencing and Rollback

1. Worker: migration, event model/service, `app/ops/worker.py`, RED lease/health tests.
2. Rules: rule/execution tables, publishers at webhook/case/appointment seams, evaluator tests.
3. Notification center/push: operation columns, read model, APIs, adapter and UI.
4. Chat: thread/message tables, service/API, constrained graph call, page/tests.
5. Dashboards: aggregate service/API, page and drill-down tests.
6. PWA: manifest, service worker, registration, cache/permission tests.

Disable rules/push, stop the worker, and retain startup sweeps before rollback. Migrations are additive; preserve events/attempts and remove tables only through an approved destructive migration. No blocking questions.

## Open Questions

None blocking; VAPID credentials and labels are deployment inputs.
