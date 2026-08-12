# Graph Report - .  (2026-08-12)

## Corpus Check
- 72 files · ~125,250 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 475 nodes · 809 edges · 32 communities (26 shown, 6 thin omitted)
- Extraction: 81% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 149 edges (avg confidence: 0.75)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Meta API & Legal Setup
- Proposal & Pricing Options
- Architecture Agents & Services
- Core Capabilities & Infra
- Admin Panel Wireframes
- Conversational Flow Diagram
- Dashboard & Case States
- Conversation & Emergency Reqs
- Build & Diagram Tooling
- OpenCode & Graphify Config
- Admin & Customer Reqs
- Multi-Agent Architecture
- Proposal Quality Standards
- Infrastructure Diagram
- General Architecture Diagram
- Feature Requirements Mix
- Customer Record Wireframe
- Security & Webhook Reqs
- Safety & Escalation Reqs
- Cortex Workflow & Skills
- Early Quotation Docs
- KB & Admin Requirements
- Build Scripts
- Conversation Core Patterns
- Screenshot Tooling
- Data Model
- File Storage
- Tech: Docker
- Tech: FastAPI
- Tech: LangGraph
- Tech: VPS

## God Nodes (most connected - your core abstractions)
1. `Propuesta Técnica y Económica Lumat — PDF (45 págs.)` - 36 edges
2. `Propuesta Final LumatAgent` - 19 edges
3. `Reporte de sesion - Plan de gestion LumatAgent` - 16 edges
4. `Admin Panel` - 16 edges
5. `Conversation Manager` - 16 edges
6. `Propuesta Técnica y Económica Lumat` - 16 edges
7. `Requerimientos de servidor e infraestructura` - 15 edges
8. `Hito 1 change — Setup + WhatsApp operativo` - 15 edges
9. `Checklist de activacion de la WhatsApp Business API` - 14 edges
10. `LumatRequest.md` - 13 edges

## Surprising Connections (you probably didn't know these)
- `Web M2 (standby 3 meses)` --semantically_similar_to--> `Milestone 2 - Pagina web Lumat`  [INFERRED] [semantically similar]
  .cortex-sessions/2026-08-07-reunion-cierre/04-plan-pagos-cronograma.md → LumatRequest.md
- `Detección de Emergencias y protocolo de seguridad` --semantically_similar_to--> `Botón y Protocolo de Emergencia (web)`  [INFERRED] [semantically similar]
  .cortex-sessions/2026-07-20-lumat-cotizacion-final/propuesta tecnica-economica para IA.md → .cortex-sessions/2026-07-20-lumat-cotizacion-final/propuesta-tecnica-economica-lumat.pdf
- `LumatAgent (proyecto)` --semantically_similar_to--> `Milestone 1 - Bot IA de atencion al cliente`  [INFERRED] [semantically similar]
  .cortex-sessions/2026-08-07-reunion-cierre/propuesta-final-lumatagent.md → LumatRequest.md
- `Panel web de administracion (PWA)` --semantically_similar_to--> `Panel de administracion (M1)`  [INFERRED] [semantically similar]
  .cortex-sessions/2026-08-07-reunion-cierre/propuesta-final-lumatagent.md → LumatRequest.md
- `Propuesta Lumat — Entrega 1 (Resumen Ejecutivo)` --references--> `LumatAgent — núcleo del ecosistema`  [EXTRACTED]
  Propuesta_Lumat_Entrega_1.pdf → .cortex-sessions/2026-07-20-lumat-cotizacion-final/propuesta tecnica-economica para IA.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Sub-agentes del LumatAgent** — arquitectura_whatsapp_agent, arquitectura_calendar_agent, arquitectura_automation_agent, arquitectura_notification_agent, arquitectura_report_agent [EXTRACTED 1.00]
