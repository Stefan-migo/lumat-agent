# LumatAgent Test Suite

> H1 acceptance traceability record (Batch 6, T6.1), kept valid as the H1
> acceptance deliverable. The suite also covers Hito 2–4; their specifications
> are traced by each archived change's own artifacts under
> `openspec/changes/archive/`, not by an H2–H4 table here.
> Source of truth for the requirement mapping: `openspec/changes/hito-1-setup-whatsapp/tasks.md`
> (Traceability section). Updated 2026-09-17.

## Running the suite

The suites run against a shared pgvector test database. Bring it up with the
compose `test` profile (T6.1):

```bash
docker compose -f infra/docker-compose.yml --profile test up -d db-test
export DEEPSEEK_API_KEY=sk-test       # optional: tests/conftest.py forces this value before importing app
.venv/bin/pytest tests/              # full suite
.venv/bin/pytest -m "spec"           # only OpenSpec requirement scenarios
.venv/bin/pytest tests/functional    # functional flows (T6.2)
.venv/bin/pytest tests/injection     # prompt-injection suite (T6.3, SH-4)
```

`pyproject.toml` configures `pytest-timeout` (`timeout = 120`,
`timeout_method = "thread"`), so a hung test is hard-exited with a
MainThread stack dump after 120 seconds instead of hanging forever.

Every scenario test carries `@pytest.mark.spec("<REQ-ID>")` so the traceability
below is executable: `pytest -m spec` runs exactly the requirement scenarios.

## Layers

| Layer | Directory | What | Deps |
|-------|-----------|------|------|
| Integration | `tests/integration/` | Webhook pipeline (WH), chat nodes (CM/HH/SH-4), customers (CR), KB (KB), emergency (EM), handoff (HH), settings (SS), costs (SS-3/4) | Real pgvector; OpenAI/Meta mocked via respx |
| Functional | `tests/functional/` | CM/CR end-to-end flows over the webhook; panel flows (AP) | TestClient + seeded DB |
| Injection | `tests/injection/` | SH-4 prompt-injection suite (golden assertions) | TestClient + respx-mocked OpenAI |
| Unit | `tests/unit/` | Pure assistant, routing, prompt, state, registry, and scheduling behavior | Python unit-test doubles; no test database |
| Spec | `tests/spec/` | Specification tests for SDB, project, and memory contracts | Migrated test DB where required; local application services |

The suite currently contains 16 unit, 45 integration, 23 functional, 1
injection, and 6 spec `.py` files (including each layer's `conftest.py`, where
present). These are the same counts used by `openspec/config.yaml` under
`testing.notes`.

## Traceability: Spec requirement → Test file

