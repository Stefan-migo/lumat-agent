# Graph Report - /run/media/stefan/Nuevo vol/Proyectos/Lumat  (2026-08-13)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 876 nodes · 1623 edges · 66 communities (53 shown, 13 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 198 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c3226c49`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- WhatsApp API Onboarding
- test_webhook_ingest.py
- Verify Report — Hito 1 Setup WhatsApp (B0+B1 PASS)
- Hito 1 change — Setup + WhatsApp operativo
- Weekly Technician Calendar
- test_db.py
- Activar protocolo de emergencia
- Propuesta Técnica y Económica Lumat — PDF (45 págs.)
- test_migrations.py
- ingest.py
- Conversation Manager
- Customer
- LumatAgent — coworker digital multi-agente
- docs/ops.md — Operations & Meta Onboarding Checklist
- package.json
- T3.5 Capture + respond + summary + unresolved nodes
- T4.1 Settings service + scope rules + tone
- verify_post
- Conversation Manager Specification
- command
- conftest.py
- Router de Agentes
- Propuesta Técnica y Económica Lumat
- T5.1 Panel auth + roles
- Backend (Python · LangGraph · Puerto 8000)
- PostgreSQL + pgvector
- test_infra.py
- Admin Panel
- get_settings
- T3.1 Customers service + tests
- T5.4 KB manager + settings views
- Cliente Ficha Screen (Lumat Admin)
- LumatAgent README
- db.py
- Customer Records
- Cotización Lumat — Borrador Interno
- WhatsApp Webhook
- router.py
- T4.4 Handoff + deriva + gates + tests
- T3.6 Send + cost services + tests
- iter_inbound_messages
- cortex-init command
- build.sh
- Knowledge Base
- SH-5 Audit Log
- download_media
- screenshot.js
- migrate.sh
- models.py
- app/__init__.py
- webhook/__init__.py
- Modelo de datos LumatAgent (clients, visits, automations, ...)
- File Storage (Fotos / Audio)
- fixture
- lumatagent
- post
- Response
- Docker (contenedor sin --privileged)
- FastAPI (API Gateway)
- LangGraph (state machine)
- VPS Hetzner
- TestClient

## God Nodes (most connected - your core abstractions)
1. `Propuesta Técnica y Económica Lumat — PDF (45 págs.)` - 36 edges
2. `Base` - 22 edges
3. `Propuesta Final LumatAgent` - 19 edges
4. `Customer` - 16 edges
5. `Reporte de sesion - Plan de gestion LumatAgent` - 16 edges
6. `Conversation Manager` - 16 edges
7. `Propuesta Técnica y Económica Lumat` - 16 edges
8. `Admin Panel` - 16 edges
9. `Verify Report — Hito 1 Setup WhatsApp (B0+B1 PASS)` - 16 edges
10. `T4.4 Handoff + deriva + gates + tests` - 16 edges

## Surprising Connections (you probably didn't know these)
- `Web M2 (standby 3 meses)` --semantically_similar_to--> `Milestone 2 - Pagina web Lumat`  [INFERRED] [semantically similar]
  .cortex-sessions/2026-08-07-reunion-cierre/04-plan-pagos-cronograma.md → LumatRequest.md
- `LumatAgent (proyecto)` --semantically_similar_to--> `Milestone 1 - Bot IA de atencion al cliente`  [INFERRED] [semantically similar]
  .cortex-sessions/2026-08-07-reunion-cierre/propuesta-final-lumatagent.md → LumatRequest.md
- `Panel web de administracion (PWA)` --semantically_similar_to--> `Panel de administracion (M1)`  [INFERRED] [semantically similar]
  .cortex-sessions/2026-08-07-reunion-cierre/propuesta-final-lumatagent.md → LumatRequest.md
- `Detección de Emergencias y protocolo de seguridad` --semantically_similar_to--> `Botón y Protocolo de Emergencia (web)`  [INFERRED] [semantically similar]
  .cortex-sessions/2026-07-20-lumat-cotizacion-final/propuesta tecnica-economica para IA.md → .cortex-sessions/2026-07-20-lumat-cotizacion-final/propuesta-tecnica-economica-lumat.pdf