- **Stack tecnológico global (VPS + Docker + PostgreSQL/pgvector + Python + Next.js)** — tech_vps, tech_docker, tech_postgres, tech_fastapi, tech_nextjs [EXTRACTED 1.00]
- **Opciones de cotización Milestone 1** — domain_m1, domain_opcion_a, domain_opcion_b, domain_opcion_c [EXTRACTED 1.00]
- **Elección de opción del Milestone 1** — cortex_sessions_2026_07_20_lumat_cotizacion_final_cotizacion_lumat_opcion_a, cortex_sessions_2026_07_20_lumat_cotizacion_final_cotizacion_lumat_opcion_b, cortex_sessions_2026_07_20_lumat_cotizacion_final_cotizacion_lumat_opcion_c, cortex_sessions_2026_07_20_lumat_cotizacion_final_cotizacion_lumat_comparativa_m1 [EXTRACTED 0.95]
- **Módulos de la Plataforma Operacional (M3)** — propuesta_ia_milestone_3, propuesta_ia_agenda_tecnica, propuesta_ia_crm, propuesta_ia_pagos, propuesta_ia_postventa [EXTRACTED 0.95]
- **Arquitectura núcleo del LumatAgent** — propuesta_ia_lumatagent, propuesta_ia_rag, propuesta_ia_base_conocimiento, propuesta_ia_panel_administrativo, propuesta_ia_postgresql_pgvector [INFERRED 0.85]
- **Plan de construccion por 4 hitos** — plan_hitos_detallado_hito1, plan_hitos_detallado_hito2, plan_hitos_detallado_hito3, plan_hitos_detallado_hito4 [EXTRACTED 0.90]
- **Arquitectura multiagente con orquestador** — cortex_sessions_2026_08_07_reunion_cierre_propuesta_final_lumatagent_orquestador_langgraph, cortex_sessions_2026_08_07_reunion_cierre_propuesta_final_lumatagent_sub_agentes, cortex_sessions_2026_08_07_reunion_cierre_propuesta_final_lumatagent_tools_layer, cortex_sessions_2026_08_07_reunion_cierre_propuesta_final_lumatagent_roles_sistema [EXTRACTED 0.90]
- **Integracion WhatsApp Business API (Meta)** — checklist_meta_api_meta_cloud_api, checklist_meta_api_meta_business_suite, checklist_meta_api_verificacion_empresa, checklist_meta_api_ventana_24h, checklist_meta_api_plantillas, checklist_meta_api_test_number [EXTRACTED 0.80]
- **Cortex skill pack bootstrap workflow** — opencode_commands_cortex_init_command, opencode_commands_cortex_init_script, cortex_skill_pack, graphify_knowledge_graph, cortex_skill_registry, sdd_init_command [EXTRACTED 1.00]
- **Propuesta PDF build pipeline** — propuesta_build_script, mmdc_mermaid_cli, headless_chrome_render, md_to_pdf_engine, propuesta_main_document [EXTRACTED 1.00]
- **H1 technical stack** — fastapi_app, langgraph_graph, postgres_pgvector, docker_compose_infra, hostinger_kvm2_vps, meta_cloud_api [EXTRACTED 1.00]
- **Inbound WhatsApp Message Pipeline** — whatsapp-webhook_whatsapp-webhook, conversation-manager_conversation-manager, emergency-detection_emergency-detection, human-handoff_human-handoff [INFERRED 0.85]
- **Case Record Lifecycle Across Specs** — shared_case_record, admin-panel_AP-5, conversation-manager_CM-3, conversation-manager_CM-5, human-handoff_HH-2, human-handoff_HH-4, emergency-detection_EM-4, customer-records_CR-5 [INFERRED 0.85]
- **Emergency Response Protocol** — emergency-detection_EM-1, emergency-detection_EM-2, emergency-detection_EM-4, settings-scope-limits_SS-2, human-handoff_HH-3, security-hardening_SH-5 [INFERRED 0.80]
- **Opciones del Milestone 1 (A/B/C)** — propuesta_ia_milestone_1, cortex_sessions_2026_07_20_lumat_cotizacion_final_cotizacion_lumat_opcion_a, cortex_sessions_2026_07_20_lumat_cotizacion_final_cotizacion_lumat_opcion_b, cortex_sessions_2026_07_20_lumat_cotizacion_final_cotizacion_lumat_opcion_c [EXTRACTED 1.00]
- **Agentes especializados del LumatAgent** — arquitectura_orchestrator, arquitectura_calendar_agent, arquitectura_automation_agent, arquitectura_notification_agent, arquitectura_report_agent [EXTRACTED 1.00]
- **Stack Tecnológico Lumat** — tech_langgraph, tech_openai, tech_postgres, postgres_pgvector, tech_nextjs, tech_docker, tech_whatsapp, tech_vps [EXTRACTED 1.00]
- **M3 Operational Platform modules** — diagrama1_agenda, diagrama1_crm, diagrama1_pagos, diagrama1_postventa, diagrama1_reportes [EXTRACTED 1.00]
- **Input channels into orchestrator** — diagrama1_whatsapp_business, diagrama1_web_lumat, diagrama1_orchestrator [EXTRACTED 1.00]
- **Core services behind orchestrator** — diagrama1_orchestrator, diagrama1_kb_rag, diagrama1_engine, diagrama1_panel [EXTRACTED 1.00]
- **Flujo de Orquestación Multiagente** — cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_orch, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_router, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_ag_wa, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_ag_cal, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_ag_aut, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_ag_not, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_ag_rep [EXTRACTED 1.00]
- **Sistemas de Soporte Transversales** — cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_tools, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_roles, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_mem, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_ctx, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama2_multiagente_kb [EXTRACTED 1.00]
- **Emergency protocol fan-out** — cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_proto, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_safety, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_notify, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_critical, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_reg_em [EXTRACTED 1.00]
- **Conversational flow pipeline** — cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_start, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_id, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_ctx, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_rag, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_ia, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_conf [EXTRACTED 1.00]
- **Persistence convergence on save** — cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_schedule, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_close, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_summary, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_save, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama3_flujo_conversacional_end [EXTRACTED 1.00]
- **Docker Compose — VPS Lumat** — cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_frontend, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_backend, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_admin, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_postgresql, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_backup, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_monitor [EXTRACTED 1.00]
- **Enrutamiento por Reverse Proxy** — cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_nginx, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_frontend, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_admin, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_backend [EXTRACTED 1.00]
- **Servicios Externos Integrados** — cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_backend, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_whatsapp_api, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_openai_api, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_google_calendar, cortex_sessions_2026_07_20_lumat_cotizacion_final_diagrams_diagrama4_infraestructura_transbank [EXTRACTED 1.00]
- **Admin Panel Navigation Menu** — cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_sidebar, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_dashboard_nav, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_clientes_nav, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_conversaciones_nav, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_casos_nav, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_agenda_nav, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_base_conocimiento_nav, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_configuracion_nav [EXTRACTED 1.00]
- **Weekly Technician Schedule Calendar** — cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_calendar, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_time_column, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_day_column, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_slot, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_event, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_blocked_slot, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_week_nav, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_tech_selector [EXTRACTED 1.00]
- **Dispatch Scheduling Workflow** — cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_tech_selector, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_nueva_visita_button, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_google_calendar_button, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_calendar, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_agenda_tecnicos_week_nav [INFERRED 0.75]
- **Customer 360 record layout** — cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_screen, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_sidebar, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_client_header, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_contacto, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_equipos, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_visitas, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_conversaciones, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_archivos, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_notas [EXTRACTED 1.00]
- **Two 2-column grid card layout** — cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_equipos, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_visitas, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_archivos, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_notas [EXTRACTED 1.00]
- **Primary interactions: schedule, derive, export** — cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_acciones, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_visitas, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_notas, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_cliente_ficha_back [INFERRED 0.80]
- **Main Dashboard Screen** — cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_dashboard_wireframe, cortex_sessions_2026_07_20_lumat_cotizacion_final_wireframes_dashboard_sidebar, header_user_bar, kpi_grid, recent_cases_table, recent_activity_feed [EXTRACTED 1.00]
- **KPI Monitoring Suite** — kpi_grid, kpi_clientes_nuevos, kpi_solicitudes_visita, kpi_emergencias, kpi_pendientes [EXTRACTED 1.00]

