# propuesta-document Specification

## Purpose

Define the structure, content, and quality requirements for the "Propuesta Técnica y Económica Lumat" — a client-facing deliverable merging GPTversion.md skeleton with cotizacion-lumat.md content into a polished MD+PDF document.

## Requirements

### Requirement: Document Structure — 21 Sections

The proposal document SHALL follow the exact 22-part structure (cover + 21 sections) defined in GPTversion.md.

| # | Section | Source | Key Content |
|---|---------|--------|-------------|
| 0 | Portada | GPT | HandCodeStudio, Stefan Miranda, Julio 2026, v2.0, confidencial |
| 1 | Resumen Ejecutivo | GPT + cotización | Tres pilares, filosofía de solución, beneficios esperados |
| 2 | Entendimiento del Proyecto | GPT + cotización | Desafíos actuales, principios de diseño, visión de largo plazo |
| 3 | Objetivos | GPT | Objetivo general + 6-8 objetivos específicos |
| 4 | Alcance General | GPT | Qué incluye/excluye cada milestone en una tabla |
| 5 | Arquitectura de la Solución | GPT + cotización | Diagrama Mermaid #1 + explicación de negocio |
| 6 | Stack Tecnológico | GPT + cotización | Tabla de tecnologías por capa (front, back, IA, infra, APIs) |
| 7 | Milestone 1 — LumatAgent | GPT + cotización | Opciones A/B/C + comparativa Chatbot vs LumatAgent + multi-agente |
| 8 | Milestone 2 — Página Web | GPT + cotización | Alcance, secciones, CMS, SEO, integraciones |
| 9 | Milestone 3 — Plataforma Operacional | GPT + cotización | Catálogo, agenda, pagos, postventa, automatizaciones |
| 10 | Infraestructura | GPT + cotización | Diagrama Mermaid #4 + VPS, Docker, backups |
| 11 | Costos Operativos | cotización | Tabla mensual + escenarios por volumen |
| 12 | Soporte | cotización | Retén mensual vs pago por evento |
| 13 | Garantías | cotización | 60 días, cobertura, exclusiones, tiempos de respuesta |
| 14 | Seguridad | GPT | Datos, acceso, cifrado, autenticación, monitoreo |
| 15 | Propiedad Intelectual | cotización | Tabla: código, BD, dominio, WhatsApp, cuentas, migración |
| 16 | Continuidad del Proyecto | cotización | Migración, cese de servicios, respaldos, documentación |
| 17 | Riesgos y Dependencias | GPT + cotización | Tabla de riesgos con mitigación |
| 18 | Roadmap | GPT | Timeline visual de los 3 milestones |
| 19 | Matriz de Trazabilidad | GPT + LumatRequest | Tabla requisito → sección de la propuesta |
| 20 | Resumen Económico | cotización | Tabla de inversión + combinaciones recomendadas |
| 21 | Próximos Pasos | cotización | 4 pasos accionables post-entrega |

#### Scenario: Client reads the proposal cover to cover
- GIVEN the final PDF is delivered to Lumat
- WHEN a stakeholder reads the document sequentially
- THEN every section from Portada to Próximos Pasos is present and flows logically
- AND no GPT internal commentary remains in any section

#### Scenario: Client navigates via table of contents
- GIVEN the document index is generated
- WHEN a stakeholder clicks any section in the TOC
- THEN the link navigates to the correct section heading

### Requirement: Mermaid Diagrams — 4 Required

The document SHALL include exactly 4 Mermaid diagrams rendered as part of the MD source.

