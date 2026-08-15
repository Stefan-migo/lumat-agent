# Graph Report - /run/media/stefan/Nuevo vol/Proyectos/Lumat  (2026-08-13)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1297 nodes · 2520 edges · 95 communities (67 shown, 28 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 228 edges (avg confidence: 0.73)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a756502c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Propuesta Final LumatAgent
- test_kb.py
- test_chat_capture.py
- test_webhook_ingest.py
- Task T3.5 — Capture + respond + summary + unresolved nodes
- Hito 1 change — Setup + WhatsApp operativo
- get_or_create_customer
- ingest.py
- test_chat_intent.py
- test_send_costs.py
- Weekly Technician Calendar
- models.py
- Task T5.4 — KB manager + settings views
- Batch 3 — conversation pipeline (66 tests)
- Activar protocolo de emergencia
- test_migrations.py
- Propuesta Técnica y Económica Lumat — PDF (45 págs.)
- test_chat_state.py
- Task T5.1 — Panel auth + roles
- Conversation Manager
- T2.2 Webhook ingest + tests
- Message
- graph.py
- LumatAgent — coworker digital multi-agente
- Wireframe — Dashboard Panel Admin
- Task T4.4 — Handoff + deriva + gates + tests
- conftest.py
- Opción B — Base Multi-Agente + WhatsApp (recomendada)
- package.json
- verify_post
- Security Hardening
- command
- capture.py
- Task T4.2 — emergency detection + gate
- Agenda Técnica con Google Calendar
- Router de Agentes
- docs/ops.md — Operations & Meta Onboarding Checklist
- Propuesta Técnica y Económica Lumat
- cotizacion-lumat.md — Cotización original Lumat
- Backend (Python · LangGraph · Puerto 8000)
- PostgreSQL + pgvector
- test_infra.py
- Admin Panel
- get_settings
- Cliente Ficha Screen (Lumat Admin)
- router.py
- Task T5.3 — Cases view
- Customer Records
- OpenSpec Project Config
- Conversation Manager Specification
- Memoria Mini-Engram (3 niveles: session/customer/knowledge)
- build.sh
- Knowledge Base
- verify-report.md — hito-1-setup-whatsapp change
- run_migrate
- api service (uvicorn, repo bind-mounted)
- Task T6.1 — test harness + conftest + traceability
- clean_db
- screenshot.js
- migrate.sh
- Batch 4 — settings/emergency/notify/handoff/costs
- app/__init__.py
- webhook/__init__.py
- app/panel/* — admin panel routes/templates
- apply-progress #1372 — TDD Cycle Evidence
- Modelo de datos LumatAgent (clients, visits, automations, ...)
- File Storage (Fotos / Audio)
- docs/ops.md — ops runbook
- fixture
- infra/docker-compose.yml — dev compose
- Task T6.5 — docs/ops.md runbook
- Design D2 — no checkpointer, rebuild state from DB
- Design D3 — OpenAI gpt-4o-mini + text-embedding-3-small
- Design D6 — cost columns + SQL SUM, no spend_ledger
- Design D8 — KB restore = active_version flip, no re-embed
- Design — Data Model (10 tables / enums / jsonb / vector)
- Design — KB Pipeline (HNSW m=16, ef_construction=64)
- Design — Webhook Pipeline (dedup / rate limit / media)
- CR-5 Conversation lifecycle (closed → new)
- lumatagent
- post
- T6.1 Test/env hardening fixes (conftest, caplog, README)
- T6.2 Functional suite (spec markers, non-JSON drop test)
- Docker (contenedor sin --privileged)
- FastAPI (API Gateway)
- LangGraph (state machine)
- VPS Hetzner
- TestClient
- Response

## God Nodes (most connected - your core abstractions)
1. `Message` - 44 edges
2. `get_or_create_customer()` - 40 edges
3. `Propuesta Técnica y Económica Lumat — PDF (45 págs.)` - 36 edges
4. `Customer` - 27 edges
5. `Task T5.4 — KB manager + settings views` - 23 edges
6. `Task T4.4 — Handoff + deriva + gates + tests` - 23 edges
7. `Conversation` - 22 edges
8. `get_or_create_conversation()` - 20 edges
9. `Propuesta Final LumatAgent` - 19 edges
10. `ConversationState` - 17 edges

## Surprising Connections (you probably didn't know these)
- `Web M2 (standby 3 meses)` --semantically_similar_to--> `Milestone 2 - Pagina web Lumat`  [INFERRED] [semantically similar]
  .cortex-sessions/2026-08-07-reunion-cierre/04-plan-pagos-cronograma.md → LumatRequest.md
- `LumatAgent (proyecto)` --semantically_similar_to--> `Milestone 1 - Bot IA de atencion al cliente`  [INFERRED] [semantically similar]
  .cortex-sessions/2026-08-07-reunion-cierre/propuesta-final-lumatagent.md → LumatRequest.md
- `Panel web de administracion (PWA)` --semantically_similar_to--> `Panel de administracion (M1)`  [INFERRED] [semantically similar]
  .cortex-sessions/2026-08-07-reunion-cierre/propuesta-final-lumatagent.md → LumatRequest.md
- `Detección de Emergencias y protocolo de seguridad` --semantically_similar_to--> `Botón y Protocolo de Emergencia (web)`  [INFERRED] [semantically similar]
  .cortex-sessions/2026-07-20-lumat-cotizacion-final/propuesta tecnica-economica para IA.md → .cortex-sessions/2026-07-20-lumat-cotizacion-final/propuesta-tecnica-economica-lumat.pdf
- `Propuesta Lumat — Entrega 1 (Resumen Ejecutivo)` --references--> `LumatAgent — núcleo del ecosistema`  [EXTRACTED]
  Propuesta_Lumat_Entrega_1.pdf → .cortex-sessions/2026-07-20-lumat-cotizacion-final/propuesta tecnica-economica para IA.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Integracion WhatsApp Business API (Meta)** — checklist_meta_api_meta_business_suite, checklist_meta_api_verificacion_empresa, checklist_meta_api_ventana_24h, checklist_meta_api_plantillas, checklist_meta_api_test_number [EXTRACTED 0.80]
- **Arquitectura multiagente con orquestador** — cortex_sessions_2026_08_07_reunion_cierre_propuesta_final_lumatagent_orquestador_langgraph, cortex_sessions_2026_08_07_reunion_cierre_propuesta_final_lumatagent_sub_agentes, cortex_sessions_2026_08_07_reunion_cierre_propuesta_final_lumatagent_tools_layer, cortex_sessions_2026_08_07_reunion_cierre_propuesta_final_lumatagent_roles_sistema [EXTRACTED 0.90]
- **Plan de construccion por 4 hitos** — plan_hitos_detallado_hito1, plan_hitos_detallado_hito2, plan_hitos_detallado_hito3, plan_hitos_detallado_hito4 [EXTRACTED 0.90]
- **Batch 3 conversation pipeline (customers → state → KB → intent → capture → send)** — tasks_t3_1, tasks_t3_2, tasks_t3_3, tasks_t3_4, tasks_t3_5, tasks_t3_6 [EXTRACTED 0.95]
- **Elección de opción del Milestone 1** — cortex_sessions_2026_07_20_lumat_cotizacion_final_cotizacion_lumat_opcion_a, cortex_sessions_2026_07_20_lumat_cotizacion_final_cotizacion_lumat_comparativa_m1 [EXTRACTED 0.95]
- **Módulos de la Plataforma Operacional (M3)** — propuesta_ia_milestone_3, propuesta_ia_agenda_tecnica, propuesta_ia_crm, propuesta_ia_pagos, propuesta_ia_postventa [EXTRACTED 0.95]
- **B3 TDD Cycle Evidence (apply-progress #1372, 6 rows)** — apply_progress, tasks_t3_1, tasks_t3_2, tasks_t3_3, tasks_t3_4, tasks_t3_5, tasks_t3_6 [EXTRACTED 0.95]
- **Admin Panel Navigation Menu** — cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_sidebar, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_dashboard_nav, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_clientes_nav, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_conversaciones_nav, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_casos_nav, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_agenda_nav, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_base_conocimiento_nav, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_configuracion_nav [EXTRACTED 1.00]
- **Agentes especializados del LumatAgent** — arquitectura_orchestrator, arquitectura_calendar_agent, arquitectura_automation_agent, arquitectura_notification_agent, arquitectura_report_agent [EXTRACTED 1.00]
- **Batch 4 — Settings/scope + emergency + notification + handoff + cost guardrails** — openspec_changes_hito_1_setup_whatsapp_tasks_t4_1, openspec_changes_hito_1_setup_whatsapp_tasks_t4_2, openspec_changes_hito_1_setup_whatsapp_tasks_t4_3, openspec_changes_hito_1_setup_whatsapp_tasks_t4_4, openspec_changes_hito_1_setup_whatsapp_tasks_t4_5 [EXTRACTED 1.00]
- **Batch 5 — Admin panel + CSV + KPIs** — openspec_changes_hito_1_setup_whatsapp_tasks_t5_1, openspec_changes_hito_1_setup_whatsapp_tasks_t5_2, openspec_changes_hito_1_setup_whatsapp_tasks_t5_3, openspec_changes_hito_1_setup_whatsapp_tasks_t5_4, openspec_changes_hito_1_setup_whatsapp_tasks_t5_5 [EXTRACTED 1.00]
- **Customer 360 record layout** — cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_screen, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_sidebar, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_client_header, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_contacto, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_equipos, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_visitas, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_conversaciones, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_archivos, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_notas [EXTRACTED 1.00]
- **Two 2-column grid card layout** — cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_equipos, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_visitas, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_archivos, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_notas [EXTRACTED 1.00]
- **Conversational flow pipeline** — cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_start, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_id, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_ctx, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_rag, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_ia, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_conf [EXTRACTED 1.00]
- **Cortex skill pack bootstrap workflow** — opencode_commands_cortex_init_command, opencode_commands_cortex_init_script, cortex_skill_pack, graphify_knowledge_graph, cortex_skill_registry, sdd_init_command [EXTRACTED 1.00]
- **Main Dashboard Screen** — cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_dashboard_wireframe, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_dashboard_sidebar, header_user_bar, kpi_grid, recent_cases_table, recent_activity_feed [EXTRACTED 1.00]
- **Core services behind orchestrator** — diagrama1_orchestrator, diagrama1_kb_rag, diagrama1_engine, diagrama1_panel [EXTRACTED 1.00]
- **Input channels into orchestrator** — diagrama1_whatsapp_business, diagrama1_web_lumat, diagrama1_orchestrator [EXTRACTED 1.00]
- **M3 Operational Platform modules** — diagrama1_agenda, diagrama1_crm, diagrama1_pagos, diagrama1_postventa, diagrama1_reportes [EXTRACTED 1.00]
- **Docker Compose — VPS Lumat** — cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_frontend, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_backend, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_admin, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_postgresql, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_backup, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_monitor [EXTRACTED 1.00]
- **Emergency protocol fan-out** — cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_proto, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_safety, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_notify, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_critical, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_reg_em [EXTRACTED 1.00]
- **Servicios Externos Integrados** — cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_backend, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_whatsapp_api, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_openai_api, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_google_calendar, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_transbank [EXTRACTED 1.00]
- **Flujo de Orquestación Multiagente** — cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_orch, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_router, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_ag_wa, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_ag_cal, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_ag_aut, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_ag_not, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_ag_rep [EXTRACTED 1.00]
- **H1 technical stack** — fastapi_app, langgraph_graph, postgres_pgvector, docker_compose_infra, hostinger_kvm2_vps, meta_cloud_api [EXTRACTED 1.00]
- **KPI Monitoring Suite** — kpi_grid, kpi_clientes_nuevos, kpi_solicitudes_visita, kpi_emergencias, kpi_pendientes [EXTRACTED 1.00]
- **Opciones de cotización Milestone 1** — domain_m1, domain_opcion_a, domain_opcion_b, domain_opcion_c [EXTRACTED 1.00]
- **Opciones del Milestone 1 (A/B/C)** — propuesta_ia_milestone_1, cortex_sessions_2026_07_20_lumat_cotizacion_final_cotizacion_lumat_opcion_a [EXTRACTED 1.00]
- **Persistence convergence on save** — cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_schedule, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_close, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_summary, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_save, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_end [EXTRACTED 1.00]
- **Propuesta PDF build pipeline** — propuesta_build_script, mmdc_mermaid_cli, headless_chrome_render, md_to_pdf_engine, propuesta_main_document [EXTRACTED 1.00]
- **Enrutamiento por Reverse Proxy** — cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_nginx, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_frontend, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_admin, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_backend [EXTRACTED 1.00]
- **Sistemas de Soporte Transversales** — cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_tools, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_roles, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_mem, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_ctx, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_kb [EXTRACTED 1.00]
- **Stack tecnológico global (VPS + Docker + PostgreSQL/pgvector + Python + Next.js)** — tech_vps, tech_docker, tech_postgres, tech_fastapi, tech_nextjs [EXTRACTED 1.00]
- **Stack Tecnológico Lumat** — tech_langgraph, tech_openai, tech_postgres, postgres_pgvector, tech_nextjs, tech_docker, tech_whatsapp, tech_vps [EXTRACTED 1.00]
- **Sub-agentes del LumatAgent** — arquitectura_whatsapp_agent, arquitectura_calendar_agent, arquitectura_automation_agent, arquitectura_notification_agent, arquitectura_report_agent [EXTRACTED 1.00]
- **Weekly Technician Schedule Calendar** — cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_calendar, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_time_column, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_day_column, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_slot, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_event, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_blocked_slot, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_week_nav, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_tech_selector [EXTRACTED 1.00]
- **Meta Cloud API onboarding prerequisites (T2.1 → live webhook)** — docs_ops_t2_1, docs_ops_webhook_whatsapp, docs_ops_wh_1, docs_ops_em_4 [INFERRED 0.70]
- **Dispatch Scheduling Workflow** — cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_tech_selector, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_nueva_visita_button, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_google_calendar_button, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_calendar, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_week_nav [INFERRED 0.75]
- **Primary interactions: schedule, derive, export** — cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_acciones, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_visitas, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_notas, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_back [INFERRED 0.80]
- **Case Record Lifecycle Across Specs** — shared_case_record [INFERRED 0.85]
- **Inbound WhatsApp Message Pipeline** — whatsapp-webhook_whatsapp-webhook, conversation-manager_conversation-manager, emergency-detection_emergency-detection, human-handoff_human-handoff [INFERRED 0.85]
- **Arquitectura núcleo del LumatAgent** — propuesta_ia_lumatagent, propuesta_ia_rag, propuesta_ia_base_conocimiento, propuesta_ia_panel_administrativo, propuesta_ia_postgresql_pgvector [INFERRED 0.85]
- **Security hardening scope — SH-1..5 requirements and their executing tasks (T6.3/T6.4/T6.6/T7.1)** — openspec_changes_hito_1_setup_whatsapp_tasks_sh_1, openspec_changes_hito_1_setup_whatsapp_tasks_sh_2, openspec_changes_hito_1_setup_whatsapp_tasks_sh_3, openspec_changes_hito_1_setup_whatsapp_tasks_sh_4, openspec_changes_hito_1_setup_whatsapp_tasks_sh_5, openspec_changes_hito_1_setup_whatsapp_tasks_t6_3, openspec_changes_hito_1_setup_whatsapp_tasks_t6_4, openspec_changes_hito_1_setup_whatsapp_tasks_t6_6, openspec_changes_hito_1_setup_whatsapp_tasks_t7_1 [INFERRED 0.85]

## Communities (95 total, 28 thin omitted)

### Community 0 - "Propuesta Final LumatAgent"
Cohesion: 0.06
Nodes (83): Ley 19.628 (proteccion de datos, Chile), Meta Business Suite / cuenta de negocio, Numero prepago dedicado de pruebas (SIM), Plantillas de utilidad (recordatorios, alertas, resumenes), Politica de retencion de conversaciones, Test number de Meta (numero de prueba), Ventana de 24 horas de Meta, Verificacion de la empresa ante Meta (+75 more)

### Community 1 - "test_kb.py"
Cohesion: 0.05
Nodes (68): AuditLog, DocumentFormat, KbChunk, KbDocument, list_audit_entries(), Session, Append-only audit service (SH-5). Every auditable action is recorded via…, Insert one append-only audit entry and return it (caller commits). (+60 more)

### Community 2 - "test_chat_capture.py"
Cohesion: 0.05
Nodes (66): classify_intent(), _current_text(), _get_or_create_case(), is_injection(), _llm_classify(), ConversationState, classify_intent node (CM-3, HH-3 partial, SH-4 partial). LLM classification…, Persist one unknown-intent attempt; returns the NEW total (HH-3). (+58 more)

### Community 3 - "test_webhook_ingest.py"
Cohesion: 0.09
Nodes (48): normalize_message(), Extract a normalized inbound message from a Meta message object. Returns None…, parametrize, Response, spec, clean_db(), _count_inbound(), _count_messages() (+40 more)

### Community 4 - "Task T3.5 — Capture + respond + summary + unresolved nodes"
Cohesion: 0.10
Nodes (26): clients, conversations, Requirement AP-3 — admin-panel, Requirement AP-4 — admin-panel, Requirement CM-1 — Single-Agent Flow with Menu, Requirement CM-2 — Progressive Capture, Requirement CM-4 — Authorized Technical Guidance, Requirement CM-5 — Conversation Summary (+18 more)

### Community 5 - "Hito 1 change — Setup + WhatsApp operativo"
Cohesion: 0.07
Nodes (45): admin-panel capability, arquitectura-lumatagent.md (diagrams source), conversation-manager capability, Cortex session report.md, Cortex skill pack, Cortex skill registry (.atl/skill-registry.md), Cost guardrails (spend limits + alerts), cotizacion-lumat.md (pricing source of truth) (+37 more)

### Community 6 - "get_or_create_customer"
Cohesion: 0.09
Nodes (41): add_note(), customer_history(), get_or_create_customer(), list_notes(), normalize_phone_e164(), datetime, Session, Customer records service (CR-1..CR-6; design: app/services/customers.py). One… (+33 more)

### Community 7 - "ingest.py"
Cohesion: 0.08
Nodes (33): Database engine, session factory and declarative base (design: app/db.py).…, MessageDirection, MessageType, Meta Cloud API outbound send (design: app/services/send.py; SS-4 basis).…, _change_is_message_event(), download_media(), _get_or_create_customer_and_conversation(), ingest_payload() (+25 more)

### Community 8 - "test_chat_intent.py"
Cohesion: 0.11
Nodes (32): _after_capture(), _after_respond(), build_graph(), _flow_start(), ConversationState, Mid-capture messages continue the capture sub-flow (CM-2), skipping re-…, Build the compiled conversation graph (Batch 3 wiring)., _route_path() (+24 more)

### Community 9 - "test_send_costs.py"
Cohesion: 0.11
Nodes (28): get_or_create_conversation(), Return the open conversation for a customer; create it if none is open. Closed…, deliver_all_pending(), deliver_outbound(), meta_message_cost(), Send one WhatsApp text message; returns the Meta wamid. Raises…, Service-message unit cost from settings (SS-4), default reference., Send pending outbound rows of a conversation; record wamid + cost_meta. Only… (+20 more)

### Community 10 - "Weekly Technician Calendar"
Cohesion: 0.09
Nodes (29): Lumat Admin Panel, Agenda Nav Item (active), Add Technician Action, Base de Conocimiento Nav Item, Blocked Slot (Lunch/Unavailable), Weekly Technician Calendar, Casos Nav Item, Clientes Nav Item (+21 more)

### Community 11 - "models.py"
Cohesion: 0.11
Nodes (24): Base, Declarative base for all ORM models (mapped to the migrated schema)., ConversationState, CustomerState, MessageStatus, pg_enum(), datetime, ORM models mapping the migrated schema (design Data Model, 10 tables). The… (+16 more)

### Community 12 - "Task T5.4 — KB manager + settings views"
Cohesion: 0.09
Nodes (28): kb, settings, Requirement AP-6 — admin-panel, Requirement EM-1 — emergency-detection, Requirement KB-1 — Ingestion Pipeline, Requirement KB-2 — Semantic Retrieval, Requirement KB-3 — KB Manager View (→ T5.4 deferred), Requirement KB-4 — Versioning and Re-Ingestion (+20 more)

### Community 13 - "Batch 3 — conversation pipeline (66 tests)"
Cohesion: 0.12
Nodes (24): app/services/chat_capture.py — capture + respond + summary, app/services/chat_intent.py — intent + routing (LLM), app/services/chat_state.py — chat state + conversation graph, app/services/send_costs.py — send + cost tracking, Design — Conversation Graph wiring, CM-1 Conversation manager / state, CM-5 Conversation transitions, CR-2 Customer E.164 dedup (+16 more)

### Community 14 - "Activar protocolo de emergencia"
Cohesion: 0.10
Nodes (24): Solicitar más antecedentes, Cierre con datos de contacto, ¿Respuesta confiable?, Crear ficha nueva (Nombre · Dirección · Comuna), Marcar prioridad crítica, Construcción de contexto, Derivar a operador humano, ¿Palabras de emergencia? (+16 more)

### Community 15 - "test_migrations.py"
Cohesion: 0.09
Nodes (22): admin_conn(), app_conn(), clean_db(), fixture, T1.1 integration tests — schema migration + migrate.sh runner. Runs…, customers.phone_e164 UNIQUE (design Data Model, CR-2 dedup)., Partial unique index: inbound wamid dedup, outbound/other rows free (WH-5)., HNSW index on kb_chunks.embedding with design params (KB-1). (+14 more)

### Community 16 - "Propuesta Técnica y Económica Lumat — PDF (45 págs.)"
Cohesion: 0.17
Nodes (23): Lumat — empresa de gasfitería (calefont/caldera/calefacción), Propuesta Lumat — Entrega 1 (Resumen Ejecutivo), HandCodeStudio (proveedor), Base de Conocimiento administrable, Botón y Protocolo de Emergencia (web), Catálogo de Servicios, CMS — Gestión de Contenidos, CRM — Base de Clientes con ficha única (+15 more)

### Community 17 - "test_chat_state.py"
Cohesion: 0.16
Nodes (19): persist_replies(), Session, Run the graph for one persisted inbound message; returns bot replies. Rebuilds…, Persist bot replies as outbound messages (status processed). The actual Meta…, run_conversation(), Session, Rebuild the state from the DB for one message (D2, no checkpointer)., _inbound_count() (+11 more)

### Community 18 - "Task T5.1 — Panel auth + roles"
Cohesion: 0.16
Nodes (11): db/migrations/*.sql (001_init, 002_customer_notes, 003_captured_data), Requirement AP-1 — admin-panel, Requirement AP-2 — admin-panel, Batch 1 — Infra + DB schema + migrations + local Docker dev env, Requirement AP-1, Requirement AP-2, Requirement SH-5 (append-only audit), Task T1.2 (+3 more)

### Community 19 - "Conversation Manager"
Cohesion: 0.19
Nodes (22): Conversation Manager, Emergency Detection, HH-5 Human Response Channel, Human Handoff, Emergency Detection Specification, Settings and Scope Limits Specification, CM-2 Progressive Structured Data Capture, CM-4 Authorized Technical Guidance (+14 more)

### Community 20 - "T2.2 Webhook ingest + tests"
Cohesion: 0.19
Nodes (19): WhatsApp Webhook Specification, Requirement WH-5, Requirement WH-6, Requirement WH-7, whatsapp-webhook spec (7 reqs / 10 scenarios), WH-1 Webhook verification / token mismatch, WH-2 Signature verification (HMAC gate), WH-6 Filter unsupported events (131051) (+11 more)

### Community 21 - "Message"
Cohesion: 0.22
Nodes (20): Case, Conversation, Customer, CustomerNote, Message, Internal staff note on a customer ficha (CR-4; 002_customer_notes.sql). Staff-…, InvalidStateTransition, Raised when a customer state change violates the CR-3 lifecycle. (+12 more)

### Community 22 - "graph.py"
Cohesion: 0.18
Nodes (13): Graph entry points (design: app/chat/graph.py). The conversation graph is a…, ConversationState, Receive node — first-contact greeting + menu (CM-1). Deterministic (no LLM):…, Handle the incoming message at the start of the graph run. `state.turn` counts…, receive(), route node — capture vs retrieval vs escalate paths (CM-3 flow). Deterministic…, summary node — conversation summary at completion/escalation (CM-5). Generates…, ConversationState (+5 more)

### Community 23 - "LumatAgent — coworker digital multi-agente"
Cohesion: 0.13
Nodes (18): Audit log (audit_log), Automation Agent (AA), Worker de automatizaciones, Notification Agent (NA), Orquestador (LangGraph supervisor), Report Agent (RA), Sistema de roles (dueño/admin/técnico/cliente), Router de sub-agentes (+10 more)

### Community 24 - "Wireframe — Dashboard Panel Admin"
Cohesion: 0.15
Nodes (17): Activity Event Dots, Case Status Enum, Sidebar Navigation, Wireframe — Dashboard Panel Admin, Header / User Bar, KPI: New Clients, KPI: Emergencies, KPI Cards Grid (+9 more)

### Community 25 - "Task T4.4 — Handoff + deriva + gates + tests"
Cohesion: 0.13
Nodes (16): app/chat/nodes/ — chat node modules, Requirement CM-3 — Intent and Case Classification, Requirement HH-1 — human-handoff, Requirement HH-2 — human-handoff, Requirement HH-3 — Escalation Triggers, Requirement HH-5 — human-handoff, Requirement CR-3, Requirement HH-1 (+8 more)

### Community 26 - "conftest.py"
Cohesion: 0.14
Nodes (17): classify_result_for(), client(), fake_embedding(), migrated_db(), mock_meta_send(), mock_openai_chat(), mock_openai_embeddings(), fixture (+9 more)

### Community 27 - "Opción B — Base Multi-Agente + WhatsApp (recomendada)"
Cohesion: 0.31
Nodes (15): Opción A — Chatbot IA, Cotización Lumat — PDF (Julio 2026), Milestone 1 — LumatAgent (Bot IA WhatsApp), Opción A — Chatbot IA (monolítico), Opción B — Base Multi-Agente + WhatsApp (recomendada), Opción C — LumatAgent Completo, Guía de Lectura Propuesta Lumat — PDF (versión final), Guía de Lectura — PDF (+7 more)

### Community 28 - "package.json"
Cohesion: 0.13
Nodes (14): author, dependencies, @mermaid-js/mermaid-cli, puppeteer, description, keywords, license, main (+6 more)

### Community 29 - "verify_post"
Cohesion: 0.16
Nodes (13): Response, WH-1: Meta subscribe handshake — return hub.challenge or 403., WH-2..WH-7: signature gate, persist-before-process, 200-first., verify_get(), verify_post(), Webhook verification helpers (specs WH-1, WH-2). WH-1 — GET verify handshake:…, Return the `hub.challenge` value when the handshake is valid, else None. Valid…, Verify `X-Hub-Signature-256` over the raw request body (WH-2). Returns True… (+5 more)

### Community 30 - "Security Hardening"
Cohesion: 0.21
Nodes (14): Meta WhatsApp Cloud API, OpenAI API, Security Hardening Specification, security-hardening spec (5 reqs / 8 scenarios), LumatAgent README, SH-1 Network and Access Hardening, SH-2 Container and Secrets Hardening, SH-3 Backups and Monitoring (+6 more)

### Community 31 - "command"
Cohesion: 0.14
Nodes (13): command, _description, enabled, type, mcp, graphify, plugin, $schema (+5 more)

### Community 32 - "capture.py"
Cohesion: 0.27
Nodes (12): _answer_consent(), _apply_consent_and_customer(), capture(), _current_text(), is_skip(), _next_field_after(), _persist_captured(), ConversationState (+4 more)

### Community 34 - "Task T4.2 — emergency detection + gate"
Cohesion: 0.17
Nodes (8): Requirement EM-2 — emergency-detection, Requirement EM-3 — emergency-detection, Requirement EM-5 — emergency-detection, Requirement EM-1, Requirement EM-2, Requirement EM-3, Requirement EM-5, Task T4.2 — emergency detection + gate

### Community 35 - "Agenda Técnica con Google Calendar"
Cohesion: 0.40
Nodes (6): Wireframe — Agenda de Técnicos, Wireframe — Ficha de Cliente, Agenda Técnica con Google Calendar, Anexo A — Flujo Conversacional Completo, Flujo Conversacional del asistente, Integración Google Calendar (bidireccional)

### Community 36 - "Router de Agentes"
Cohesion: 0.21
Nodes (13): Agente Automatizaciones (Reglas de Negocio), Agente Calendario (Agenda + Google Cal), Agente Notificaciones (WhatsApp + Email), Agente Reportes (KPIs + Exportación), Agente WhatsApp Atención al Cliente, Registro de Auditoría, Contexto del Cliente, Base de Conocimiento (RAG + pgvector) (+5 more)

### Community 37 - "docs/ops.md — Operations & Meta Onboarding Checklist"
Cohesion: 0.05
Nodes (49): docs/hardening.md — executable SH-1..3 checklist, DNS agente.lumat.cl (public HTTPS endpoint), EM-4 — emergency alert notifications flow, Meta utility template: emergency_alert, docs/ops.md — Operations & Meta Onboarding Checklist, Change hito-1-setup-whatsapp, Design SH-2 — env-only secrets (env_file=None), Task T2.1 — Meta Cloud API onboarding checklist (BLOCKED) (+41 more)

### Community 38 - "Propuesta Técnica y Económica Lumat"
Cohesion: 0.15
Nodes (13): Chatbot vs LumatAgent Comparison Table, Content Cleanliness, Mermaid Diagrams — 4 Required, Multi-Agent Architecture Explanation, Option Naming Convention, Output Artifacts, Quality Standards, Document Structure — 21 Sections (+5 more)

### Community 39 - "cotizacion-lumat.md — Cotización original Lumat"
Cohesion: 0.23
Nodes (12): Copia final de la Propuesta Técnica y Económica, Comparativa Chatbot vs LumatAgent, cotizacion-lumat.md — Cotización original Lumat, Resumen de inversión por milestone, GPTversion.md — Borrador narrativo de la propuesta, guia-lectura-propuesta.md — Guía de lectura, presentacion-ejecutiva-lumat.md — Presentación ejecutiva 13 slides, propuesta-tecnica-economica-lumat.md (versión con imágenes) (+4 more)

### Community 40 - "Backend (Python · LangGraph · Puerto 8000)"
Cohesion: 0.21
Nodes (12): Panel Admin (Next.js · Puerto 3001), Backend (Python · LangGraph · Puerto 8000), Backup Service (Diario · Automático), Frontend (Next.js · Puerto 3000), Google Calendar (Sincronización), Health Check / Monitoreo, Nginx Reverse Proxy (HTTPS/SSL · Let's Encrypt), OpenAI API (GPT-4o-mini) (+4 more)

### Community 41 - "PostgreSQL + pgvector"
Cohesion: 0.24
Nodes (12): Agenda Técnica (M3), CRM / Clientes (M3), PostgreSQL + pgvector, Motor IA GPT + LangGraph, Base de Conocimiento RAG, LumatAgent Orquestador Central, Pagos (M3), Panel Administrativo Next.js (+4 more)

### Community 42 - "test_infra.py"
Cohesion: 0.23
Nodes (8): _load_compose(), T1.3 integration tests — local dev env (compose + .env.example, SH-2). Static…, SH-2: secrets never in repo — .env.example carries placeholders only., test_api_service_wires_health_endpoint_port(), test_compose_declares_db_media_backups_volumes(), test_compose_defines_api_and_db_services(), test_db_service_uses_pgvector_image(), test_env_example_has_no_real_secrets()

### Community 43 - "Admin Panel"
Cohesion: 0.33
Nodes (11): Admin Panel, Admin Panel Specification, AP-1 Authentication, AP-2 Roles and Permissions, AP-3 Clients List and Search, AP-4 Conversation View, AP-5 Cases View, AP-6 KB Manager Access (+3 more)

### Community 44 - "get_settings"
Cohesion: 0.24
Nodes (8): get_settings(), Application configuration. Settings are read from environment variables ONLY…, Environment-only application settings (design: app/config.py, D3, SH-2)., Return the cached settings instance (cleared in tests via cache_clear)., Settings, BaseSettings, T0.2 — app factory + environment config. Mirrors the T0.2 runtime acceptance as…, test_missing_required_env_raises_clear_boot_error()

### Community 45 - "Cliente Ficha Screen (Lumat Admin)"
Cohesion: 0.31
Nodes (11): Quick Actions (Agendar Visita / Derivar / Exportar), Archivos del Cliente (media pills), Back to Clientes list, Client Header Card, Customer Contact Data, Conversaciones Recientes table, Equipos Registrados table, Notas Internas (+3 more)

### Community 46 - "router.py"
Cohesion: 0.31
Nodes (8): create_app(), lifespan(), LumatAgent API application factory (design: app/main.py). `app = create_app()`…, Startup sweep: reprocess messages stuck in `received` (crash recovery). Rows…, Crash recovery: reset `processing` rows back to `received` at startup. The…, reset_stale_processing(), WhatsApp webhook routes (specs WH-1..WH-7). GET /webhook/whatsapp — verify…, FastAPI

### Community 47 - "Task T5.3 — Cases view"
Cohesion: 0.17
Nodes (10): cases, Requirement AP-5 — admin-panel, Requirement EM-4 — emergency-detection, Requirement HH-4 — human-handoff, Requirement AP-5, Requirement EM-4, Requirement SH-5, Task T4.3 — Emergency notification + ack (+2 more)

### Community 48 - "Customer Records"
Cohesion: 0.42
Nodes (9): Customer Records, Customer Records Specification, CR-1 Auto-Ficha on First Contact, CR-2 Phone-Based Deduplication, CR-3 Lifecycle States, CR-4 Internal Notes, CR-5 History Linkage, CR-6 Data and Consent Recording (+1 more)

### Community 49 - "OpenSpec Project Config"
Cohesion: 0.22
Nodes (9): Docker Compose, Hostinger KVM 2 (São Paulo), LangGraph, OpenSpec Project Config, PostgreSQL, CM-1 Single-Agent Flow with Menu, HH-1 Per-Conversation State Model, 8-Category Menu (+1 more)

### Community 51 - "Conversation Manager Specification"
Cohesion: 0.33
Nodes (9): Conversation Manager Specification, Human Handoff Specification, CM-3 Intent and Case Classification, CM-5 Conversation Summary, HH-2 Deriva with History and Summary, HH-4 Case Visibility in Panel, HH-5 Human Response Channel (H1), Case Record (+1 more)

### Community 52 - "Memoria Mini-Engram (3 niveles: session/customer/knowledge)"
Cohesion: 0.14
Nodes (15): Calendar Agent (CA), Memoria Mini-Engram (3 niveles: session/customer/knowledge), Calendario propio (PostgreSQL, fuente de verdad), Captura estructurada de datos del cliente, Derivación a atención humana, Estrategia M3 (alcance base + cláusula de re-evaluación), Exportación ICS read-only (CalDAV), Identificación del cliente por teléfono (+7 more)

### Community 53 - "build.sh"
Cohesion: 0.71
Nodes (7): clean(), generate_diagrams(), generate_pdf(), generate_wireframes(), log(), build.sh script, success()

### Community 54 - "Knowledge Base"
Cohesion: 0.39
Nodes (8): Knowledge Base, Knowledge Base Specification, pgvector, CM-6 Unresolved Response Logging, KB-1 Ingestion Pipeline, KB-2 Semantic Retrieval, KB-3 KB Manager, KB-4 Versioning and Re-Ingestion

### Community 56 - "verify-report.md — hito-1-setup-whatsapp change"
Cohesion: 0.25
Nodes (8): verify-report.md — hito-1-setup-whatsapp change, tasks.md (33 task rows; header says 34), Batch 0 (PR 1) — scaffold + webhook verify, Batch 1 (PR 2) — schema / ORM / infra, Batch 2 (PR 3) — webhook ingest, T1.2 ORM + session + audit service, T1.3 Compose + env hardening, T2.1 Meta onboarding checklist (blocked on client credentials)

### Community 57 - "run_migrate"
Cohesion: 0.40
Nodes (5): CompletedProcess, Run db/migrate.sh against the test DB (idempotent)., run_migrate(), Acceptance: applies cleanly twice (idempotent)., test_migrate_applies_cleanly_twice()

### Community 58 - "api service (uvicorn, repo bind-mounted)"
Cohesion: 0.33
Nodes (7): api service (uvicorn, repo bind-mounted), db service (pgvector/pgvector:pg16), infra/docker-compose.yml — local dev environment, Named volume: backups (dumps), Named volume: db (postgres data), Named volume: media (WhatsApp media), Named volume: venv (container .venv)

### Community 59 - "Task T6.1 — test harness + conftest + traceability"
Cohesion: 0.18
Nodes (10): Requirement AP-7 — admin-panel, Requirement AP-8 — admin-panel, Design D7 — streaming CSV export via stdlib csv, Requirement AP-8, Task T5.5 — Dashboard KPIs + CSV export, Task T6.1 — test harness + conftest + traceability, Task T6.2 — functional suite (CM/CR/AP), tests/conftest.py — fixtures (pgvector, respx mocks) (+2 more)

### Community 60 - "clean_db"
Cohesion: 0.17
Nodes (9): clean_db(), fixture, Reset chat-related tables before every test (shared test DB)., clean_db(), fixture, Reset all customer-related tables before every test (shared test DB)., clean_db(), fixture (+1 more)

### Community 61 - "screenshot.js"
Cohesion: 0.50
Nodes (3): path, puppeteer, wireframes

### Community 62 - "migrate.sh"
Cohesion: 0.50
Nodes (3): APP_DB_PASSWORD, DATABASE_URL, migrate.sh script

### Community 63 - "Batch 4 — settings/emergency/notify/handoff/costs"
Cohesion: 0.50
Nodes (4): HH-3 Evidence requiring technical review, Batch 4 — settings/emergency/notify/handoff/costs, T4.1 Settings, T4.4 Handoff (media evidence review)

## Ambiguous Edges - Review These
- `Schedule Event Block` → `Emergency Event Type`  [AMBIGUOUS]
  .cortex-sessions/2026-07-20-lumat-cotizacion-final/wireframes/agenda-tecnicos.png · relation: implements
- `Task T4.3 — Emergency notification + ack` → `Task T5.3 — Cases view`  [AMBIGUOUS]
  openspec/changes/hito-1-setup-whatsapp/tasks.md · relation: conceptually_related_to
- `Requirement config.yaml (refresh/verify)` → `T0.1 — Repo scaffold + git init + config`  [AMBIGUOUS]
  openspec/changes/hito-1-setup-whatsapp/tasks.md · relation: implements

## Knowledge Gaps
- **206 isolated node(s):** `author`, `description`, `keywords`, `license`, `main` (+201 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **28 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Schedule Event Block` and `Emergency Event Type`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **What is the exact relationship between `Task T4.3 — Emergency notification + ack` and `Task T5.3 — Cases view`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Requirement config.yaml (refresh/verify)` and `T0.1 — Repo scaffold + git init + config`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **Why does `LangGraph conversation graph` connect `Hito 1 change — Setup + WhatsApp operativo` to `graph.py`?**
  _High betweenness centrality (0.199) - this node is a cross-community bridge._
- **Why does `LumatAgent Project` connect `Hito 1 change — Setup + WhatsApp operativo` to `OpenSpec Project Config`, `docs/ops.md — Operations & Meta Onboarding Checklist`, `Security Hardening`?**
  _High betweenness centrality (0.198) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `Message` (e.g. with `ConversationState` and `InvalidStateTransition`) actually correct?**
  _`Message` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Propuesta Técnica y Económica Lumat — PDF (45 págs.)` (e.g. with `Propuesta Lumat — Entrega 1 (Resumen Ejecutivo)` and `Propuesta Técnica y Económica Lumat — PDF (versión final, 59 págs.)`) actually correct?**
  _`Propuesta Técnica y Económica Lumat — PDF (45 págs.)` has 2 INFERRED edges - model-reasoned connections that need verification._