## Communities (32 total, 6 thin omitted)

### Community 0 - "Meta API & Legal Setup"
Cohesion: 0.07
Nodes (74): Ley 19.628 (proteccion de datos, Chile), Meta Business Suite / cuenta de negocio, WhatsApp Business Cloud API (Meta), Numero prepago dedicado de pruebas (SIM), Plantillas de utilidad (recordatorios, alertas, resumenes), Politica de retencion de conversaciones, Test number de Meta (numero de prueba), Ventana de 24 horas de Meta (+66 more)

### Community 1 - "Proposal & Pricing Options"
Cohesion: 0.08
Nodes (57): Copia final de la Propuesta Técnica y Económica, Comparativa Chatbot vs LumatAgent, cotizacion-lumat.md — Cotización original Lumat, Opción A — Chatbot IA, Opción B — Base Multi-Agente + WhatsApp (Recomendada), Opción C — LumatAgent Completo, Cotización Lumat — PDF (Julio 2026), Resumen de inversión por milestone (+49 more)

### Community 2 - "Architecture Agents & Services"
Cohesion: 0.07
Nodes (39): Audit log (audit_log), Automation Agent (AA), Worker de automatizaciones, Calendar Agent (CA), Notification Agent (NA), Orquestador (LangGraph supervisor), Report Agent (RA), Sistema de roles (dueño/admin/técnico/cliente) (+31 more)

