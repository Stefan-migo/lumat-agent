# LumatAgent Test Suite

> H1 acceptance deliverable (Batch 6, T6.1) — spec-to-test traceability.
> Source of truth for the requirement mapping: `openspec/changes/hito-1-setup-whatsapp/tasks.md`
> (Traceability section). Updated 2026-08-13.

## Running the suite

The suites run against a shared pgvector test database. Bring it up with the
compose `test` profile (T6.1):

```bash
docker compose -f infra/docker-compose.yml --profile test up -d db-test
export OPENAI_API_KEY=sk-test        # never let the dev-shell real key leak in
.venv/bin/pytest tests/              # full suite
.venv/bin/pytest -m "spec"           # only OpenSpec requirement scenarios
.venv/bin/pytest tests/functional    # functional flows (T6.2)
.venv/bin/pytest tests/injection     # prompt-injection suite (T6.3, SH-4)
```

Every scenario test carries `@pytest.mark.spec("<REQ-ID>")` so the traceability
below is executable: `pytest -m spec` runs exactly the requirement scenarios.

## Layers

| Layer | Directory | What | Deps |
|-------|-----------|------|------|
| Integration | `tests/integration/` | Webhook pipeline (WH), chat nodes (CM/HH/SH-4), customers (CR), KB (KB), emergency (EM), handoff (HH), settings (SS), costs (SS-3/4) | Real pgvector; OpenAI/Meta mocked via respx |
| Functional | `tests/functional/` | CM/CR end-to-end flows over the webhook; panel flows (AP) | TestClient + seeded DB |
| Injection | `tests/injection/` | SH-4 prompt-injection suite (golden assertions) | TestClient + respx-mocked OpenAI |

## Traceability: Spec requirement → Test file

