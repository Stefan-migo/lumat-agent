# Proposal: Propuesta Técnica y Económica Lumat

## Intent

Transform GPTversion.md (2,721-line skeleton with internal GPT commentary and placeholders) and cotizacion-lumat.md (380-line final quote) into a polished professional "Propuesta Técnica y Económica" document — a client-facing deliverable, not code.

## Scope

### In Scope
- Clean GPT skeleton — remove all internal commentary ("Excelente. Esta entrega...") and placeholders
- Integrate cotización content into GPT's 21-section structure: Chatbot vs LumatAgent comparison, architecture explanation, sub-agent system, permissions model, pricing tables, costos operativos, propiedad y continuidad
- Generate Mermaid diagrams: system architecture, conversational flow, multi-agent topology, infrastructure
- Generate HTML/CSS wireframes: dashboard admin, ficha de cliente, vista de agenda
- Output: professional MD (~25-30 pages) + polished PDF

### Out of Scope
- New content creation beyond what exists in source documents
- Code implementation or technical deliverables
- Client negotiation or revision rounds
- Branding, logos, or custom graphic design

## Capabilities

### New Capabilities
- `propuesta-document`: Polished client-facing proposal document merging GPT structure structure with validated content, diagrams, and wireframes. Output in MD + PDF.

### Modified Capabilities
None — this is a greenfield documentation deliverable. No existing specs.

## Approach

1. **Clean GPT skeleton**: Strip internal commentary, placeholders, and merge-ready markers from GPTversion.md
2. **Content merge**: Map cotizacion-lumat.md sections into the 21-section structure. The cotización is the source of truth for pricing, scope, components, and terms.
3. **Diagrams (Mermaid)**: Generate 4 diagrams — system architecture (components + data flow), conversational flow (WhatsApp→Bot→Human), multi-agent topology (Orchestrator + agents), infrastructure (VPS + Docker + services)
4. **Wireframes (HTML/CSS)**: 3 static HTML mockups — admin dashboard, client ficha, calendar/agenda view
5. **PDF generation**: Convert final MD to PDF via pandoc with professional template

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `openspec/changes/lumat-propuesta-final/` | New | Output directory for MD + diagrams + wireframes + PDF |
| `.cortex-sessions/2026-07-20-lumat-cotizacion-final/GPTversion.md` | Referenced | Source skeleton — read, not modified |
| `.cortex-sessions/2026-07-20-lumat-cotizacion-final/cotizacion-lumat.md` | Referenced | Source content — read, not modified |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| GPT skeleton structure gaps vs. client requirements (LumatRequest.md) | Low | Cross-reference against LumatRequest.md requirements matrix before writing |
| PDF rendering quality (Mermaid diagrams, wireframes) may need iteration | Med | Validate MD output first; use pandoc weasyprint backend for reliable diagram rendering |
| Content volume exceeds expected page count (25-30 pages target) | Med | Use collapsible sections and appendix for detailed technical specs; keep main body concise |

## Rollback Plan

Output is a new file tree under `openspec/changes/lumat-propuesta-final/`. Rollback is trivial: delete the directory. No existing files are modified.

## Dependencies

- `cotizacion-lumat.md` — source of truth for pricing, scope, components, terms
- `GPTversion.md` — 21-section structure skeleton (cleaned)
- `LumatRequest.md` — client requirements for compliance matrix
- `pandoc` + `weasyprint` (or `wkhtmltopdf`) — for PDF generation

## Success Criteria

- [ ] Document follows GPT's 21-section structure with no missing sections
- [ ] Zero GPT internal commentary or placeholders remain in final output
- [ ] All pricing, scope, and terms match cotizacion-lumat.md exactly
- [ ] 4 Mermaid diagrams render without errors in MD preview
- [ ] 3 HTML/CSS wireframes render correctly in browser
- [ ] Final PDF is paginated, professional, and under 35 pages
- [ ] Compliance matrix confirms coverage of all LumatRequest.md requirements
