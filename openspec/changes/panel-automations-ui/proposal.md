# Proposal: Panel Automations UI

## Intent

Close roadmap line 4.8 by giving authorized staff a safe management surface for the already-delivered H4 automation engine. Administrators need to create and edit deterministic notification rules; operators need to understand which rules exist without receiving mutation authority.

## Scope

### In Scope
- Authenticated JSON CRUD for existing `AutomationRule` fields, with list and detail responses.
- Admin-only create, update, and explicit enable/disable mutations; operators may read rules.
- React management page with list, separate detail/edit form, loading/error/empty/403 states, and enable/disable confirmation.
- API-bound validation, stable automation CRUD audit actions, before/after snapshots, and refresh-after-mutation behavior.

### Out of Scope
- Hard delete: disabling is the reversible lifecycle action and preserves execution/audit history.
- LLM or natural-language rule creation, complex triggers/DSL, new event publishers, execution-history UI, or evaluator/worker redesign.
- Notification-template-version linkage or redesign. `template_event` remains an explicit event/content value, not a rendered template selector.

## Capabilities

### New Capabilities
- `automation-rules-panel`: Authenticated rule management API and React list/detail surface with role-aware mutations.

### Modified Capabilities
- `automation-rules`: Add the management contract, bounded authoring validation, explicit disablement mutations, and CRUD audit requirements without changing H4 evaluation semantics.
- `admin-panel`: Expose automation reads to authenticated operators and admin-only automation mutations.

## Approach

Reuse the H4 `AutomationRule` model and evaluator policy constants (`ALLOWED_EVENTS`, `ALLOWED_CHANNELS`, cooldown bounds) at the API boundary. Accept only the evaluator-supported conditions shape and reject unsupported operators rather than introducing a trigger language. Preserve `created_by`; record the authenticated actor and before/after snapshots for create, update, enable, and disable. Extend the existing panel router/serializer/auth patterns and native History API SPA, using a separate detail form rather than inline editing.

## Deliverables / Affected Areas

| Area | Impact | Deliverable |
|------|--------|-------------|
| `app/panel/api/routes`, serializers, automation service, audit | Modified | CRUD/status endpoints, validation, authorization, audit |
| `web/src/api.ts`, `types.ts`, panel routes/shell, pages | New/Modified | API client, navigation, list/detail UI |
| `tests/functional`, `web/src/**/*.test.*`, stories | New/Modified | Contract, role, state, and accessibility coverage |

## Test Plan Hints

Strict RED→GREEN TDD. Cover operator read/admin mutation, anonymous/forbidden responses, validation rejection, audit snapshots, disablement, and refresh behavior. Run `uv run pytest tests/` and Vitest/build in `web/`.

## Risks

| Risk | Mitigation |
|------|------------|
| API policy drifts from evaluator | Reuse service constants and bounded condition validation. |
| Operators misunderstand `template_event` | Label it as notification event/content and defer template-aware UX. |
| Broad change overloads review | Deliver stacked-to-main slices, each under ~400 changed lines. |

## Rollback Plan

Revert the additive API, route, navigation, and page slices. Existing H4 evaluation, worker, rules, executions, and audit data remain unchanged; disabling is reversible through the API.

## Dependencies

- Delivered H4 automation rules/evaluator, existing panel authentication/audit, and React SPA primitives.

## Success Criteria

- [ ] Admins can create, edit, enable, and disable valid rules; operators can read them but cannot mutate.
- [ ] Unsupported policies and condition semantics are rejected before persistence, with auditable before/after changes.
- [ ] The page exposes actionable loading, empty, error, and permission states without changing H4 execution behavior.
