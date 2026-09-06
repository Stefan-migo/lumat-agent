## Exploration: Panel automations API and management UI

### Current State
H4 provides the persistence and deterministic execution core, but no management contract. `AutomationRule` has `id`, `name`, `event_type`, JSONB `conditions`, `channel`, `template_event`, `cooldown_seconds`, `enabled`, `created_by`, and timestamps. Database constraints allow cooldowns from 0 to 2,592,000 seconds; the ORM adds an `(event_type, enabled)` index. `AutomationExecution` records rule/event linkage, unique execution key, outcome/reason, and optional `NotificationOperation`.

Rules are not seeded and there is no production creation path: current construction is test-only (`tests/integration/test_h4_automations.py` and `test_h4_notifications.py`). `evaluate_event` selects all rules for the event, then skips disabled, unsupported event/channel/template, non-matching conditions, cooldown, or missing recipient. Matching rules create/reuse a notification operation using idempotency key `automation:{rule_id}:event:{event_id}` and audit evaluation; cooldown is scoped to the same entity type/id. The implementation currently uses event payload content/text, or `template_event` as fallback content; it does not resolve `NotificationTemplateVersion`.

Published event types and sources are:
- `message.received` from webhook message persistence (`app/webhook/ingest.py`)
- `case.created` and `case.updated` from case creation/handoff/update (`app/services/cases.py`)
- `appointment.booked` and `appointment.cancelled` from scheduling (`app/services/scheduling.py`)

The panel JSON API is mounted at `/panel/api/*` through `app/panel/routes/__init__.py` → `app/panel/api/__init__.py` → per-domain routers. Routes use Pydantic request bodies, explicit ORM-to-dict serializers in `serializers.py`, request-scoped `get_db`, and JSON authentication (`401` rather than HTML redirect) via `require_user_json`; admin-only surfaces use `require_admin_json`. There is no automation router or serializer today.

The React panel is a native History API SPA. `PanelView`, `PANEL_ROUTES`, `parsePanelPath`, `AppShell`, and `PanelShell` must be extended for a new top-level view. `AgendaPage` is the closest operational pattern: page-local fetch through `useAsyncData`, typed API helpers, explicit loading/error/denied/empty/stale states, `PageFrame`, shared primitives, and focused component plus Storybook state-matrix tests. NotificationCenter is a smaller read/action example. Settings is unrelated configuration UI; its `scope_rules` are conversation scope policy, not automation rules. No existing Settings or NotificationCenter rule-management UI overlaps this change.

Graph Check consulted fresh graph nodes/edges: `AutomationRule` (`app/models.py`) → `evaluate_event()` (`app/services/automation.py`) → `create_operation()` (`app/services/notifications.py`); `publish_event()` (`app/services/events.py`) with `events.py` callers in webhook ingest, cases, and scheduling; panel `api_router`/`panel_router` and `require_user_json`/`require_admin_json`; React `panelRoutes`, `PanelShell`, `AppShell`, `AgendaPage`, `NotificationCenter`, `api.ts`, and `types.ts`. Graph report: 3919 nodes, 8332 edges, built at `5f32ca50`.

### Affected Areas
- `app/models.py`, `db/migrations/015_h4_automations.sql` — existing rule/execution schema; no migration is pending for CRUD, but future API validation may require schema constraints or a migration if the model changes.
- `app/services/automation.py`, `app/services/notifications.py`, `app/services/templates.py` — rule evaluation, operation linkage, and currently separate immutable template subsystem.
- `app/panel/api/__init__.py`, `app/panel/api/routes/*.py`, `app/panel/api/serializers.py`, `app/panel/api/deps.py` — add authenticated CRUD endpoints, validation, audit, and JSON boundary serialization.
- `web/src/api.ts`, `web/src/types.ts` — typed rule client and response model.
- `web/src/components/domain/panelRoutes.ts`, `PanelShell.tsx`, `AppShell.tsx` — route, navigation, and page mounting.
- `web/src/components/pages/AutomationRulesList.tsx`, optional detail/edit component, and matching tests/stories — management UI following Agenda/NotificationCenter patterns.

### Approaches
1. **Minimal rule CRUD with inline edit/detail** — expose list/create/update/delete or disable, plus a focused list/detail form for the fields already supported by `AutomationRule`; keep evaluation and notification delivery unchanged.
   - Pros: directly closes the roadmap gap; preserves H4 behavior; small API/UI surface.
   - Cons: conditions remain JSON-oriented; template association remains the current event-string behavior.
   - Effort: Medium

2. **Template-aware automation editor** — make rules reference a concrete notification template version and integrate template selection/rendering into CRUD/evaluation.
   - Pros: coherent user-facing message authoring and stronger policy control.
   - Cons: changes H4 semantics, requires new linkage/version policy and broader tests; not required for “ver, editar, activar/desactivar”.
   - Effort: High

### Recommendation
Choose the minimal approach. The minimum contract is authenticated CRUD for existing fields, list/detail data including `enabled`, and an explicit enable/disable mutation that records audit context. Validate event types/channels/template-event policy and cooldown bounds at the API boundary, preserve JSONB conditions as a deliberately bounded shape, and reject unsupported trigger semantics rather than inventing a trigger DSL. Use admin-only mutation (and decide explicitly whether operators may read) because rules affect outbound notifications. Suggested slices: (1) backend serializer/schema/service CRUD plus auth, validation, audit, and tests; (2) frontend route/nav/types/API client and read-only list states; (3) detail/edit form, enable/disable action, optimistic or refresh-after-mutation behavior, component tests and stories; (4) full backend `uv run pytest tests/` and web Vitest gates.

### Risks
- `template_event` is not a foreign key or template ID. `evaluate_event` currently sends payload text or the event name directly and does not call `templates.render`; exposing it as a “template” field can mislead operators. Keep this explicit in the UI or defer template redesign.
- `ALLOWED_EVENTS` and `ALLOWED_CHANNELS` are service constants, while the schema does not enforce them; API and evaluator validation can drift unless the CRUD contract reuses the same policy.
- `evaluate_event` audits disabled rules and evaluations, but CRUD has no established automation-specific audit action; define stable actions and before/after snapshots.
- `created_by` is a required string, while updates do not change ownership; preserve creator and use the authenticated username as mutation actor.
- No relationships are declared on `AutomationRule`/`AutomationExecution`; detail views must query executions explicitly and should not assume ORM navigation.
- Rules with `channel="email"` are allowed by H4, but the evaluator recipient fallback and delivery policy must be made visible; UI should not promise template approval or SMTP semantics that are not currently applied.
- Migration 015 already exists and is included in migration integration expectations; no pending migration was found. A schema extension (for example, template version FK) would be a separate change, not incidental UI work.

### Ready for Proposal
Yes. The proposal should define the actor/role policy, exact CRUD paths and response shapes, whether delete means hard delete or disable, the bounded conditions format, and explicitly keep LLM `create_automation`, complex triggers, template-version linkage, execution history UI, and new event publishers out of scope.
