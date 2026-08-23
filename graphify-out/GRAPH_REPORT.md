# Graph Report - .  (2026-08-23)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2993 nodes · 6341 edges · 225 communities (164 shown, 61 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 249 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `edd18692`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- models.py
- api/routes/auth.py
- test_prompts.py
- test_emergency_notify.py
- Message
- get_or_create_customer
- devDependencies
- Hito 1 change — Setup + WhatsApp operativo
- get_setting
- post_message
- ADDED Requirements
- CasesList.stories.tsx
- ConversationThread.stories.tsx
- test_emergency.py
- ClientMemories.tsx
- api/routes/clients.py
- ClientFicha.stories.tsx
- upsert
- test_webhook_ingest.py
- make_user
- test_api_memories.py
- test_auth.py
- test_memory_observations.py
- H1 — Setup + WhatsApp Operativo (Tasks)
- notify.py
- test_api_clients.py
- User
- memory.py
- test_handoff.py
- costs.py
- get_settings
- test_cost_guardrails.py
- matrix.tsx
- ConversationsList.stories.tsx
- Settings.stories.tsx
- test_api_auth.py
- Textarea.tsx
- test_chat_state.py
- compilerOptions
- ChatWithAgent.stories.tsx
- tests/conftest.py
- test_agent_registry.py
- serializers.py
- test_migrations.py
- test_chat_capture.py
- sweep_received
- test_send_costs.py
- test_api_cases.py
- test_kb_settings.py
- test_chat_intent.py
- AuditLog
- api/routes/settings.py
- Conversation Manager Specification
- Login.stories.tsx
- Admin Panel
- Panel Design System Specification
- KbList.stories.tsx
- panel/routes/kb.py
- services/kb.py
- Security Hardening
- Agent Config Specification
- test_clients.py
- integration/conftest.py
- test_kb.py
- compilerOptions
- _seed
- api/routes/kb.py
- build_graph
- handoff_gate
- case_update
- Dashboard.stories.tsx
- record_audit
- Settings and Scope Limits
- types.ts
- set_conversation_state
- panel/routes/settings.py
- command
- test_infra.py
- EmptyState.tsx
- capture.py
- create_handoff_case
- Propuesta Técnica y Económica Lumat
- Proposal: Panel H2/H4 UI Advance (Inbox + Chat)
- Verification Report
- spec/conftest.py
- Tokens.stories.tsx
- agent/registry.yaml
- panel/routes/clients.py
- Lumat Panel Design System
- Knowledge Base
- Design: Panel H2/H4 UI Advance (Inbox + Chat)
- tokens.css
- Button.stories.tsx
- Archive Report: Panel H2/H4 UI Advance (Inbox + Chat)
- Memory Specification
- app.tsx
- cortex-persona SKILL.md
- kpis
- Tasks: Propuesta Técnica y Económica Lumat
- Verification Report
- Customer Records Specification
- StatusBadge component
- AppShell.tsx
- tokens.test.ts
- classify_intent
- KbDocument
- get_current_user_json
- export.py
- Base Layout Template
- Tasks: Panel H2/H4 UI Advance
- test_webhook_verify.py
- unit/conftest.py
- get_current_user
- archive-report.md
- PanelShell.tsx
- Design: Panel Design System
- Tasks: Panel H2/H4 UI Advance (Inbox + Chat)
- _seed
- PanelEntry.stories.tsx
- respond
- Requirement: R-PRD-PG-14 — Conversation State Domain
- AppShell.stories.tsx
- Ponytail Review (diff over-engineering)
- DS-UI-PRIMS Token-correct focus and motion
- clean_db
- clean_db
- migrate.sh
- seed.sh
- Milestone 1 - Bot IA de atencion al cliente
- Base
- conversation_thread
- monitor.sh
- graphify.js
- Verify Report: Panel Real Design
- Design: Panel Real Design
- Panel Design System Delta Spec
- ClientesList.stories.tsx
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
- meta_message_cost
- main.ts
- Classify Persona
- Orchestrator Persona
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
- config-agente-lumat Archive Report
- config-agente-lumat Proposal
- db/migrations/*.sql (001_init, 002_customer_notes, 003_captured_data)
- Doc-Level Story Upgrades (all 10 files)
- Token Drift Guard + no-hard-coded-hex walk
- Propuesta Lumat — Entrega 1 (Resumen Ejecutivo)
- H2 Router Proposal
- Docker Compose (api + pgvector, volumes, healthcheck)
- Milestone 2 - Pagina web Lumat
- Milestone 3 - Servicios, agendamiento e integraciones
- Memoria Persistente LumatAgent Proposal
- Memoria Persistente Tasks
- Proposal: Panel Real Design — Page-First Storybook Workflow
- Memory Specification
- lumatagent
- Storybook Redesign Exploration
- tests/functional/ — CM/CR/AP suite
- CustomerState
- tests/injection/ — SH-4 suite
- Token Foundation (type/focus/motion/breakpoints/shadow)
- Index HTML (Lumat Panel root)
- Avatar.stories.tsx
- SearchInput.stories.tsx
- Select.stories.tsx
- Input.stories.tsx

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

## Communities (225 total, 61 thin omitted)

### Community 0 - "models.py"
Cohesion: 0.05
Nodes (64): Graph entry points (design: app/chat/graph.py). The conversation graph is a…, classify_intent node (CM-3, HH-3 partial, SH-4 partial). LLM classification…, cost_gate node (SS-3; design: deterministic gate before any LLM). Runs on EVERY…, emergency_gate node (EM-1, EM-2, EM-5; design: gate before any LLM).…, emergency node (EM-2, EM-3; T4.2, weak path migrated in T4.4). Runs ONLY via…, handoff_gate node — deterministic pre-LLM escalation triggers (HH-3, T4.4).…, handoff node — deriva bundle + human takeover (HH-1, HH-2, HH-3; T4.4). Reached…, ConversationState (+56 more)

### Community 1 - "api/routes/auth.py"
Cohesion: 0.05
Nodes (69): UserRole, _audit(), login(), LoginBody, logout(), me(), BaseModel, get (+61 more)

### Community 2 - "test_prompts.py"
Cohesion: 0.05
Nodes (60): app/chat/nodes/ — chat node modules, _llm_classify(), Call gpt-4o-mini with input-as-data (SH-4); returns the parsed JSON. Records…, _answer_from_kb(), Grounded answer; records the LLM cost on the current message (D6). ``brief``…, generate_summary(), ConversationState, Customer (+52 more)

### Community 3 - "test_emergency_notify.py"
Cohesion: 0.06
Nodes (60): get_or_create_conversation(), Customer, Return the open conversation for a customer; create it if none is open. Closed…, acknowledge_emergency_if_ack(), is_ack_message(), True when the customer's reply is a pure ack-keyword message. "ok" / "listo" /…, Record the customer reply-keyword ack on the emergency case (T4.3.2).…, _audit_rows() (+52 more)

### Community 4 - "Message"
Cohesion: 0.05
Nodes (75): Case, Conversation, Customer, CustomerNote, MemoryObservation, MemoryRelation, Message, Internal staff note on a customer ficha (CR-4; 002_customer_notes.sql). Staff-… (+67 more)

### Community 5 - "get_or_create_customer"
Cohesion: 0.08
Nodes (48): add_note(), customer_history(), get_or_create_customer(), list_notes(), normalize_phone_e164(), Customer, CustomerNote, CustomerState (+40 more)

### Community 6 - "devDependencies"
Cohesion: 0.04
Nodes (45): jsdom, react, react-dom, @storybook/addon-essentials, @storybook/react-vite, @testing-library/jest-dom, @testing-library/react, @testing-library/user-event (+37 more)

### Community 7 - "Hito 1 change — Setup + WhatsApp operativo"
Cohesion: 0.07
Nodes (45): admin-panel capability, arquitectura-lumatagent.md (diagrams source), conversation-manager capability, Cortex session report.md, Cortex skill pack, Cortex skill registry (.atl/skill-registry.md), Cost guardrails (spend limits + alerts), cotizacion-lumat.md (pricing source of truth) (+37 more)

### Community 8 - "get_setting"
Cohesion: 0.07
Nodes (49): _protocol_replies(), EM-3: safety instructions + contacts + technician-notified blocks., get_emergency_keywords(), get_message(), get_scope_mode(), get_setting(), get_tone(), Session (+41 more)

### Community 9 - "post_message"
Cohesion: 0.09
Nodes (40): _conversation(), _last_outbound(), _outbound_texts(), Customer, Message, spec, T6.2 functional tests — conversation-manager flows over the webhook (CM-1..6).…, Full capture: each answer stored, skip on evidence, consent -> ficha. (+32 more)

### Community 10 - "ADDED Requirements"
Cohesion: 0.05
Nodes (42): panel-h2-advance delta spec, ADDED Requirements, Delta for panel-h2-advance, Requirement: R-PRD-PG-10 — 24-Hour Reply Window, Requirement: R-PRD-PG-11 — Chat With Agent Page, Requirement: R-PRD-PG-12 — Dedicated Chat & Assignee Mock Shapes, Requirement: R-PRD-PG-13 — Verification Gates & Boundary Guards, Requirement: R-PRD-PG-8 — Inbox List: State, Assignee & Filter (+34 more)

### Community 11 - "CasesList.stories.tsx"
Cohesion: 0.09
Nodes (22): CASE_STATUSES, CaseActions(), CasesListEmpty(), CasesListState, CasesListView(), columns, Default, Empty (+14 more)

### Community 12 - "ConversationThread.stories.tsx"
Cohesion: 0.10
Nodes (26): BubbleVariant, ConversationThreadBubbles(), ConversationThreadState, ConversationThreadView(), customer, Default, Empty, Loading (+18 more)

### Community 13 - "test_emergency.py"
Cohesion: 0.09
Nodes (39): _current_text(), emergency_gate(), ConversationState, Classify the current message; store `emergency_hit` for the router. A weak hit…, classify_emergency(), compile_keywords(), fold_accents(), _keyword_fragment() (+31 more)

### Community 14 - "ClientMemories.tsx"
Cohesion: 0.16
Nodes (16): ClientMemories(), ClientMemoriesProps, MemoryHandler, MemoryPinHandler, statusTone(), tipoTone(), ClientMemoriesView(), Default (+8 more)

### Community 15 - "api/routes/clients.py"
Cohesion: 0.14
Nodes (37): CustomerState, Memory, MemoryStatus, MemoryType, Persistent, domain-aware memory row (099_memory.sql, MEM-1). Typed memories…, client_add_note(), client_ficha(), client_memories_list() (+29 more)

### Community 16 - "ClientFicha.stories.tsx"
Cohesion: 0.09
Nodes (31): Badge(), BadgeProps, BadgeTone, caseColumns, ClientFichaView(), conversationColumns, customerMemo, customerStates (+23 more)

### Community 17 - "upsert"
Cohesion: 0.07
Nodes (36): Any, _current_turn_text(), _embed(), _guard_writable_project(), hybrid_search(), persist_memory_session(), MemoryType, Create-or-update one memory by (proyecto, scope, entity_id, topic_key). Embeds… (+28 more)

### Community 18 - "test_webhook_ingest.py"
Cohesion: 0.14
Nodes (36): normalize_message(), Extract a normalized inbound message from a Meta message object. Returns None…, _count_inbound(), _count_messages(), _message(), _message_rows(), _payload(), _post() (+28 more)

### Community 19 - "make_user"
Cohesion: 0.15
Nodes (34): make_user(), Factory creating a panel user row directly (bcrypt hash) in a session., _doc_version(), _last_audit(), _login(), Panel JSON API KB + settings (B4/T4.1+T4.2; PDW-API-1/2/3/4, D1, D4). Admin-…, Seed a KB document through the service path (v1, embedded)., Limit validation mirrors the Jinja _number guard (SS-3): >= 0. (+26 more)

### Community 20 - "test_api_memories.py"
Cohesion: 0.11
Nodes (35): _login(), Memory, MemoryType, Panel JSON API memories (MEM-6; PDW-API, PDW-API-3, PDW-AUTH-1, D4, SH-5). Thin…, Only this customer's memories return, in a stable serializer shape., A customer with no memories -> empty list, no error (MEM-6)., Same topic_key -> the existing row is refreshed, not duplicated (MEM-2)., MEM-2: writers reject a non-default project before any write. The routes never… (+27 more)

### Community 21 - "test_auth.py"
Cohesion: 0.10
Nodes (34): _audit_actions(), CompletedProcess, spec, User, Panel authentication + roles (T5.1; AP-1, AP-2, SH-5). Functional suite over…, No such user -> generic error + audit row, nothing else leaks., 5 failed attempts -> locked_until set; correct password then rejected., After locked_until passes, a correct login succeeds (15-min ban ends). (+26 more)

### Community 22 - "test_memory_observations.py"
Cohesion: 0.12
Nodes (33): ObservationType, _add_inbound(), clean_db(), _close(), _memo_text(), _obs(), fixture, S3 integration tests — close event memo + observations (MEM-4, MEM-5, CM-9).… (+25 more)

### Community 23 - "H1 — Setup + WhatsApp Operativo (Tasks)"
Cohesion: 0.07
Nodes (34): Security Hardening (SH-1..5), Hardening Checklist (SH-1/2/3 executable), SH-1 Network/Access Hardening, SH-2 Container/Secrets Hardening, SH-5 Audit Log Append-Only, Ops Runbook & Meta Onboarding Checklist, Backup Restore Drill, Deploy Flow (tag + compose restart) (+26 more)

### Community 24 - "notify.py"
Cohesion: 0.19
Nodes (21): _audit_notification(), _customer_location(), _notification_body(), Case, Conversation, Customer, Session, Emergency owner/technician notification (EM-4; T4.3).… (+13 more)

### Community 25 - "test_api_clients.py"
Cohesion: 0.13
Nodes (32): CustomerState, _customer_row(), _login(), Customer, Panel JSON API clients (B2/T2.2; PDW-API, PDW-API-3, PDW-AUTH-1, D1, D4). The…, Empty result is real (service filtered) — companion to the non-empty test., search_customers limit=100 honored by the API wrapper., CR-7: the latest customer_memo appears on the ficha, as a string. (+24 more)

### Community 26 - "User"
Cohesion: 0.14
Nodes (22): User, Panel JSON API auth dependencies (design D4; PDW-AUTH-1, PDW-API-4). Parallel…, Any authenticated user (admin or operador) — shared JSON routes., require_user_json(), Panel JSON API package (design D4; PDW-API, PDW-AUTH). Additive JSON layer…, CaseUpdateBody, BaseModel, Panel JSON API cases (B3/T3.2; PDW-API, PDW-API-3, D4, D8). Thin JSON wrappers… (+14 more)

### Community 27 - "memory.py"
Cohesion: 0.12
Nodes (31): close_conversation(), delete(), _fires_oportunidad(), _fires_recurrencia(), _fires_riesgo(), _fires_sin_respuesta(), get_by_key(), list_for_entity() (+23 more)

### Community 28 - "test_handoff.py"
Cohesion: 0.13
Nodes (31): process_message(), Message, Process one inbound message: media download, conversation run, delivery. The…, _case(), _conversation_state(), _events(), T4.4 integration tests — handoff state model, gate triggers, deriva bundle.…, HH-1 "Bot to human": transition + timestamp + cause + actor recorded. (+23 more)

### Community 29 - "costs.py"
Cohesion: 0.13
Nodes (29): cost_gate(), ConversationState, Evaluate spend states, alert the owner on crossings, flag cost_mode., _alert_action(), combined_cost_mode(), conversation_spend(), daily_cost_state(), daily_spend() (+21 more)

### Community 30 - "get_settings"
Cohesion: 0.09
Nodes (26): get_settings(), Application configuration. Settings are read from environment variables ONLY…, Environment-only application settings (design: app/config.py, D3, SH-2)., Return the cached settings instance (cleared in tests via cache_clear)., Settings, BaseSettings, api_login(), clean_db() (+18 more)

### Community 31 - "test_cost_guardrails.py"
Cohesion: 0.11
Nodes (31): conversation_cost_state(), SS-3: (percent, mode) of one conversation against its limit. Total function…, _audit_actions(), _capturing_smtp(), clean_db(), no_real_smtp(), fixture, T4.5 integration tests — cost guardrails (SS-3, SS-4). Scenarios mapped from… (+23 more)

### Community 32 - "matrix.tsx"
Cohesion: 0.14
Nodes (13): Matrix(), Matrix, meta, Story, Warning, Default, Matrix, meta (+5 more)

### Community 33 - "ConversationsList.stories.tsx"
Cohesion: 0.11
Nodes (20): Status, StatusBadge(), StatusBadgeProps, statusTone, ASSIGNEE_BY_CONV, assigneeForConversation(), columns, ConversationsListEmpty() (+12 more)

### Community 34 - "Settings.stories.tsx"
Cohesion: 0.11
Nodes (20): Default, meta, Saved, Saving, ServerError, SettingsState, SettingsView(), Stale (+12 more)

### Community 35 - "test_api_auth.py"
Cohesion: 0.09
Nodes (28): _audit_actions(), User, Panel JSON API authentication (B1/T1.2; PDW-AUTH-1/2/4, PDW-API-3, D1, D4). The…, Valid JSON credentials -> 200 {ok, role}, session cookie, audit., operador credentials -> same cookie, role=operador (triangulation)., Wrong password -> 401 JSON {"detail":"invalid credentials"}, audited., No such user -> same generic 401, nothing leaks (no user oracle)., 5 failures -> lock; even a correct password returns 401 "account locked". (+20 more)

### Community 36 - "Textarea.tsx"
Cohesion: 0.13
Nodes (14): FieldShell(), FieldShellProps, Select(), SelectOption, SelectProps, options, Textarea(), TextareaProps (+6 more)

### Community 37 - "test_chat_state.py"
Cohesion: 0.12
Nodes (26): persist_replies(), Message, Session, Persist bot replies as outbound messages (status processed). The actual Meta…, Run the graph for one persisted inbound message; returns bot replies. Rebuilds…, run_conversation(), Session, Rebuild the state from the DB for one message (D2, no checkpointer). (+18 more)

### Community 38 - "compilerOptions"
Cohesion: 0.07
Nodes (27): DOM, DOM.Iterable, ES2022, node, src, vite/client, compilerOptions, erasableSyntaxOnly (+19 more)

### Community 39 - "ChatWithAgent.stories.tsx"
Cohesion: 0.16
Nodes (12): AgentThinking, ChatWithAgentView(), Default, meta, roleLabel, Story, AgentChatMessage, agentChatMessages (+4 more)

### Community 40 - "tests/conftest.py"
Cohesion: 0.10
Nodes (26): classify_result_for(), clean_db(), client(), fake_embedder(), fake_embedding(), migrated_db(), mock_meta_send(), mock_openai_chat() (+18 more)

### Community 41 - "test_agent_registry.py"
Cohesion: 0.15
Nodes (24): Agent README, Agent, _build_agent(), _build_subagent(), _coerce_optional_str_list(), _coerce_str_list(), load_registry(), Read-only startup registry reader for the multi-agent roster (H2 router). AO-2… (+16 more)

### Community 42 - "serializers.py"
Cohesion: 0.10
Nodes (25): _conversation_or_404(), conversation_thread(), Conversation, get, Session, User, Conversation metadata + chronological messages (media as URL links)., _iso() (+17 more)

### Community 43 - "test_migrations.py"
Cohesion: 0.08
Nodes (24): admin_conn(), app_conn(), clean_db(), fixture, T1.1 integration tests — schema migration + migrate.sh runner. Runs…, Acceptance: \\dt shows all tables (10 design tables + schema_migrations)., customers.phone_e164 UNIQUE (design Data Model, CR-2 dedup)., Partial unique index: inbound wamid dedup, outbound/other rows free (WH-5). (+16 more)

### Community 44 - "test_chat_capture.py"
Cohesion: 0.16
Nodes (24): list_unresolved_questions(), Message, CM-6 query (no dedicated SQL view — filter by payload flag)., Session, Context manager yielding a committed-on-success session (rollback on error)., session_scope(), clean_db(), _conversation_captured() (+16 more)

### Community 45 - "sweep_received"
Cohesion: 0.12
Nodes (22): create_app(), lifespan(), LumatAgent API application factory (design: app/main.py). `app = create_app()`…, Startup sweep: reprocess messages stuck in `received` (crash recovery). Rows…, Crash recovery: reset `processing` rows back to `received` at startup. The…, Process messages stuck in `received` (BackgroundTask + startup sweep). Claim…, reset_stale_processing(), sweep_received() (+14 more)

### Community 46 - "test_send_costs.py"
Cohesion: 0.11
Nodes (24): deliver_all_pending(), deliver_outbound(), Send every pending outbound message across conversations (sweep path)., Send one WhatsApp text message; returns the Meta wamid. Raises…, Send pending outbound rows of a conversation; record wamid + cost_meta. Only…, send_text(), clean_db(), fixture (+16 more)

### Community 47 - "test_api_cases.py"
Cohesion: 0.16
Nodes (24): _case_row(), _login(), Case, datetime, Panel JSON API cases (B3/T3.2; PDW-API, PDW-API-3, PDW-AUTH-1, D1, D4, D8).…, No session -> every cases endpoint answers 401 JSON, never a 302., closed_at set -> case excluded from the open list (HH-4)., Among escalated cases, the newest escalation comes first. (+16 more)

### Community 48 - "test_kb_settings.py"
Cohesion: 0.17
Nodes (22): login(), Login helper: authenticate as the given user through the login form., admin_client(), _last_audit(), oper_client(), fixture, spec, KB manager + settings panel views (T5.4; AP-2, AP-6, KB-3, KB-4, SS-1..5,… (+14 more)

### Community 49 - "test_chat_intent.py"
Cohesion: 0.18
Nodes (22): _case_rows(), clean_db(), mock_chat(), Case, fixture, T3.4 integration tests — classify_intent + route nodes (CM-3, HH-3, SH-4).…, Seed a customer + open conversation + one inbound received message., Intercept OpenAI /chat/completions; captures requests for SH-4 checks. (+14 more)

### Community 50 - "AuditLog"
Cohesion: 0.15
Nodes (22): AuditLog, list_audit_entries(), Admin read: newest entries first (SH-5 — admin-only at the app layer)., _all_call_texts(), _conversation_id(), _handoff_audit(), _injection_audit(), Customer (+14 more)

### Community 51 - "api/routes/settings.py"
Cohesion: 0.21
Nodes (22): KeywordsBody, LimitsBody, MetaBody, _number(), _parse_scope(), BaseModel, get, Session (+14 more)

### Community 52 - "Conversation Manager Specification"
Cohesion: 0.13
Nodes (22): CM-7 Memory Context Pre-Respond, CM-8 Turn-Time Persistence, CM-9 Close Trigger Feeds Customer Memo, CR-7 Living Customer Memo, Conversation Manager Specification, Conversation Manager Spec, Conversation summary acta (CM-5), CM-8 Turn-Time Memory Persistence (+14 more)

### Community 53 - "Login.stories.tsx"
Cohesion: 0.15
Nodes (13): Card(), CardProps, Input(), InputProps, Default, Error, Loading, LoginAuth() (+5 more)

### Community 54 - "Admin Panel"
Cohesion: 0.16
Nodes (22): Admin Panel, HH-5 Human Response Channel, Human Handoff, Admin Panel Specification, Human Handoff Specification, AP-1 Authentication, AP-2 Roles and Permissions, AP-3 Clients List and Search (+14 more)

### Community 55 - "Panel Design System Specification"
Cohesion: 0.14
Nodes (22): Panel Design System Specification, DS-STORY-1 Doc-Level Coverage for All Stories, DS-STORY-2 Description and Usage Guidance, DS-STORY-3 Interactive Controls, DS-STORY-4 Variant Matrix Story, DS-STORY-5 Accessibility Notes, DS-STORY-6 Autodocs Enabled, DS-STORY-7 Viewports Aligned to Breakpoints (+14 more)

### Community 56 - "KbList.stories.tsx"
Cohesion: 0.13
Nodes (16): columns, Default, DisableConfirmation, Empty, Error, KbListEmpty(), KbListState, KbListView() (+8 more)

### Community 57 - "panel/routes/kb.py"
Cohesion: 0.18
Nodes (20): flash(), Store a one-shot notice in the session (shown on the next page)., case_ack(), _case_or_404(), case_update(), cases_list(), get, Request (+12 more)

### Community 58 - "services/kb.py"
Cohesion: 0.15
Nodes (20): chunk_text(), _csv_rows_to_text(), _embed_cost(), embed_texts(), extract_text(), get_embedder(), ingest_document(), Decimal (+12 more)

### Community 59 - "Security Hardening"
Cohesion: 0.16
Nodes (21): Meta WhatsApp Cloud API, OpenAI API, Security Hardening Specification, WhatsApp Webhook Specification, LumatAgent README, SH-1 Network and Access Hardening, SH-2 Container and Secrets Hardening, SH-3 Backups and Monitoring (+13 more)

### Community 60 - "Agent Config Specification"
Cohesion: 0.11
Nodes (21): Agent Config Specification (archived), AC-1 Declarative agent/ Layout, AC-2 Single Loader with Constant Fallback, AC-3 Behavior-Preserving Extraction, AC-4 Data-Only Registry, AC-5 Strict Typed Template Rendering, AC-6 Skills as Reference Files, AC-7 DB-Migration Triggers Documented (+13 more)

### Community 61 - "test_clients.py"
Cohesion: 0.24
Nodes (20): logged_client(), _login_oper(), CustomerState, fixture, spec, Clients + conversations panel views (T5.2; AP-3, AP-4, CR-3, CR-4, CR-5).…, A TestClient already authenticated as an operador., Create a customer with one conversation, `messages` messages and a case. (+12 more)

### Community 62 - "integration/conftest.py"
Cohesion: 0.12
Nodes (20): classify_result_for(), client(), fake_embedder(), fake_embedding(), migrated_db(), mock_meta_send(), mock_openai_chat(), CompletedProcess (+12 more)

### Community 63 - "test_kb.py"
Cohesion: 0.18
Nodes (19): KbChunk, Semantic retrieval over the ACTIVE versions of enabled documents. Filters:…, retrieve(), _chunk_rows(), _embed(), _ingest(), _pdf_with_text(), T3.3 integration tests — KB ingestion + retrieval + versioning (KB-1..KB-4).… (+11 more)

### Community 64 - "compilerOptions"
Cohesion: 0.10
Nodes (19): ES2023, vite.config.ts, compilerOptions, composite, isolatedModules, lib, module, moduleDetection (+11 more)

### Community 65 - "_seed"
Cohesion: 0.17
Nodes (20): _append(), Create a customer + open conversation + one inbound received message., Append one inbound message to an existing conversation., Stamp a seeded message's cost columns (simulates recorded prior spend)., Rebuild state from the DB and run the compiled graph (D2)., SS-3: below 80% the flow is exactly the pre-T4.5 path., SS-3 conversation limit reached: escalate, deterministic reply, no LLM., SS-3 daily limit reached: paid LLM blocked, fallback + escalate. (+12 more)

### Community 66 - "api/routes/kb.py"
Cohesion: 0.20
Nodes (18): _doc_or_404(), kb_disable(), kb_edit(), kb_list(), kb_restore(), kb_upload(), get, Session (+10 more)

### Community 67 - "build_graph"
Cohesion: 0.16
Nodes (17): _after_capture(), _after_cost_gate(), _after_emergency_gate(), _after_handoff_gate(), _after_respond(), build_graph(), _flow_start(), ConversationState (+9 more)

### Community 68 - "handoff_gate"
Cohesion: 0.16
Nodes (17): _current_message(), evaluate_handoff(), handoff_gate(), ConversationState, Store the deterministic trigger reason for the graph router., Deterministic pre-LLM trigger evaluation; returns the reason or None., _gate_state(), ConversationState (+9 more)

### Community 69 - "case_update"
Cohesion: 0.16
Nodes (17): case_ack(), _case_or_404(), case_update(), cases_list(), Case, get, Session, User (+9 more)

### Community 70 - "Dashboard.stories.tsx"
Cohesion: 0.15
Nodes (14): DashboardOverview(), DashboardOverviewProps, DashboardState, Empty, FatalError, formatWindowStart(), Loading, meta (+6 more)

### Community 71 - "record_audit"
Cohesion: 0.14
Nodes (16): Create the initial admin user; returns (created, message). Idempotent: when the…, seed_admin(), Session, Insert one append-only audit entry and return it (caller commits)., record_audit(), disable_document(), Restore a prior version: active_version pointer flip (D8, no re-embed)., Disable a document: excluded from retrieval, content kept (KB-3). (+8 more)

### Community 72 - "Settings and Scope Limits"
Cohesion: 0.24
Nodes (16): Emergency Detection, Emergency Detection Specification, Settings and Scope Limits Specification, EM-1 Deterministic Keyword Detection, EM-2 Flow Interrupt, EM-3 Safety Instructions, EM-4 Immediate Owner/Technician Notification, EM-5 Conservative Default (+8 more)

### Community 73 - "types.ts"
Cohesion: 0.10
Nodes (26): casesData, CASE_KEYS, CASE_STATUSES, clients, CUSTOMER_STATES, CONV_STATES, CONVERSATION_KEYS, MESSAGE_KEYS (+18 more)

### Community 74 - "set_conversation_state"
Cohesion: 0.15
Nodes (14): emergency(), ConversationState, Run the safety protocol (EM-3). The gate only routes strong hits here., _escalate_reason(), handoff(), ConversationState, Label the escalation: post-classification reason > gate trigger., Escalate to a human: deriva bundle + state -> human + reply + audit. (+6 more)

### Community 75 - "panel/routes/settings.py"
Cohesion: 0.30
Nodes (13): _number(), _pop_flash(), get, Request, Settings panel views (T5.4; SS-1..5, SH-5). Admin-only (require_admin — AP-2…, Parse a decimal form value; reject invalid/negative input loudly., _save(), settings_keywords() (+5 more)

### Community 76 - "command"
Cohesion: 0.14
Nodes (13): command, _description, enabled, type, mcp, graphify, plugin, $schema (+5 more)

### Community 77 - "test_infra.py"
Cohesion: 0.19
Nodes (10): _load_compose(), T1.3 integration tests — local dev env (compose + .env.example, SH-2). Static…, SH-2: secrets never in repo — .env.example carries placeholders only., Deploy scripts must be executable IN THE GIT INDEX (100755), not just in the…, test_api_service_wires_health_endpoint_port(), test_compose_declares_db_media_backups_volumes(), test_compose_defines_api_and_db_services(), test_db_service_uses_pgvector_image() (+2 more)

### Community 78 - "EmptyState.tsx"
Cohesion: 0.24
Nodes (7): EmptyState(), EmptyStateProps, FlashMessage(), PageHeader(), PageHeaderProps, StatCard(), StatCardProps

### Community 79 - "capture.py"
Cohesion: 0.27
Nodes (12): _answer_consent(), _apply_consent_and_customer(), capture(), _current_text(), is_skip(), _next_field_after(), _persist_captured(), ConversationState (+4 more)

### Community 80 - "create_handoff_case"
Cohesion: 0.23
Nodes (13): build_deriva_bundle(), create_handoff_case(), get_or_create_case(), list_open_cases(), Case, ConversationState, Session, HH-4: pending/escalated cases (open, not closed), escalated first. The panel… (+5 more)

### Community 81 - "Propuesta Técnica y Económica Lumat"
Cohesion: 0.15
Nodes (13): Chatbot vs LumatAgent Comparison Table, Content Cleanliness, Mermaid Diagrams — 4 Required, Multi-Agent Architecture Explanation, Option Naming Convention, Output Artifacts, Quality Standards, Document Structure — 21 Sections (+5 more)

### Community 82 - "Proposal: Panel H2/H4 UI Advance (Inbox + Chat)"
Cohesion: 0.15
Nodes (13): Affected Areas, Approach, Capabilities, Dependencies, In Scope, Intent, Out of Scope, Product Assumptions & Constraints (+5 more)

### Community 83 - "Verification Report"
Cohesion: 0.15
Nodes (13): Assertion Quality, Build & Tests Execution, Changed File Coverage, Coherence (Design, B2), Completeness (B2 scope — T2.1..T2.3), Correctness (Static Evidence, B2), Issues Found, Quality Metrics (+5 more)

### Community 84 - "spec/conftest.py"
Cohesion: 0.21
Nodes (12): admin_conn(), clean_db(), fake_embedder(), migrated_db(), CompletedProcess, fixture, Shared fixtures for the spec suite (OpenSpec requirement scenarios). Sets the…, Run db/migrate.sh against the test DB (idempotent). (+4 more)

### Community 85 - "Tokens.stories.tsx"
Cohesion: 0.18
Nodes (11): GROUP_ORDER, GROUP_RULES, groups, groupToken(), meta, orderedGroups, Overview, sample() (+3 more)

### Community 86 - "agent/registry.yaml"
Cohesion: 0.20
Nodes (9): Agent Config Delta Spec, Orchestrator Agent Declaration, research_triage persona, research_triage Sub-Agent, Sub-Agent Roster Declaration, config-agente-lumat Exploration, H2 Multi-Agent Router Design, H2 Router Tasks (+1 more)

### Community 87 - "panel/routes/clients.py"
Cohesion: 0.29
Nodes (11): pop_flash(), Request, Read and clear the one-shot notice for this request., client_add_note(), client_ficha(), client_state_change(), clients_list(), _customer_or_404() (+3 more)

### Community 88 - "Lumat Panel Design System"
Cohesion: 0.17
Nodes (12): Brand Aqua (#8BCCD5), Brand Cyan (#3D93AF), Brand Forest (#576F31), Brand Graphite (#656665), Brand Lime (#ABC333), FastAPI/Jinja Production Panel, Lumat Operational AI Assistant, Lumat Admin and Operador Roles (+4 more)

### Community 89 - "Knowledge Base"
Cohesion: 0.21
Nodes (12): Docker Compose, Hostinger KVM 2 (São Paulo), Knowledge Base, LangGraph, Knowledge Base Specification, OpenSpec Project Config, pgvector, PostgreSQL (+4 more)

### Community 90 - "Design: Panel H2/H4 UI Advance (Inbox + Chat)"
Cohesion: 0.17
Nodes (12): Architecture Decisions (D#), Batch/PR Plan, Component/Story Structure (excludeStories + variants), Data Flow, Design: Panel H2/H4 UI Advance (Inbox + Chat), File Changes, Graph Notes, Migration / Rollout (+4 more)

### Community 91 - "tokens.css"
Cohesion: 0.17
Nodes (12): DS-TKN-1 Single Token Source, DS-TKN-2 Additive-Only Token Evolution, DS-TKN-3 Typography Scale, DS-TKN-4 Focus-Ring Token Set, DS-TKN-5 Motion Tokens, DS-TKN-6 Breakpoint Tokens, DS-TKN-7 Elevation Tokens, DS-TKN-8 Drift Guard Stays Green (+4 more)

### Community 92 - "Button.stories.tsx"
Cohesion: 0.25
Nodes (7): Disabled, Link, Matrix, meta, Primary, Secondary, Story

### Community 93 - "Archive Report: Panel H2/H4 UI Advance (Inbox + Chat)"
Cohesion: 0.18
Nodes (11): Archive Audit Trail, Archive Report: Panel H2/H4 UI Advance (Inbox + Chat), Delivery State, Executive Summary, Final-State Authority, Per-Capability Delta Sync, Review Receipts (Native RDD — approved), Risks / Notes (+3 more)

### Community 94 - "Memory Specification"
Cohesion: 0.20
Nodes (10): Memory Specification, HNSW embedding index (pgvector), Hybrid semantic+FTS search, MEM-1 Schema and Migration, MEM-2 Memory Service CRUD, MEM-3 Hybrid Search, MEM-5 Observations, memories table (+2 more)

### Community 95 - "app.tsx"
Cohesion: 0.29
Nodes (6): ApiError, apiFetch(), App(), GateState, root, User

### Community 96 - "cortex-persona SKILL.md"
Cohesion: 0.29
Nodes (9): Cortex persona (Senior Architect), cortex-session skill (Planning Mode), Engram memory capture, 5-Step Execution Gate, Graph Check (Gate Step 1), Graphify knowledge graph, Ponytail Rules, SDD Pipeline integration (+1 more)

### Community 97 - "kpis"
Cohesion: 0.20
Nodes (10): kpis(), get, Session, User, Dashboard KPI counts over the configured window (AP-8)., compute_kpis(), panel_home(), get (+2 more)

### Community 98 - "Tasks: Propuesta Técnica y Económica Lumat"
Cohesion: 0.20
Nodes (9): Phase 1: Content Preparation, Phase 2: Mermaid Diagrams — 4 source files, Phase 3: HTML Wireframes — 3 source files, Phase 4: Main Document Assembly, Phase 5: CSS, Build Script, PDF, Phase 6: Verification, Phase 7: Bonus — Executive Presentation (optional), Review Workload Forecast (+1 more)

### Community 99 - "Verification Report"
Cohesion: 0.20
Nodes (9): Build & Tests Execution, Coherence (Design), Completeness, Correctness (Static Evidence), Design Deviation Report, Issues Found, Spec Compliance Matrix (Spec: propuesta-document), Verdict (+1 more)

### Community 100 - "Customer Records Specification"
Cohesion: 0.33
Nodes (10): Customer Records Specification, CR-7 Living Customer Memo on Ficha, Customer Records Specification, Customer record (ficha), CR-1 Auto-Ficha on First Contact, CR-2 Phone-Based Deduplication, CR-3 Lifecycle States, CR-4 Internal Notes (+2 more)

### Community 101 - "StatusBadge component"
Cohesion: 0.22
Nodes (10): ClientFicha panel pattern, MEM-6 Panel Management, DS-UI-LABELS Approved Spanish status labels, DS-UI-TONEFIX Correct case tone on ClientFicha, R-PRD-PG-14 Conversation State Domain, R-PRD-PG-3 Typed Mocks, R-PRD-PG-7 StatusBadge/Case Tone Maps, app/panel/api/serializers.py (+2 more)

### Community 102 - "AppShell.tsx"
Cohesion: 0.22
Nodes (7): AppShell(), AppShellProps, admin, operador, View, VIEW_LABELS, PanelView

### Community 103 - "tokens.test.ts"
Cohesion: 0.27
Nodes (6): radius, spacing, componentsRoot, tokensRaw, zIndex, preview

### Community 104 - "classify_intent"
Cohesion: 0.31
Nodes (9): classify_intent(), _current_text(), is_injection(), ConversationState, Persist one unknown-intent attempt; returns the NEW total (HH-3)., Classify the current message; sets intent/case/unknown/escalate flags., Deterministic SH-4 pattern check over the raw user text., _record_unknown_intent() (+1 more)

### Community 105 - "KbDocument"
Cohesion: 0.31
Nodes (9): DocumentFormat, KbDocument, DocEditBody, DocRestoreBody, BaseModel, One retrieval result (KB-2)., RetrievedChunk, kb_chunks.embedding vector(384) round-trips via ORM (KB-1). (+1 more)

### Community 106 - "get_current_user_json"
Cohesion: 0.25
Nodes (9): get_current_user_json(), HTTPException, Request, Session, User, Resolve the signed-session user; JSON 401 when absent (PDW-AUTH-1)., Admin-only JSON routes (PDW-API-4): operador -> 403 JSON., require_admin_json() (+1 more)

### Community 107 - "export.py"
Cohesion: 0.36
Nodes (8): _csv_response(), _csv_stream(), export_cases(), export_clients(), get, CSV export (T5.5; AP-7). GET /panel/export/clients.csv — clients with the…, Yield CSV lines from a row iterable (stdlib csv, streaming)., StreamingResponse

### Community 108 - "Base Layout Template"
Cohesion: 0.22
Nodes (9): Base Layout Template, Cases List Template, Client Ficha Template, Clients List Template, Conversation Thread Template, Dashboard Template, Knowledge Base List Template, Login Template (+1 more)

### Community 109 - "Tasks: Panel H2/H4 UI Advance"
Cohesion: 0.42
Nodes (9): Tasks: Panel H2/H4 UI Advance, Verify Report: Panel H2/H4 UI Advance, panel-h2-advance capability (H2 inbox + H4 chat), R-PRD-PG-10 24-Hour Reply Window, R-PRD-PG-11 Chat With Agent Page, R-PRD-PG-12 Dedicated Chat & Assignee Mock Shapes, R-PRD-PG-13 Verification Gates & Boundary Guards, R-PRD-PG-8 Inbox List: State, Assignee & Filter (+1 more)

### Community 110 - "test_webhook_verify.py"
Cohesion: 0.36
Nodes (8): parametrize, spec, T0.3 — webhook GET verify handshake (WH-1) and POST signature check (WH-2).…, _signature(), test_get_verify_rejects_invalid_handshake(), test_get_verify_returns_challenge_with_correct_token(), test_post_with_invalid_signature_returns_403(), test_post_with_valid_signature_returns_200()

### Community 111 - "unit/conftest.py"
Cohesion: 0.28
Nodes (8): clean_db(), migrated_db(), fixture, Path, DB-free unit test harness (config-agente-lumat, PR 1). Unit tests assert that…, No-op override — this suite never touches Postgres., No-op override — nothing to reset for a DB-free unit suite., _repo_root()

### Community 112 - "get_current_user"
Cohesion: 0.29
Nodes (8): get_current_user(), HTTPException, Session, User, Resolve the signed-session user; redirect to login when absent. The session…, Admin-only routes: settings and KB management (AP-2)., _redirect_to_login(), require_admin()

### Community 113 - "archive-report.md"
Cohesion: 0.36
Nodes (5): AgentChatMessage dedicated type, B1 Inbox batch, B2 Chat batch, PR #30 (B1 to main), PR #31 (B2 to B1, stacked)

### Community 114 - "PanelShell.tsx"
Cohesion: 0.29
Nodes (4): NAVIGATION, NavigationItem, PanelShell(), PanelShellProps

### Community 115 - "Design: Panel Design System"
Cohesion: 0.38
Nodes (7): Apply Progress: Panel Design System, Archive Report: Panel Design System, Design: Panel Design System, Proposal: Panel Design System, Panel Design System Spec (change delta), Tasks: Panel Design System, Verify Report: Panel Design System

### Community 116 - "Tasks: Panel H2/H4 UI Advance (Inbox + Chat)"
Cohesion: 0.29
Nodes (7): Lifecycle Gates, Notes, Phase 1 — B1 Inbox (T1.x, PR 1), Phase 2 — B2 Chat (T2.x, PR 2), Review Workload Forecast, Suggested Work Units, Tasks: Panel H2/H4 UI Advance (Inbox + Chat)

### Community 117 - "_seed"
Cohesion: 0.33
Nodes (7): Seed a customer + open conversation + one inbound received message., HH-3/SS-1: an always_escalate category escalates regardless of answer., SS-1 default: a bot_resolve category follows the normal capture flow., _run_graph(), _seed(), test_scope_always_escalate_category_escalates(), test_scope_bot_resolve_category_does_not_escalate()

### Community 118 - "PanelEntry.stories.tsx"
Cohesion: 0.29
Nodes (6): DesktopAdmin, DesktopOperator, meta, MobileDrawerOpen, Story, TabletDrawerOpen

### Community 119 - "respond"
Cohesion: 0.40
Nodes (6): _current_text(), log_unresolved(), ConversationState, Answer the current message: clarification / KB-grounded / cannot-answer., CM-6: mark an inbound message as unresolved (question+context+ts)., respond()

### Community 120 - "Requirement: R-PRD-PG-14 — Conversation State Domain"
Cohesion: 0.33
Nodes (5): ADDED Requirements, Delta for panel-design-system, Requirement: R-PRD-PG-14 — Conversation State Domain, Scenario: Mock domain is valid, Scenario: StatusBadge renders every domain state

### Community 121 - "AppShell.stories.tsx"
Cohesion: 0.33
Nodes (5): Admin, Matrix, meta, Operador, Story

### Community 122 - "Ponytail Review (diff over-engineering)"
Cohesion: 0.40
Nodes (5): Ponytail Audit (repo-wide), Ponytail Debt Ledger, Ponytail Help Reference Card, Ponytail Plan (pre-code review), Ponytail Review (diff over-engineering)

### Community 123 - "DS-UI-PRIMS Token-correct focus and motion"
Cohesion: 0.40
Nodes (5): DS-UI-FRAME Shared page shell and banner language, DS-UI-PRIMS Token-correct focus and motion, stories/pages/_shared helpers, primitives.css, R-PRD-PG-2 Shared Story Patterns

### Community 124 - "clean_db"
Cohesion: 0.40
Nodes (5): clean_db(), fake_embedder(), fixture, Inject a deterministic 384-d embedder; counts `.embed` calls., Reset KB tables before every test (shared test DB).

### Community 125 - "clean_db"
Cohesion: 0.40
Nodes (5): clean_db(), fixture, Reset webhook-related tables before every test (shared test DB)., The in-memory rate limiter is module state; reset it per test., _reset_rate_limiter()

### Community 127 - "migrate.sh"
Cohesion: 0.50
Nodes (3): APP_DB_PASSWORD, DATABASE_URL, migrate.sh script

### Community 128 - "seed.sh"
Cohesion: 0.50
Nodes (3): DATABASE_URL, SEED_REPO_ROOT, seed.sh script

### Community 129 - "Milestone 1 - Bot IA de atencion al cliente"
Cohesion: 0.50
Nodes (4): Derivacion a atencion humana, Ficha del cliente y registro de conversaciones, Milestone 1 - Bot IA de atencion al cliente, Panel de administracion (M1)

### Community 130 - "Base"
Cohesion: 0.67
Nodes (3): Base, Declarative base for all ORM models (mapped to the migrated schema)., DeclarativeBase

### Community 131 - "conversation_thread"
Cohesion: 0.67
Nodes (3): conversation_thread(), get, Request

### Community 134 - "Verify Report: Panel Real Design"
Cohesion: 0.67
Nodes (3): Archive Report: Panel Real Design, Spec Delta: panel-design-system (H1), Verify Report: Panel Real Design

### Community 135 - "Design: Panel Real Design"
Cohesion: 0.67
Nodes (3): Design: Panel Real Design, Exploration: Panel Real Design, Tasks: Panel Real Design

### Community 136 - "Panel Design System Delta Spec"
Cohesion: 0.67
Nodes (3): Panel Design System Delta Spec, Storybook Redesign Proposal, Storybook Redesign Tasks

### Community 137 - "ClientesList.stories.tsx"
Cohesion: 0.13
Nodes (14): Button(), ButtonProps, ClientesListEmpty(), ClientesListState, ClientesListView(), columns, Default, Empty (+6 more)

### Community 138 - "clean_db"
Cohesion: 0.67
Nodes (3): clean_db(), fixture, Reset chat + settings tables before every test (shared test DB).

### Community 152 - "meta_message_cost"
Cohesion: 0.40
Nodes (5): meta_message_cost(), Service-message unit cost from settings (SS-4), default reference. T4.5…, No row / malformed dict -> the reference default (SS-4, pre-2026-10-01)., test_meta_message_cost_falls_back_to_reference_default(), test_meta_message_cost_uses_stored_settings_value()

### Community 221 - "Avatar.stories.tsx"
Cohesion: 0.27
Nodes (7): Avatar(), AvatarProps, initials(), Initials, Matrix, meta, Story

### Community 222 - "SearchInput.stories.tsx"
Cohesion: 0.28
Nodes (6): SearchInput(), SearchInputProps, Default, Matrix, meta, Story

### Community 223 - "Select.stories.tsx"
Cohesion: 0.22
Nodes (8): Default, Disabled, Matrix, meta, options, Small, Story, WithError

### Community 224 - "Input.stories.tsx"
Cohesion: 0.25
Nodes (7): Default, Disabled, Matrix, meta, Small, Story, WithError

## Ambiguous Edges - Review These
- `Graphify Knowledge Graph (636 nodes / 1211 edges / 39 communities)` → `Strict TDD Compliance (7/7 checks)`  [AMBIGUOUS]
  openspec/changes/hito-1-setup-whatsapp/verify-report.md · relation: conceptually_related_to

## Knowledge Gaps
- **589 isolated node(s):** `AppShellProps`, `View`, `CasesListState`, `Story`, `ClientFichaResponse` (+584 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **61 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Graphify Knowledge Graph (636 nodes / 1211 edges / 39 communities)` and `Strict TDD Compliance (7/7 checks)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `LangGraph conversation graph` connect `Hito 1 change — Setup + WhatsApp operativo` to `models.py`?**
  _High betweenness centrality (0.162) - this node is a cross-community bridge._
- **Are the 95 inferred relationships involving `make_user()` (e.g. with `test_json_login_invalid_credentials()` and `test_json_login_locked_account()`) actually correct?**
  _`make_user()` has 95 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `Message` (e.g. with `ConversationState` and `InvalidStateTransition`) actually correct?**
  _`Message` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `Conversation` (e.g. with `ConversationState` and `InvalidStateTransition`) actually correct?**
  _`Conversation` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Customer` (e.g. with `ConversationState` and `InvalidStateTransition`) actually correct?**
  _`Customer` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `AppShellProps`, `View`, `CasesListState` to the rest of the system?**
  _589 weakly-connected nodes found - possible documentation gaps or missing edges._