### Community 3 - "Core Capabilities & Infra"
Cohesion: 0.10
Nodes (37): admin-panel capability, arquitectura-lumatagent.md (diagrams source), conversation-manager capability, Cost guardrails (spend limits + alerts), cotizacion-lumat.md (pricing source of truth), customer-records capability, Docker Compose infra, emergency-detection capability (+29 more)

### Community 4 - "Admin Panel Wireframes"
Cohesion: 0.09
Nodes (29): Lumat Admin Panel, Agenda Nav Item (active), Add Technician Action, Base de Conocimiento Nav Item, Blocked Slot (Lunch/Unavailable), Weekly Technician Calendar, Casos Nav Item, Clientes Nav Item (+21 more)

### Community 5 - "Conversational Flow Diagram"
Cohesion: 0.10
Nodes (24): Solicitar más antecedentes, Cierre con datos de contacto, ¿Respuesta confiable?, Crear ficha nueva (Nombre · Dirección · Comuna), Marcar prioridad crítica, Construcción de contexto, Derivar a operador humano, ¿Palabras de emergencia? (+16 more)

### Community 6 - "Dashboard & Case States"
Cohesion: 0.18
Nodes (15): Activity Event Dots, Case Status Enum, Sidebar Navigation, Wireframe — Dashboard Panel Admin, Header / User Bar, KPI: New Clients, KPI: Emergencies, KPI Cards Grid (+7 more)

### Community 7 - "Conversation & Emergency Reqs"
Cohesion: 0.22
Nodes (15): CM-2 Progressive Structured Data Capture, Conversation Manager, EM-1 Deterministic Keyword Detection, EM-2 Flow Interrupt, EM-3 Safety Instructions, Emergency Detection, HH-5 Human Response Channel, Human Handoff (+7 more)

### Community 8 - "Build & Diagram Tooling"
Cohesion: 0.13
Nodes (14): author, dependencies, @mermaid-js/mermaid-cli, puppeteer, description, keywords, license, main (+6 more)

### Community 9 - "OpenCode & Graphify Config"
Cohesion: 0.14
Nodes (13): command, _description, enabled, type, mcp, graphify, plugin, $schema (+5 more)

### Community 10 - "Admin & Customer Reqs"
Cohesion: 0.22
Nodes (13): AP-2 Roles and Permissions, AP-3 Clients List and Search, AP-4 Conversation View, AP-7 CSV/Excel Export, Admin Panel, CR-1 Auto-Ficha on First Contact, CR-2 Phone-Based Deduplication, CR-3 Lifecycle States (+5 more)

### Community 11 - "Multi-Agent Architecture"
Cohesion: 0.21
Nodes (13): Agente Automatizaciones (Reglas de Negocio), Agente Calendario (Agenda + Google Cal), Agente Notificaciones (WhatsApp + Email), Agente Reportes (KPIs + Exportación), Agente WhatsApp Atención al Cliente, Registro de Auditoría, Contexto del Cliente, Base de Conocimiento (RAG + pgvector) (+5 more)

### Community 12 - "Proposal Quality Standards"
Cohesion: 0.15
Nodes (13): Chatbot vs LumatAgent Comparison Table, Content Cleanliness, Mermaid Diagrams — 4 Required, Multi-Agent Architecture Explanation, Option Naming Convention, Output Artifacts, Quality Standards, Document Structure — 21 Sections (+5 more)