| Req | Scenario | Test file(s) |
|-----|----------|--------------|
| WH-1 | Verify handshake | `tests/integration/test_webhook_verify.py` (`test_get_verify_returns_challenge_with_correct_token`) |
| WH-2 | Signature verified/rejected | `tests/integration/test_webhook_verify.py` (`test_post_with_valid_signature_returns_200`, `test_post_with_invalid_signature_returns_403`); `tests/integration/test_webhook_ingest.py` (`test_post_invalid_signature_rejected_and_dropped`, `test_post_missing_signature_rejected`) |
| WH-3 | 200 before processing | `tests/integration/test_webhook_ingest.py` (`test_200_returned_before_processing_runs`, `test_background_task_processes_message_after_200`) |
| WH-4 | Persist before process / sweep | `tests/integration/test_webhook_ingest.py` (`test_post_valid_message_persists_normalized_row`, `test_sweep_recovers_stuck_received_messages`) |
| WH-5 | wamid dedup | `tests/integration/test_webhook_ingest.py` (`test_wamid_dedup_keeps_single_row`) |
| WH-6 | Unsupported / 131051 | `tests/integration/test_webhook_ingest.py` (`test_unsupported_event_type_acknowledged_not_persisted`, `test_error_131051_value_skipped`, `test_error_131051_on_message_object_skipped`) |
| WH-7 | Retry storm / rate limit | `tests/integration/test_webhook_ingest.py` (`test_retry_storm_single_processing_pass`, `test_rate_limit_drops_overflow_after_15_per_minute`) |
| CM-1 | First contact menu + repeat resume | `tests/integration/test_chat_state.py` (`test_cm1_first_contact_greeting_with_menu`, `test_cm1_menu_has_exactly_8_categories`, `test_cm1_repeat_contact_resumes_not_from_scratch`); `tests/functional/test_conversation_flows.py` (`test_cm1_first_contact_presents_8_category_menu`, `test_cm1_repeat_contact_resumes_not_restarts`) |
| CM-2 | Progressive capture / skip | `tests/integration/test_chat_capture.py` (`test_cm2_progressive_capture_asks_fields_in_order`, `test_cm2_complete_capture_persists_and_confirms`, `test_cm2_skip_is_unknown_and_non_blocking`); `tests/functional/test_conversation_flows.py` (`test_cm2_skip_marks_unknown_and_continues`, `test_cm2_complete_capture_persists_consent_and_ficha`) |
| CM-3 | Intent + case classification | `tests/integration/test_chat_intent.py` (`test_cm3_intent_classified`, `test_cm3_case_classification_stored`, `test_cm3_state_case_holds_classification`) |
| CM-4 | Authorized guidance / no reliable answer | `tests/integration/test_chat_capture.py` (`test_cm4_kb_grounded_answer_with_kb_tags`, `test_cm4_kb_miss_cannot_answer_and_logs_unresolved`); `tests/functional/test_conversation_flows.py` (`test_cm6_kb_miss_logs_unresolved_and_escalates`) |
| CM-5 | Conversation summary | `tests/integration/test_chat_capture.py` (`test_cm5_summary_stored_on_conversation_and_case`); `tests/integration/test_handoff.py` (`test_handoff_bundle_contains_history_summary_customer_captured`) |
| CM-6 | Unresolved response logged | `tests/functional/test_conversation_flows.py` (`test_cm6_kb_miss_logs_unresolved_and_escalates`) |
| CR-1 | Auto-ficha on first contact | `tests/integration/test_customers.py` (`test_cr1_first_contact_creates_ficha`, `test_cr1_unknown_phone_creates_exactly_one_row`); `tests/functional/test_customer_flows.py` (`test_cr1_auto_ficha_on_first_contact`) |
| CR-2 | Phone-based dedup (E.164) | `tests/integration/test_customers.py` (`test_cr2_same_number_reuses_record`, `test_cr2_full_international_format_dedups`, `test_cr2_different_formatting_dedups`); `tests/integration/test_webhook_ingest.py` (`test_normalize_phone_e164_full_number`, `test_normalize_phone_e164_local_mobile`, `test_normalize_phone_e164_with_spaces_and_plus`); `tests/functional/test_customer_flows.py` (`test_cr2_phone_dedup_across_formats`) |
| CR-3 | Lifecycle states + invalid transition | `tests/integration/test_customers.py` (`test_cr3_valid_transition_updates_state`, `test_cr3_invalid_transition_rejected`, `test_cr3_state_change_audited`); `tests/functional/test_api_clients.py` (`test_state_change_valid_transition_audited`, `test_state_change_invalid_transition_400_json`) |
| CR-4 | Internal notes | `tests/integration/test_customers.py` (`test_cr4_add_note_stores_author_and_timestamp`, `test_cr4_list_notes_chronological`, `test_cr4_notes_are_staff_only_no_customer_exposure`); `tests/functional/test_api_clients.py` (`test_add_note_returns_note_and_audits`) |
| CR-5 | History linkage | `tests/integration/test_customers.py` (`test_cr5_history_lists_conversations_cases_messages`); `tests/functional/test_api_clients.py` (`test_client_ficha_returns_full_payload`, `test_client_ficha_returns_chronological_visit_lifecycle_history`) |
| CR-6 | Captured data + consent on ficha | `tests/integration/test_customers.py` (`test_cr6_captured_data_persisted_on_ficha`, `test_cr6_consent_recorded_with_timestamp`); `tests/functional/test_conversation_flows.py` (`test_cm2_complete_capture_persists_consent_and_ficha`) |
| KB-1 | Ingest formats + chunks | `tests/integration/test_kb.py` (`test_kb1_ingest_markdown_chunks_stored`, `test_kb1_ingest_pdf_extracts_text`, `test_kb1_ingest_csv_row_grouped`, `test_kb1_chunk_count_for_long_document`) |
| KB-2 | Retrieval top-k/threshold | `tests/integration/test_kb.py` (`test_kb2_retrieval_relevant_hit`, `test_kb2_retrieval_threshold_miss`, `test_kb2_retrieval_top_k_limits_results`, `test_kb2_min_sim_configurable`) |
| KB-3 | Disable | `tests/integration/test_kb.py` (`test_kb3_disable_document_excludes_from_retrieval`); `tests/functional/test_api_kb_settings.py` (`test_kb_disable_document_audits`) |
| KB-4 | Version / restore | `tests/integration/test_kb.py` (`test_kb4_update_creates_new_version_and_reembeds`, `test_kb4_restore_previous_version_flip_no_reembed`); `tests/functional/test_api_kb_settings.py` (`test_kb_edit_creates_new_version_and_audits`, `test_kb_restore_previous_version_audits`) |
| EM-1 | Keyword detection | `tests/integration/test_emergency.py` (`test_strong_hit_each_default_keyword`, `test_accent_folded_variants_are_strong`, `test_custom_keyword_from_settings_detected`); `tests/integration/test_settings.py` (`test_emergency_keywords_default_contains_em1_core`, `test_emergency_keywords_override_round_trip`) |
| EM-2 | Flow interrupt mid-capture | `tests/integration/test_emergency.py` (`test_strong_hit_mid_capture_interrupts`) |
| EM-3 | Safety instructions + notified | `tests/integration/test_emergency.py` (`test_strong_hit_mid_capture_interrupts`); `tests/integration/test_emergency_notify.py` (`test_emergency_node_fires_notification_on_strong_hit`, `test_notification_failure_never_blocks_safety_reply`) |
| EM-4 | Notification + ack | `tests/integration/test_emergency_notify.py` (`test_template_goes_to_owner_with_phone_and_context`, `test_email_fallback_on_whatsapp_failure`, `test_emergency_node_fires_notification_on_strong_hit`); `tests/functional/test_api_cases.py` (`test_case_ack_emergency_records_ack_and_audits`) |
| EM-5 | Weak hit → escalate | `tests/integration/test_emergency.py` (`test_weak_hit_escalates_not_ignored`, `test_weak_hit_escalates_to_human`) |
| HH-1 | State transitions | `tests/integration/test_handoff.py` (`test_state_transition_bot_to_human_records_event`, `test_state_transition_close_records_closure`) |
| HH-2 | Deriva bundle | `tests/integration/test_handoff.py` (`test_handoff_bundle_contains_history_summary_customer_captured`) |
| HH-3 | 2× unknown + deterministic triggers | `tests/integration/test_chat_intent.py` (`test_hh3_unknown_intent_increments_counter`, `test_hh3_second_unknown_escalates`); `tests/functional/test_conversation_flows.py` (`test_hh3_two_failures_escalate`) |
| HH-4 | Cases view | `tests/functional/test_api_cases.py` (`test_cases_list_returns_open_cases_with_embedded_customer_and_users`, `test_cases_list_skips_closed_cases`) |
| HH-5 | Persist during human | `tests/integration/test_handoff.py` (`test_hh5_human_state_persists_without_bot_reply`, `test_hh5_human_state_graph_direct_still_persists_events`); `tests/integration/test_webhook_ingest.py` (`test_retry_storm_single_processing_pass`) |
| AP-1 | Login / lockout / audit | `tests/functional/test_auth.py` (`test_authorized_json_login_resets_failed_counter`, `test_lock_expiry_allows_json_login_again`, `test_inactive_user_cannot_json_login`) |
| AP-2 | Role matrix (server-side) | `tests/functional/test_auth.py` (`test_json_session_role_and_tampered_cookie_are_enforced`); `tests/functional/test_api_kb_settings.py` (`test_kb_endpoints_denied_403_for_operador_json`, `test_settings_endpoints_denied_403_for_operador_json`) |
| AP-3 | Clients list/search | `tests/functional/test_api_clients.py` (`test_clients_list_returns_wrapped_search`, `test_clients_search_by_name_and_phone`, `test_clients_search_no_matches_returns_empty_list`) |
| AP-4 | Conversation view | `tests/functional/test_api_conversations.py` (`test_conversation_returns_metadata_and_messages_chronological`, `test_conversation_detail_uses_same_selected_case_and_captured_data`) |
| AP-5 | Cases update + assign | `tests/functional/test_api_cases.py` (`test_case_update_changes_status_and_responsible_audited`, `test_case_update_clears_responsible_with_null`) |
| AP-6 | KB manager access | `tests/functional/test_api_kb_settings.py` (`test_kb_endpoints_denied_403_for_operador_json`, `test_kb_list_returns_docs_with_provider_model_cost`) |
| AP-7 | CSV export | `tests/functional/test_dashboard_export.py` (`test_export_clients_csv`, `test_export_cases_csv`) |
| AP-8 | Basic KPIs | `tests/functional/test_api_dashboard.py` (`test_kpis_returns_exact_seeded_values`, `test_kpis_empty_db_returns_zeros`, `test_kpis_respects_configured_window`) |
| SS-1 | Scope rules (bot/escalate) | `tests/integration/test_settings.py` (`test_scope_mode_default_is_bot_resolve`, `test_scope_mode_per_category_override`); `tests/functional/test_api_kb_settings.py` (`test_settings_update_scope_audited`) |
| SS-2 | Emergency keywords | `tests/integration/test_settings.py` (`test_emergency_keywords_default_contains_em1_core`, `test_emergency_keywords_override_round_trip`); `tests/functional/test_api_kb_settings.py` (`test_settings_update_keywords_audited`) |
| SS-3 | Cost guardrails | `tests/integration/test_cost_guardrails.py` (`test_conversation_cost_state_normal_below_80`, `test_conversation_cost_state_conservative_at_80`, `test_conversation_cost_state_blocked_at_100`, `test_daily_cost_state_thresholds`); `tests/functional/test_api_kb_settings.py` (`test_settings_update_limits_audited`) |
| SS-4 | Spend tracking + panel data | `tests/integration/test_send_costs.py` (`test_conversation_spend_sums_cost_columns`, `test_daily_spend_sums_all_conversations`); `tests/integration/test_cost_guardrails.py` (`test_spend_snapshot_exposes_spend_limits_and_mode`); `tests/functional/test_api_kb_settings.py` (`test_settings_get_returns_all_sections_and_snapshot`) |
| SS-5 | Tone / standard messages | `tests/integration/test_settings.py` (`test_tone_default_when_unset`, `test_tone_override`, `test_message_override_wins_over_caller_default`); `tests/functional/test_api_kb_settings.py` (`test_settings_update_tone_audited`) |
| SH-1 | Network/access hardening | UNCOVERED — no covering test found after searching the `tests` tree; checklist remains in `docs/hardening.md`. |
| SH-2 | Container/secrets hardening | UNCOVERED — no covering test found after searching the `tests` tree; checklist remains in `docs/hardening.md`. |
| SH-3 | Backups + monitoring | UNCOVERED — no covering test found after searching the `tests` tree; operational scripts are `infra/backup.sh`, `infra/restore-test.sh`, and `infra/monitor.sh`, with the checklist in `docs/hardening.md`. |
| SH-4 | Prompt-injection mitigations | `tests/injection/test_injection_suite.py` (`test_sh4_deterministic_payload_never_reaches_llm_and_escalates`, `test_sh4_llm_flag_layer_isolates_payload_as_data`, `test_sh4_admin_tool_attempt_never_executes`); `tests/integration/test_chat_intent.py` (`test_sh4_user_text_only_in_user_input_slot`, `test_sh4_injection_escalates_without_llm_call`, `test_sh4_injection_detected_by_llm_also_escalates`) |
| SH-5 | Audit log | `tests/integration/test_emergency_notify.py` (`test_template_goes_to_owner_with_phone_and_context`); `tests/integration/test_cost_guardrails.py` (`test_internal_cost_call_key_is_idempotent_under_concurrent_retry`); `tests/functional/test_auth.py` (`test_authorized_json_login_resets_failed_counter`); `tests/functional/test_api_kb_settings.py` (`test_kb_upload_ingests_and_audits`, `test_settings_update_scope_audited`); `tests/functional/test_api_cases.py` (`test_case_update_changes_status_and_responsible_audited`, `test_case_ack_emergency_records_ack_and_audits`); `tests/functional/test_api_clients.py` (`test_state_change_valid_transition_audited`, `test_add_note_returns_note_and_audits`); `tests/injection/test_injection_suite.py` (`test_sh4_deterministic_payload_never_reaches_llm_and_escalates`) |
