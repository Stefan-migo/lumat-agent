# Design: Panel Automations UI

## Technical Approach

Add a thin authenticated JSON router over the existing `AutomationRule` table and a small service boundary that owns authoring validation and CRUD/audit orchestration. The evaluator remains unchanged; its allowlists and matching semantics are reused by the management boundary. The SPA adds a top-level list route plus a separate detail/edit route using the existing History API, `PageFrame`, `DataTable`, `StateMessage`, `Dialog`, and `useAsyncData` patterns.

Graph nodes consulted: `AutomationRule`, `automation.py`, `evaluate_event()`, `record_audit()`, `AuditLog`, `api/routes/settings.py`, `routes/notifications.py`, `require_user_json()`, `require_admin_json()`, `serializers.py`, `apiFetch()`, `AgendaPage.tsx`, `DataTable`, `PanelShell.tsx`, `AppShell.tsx`, and `panelRoutes.ts`. Consulted edges: `automation.py → AutomationRule`, `automation.py → record_audit()`, `routes/settings.py → require_admin_json()`, `routes/notifications.py → require_user_json()`, `api.ts → AgendaPage.tsx`, and `AppShell.tsx → panelRoutes.ts`.

## Architecture Decisions

| Option | Tradeoff | Decision |
|---|---|---|
| `/panel/api/automation-rules` resource with explicit status actions | Conventional resource API; no hard-delete ambiguity | Choose `GET /panel/api/automation-rules`, `POST /panel/api/automation-rules`, `GET /panel/api/automation-rules/{id}`, `PATCH /panel/api/automation-rules/{id}`, `POST /panel/api/automation-rules/{id}/enable`, `POST /panel/api/automation-rules/{id}/disable`. |
| Validation in `app/services/automation.py` | Keeps policy identical for every caller; route stays thin | Choose shared `validate_rule_input()` using `ALLOWED_EVENTS`, `ALLOWED_CHANNELS`, and the new authoring range policy `0..2592000`; this range is not an existing evaluator policy. |
| Flat scalar conditions only | Excludes evaluator-unsupported DSL/nesting and keeps the form deterministic | Choose object keys with non-empty strings and JSON scalar values (`string`, `number`, `boolean`, `null`); reject arrays/objects and unknown operators before persistence. |
| Admin dependency on every mutation | Server authority cannot be bypassed by hiding controls | Choose `require_admin_json`; reads use `require_user_json`. |
| Separate detail/edit page | Avoids dense inline mutation state and gives deep-linkable editing | Choose `/panel/app/automation-rules/{id}`. |

## Data Flow and Contracts

`SPA → apiFetch (/panel/api/automation-rules) → automation_rules router → automation service validation/CRUD → AutomationRule → serializer + audit → JSON response`.

All responses are JSON-native. `Rule` is `{id,name,event_type,conditions,channel,template_event,cooldown_seconds,enabled,created_by,created_at,updated_at}` with ISO-8601 timestamps. `GET /panel/api/automation-rules` returns `{"rules":[Rule]}` (ordered `id ASC`); `GET /panel/api/automation-rules/{id}` returns `{"rule":Rule}`. `POST /panel/api/automation-rules` accepts `{name,event_type,conditions,channel,template_event,cooldown_seconds}` and returns `201 {"rule":Rule}` with `enabled=true` and `created_by=current.username`. `PATCH /panel/api/automation-rules/{id}` accepts the same fields and returns `200 {"rule":Rule}`; `enabled` is not editable there. `POST /panel/api/automation-rules/{id}/enable` and `POST /panel/api/automation-rules/{id}/disable` return `200 {"ok":true,"rule":Rule}` and are idempotent. Missing IDs return `404 {"detail":"automation rule not found"}`; validation returns `422` with field/detail information; anonymous and operator mutation responses are JSON `401`/`403`.

Validation requires `event_type` and `template_event` in `ALLOWED_EVENTS`, `channel` in `ALLOWED_CHANNELS`, and integer `cooldown_seconds` in the new shared authoring policy range `0..2592000`; this range is defined by management validation in `app/services/automation.py`, not consumed or defined by the evaluator. `conditions` must be a flat object of scalar exact-match values, matching `_matches`/`evaluate_event`; no LLM rules or template-version identifiers are accepted. Create, update, enable, and disable call `record_audit` with actions `automation.rule.create|update|enable|disable`, actor `current.username`, entity `automation_rule`, and serialized before/after snapshots (`before=null` on create). `created_by` is never changed. Commit occurs only after mutation and audit are staged.

## File Changes

| File | Action | Description |
|---|---|---|
| `app/services/automation.py` | Modify | Shared policy validation and rule CRUD/status helpers; evaluator behavior unchanged. |
| `app/panel/api/routes/automation_rules.py` | Create | Authenticated list/detail and admin mutation endpoints. |
| `app/panel/api/serializers.py`, `app/panel/api/__init__.py` | Modify | Rule serializer and router registration. |
| `web/src/{api.ts,types.ts}` | Modify | Rule types and six client functions. |
| `web/src/components/domain/{panelRoutes,PanelShell,AppShell}.tsx` | Modify | Route/detail ID, nav entry, page selection. |
| `web/src/components/pages/{AutomationRulesPage,AutomationRuleDetailPage}.tsx` | Create | Read-only list and separate create/edit/status form. |
| `tests/functional/test_api_automation_rules.py`, `web/src/components/pages/*test.tsx`, stories | Create | RED-first contract, role, state, accessibility, confirmation, refresh, and fixtures. |

## Testing Strategy

Backend functional tests cover anonymous/operator/admin access, exact shapes, validation atomicity, preservation of `created_by`, status idempotence, no deletion, and four audit snapshots. Frontend Vitest tests cover list/detail navigation, loading/error/empty/403, read-only operator controls, form validation display, confirmation, and refresh-after-mutation. Storybook covers data, loading, empty, error, forbidden, create, edit, and confirmation states. Gates: `uv run pytest tests/`; `cd web && npx vitest run && npx tsc -b && npm run build`.

## Threat Matrix

| Boundary | Applicability | Safe/failure behavior | Planned RED tests |
|---|---|---|---|
| Documentation-like paths | N/A — no file execution | None | None |
| Git repository selection | N/A — no VCS automation | None | None |
| Commit state | N/A — no commit automation | None | None |
| Push state | N/A — no push automation | None | None |
| PR commands | N/A — no PR command execution | None | None |
| SPA routing | Applicable | Canonical list/detail paths; malformed/non-rule IDs fall back to dashboard | Parser, deep-link, canonicalization, `aria-current`, and detail-back tests |

## Migration / Rollout

No migration required; the model and schema already exist. Deliver 3–4 stacked-to-main slices, each under ~400 authored lines: (1) backend contract/validation/audit, (2) frontend route/list/client, (3) detail mutations/confirmation/refresh, (4) stories and final gates. Each slice has strict RED→GREEN tests and is independently revertible.

## Open Questions

None.