- `T3.2 Chat state + graph scaffold + receive node` --references--> `app/chat/graph.py — graph builder`  [EXTRACTED]
  openspec/changes/hito-1-setup-whatsapp/tasks.md → app/chat/graph.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Integracion WhatsApp Business API (Meta)** — checklist_meta_api_meta_business_suite, checklist_meta_api_verificacion_empresa, checklist_meta_api_ventana_24h, checklist_meta_api_plantillas, checklist_meta_api_test_number [EXTRACTED 0.80]
- **Arquitectura multiagente con orquestador** — cortex_sessions_2026_08_07_reunion_cierre_propuesta_final_lumatagent_orquestador_langgraph, cortex_sessions_2026_08_07_reunion_cierre_propuesta_final_lumatagent_sub_agentes, cortex_sessions_2026_08_07_reunion_cierre_propuesta_final_lumatagent_tools_layer, cortex_sessions_2026_08_07_reunion_cierre_propuesta_final_lumatagent_roles_sistema [EXTRACTED 0.90]
- **Emergency detection → notification → acknowledgement flow** — openspec_changes_hito_1_setup_whatsapp_tasks_t4_1, openspec_changes_hito_1_setup_whatsapp_tasks_t4_2, openspec_changes_hito_1_setup_whatsapp_tasks_t4_3, app_services_emergency, app_services_notify, app_chat_nodes, openspec_changes_hito_1_setup_whatsapp_tasks_em_2, openspec_changes_hito_1_setup_whatsapp_tasks_em_3, openspec_changes_hito_1_setup_whatsapp_tasks_em_4 [EXTRACTED 0.90]
- **Plan de construccion por 4 hitos** — plan_hitos_detallado_hito1, plan_hitos_detallado_hito2, plan_hitos_detallado_hito3, plan_hitos_detallado_hito4 [EXTRACTED 0.90]
- **Elección de opción del Milestone 1** — cortex_sessions_2026_07_20_lumat_cotizacion_final_cotizacion_lumat_opcion_a, cortex_sessions_2026_07_20_lumat_cotizacion_final_cotizacion_lumat_comparativa_m1 [EXTRACTED 0.95]
- **Módulos de la Plataforma Operacional (M3)** — propuesta_ia_milestone_3, propuesta_ia_agenda_tecnica, propuesta_ia_crm, propuesta_ia_pagos, propuesta_ia_postventa [EXTRACTED 0.95]
- **Eight chained PRs stacked to main (PR 1..PR 8)** — openspec_changes_hito_1_setup_whatsapp_tasks_b0, openspec_changes_hito_1_setup_whatsapp_tasks_b1, openspec_changes_hito_1_setup_whatsapp_tasks_b2, openspec_changes_hito_1_setup_whatsapp_tasks_b3, openspec_changes_hito_1_setup_whatsapp_tasks_b4, openspec_changes_hito_1_setup_whatsapp_tasks_b5, openspec_changes_hito_1_setup_whatsapp_tasks_b6, openspec_changes_hito_1_setup_whatsapp_tasks_b7 [EXTRACTED 0.95]
- **Admin Panel Navigation Menu** — cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_sidebar, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_dashboard_nav, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_clientes_nav, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_conversaciones_nav, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_casos_nav, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_agenda_nav, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_base_conocimiento_nav, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_configuracion_nav [EXTRACTED 1.00]
- **Agentes especializados del LumatAgent** — arquitectura_orchestrator, arquitectura_calendar_agent, arquitectura_automation_agent, arquitectura_notification_agent, arquitectura_report_agent [EXTRACTED 1.00]
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

## Communities (66 total, 13 thin omitted)

