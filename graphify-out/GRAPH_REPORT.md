# Graph Report - .  (2026-08-20)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2489 nodes · 5348 edges · 183 communities (145 shown, 38 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 231 edges (avg confidence: 0.69)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d8f26896`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- services/kb.py
- test_webhook_ingest.py
- get_or_create_customer
- api/routes/auth.py
- Hito 1 change — Setup + WhatsApp operativo
- get_setting
- test_emergency_notify.py
- post_message
- ADDED Requirements
- models.py
- test_emergency.py
- CasesList.stories.tsx
- test_cost_guardrails.py
- InboxThread.stories.tsx
- _seed_conv_costs
- Message
- test_auth.py
- H1 — Setup + WhatsApp Operativo (Tasks)
- make_user
- User
- ClientFicha.stories.tsx
- record_audit
- notify.py
- get_settings
- test_api_auth.py
- compilerOptions
- ChatWithAgent.stories.tsx
- tests/conftest.py
- test_api_clients.py
- Textarea.tsx
- graph.py
- sweep_received
- test_api_cases.py
- types.ts
- test_kb_settings.py
- test_chat_intent.py
- test_migrations.py
- state.py
- panel/routes/kb.py
- test_chat_capture.py
- api/routes/clients.py
- Dashboard.stories.tsx
- test_send_costs.py
- ingest.py
- Login.stories.tsx
- Settings.stories.tsx
- matrix.tsx
- test_chat_state.py
- compilerOptions
- ConversationsList.stories.tsx
- db.py
- test_handoff.py
- AuditLog
- case_update
- Conversation Manager
- devDependencies
- test_clients.py
- customers.py
- router.py
- KbList.stories.tsx
- classify_intent.py
- respond.py
- conversation_thread
- WhatsApp Webhook
- test_api_conversations.py
- panel/routes/clients.py
- test_cases.py
- Select.stories.tsx
- summary.py
- Lumat Panel Design System
- command
- test_infra.py
- capture.py
- Propuesta Técnica y Económica Lumat
- Proposal: Panel H2/H4 UI Advance (Inbox + Chat)
- Verification Report
- AppShell.tsx
- Tokens.stories.tsx
- Admin Panel
- Customer Records
- Design: Panel H2/H4 UI Advance (Inbox + Chat)
- login
- test_seed.py
- panel/routes/cases.py
- Archive Report: Panel H2/H4 UI Advance (Inbox + Chat)
- Tasks: Panel H2/H4 UI Advance
- app.tsx
- AppShell.stories.tsx
- cortex-persona SKILL.md
- kpis
- Tasks: Propuesta Técnica y Económica Lumat
- Verification Report
- tokens.test.ts
- get_current_user_json
- Base Layout Template
- OpenSpec Project Config
- archive-report.md
- test_webhook_verify.py
- get_or_create_conversation
- add_note
- clean_db
- Knowledge Base
- scripts
- _csv_response
- Design: Panel Design System
- Requirement: R-PRD-PG-14 — Conversation State Domain
- Tasks: Panel H2/H4 UI Advance (Inbox + Chat)
- Conversation Manager Specification
- Security Hardening
- run_migrate
- package.json
- PanelEntry.stories.tsx
- Ponytail Review (diff over-engineering)
- dependencies
- migrate.sh
- seed.sh
- Milestone 1 - Bot IA de atencion al cliente
- conversation_thread
- monitor.sh
- Verify Report: Panel Real Design
- Design: Panel Real Design
- logged_client
- clean_db
- app/__init__.py
- api/routes/__init__.py
- webhook/__init__.py
- Graphify Knowledge Graph (636 nodes / 1211 edges / 39 communities)
- backup.sh
- restore-test.sh
- tasks.md (33 tasks, traceability)
- B1 Spec Compliance Matrix
- B2 Spec Compliance Matrix
- B3 Spec Compliance Matrix
- @testing-library/react
- @testing-library/user-event
- test_kb_endpoints_require_login_401_json
- vitest
- main.ts
- app/chat/nodes/ — chat node modules
- app/panel/* — admin panel routes/templates
- Chat Manager (CM-1..6)
- Customer Records (CR-1..6)
- Design D2: no checkpointer, state rebuild from DB
- Design D6: cost on messages columns + SQL SUM
- Design D8: versioning restore = active_version flip
- Knowledge Base Pipeline (KB-1/2/4)
- WhatsApp Webhook Pipeline (WH-1..7)
- db/migrations/*.sql (001_init, 002_customer_notes, 003_captured_data)
- Doc-Level Story Upgrades (all 10 files)
- Token Drift Guard + no-hard-coded-hex walk
- Propuesta Lumat — Entrega 1 (Resumen Ejecutivo)
- Docker Compose (api + pgvector, volumes, healthcheck)
- Milestone 2 - Pagina web Lumat
- Milestone 3 - Servicios, agendamiento e integraciones
- Proposal: Panel Real Design — Page-First Storybook Workflow
- lumatagent
- tests/functional/ — CM/CR/AP suite
- tests/injection/ — SH-4 suite
- Token Foundation (type/focus/motion/breakpoints/shadow)
- Index HTML (Lumat Panel root)

## God Nodes (most connected - your core abstractions)
1. `make_user()` - 79 edges
2. `Message` - 77 edges
3. `Conversation` - 60 edges
4. `Customer` - 55 edges
5. `get_or_create_customer()` - 55 edges
6. `_post()` - 46 edges
7. `record_audit()` - 40 edges
8. `Case` - 39 edges
9. `User` - 36 edges
10. `get_or_create_conversation()` - 34 edges

## Surprising Connections (you probably didn't know these)
- `LumatAgent Project` --shares_data_with--> `Engram persistent memory`  [INFERRED]
  README.md → .opencode/skills/cortex-session/SKILL.md
- `LumatAgent README` --references--> `PostgreSQL`  [EXTRACTED]
  README.md → openspec/config.yaml
- `_seed_case()` --calls--> `Case`  [EXTRACTED]
  tests/functional/test_api_cases.py → app/models.py
- `test_cases_list_orders_by_escalated_at_within_same_status()` --calls--> `Case`  [EXTRACTED]
  tests/functional/test_api_cases.py → app/models.py
- `test_cases_list_skips_closed_cases()` --calls--> `Case`  [EXTRACTED]
  tests/functional/test_api_cases.py → app/models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **H1 spec requirement areas mapped to task batches (traceability)** — openspec_changes_hito_1_setup_whatsapp_tasks_wh, openspec_changes_hito_1_setup_whatsapp_tasks_cm, openspec_changes_hito_1_setup_whatsapp_tasks_cr, openspec_changes_hito_1_setup_whatsapp_tasks_kb, openspec_changes_hito_1_setup_whatsapp_tasks_em, openspec_changes_hito_1_setup_whatsapp_tasks_hh, openspec_changes_hito_1_setup_whatsapp_tasks_ap, openspec_changes_hito_1_setup_whatsapp_tasks_ss, openspec_changes_hito_1_setup_whatsapp_tasks_sh [EXTRACTED 0.85]
- **Lumat brand primitives and operational primary color system** — brand_lime, brand_cyan, brand_aqua, brand_forest, brand_graphite, primary_800_token [EXTRACTED 0.85]
- **B3 Verified Spec Families (CR, CM, KB, HH, SH, SS)** — concept_cr_family, concept_cm_family, concept_kb_pipeline, concept_sh_security, openspec_changes_hito-1-setup-whatsapp_verify-report__spec_compliance_b3 [EXTRACTED 0.90]
- **Cortex workflow (Graphify gate + Ponytail + SDD)** — opencode_skills_cortex_persona_skill_graphify, opencode_skills_cortex_persona_skill_graph_check, opencode_skills_cortex_persona_skill_ponytail_rules, opencode_skills_cortex_persona_skill_execution_gate, opencode_skills_cortex_persona_skill_sdd_pipeline, opencode_skills_cortex_persona_skill_engram [EXTRACTED 0.90]
- **SH-1..SH-5 security hardening checklist executed on rehearsal VM** — docs_hardening, docs_hardening_sh1, docs_hardening_sh2, docs_hardening_sh5, infra_docker_compose_prod_yml [EXTRACTED 0.90]
- **Ponytail minimal-code skill family (ladder YAGNI→stdlib→native→one line)** — opencode_skills_ponytail_audit, opencode_skills_ponytail_debt, opencode_skills_ponytail_help, opencode_skills_ponytail_plan, opencode_skills_ponytail_review [EXTRACTED 0.90]
- **Admin Panel Jinja Template Set (base + 8 views)** — app_panel_templates_base, app_panel_templates_dashboard, app_panel_templates_login, app_panel_templates_cases_list, app_panel_templates_clients_ficha, app_panel_templates_clients_list, app_panel_templates_conversations_thread, app_panel_templates_kb_list, app_panel_templates_settings_index [EXTRACTED 0.95]
- **Cortex skill pack bootstrap workflow** — opencode_commands_cortex_init_command, opencode_commands_cortex_init_script, cortex_skill_pack, graphify_knowledge_graph, cortex_skill_registry, sdd_init_command [EXTRACTED 1.00]
- **H1 technical stack** — fastapi_app, langgraph_graph, postgres_pgvector, docker_compose_infra, hostinger_kvm2_vps, meta_cloud_api [EXTRACTED 1.00]
- **Panel Design System SDD Change Cycle** — openspec_changes_archive_2026_08_19_panel_design_system_proposal, openspec_changes_archive_2026_08_19_panel_design_system_design, openspec_changes_archive_2026_08_19_panel_design_system_tasks, openspec_changes_archive_2026_08_19_panel_design_system_apply_progress, openspec_changes_archive_2026_08_19_panel_design_system_verify_report, openspec_changes_archive_2026_08_19_panel_design_system_archive_report, openspec_changes_archive_2026_08_19_panel_design_system_specs_panel_design_system_spec [EXTRACTED 1.00]
- **Propuesta PDF build pipeline** — propuesta_build_script, mmdc_mermaid_cli, headless_chrome_render, md_to_pdf_engine, propuesta_main_document [EXTRACTED 1.00]
- **Case Record Lifecycle Across Specs** — shared_case_record [INFERRED 0.85]
- **Inbound WhatsApp Message Pipeline** — whatsapp-webhook_whatsapp-webhook, conversation-manager_conversation-manager, emergency-detection_emergency-detection, human-handoff_human-handoff [INFERRED 0.85]

## Communities (183 total, 38 thin omitted)

### Community 0 - "services/kb.py"
Cohesion: 0.05
Nodes (78): DocumentFormat, KbChunk, KbDocument, _doc_or_404(), DocEditBody, DocRestoreBody, kb_disable(), kb_edit() (+70 more)

### Community 1 - "test_webhook_ingest.py"
Cohesion: 0.08
Nodes (63): KeywordsBody, LimitsBody, MetaBody, _number(), _parse_scope(), BaseModel, get, Session (+55 more)

### Community 2 - "get_or_create_customer"
Cohesion: 0.19
Nodes (19): get_or_create_customer(), Customer, CustomerState, Return the ficha for `phone`, creating it on first contact (CR-1/CR-2). The…, Transition a customer to `new_state`; reject invalid CR-3 transitions. Records…, set_customer_state(), _count_customers(), T3.1 integration tests — customers service (CR-1..CR-6). Scenarios mapped 1:1… (+11 more)

### Community 3 - "api/routes/auth.py"
Cohesion: 0.12
Nodes (28): _audit(), login(), LoginBody, logout(), me(), BaseModel, get, Request (+20 more)

### Community 4 - "Hito 1 change — Setup + WhatsApp operativo"
Cohesion: 0.07
Nodes (45): admin-panel capability, arquitectura-lumatagent.md (diagrams source), conversation-manager capability, Cortex session report.md, Cortex skill pack, Cortex skill registry (.atl/skill-registry.md), Cost guardrails (spend limits + alerts), cotizacion-lumat.md (pricing source of truth) (+37 more)

### Community 5 - "get_setting"
Cohesion: 0.08
Nodes (43): Any, get_message(), get_setting(), get_tone(), Session, Read one setting: stored value > built-in default > caller default., Upsert one setting and audit the change (SH-5). The caller commits., SS-5: tone style (`tone.style`), default `warm-professional`. (+35 more)

### Community 6 - "test_emergency_notify.py"
Cohesion: 0.09
Nodes (42): acknowledge_emergency_if_ack(), is_ack_message(), True when the customer's reply is a pure ack-keyword message. "ok" / "listo" /…, Record the customer reply-keyword ack on the emergency case (T4.3.2).…, _audit_rows(), _call_notification(), _capturing_smtp(), clean_db() (+34 more)

### Community 7 - "post_message"
Cohesion: 0.09
Nodes (40): _conversation(), _last_outbound(), _outbound_texts(), Customer, Message, spec, T6.2 functional tests — conversation-manager flows over the webhook (CM-1..6).…, Full capture: each answer stored, skip on evidence, consent -> ficha. (+32 more)

### Community 8 - "ADDED Requirements"
Cohesion: 0.05
Nodes (42): panel-h2-advance delta spec, ADDED Requirements, Delta for panel-h2-advance, Requirement: R-PRD-PG-10 — 24-Hour Reply Window, Requirement: R-PRD-PG-11 — Chat With Agent Page, Requirement: R-PRD-PG-12 — Dedicated Chat & Assignee Mock Shapes, Requirement: R-PRD-PG-13 — Verification Gates & Boundary Guards, Requirement: R-PRD-PG-8 — Inbox List: State, Assignee & Filter (+34 more)

### Community 9 - "models.py"
Cohesion: 0.09
Nodes (36): Base, Declarative base for all ORM models (mapped to the migrated schema)., ConversationState, CustomerState, MessageDirection, MessageStatus, MessageType, pg_enum() (+28 more)

### Community 10 - "test_emergency.py"
Cohesion: 0.10
Nodes (35): classify_emergency(), compile_keywords(), fold_accents(), _keyword_fragment(), Emergency detection service (EM-1..EM-5, SS-2; design:…, Classify one message: ``"strong"`` | ``"weak"`` | None (no hit). ``pattern`` is…, Lowercase + fold accents to ASCII base letters ("Explosión" -> "explosion")., One keyword -> regex fragment (accent-folded, whole-word bounded). A bare-word… (+27 more)

### Community 11 - "CasesList.stories.tsx"
Cohesion: 0.09
Nodes (24): Badge(), BadgeProps, BadgeTone, CASE_STATUSES, CasesListEmpty(), CasesListView(), columns, Default (+16 more)

### Community 12 - "test_cost_guardrails.py"
Cohesion: 0.11
Nodes (35): _append(), _audit_actions(), _capturing_smtp(), clean_db(), no_real_smtp(), fixture, T4.5 integration tests — cost guardrails (SS-3, SS-4). Scenarios mapped from…, Audit actions limited to the cost-alert surface (seed noise excluded). (+27 more)

### Community 13 - "InboxThread.stories.tsx"
Cohesion: 0.09
Nodes (27): BubbleVariant, ConversationThreadBubbles(), ConversationThreadView(), customer, Default, messageColumns, meta, Story (+19 more)

### Community 14 - "_seed_conv_costs"
Cohesion: 0.10
Nodes (35): cost_gate(), ConversationState, Evaluate spend states, alert the owner on crossings, flag cost_mode., combined_cost_mode(), conversation_cost_state(), conversation_spend(), daily_cost_state(), daily_spend() (+27 more)

### Community 15 - "Message"
Cohesion: 0.10
Nodes (45): Case, Conversation, Customer, CustomerNote, Message, Internal staff note on a customer ficha (CR-4; 002_customer_notes.sql). Staff-…, Panel JSON API serializers (B2/T2.1+T2.2; PDW-API, D4). ORM rows -> plain dicts…, Cases service (HH-2 deriva; design: app/services/cases.py). Formal replacement… (+37 more)

### Community 16 - "test_auth.py"
Cohesion: 0.10
Nodes (34): _audit_actions(), CompletedProcess, spec, User, Panel authentication + roles (T5.1; AP-1, AP-2, SH-5). Functional suite over…, No such user -> generic error + audit row, nothing else leaks., 5 failed attempts -> locked_until set; correct password then rejected., After locked_until passes, a correct login succeeds (15-min ban ends). (+26 more)

### Community 17 - "H1 — Setup + WhatsApp Operativo (Tasks)"
Cohesion: 0.07
Nodes (34): Security Hardening (SH-1..5), Hardening Checklist (SH-1/2/3 executable), SH-1 Network/Access Hardening, SH-2 Container/Secrets Hardening, SH-5 Audit Log Append-Only, Ops Runbook & Meta Onboarding Checklist, Backup Restore Drill, Deploy Flow (tag + compose restart) (+26 more)

### Community 18 - "make_user"
Cohesion: 0.16
Nodes (32): make_user(), Factory creating a panel user row directly (bcrypt hash) in a session., _doc_version(), _last_audit(), _login(), Panel JSON API KB + settings (B4/T4.1+T4.2; PDW-API-1/2/3/4, D1, D4). Admin-…, Seed a KB document through the service path (v1, embedded)., Limit validation mirrors the Jinja _number guard (SS-3): >= 0. (+24 more)

### Community 19 - "User"
Cohesion: 0.12
Nodes (27): User, Panel JSON API auth dependencies (design D4; PDW-AUTH-1, PDW-API-4). Parallel…, Any authenticated user (admin or operador) — shared JSON routes., require_user_json(), Panel JSON API package (design D4; PDW-API, PDW-AUTH). Additive JSON layer…, Panel JSON API cases (B3/T3.2; PDW-API, PDW-API-3, D4, D8). Thin JSON wrappers…, Panel JSON API conversations (B3/T3.1; PDW-API, PDW-API-3, D4). Thin JSON…, Panel JSON API dashboard (B2/T2.1; PDW-API, PDW-AUTH-1, D4). GET… (+19 more)

### Community 20 - "ClientFicha.stories.tsx"
Cohesion: 0.09
Nodes (25): ClientesListEmpty(), ClientesListView(), columns, Default, Empty, Loading, meta, Story (+17 more)

### Community 21 - "record_audit"
Cohesion: 0.09
Nodes (27): emergency(), _protocol_replies(), ConversationState, emergency node (EM-2, EM-3; T4.2, weak path migrated in T4.4). Runs ONLY via…, EM-3: safety instructions + contacts + technician-notified blocks., Run the safety protocol (EM-3). The gate only routes strong hits here., list_audit_entries(), Session (+19 more)

### Community 22 - "notify.py"
Cohesion: 0.12
Nodes (29): acknowledge_case(), _audit_notification(), _customer_location(), _notification_body(), Case, Conversation, Customer, Session (+21 more)

### Community 23 - "get_settings"
Cohesion: 0.09
Nodes (26): get_settings(), Application configuration. Settings are read from environment variables ONLY…, Environment-only application settings (design: app/config.py, D3, SH-2)., Return the cached settings instance (cleared in tests via cache_clear)., Settings, BaseSettings, api_login(), clean_db() (+18 more)

### Community 24 - "test_api_auth.py"
Cohesion: 0.09
Nodes (28): _audit_actions(), User, Panel JSON API authentication (B1/T1.2; PDW-AUTH-1/2/4, PDW-API-3, D1, D4). The…, Valid JSON credentials -> 200 {ok, role}, session cookie, audit., operador credentials -> same cookie, role=operador (triangulation)., Wrong password -> 401 JSON {"detail":"invalid credentials"}, audited., No such user -> same generic 401, nothing leaks (no user oracle)., 5 failures -> lock; even a correct password returns 401 "account locked". (+20 more)

### Community 25 - "compilerOptions"
Cohesion: 0.07
Nodes (27): DOM, DOM.Iterable, ES2022, node, src, vite/client, compilerOptions, erasableSyntaxOnly (+19 more)

### Community 26 - "ChatWithAgent.stories.tsx"
Cohesion: 0.10
Nodes (19): Avatar(), AvatarProps, initials(), AgentThinking, ChatWithAgentView(), Default, meta, roleLabel (+11 more)

### Community 27 - "tests/conftest.py"
Cohesion: 0.10
Nodes (26): classify_result_for(), clean_db(), client(), fake_embedder(), fake_embedding(), migrated_db(), mock_meta_send(), mock_openai_chat() (+18 more)

### Community 28 - "test_api_clients.py"
Cohesion: 0.16
Nodes (26): _customer_row(), _login(), Customer, CustomerState, Panel JSON API clients (B2/T2.2; PDW-API, PDW-API-3, PDW-AUTH-1, D1, D4). The…, Empty result is real (service filtered) — companion to the non-empty test., search_customers limit=100 honored by the API wrapper., Missing customer -> 404 {"detail":"customer not found"} (PDW-API-3). (+18 more)

### Community 29 - "Textarea.tsx"
Cohesion: 0.10
Nodes (19): FieldShell(), FieldShellProps, Input(), InputProps, Textarea(), TextareaProps, Default, Disabled (+11 more)

### Community 30 - "graph.py"
Cohesion: 0.14
Nodes (24): _after_capture(), _after_cost_gate(), _after_emergency_gate(), _after_handoff_gate(), _after_respond(), build_graph(), _flow_start(), persist_replies() (+16 more)

### Community 31 - "sweep_received"
Cohesion: 0.11
Nodes (23): create_app(), lifespan(), LumatAgent API application factory (design: app/main.py). `app = create_app()`…, Startup sweep: reprocess messages stuck in `received` (crash recovery). Rows…, Crash recovery: reset `processing` rows back to `received` at startup. The…, Process messages stuck in `received` (BackgroundTask + startup sweep). Claim…, reset_stale_processing(), sweep_received() (+15 more)

### Community 32 - "test_api_cases.py"
Cohesion: 0.16
Nodes (24): _case_row(), _login(), Case, datetime, Panel JSON API cases (B3/T3.2; PDW-API, PDW-API-3, PDW-AUTH-1, D1, D4, D8).…, No session -> every cases endpoint answers 401 JSON, never a 302., closed_at set -> case excluded from the open list (HH-4)., Among escalated cases, the newest escalation comes first. (+16 more)

### Community 33 - "types.ts"
Cohesion: 0.14
Nodes (18): CASE_KEYS, CASE_STATUSES, clients, CUSTOMER_STATES, users, Case, CasesResponse, ClientFichaResponse (+10 more)

### Community 34 - "test_kb_settings.py"
Cohesion: 0.17
Nodes (22): login(), Login helper: authenticate as the given user through the login form., admin_client(), _last_audit(), oper_client(), fixture, spec, KB manager + settings panel views (T5.4; AP-2, AP-6, KB-3, KB-4, SS-1..5,… (+14 more)

### Community 35 - "test_chat_intent.py"
Cohesion: 0.18
Nodes (22): _case_rows(), clean_db(), mock_chat(), Case, fixture, T3.4 integration tests — classify_intent + route nodes (CM-3, HH-3, SH-4).…, Seed a customer + open conversation + one inbound received message., Intercept OpenAI /chat/completions; captures requests for SH-4 checks. (+14 more)

### Community 36 - "test_migrations.py"
Cohesion: 0.09
Nodes (22): admin_conn(), app_conn(), clean_db(), fixture, T1.1 integration tests — schema migration + migrate.sh runner. Runs…, Acceptance: \\dt shows all tables (10 design tables + schema_migrations)., customers.phone_e164 UNIQUE (design Data Model, CR-2 dedup)., Partial unique index: inbound wamid dedup, outbound/other rows free (WH-5). (+14 more)

### Community 37 - "state.py"
Cohesion: 0.12
Nodes (21): cost_gate node (SS-3; design: deterministic gate before any LLM). Runs on EVERY…, _escalate_reason(), handoff(), ConversationState, handoff node — deriva bundle + human takeover (HH-1, HH-2, HH-3; T4.4). Reached…, Label the escalation: post-classification reason > gate trigger., Escalate to a human: deriva bundle + state -> human + reply + audit., ConversationState (+13 more)

### Community 38 - "panel/routes/kb.py"
Cohesion: 0.15
Nodes (27): flash(), Store a one-shot notice in the session (shown on the next page)., _doc_or_404(), kb_add(), kb_disable(), kb_edit(), kb_list(), kb_restore() (+19 more)

### Community 39 - "test_chat_capture.py"
Cohesion: 0.19
Nodes (21): list_unresolved_questions(), Message, CM-6 query (no dedicated SQL view — filter by payload flag)., clean_db(), _conversation_captured(), _customer(), fixture, T3.5 integration tests — capture / respond / summary / unresolved nodes.… (+13 more)

### Community 40 - "api/routes/clients.py"
Cohesion: 0.14
Nodes (25): client_add_note(), client_ficha(), client_state_change(), clients_list(), _customer_or_404(), NoteBody, BaseModel, Customer (+17 more)

### Community 41 - "Dashboard.stories.tsx"
Cohesion: 0.11
Nodes (18): DashboardOverview(), DashboardOverviewProps, DashboardState, Empty, FatalError, formatWindowStart(), Loading, meta (+10 more)

### Community 42 - "test_send_costs.py"
Cohesion: 0.14
Nodes (20): deliver_all_pending(), deliver_outbound(), Send every pending outbound message across conversations (sweep path)., Send one WhatsApp text message; returns the Meta wamid. Raises…, Send pending outbound rows of a conversation; record wamid + cost_meta. Only…, send_text(), clean_db(), fixture (+12 more)

### Community 43 - "ingest.py"
Cohesion: 0.13
Nodes (20): _change_is_message_event(), download_media(), _get_or_create_customer_and_conversation(), ingest_payload(), iter_inbound_messages(), _message_error_131051(), persist_message(), Webhook ingest pipeline (specs WH-3..WH-7; design "Webhook Pipeline"). Flow per… (+12 more)

### Community 44 - "Login.stories.tsx"
Cohesion: 0.12
Nodes (15): Button(), ButtonProps, Default, Error, LoginDefault(), LoginError(), meta, Story (+7 more)

### Community 45 - "Settings.stories.tsx"
Cohesion: 0.13
Nodes (14): Card(), CardProps, Default, meta, SettingsView(), Story, settings, SETTINGS_KEYS (+6 more)

### Community 46 - "matrix.tsx"
Cohesion: 0.12
Nodes (15): SearchInput(), SearchInputProps, Matrix(), Matrix, meta, Story, Warning, Default (+7 more)

### Community 47 - "test_chat_state.py"
Cohesion: 0.15
Nodes (17): Session, Rebuild the state from the DB for one message (D2, no checkpointer)., clean_db(), _inbound_count(), _outbound_texts(), fixture, T3.2 integration tests — conversation state + graph scaffold + receive node.…, The outbound reply from turn 1 is part of turn 2's context (D2). (+9 more)

### Community 48 - "compilerOptions"
Cohesion: 0.10
Nodes (19): ES2023, vite.config.ts, compilerOptions, composite, isolatedModules, lib, module, moduleDetection (+11 more)

### Community 49 - "ConversationsList.stories.tsx"
Cohesion: 0.15
Nodes (14): Status, StatusBadge(), statusTone, ASSIGNEE_BY_CONV, assigneeForConversation(), columns, ConversationsListEmpty(), ConversationsListView() (+6 more)

### Community 50 - "db.py"
Cohesion: 0.15
Nodes (16): _current_text(), emergency_gate(), ConversationState, emergency_gate node (EM-1, EM-2, EM-5; design: gate before any LLM).…, Classify the current message; store `emergency_hit` for the router. A weak hit…, Session, Database engine, session factory and declarative base (design: app/db.py).…, Context manager yielding a committed-on-success session (rollback on error). (+8 more)

### Community 51 - "test_handoff.py"
Cohesion: 0.06
Nodes (59): _current_message(), evaluate_handoff(), handoff_gate(), ConversationState, handoff_gate node — deterministic pre-LLM escalation triggers (HH-3, T4.4).…, Store the deterministic trigger reason for the graph router., Deterministic pre-LLM trigger evaluation; returns the reason or None., process_message() (+51 more)

### Community 52 - "AuditLog"
Cohesion: 0.20
Nodes (18): AuditLog, _all_call_texts(), _conversation_id(), _handoff_audit(), _injection_audit(), Customer, parametrize, spec (+10 more)

### Community 53 - "case_update"
Cohesion: 0.14
Nodes (19): case_ack(), _case_or_404(), case_update(), cases_list(), CaseUpdateBody, BaseModel, Case, get (+11 more)

### Community 54 - "Conversation Manager"
Cohesion: 0.22
Nodes (19): Conversation Manager, Emergency Detection, HH-5 Human Response Channel, Human Handoff, Emergency Detection Specification, Settings and Scope Limits Specification, CM-4 Authorized Technical Guidance, EM-1 Deterministic Keyword Detection (+11 more)

### Community 55 - "devDependencies"
Cohesion: 0.11
Nodes (19): jsdom, @storybook/addon-essentials, @storybook/react-vite, @testing-library/jest-dom, @types/node, @types/react-dom, typescript, vite (+11 more)

### Community 56 - "test_clients.py"
Cohesion: 0.31
Nodes (17): _login_oper(), CustomerState, spec, Clients + conversations panel views (T5.2; AP-3, AP-4, CR-3, CR-4, CR-5).…, Create a customer with one conversation, `messages` messages and a case., _seed_customer(), test_add_internal_note(), test_clients_list_lists_customers_with_state() (+9 more)

### Community 57 - "customers.py"
Cohesion: 0.14
Nodes (17): customer_history(), normalize_phone_e164(), datetime, Session, Customer records service (CR-1..CR-6; design: app/services/customers.py). One…, List customers, optionally filtered by name or phone (AP-3). `query` matches…, Complete linked history: conversations, cases, messages (CR-5). Returns dicts…, Persist conversation-captured personal/contact data (CR-6, CM-2). (+9 more)

### Community 58 - "router.py"
Cohesion: 0.17
Nodes (14): get, Request, Response, WhatsApp webhook routes (specs WH-1..WH-7). GET /webhook/whatsapp — verify…, WH-1: Meta subscribe handshake — return hub.challenge or 403., WH-2..WH-7: signature gate, persist-before-process, 200-first., verify_get(), verify_post() (+6 more)

### Community 59 - "KbList.stories.tsx"
Cohesion: 0.18
Nodes (11): columns, Default, Empty, KbListEmpty(), KbListView(), meta, Story, docs (+3 more)

### Community 60 - "classify_intent.py"
Cohesion: 0.14
Nodes (22): classify_intent(), _current_text(), is_injection(), _llm_classify(), ConversationState, classify_intent node (CM-3, HH-3 partial, SH-4 partial). LLM classification…, Persist one unknown-intent attempt; returns the NEW total (HH-3)., Classify the current message; sets intent/case/unknown/escalate flags. (+14 more)

### Community 61 - "respond.py"
Cohesion: 0.20
Nodes (13): _answer_from_kb(), _current_text(), log_unresolved(), ConversationState, respond node — KB-grounded answers + unresolved logging (CM-4, CM-6). Only…, Answer the current message: clarification / KB-grounded / cannot-answer., CM-6: mark an inbound message as unresolved (question+context+ts)., Grounded answer; records the LLM cost on the current message (D6). ``brief``… (+5 more)

### Community 62 - "conversation_thread"
Cohesion: 0.17
Nodes (13): _conversation_or_404(), conversation_thread(), Conversation, get, Session, User, Conversation metadata + chronological messages (media as URL links)., Conversation (+5 more)

### Community 63 - "WhatsApp Webhook"
Cohesion: 0.33
Nodes (10): WhatsApp Webhook Specification, WH-1 Verify Handshake, WH-2 Signature Verification, WH-3 Immediate 200, WH-4 Persist Before Process, WH-5 Deduplicate by WAMID, WH-6 Filter Unsupported Events, WH-7 Retry-Storm Tolerance (+2 more)

### Community 64 - "test_api_conversations.py"
Cohesion: 0.18
Nodes (14): _login(), ConversationState, Panel JSON API conversations (B3/T3.1; PDW-API, PDW-API-3, PDW-AUTH-1, D1, D4).…, Two messages in the same second still render in insertion order (id asc)., A conversation with zero messages still answers 200 with an empty list., Missing conversation -> 404 {"detail":"conversation not found"} (PDW-API-3)., Create a customer + one conversation with 3 messages (1 with media)., No session -> GET /conversations/{id} answers 401 JSON, never a 302. (+6 more)

### Community 65 - "panel/routes/clients.py"
Cohesion: 0.29
Nodes (11): pop_flash(), Request, Read and clear the one-shot notice for this request., client_add_note(), client_ficha(), client_state_change(), clients_list(), _customer_or_404() (+3 more)

### Community 66 - "test_cases.py"
Cohesion: 0.33
Nodes (14): _login_oper(), spec, Cases panel view (T5.3; HH-4, AP-5, EM-4 ack). Functional suite: the…, Create customer + conversation + one case; returns the case id., Create the operador (once) and log in; returns the user id., _seed_case(), test_ack_button_hidden_after_ack(), test_ack_button_records_ack_and_audits() (+6 more)

### Community 67 - "Select.stories.tsx"
Cohesion: 0.15
Nodes (12): Select(), SelectOption, SelectProps, options, Default, Disabled, Matrix, meta (+4 more)

### Community 68 - "summary.py"
Cohesion: 0.21
Nodes (13): generate_summary(), ConversationState, Customer, summary node — conversation summary at completion (CM-5). Generates a concise…, LLM summary persisted on conversation + case (CM-5); returns the text. Shared…, CM-5: summary at completion (capture finished); escalation summaries are…, summary(), _summary_context() (+5 more)

### Community 69 - "Lumat Panel Design System"
Cohesion: 0.14
Nodes (14): Brand Aqua (#8BCCD5), Brand Cyan (#3D93AF), Brand Forest (#576F31), Brand Graphite (#656665), Brand Lime (#ABC333), FastAPI/Jinja Production Panel, Lumat Operational AI Assistant, Lumat Admin and Operador Roles (+6 more)

### Community 70 - "command"
Cohesion: 0.14
Nodes (13): command, _description, enabled, type, mcp, graphify, plugin, $schema (+5 more)

### Community 71 - "test_infra.py"
Cohesion: 0.19
Nodes (10): _load_compose(), T1.3 integration tests — local dev env (compose + .env.example, SH-2). Static…, SH-2: secrets never in repo — .env.example carries placeholders only., Deploy scripts must be executable IN THE GIT INDEX (100755), not just in the…, test_api_service_wires_health_endpoint_port(), test_compose_declares_db_media_backups_volumes(), test_compose_defines_api_and_db_services(), test_db_service_uses_pgvector_image() (+2 more)

### Community 72 - "capture.py"
Cohesion: 0.27
Nodes (12): _answer_consent(), _apply_consent_and_customer(), capture(), _current_text(), is_skip(), _next_field_after(), _persist_captured(), ConversationState (+4 more)

### Community 73 - "Propuesta Técnica y Económica Lumat"
Cohesion: 0.15
Nodes (13): Chatbot vs LumatAgent Comparison Table, Content Cleanliness, Mermaid Diagrams — 4 Required, Multi-Agent Architecture Explanation, Option Naming Convention, Output Artifacts, Quality Standards, Document Structure — 21 Sections (+5 more)

### Community 74 - "Proposal: Panel H2/H4 UI Advance (Inbox + Chat)"
Cohesion: 0.15
Nodes (13): Affected Areas, Approach, Capabilities, Dependencies, In Scope, Intent, Out of Scope, Product Assumptions & Constraints (+5 more)

### Community 75 - "Verification Report"
Cohesion: 0.15
Nodes (13): Assertion Quality, Build & Tests Execution, Changed File Coverage, Coherence (Design, B2), Completeness (B2 scope — T2.1..T2.3), Correctness (Static Evidence, B2), Issues Found, Quality Metrics (+5 more)

### Community 76 - "AppShell.tsx"
Cohesion: 0.19
Nodes (8): AppShellProps, View, VIEW_LABELS, NAVIGATION, NavigationItem, PanelShell(), PanelShellProps, PanelView

### Community 77 - "Tokens.stories.tsx"
Cohesion: 0.18
Nodes (11): GROUP_ORDER, GROUP_RULES, groups, groupToken(), meta, orderedGroups, Overview, sample() (+3 more)

### Community 78 - "Admin Panel"
Cohesion: 0.30
Nodes (12): Admin Panel, Admin Panel Specification, AP-1 Authentication, AP-2 Roles and Permissions, AP-3 Clients List and Search, AP-4 Conversation View, AP-5 Cases View, AP-6 KB Manager Access (+4 more)

### Community 79 - "Customer Records"
Cohesion: 0.24
Nodes (12): Customer Records, Customer Records Specification, CM-2 Progressive Structured Data Capture, CR-1 Auto-Ficha on First Contact, CR-2 Phone-Based Deduplication, CR-3 Lifecycle States, CR-4 Internal Notes, CR-5 History Linkage (+4 more)

### Community 80 - "Design: Panel H2/H4 UI Advance (Inbox + Chat)"
Cohesion: 0.17
Nodes (12): Architecture Decisions (D#), Batch/PR Plan, Component/Story Structure (excludeStories + variants), Data Flow, Design: Panel H2/H4 UI Advance (Inbox + Chat), File Changes, Graph Notes, Migration / Rollout (+4 more)

### Community 81 - "login"
Cohesion: 0.23
Nodes (12): _audit(), login(), login_form(), logout(), get, Request, Response, Session (+4 more)

### Community 82 - "test_seed.py"
Cohesion: 0.23
Nodes (11): _count(), CompletedProcess, T7.2 integration tests — db/seed.sh (design deploy step 4). Runs the seed…, Run db/seed.sh against the test DB with a fixed admin bootstrap env., Two runs: settings/users inserted once, audit_log untouched on re-run., The seeded rows match SETTINGS_DEFAULTS and the admin verifies (AP-1)., Missing PANEL_ADMIN_PASSWORD fails loudly instead of seeding silently., _run_seed() (+3 more)

### Community 83 - "panel/routes/cases.py"
Cohesion: 0.22
Nodes (12): case_ack(), _case_or_404(), case_update(), cases_list(), get, Request, Cases panel view (T5.3; HH-4, AP-5, EM-4 ack). GET /panel/cases ->…, list_open_cases() (+4 more)

### Community 84 - "Archive Report: Panel H2/H4 UI Advance (Inbox + Chat)"
Cohesion: 0.18
Nodes (11): Archive Audit Trail, Archive Report: Panel H2/H4 UI Advance (Inbox + Chat), Delivery State, Executive Summary, Final-State Authority, Per-Capability Delta Sync, Review Receipts (Native RDD — approved), Risks / Notes (+3 more)

### Community 85 - "Tasks: Panel H2/H4 UI Advance"
Cohesion: 0.33
Nodes (11): Tasks: Panel H2/H4 UI Advance, Verify Report: Panel H2/H4 UI Advance, panel-design-system capability, R-PRD-PG-14 Conversation State Domain, panel-h2-advance capability (H2 inbox + H4 chat), R-PRD-PG-10 24-Hour Reply Window, R-PRD-PG-11 Chat With Agent Page, R-PRD-PG-12 Dedicated Chat & Assignee Mock Shapes (+3 more)

### Community 86 - "app.tsx"
Cohesion: 0.29
Nodes (6): ApiError, apiFetch(), App(), GateState, root, User

### Community 87 - "AppShell.stories.tsx"
Cohesion: 0.18
Nodes (8): AppShell(), admin, operador, Admin, Matrix, meta, Operador, Story

### Community 88 - "cortex-persona SKILL.md"
Cohesion: 0.29
Nodes (9): Cortex persona (Senior Architect), cortex-session skill (Planning Mode), Engram memory capture, 5-Step Execution Gate, Graph Check (Gate Step 1), Graphify knowledge graph, Ponytail Rules, SDD Pipeline integration (+1 more)

### Community 89 - "kpis"
Cohesion: 0.20
Nodes (10): kpis(), get, Session, User, Dashboard KPI counts over the configured window (AP-8)., compute_kpis(), panel_home(), get (+2 more)

### Community 90 - "Tasks: Propuesta Técnica y Económica Lumat"
Cohesion: 0.20
Nodes (9): Phase 1: Content Preparation, Phase 2: Mermaid Diagrams — 4 source files, Phase 3: HTML Wireframes — 3 source files, Phase 4: Main Document Assembly, Phase 5: CSS, Build Script, PDF, Phase 6: Verification, Phase 7: Bonus — Executive Presentation (optional), Review Workload Forecast (+1 more)

### Community 91 - "Verification Report"
Cohesion: 0.20
Nodes (9): Build & Tests Execution, Coherence (Design), Completeness, Correctness (Static Evidence), Design Deviation Report, Issues Found, Spec Compliance Matrix (Spec: propuesta-document), Verdict (+1 more)

### Community 92 - "tokens.test.ts"
Cohesion: 0.27
Nodes (6): radius, spacing, componentsRoot, tokensRaw, zIndex, preview

### Community 93 - "get_current_user_json"
Cohesion: 0.25
Nodes (9): get_current_user_json(), HTTPException, Request, Session, User, Resolve the signed-session user; JSON 401 when absent (PDW-AUTH-1)., Admin-only JSON routes (PDW-API-4): operador -> 403 JSON., require_admin_json() (+1 more)

### Community 94 - "Base Layout Template"
Cohesion: 0.22
Nodes (9): Base Layout Template, Cases List Template, Client Ficha Template, Clients List Template, Conversation Thread Template, Dashboard Template, Knowledge Base List Template, Login Template (+1 more)

### Community 95 - "OpenSpec Project Config"
Cohesion: 0.22
Nodes (9): Docker Compose, Hostinger KVM 2 (São Paulo), LangGraph, OpenSpec Project Config, PostgreSQL, CM-1 Single-Agent Flow with Menu, HH-1 Per-Conversation State Model, 8-Category Menu (+1 more)

### Community 96 - "archive-report.md"
Cohesion: 0.31
Nodes (6): AgentChatMessage dedicated type, B1 Inbox batch, B2 Chat batch, PR #30 (B1 to main), PR #31 (B2 to B1, stacked), R-PRD-PG-1 Page Stories

### Community 97 - "test_webhook_verify.py"
Cohesion: 0.36
Nodes (8): parametrize, spec, T0.3 — webhook GET verify handshake (WH-1) and POST signature check (WH-2).…, _signature(), test_get_verify_rejects_invalid_handshake(), test_get_verify_returns_challenge_with_correct_token(), test_post_with_invalid_signature_returns_403(), test_post_with_valid_signature_returns_200()

### Community 98 - "get_or_create_conversation"
Cohesion: 0.22
Nodes (9): get_or_create_conversation(), Conversation, Customer, Return the open conversation for a customer; create it if none is open. Closed…, test_cr5_closed_conversation_opens_new(), CR-5: a closed conversation never reopens; the next inbound lands in a new…, test_cr5_closed_opens_new_conversation_through_ingest(), A received text through the sweep answers AND sends via Meta. (+1 more)

### Community 99 - "add_note"
Cohesion: 0.25
Nodes (9): add_note(), list_notes(), CustomerNote, Store an internal staff note on a customer ficha (author + timestamp)., Internal notes in chronological order (CR-4 panel view)., Notes are internal: no column on the customer record exposes them., test_cr4_add_note_stores_author_and_timestamp(), test_cr4_list_notes_chronological() (+1 more)

### Community 100 - "clean_db"
Cohesion: 0.67
Nodes (3): clean_db(), fixture, Reset all customer-related tables before every test (shared test DB).

### Community 101 - "Knowledge Base"
Cohesion: 0.39
Nodes (8): Knowledge Base, Knowledge Base Specification, pgvector, CM-6 Unresolved Response Logging, KB-1 Ingestion Pipeline, KB-2 Semantic Retrieval, KB-3 KB Manager, KB-4 Versioning and Re-Ingestion

### Community 102 - "scripts"
Cohesion: 0.25
Nodes (8): scripts, build, build-storybook, dev, preview, storybook, test, test:watch

### Community 103 - "_csv_response"
Cohesion: 0.38
Nodes (7): _csv_response(), _csv_stream(), export_cases(), export_clients(), get, Yield CSV lines from a row iterable (stdlib csv, streaming)., StreamingResponse

### Community 104 - "Design: Panel Design System"
Cohesion: 0.38
Nodes (7): Apply Progress: Panel Design System, Archive Report: Panel Design System, Design: Panel Design System, Proposal: Panel Design System, Panel Design System Spec (change delta), Tasks: Panel Design System, Verify Report: Panel Design System

### Community 105 - "Requirement: R-PRD-PG-14 — Conversation State Domain"
Cohesion: 0.29
Nodes (6): ADDED Requirements, Delta for panel-design-system, Requirement: R-PRD-PG-14 — Conversation State Domain, Scenario: Mock domain is valid, Scenario: StatusBadge renders every domain state, panel-design-system main spec

### Community 106 - "Tasks: Panel H2/H4 UI Advance (Inbox + Chat)"
Cohesion: 0.29
Nodes (7): Lifecycle Gates, Notes, Phase 1 — B1 Inbox (T1.x, PR 1), Phase 2 — B2 Chat (T2.x, PR 2), Review Workload Forecast, Suggested Work Units, Tasks: Panel H2/H4 UI Advance (Inbox + Chat)

### Community 107 - "Conversation Manager Specification"
Cohesion: 0.43
Nodes (7): Conversation Manager Specification, Human Handoff Specification, CM-3 Intent and Case Classification, CM-5 Conversation Summary, HH-2 Deriva with History and Summary, HH-5 Human Response Channel (H1), Case Record

### Community 108 - "Security Hardening"
Cohesion: 0.24
Nodes (12): Meta WhatsApp Cloud API, OpenAI API, Security Hardening Specification, LumatAgent README, SH-1 Network and Access Hardening, SH-2 Container and Secrets Hardening, SH-3 Backups and Monitoring, SH-4 Prompt-Injection Mitigations (+4 more)

### Community 109 - "run_migrate"
Cohesion: 0.29
Nodes (7): migrated_db(), CompletedProcess, Run db/migrate.sh against the test DB (idempotent)., Apply migrations once per session (idempotent runner)., run_migrate(), Acceptance: applies cleanly twice (idempotent)., test_migrate_applies_cleanly_twice()

### Community 110 - "package.json"
Cohesion: 0.29
Nodes (6): engines, node, name, private, type, version

### Community 111 - "PanelEntry.stories.tsx"
Cohesion: 0.29
Nodes (6): DesktopAdmin, DesktopOperator, meta, MobileDrawerOpen, Story, TabletDrawerOpen

### Community 113 - "Ponytail Review (diff over-engineering)"
Cohesion: 0.40
Nodes (5): Ponytail Audit (repo-wide), Ponytail Debt Ledger, Ponytail Help Reference Card, Ponytail Plan (pre-code review), Ponytail Review (diff over-engineering)

### Community 114 - "dependencies"
Cohesion: 0.40
Nodes (5): react, react-dom, dependencies, react, react-dom

### Community 116 - "migrate.sh"
Cohesion: 0.50
Nodes (3): APP_DB_PASSWORD, DATABASE_URL, migrate.sh script

### Community 117 - "seed.sh"
Cohesion: 0.50
Nodes (3): DATABASE_URL, SEED_REPO_ROOT, seed.sh script

### Community 118 - "Milestone 1 - Bot IA de atencion al cliente"
Cohesion: 0.50
Nodes (4): Derivacion a atencion humana, Ficha del cliente y registro de conversaciones, Milestone 1 - Bot IA de atencion al cliente, Panel de administracion (M1)

### Community 119 - "conversation_thread"
Cohesion: 0.67
Nodes (3): conversation_thread(), get, Request

### Community 121 - "Verify Report: Panel Real Design"
Cohesion: 0.67
Nodes (3): Archive Report: Panel Real Design, Spec Delta: panel-design-system (H1), Verify Report: Panel Real Design

### Community 122 - "Design: Panel Real Design"
Cohesion: 0.67
Nodes (3): Design: Panel Real Design, Exploration: Panel Real Design, Tasks: Panel Real Design

### Community 123 - "logged_client"
Cohesion: 0.67
Nodes (3): logged_client(), fixture, A TestClient already authenticated as an operador.

### Community 124 - "clean_db"
Cohesion: 0.67
Nodes (3): clean_db(), fixture, Reset settings, audit_log and users before every test (shared test DB).

## Ambiguous Edges - Review These
- `Graphify Knowledge Graph (636 nodes / 1211 edges / 39 communities)` → `Strict TDD Compliance (7/7 checks)`  [AMBIGUOUS]
  openspec/changes/hito-1-setup-whatsapp/verify-report.md · relation: conceptually_related_to

## Knowledge Gaps
- **481 isolated node(s):** `BadgeProps`, `Story`, `EmptyStateProps`, `PageHeaderProps`, `StatCardProps` (+476 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **38 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Graphify Knowledge Graph (636 nodes / 1211 edges / 39 communities)` and `Strict TDD Compliance (7/7 checks)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `LangGraph conversation graph` connect `Hito 1 change — Setup + WhatsApp operativo` to `graph.py`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Are the 76 inferred relationships involving `make_user()` (e.g. with `test_json_login_invalid_credentials()` and `test_json_login_locked_account()`) actually correct?**
  _`make_user()` has 76 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `Message` (e.g. with `ConversationState` and `Base`) actually correct?**
  _`Message` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `Conversation` (e.g. with `ConversationState` and `Base`) actually correct?**
  _`Conversation` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `Customer` (e.g. with `ConversationState` and `Base`) actually correct?**
  _`Customer` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `BadgeProps`, `Story`, `EmptyStateProps` to the rest of the system?**
  _481 weakly-connected nodes found - possible documentation gaps or missing edges._