| # | Diagram | Placement | What it SHALL show |
|---|---------|-----------|--------------------|
| D1 | Arquitectura General del Sistema | Sección 5 | Canales (WhatsApp, Web, Teléfono) → LumatAgent (Orquestador + sub-agentes) → PostgreSQL → Panel Admin. Flujo de datos entre capas. |
| D2 | Arquitectura Multi-Agente | Sección 7 (M1) | Orquestador central → 5 sub-agentes (WhatsApp, Calendario, Automatizaciones, Notificaciones, Reportes) + Tools Layer + Memory. Cada agente conectado al orquestador, no entre sí. |
| D3 | Flujo Conversacional del Bot | Sección 7 (M1) | Secuencia: Saludo → Clasificación de motivo → Captura de datos → Consulta RAG → Respuesta/Orientación → Decisión (derivar o resolver) → Registro. Con bifurcación de emergencia. |
| D4 | Infraestructura de Despliegue | Sección 10 | Internet → Nginx Reverse Proxy → Docker containers (App, DB, Redis) → VPS Hetzner + Backup automático diario. WhatsApp Cloud API como servicio externo. |

#### Scenario: Diagrams render in MD preview
- GIVEN the MD source file is opened in a Mermaid-compatible viewer
- WHEN any of the 4 diagrams is rendered
- THEN the diagram displays without syntax errors
- AND all nodes and edges are correctly labeled and connected

#### Scenario: Diagrams survive PDF conversion
- GIVEN the MD is converted to PDF via md-to-pdf or pandoc
- WHEN the PDF is generated
- THEN all 4 diagrams are visible and legible in the final PDF
- AND no diagram overlaps page margins or breaks across pages

### Requirement: HTML/CSS Wireframes — 3 Required

The document SHALL reference 3 standalone HTML/CSS wireframe files.

| # | Wireframe | File | What it SHALL show |
|---|-----------|------|--------------------|
| W1 | Dashboard del Panel Administrativo | `wireframes/dashboard.html` | Sidebar nav (Clientes, Conversaciones, Agenda, Configuración), KPI cards (contactos hoy, pendientes, derivados, emergencias), tabla de últimos casos, gráfico de motivos |
| W2 | Ficha de Cliente (CRM) | `wireframes/ficha-cliente.html` | Datos personales, historial de conversaciones, equipos registrados, visitas, pagos, notas internas, botón de exportar |
| W3 | Vista de Agenda de Técnicos | `wireframes/agenda.html` | Vista semanal/mensual, técnicos como columnas, bloques de visita de 1h, colores por estado, filtros por técnico |

#### Scenario: Wireframes render in browser
- GIVEN any of the 3 HTML files is opened in a modern browser
- WHEN the page loads
- THEN the wireframe displays correctly with CSS styling applied
- AND layout is responsive (desktop-first acceptable)

#### Scenario: Wireframes use professional palette
- GIVEN the wireframes are inspected
- WHEN a reviewer checks the visual style
- THEN the design uses a clean professional aesthetic (no placeholders, no lorem ipsum visible)
- AND labels and data reflect Lumat's domain (calefont, calderas, calefacción, técnicos, clientes)

### Requirement: Content Cleanliness

The final document SHALL contain zero GPT internal commentary, zero placeholders, and zero merge-ready markers.

#### Scenario: No internal commentary
- GIVEN the GPTversion.md contains lines like "Excelente. Esta entrega definirá el tono..."
- WHEN the final document is generated
- THEN no such internal commentary appears anywhere in the output

#### Scenario: No placeholders
- GIVEN the GPT skeleton uses placeholders like [COMPLETAR] or "(describir aquí)"
- WHEN the final document is generated
- THEN every placeholder has been replaced with actual content from cotizacion-lumat.md

#### Scenario: Source-of-truth alignment
- GIVEN cotizacion-lumat.md defines pricing, scope, deadlines, and terms
- WHEN the final document is compared against cotizacion-lumat.md
- THEN all prices, timelines, components, and exclusion lists match exactly

### Requirement: Option Naming Convention

The document SHALL use the canonical option names throughout.

| Internal Name | Canonical Name in Document |
|---------------|---------------------------|
| Opción A | Chatbot IA |
| Opción B | Base Multi-Agente + WhatsApp |
| Opción C | LumatAgent Completo |

#### Scenario: Consistent naming across sections
- GIVEN the document references M1 options in sections 7, 20, and 21
- WHEN a reviewer searches for option names
- THEN the same canonical name is used consistently in every section
- AND no section uses a different or abbreviated name

