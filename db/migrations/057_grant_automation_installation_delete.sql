-- 057_grant_automation_installation_delete.sql — allow the app role to uninstall recipes.
-- 045 granted only SELECT/INSERT/UPDATE; the uninstall path deletes the installation row.

GRANT DELETE ON automation_installations TO app;

-- Rollback: REVOKE DELETE ON automation_installations FROM app;
