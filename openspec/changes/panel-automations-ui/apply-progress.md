# Apply Progress: Panel Automations UI

## Slice 1 — Backend CRUD, Validation, Audit

**Mode:** Strict TDD (RED → GREEN → triangulate → refactor)
**Delivery:** auto-chain, stacked-to-main, branch `feat/panel-automations-backend`
**Boundary:** backend API/service only; no `web/` changes
**Estimated authored lines:** ~300, within the 400-line slice budget

### Completed Tasks

- [x] 1.1 AP-12 access and envelope tests
- [x] 1.2 AR-4/5/6 CRUD, validation, atomicity, and audit tests
- [x] 1.3 Automation authoring validation and CRUD/status service helpers
- [x] 1.4 Authenticated automation-rules API, serializer, and router registration

### TDD Cycle Evidence

| Task | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 1.1 | `tests/functional/test_api_automation_rules.py` | Functional HTTP | N/A (new file) | ✅ 5 tests failed with route 404/fixture setup errors | ✅ 5 passed | ✅ Anonymous, operator, admin, 404, and method cases | ✅ Shared login/create helpers and local rule cleanup |
| 1.2 | `tests/functional/test_api_automation_rules.py` | Functional HTTP | N/A (new file) | ✅ CRUD/validation/audit assertions failed before route/service existed | ✅ 5 passed | ✅ Valid CRUD, boundary cooldown, scalar/null values, nested/list rejection, idempotent status | ✅ Atomic validation before mutation and snapshot helper |
| 1.3 | `tests/functional/test_api_automation_rules.py` | Functional HTTP | Existing automation evaluator behavior covered by full suite | ✅ Tests referenced missing service behavior | ✅ 5 focused tests passed | ✅ Multiple events/channels/cooldowns/condition shapes | ✅ Reused evaluator allowlists; authoring cooldown remains service-only |
| 1.4 | `tests/functional/test_api_automation_rules.py` | Functional HTTP | Existing panel API suite passed in full gate | ✅ Endpoint requests returned 404 | ✅ 5 focused tests passed | ✅ Read/admin/operator/anonymous/status/not-found paths | ✅ Thin routes delegate to service and serializer |

### Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command and exact result | `uv run pytest tests/functional/test_api_automation_rules.py` → **5 passed** in 6.78s |
| Runtime harness command/scenario and exact result | Same real FastAPI `TestClient` path through login/session, JSON routes, PostgreSQL test DB, mutation, and audit persistence → **5 passed** |
| Rollback boundary | Revert `app/services/automation.py`, `app/panel/api/routes/automation_rules.py`, `app/panel/api/serializers.py`, `app/panel/api/__init__.py`, and `tests/functional/test_api_automation_rules.py`; evaluator remains unchanged |

### Gate Evidence

- `uv run pytest tests/` → **583 passed** in 4m39s.
- `uv run pytest tests/functional/test_api_automation_rules.py` → **5 passed** in 6.78s.
- No `web/` files were modified.

### Graph Check

Consulted `AutomationRule`, `automation.py`, `record_audit()`, `AuditLog`, `panel/deps.py`, `serializers.py`, `routes/notifications.py`, and `AR-6 CRUD Audit Trail`. Consulted edges included `AutomationRule ↔ models.py`, `automation.py → AutomationRule`, `automation.py → record_audit()`, `routes/notifications.py → require_user_json()`, and `routes/settings.py → require_admin_json()`.

### Deviations / Issues

None from the corrected design. The shared functional fixture does not truncate `automation_rules`, so the new test file owns cleanup for that table to keep tests isolated.