### Community 0 - "WhatsApp API Onboarding"
Cohesion: 0.07
Nodes (74): Ley 19.628 (proteccion de datos, Chile), Meta Business Suite / cuenta de negocio, Numero prepago dedicado de pruebas (SIM), Plantillas de utilidad (recordatorios, alertas, resumenes), Politica de retencion de conversaciones, Test number de Meta (numero de prueba), Ventana de 24 horas de Meta, Verificacion de la empresa ante Meta (+66 more)

### Community 1 - "test_webhook_ingest.py"
Cohesion: 0.09
Nodes (49): normalize_message(), normalize_phone_e164(), Extract a normalized inbound message from a Meta message object. Returns None…, Normalize a WhatsApp wa_id to E.164 (design CR-2 dedup basis). Handles: full…, parametrize, spec, clean_db(), _count_messages() (+41 more)

### Community 2 - "Verify Report — Hito 1 Setup WhatsApp (B0+B1 PASS)"
Cohesion: 0.09
Nodes (42): docs/hardening.md — SH-1..3 checklist, docs/ops.md — ops runbook, infra/backup.sh — daily pg_dump, infra/docker-compose.yml — dev compose, infra/monitor.sh — health/webhook/backup-age, infra/restore-test.sh — weekly restore drill, Tasks: Hito 1 — Setup + WhatsApp (LumatAgent), Batch 0 — Repo scaffold + webhook alive (+34 more)

### Community 3 - "Hito 1 change — Setup + WhatsApp operativo"
Cohesion: 0.10
Nodes (35): admin-panel capability, arquitectura-lumatagent.md (diagrams source), conversation-manager capability, Cost guardrails (spend limits + alerts), cotizacion-lumat.md (pricing source of truth), customer-records capability, Docker Compose infra, emergency-detection capability (+27 more)

### Community 4 - "Weekly Technician Calendar"
Cohesion: 0.09
Nodes (29): Lumat Admin Panel, Agenda Nav Item (active), Add Technician Action, Base de Conocimiento Nav Item, Blocked Slot (Lunch/Unavailable), Weekly Technician Calendar, Casos Nav Item, Clientes Nav Item (+21 more)

### Community 5 - "test_db.py"
Cohesion: 0.11
Nodes (24): AuditLog, Settings, list_audit_entries(), Session, Append-only audit service (SH-5). Every auditable action is recorded via…, Insert one append-only audit entry and return it (caller commits)., Admin read: newest entries first (SH-5 — admin-only at the app layer)., record_audit() (+16 more)

### Community 6 - "Activar protocolo de emergencia"
Cohesion: 0.10
Nodes (24): Solicitar más antecedentes, Cierre con datos de contacto, ¿Respuesta confiable?, Crear ficha nueva (Nombre · Dirección · Comuna), Marcar prioridad crítica, Construcción de contexto, Derivar a operador humano, ¿Palabras de emergencia? (+16 more)

### Community 7 - "Propuesta Técnica y Económica Lumat — PDF (45 págs.)"
Cohesion: 0.05
Nodes (81): Activity Event Dots, Copia final de la Propuesta Técnica y Económica, Case Status Enum, Memoria Mini-Engram (3 niveles: session/customer/knowledge), Comparativa Chatbot vs LumatAgent, cotizacion-lumat.md — Cotización original Lumat, Opción A — Chatbot IA, Cotización Lumat — PDF (Julio 2026) (+73 more)

### Community 8 - "test_migrations.py"
Cohesion: 0.09
Nodes (22): admin_conn(), app_conn(), clean_db(), fixture, T1.1 integration tests — schema migration + migrate.sh runner. Runs…, customers.phone_e164 UNIQUE (design Data Model, CR-2 dedup)., Partial unique index: inbound wamid dedup, outbound/other rows free (WH-5)., HNSW index on kb_chunks.embedding with design params (KB-1). (+14 more)

### Community 9 - "ingest.py"
Cohesion: 0.19
Nodes (19): Base, Declarative base for all ORM models (mapped to the migrated schema)., ConversationState, CustomerState, DocumentFormat, MessageDirection, MessageStatus, MessageType (+11 more)

