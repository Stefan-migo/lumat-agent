# Graph Report - .  (2026-08-19)

## Corpus Check
- 62 files · ~0 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2269 nodes · 4888 edges · 192 communities (129 shown, 63 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 233 edges (avg confidence: 0.71)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 122
- Community 128
- Community 129
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 141
- Community 142
- Community 143
- Community 144
- Community 145
- Community 146
- Community 147
- Community 148
- Community 149
- Community 150
- Community 152
- Community 153
- Community 154
- Community 155
- Community 157
- Community 158
- Community 159
- Community 160
- Community 161
- Community 162
- Community 163
- Community 164
- Community 165
- Community 166
- Community 167
- Community 168
- Community 169
- Community 170
- Community 171
- Community 172
- Community 173
- Community 174
- Community 175
- Community 176
- Community 177
- Community 178
- Community 179
- Community 180
- Community 181
- Community 182
- Community 184
- Community 189

## God Nodes (most connected - your core abstractions)
1. `make_user()` - 79 edges
2. `Message` - 77 edges
3. `Customer` - 64 edges
4. `Conversation` - 63 edges
5. `get_or_create_customer()` - 49 edges
6. `Case` - 46 edges
7. `User` - 45 edges
8. `_post()` - 30 edges
9. `get_setting()` - 29 edges
10. `get_or_create_conversation()` - 29 edges

## Surprising Connections (you probably didn't know these)
- `test_read_unknown_key_returns_none()` --calls--> `get_setting()`  [EXTRACTED]
  tests/integration/test_settings.py → app/services/settings.py
- `test_read_unknown_key_uses_caller_default()` --calls--> `get_setting()`  [EXTRACTED]
  tests/integration/test_settings.py → app/services/settings.py
- `_run_graph()` --calls--> `build_graph()`  [INFERRED]
  tests/integration/test_cost_guardrails.py → app/chat/graph.py
- `build_graph()` --calls--> `_run_graph()`  [INFERRED]
  app/chat/graph.py → tests/integration/test_chat_intent.py
- `LumatAgent Project` --shares_data_with--> `Engram persistent memory`  [INFERRED]
  README.md → .opencode/skills/cortex-session/SKILL.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **H1 spec requirement areas mapped to task batches (traceability)** — openspec_changes_hito_1_setup_whatsapp_tasks_wh, openspec_changes_hito_1_setup_whatsapp_tasks_cm, openspec_changes_hito_1_setup_whatsapp_tasks_cr, openspec_changes_hito_1_setup_whatsapp_tasks_kb, openspec_changes_hito_1_setup_whatsapp_tasks_em, openspec_changes_hito_1_setup_whatsapp_tasks_hh, openspec_changes_hito_1_setup_whatsapp_tasks_ap, openspec_changes_hito_1_setup_whatsapp_tasks_ss, openspec_changes_hito_1_setup_whatsapp_tasks_sh [EXTRACTED 0.85]
- **B3 Verified Spec Families (CR, CM, KB, HH, SH, SS)** — concept_cr_family, concept_cm_family, concept_kb_pipeline, concept_sh_security, openspec_changes_hito-1-setup-whatsapp_verify-report__spec_compliance_b3 [EXTRACTED 0.90]
- **SH-1..SH-5 security hardening checklist executed on rehearsal VM** — docs_hardening, docs_hardening_sh1, docs_hardening_sh2, docs_hardening_sh5, infra_docker_compose_prod_yml [EXTRACTED 0.90]
- **Ponytail minimal-code skill family (ladder YAGNI→stdlib→native→one line)** — opencode_skills_ponytail_audit, opencode_skills_ponytail_debt, opencode_skills_ponytail_help, opencode_skills_ponytail_plan, opencode_skills_ponytail_review, opencode_skills_cortex_persona_ponytail_rules [EXTRACTED 0.90]
- **Admin Panel Jinja Template Set (base + 8 views)** — app_panel_templates_base, app_panel_templates_dashboard, app_panel_templates_login, app_panel_templates_cases_list, app_panel_templates_clients_ficha, app_panel_templates_clients_list, app_panel_templates_conversations_thread, app_panel_templates_kb_list, app_panel_templates_settings_index [EXTRACTED 0.95]
- **Cortex skill pack bootstrap workflow** — opencode_commands_cortex_init_command, opencode_commands_cortex_init_script, cortex_skill_pack, graphify_knowledge_graph, cortex_skill_registry, sdd_init_command [EXTRACTED 1.00]
- **H1 technical stack** — fastapi_app, langgraph_graph, postgres_pgvector, docker_compose_infra, hostinger_kvm2_vps, meta_cloud_api [EXTRACTED 1.00]
- **Propuesta PDF build pipeline** — propuesta_build_script, mmdc_mermaid_cli, headless_chrome_render, md_to_pdf_engine, propuesta_main_document [EXTRACTED 1.00]
- **Case Record Lifecycle Across Specs** — shared_case_record [INFERRED 0.85]
- **Inbound WhatsApp Message Pipeline** — whatsapp-webhook_whatsapp-webhook, conversation-manager_conversation-manager, emergency-detection_emergency-detection, human-handoff_human-handoff [INFERRED 0.85]

## Communities (192 total, 63 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (80): cost_gate(), ConversationState, Evaluate spend states, alert the owner on crossings, flag cost_mode., _alert_action(), combined_cost_mode(), conversation_cost_state(), conversation_spend(), daily_cost_state() (+72 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (58): _answer_from_kb(), respond node — KB-grounded answers + unresolved logging (CM-4, CM-6). Only…, Grounded answer; records the LLM cost on the current message (D6). ``brief``…, get_settings(), Application configuration. Settings are read from environment variables ONLY…, Environment-only application settings (design: app/config.py, D3, SH-2)., Return the cached settings instance (cleared in tests via cache_clear)., Settings (+50 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (65): AuditLog, parametrize, Response, spec, _conversation(), _last_outbound(), _outbound_texts(), Customer (+57 more)

### Community 3 - "Community 3"
Cohesion: 0.09
Nodes (48): summary node — conversation summary at completion (CM-5). Generates a concise…, Case, Conversation, Customer, Message, process_message(), Process one inbound message: media download, conversation run, delivery. The…, Process messages stuck in `received` (BackgroundTask + startup sweep). Claim… (+40 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (43): persist_replies(), Session, Persist bot replies as outbound messages (status processed). The actual Meta…, Run the graph for one persisted inbound message; returns bot replies. Rebuilds…, run_conversation(), list_unresolved_questions(), Message, CM-6 query (no dedicated SQL view — filter by payload flag). (+35 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (46): jsdom, react, react-dom, storybook, @storybook/addon-essentials, @storybook/react-vite, @testing-library/jest-dom, @testing-library/react (+38 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (45): admin-panel capability, arquitectura-lumatagent.md (diagrams source), conversation-manager capability, Cortex session report.md, Cortex skill pack, Cortex skill registry (.atl/skill-registry.md), Cost guardrails (spend limits + alerts), cotizacion-lumat.md (pricing source of truth) (+37 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (43): create_app(), normalize_message(), Extract a normalized inbound message from a Meta message object. Returns None…, clean_db(), _count_inbound(), _count_messages(), _message(), _message_rows() (+35 more)

### Community 8 - "Community 8"
Cohesion: 0.09
Nodes (42): add_note(), customer_history(), get_or_create_customer(), InvalidStateTransition, list_notes(), normalize_phone_e164(), datetime, Session (+34 more)

### Community 9 - "Community 9"
Cohesion: 0.09
Nodes (42): acknowledge_emergency_if_ack(), is_ack_message(), True when the customer's reply is a pure ack-keyword message. "ok" / "listo" /…, Record the customer reply-keyword ack on the emergency case (T4.3.2).…, _audit_rows(), _call_notification(), _capturing_smtp(), clean_db() (+34 more)

### Community 10 - "Community 10"
Cohesion: 0.09
Nodes (42): Transition a conversation's bot/human/closed state (HH-1). Every transition…, set_conversation_state(), NormalizedMessage, persist_message(), INSERT the normalized message as `received`; True when newly inserted. ON…, The normalized inbound message record persisted before processing., ConvState, _case() (+34 more)

### Community 11 - "Community 11"
Cohesion: 0.06
Nodes (43): Security Hardening (SH-1..5), Hardening Checklist (SH-1/2/3 executable), SH-1 Network/Access Hardening, SH-2 Container/Secrets Hardening, SH-5 Audit Log Append-Only, Ops Runbook & Meta Onboarding Checklist, Backup Restore Drill, Deploy Flow (tag + compose restart) (+35 more)

### Community 12 - "Community 12"
Cohesion: 0.05
Nodes (39): client(), fake_embedder(), migrated_db(), mock_meta_send(), mock_openai_chat(), CompletedProcess, fixture, TestClient (+31 more)

### Community 13 - "Community 13"
Cohesion: 0.08
Nodes (37): api_login(), clean_db(), client(), fake_embedder(), login(), migrated_db(), CompletedProcess, fixture (+29 more)

### Community 14 - "Community 14"
Cohesion: 0.10
Nodes (34): CustomerState, client_add_note(), client_ficha(), client_state_change(), clients_list(), _customer_or_404(), NoteBody, BaseModel (+26 more)

### Community 15 - "Community 15"
Cohesion: 0.07
Nodes (31): MessageDirection, MessageStatus, MessageType, Settings, UserRole, MediaDownloadError, RateLimiter, Per-phone sliding window. ponytail: in-memory only — resets on restart.… (+23 more)

### Community 16 - "Community 16"
Cohesion: 0.10
Nodes (27): get_current_user_json(), Request, Session, User, Panel JSON API auth dependencies (design D4; PDW-AUTH-1, PDW-API-4). Parallel…, Resolve the signed-session user; JSON 401 when absent (PDW-AUTH-1)., Any authenticated user (admin or operador) — shared JSON routes., Admin-only JSON routes (PDW-API-4): operador -> 403 JSON. (+19 more)

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (31): User, _audit(), login(), login_form(), logout(), get, Request, Response (+23 more)

### Community 18 - "Community 18"
Cohesion: 0.16
Nodes (32): make_user(), Factory creating a panel user row directly (bcrypt hash) in a session., _doc_version(), _last_audit(), _login(), Panel JSON API KB + settings (B4/T4.1+T4.2; PDW-API-1/2/3/4, D1, D4). Admin-…, Seed a KB document through the service path (v1, embedded)., Limit validation mirrors the Jinja _number guard (SS-3): >= 0. (+24 more)

### Community 19 - "Community 19"
Cohesion: 0.10
Nodes (33): _audit_actions(), CompletedProcess, spec, Panel authentication + roles (T5.1; AP-1, AP-2, SH-5). Functional suite over…, No such user -> generic error + audit row, nothing else leaks., 5 failed attempts -> locked_until set; correct password then rejected., After locked_until passes, a correct login succeeds (15-min ban ends)., active=False accounts are rejected at the door (no session, audited). (+25 more)

### Community 20 - "Community 20"
Cohesion: 0.09
Nodes (32): get_or_create_conversation(), Return the open conversation for a customer; create it if none is open. Closed…, Decimal, Accumulate the token cost of one LLM call on the message (D6)., record_llm_cost(), deliver_all_pending(), deliver_outbound(), Send every pending outbound message across conversations (sweep path). (+24 more)

### Community 21 - "Community 21"
Cohesion: 0.12
Nodes (29): flash(), pop_flash(), Request, Store a one-shot notice in the session (shown on the next page)., Read and clear the one-shot notice for this request., Admin-only routes: settings and KB management (AP-2)., require_admin(), client_add_note() (+21 more)

### Community 22 - "Community 22"
Cohesion: 0.09
Nodes (24): ClientesListEmpty(), ClientesListView(), columns, Default, Empty, Loading, meta, Story (+16 more)

### Community 23 - "Community 23"
Cohesion: 0.14
Nodes (28): CustomerNote, Internal staff note on a customer ficha (CR-4; 002_customer_notes.sql). Staff-…, CustomerState, _customer_row(), _login(), Customer, Panel JSON API clients (B2/T2.2; PDW-API, PDW-API-3, PDW-AUTH-1, D1, D4). The…, Empty result is real (service filtered) — companion to the non-empty test. (+20 more)

### Community 24 - "Community 24"
Cohesion: 0.13
Nodes (26): Append-only audit service (SH-5). Every auditable action is recorded via…, acknowledge_case(), _audit_notification(), _customer_location(), _notification_body(), Session, Emergency owner/technician notification (EM-4; T4.3).…, Best-known location from the captured-data map (address, else comuna). (+18 more)

### Community 25 - "Community 25"
Cohesion: 0.09
Nodes (28): _audit_actions(), User, Panel JSON API authentication (B1/T1.2; PDW-AUTH-1/2/4, PDW-API-3, D1, D4). The…, Valid JSON credentials -> 200 {ok, role}, session cookie, audit., operador credentials -> same cookie, role=operador (triangulation)., Wrong password -> 401 JSON {"detail":"invalid credentials"}, audited., No such user -> same generic 401, nothing leaks (no user oracle)., 5 failures -> lock; even a correct password returns 401 "account locked". (+20 more)

### Community 26 - "Community 26"
Cohesion: 0.07
Nodes (27): DOM, DOM.Iterable, ES2022, node, src, vite/client, compilerOptions, erasableSyntaxOnly (+19 more)

### Community 27 - "Community 27"
Cohesion: 0.16
Nodes (24): _case_row(), _login(), Case, datetime, Panel JSON API cases (B3/T3.2; PDW-API, PDW-API-3, PDW-AUTH-1, D1, D4, D8).…, No session -> every cases endpoint answers 401 JSON, never a 302., closed_at set -> case excluded from the open list (HH-4)., Among escalated cases, the newest escalation comes first. (+16 more)

### Community 28 - "Community 28"
Cohesion: 0.22
Nodes (23): KeywordsBody, LimitsBody, MetaBody, _number(), _parse_scope(), BaseModel, get, post (+15 more)

### Community 29 - "Community 29"
Cohesion: 0.18
Nodes (22): _case_rows(), clean_db(), mock_chat(), Case, fixture, T3.4 integration tests — classify_intent + route nodes (CM-3, HH-3, SH-4).…, Seed a customer + open conversation + one inbound received message., Intercept OpenAI /chat/completions; captures requests for SH-4 checks. (+14 more)

### Community 30 - "Community 30"
Cohesion: 0.13
Nodes (13): ApiError, apiFetch(), App(), GateState, AppShell(), AppShellProps, NAV, NavEntry (+5 more)

### Community 31 - "Community 31"
Cohesion: 0.15
Nodes (22): KbChunk, disable_document(), Disable a document: excluded from retrieval, content kept (KB-3)., Semantic retrieval over the ACTIVE versions of enabled documents. Filters:…, retrieve(), _chunk_rows(), _embed(), _ingest() (+14 more)

### Community 32 - "Community 32"
Cohesion: 0.19
Nodes (21): classify_emergency(), compile_keywords(), fold_accents(), _keyword_fragment(), Emergency detection service (EM-1..EM-5, SS-2; design:…, Classify one message: ``"strong"`` | ``"weak"`` | None (no hit). ``pattern`` is…, Lowercase + fold accents to ASCII base letters ("Explosión" -> "explosion")., One keyword -> regex fragment (accent-folded, whole-word bounded). A bare-word… (+13 more)

### Community 33 - "Community 33"
Cohesion: 0.15
Nodes (21): case_ack(), _case_or_404(), case_update(), cases_list(), CaseUpdateBody, BaseModel, Case, get (+13 more)

### Community 34 - "Community 34"
Cohesion: 0.13
Nodes (21): _count_audit(), _count_settings(), _insert_user(), T4.1 integration tests — settings KV service + semantic accessors. Scenarios…, Unset categories resolve as bot_resolve; reading never creates a row., EM-1 expressions present by default; no row materialized until set., Content defaults live in the chat nodes; accessor only overrides., scope_rules and emergency.keywords writes each record an audit entry. (+13 more)

### Community 35 - "Community 35"
Cohesion: 0.11
Nodes (16): Card(), CardProps, Admin, Matrix, meta, Operador, Story, Matrix() (+8 more)

### Community 36 - "Community 36"
Cohesion: 0.14
Nodes (14): CASE_STATUSES, CasesListEmpty(), CasesListView(), columns, Default, Empty, meta, Story (+6 more)

### Community 37 - "Community 37"
Cohesion: 0.17
Nodes (19): _after_capture(), _after_cost_gate(), _after_emergency_gate(), _after_handoff_gate(), _after_respond(), build_graph(), _flow_start(), ConversationState (+11 more)

### Community 38 - "Community 38"
Cohesion: 0.12
Nodes (21): list_audit_entries(), Session, Insert one append-only audit entry and return it (caller commits)., Admin read: newest entries first (SH-5 — admin-only at the app layer)., record_audit(), ingest_document(), Session, Chunk + embed + insert kb_chunks for one document version; records cost. (+13 more)

### Community 39 - "Community 39"
Cohesion: 0.10
Nodes (21): clean_db(), client(), fake_embedder(), migrated_db(), mock_meta_send(), mock_openai_chat(), CompletedProcess, fixture (+13 more)

### Community 40 - "Community 40"
Cohesion: 0.21
Nodes (19): _doc_or_404(), kb_disable(), kb_edit(), kb_list(), kb_restore(), kb_upload(), get, post (+11 more)

### Community 41 - "Community 41"
Cohesion: 0.10
Nodes (19): ES2023, vite.config.ts, compilerOptions, composite, isolatedModules, lib, module, moduleDetection (+11 more)

### Community 42 - "Community 42"
Cohesion: 0.26
Nodes (19): logged_client(), _login_oper(), fixture, spec, Clients + conversations panel views (T5.2; AP-3, AP-4, CR-3, CR-4, CR-5).…, A TestClient already authenticated as an operador., Create a customer with one conversation, `messages` messages and a case., _seed_customer() (+11 more)

### Community 43 - "Community 43"
Cohesion: 0.10
Nodes (19): Case, CasesResponse, ClientFichaResponse, Conversation, ConversationThread, Customer, CustomerNote, CustomerState (+11 more)

### Community 44 - "Community 44"
Cohesion: 0.18
Nodes (14): cost_gate node (SS-3; design: deterministic gate before any LLM). Runs on EVERY…, _protocol_replies(), emergency node (EM-2, EM-3; T4.2, weak path migrated in T4.4). Runs ONLY via…, EM-3: safety instructions + contacts + technician-notified blocks., handoff node — deriva bundle + human takeover (HH-1, HH-2, HH-3; T4.4). Reached…, Receive node — first-contact greeting + menu (CM-1). Deterministic (no LLM):…, ConversationState, greeting_with_menu() (+6 more)

### Community 45 - "Community 45"
Cohesion: 0.15
Nodes (18): _current_message(), evaluate_handoff(), handoff_gate(), ConversationState, handoff_gate node — deterministic pre-LLM escalation triggers (HH-3, T4.4).…, Store the deterministic trigger reason for the graph router., Deterministic pre-LLM trigger evaluation; returns the reason or None., _gate_state() (+10 more)

### Community 46 - "Community 46"
Cohesion: 0.22
Nodes (19): Conversation Manager, Emergency Detection, HH-5 Human Response Channel, Human Handoff, Emergency Detection Specification, Settings and Scope Limits Specification, CM-4 Authorized Technical Guidance, EM-1 Deterministic Keyword Detection (+11 more)

### Community 47 - "Community 47"
Cohesion: 0.18
Nodes (16): classify_intent(), _current_text(), is_injection(), _llm_classify(), ConversationState, classify_intent node (CM-3, HH-3 partial, SH-4 partial). LLM classification…, Persist one unknown-intent attempt; returns the NEW total (HH-3)., Classify the current message; sets intent/case/unknown/escalate flags. (+8 more)

### Community 48 - "Community 48"
Cohesion: 0.21
Nodes (17): Apply Progress, Autodocs, Batch B10, Batch B9, Design: Panel Design System, Doc-Level Stories, Drift Guard, Proposal: Panel Design System (+9 more)

### Community 49 - "Community 49"
Cohesion: 0.21
Nodes (15): _answer_consent(), _apply_consent_and_customer(), capture(), _current_text(), is_skip(), _next_field_after(), _persist_captured(), ConversationState (+7 more)

### Community 50 - "Community 50"
Cohesion: 0.19
Nodes (15): _audit(), login(), LoginBody, logout(), me(), BaseModel, get, post (+7 more)

### Community 51 - "Community 51"
Cohesion: 0.20
Nodes (12): BubbleVariant, ConversationThreadBubbles(), ConversationThreadView(), customer, Default, messageColumns, meta, Story (+4 more)

### Community 52 - "Community 52"
Cohesion: 0.30
Nodes (14): _number(), _pop_flash(), get, Request, Settings panel views (T5.4; SS-1..5, SH-5). Admin-only (require_admin — AP-2…, Parse a decimal form value; reject invalid/negative input loudly., _save(), settings_keywords() (+6 more)

### Community 53 - "Community 53"
Cohesion: 0.20
Nodes (15): Meta WhatsApp Cloud API, OpenAI API, WhatsApp Webhook Specification, LumatAgent README, SS-4 Cost Tracking and Meta Pricing Awareness, WH-1 Verify Handshake, WH-2 Signature Verification, WH-3 Immediate 200 (+7 more)

### Community 54 - "Community 54"
Cohesion: 0.33
Nodes (14): _login_oper(), spec, Cases panel view (T5.3; HH-4, AP-5, EM-4 ack). Functional suite: the…, Create customer + conversation + one case; returns the case id., Create the operador (once) and log in; returns the user id., _seed_case(), test_ack_button_hidden_after_ack(), test_ack_button_records_ack_and_audits() (+6 more)

### Community 55 - "Community 55"
Cohesion: 0.19
Nodes (10): Badge(), BadgeProps, BadgeTone, Status, StatusBadge(), statusTone, Escalated, Matrix (+2 more)

### Community 56 - "Community 56"
Cohesion: 0.15
Nodes (12): Select(), SelectOption, SelectProps, options, Default, Disabled, Matrix, meta (+4 more)

### Community 57 - "Community 57"
Cohesion: 0.22
Nodes (9): DashboardOverview(), meta, Overview, Story, kpis, PageHeader(), PageHeaderProps, StatCard() (+1 more)

### Community 58 - "Community 58"
Cohesion: 0.19
Nodes (10): columns, Default, Empty, KbListEmpty(), KbListView(), meta, Story, docs (+2 more)

### Community 59 - "Community 59"
Cohesion: 0.14
Nodes (14): Any, Upsert one setting and audit the change (SH-5). The caller commits., set_setting(), Settings, No row / malformed dict -> the reference default (SS-4, pre-2026-10-01)., test_meta_message_cost_falls_back_to_reference_default(), test_meta_message_cost_uses_stored_settings_value(), One category set to always_escalate; other categories keep the default. (+6 more)

### Community 60 - "Community 60"
Cohesion: 0.20
Nodes (14): _escalate_reason(), handoff(), ConversationState, Label the escalation: post-classification reason > gate trigger., Escalate to a human: deriva bundle + state -> human + reply + audit., generate_summary(), ConversationState, LLM summary persisted on conversation + case (CM-5); returns the text. Shared… (+6 more)

### Community 61 - "Community 61"
Cohesion: 0.22
Nodes (13): build_deriva_bundle(), create_handoff_case(), get_or_create_case(), list_open_cases(), ConversationState, Session, Cases service (HH-2 deriva; design: app/services/cases.py). Formal replacement…, HH-4: pending/escalated cases (open, not closed), escalated first. The panel… (+5 more)

### Community 62 - "Community 62"
Cohesion: 0.18
Nodes (13): chunk_text(), _csv_rows_to_text(), _embed_cost(), embed_texts(), extract_text(), get_embedder(), Decimal, Knowledge base pipeline (KB-1..KB-4; design "KB Pipeline"). Ingest (PDF/MD/CSV)… (+5 more)

### Community 63 - "Community 63"
Cohesion: 0.14
Nodes (13): command, _description, enabled, type, mcp, graphify, plugin, $schema (+5 more)

### Community 64 - "Community 64"
Cohesion: 0.19
Nodes (10): _load_compose(), T1.3 integration tests — local dev env (compose + .env.example, SH-2). Static…, SH-2: secrets never in repo — .env.example carries placeholders only., Deploy scripts must be executable IN THE GIT INDEX (100755), not just in the…, test_api_service_wires_health_endpoint_port(), test_compose_declares_db_media_backups_volumes(), test_compose_defines_api_and_db_services(), test_db_service_uses_pgvector_image() (+2 more)

### Community 65 - "Community 65"
Cohesion: 0.18
Nodes (10): FieldShell(), FieldShellProps, Textarea(), TextareaProps, Default, Disabled, Matrix, meta (+2 more)

### Community 66 - "Community 66"
Cohesion: 0.18
Nodes (9): columns, ConversationsListEmpty(), ConversationsListView(), Default, Empty, meta, Story, EmptyState() (+1 more)

### Community 67 - "Community 67"
Cohesion: 0.21
Nodes (9): Default, meta, SettingsView(), Story, FlashMessage(), FlashMessageProps, settings, SETTINGS_KEYS (+1 more)

### Community 68 - "Community 68"
Cohesion: 0.15
Nodes (13): Chatbot vs LumatAgent Comparison Table, Content Cleanliness, Mermaid Diagrams — 4 Required, Multi-Agent Architecture Explanation, Option Naming Convention, Output Artifacts, Quality Standards, Document Structure — 21 Sections (+5 more)

### Community 69 - "Community 69"
Cohesion: 0.30
Nodes (12): Admin Panel, Admin Panel Specification, AP-1 Authentication, AP-2 Roles and Permissions, AP-3 Clients List and Search, AP-4 Conversation View, AP-5 Cases View, AP-6 KB Manager Access (+4 more)

### Community 70 - "Community 70"
Cohesion: 0.21
Nodes (11): _current_text(), emergency_gate(), ConversationState, emergency_gate node (EM-1, EM-2, EM-5; design: gate before any LLM).…, Classify the current message; store `emergency_hit` for the router. A weak hit…, get_emergency_keywords(), get_message(), Session (+3 more)

### Community 71 - "Community 71"
Cohesion: 0.24
Nodes (12): Customer Records, Customer Records Specification, CM-2 Progressive Structured Data Capture, CR-1 Auto-Ficha on First Contact, CR-2 Phone-Based Deduplication, CR-3 Lifecycle States, CR-4 Internal Notes, CR-5 History Linkage (+4 more)

### Community 72 - "Community 72"
Cohesion: 0.23
Nodes (11): _count(), CompletedProcess, T7.2 integration tests — db/seed.sh (design deploy step 4). Runs the seed…, Run db/seed.sh against the test DB with a fixed admin bootstrap env., Two runs: settings/users inserted once, audit_log untouched on re-run., The seeded rows match SETTINGS_DEFAULTS and the admin verifies (AP-1)., Missing PANEL_ADMIN_PASSWORD fails loudly instead of seeding silently., _run_seed() (+3 more)

### Community 73 - "Community 73"
Cohesion: 0.20
Nodes (9): Button(), ButtonProps, Disabled, Link, Matrix, meta, Primary, Secondary (+1 more)

### Community 74 - "Community 74"
Cohesion: 0.20
Nodes (9): Input(), InputProps, Default, Disabled, Matrix, meta, Small, Story (+1 more)

### Community 75 - "Community 75"
Cohesion: 0.22
Nodes (9): GROUP_RULES, groups, groupToken(), meta, Overview, sample(), Story, tokens (+1 more)

### Community 76 - "Community 76"
Cohesion: 0.20
Nodes (10): kpis(), get, Session, User, Dashboard KPI counts over the configured window (AP-8)., compute_kpis(), panel_home(), get (+2 more)

### Community 77 - "Community 77"
Cohesion: 0.27
Nodes (7): Avatar(), AvatarProps, initials(), Initials, Matrix, meta, Story

### Community 78 - "Community 78"
Cohesion: 0.27
Nodes (6): radius, spacing, componentsRoot, tokensRaw, zIndex, preview

### Community 79 - "Community 79"
Cohesion: 0.31
Nodes (9): DocumentFormat, KbDocument, DocEditBody, DocRestoreBody, BaseModel, One retrieval result (KB-2)., RetrievedChunk, kb_chunks.embedding vector(384) round-trips via ORM (KB-1). (+1 more)

### Community 80 - "Community 80"
Cohesion: 0.36
Nodes (8): _csv_response(), _csv_stream(), export_cases(), export_clients(), get, CSV export (T5.5; AP-7). GET /panel/export/clients.csv — clients with the…, Yield CSV lines from a row iterable (stdlib csv, streaming)., StreamingResponse

### Community 81 - "Community 81"
Cohesion: 0.22
Nodes (9): Base Layout Template, Cases List Template, Client Ficha Template, Clients List Template, Conversation Thread Template, Dashboard Template, Knowledge Base List Template, Login Template (+1 more)

### Community 82 - "Community 82"
Cohesion: 0.22
Nodes (9): Docker Compose, Hostinger KVM 2 (São Paulo), LangGraph, OpenSpec Project Config, PostgreSQL, CM-1 Single-Agent Flow with Menu, HH-1 Per-Conversation State Model, 8-Category Menu (+1 more)

### Community 83 - "Community 83"
Cohesion: 0.22
Nodes (9): Append an inbound message and run the graph (replies persisted)., EM-2: a strong hit abandons the capture flow and runs the protocol., EM-5: ambiguous risk escalates to a human, never ignored. T4.4: the weak path…, EM-1 'Keyword configured': a settings change applies on the next message., test_benign_text_passes_through_normal_flow(), test_custom_keyword_from_settings_detected(), test_strong_hit_mid_capture_interrupts(), test_weak_hit_escalates_to_human() (+1 more)

### Community 84 - "Community 84"
Cohesion: 0.28
Nodes (6): SearchInput(), SearchInputProps, Default, Matrix, meta, Story

### Community 85 - "Community 85"
Cohesion: 0.28
Nodes (6): Default, Error, LoginDefault(), LoginError(), meta, Story

### Community 86 - "Community 86"
Cohesion: 0.32
Nodes (7): pg_enum(), datetime, ORM models mapping the migrated schema (design Data Model, 10 tables). The…, PG-native Enum that stores the *member values* (labels in 001_init.sql).…, _ts(), Enum, Mapped

### Community 87 - "Community 87"
Cohesion: 0.39
Nodes (7): case_ack(), _case_or_404(), case_update(), cases_list(), get, Request, Cases panel view (T5.3; HH-4, AP-5, EM-4 ack). GET /panel/cases ->…

### Community 88 - "Community 88"
Cohesion: 0.39
Nodes (8): Knowledge Base, Knowledge Base Specification, pgvector, CM-6 Unresolved Response Logging, KB-1 Ingestion Pipeline, KB-2 Semantic Retrieval, KB-3 KB Manager, KB-4 Versioning and Re-Ingestion

### Community 89 - "Community 89"
Cohesion: 0.33
Nodes (7): _conversation_or_404(), conversation_thread(), Conversation, get, Session, User, Conversation metadata + chronological messages (media as URL links).

### Community 90 - "Community 90"
Cohesion: 0.43
Nodes (7): Conversation Manager Specification, Human Handoff Specification, CM-3 Intent and Case Classification, CM-5 Conversation Summary, HH-2 Deriva with History and Summary, HH-5 Human Response Channel (H1), Case Record

### Community 91 - "Community 91"
Cohesion: 0.48
Nodes (7): Security Hardening Specification, SH-1 Network and Access Hardening, SH-2 Container and Secrets Hardening, SH-3 Backups and Monitoring, SH-4 Prompt-Injection Mitigations, SH-5 Audit Log, Security Hardening

### Community 92 - "Community 92"
Cohesion: 0.33
Nodes (5): Column, DataTable(), DataTableProps, COLUMNS, Row

### Community 93 - "Community 93"
Cohesion: 0.40
Nodes (6): _current_text(), log_unresolved(), Answer the current message: clarification / KB-grounded / cannot-answer., CM-6: mark an inbound message as unresolved (question+context+ts)., respond(), ConversationState

### Community 94 - "Community 94"
Cohesion: 0.40
Nodes (5): download_media(), Filesystem-safe filename stem derived from the wamid., Download a Meta media URL to the media volume; raise on failure. Meta lookaside…, _safe_filename(), Path

### Community 95 - "Community 95"
Cohesion: 0.40
Nodes (5): clean_db(), fake_embedder(), fixture, Inject a deterministic 384-d embedder; counts `.embed` calls., Reset KB tables before every test (shared test DB).

### Community 96 - "Community 96"
Cohesion: 0.50
Nodes (3): APP_DB_PASSWORD, DATABASE_URL, migrate.sh script

### Community 97 - "Community 97"
Cohesion: 0.50
Nodes (3): DATABASE_URL, SEED_REPO_ROOT, seed.sh script

### Community 98 - "Community 98"
Cohesion: 0.50
Nodes (4): Derivacion a atencion humana, Ficha del cliente y registro de conversaciones, Milestone 1 - Bot IA de atencion al cliente, Panel de administracion (M1)

### Community 99 - "Community 99"
Cohesion: 0.67
Nodes (3): emergency(), ConversationState, Run the safety protocol (EM-3). The gate only routes strong hits here.

### Community 100 - "Community 100"
Cohesion: 0.67
Nodes (3): ConversationState, Handle the incoming message at the start of the graph run. `state.turn` counts…, receive()

### Community 101 - "Community 101"
Cohesion: 0.67
Nodes (3): Base, Declarative base for all ORM models (mapped to the migrated schema)., DeclarativeBase

### Community 102 - "Community 102"
Cohesion: 0.67
Nodes (3): get_tone(), SS-5: tone style (`tone.style`), default `warm-professional`., test_tone_override()

### Community 104 - "Community 104"
Cohesion: 0.67
Nodes (3): clean_db(), fixture, Reset all customer-related tables before every test (shared test DB).

### Community 105 - "Community 105"
Cohesion: 0.67
Nodes (3): clean_db(), fixture, Reset all tables before this module's tests (dedicated test DB only).

### Community 106 - "Community 106"
Cohesion: 0.67
Nodes (3): clean_db(), fixture, Reset chat + settings tables before every test (shared test DB).

### Community 107 - "Community 107"
Cohesion: 0.67
Nodes (3): clean_db(), fixture, Reset chat + settings tables before every test (shared test DB).

### Community 108 - "Community 108"
Cohesion: 0.67
Nodes (3): clean_db(), fixture, Reset settings, audit_log and users before every test (shared test DB).

## Ambiguous Edges - Review These
- `Graphify Knowledge Graph (636 nodes / 1211 edges / 39 communities)` → `Strict TDD Compliance (7/7 checks)`  [AMBIGUOUS]
  openspec/changes/hito-1-setup-whatsapp/verify-report.md · relation: conceptually_related_to

## Knowledge Gaps
- **362 isolated node(s):** `GateState`, `NavEntry`, `View`, `Case`, `CasesResponse` (+357 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **63 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.