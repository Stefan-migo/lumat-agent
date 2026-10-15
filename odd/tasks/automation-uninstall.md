# automation-uninstall — remove an installed automation recipe

Objective: let an admin uninstall an installed automation recipe, which today can only be
installed, never removed.
Branch: `odd/automation-uninstall` · Worktree: `../lumat-agent-odd-automation-uninstall` · Base: `main`
Delivery: single PR (small work unit). Test runner: `uv run pytest` (backend), `npx vitest run` (web).

## Specs

- **S1 — Uninstall frees the recipe slot.** Uninstalling removes the `AutomationInstallation`
  row so the same `recipe_id` can be installed again. Today `install()` rejects with
  `RecipeAlreadyInstalled` while any installation of the recipe exists (even disabled), so a
  disabled recipe occupied its slot forever.
- **S2 — Uninstall removes the compiled rule and its execution history.** The derived
  `AutomationRule` and its `AutomationExecution` rows are deleted in one transaction, in
  dependency order (executions → rule → installation).
- **S3 — Uninstall is audited.** Exactly one `audit_log` entry `automation.installation.delete`
  with the installation snapshot in `before`, written by the caller's session.
- **S4 — API.** `DELETE /panel/api/automation-installations/{id}` — admin only
  (`require_admin_json`), `200 {"ok": true}`, `404` when the installation does not exist,
  `403` for non-admin roles. `disable`/`enable` remain unchanged.
- **S5 — UI.** The "Instaladas" tab offers a "Quitar" action that opens a confirmation dialog;
  on success the list refreshes and the recipe reappears as installable in the catalog. A
  failed removal keeps the dialog open and shows the error inside it.
- **S6 — DB grant.** The `app` role gains `DELETE` on `automation_installations` (migration 057);
  045 granted only `SELECT/INSERT/UPDATE`.

## Tasks

- T1 (S6) — migration `057_grant_automation_installation_delete.sql` + version in `test_migrations`. commit `4f6aa8cf`
- T2 (S1,S2,S3,S4) — `uninstall()` in `automation_installations.py` + DELETE route + integration/functional tests. commit `14ff7515`
- T3 (S5) — `deleteAutomationInstallation` in `api.ts` + "Quitar" button/dialog + page tests. commit `f0f0999c`

## Log

- L1 (2026-10-15, owner): "vamos con 1. desinstalador" — implement the uninstall work unit.
- L2: Graph Check consulted nodes `automation_installations`, `AutomationRule`, `AutomationExecution`,
  `AutomationRecipesPage.tsx`, `api.ts`, `record_audit`.
- L3: RED observed — `ImportError: cannot import name 'uninstall'`, then `InsufficientPrivilege`
  (missing DELETE grant) and a FK-order failure before the final green.
- L4: Backend focused green (59 passed); full backend suite exit 0 (2268 tests);
  frontend 108 files / 1229 tests green + `npm run build` green.
- L5: Independent verification (gentle-ai-verify, read-only) — S1..S6 all MET, 0 blockers,
  1 advisory (duplicate page-level error banner behind the dialog). Probes confirmed
  isolation, dependency order, atomic rollback, the 057 grant, and that baseline RED was
  `ImportError`/`405`. Probes committed as regression tests; advisory fixed.