### Community 10 - "Conversation Manager"
Cohesion: 0.20
Nodes (21): Conversation Manager, Emergency Detection, HH-5 Human Response Channel, Human Handoff, Emergency Detection Specification, Settings and Scope Limits Specification, CM-2 Progressive Structured Data Capture, CM-4 Authorized Technical Guidance (+13 more)

### Community 11 - "Customer"
Cohesion: 0.23
Nodes (17): Conversation, Customer, Message, _get_or_create_customer_and_conversation(), process_message(), Minimal get-or-create for the messages FK (customers/conversations). Full…, Process one inbound message: media download, then status processed. The…, Process messages stuck in `received` (BackgroundTask + startup sweep). FOR… (+9 more)

### Community 12 - "LumatAgent — coworker digital multi-agente"
Cohesion: 0.09
Nodes (25): Audit log (audit_log), Automation Agent (AA), Worker de automatizaciones, Calendar Agent (CA), Notification Agent (NA), Orquestador (LangGraph supervisor), Report Agent (RA), Sistema de roles (dueño/admin/técnico/cliente) (+17 more)

### Community 13 - "docs/ops.md — Operations & Meta Onboarding Checklist"
Cohesion: 0.13
Nodes (19): DNS agente.lumat.cl (public HTTPS endpoint), EM-4 — emergency alert notifications flow, Meta utility template: emergency_alert, docs/ops.md — Operations & Meta Onboarding Checklist, Change hito-1-setup-whatsapp, Design SH-2 — env-only secrets (env_file=None), Task T2.1 — Meta Cloud API onboarding checklist (BLOCKED), Task T6.5 — Ops runbook (placeholder) (+11 more)

### Community 15 - "package.json"
Cohesion: 0.13
Nodes (14): author, dependencies, @mermaid-js/mermaid-cli, puppeteer, description, keywords, license, main (+6 more)

