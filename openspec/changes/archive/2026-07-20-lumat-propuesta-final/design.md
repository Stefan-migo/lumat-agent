# Design: Propuesta Técnica y Económica Lumat

## Technical Approach

Single-pipeline document build: raw markdown → rendered assets (Mermaid PNGs + wireframe PNGs) → styled PDF via `md-to-pdf`. One source file (`propuesta-tecnica-economica-lumat.md`), one output (`propuesta-tecnica-economica-lumat.pdf`). All assets pre-rendered before PDF generation — the markdown references static PNGs, not inline Mermaid or HTML.

**Source integration**: GPTversion.md (21 sections, cleaned of GPT meta-commentary) + cotizacion-lumat.md (pricing, scope, terms) + arquitectura-lumatagent.md (diagrams source). Cotización is the source of truth for pricing and M1 option names.

## Architecture Decisions

| # | Decision | Options considered | Choice | Rationale |
|---|----------|--------------------|--------|-----------|
| AD1 | PDF engine | pandoc+weasyprint or md-to-pdf | **md-to-pdf** | Already proven on this project (`style.css` + `config.js` work). Uses headless Chrome internally — renders CSS, tables, and images correctly. |
| AD2 | Diagram rendering | Inline Mermaid or pre-rendered PNGs | **Pre-rendered PNGs** | md-to-pdf cannot render Mermaid. `mmdc` (v11.16.0, confirmed working) converts `.mmd` → `.png`. Markdown references `diagrams/arch.png` etc. |
| AD3 | Wireframe rendering | Embedded HTML or pre-rendered PNGs | **Pre-rendered PNGs** | Headless Chrome screenshots of `.html` files. Same Puppeteer that md-to-pdf already bundles. `page.setViewport({width:1280, height:800})` → `page.screenshot()`. |
| AD4 | Document structure | Multi-file or single-file | **Single markdown file** | 25-30 pages, single pipeline. Multi-file adds build complexity with no benefit for a linear document. |
| AD5 | Section cleanup | Manual edit or scripted strip | **Scripted strip of GPT lines then manual polish** | Lines matching `"Excelente."`, `"Aquí incorporaremos"`, and GPT meta-commentary stripped via sed. Then manual content merge and polish. |

## File Organization

```
openspec/changes/lumat-propuesta-final/
├── proposal.md
├── design.md                          ← This file
├── propuesta-tecnica-economica-lumat.md   ← Main document source
├── style.css                          ← Adapted from existing
├── config.js                          ← Adapted from existing
├── diagrams/
│   ├── arch.mmd                       → arch.png         (System architecture)
│   ├── multi-agent.mmd                → multi-agent.png  (Orchestrator + sub-agents)
│   ├── conversational-flow.mmd        → flow.png         (Decision tree)
│   └── infra.mmd                      → infra.png        (Docker deployment)
├── wireframes/
│   ├── dashboard.html                 → dashboard.png    (Admin panel)
│   ├── client-ficha.html              → ficha.png        (Client detail)
│   └── agenda.html                    → agenda.png       (Calendar view)
└── propuesta-tecnica-economica-lumat.pdf   ← Built artifact
```

## Build Pipeline

```
diagrams/*.mmd  ──[mmdc]────→ diagrams/*.png ──┐
wireframes/*.html ──[Chrome]─→ wireframes/*.png ─┤
                                                  ├──→ md-to-pdf → PDF
propuesta-tecnica-economica-lumat.md ─────────────┘
                       ↑
                  (references .png files)
```

Build order: render diagrams → render wireframes → md-to-pdf. Single `build.sh` orchestrates the three steps.

## Diagram Specifications (4 Mermaid diagrams)

| Diagram | File | Nodes | Connectors | Key annotations |
|---------|------|-------|------------|-----------------|
| System architecture | `arch.mmd` | WhatsApp channel, Web channel, API Gateway (FastAPI), LumatAgent Core, PostgreSQL/pgvector, Panel Admin | WhatsApp→Gateway, Web→Gateway, Gateway→Core, Core→DB, DB→Panel | Flow direction: LR. Highlight: Gateway is the single entry point |
| Multi-agent topology | `multi-agent.mmd` | Orchestrator (LangGraph), WhatsApp Agent, Calendar Agent, Automation Agent, Notification Agent, Report Agent | Orchestrator→each agent. Each agent→tools list | Flow direction: TB. Each agent node lists its tools |
| Conversational flow | `flow.mmd` | Cliente→Identificar→¿Existe?→Construir contexto→RAG→¿Respuesta confiable?→Responder/Derivar→Guardar→Resumen | Decision diamonds for ¿Existe? and ¿Respuesta confiable? | Flow direction: TD. Decision nodes are diamond-shaped |
| Infrastructure | `infra.mmd` | Internet→Nginx→Docker Compose→[Frontend, Backend, PostgreSQL, Worker]→Backup volume | Sequential with branching at Compose | Flow direction: TD. Rounded boxes for services, cylinder for DB |