### Community 13 - "Infrastructure Diagram"
Cohesion: 0.21
Nodes (12): Panel Admin (Next.js · Puerto 3001), Backend (Python · LangGraph · Puerto 8000), Backup Service (Diario · Automático), Frontend (Next.js · Puerto 3000), Google Calendar (Sincronización), Health Check / Monitoreo, Nginx Reverse Proxy (HTTPS/SSL · Let's Encrypt), OpenAI API (GPT-4o-mini) (+4 more)

### Community 14 - "General Architecture Diagram"
Cohesion: 0.24
Nodes (12): Agenda Técnica (M3), CRM / Clientes (M3), PostgreSQL + pgvector, Motor IA GPT + LangGraph, Base de Conocimiento RAG, LumatAgent Orquestador Central, Pagos (M3), Panel Administrativo Next.js (+4 more)

### Community 15 - "Feature Requirements Mix"
Cohesion: 0.22
Nodes (11): AP-1 Authentication, AP-5 Cases View, AP-8 Basic KPIs, CM-3 Intent and Case Classification, CM-5 Conversation Summary, CR-5 History Linkage, HH-2 Deriva with History and Summary, HH-4 Case Visibility in Panel (+3 more)

### Community 16 - "Customer Record Wireframe"
Cohesion: 0.31
Nodes (11): Quick Actions (Agendar Visita / Derivar / Exportar), Archivos del Cliente (media pills), Back to Clientes list, Client Header Card, Customer Contact Data, Conversaciones Recientes table, Equipos Registrados table, Notas Internas (+3 more)

### Community 17 - "Security & Webhook Reqs"
Cohesion: 0.18
Nodes (11): SH-1 Network and Access Hardening, SH-2 Container and Secrets Hardening, SH-3 Backups and Monitoring, Security Hardening, WH-2 Signature Verification, WH-3 Immediate 200, WH-4 Persist Before Process, WH-5 Deduplicate by WAMID (+3 more)

### Community 18 - "Safety & Escalation Reqs"
Cohesion: 0.25
Nodes (9): CM-4 Authorized Technical Guidance, EM-4 Immediate Owner/Technician Notification, EM-5 Conservative Default, HH-3 Escalation Triggers, SH-4 Prompt-Injection Mitigations, SS-4 Cost Tracking and Meta Pricing Awareness, WhatsApp Webhook Endpoint, Meta WhatsApp Cloud API (+1 more)

### Community 19 - "Cortex Workflow & Skills"
Cohesion: 0.25
Nodes (9): Cortex session report.md, Cortex skill pack, Cortex skill registry (.atl/skill-registry.md), Engram persistent memory, Graphify knowledge graph, cortex-init command, cortex-init.sh bootstrap script, cortex-session skill (planning mode) (+1 more)

### Community 20 - "Early Quotation Docs"
Cohesion: 0.25
Nodes (9): LumatAgent — Arquitectura Multi-Agente, Cotización Lumat — Borrador Interno, Estimación de Costos — Lumat, Flujo del Bot IA — Lumat, Preguntas para Lumat, Preguntas Filtradas, Session Report — Evaluación y Cotización, Roadmap M1 — LumatAgent (+1 more)

### Community 21 - "KB & Admin Requirements"
Cohesion: 0.29
Nodes (8): AP-6 KB Manager Access, CM-6 Unresolved Response Logging, KB-1 Ingestion Pipeline, KB-2 Semantic Retrieval, KB-3 KB Manager, KB-4 Versioning and Re-Ingestion, Knowledge Base, pgvector

### Community 22 - "Build Scripts"
Cohesion: 0.71
Nodes (7): clean(), generate_diagrams(), generate_pdf(), generate_wireframes(), log(), build.sh script, success()

### Community 23 - "Conversation Core Patterns"
Cohesion: 0.40
Nodes (5): CM-1 Single-Agent Flow with Menu, HH-1 Per-Conversation State Model, 8-Category Menu, Per-Conversation State, LangGraph

### Community 24 - "Screenshot Tooling"
Cohesion: 0.50
Nodes (3): path, puppeteer, wireframes

## Ambiguous Edges - Review These
- `Schedule Event Block` → `Emergency Event Type`  [AMBIGUOUS]
  .cortex-sessions/2026-07-20-lumat-cotizacion-final/wireframes/agenda-tecnicos.png · relation: implements

## Knowledge Gaps
- **127 isolated node(s):** `name`, `version`, `description`, `main`, `test` (+122 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Schedule Event Block` and `Emergency Event Type`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **Why does `Propuesta Técnica y Económica Lumat — PDF (45 págs.)` connect `Proposal & Pricing Options` to `Meta API & Legal Setup`?**
  _High betweenness centrality (0.090) - this node is a cross-community bridge._
- **Why does `LumatRequest.md` connect `Meta API & Legal Setup` to `Proposal & Pricing Options`, `Early Quotation Docs`?**
  _High betweenness centrality (0.089) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Propuesta Técnica y Económica Lumat — PDF (45 págs.)` (e.g. with `Propuesta Lumat — Entrega 1 (Resumen Ejecutivo)` and `Propuesta Técnica y Económica Lumat — PDF (versión final, 59 págs.)`) actually correct?**
  _`Propuesta Técnica y Económica Lumat — PDF (45 págs.)` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `Admin Panel` (e.g. with `Conversation Manager` and `Customer Records`) actually correct?**
  _`Admin Panel` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `Conversation Manager` (e.g. with `Admin Panel` and `Propuesta Técnica y Económica Lumat`) actually correct?**
  _`Conversation Manager` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `version`, `description` to the rest of the system?**
  _127 weakly-connected nodes found - possible documentation gaps or missing edges._