### Community 16 - "T3.5 Capture + respond + summary + unresolved nodes"
Cohesion: 0.23
Nodes (14): app/chat/graph.py — graph builder, app/chat/nodes/* — chat graph nodes, app/chat/state.py — ConversationState, Batch 3 — Conversation graph + customers + KB, CM-1 · First-contact greeting + menu + resume, CM-2 · Progressive capture, CM-3 · Intent classification, CM-4 · KB-grounded responses only (+6 more)

### Community 17 - "T4.1 Settings service + scope rules + tone"
Cohesion: 0.19
Nodes (11): app/services/emergency.py — regex engine, app/services/notify.py — emergency notification, app/services/settings.py — KV settings, Batch 4 — Settings/emergency/handoff/cost guardrails, EM-1 · Emergency gate before any LLM, EM-2 · Abandon capture on emergency, EM-3 · Safety instructions + technician notified, SS-2 · Emergency keywords (+3 more)

### Community 18 - "verify_post"
Cohesion: 0.16
Nodes (13): Response, WH-1: Meta subscribe handshake — return hub.challenge or 403., WH-2..WH-7: signature gate, persist-before-process, 200-first., verify_get(), verify_post(), Webhook verification helpers (specs WH-1, WH-2). WH-1 — GET verify handshake:…, Return the `hub.challenge` value when the handshake is valid, else None. Valid…, Verify `X-Hub-Signature-256` over the raw request body (WH-2). Returns True… (+5 more)

### Community 19 - "Conversation Manager Specification"
Cohesion: 0.20
Nodes (14): LangGraph, Conversation Manager Specification, Human Handoff Specification, CM-1 Single-Agent Flow with Menu, CM-3 Intent and Case Classification, CM-5 Conversation Summary, HH-1 Per-Conversation State Model, HH-2 Deriva with History and Summary (+6 more)

### Community 20 - "command"
Cohesion: 0.14
Nodes (13): command, _description, enabled, type, mcp, graphify, plugin, $schema (+5 more)

### Community 21 - "conftest.py"
Cohesion: 0.18
Nodes (12): CompletedProcess, client(), migrated_db(), fixture, TestClient, Shared fixtures for the integration suite (T0.2; extended by T1.2/T6.1). Sets…, Run db/migrate.sh against the test DB (idempotent)., Apply migrations once per session (idempotent runner). (+4 more)

### Community 23 - "Router de Agentes"
Cohesion: 0.21
Nodes (13): Agente Automatizaciones (Reglas de Negocio), Agente Calendario (Agenda + Google Cal), Agente Notificaciones (WhatsApp + Email), Agente Reportes (KPIs + Exportación), Agente WhatsApp Atención al Cliente, Registro de Auditoría, Contexto del Cliente, Base de Conocimiento (RAG + pgvector) (+5 more)

### Community 24 - "Propuesta Técnica y Económica Lumat"
Cohesion: 0.15
Nodes (13): Chatbot vs LumatAgent Comparison Table, Content Cleanliness, Mermaid Diagrams — 4 Required, Multi-Agent Architecture Explanation, Option Naming Convention, Output Artifacts, Quality Standards, Document Structure — 21 Sections (+5 more)

### Community 25 - "T5.1 Panel auth + roles"
Cohesion: 0.23
Nodes (11): app/panel/* — admin panel routes/templates, AP-1 · Panel login + roles, AP-2 · Lockout + audit, AP-5 · Cases state change + assign, AP-7 · CSV export, AP-8 · Dashboard KPIs, Batch 5 — Admin panel + CSV + KPIs, HH-4 · Pending/escalated cases view (+3 more)

### Community 27 - "Backend (Python · LangGraph · Puerto 8000)"
Cohesion: 0.21
Nodes (12): Panel Admin (Next.js · Puerto 3001), Backend (Python · LangGraph · Puerto 8000), Backup Service (Diario · Automático), Frontend (Next.js · Puerto 3000), Google Calendar (Sincronización), Health Check / Monitoreo, Nginx Reverse Proxy (HTTPS/SSL · Let's Encrypt), OpenAI API (GPT-4o-mini) (+4 more)

### Community 28 - "PostgreSQL + pgvector"
Cohesion: 0.24
Nodes (12): Agenda Técnica (M3), CRM / Clientes (M3), PostgreSQL + pgvector, Motor IA GPT + LangGraph, Base de Conocimiento RAG, LumatAgent Orquestador Central, Pagos (M3), Panel Administrativo Next.js (+4 more)

### Community 29 - "test_infra.py"
Cohesion: 0.23
Nodes (8): _load_compose(), T1.3 integration tests — local dev env (compose + .env.example, SH-2). Static…, SH-2: secrets never in repo — .env.example carries placeholders only., test_api_service_wires_health_endpoint_port(), test_compose_declares_db_media_backups_volumes(), test_compose_defines_api_and_db_services(), test_db_service_uses_pgvector_image(), test_env_example_has_no_real_secrets()

### Community 30 - "Admin Panel"
Cohesion: 0.33
Nodes (11): Admin Panel, Admin Panel Specification, AP-1 Authentication, AP-2 Roles and Permissions, AP-3 Clients List and Search, AP-4 Conversation View, AP-5 Cases View, AP-6 KB Manager Access (+3 more)

### Community 31 - "get_settings"
Cohesion: 0.24
Nodes (8): get_settings(), Application configuration. Settings are read from environment variables ONLY…, Environment-only application settings (design: app/config.py, D3, SH-2)., Return the cached settings instance (cleared in tests via cache_clear)., Settings, BaseSettings, T0.2 — app factory + environment config. Mirrors the T0.2 runtime acceptance as…, test_missing_required_env_raises_clear_boot_error()

### Community 32 - "T3.1 Customers service + tests"
Cohesion: 0.22
Nodes (9): AP-3 · Clients list/search + ficha, AP-4 · Conversations read-only thread, CR-1 · Get-or-create customer (auto-ficha), CR-2 · E.164 normalization + dedup, CR-3 · State transitions validated, CR-5 · History query (conv/cases/messages), CR-6 · Captured data + consent store, T3.1 Customers service + tests (+1 more)

### Community 33 - "T5.4 KB manager + settings views"
Cohesion: 0.18
Nodes (11): app/services/kb.py — KB pipeline, AP-6 · KB manager view, KB-1 · Ingest PDF/MD/CSV + embeddings, KB-2 · Retrieval top_k + min_sim, KB-3 · KB manager (add/edit/disable/restore), KB-4 · Versioning + re-embed / version flip, SS-1 · Scope rules per category, SS-3 · Cost limits + conservative mode (+3 more)

### Community 34 - "Cliente Ficha Screen (Lumat Admin)"
Cohesion: 0.31
Nodes (11): Quick Actions (Agendar Visita / Derivar / Exportar), Archivos del Cliente (media pills), Back to Clientes list, Client Header Card, Customer Contact Data, Conversaciones Recientes table, Equipos Registrados table, Notas Internas (+3 more)

### Community 35 - "LumatAgent README"
Cohesion: 0.20
Nodes (11): Docker Compose, Engram persistent memory, Hostinger KVM 2 (São Paulo), LumatAgent Project, Meta WhatsApp Cloud API, OpenAI API, OpenSpec Project Config, PostgreSQL (+3 more)

### Community 36 - "db.py"
Cohesion: 0.22
Nodes (8): Session, Database engine, session factory and declarative base (design: app/db.py).…, Context manager yielding a committed-on-success session (rollback on error)., session_scope(), ingest_payload(), persist_message(), INSERT the normalized message as `received`; True when newly inserted. ON…, Persist every accepted inbound message; returns rows newly inserted. The 200 is…

### Community 38 - "Customer Records"
Cohesion: 0.42
Nodes (9): Customer Records, Customer Records Specification, CR-1 Auto-Ficha on First Contact, CR-2 Phone-Based Deduplication, CR-3 Lifecycle States, CR-4 Internal Notes, CR-5 History Linkage, CR-6 Data and Consent Recording (+1 more)

### Community 39 - "Cotización Lumat — Borrador Interno"
Cohesion: 0.25
Nodes (9): LumatAgent — Arquitectura Multi-Agente, Cotización Lumat — Borrador Interno, Estimación de Costos — Lumat, Flujo del Bot IA — Lumat, Preguntas para Lumat, Preguntas Filtradas, Session Report — Evaluación y Cotización, Roadmap M1 — LumatAgent (+1 more)

### Community 40 - "WhatsApp Webhook"
Cohesion: 0.36
Nodes (9): WhatsApp Webhook Specification, WH-1 Verify Handshake, WH-2 Signature Verification, WH-3 Immediate 200, WH-4 Persist Before Process, WH-6 Filter Unsupported Events, WH-7 Retry-Storm Tolerance, WhatsApp Webhook Endpoint (+1 more)

### Community 41 - "router.py"
Cohesion: 0.39
Nodes (6): create_app(), lifespan(), LumatAgent API application factory (design: app/main.py). `app = create_app()`…, Startup sweep: reprocess messages stuck in `received` (crash recovery)., WhatsApp webhook routes (specs WH-1..WH-7). GET /webhook/whatsapp — verify…, FastAPI

### Community 42 - "T4.4 Handoff + deriva + gates + tests"
Cohesion: 0.25
Nodes (6): EM-5 · Weak hit → escalate, never ignore, HH-1 · State transitions → conversation_events, HH-2 · Deriva bundle to cases, HH-3 · Deterministic handoff triggers, HH-5 · Persist during human state, T4.4 Handoff + deriva + gates + tests

### Community 43 - "T3.6 Send + cost services + tests"
Cohesion: 0.38
Nodes (5): app/services/costs.py — LLM/Meta costs, app/services/send.py — Meta outbound, SS-4 · Spend tracking + panel data, T3.6 Send + cost services + tests, T4.5 Cost guardrails

### Community 44 - "iter_inbound_messages"
Cohesion: 0.25
Nodes (8): _change_is_message_event(), iter_inbound_messages(), _message_error_131051(), True when a webhook change carries a `messages` payload (WH-6)., True when the change value carries Meta error 131051 (WH-6)., True when a message object carries error 131051 (WH-6, message-level)., Yield normalized inbound messages from a Meta webhook payload. Filters (WH-6):…, _value_error_131051()

### Community 45 - "cortex-init command"
Cohesion: 0.29
Nodes (8): Cortex session report.md, Cortex skill pack, Cortex skill registry (.atl/skill-registry.md), Graphify knowledge graph, cortex-init command, cortex-init.sh bootstrap script, cortex-session skill (planning mode), sdd-init command

### Community 46 - "build.sh"
Cohesion: 0.71
Nodes (7): clean(), generate_diagrams(), generate_pdf(), generate_wireframes(), log(), build.sh script, success()

### Community 47 - "Knowledge Base"
Cohesion: 0.39
Nodes (8): Knowledge Base, Knowledge Base Specification, pgvector, CM-6 Unresolved Response Logging, KB-1 Ingestion Pipeline, KB-2 Semantic Retrieval, KB-3 KB Manager, KB-4 Versioning and Re-Ingestion

### Community 50 - "SH-5 Audit Log"
Cohesion: 0.48
Nodes (7): Security Hardening Specification, SH-1 Network and Access Hardening, SH-2 Container and Secrets Hardening, SH-3 Backups and Monitoring, SH-4 Prompt-Injection Mitigations, SH-5 Audit Log, Security Hardening

### Community 52 - "download_media"
Cohesion: 0.40
Nodes (5): download_media(), Filesystem-safe filename stem derived from the wamid., Download a Meta media URL to the media volume; raise on failure. Meta lookaside…, _safe_filename(), Path

### Community 53 - "screenshot.js"
Cohesion: 0.50
Nodes (3): path, puppeteer, wireframes

### Community 54 - "migrate.sh"
Cohesion: 0.50
Nodes (3): APP_DB_PASSWORD, DATABASE_URL, migrate.sh script

### Community 55 - "models.py"
Cohesion: 0.16
Nodes (14): Case, ConversationEvent, KbChunk, KbDocument, pg_enum(), ORM models mapping the migrated schema (design Data Model, 10 tables). The…, PG-native Enum that stores the *member values* (labels in 001_init.sql).…, _ts() (+6 more)

## Ambiguous Edges - Review These
- `Schedule Event Block` → `Emergency Event Type`  [AMBIGUOUS]
  .cortex-sessions/2026-07-20-lumat-cotizacion-final/wireframes/agenda-tecnicos.png · relation: implements

## Knowledge Gaps
- **166 isolated node(s):** `author`, `description`, `keywords`, `license`, `main` (+161 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Schedule Event Block` and `Emergency Event Type`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **Why does `SH-5 Audit Log` connect `SH-5 Audit Log` to `T5.4 KB manager + settings views`, `Verify Report — Hito 1 Setup WhatsApp (B0+B1 PASS)`, `T4.4 Handoff + deriva + gates + tests`, `T4.1 Settings service + scope rules + tone`, `T5.1 Panel auth + roles`, `Admin Panel`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `LumatAgent Project` connect `LumatAgent README` to `Hito 1 change — Setup + WhatsApp operativo`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `LumatAgent README` connect `LumatAgent README` to `WhatsApp Webhook`, `SH-5 Audit Log`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Propuesta Técnica y Económica Lumat — PDF (45 págs.)` (e.g. with `Propuesta Lumat — Entrega 1 (Resumen Ejecutivo)` and `Propuesta Técnica y Económica Lumat — PDF (versión final, 59 págs.)`) actually correct?**
  _`Propuesta Técnica y Económica Lumat — PDF (45 págs.)` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `Base` (e.g. with `AuditLog` and `Case`) actually correct?**
  _`Base` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `Customer` (e.g. with `Base` and `MediaDownloadError`) actually correct?**
  _`Customer` has 4 INFERRED edges - model-reasoned connections that need verification._