## Wireframe Specifications (3 HTML mockups)

| Wireframe | File | Key elements |
|-----------|------|-------------|
| Dashboard | `dashboard.html` | Left nav (Clientes, Conversaciones, Agenda, Reportes, Config), top stat cards (Nuevos: 18, Solicitudes: 24, Emergencias: 1, Pendientes: 6), recent cases table (5 rows), activity feed |
| Client ficha | `client-ficha.html` | Header (client name + status badge "Activo"), tabs (Datos, Equipos, Historial, Conversaciones, Pagos), action buttons (Agendar, Derivar, Exportar), content panel with structured fields |
| Agenda | `agenda.html` | Week view grid (Mon–Fri), technician filter dropdown, time slots 8:00–18:00 (1h blocks), color-coded blocks (green=confirmed, yellow=pending, gray=blocked). CSS grid layout, no JS required |

Wireframes are static HTML + inline CSS — no JavaScript needed. They represent the visual layout, not interactive behavior. Rendered at 1440×900 viewport.

## Content Adaptation from GPT Skeleton

1. **Strip**: `grep -v -E '(Excelente\.|Aquí incorporaremos|Esta entrega|ENTREGA [0-9])'` removes GPT commentary
2. **Merge**: Map cotizacion-lumat.md sections → 21-section structure. Cotización is the pricing source of truth
3. **Diagrams**: Replace ASCII placeholder diagrams with `![Diagrama](diagrams/arch.png)` references
4. **Wireframes**: Replace ASCII mockups with `![Mockup](wireframes/dashboard.png)` references  
5. **Comparison**: Integrate "Chatbot vs LumatAgent" comparison table from cotizacion-lumat.md §¿Chatbot o LumatAgent?
6. **M1 names**: Use exact option names from cotización: "Opción A — Chatbot IA", "Opción B — Base Multi-Agente + WhatsApp", "Opción C — LumatAgent Completo"

## Tooling

| Tool | Status | Command |
|------|--------|---------|
| `npx md-to-pdf` | ✅ v5.2.5 | `npx md-to-pdf config.js propuesta-tecnica-economica-lumat.md` |
| `npx @mermaid-js/mermaid-cli` (mmdc) | ✅ v11.16.0 | `npx mmdc -i diagrams/arch.mmd -o diagrams/arch.png -w 1200` |
| Node.js / Puppeteer | ✅ Node v22 | Chrome bundled with md-to-pdf. Wireframe script uses it directly |
| Bash | ✅ Available | `build.sh` orchestrates the pipeline |

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Diagram syntax | All 4 `.mmd` files parse without errors | `npx mmdc -i file.mmd -o /dev/null` — exit code 0 |
| Wireframe render | All 3 `.html` files produce valid PNGs | Visual inspection of output PNGs |
| PDF generation | Final PDF renders without errors | `npx md-to-pdf` exit code 0 |
| Content compliance | No GPT commentary, pricing matches cotización | `grep` for forbidden patterns, manual section-by-section review |
| LumatRequest coverage | All 10 requirements from §3 covered | Cross-reference checklist against `LumatRequest.md` |

## Open Questions

- [ ] Q1: Should the portada include logos/branding? (Out of scope per proposal, but verify)
- [ ] Q2: Target delivery date for client review? (Affects pipeline iteration timing)

## References

- Source skeleton: `.cortex-sessions/2026-07-20-lumat-cotizacion-final/GPTversion.md` (2,720 lines)
- Source pricing: `.cortex-sessions/2026-07-20-lumat-cotizacion-final/cotizacion-lumat.md` (380 lines)
- Source architecture: `.cortex-sessions/2026-07-20-lumat-agent-arquitectura/arquitectura-lumatagent.md` (236 lines)
- Existing CSS: `.cortex-sessions/2026-07-20-lumat-cotizacion-final/style.css`
- Existing config: `.cortex-sessions/2026-07-20-lumat-cotizacion-final/md-to-pdf.config.js`
- Client requirements: `LumatRequest.md` (380 lines)
