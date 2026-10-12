-- 049_drop_automation_rule_template_event.sql — remove the redundant automation event field.

ALTER TABLE automation_rules DROP COLUMN IF EXISTS template_event;