| Req | Scenario | Test file(s) |
|-----|----------|--------------|
| WH-1 | Verify handshake | `tests/integration/test_webhook_verify.py` |
| WH-2 | Signature verified/rejected | `tests/integration/test_webhook_ingest.py` (test_post_invalid_signature_rejected_and_dropped, test_post_missing_signature_rejected) |
| WH-3 | 200 before processing | `tests/integration/test_webhook_ingest.py` (test_200_returned_before_processing_runs, test_background_task_processes_message_after_200) |
| WH-4 | Persist before process / sweep | `tests/integration/test_webhook_ingest.py` (test_post_valid_message_persists_normalized_row, test_sweep_recovers_stuck_received_messages) |
| WH-5 | wamid dedup | `tests/integration/test_webhook_ingest.py` (test_wamid_dedup_keeps_single_row) |
| WH-6 | Unsupported / 131051 | `tests/integration/test_webhook_ingest.py` |
| WH-7 | Retry storm / rate limit | `tests/integration/test_webhook_ingest.py` (test_retry_storm_single_processing_pass, test_rate_limit_drops_overflow_after_15_per_minute) |
| CM-1 | First contact menu + repeat resume | `tests/integration/test_chat_state.py`, `tests/functional/test_conversation_flows.py` (test_cm1_first_contact_presents_8_category_menu, test_cm1_repeat_contact_resumes_not_restarts) |
| CM-2 | Progressive capture / skip | `tests/integration/test_chat_capture.py`, `tests/functional/test_conversation_flows.py` (test_cm2_skip_marks_unknown_and_continues, test_cm2_complete_capture_persists_consent) |
| CM-3 | Intent + case classification | `tests/integration/test_chat_intent.py` (test_cm3_*) |
| CM-4 | Authorized guidance / no reliable answer | `tests/integration/test_chat_capture.py` + KB-miss coverage in `tests/functional/test_conversation_flows.py` (test_cm6_kb_miss_logs_unresolved_and_escalates) |
| CM-5 | Conversation summary | `tests/integration/test_chat_capture.py`, `tests/integration/test_handoff.py` (bundle) |
| CM-6 | Unresolved response logged | `tests/functional/test_conversation_flows.py` (test_cm6_kb_miss_logs_unresolved_and_escalates) |
| CR-1 | Auto-ficha on first contact | `tests/integration/test_customers.py`, `tests/functional/test_customer_flows.py` (test_cr1_auto_ficha_on_first_contact) |
| CR-2 | Phone-based dedup (E.164) | `tests/integration/test_customers.py`, `tests/integration/test_webhook_ingest.py` (test_normalize_phone_e164_*), `tests/functional/test_customer_flows.py` (test_cr2_phone_dedup_across_formats) |
| CR-3 | Lifecycle states + invalid transition | `tests/integration/test_customers.py`, `tests/functional/test_clients.py` (test_state_change_updates_and_audits, test_invalid_state_transition_rejected) |
| CR-4 | Internal notes | `tests/functional/test_clients.py` (test_add_internal_note) |
| CR-5 | History linkage | `tests/functional/test_clients.py` (test_ficha_lists_history), `tests/integration/test_handoff.py` |
| CR-6 | Captured data + consent on ficha | `tests/functional/test_conversation_flows.py` (test_cm2_complete_capture_persists_consent) |
| KB-1 | Ingest formats + chunks | `tests/integration/test_kb.py` |
| KB-2 | Retrieval top-k/threshold | `tests/integration/test_kb.py` |
| KB-3 | Disable | `tests/integration/test_kb.py`, `tests/functional/test_kb_settings.py` (test_kb_disable_document) |
| KB-4 | Version / restore | `tests/integration/test_kb.py`, `tests/functional/test_kb_settings.py` (test_kb_edit_creates_new_version, test_kb_restore_previous_version) |
| EM-1 | Keyword detection | `tests/integration/test_emergency.py`, `tests/integration/test_settings.py` |
| EM-2 | Flow interrupt mid-capture | `tests/integration/test_emergency.py` |
| EM-3 | Safety instructions + notified | `tests/integration/test_emergency.py`, `tests/integration/test_emergency_notify.py` |
| EM-4 | Notification + ack | `tests/integration/test_emergency_notify.py`, `tests/functional/test_cases.py` (ack button) |
| EM-5 | Weak hit → escalate | `tests/integration/test_emergency.py` |
| HH-1 | State transitions | `tests/integration/test_handoff.py` |
| HH-2 | Deriva bundle | `tests/integration/test_handoff.py` |
| HH-3 | 2× unknown + deterministic triggers | `tests/integration/test_chat_intent.py` (test_hh3_*), `tests/functional/test_conversation_flows.py` (test_hh3_two_failures_escalate) |
| HH-4 | Cases view | `tests/functional/test_cases.py` |
| HH-5 | Persist during human | `tests/integration/test_handoff.py`, `tests/integration/test_webhook_ingest.py` (test_retry_storm_single_processing_pass) |
| AP-1 | Login / lockout / audit | `tests/functional/test_auth.py` |
| AP-2 | Role matrix (server-side) | `tests/functional/test_auth.py`, `tests/functional/test_kb_settings.py` (operador 403 on /panel/kb + /panel/settings) |
| AP-3 | Clients list/search | `tests/functional/test_clients.py` |
| AP-4 | Conversation view | `tests/functional/test_clients.py` (test_conversation_thread_*) |
| AP-5 | Cases update + assign | `tests/functional/test_cases.py` |
| AP-6 | KB manager access | `tests/functional/test_kb_settings.py` |
| AP-7 | CSV export | `tests/functional/test_dashboard_export.py` (test_export_clients_csv, test_export_cases_csv) |
| AP-8 | Basic KPIs | `tests/functional/test_dashboard_export.py` (test_dashboard_*) |
| SS-1 | Scope rules (bot/escalate) | `tests/integration/test_settings.py`, `tests/functional/test_kb_settings.py` (test_settings_save_scope_rules) |
| SS-2 | Emergency keywords | `tests/integration/test_settings.py`, `tests/functional/test_kb_settings.py` (test_settings_save_emergency_keywords) |
| SS-3 | Cost guardrails | `tests/integration/test_cost_guardrails.py` |
| SS-4 | Spend tracking + panel data | `tests/integration/test_send_costs.py`, `tests/functional/test_kb_settings.py` (test_settings_page_shows_spend_snapshot) |
| SS-5 | Tone / standard messages | `tests/integration/test_settings.py`, `tests/functional/test_kb_settings.py` (test_settings_save_tone) |
| SH-1 | Network/access hardening | `docs/hardening.md` (executable checklist) |
| SH-2 | Container/secrets hardening | `docs/hardening.md` (executable checklist) |
| SH-3 | Backups + monitoring | `infra/backup.sh`, `infra/restore-test.sh`, `infra/monitor.sh` + `docs/hardening.md` |
| SH-4 | Prompt-injection mitigations | `tests/injection/test_injection_suite.py` (golden assertions), `tests/integration/test_chat_intent.py` (test_sh4_*) |
| SH-5 | Audit log | audit assertions across `tests/integration/test_emergency_notify.py`, `tests/integration/test_cost_guardrails.py`, `tests/functional/test_auth.py`, `tests/functional/test_kb_settings.py`, `tests/functional/test_cases.py`, `tests/functional/test_clients.py`, `tests/injection/test_injection_suite.py` |
