# Tasks: Propuesta Técnica y Económica Lumat

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 1700-2500 (MD body + 4 diagrams + 3 wireframes + CSS + config) |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single delivery — monolithic documentation artifact |
| Delivery strategy | exception-ok |
| Chain strategy | pending |
| Decision needed before apply | No |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Medium

## Phase 1: Content Preparation

- [x] 1.1 Strip GPT internal commentary from `GPTversion.md` → cleaned 22-section skeleton in `propuesta-tecnica-economica-lumat.md`
- [x] 1.2 Extract and map `cotizacion-lumat.md` sections to the 22-section structure (pricing, scope, support, IP, continuity, next steps)
- [x] 1.3 Establish canonical option names: A→"Chatbot IA", B→"Base Multi-Agente + WhatsApp", C→"LumatAgent Completo"

## Phase 2: Mermaid Diagrams — 4 source files

- [x] 2.1 Write `diagrams/arch.mmd` — LR flow: WhatsApp/Web → API Gateway → LumatAgent Core → PostgreSQL/pgvector → Panel Admin
- [x] 2.2 Write `diagrams/multi-agent.mmd` — TB topology: Orchestrator (LangGraph) → 5 sub-agents + Tools layer + Memory
- [x] 2.3 Write `diagrams/conversational-flow.mmd` — TD decision tree: Saludo→Clasificar→¿Existe?→RAG→¿Confiable?→Resolver/Derivar
- [x] 2.4 Write `diagrams/infra.mmd` — TD deployment: Internet→Nginx→Docker Compose→[Frontend,Backend,PostgreSQL,Worker]→Backup

## Phase 3: HTML Wireframes — 3 source files

- [x] 3.1 Write `wireframes/dashboard.html` — sidebar nav, KPI cards (Nuevos:18,Solicitudes:24,Emergencias:1,Pendientes:6), cases table
- [x] 3.2 Write `wireframes/ficha-cliente.html` — client header+"Activo" badge, tabs (Datos,Equipos,Historial,Pagos), action buttons
- [x] 3.3 Write `wireframes/agenda.html` — Mon-Fri grid, 8-18h slots, technician columns, color-coded (green/yellow/gray), CSS grid, no JS

## Phase 4: Main Document Assembly

- [x] 4.1 Merge cleaned skeleton + cotización content + diagram/wireframe PNG refs into final 22-part `propuesta-tecnica-economica-lumat.md`
- [x] 4.2 Write section 7: Chatbot vs LumatAgent comparison table + multi-agent architecture business-level explanation
- [x] 4.3 Write section 19: traceability matrix mapping all `LumatRequest.md` requirements to proposal sections

## Phase 5: CSS, Build Script, PDF

- [x] 5.1 Adapt `style.css` + `md-to-pdf.config.js` from `.cortex-sessions/2026-07-20-lumat-cotizacion-final/` for this document
- [x] 5.2 Write `build.sh` — sequential: `mmdc` render all diagrams → headless Chrome screenshot all wireframes → `md-to-pdf` generate PDF
- [x] 5.3 Run `build.sh` and verify PDF: 25-30 pages, diagrams legible, no orphan headings, professional cover page

## Phase 6: Verification

- [x] 6.1 Verify diagram syntax: `mmdc -i diagrams/*.mmd -o /dev/null` exit code 0
- [x] 6.2 Verify content cleanliness: grep for GPT commentary, "[COMPLETAR]", placeholder markers; diff prices against `cotizacion-lumat.md`
- [x] 6.3 Cross-reference `LumatRequest.md` requirements against proposal sections (matrix coverage check)

## Phase 7: Bonus — Executive Presentation (optional)

- [x] 7.1 Create 10-12 slide executive summary presentation from key proposal highlights

> **Reconciliation note** (2026-07-20): All 19 tasks were marked `[x]` during archive reconciliation.
> These were stale checkboxes — `sdd-apply` completed all tasks but did not update the checkboxes.
> The verify-report (2026-07-20, 23/24 compliant, 0 incomplete tasks) proves every task is complete.
