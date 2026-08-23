# Graph Report - /home/stefan/repos/lumat-agent  (2026-08-22)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2947 nodes · 6276 edges · 211 communities (158 shown, 53 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 246 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cff652ce`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- get_settings
- test_webhook_ingest.py
- test_handoff.py
- AuditLog
- db.py
- get_or_create_customer
- Hito 1 change — Setup + WhatsApp operativo
- models.py
- get_setting
- panel/deps.py
- test_cost_guardrails.py
- devDependencies
- test_emergency.py
- test_emergency_notify.py
- ClientFicha.stories.tsx
- ADDED Requirements
- api/routes/clients.py
- ingest.py
- test_migrations.py
- test_kb_settings.py
- KbList.stories.tsx
- CasesList.stories.tsx
- make_user
- test_api_memories.py
- test_api_clients.py
- test_auth.py
- types.ts
- H1 — Setup + WhatsApp Operativo (Tasks)
- ConversationThread.stories.tsx
- graph.py
- costs.py
- get_or_create_conversation
- upsert
- test_memory_observations.py
- notify.py
- test_api_auth.py
- compilerOptions
- test_chat_state.py
- Conversation
- Human Handoff
- KbDocument
- services/kb.py
- ConversationsList.stories.tsx
- Settings.stories.tsx
- test_kb.py
- test_chat_intent.py
- serializers.py
- Conversation Manager Specification
- test_api_cases.py
- render
- test_chat_capture.py
- Panel Design System Specification
- memory.py
- Agent Config Specification
- ClientMemories.tsx
- compilerOptions
- case_update
- panel/routes/settings.py
- Login.stories.tsx
- test_clients.py
- ChatWithAgent.stories.tsx
- Admin Panel
- services/cases.py
- matrix.tsx
- Dashboard.stories.tsx
- test_prompts.py
- Message
- test_memory_pipeline.py
- summary.py
- panel/routes/kb.py
- test_cases.py
- ClientesList.stories.tsx
- Case
- WhatsApp Webhook
- command
- test_infra.py
- capture.py
- Propuesta Técnica y Económica Lumat
- Proposal: Panel H2/H4 UI Advance (Inbox + Chat)
- Verification Report
- spec/conftest.py
- _FakeClient
- Tokens.stories.tsx
- panel/routes/clients.py
- login
- list_for_entity
- Lumat Panel Design System
- Design: Panel H2/H4 UI Advance (Inbox + Chat)
- tokens.css
- test_seed.py
- Archive Report: Panel H2/H4 UI Advance (Inbox + Chat)
- Memory Specification
- app.tsx
- cortex-persona SKILL.md
- respond.py
- Tasks: Propuesta Técnica y Económica Lumat
- Verification Report
- Customer Records Specification
- StatusBadge component
- AppShell.tsx
- Avatar.stories.tsx
- tokens.test.ts
- get_by_key
- get_current_user_json
- export.py
- Base Layout Template
- Tasks: Panel H2/H4 UI Advance
- test_webhook_verify.py
- unit/conftest.py
- SearchInput.stories.tsx
- Select.stories.tsx
- archive-report.md
- PanelShell.tsx
- Button.stories.tsx
- Input.stories.tsx
- Design: Panel Design System
- Tasks: Panel H2/H4 UI Advance (Inbox + Chat)
- Security Hardening
- PanelEntry.stories.tsx
- Textarea.stories.tsx
- llm.py
- Requirement: R-PRD-PG-14 — Conversation State Domain
- AppShell.stories.tsx
- Ponytail Review (diff over-engineering)
- DS-UI-PRIMS Token-correct focus and motion
- clean_db
- migrate.sh
- seed.sh
- Milestone 1 - Bot IA de atencion al cliente
- Agent Registry
- monitor.sh
- graphify.js
- Verify Report: Panel Real Design
- Design: Panel Real Design
- logged_client
- clean_db
- Agent Config Requirements AC-1..8
- app/__init__.py
- api/routes/__init__.py
- webhook/__init__.py
- Graphify Knowledge Graph (636 nodes / 1211 edges / 39 communities)
- Design System UI Requirements DS-UI
- backup.sh
- restore-test.sh
- Memory Requirements MEM-1..6
- tasks.md (33 tasks, traceability)
- B1 Spec Compliance Matrix
- B2 Spec Compliance Matrix
- B3 Spec Compliance Matrix
- main.ts
- Classify Persona
- Orchestrator Brief Persona
- Summary Persona
- Classify Prompt Template
- Respond Prompt Template
- Summary Prompt Template
- Capture Skill
- Emergency Skill
- Handoff Skill
- SDB Skill
- datetime
- app/panel/* — admin panel routes/templates
- BaseModel
- get
- Case
- CustomerNote
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
- CustomerState
- tests/injection/ — SH-4 suite
- Token Foundation (type/focus/motion/breakpoints/shadow)
- Index HTML (Lumat Panel root)
- clean_db

## God Nodes (most connected - your core abstractions)
1. `make_user()` - 98 edges
2. `Message` - 83 edges
3. `Conversation` - 65 edges
4. `Customer` - 57 edges
5. `get_or_create_customer()` - 55 edges
6. `Case` - 44 edges
7. `_post()` - 44 edges
8. `Panel Design System Specification` - 42 edges
9. `record_audit()` - 41 edges
10. `User` - 38 edges

## Surprising Connections (you probably didn't know these)
- `DS-STORY-1 Doc-Level Coverage for All Stories` --references--> `storybook`  [EXTRACTED]
  openspec/specs/panel-design-system/spec.md → web/package.json
- `DS-STORY-2 Description and Usage Guidance` --references--> `storybook`  [EXTRACTED]
  openspec/specs/panel-design-system/spec.md → web/package.json
- `DS-STORY-3 Interactive Controls` --references--> `storybook`  [EXTRACTED]
  openspec/specs/panel-design-system/spec.md → web/package.json
- `DS-STORY-4 Variant Matrix Story` --references--> `storybook`  [EXTRACTED]
  openspec/specs/panel-design-system/spec.md → web/package.json
- `DS-STORY-6 Autodocs Enabled` --references--> `storybook`  [EXTRACTED]
  openspec/specs/panel-design-system/spec.md → web/package.json

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **H1 spec requirement areas mapped to task batches (traceability)** — openspec_changes_hito_1_setup_whatsapp_tasks_wh, openspec_changes_hito_1_setup_whatsapp_tasks_cm, openspec_changes_hito_1_setup_whatsapp_tasks_cr, openspec_changes_hito_1_setup_whatsapp_tasks_kb, openspec_changes_hito_1_setup_whatsapp_tasks_em, openspec_changes_hito_1_setup_whatsapp_tasks_hh, openspec_changes_hito_1_setup_whatsapp_tasks_ap, openspec_changes_hito_1_setup_whatsapp_tasks_ss, openspec_changes_hito_1_setup_whatsapp_tasks_sh [EXTRACTED 0.85]
- **Lumat brand primitives and operational primary color system** — brand_lime, brand_cyan, brand_aqua, brand_forest, brand_graphite, primary_800_token [EXTRACTED 0.85]
- **Agent config loader flow** — openspec_specs_agent_config_spec_doc, openspec_specs_agent_config_spec_ac1, openspec_specs_agent_config_spec_ac2, openspec_specs_agent_config_spec_ac3, openspec_specs_agent_config_spec_ac4, openspec_specs_agent_config_spec_ac5, openspec_specs_agent_config_spec_ac6, openspec_specs_agent_config_spec_ac7, openspec_specs_agent_config_spec_ac8, openspec_specs_agent_config_spec_prompts_loader, openspec_specs_agent_config_spec_registry_yaml [EXTRACTED 0.90]
- **B3 Verified Spec Families (CR, CM, KB, HH, SH, SS)** — concept_cr_family, concept_cm_family, concept_kb_pipeline, concept_sh_security, openspec_changes_hito-1-setup-whatsapp_verify-report__spec_compliance_b3 [EXTRACTED 0.90]
- **Cortex workflow (Graphify gate + Ponytail + SDD)** — opencode_skills_cortex_persona_skill_graphify, opencode_skills_cortex_persona_skill_graph_check, opencode_skills_cortex_persona_skill_ponytail_rules, opencode_skills_cortex_persona_skill_execution_gate, opencode_skills_cortex_persona_skill_sdd_pipeline, opencode_skills_cortex_persona_skill_engram [EXTRACTED 0.90]
- **SH-1..SH-5 security hardening checklist executed on rehearsal VM** — docs_hardening, docs_hardening_sh1, docs_hardening_sh2, docs_hardening_sh5, infra_docker_compose_prod_yml [EXTRACTED 0.90]
- **Persistent memory layer** — openspec_specs_memory_spec_doc, openspec_specs_memory_spec_mem1, openspec_specs_memory_spec_mem2, openspec_specs_memory_spec_mem3, openspec_specs_memory_spec_mem4, openspec_specs_memory_spec_mem5, openspec_specs_memory_spec_mem6, openspec_specs_memory_spec_customer_memo [EXTRACTED 0.90]
- **Ponytail minimal-code skill family (ladder YAGNI→stdlib→native→one line)** — opencode_skills_ponytail_audit, opencode_skills_ponytail_debt, opencode_skills_ponytail_help, opencode_skills_ponytail_plan, opencode_skills_ponytail_review [EXTRACTED 0.90]
- **Admin Panel Jinja Template Set (base + 8 views)** — app_panel_templates_base, app_panel_templates_dashboard, app_panel_templates_login, app_panel_templates_cases_list, app_panel_templates_clients_ficha, app_panel_templates_clients_list, app_panel_templates_conversations_thread, app_panel_templates_kb_list, app_panel_templates_settings_index [EXTRACTED 0.95]
- **Cortex skill pack bootstrap workflow** — opencode_commands_cortex_init_command, opencode_commands_cortex_init_script, cortex_skill_pack, graphify_knowledge_graph, cortex_skill_registry, sdd_init_command [EXTRACTED 1.00]
- **H1 technical stack** — fastapi_app, langgraph_graph, postgres_pgvector, docker_compose_infra, hostinger_kvm2_vps, meta_cloud_api [EXTRACTED 1.00]
- **Panel Design System SDD Change Cycle** — openspec_changes_archive_2026_08_19_panel_design_system_proposal, openspec_changes_archive_2026_08_19_panel_design_system_design, openspec_changes_archive_2026_08_19_panel_design_system_tasks, openspec_changes_archive_2026_08_19_panel_design_system_apply_progress, openspec_changes_archive_2026_08_19_panel_design_system_verify_report, openspec_changes_archive_2026_08_19_panel_design_system_archive_report, openspec_changes_archive_2026_08_19_panel_design_system_specs_panel_design_system_spec [EXTRACTED 1.00]
- **Propuesta PDF build pipeline** — propuesta_build_script, mmdc_mermaid_cli, headless_chrome_render, md_to_pdf_engine, propuesta_main_document [EXTRACTED 1.00]
- **Conversation → ficha → memo lifecycle** — openspec_specs_conversation_manager_spec_doc, openspec_specs_customer_records_spec_doc, openspec_specs_memory_spec_doc, openspec_specs_memory_spec_customer_memo, openspec_specs_conversation_manager_spec_acta [INFERRED 0.75]
- **Case Record Lifecycle Across Specs** — shared_case_record [INFERRED 0.85]
- **Inbound WhatsApp Message Pipeline** — whatsapp-webhook_whatsapp-webhook, emergency-detection_emergency-detection, human-handoff_human-handoff [INFERRED 0.85]

## Communities (211 total, 53 thin omitted)

### Community 0 - "get_settings"
Cohesion: 0.04
Nodes (62): get_settings(), Application configuration. Settings are read from environment variables ONLY…, Environment-only application settings (design: app/config.py, D3, SH-2)., Return the cached settings instance (cleared in tests via cache_clear)., Settings, create_app(), lifespan(), LumatAgent API application factory (design: app/main.py). `app = create_app()`… (+54 more)

### Community 1 - "test_webhook_ingest.py"
Cohesion: 0.07
Nodes (64): KeywordsBody, LimitsBody, MetaBody, _number(), _parse_scope(), BaseModel, get, Session (+56 more)

### Community 2 - "test_handoff.py"
Cohesion: 0.06
Nodes (62): _current_message(), evaluate_handoff(), handoff_gate(), ConversationState, handoff_gate node — deterministic pre-LLM escalation triggers (HH-3, T4.4).…, Store the deterministic trigger reason for the graph router., Deterministic pre-LLM trigger evaluation; returns the reason or None., Transition a conversation's bot/human/closed state (HH-1). Every transition… (+54 more)

### Community 3 - "AuditLog"
Cohesion: 0.07
Nodes (58): AuditLog, _conversation(), _last_outbound(), _outbound_texts(), Customer, Message, spec, T6.2 functional tests — conversation-manager flows over the webhook (CM-1..6).… (+50 more)

### Community 4 - "db.py"
Cohesion: 0.06
Nodes (50): cost_gate node (SS-3; design: deterministic gate before any LLM). Runs on EVERY…, emergency(), _protocol_replies(), ConversationState, emergency node (EM-2, EM-3; T4.2, weak path migrated in T4.4). Runs ONLY via…, EM-3: safety instructions + contacts + technician-notified blocks., Run the safety protocol (EM-3). The gate only routes strong hits here., _escalate_reason() (+42 more)

### Community 5 - "get_or_create_customer"
Cohesion: 0.08
Nodes (49): add_note(), customer_history(), get_or_create_customer(), InvalidStateTransition, list_notes(), normalize_phone_e164(), Customer, CustomerNote (+41 more)

### Community 6 - "Hito 1 change — Setup + WhatsApp operativo"
Cohesion: 0.06
Nodes (51): admin-panel capability, arquitectura-lumatagent.md (diagrams source), conversation-manager capability, Cortex session report.md, Cortex skill pack, Cortex skill registry (.atl/skill-registry.md), Cost guardrails (spend limits + alerts), cotizacion-lumat.md (pricing source of truth) (+43 more)

### Community 7 - "models.py"
Cohesion: 0.07
Nodes (46): MemoryRelation, pg_enum(), ORM models mapping the migrated schema (design Data Model, 10 tables). The…, Schema-only relation between two memory rows (Ponytail deferral). No consumer…, PG-native Enum that stores the *member values* (labels in 001_init.sql).…, _ts(), User, UserRole (+38 more)

### Community 8 - "get_setting"
Cohesion: 0.07
Nodes (49): get_message(), get_scope_mode(), get_setting(), get_tone(), Session, Settings KV service (design: app/services/settings.py, D5; SS-1..5 storage).…, Read one setting: stored value > built-in default > caller default., Upsert one setting and audit the change (SH-5). The caller commits. (+41 more)

### Community 9 - "panel/deps.py"
Cohesion: 0.08
Nodes (38): Panel JSON API auth dependencies (design D4; PDW-AUTH-1, PDW-API-4). Parallel…, Any authenticated user (admin or operador) — shared JSON routes., require_user_json(), Panel JSON API package (design D4; PDW-API, PDW-AUTH). Additive JSON layer…, Panel JSON API cases (B3/T3.2; PDW-API, PDW-API-3, D4, D8). Thin JSON wrappers…, Panel JSON API conversations (B3/T3.1; PDW-API, PDW-API-3, D4). Thin JSON…, kpis(), get (+30 more)

### Community 10 - "test_cost_guardrails.py"
Cohesion: 0.09
Nodes (46): _append(), _audit_actions(), _capturing_smtp(), clean_db(), no_real_smtp(), fixture, T4.5 integration tests — cost guardrails (SS-3, SS-4). Scenarios mapped from…, Audit actions limited to the cost-alert surface (seed noise excluded). (+38 more)

### Community 11 - "devDependencies"
Cohesion: 0.04
Nodes (45): jsdom, react, react-dom, @storybook/addon-essentials, @storybook/react-vite, @testing-library/jest-dom, @testing-library/react, @testing-library/user-event (+37 more)

### Community 12 - "test_emergency.py"
Cohesion: 0.08
Nodes (42): _current_text(), emergency_gate(), ConversationState, emergency_gate node (EM-1, EM-2, EM-5; design: gate before any LLM).…, Classify the current message; store `emergency_hit` for the router. A weak hit…, classify_emergency(), compile_keywords(), fold_accents() (+34 more)

### Community 13 - "test_emergency_notify.py"
Cohesion: 0.09
Nodes (42): acknowledge_emergency_if_ack(), is_ack_message(), True when the customer's reply is a pure ack-keyword message. "ok" / "listo" /…, Record the customer reply-keyword ack on the emergency case (T4.3.2).…, _audit_rows(), _call_notification(), _capturing_smtp(), clean_db() (+34 more)

### Community 14 - "ClientFicha.stories.tsx"
Cohesion: 0.08
Nodes (35): Badge(), BadgeProps, BadgeTone, CaseActions(), CasesListEmpty(), CasesListView(), caseColumns, ClientFichaView() (+27 more)

### Community 15 - "ADDED Requirements"
Cohesion: 0.05
Nodes (42): panel-h2-advance delta spec, ADDED Requirements, Delta for panel-h2-advance, Requirement: R-PRD-PG-10 — 24-Hour Reply Window, Requirement: R-PRD-PG-11 — Chat With Agent Page, Requirement: R-PRD-PG-12 — Dedicated Chat & Assignee Mock Shapes, Requirement: R-PRD-PG-13 — Verification Gates & Boundary Guards, Requirement: R-PRD-PG-8 — Inbox List: State, Assignee & Filter (+34 more)

### Community 16 - "api/routes/clients.py"
Cohesion: 0.12
Nodes (40): CustomerState, Memory, MemoryStatus, MemoryType, Persistent, domain-aware memory row (099_memory.sql, MEM-1). Typed memories…, client_add_note(), client_ficha(), client_memories_list() (+32 more)

### Community 17 - "ingest.py"
Cohesion: 0.08
Nodes (36): MessageDirection, MessageStatus, MessageType, deliver_all_pending(), deliver_outbound(), Meta Cloud API outbound send (design: app/services/send.py; SS-4 basis).…, Send every pending outbound message across conversations (sweep path)., Send pending outbound rows of a conversation; record wamid + cost_meta. Only… (+28 more)

### Community 18 - "test_migrations.py"
Cohesion: 0.05
Nodes (39): client(), fake_embedder(), migrated_db(), mock_meta_send(), mock_openai_chat(), CompletedProcess, fixture, TestClient (+31 more)

### Community 19 - "test_kb_settings.py"
Cohesion: 0.08
Nodes (37): api_login(), clean_db(), client(), fake_embedder(), login(), migrated_db(), CompletedProcess, fixture (+29 more)

### Community 20 - "KbList.stories.tsx"
Cohesion: 0.08
Nodes (26): FieldShell(), FieldShellProps, Input(), InputProps, Select(), SelectOption, SelectProps, options (+18 more)

### Community 21 - "CasesList.stories.tsx"
Cohesion: 0.07
Nodes (26): CASE_STATUSES, CasesListState, columns, Default, Empty, FatalError, Loading, meta (+18 more)

### Community 22 - "make_user"
Cohesion: 0.15
Nodes (34): make_user(), Factory creating a panel user row directly (bcrypt hash) in a session., _doc_version(), _last_audit(), _login(), Panel JSON API KB + settings (B4/T4.1+T4.2; PDW-API-1/2/3/4, D1, D4). Admin-…, Seed a KB document through the service path (v1, embedded)., Limit validation mirrors the Jinja _number guard (SS-3): >= 0. (+26 more)

### Community 23 - "test_api_memories.py"
Cohesion: 0.11
Nodes (35): _login(), Memory, MemoryType, Panel JSON API memories (MEM-6; PDW-API, PDW-API-3, PDW-AUTH-1, D4, SH-5). Thin…, Only this customer's memories return, in a stable serializer shape., A customer with no memories -> empty list, no error (MEM-6)., Same topic_key -> the existing row is refreshed, not duplicated (MEM-2)., MEM-2: writers reject a non-default project before any write. The routes never… (+27 more)

### Community 24 - "test_api_clients.py"
Cohesion: 0.12
Nodes (34): CustomerNote, Internal staff note on a customer ficha (CR-4; 002_customer_notes.sql). Staff-…, CustomerState, _customer_row(), _login(), Customer, Panel JSON API clients (B2/T2.2; PDW-API, PDW-API-3, PDW-AUTH-1, D1, D4). The…, Empty result is real (service filtered) — companion to the non-empty test. (+26 more)

### Community 25 - "test_auth.py"
Cohesion: 0.10
Nodes (34): _audit_actions(), CompletedProcess, spec, User, Panel authentication + roles (T5.1; AP-1, AP-2, SH-5). Functional suite over…, No such user -> generic error + audit row, nothing else leaks., 5 failed attempts -> locked_until set; correct password then rejected., After locked_until passes, a correct login succeeds (15-min ban ends). (+26 more)

### Community 26 - "types.ts"
Cohesion: 0.10
Nodes (26): casesData, CASE_KEYS, CASE_STATUSES, clients, CUSTOMER_STATES, CONV_STATES, CONVERSATION_KEYS, MESSAGE_KEYS (+18 more)

### Community 27 - "H1 — Setup + WhatsApp Operativo (Tasks)"
Cohesion: 0.07
Nodes (34): Security Hardening (SH-1..5), Hardening Checklist (SH-1/2/3 executable), SH-1 Network/Access Hardening, SH-2 Container/Secrets Hardening, SH-5 Audit Log Append-Only, Ops Runbook & Meta Onboarding Checklist, Backup Restore Drill, Deploy Flow (tag + compose restart) (+26 more)

### Community 28 - "ConversationThread.stories.tsx"
Cohesion: 0.09
Nodes (25): BubbleVariant, ConversationThreadBubbles(), ConversationThreadState, ConversationThreadView(), customer, Default, Empty, Loading (+17 more)

### Community 29 - "graph.py"
Cohesion: 0.11
Nodes (30): _after_capture(), _after_cost_gate(), _after_emergency_gate(), _after_handoff_gate(), _after_respond(), build_graph(), _flow_start(), ConversationState (+22 more)

### Community 30 - "costs.py"
Cohesion: 0.13
Nodes (31): cost_gate(), ConversationState, Evaluate spend states, alert the owner on crossings, flag cost_mode., _alert_action(), combined_cost_mode(), conversation_cost_state(), conversation_spend(), daily_cost_state() (+23 more)

### Community 31 - "get_or_create_conversation"
Cohesion: 0.10
Nodes (29): get_or_create_conversation(), Conversation, Customer, Session, Return the open conversation for a customer; create it if none is open. Closed…, Settings, Send one WhatsApp text message; returns the Meta wamid. Raises…, send_text() (+21 more)

### Community 32 - "upsert"
Cohesion: 0.09
Nodes (29): _embed(), _guard_writable_project(), hybrid_search(), MemoryType, Create-or-update one memory by (proyecto, scope, entity_id, topic_key). Embeds…, Hybrid retrieval over one entity's memories (MEM-3). Two-phase recall that…, Reject writes targeting a non-default project (MEM-2)., Embed a batch locally; empty text -> empty list (reuses kb seam). Retries… (+21 more)

### Community 33 - "test_memory_observations.py"
Cohesion: 0.15
Nodes (29): _add_inbound(), _close(), _memo_text(), _obs(), S3 integration tests — close event memo + observations (MEM-4, MEM-5, CM-9).…, Closing upserts: the close-time acta wins over any stale prior memo., A close with no summary still writes an empty memo (never fabricated)., A single close produces no recurrencia observation (MEM-5 threshold). (+21 more)

### Community 34 - "notify.py"
Cohesion: 0.13
Nodes (28): acknowledge_case(), _audit_notification(), _customer_location(), _notification_body(), Case, Conversation, Customer, Session (+20 more)

### Community 35 - "test_api_auth.py"
Cohesion: 0.09
Nodes (28): _audit_actions(), User, Panel JSON API authentication (B1/T1.2; PDW-AUTH-1/2/4, PDW-API-3, D1, D4). The…, Valid JSON credentials -> 200 {ok, role}, session cookie, audit., operador credentials -> same cookie, role=operador (triangulation)., Wrong password -> 401 JSON {"detail":"invalid credentials"}, audited., No such user -> same generic 401, nothing leaks (no user oracle)., 5 failures -> lock; even a correct password returns 401 "account locked". (+20 more)

### Community 36 - "compilerOptions"
Cohesion: 0.07
Nodes (27): DOM, DOM.Iterable, ES2022, node, src, vite/client, compilerOptions, erasableSyntaxOnly (+19 more)

### Community 37 - "test_chat_state.py"
Cohesion: 0.13
Nodes (24): persist_replies(), Message, Session, Persist bot replies as outbound messages (status processed). The actual Meta…, Run the graph for one persisted inbound message; returns bot replies. Rebuilds…, run_conversation(), Rebuild the state from the DB for one message (D2, no checkpointer)., clean_db() (+16 more)

### Community 38 - "Conversation"
Cohesion: 0.12
Nodes (26): Conversation, Customer, closed_at set -> case excluded from the open list (HH-4)., test_cases_list_skips_closed_cases(), _login(), ConversationState, Panel JSON API conversations (B3/T3.1; PDW-API, PDW-API-3, PDW-AUTH-1, D1, D4).…, Two messages in the same second still render in insertion order (id asc). (+18 more)

### Community 39 - "Human Handoff"
Cohesion: 0.14
Nodes (27): Emergency Detection, HH-5 Human Response Channel, Human Handoff, Emergency Detection Specification, Human Handoff Specification, Settings and Scope Limits Specification, EM-1 Deterministic Keyword Detection, EM-2 Flow Interrupt (+19 more)

### Community 40 - "KbDocument"
Cohesion: 0.16
Nodes (25): DocumentFormat, KbDocument, _doc_or_404(), DocEditBody, DocRestoreBody, kb_disable(), kb_edit(), kb_list() (+17 more)

### Community 41 - "services/kb.py"
Cohesion: 0.12
Nodes (24): KbChunk, chunk_text(), _csv_rows_to_text(), disable_document(), _embed_cost(), embed_texts(), extract_text(), get_embedder() (+16 more)

### Community 42 - "ConversationsList.stories.tsx"
Cohesion: 0.11
Nodes (20): Status, StatusBadge(), StatusBadgeProps, statusTone, ASSIGNEE_BY_CONV, assigneeForConversation(), columns, ConversationsListEmpty() (+12 more)

### Community 43 - "Settings.stories.tsx"
Cohesion: 0.11
Nodes (20): Default, meta, Saved, Saving, ServerError, SettingsState, SettingsView(), Stale (+12 more)

### Community 44 - "test_kb.py"
Cohesion: 0.17
Nodes (22): ingest_document(), Create a document (version 1) and ingest its chunks (KB-1)., Semantic retrieval over the ACTIVE versions of enabled documents. Filters:…, retrieve(), _chunk_rows(), _embed(), _ingest(), _pdf_with_text() (+14 more)

### Community 45 - "test_chat_intent.py"
Cohesion: 0.18
Nodes (22): _case_rows(), clean_db(), mock_chat(), Case, fixture, T3.4 integration tests — classify_intent + route nodes (CM-3, HH-3, SH-4).…, Seed a customer + open conversation + one inbound received message., Intercept OpenAI /chat/completions; captures requests for SH-4 checks. (+14 more)

### Community 46 - "serializers.py"
Cohesion: 0.11
Nodes (22): _conversation_or_404(), conversation_thread(), Conversation, get, Session, User, Conversation metadata + chronological messages (media as URL links)., _iso() (+14 more)

### Community 47 - "Conversation Manager Specification"
Cohesion: 0.13
Nodes (22): CM-7 Memory Context Pre-Respond, CM-8 Turn-Time Persistence, CM-9 Close Trigger Feeds Customer Memo, CR-7 Living Customer Memo, Conversation Manager Specification, Conversation Manager Spec, Conversation summary acta (CM-5), CM-8 Turn-Time Memory Persistence (+14 more)

### Community 48 - "test_api_cases.py"
Cohesion: 0.17
Nodes (22): _case_row(), _login(), Case, datetime, Panel JSON API cases (B3/T3.2; PDW-API, PDW-API-3, PDW-AUTH-1, D1, D4, D8).…, No session -> every cases endpoint answers 401 JSON, never a 302., Among escalated cases, the newest escalation comes first., responsible_id:null explicitly clears the assignment (service sentinel). (+14 more)

### Community 49 - "render"
Cohesion: 0.13
Nodes (22): _llm_classify(), Call gpt-4o-mini with input-as-data (SH-4); returns the parsed JSON. Records…, _answer_from_kb(), Grounded answer; records the LLM cost on the current message (D6). ``brief``…, Decimal, Accumulate the token cost of one LLM call on the message (D6)., record_llm_cost(), load() (+14 more)

### Community 50 - "test_chat_capture.py"
Cohesion: 0.19
Nodes (21): list_unresolved_questions(), Message, CM-6 query (no dedicated SQL view — filter by payload flag)., clean_db(), _conversation_captured(), _customer(), fixture, T3.5 integration tests — capture / respond / summary / unresolved nodes.… (+13 more)

### Community 51 - "Panel Design System Specification"
Cohesion: 0.14
Nodes (22): Panel Design System Specification, DS-STORY-1 Doc-Level Coverage for All Stories, DS-STORY-2 Description and Usage Guidance, DS-STORY-3 Interactive Controls, DS-STORY-4 Variant Matrix Story, DS-STORY-5 Accessibility Notes, DS-STORY-6 Autodocs Enabled, DS-STORY-7 Viewports Aligned to Breakpoints (+14 more)

### Community 52 - "memory.py"
Cohesion: 0.19
Nodes (20): MemoryObservation, ObservationType, Typed observation linked to a memory (MEM-5; 099_memory.sql)., close_conversation(), _fires_oportunidad(), _fires_recurrencia(), _fires_riesgo(), _fires_sin_respuesta() (+12 more)

### Community 53 - "Agent Config Specification"
Cohesion: 0.11
Nodes (21): Agent Config Specification (archived), AC-1 Declarative agent/ Layout, AC-2 Single Loader with Constant Fallback, AC-3 Behavior-Preserving Extraction, AC-4 Data-Only Registry, AC-5 Strict Typed Template Rendering, AC-6 Skills as Reference Files, AC-7 DB-Migration Triggers Documented (+13 more)

### Community 54 - "ClientMemories.tsx"
Cohesion: 0.16
Nodes (16): ClientMemories(), ClientMemoriesProps, MemoryHandler, MemoryPinHandler, statusTone(), tipoTone(), ClientMemoriesView(), Default (+8 more)

### Community 55 - "compilerOptions"
Cohesion: 0.10
Nodes (19): ES2023, vite.config.ts, compilerOptions, composite, isolatedModules, lib, module, moduleDetection (+11 more)

### Community 56 - "case_update"
Cohesion: 0.14
Nodes (19): case_ack(), _case_or_404(), case_update(), cases_list(), CaseUpdateBody, BaseModel, Case, get (+11 more)

### Community 57 - "panel/routes/settings.py"
Cohesion: 0.22
Nodes (18): case_ack(), _case_or_404(), case_update(), Request, _number(), _pop_flash(), get, Request (+10 more)

### Community 58 - "Login.stories.tsx"
Cohesion: 0.15
Nodes (13): Button(), ButtonProps, Card(), CardProps, Default, Error, Loading, LoginAuth() (+5 more)

### Community 59 - "test_clients.py"
Cohesion: 0.31
Nodes (17): _login_oper(), CustomerState, spec, Clients + conversations panel views (T5.2; AP-3, AP-4, CR-3, CR-4, CR-5).…, Create a customer with one conversation, `messages` messages and a case., _seed_customer(), test_add_internal_note(), test_clients_list_lists_customers_with_state() (+9 more)

### Community 60 - "ChatWithAgent.stories.tsx"
Cohesion: 0.16
Nodes (12): AgentThinking, ChatWithAgentView(), Default, meta, roleLabel, Story, AgentChatMessage, agentChatMessages (+4 more)

### Community 61 - "Admin Panel"
Cohesion: 0.21
Nodes (17): Admin Panel, Knowledge Base, Admin Panel Specification, Knowledge Base Specification, AP-1 Authentication, AP-2 Roles and Permissions, AP-3 Clients List and Search, AP-4 Conversation View (+9 more)

### Community 62 - "services/cases.py"
Cohesion: 0.19
Nodes (16): cases_list(), get, build_deriva_bundle(), create_handoff_case(), get_or_create_case(), list_open_cases(), Case, ConversationState (+8 more)

### Community 63 - "matrix.tsx"
Cohesion: 0.14
Nodes (13): Matrix(), Matrix, meta, Story, Warning, Default, Matrix, meta (+5 more)

### Community 64 - "Dashboard.stories.tsx"
Cohesion: 0.15
Nodes (14): DashboardOverview(), DashboardOverviewProps, DashboardState, Empty, FatalError, formatWindowStart(), Loading, meta (+6 more)

### Community 65 - "test_prompts.py"
Cohesion: 0.18
Nodes (11): app/chat/nodes/ — chat node modules, Path, `agent/` declarative tree + loader coverage (config-agente-lumat). PR 1…, _read(), test_fallbacks_equal_agent_files(), test_load_returns_file_verbatim(), test_persona_files_have_no_slots(), test_prompt_classify_template() (+3 more)

### Community 66 - "Message"
Cohesion: 0.17
Nodes (15): Message, _login(), Panel JSON API dashboard KPIs (B2/T2.1; PDW-API, PDW-AUTH-1, D1, D4). GET…, No session cookie -> 401 {"detail":"unauthorized"}, never a 302., D1: same-origin only — no CORS headers on API responses., Seeded dataset -> exact KPI counts, motivos breakdown, window metadata., No data at all -> zero counts and an empty motivos breakdown., Narrowing kpi.window_days pushes out-of-window data out of the KPIs. (+7 more)

### Community 67 - "test_memory_pipeline.py"
Cohesion: 0.23
Nodes (15): clean_db(), fixture, S2 integration tests — per-turn memory pipeline (CM-7, CM-8). Scenarios mapped…, The user content of the LAST respond LLM call (after classify)., Reset chat + KB + memory tables before every test (shared test DB)., Create a customer + open conversation; returns (conversation, customer)., Append an inbound message and run the graph (replies persisted)., _respond_user_content() (+7 more)

### Community 68 - "summary.py"
Cohesion: 0.22
Nodes (14): generate_summary(), ConversationState, Customer, summary node — conversation summary at completion (CM-5). Generates a concise…, Return the prompt-template slot values for a summary render (task 3.3). The…, LLM summary persisted on conversation + case (CM-5); returns the text. Shared…, CM-5: summary at completion (capture finished); escalation summaries are…, summary() (+6 more)

### Community 69 - "panel/routes/kb.py"
Cohesion: 0.20
Nodes (16): flash(), Store a one-shot notice in the session (shown on the next page)., _doc_or_404(), kb_add(), kb_disable(), kb_edit(), kb_list(), kb_restore() (+8 more)

### Community 70 - "test_cases.py"
Cohesion: 0.33
Nodes (14): _login_oper(), spec, Cases panel view (T5.3; HH-4, AP-5, EM-4 ack). Functional suite: the…, Create customer + conversation + one case; returns the case id., Create the operador (once) and log in; returns the user id., _seed_case(), test_ack_button_hidden_after_ack(), test_ack_button_records_ack_and_audits() (+6 more)

### Community 71 - "ClientesList.stories.tsx"
Cohesion: 0.15
Nodes (12): ClientesListEmpty(), ClientesListState, ClientesListView(), columns, Default, Empty, FatalError, Loading (+4 more)

### Community 72 - "Case"
Cohesion: 0.33
Nodes (13): Case, _login_oper(), spec, Dashboard KPIs + CSV export (T5.5; AP-7, AP-8). Functional suite: the dashboard…, Seed a deterministic KPI dataset (all within the default 7-day window): - 2…, _seed_kpi_data(), test_dashboard_and_export_require_login(), test_dashboard_empty_state_shows_zero_kpis() (+5 more)

### Community 73 - "WhatsApp Webhook"
Cohesion: 0.22
Nodes (14): Meta WhatsApp Cloud API, OpenAI API, WhatsApp Webhook Specification, LumatAgent README, WH-1 Verify Handshake, WH-2 Signature Verification, WH-3 Immediate 200, WH-4 Persist Before Process (+6 more)

### Community 74 - "command"
Cohesion: 0.14
Nodes (13): command, _description, enabled, type, mcp, graphify, plugin, $schema (+5 more)

### Community 75 - "test_infra.py"
Cohesion: 0.19
Nodes (10): _load_compose(), T1.3 integration tests — local dev env (compose + .env.example, SH-2). Static…, SH-2: secrets never in repo — .env.example carries placeholders only., Deploy scripts must be executable IN THE GIT INDEX (100755), not just in the…, test_api_service_wires_health_endpoint_port(), test_compose_declares_db_media_backups_volumes(), test_compose_defines_api_and_db_services(), test_db_service_uses_pgvector_image() (+2 more)

### Community 76 - "capture.py"
Cohesion: 0.27
Nodes (12): _answer_consent(), _apply_consent_and_customer(), capture(), _current_text(), is_skip(), _next_field_after(), _persist_captured(), ConversationState (+4 more)

### Community 77 - "Propuesta Técnica y Económica Lumat"
Cohesion: 0.15
Nodes (13): Chatbot vs LumatAgent Comparison Table, Content Cleanliness, Mermaid Diagrams — 4 Required, Multi-Agent Architecture Explanation, Option Naming Convention, Output Artifacts, Quality Standards, Document Structure — 21 Sections (+5 more)

### Community 78 - "Proposal: Panel H2/H4 UI Advance (Inbox + Chat)"
Cohesion: 0.15
Nodes (13): Affected Areas, Approach, Capabilities, Dependencies, In Scope, Intent, Out of Scope, Product Assumptions & Constraints (+5 more)

### Community 79 - "Verification Report"
Cohesion: 0.15
Nodes (13): Assertion Quality, Build & Tests Execution, Changed File Coverage, Coherence (Design, B2), Completeness (B2 scope — T2.1..T2.3), Correctness (Static Evidence, B2), Issues Found, Quality Metrics (+5 more)

### Community 80 - "spec/conftest.py"
Cohesion: 0.21
Nodes (12): admin_conn(), clean_db(), fake_embedder(), migrated_db(), CompletedProcess, fixture, Shared fixtures for the spec suite (OpenSpec requirement scenarios). Sets the…, Run db/migrate.sh against the test DB (idempotent). (+4 more)

### Community 81 - "_FakeClient"
Cohesion: 0.21
Nodes (10): classify_client(), _FakeClient, _FakeCompletion, _noop_session_scope(), fixture, Mimics openai_client().chat.completions.create capturing the payload. The…, Function-typed stand-in for `with session_scope() as session:`. Yielded object…, Mock the respond node's boundaries; returns the capturing fake client. (+2 more)

### Community 82 - "Tokens.stories.tsx"
Cohesion: 0.18
Nodes (11): GROUP_ORDER, GROUP_RULES, groups, groupToken(), meta, orderedGroups, Overview, sample() (+3 more)

### Community 83 - "panel/routes/clients.py"
Cohesion: 0.29
Nodes (11): pop_flash(), Request, Read and clear the one-shot notice for this request., client_add_note(), client_ficha(), client_state_change(), clients_list(), _customer_or_404() (+3 more)

### Community 84 - "login"
Cohesion: 0.23
Nodes (12): _audit(), login(), login_form(), logout(), get, Request, Response, Session (+4 more)

### Community 85 - "list_for_entity"
Cohesion: 0.20
Nodes (12): delete(), list_for_entity(), load_customer_context(), Memory, All memories for one (scope, entity_id), newest first (MEM-2)., Delete one memory row by id (MEM-2). Raises ValueError if absent., Toggle pin and/or status on one memory (MEM-2). Raises ValueError if absent., Return the customer's memory context as text for prompt injection (CM-7). Reads… (+4 more)

### Community 86 - "Lumat Panel Design System"
Cohesion: 0.17
Nodes (12): Brand Aqua (#8BCCD5), Brand Cyan (#3D93AF), Brand Forest (#576F31), Brand Graphite (#656665), Brand Lime (#ABC333), FastAPI/Jinja Production Panel, Lumat Operational AI Assistant, Lumat Admin and Operador Roles (+4 more)

### Community 87 - "Design: Panel H2/H4 UI Advance (Inbox + Chat)"
Cohesion: 0.17
Nodes (12): Architecture Decisions (D#), Batch/PR Plan, Component/Story Structure (excludeStories + variants), Data Flow, Design: Panel H2/H4 UI Advance (Inbox + Chat), File Changes, Graph Notes, Migration / Rollout (+4 more)

### Community 88 - "tokens.css"
Cohesion: 0.17
Nodes (12): DS-TKN-1 Single Token Source, DS-TKN-2 Additive-Only Token Evolution, DS-TKN-3 Typography Scale, DS-TKN-4 Focus-Ring Token Set, DS-TKN-5 Motion Tokens, DS-TKN-6 Breakpoint Tokens, DS-TKN-7 Elevation Tokens, DS-TKN-8 Drift Guard Stays Green (+4 more)

### Community 89 - "test_seed.py"
Cohesion: 0.23
Nodes (11): _count(), CompletedProcess, T7.2 integration tests — db/seed.sh (design deploy step 4). Runs the seed…, Run db/seed.sh against the test DB with a fixed admin bootstrap env., Two runs: settings/users inserted once, audit_log untouched on re-run., The seeded rows match SETTINGS_DEFAULTS and the admin verifies (AP-1)., Missing PANEL_ADMIN_PASSWORD fails loudly instead of seeding silently., _run_seed() (+3 more)

### Community 90 - "Archive Report: Panel H2/H4 UI Advance (Inbox + Chat)"
Cohesion: 0.18
Nodes (11): Archive Audit Trail, Archive Report: Panel H2/H4 UI Advance (Inbox + Chat), Delivery State, Executive Summary, Final-State Authority, Per-Capability Delta Sync, Review Receipts (Native RDD — approved), Risks / Notes (+3 more)

### Community 91 - "Memory Specification"
Cohesion: 0.20
Nodes (10): Memory Specification, HNSW embedding index (pgvector), Hybrid semantic+FTS search, MEM-1 Schema and Migration, MEM-2 Memory Service CRUD, MEM-3 Hybrid Search, MEM-5 Observations, memories table (+2 more)

### Community 92 - "app.tsx"
Cohesion: 0.29
Nodes (6): ApiError, apiFetch(), App(), GateState, root, User

### Community 93 - "cortex-persona SKILL.md"
Cohesion: 0.29
Nodes (9): Cortex persona (Senior Architect), cortex-session skill (Planning Mode), Engram memory capture, 5-Step Execution Gate, Graph Check (Gate Step 1), Graphify knowledge graph, Ponytail Rules, SDD Pipeline integration (+1 more)

### Community 94 - "respond.py"
Cohesion: 0.27
Nodes (8): _current_text(), log_unresolved(), ConversationState, respond node — KB-grounded answers + unresolved logging (CM-4, CM-6). Only…, Answer the current message: clarification / KB-grounded / cannot-answer., CM-6: mark an inbound message as unresolved (question+context+ts)., respond(), Declarative LLM-prompt loader for the `agent/` tree (config-agente-lumat).…

### Community 95 - "Tasks: Propuesta Técnica y Económica Lumat"
Cohesion: 0.20
Nodes (9): Phase 1: Content Preparation, Phase 2: Mermaid Diagrams — 4 source files, Phase 3: HTML Wireframes — 3 source files, Phase 4: Main Document Assembly, Phase 5: CSS, Build Script, PDF, Phase 6: Verification, Phase 7: Bonus — Executive Presentation (optional), Review Workload Forecast (+1 more)

### Community 96 - "Verification Report"
Cohesion: 0.20
Nodes (9): Build & Tests Execution, Coherence (Design), Completeness, Correctness (Static Evidence), Design Deviation Report, Issues Found, Spec Compliance Matrix (Spec: propuesta-document), Verdict (+1 more)

### Community 97 - "Customer Records Specification"
Cohesion: 0.33
Nodes (10): Customer Records Specification, CR-7 Living Customer Memo on Ficha, Customer Records Specification, Customer record (ficha), CR-1 Auto-Ficha on First Contact, CR-2 Phone-Based Deduplication, CR-3 Lifecycle States, CR-4 Internal Notes (+2 more)

### Community 98 - "StatusBadge component"
Cohesion: 0.22
Nodes (10): ClientFicha panel pattern, MEM-6 Panel Management, DS-UI-LABELS Approved Spanish status labels, DS-UI-TONEFIX Correct case tone on ClientFicha, R-PRD-PG-14 Conversation State Domain, R-PRD-PG-3 Typed Mocks, R-PRD-PG-7 StatusBadge/Case Tone Maps, app/panel/api/serializers.py (+2 more)

### Community 99 - "AppShell.tsx"
Cohesion: 0.22
Nodes (7): AppShell(), AppShellProps, admin, operador, View, VIEW_LABELS, PanelView

### Community 100 - "Avatar.stories.tsx"
Cohesion: 0.27
Nodes (7): Avatar(), AvatarProps, initials(), Initials, Matrix, meta, Story

### Community 101 - "tokens.test.ts"
Cohesion: 0.27
Nodes (6): radius, spacing, componentsRoot, tokensRaw, zIndex, preview

### Community 102 - "get_by_key"
Cohesion: 0.25
Nodes (9): Any, _current_turn_text(), get_by_key(), persist_memory_session(), Return one memory by its composite key, or None when absent (MEM-2)., Flush the current turn into the session memory before END (CM-8). Accumulates…, The latest inbound user text from a rebuilt ConversationState (CM-8). Only the…, Upsert stores content with a 384-dim embedding and no duplicates. Scenario:… (+1 more)

### Community 103 - "get_current_user_json"
Cohesion: 0.25
Nodes (9): get_current_user_json(), HTTPException, Request, Session, User, Resolve the signed-session user; JSON 401 when absent (PDW-AUTH-1)., Admin-only JSON routes (PDW-API-4): operador -> 403 JSON., require_admin_json() (+1 more)

### Community 104 - "export.py"
Cohesion: 0.36
Nodes (8): _csv_response(), _csv_stream(), export_cases(), export_clients(), get, CSV export (T5.5; AP-7). GET /panel/export/clients.csv — clients with the…, Yield CSV lines from a row iterable (stdlib csv, streaming)., StreamingResponse

### Community 105 - "Base Layout Template"
Cohesion: 0.22
Nodes (9): Base Layout Template, Cases List Template, Client Ficha Template, Clients List Template, Conversation Thread Template, Dashboard Template, Knowledge Base List Template, Login Template (+1 more)

### Community 106 - "Tasks: Panel H2/H4 UI Advance"
Cohesion: 0.42
Nodes (9): Tasks: Panel H2/H4 UI Advance, Verify Report: Panel H2/H4 UI Advance, panel-h2-advance capability (H2 inbox + H4 chat), R-PRD-PG-10 24-Hour Reply Window, R-PRD-PG-11 Chat With Agent Page, R-PRD-PG-12 Dedicated Chat & Assignee Mock Shapes, R-PRD-PG-13 Verification Gates & Boundary Guards, R-PRD-PG-8 Inbox List: State, Assignee & Filter (+1 more)

### Community 107 - "test_webhook_verify.py"
Cohesion: 0.36
Nodes (8): parametrize, spec, T0.3 — webhook GET verify handshake (WH-1) and POST signature check (WH-2).…, _signature(), test_get_verify_rejects_invalid_handshake(), test_get_verify_returns_challenge_with_correct_token(), test_post_with_invalid_signature_returns_403(), test_post_with_valid_signature_returns_200()

### Community 108 - "unit/conftest.py"
Cohesion: 0.28
Nodes (8): clean_db(), migrated_db(), fixture, Path, DB-free unit test harness (config-agente-lumat, PR 1). Unit tests assert that…, No-op override — this suite never touches Postgres., No-op override — nothing to reset for a DB-free unit suite., _repo_root()

### Community 109 - "SearchInput.stories.tsx"
Cohesion: 0.28
Nodes (6): SearchInput(), SearchInputProps, Default, Matrix, meta, Story

### Community 110 - "Select.stories.tsx"
Cohesion: 0.22
Nodes (8): Default, Disabled, Matrix, meta, options, Small, Story, WithError

### Community 111 - "archive-report.md"
Cohesion: 0.36
Nodes (5): AgentChatMessage dedicated type, B1 Inbox batch, B2 Chat batch, PR #30 (B1 to main), PR #31 (B2 to B1, stacked)

### Community 112 - "PanelShell.tsx"
Cohesion: 0.29
Nodes (4): NAVIGATION, NavigationItem, PanelShell(), PanelShellProps

### Community 113 - "Button.stories.tsx"
Cohesion: 0.25
Nodes (7): Disabled, Link, Matrix, meta, Primary, Secondary, Story

### Community 114 - "Input.stories.tsx"
Cohesion: 0.25
Nodes (7): Default, Disabled, Matrix, meta, Small, Story, WithError

### Community 115 - "Design: Panel Design System"
Cohesion: 0.38
Nodes (7): Apply Progress: Panel Design System, Archive Report: Panel Design System, Design: Panel Design System, Proposal: Panel Design System, Panel Design System Spec (change delta), Tasks: Panel Design System, Verify Report: Panel Design System

### Community 116 - "Tasks: Panel H2/H4 UI Advance (Inbox + Chat)"
Cohesion: 0.29
Nodes (7): Lifecycle Gates, Notes, Phase 1 — B1 Inbox (T1.x, PR 1), Phase 2 — B2 Chat (T2.x, PR 2), Review Workload Forecast, Suggested Work Units, Tasks: Panel H2/H4 UI Advance (Inbox + Chat)

### Community 117 - "Security Hardening"
Cohesion: 0.48
Nodes (7): Security Hardening Specification, SH-1 Network and Access Hardening, SH-2 Container and Secrets Hardening, SH-3 Backups and Monitoring, SH-4 Prompt-Injection Mitigations, SH-5 Audit Log, Security Hardening

### Community 118 - "PanelEntry.stories.tsx"
Cohesion: 0.29
Nodes (6): DesktopAdmin, DesktopOperator, meta, MobileDrawerOpen, Story, TabletDrawerOpen

### Community 119 - "Textarea.stories.tsx"
Cohesion: 0.29
Nodes (6): Default, Disabled, Matrix, meta, Story, WithError

### Community 120 - "llm.py"
Cohesion: 0.40
Nodes (5): openai_client(), LLM client factory (multi-provider chat; OpenAI-compatible protocol). DeepSeek…, Return a chat-completions client for the ACTIVE provider (env, SH-2). Raises a…, OpenAI, RuntimeError

### Community 121 - "Requirement: R-PRD-PG-14 — Conversation State Domain"
Cohesion: 0.33
Nodes (5): ADDED Requirements, Delta for panel-design-system, Requirement: R-PRD-PG-14 — Conversation State Domain, Scenario: Mock domain is valid, Scenario: StatusBadge renders every domain state

### Community 122 - "AppShell.stories.tsx"
Cohesion: 0.33
Nodes (5): Admin, Matrix, meta, Operador, Story

### Community 123 - "Ponytail Review (diff over-engineering)"
Cohesion: 0.40
Nodes (5): Ponytail Audit (repo-wide), Ponytail Debt Ledger, Ponytail Help Reference Card, Ponytail Plan (pre-code review), Ponytail Review (diff over-engineering)

### Community 124 - "DS-UI-PRIMS Token-correct focus and motion"
Cohesion: 0.40
Nodes (5): DS-UI-FRAME Shared page shell and banner language, DS-UI-PRIMS Token-correct focus and motion, stories/pages/_shared helpers, primitives.css, R-PRD-PG-2 Shared Story Patterns

### Community 125 - "clean_db"
Cohesion: 0.40
Nodes (5): clean_db(), fake_embedder(), fixture, Inject a deterministic 384-d embedder; counts `.embed` calls., Reset KB tables before every test (shared test DB).

### Community 127 - "migrate.sh"
Cohesion: 0.50
Nodes (3): APP_DB_PASSWORD, DATABASE_URL, migrate.sh script

### Community 128 - "seed.sh"
Cohesion: 0.50
Nodes (3): DATABASE_URL, SEED_REPO_ROOT, seed.sh script

### Community 129 - "Milestone 1 - Bot IA de atencion al cliente"
Cohesion: 0.50
Nodes (4): Derivacion a atencion humana, Ficha del cliente y registro de conversaciones, Milestone 1 - Bot IA de atencion al cliente, Panel de administracion (M1)

### Community 130 - "Agent Registry"
Cohesion: 0.67
Nodes (3): Agent README, Orchestrator Persona, Agent Registry

### Community 133 - "Verify Report: Panel Real Design"
Cohesion: 0.67
Nodes (3): Archive Report: Panel Real Design, Spec Delta: panel-design-system (H1), Verify Report: Panel Real Design

### Community 134 - "Design: Panel Real Design"
Cohesion: 0.67
Nodes (3): Design: Panel Real Design, Exploration: Panel Real Design, Tasks: Panel Real Design

### Community 135 - "logged_client"
Cohesion: 0.67
Nodes (3): logged_client(), fixture, A TestClient already authenticated as an operador.

### Community 136 - "clean_db"
Cohesion: 0.67
Nodes (3): clean_db(), fixture, Reset chat + memory tables before every test (shared test DB).

### Community 210 - "clean_db"
Cohesion: 0.67
Nodes (3): clean_db(), fixture, Reset all customer-related tables before every test (shared test DB).

## Ambiguous Edges - Review These
- `Graphify Knowledge Graph (636 nodes / 1211 edges / 39 communities)` → `Strict TDD Compliance (7/7 checks)`  [AMBIGUOUS]
  openspec/changes/hito-1-setup-whatsapp/verify-report.md · relation: conceptually_related_to

## Knowledge Gaps
- **577 isolated node(s):** `AvatarProps`, `Story`, `SearchInputProps`, `Story`, `Story` (+572 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **53 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Graphify Knowledge Graph (636 nodes / 1211 edges / 39 communities)` and `Strict TDD Compliance (7/7 checks)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `LangGraph conversation graph` connect `Hito 1 change — Setup + WhatsApp operativo` to `graph.py`?**
  _High betweenness centrality (0.143) - this node is a cross-community bridge._
- **Are the 95 inferred relationships involving `make_user()` (e.g. with `test_json_login_invalid_credentials()` and `test_json_login_locked_account()`) actually correct?**
  _`make_user()` has 95 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `Message` (e.g. with `ConversationState` and `InvalidStateTransition`) actually correct?**
  _`Message` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `Conversation` (e.g. with `ConversationState` and `InvalidStateTransition`) actually correct?**
  _`Conversation` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Customer` (e.g. with `ConversationState` and `InvalidStateTransition`) actually correct?**
  _`Customer` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `AvatarProps`, `Story`, `SearchInputProps` to the rest of the system?**
  _577 weakly-connected nodes found - possible documentation gaps or missing edges._