### Requirement: Chatbot vs LumatAgent Comparison Table

Section 7 SHALL include the "¿Chatbot o LumatAgent?" comparison table from cotizacion-lumat.md, explaining at a business level what each option solves.

#### Scenario: Business-level explanation
- GIVEN the comparison table is rendered in section 7
- WHEN a non-technical stakeholder reads it
- THEN the language describes business problems and solutions (e.g., "perdemos clientes porque no siempre podemos contestar")
- AND technical jargon is minimized or explained inline

#### Scenario: Functional comparison matrix
- GIVEN the comparison table includes the multi-column matrix
- WHEN the table is rendered
- THEN it includes columns for: WhatsApp, Panel Admin, Multi-Agente, Roles, Automatizaciones, Calendario, Lenguaje Natural, Preparado M3, Plazo, Precio
- AND each cell is marked with ✅, ❌, or a specific value

### Requirement: Multi-Agent Architecture Explanation

Section 7 SHALL explain the multi-agent architecture at a business level.

#### Scenario: Non-technical reader understands the concept
- GIVEN the multi-agent section in M1 is read by Lumat's owner
- WHEN the explanation is complete
- THEN the reader understands: what an orchestrator does, what sub-agents are, what tools/permisos means, and why this architecture matters for growth
- AND the explanation uses analogies or simple language (e.g., "es como un jefe de equipo que coordina especialistas")

### Requirement: LumatRequest.md Traceability

Section 19 SHALL contain a traceability matrix mapping every requirement from LumatRequest.md to the corresponding section(s) in the proposal.

#### Scenario: Full coverage
- GIVEN LumatRequest.md defines requirements across sections 1-7
- WHEN the traceability matrix is generated
- THEN every requirement from LumatRequest.md maps to at least one proposal section
- AND no LumatRequest.md requirement is orphaned

#### Scenario: Granular mapping
- GIVEN the traceability matrix in section 19
- WHEN a reviewer checks a specific requirement (e.g., "1.4 Menú inicial requerido")
- THEN the matrix shows exactly which proposal section(s) address it (e.g., "Sección 7.3 Flujo Conversacional")

### Requirement: Quality Standards

The final deliverable SHALL meet these quality targets.

| Metric | Target |
|--------|--------|
| Language | Spanish, neutral/professional (not regional) |
| Provider attribution | HandCodeStudio, Contacto: Stefan Miranda |
| Currency | All prices in USD |
| PDF page count | 25-30 pages (target) / 45 pages (hard max, includes Anexos A–C) |
| Source format | Markdown (.md) |
| Output format | PDF via md-to-pdf with custom CSS |

#### Scenario: PDF pagination is clean
- GIVEN the MD is converted to PDF
- WHEN the output is generated
- THEN the document has 25-30 pages
- AND section headings do not orphan at the bottom of pages
- AND diagrams fit within page margins without truncation

#### Scenario: Professional appearance
- GIVEN the PDF is viewed by a client
- WHEN they browse the document
- THEN the formatting uses consistent fonts, spacing, and heading hierarchy
- AND the cover page displays HandCodeStudio, Stefan Miranda, Julio 2026, and "Documento Confidencial"

### Requirement: Output Artifacts

The deliverable SHALL produce exactly these files.

| File | Format | Description |
|------|--------|-------------|
| `propuesta-tecnica-lumat.md` | Markdown | Complete 22-part source document |
| `propuesta-tecnica-lumat.pdf` | PDF | Polished PDF generated from MD |
| `diagrams/*.mmd` | Mermaid | 4 standalone diagram source files |
| `wireframes/*.html` | HTML/CSS | 3 standalone wireframe files |
| `propuesta-tecnica-lumat.css` | CSS | Custom stylesheet for PDF generation |

#### Scenario: All artifacts present
- GIVEN the spec phase is complete
- WHEN the change directory is inspected
- THEN all 5 artifact types exist and are valid files
- AND the MD file opens in any text editor without syntax errors
