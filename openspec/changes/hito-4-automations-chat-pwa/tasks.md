# Tasks: H4 Automations, Chat, and PWA

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

## Suggested Work Units

| Unit | Goal | PR | Focused test | Runtime harness | Rollback |
|---|---|---|---|---|---|
| 1 | Outbox/worker | 1 | `pytest tests/ -k 'event or worker'` | `python -m app.ops.worker --once` | migration/events/worker |
| 2 | Rules/fan-out | 2 | `pytest tests/ -k automation` | webhook/case/booking transition | rules/publishers |
| 3 | Center/push | 3 | `pytest tests/ -k notification && cd web && npm test` | center + fallback | notification/push/UI |
| 4 | Internal chat | 4 | `pytest tests/ -k chat && cd web && npm test` | admin thread send/retry | chat slice |
| 5 | Dashboards | 5 | `pytest tests/ -k dashboard && cd web && npm test` | bounded dashboard query | dashboard slice |
| 6 | PWA shell | 6 | `cd web && npm test` | HTTPS install/update | manifest/SW/registration |

## Phase 1: Slice 1 — Outbox and Worker (PR 1)

- [x] 1.1 **RED:** `tests/integration/test_h4_worker.py` covers EO-1/2 and DW-1/2/3: commit/rollback, dedupe/linkage, batch/lease recovery, retry/exhaustion, health.
- [x] 1.2 **GREEN:** Add `db/migrations/014_h4_automations_chat_pwa.sql`, event ORM in `app/models.py`, `app/services/events.py`, and bounded `app/ops/worker.py`.

## Phase 2: Slice 2 — Rules and Fan-out (PR 2)

- [x] 2.1 **RED:** `tests/integration/test_h4_automations.py` covers AR-1/2/3: match/nonmatch, disabled audit, cooldown, retry reuse, and publisher rollback/no event.
- [x] 2.2 **GREEN:** Extend migration/models; implement `app/services/automation.py`; publish transactionally from `app/webhook/ingest.py`, `app/services/cases.py`, and `app/services/scheduling.py`.

## Phase 3: Slice 3 — Notification Center and Push (PR 3)

- [x] 3.1 **RED:** Backend/web tests cover NC-1/2/3 and NT-1/2/3: auth/filter/read isolation, fan-out, retries/exhaustion, and push failure/unsupported fallback audit.
- [x] 3.2 **GREEN:** Extend models/migration and `app/services/notifications.py`; add `app/services/push.py`, routers, `NotificationCenter.tsx`, `PushSettings.tsx`, API helpers, and `AppShell` wiring.

## Phase 4: Slice 4 — Internal Agent Chat (PR 4)

- [ ] 4.1 **RED:** `tests/integration/test_h4_chat.py` and Vitest cover IAC-1/2/3: admin audit, operador denial, constrained response, privileged-action refusal, and recoverable failure.
- [ ] 4.2 **GREEN:** Add `app/services/agent_chat.py`, chat routers/serializers/ORM, constrained `app/chat/graph.py` boundary, `AgentChat.tsx`, and `PanelShell` navigation.

## Phase 5: Slice 5 — Dashboards (PR 5)

- [ ] 5.1 **RED:** `tests/functional/test_h4_dashboard.py` and Vitest cover AD-1/2: timezone metrics, invalid bounded period, zero buckets, matching drill-down.
- [ ] 5.2 **GREEN:** Implement `app/services/dashboard.py`, summary/trend/drill-down routers/serializers, and `AdvancedDashboard.tsx` integrated with `Dashboard.tsx`.

## Phase 6: Slice 6 — PWA Shell (PR 6)

- [ ] 6.1 **RED:** Vitest covers PWA-1/2/3: manifest/icons, insecure fallback, API non-cache, version replacement, explicit permission denial/unsupported state.
- [ ] 6.2 **GREEN:** Add `web/public/manifest.webmanifest`, `web/public/sw.js` and icons; update `web/src/main.tsx`, `index.html`, and cache/registration helpers.

## Review Workload Forecast

| Slice | Estimated changed lines |
|---|---:|
| 1 | 220–300 |
| 2 | 180–260 |
| 3 | 300–400 |
| 4 | 220–320 |
| 5 | 180–260 |
| 6 | 100–180 |

Chained PRs recommended: Yes — scope crosses the 400-line budget and database, worker, API, and web boundaries. Stack PRs to `main` in order 1 → 2 → 3 → 4 → 5 → 6; each slice rolls back independently.
