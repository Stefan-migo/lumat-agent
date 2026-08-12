# Session: Lumat — Evaluación y Cotización

**Goal**: Analizar el requerimiento de Lumat, definir alcance técnico, evaluar tecnologías, estimar tiempos y costos, y producir una propuesta económica completa para los 3 milestones.
**Status**: cerrada (2026-07-16)
**Continuar en**: schema SQL completo, tools del agente (parámetros/validaciones), estados del LangGraph

## Context

Lumat es una empresa de servicios técnicos (calefont, calderas, calefacción) que necesita:
- **M1**: Bot IA de atención al cliente vía WhatsApp
- **M2**: Página web institucional
- **M3**: Catálogo, agendamiento, pagos, CRM

Recibimos `LumatRequest.md` (380 líneas) con requerimientos detallados por milestone. El cliente pide cotización separada por etapa con costos únicos, mensuales, variables, plazos, exclusiones, garantía, propiedad del código.

Prioridad inmediata: M1. M2 y M3 deben considerar integración futura desde el diseño.

Stack global decidido: **VPS (Hetzner) + Docker + PostgreSQL/pgvector + Python (FastAPI/LangChain) + Next.js (admin/web)**

Arquitectura del bot: **Agente con LLM + Harness + Config + Memoria** (mismo patrón que coding agents).

## Decisions

| # | Decision | Rationale | Alternatives |
|---|----------|-----------|-------------|
| 1 | VPS con Docker como base de infraestructura | Propiedad total de datos y código, costos predecibles, escalabilidad sin vendor lock-in, requisito explícito del cliente | Plataformas híbridas (Supabase+Vercel), low-code (WATI/Webflow) |
| 2 | Bot con arquitectura agéntica: LLM + Harness + Config + Memoria | Misma arquitectura que el coding agent pero adaptada a atención al cliente. Memoria tipo Engram con PostgreSQL+pgvector para sessions, clientes, RAG. | Chatbot tradicional con árbol de decisión (rígido, difícil de mantener, no escala) |
| 3 | Python (FastAPI + LangChain/LlamaIndex) para bot engine | Mejor ecosistema RAG y agentes, madurez en NLP, LangGraph para state machines | Node.js / Vercel AI SDK (ecosistema RAG menos maduro) |
| 4 | Next.js para admin panel + web M2 | UI moderna, mismo ecosistema frontend, conecta vía REST al backend Python | — |
| 5 | Memoria tipo Engram en PostgreSQL con pgvector | Permite que el bot recuerde clientes entre sesiones, RAG sobre knowledge base, historial conversacional completo | — |

## Tradeoffs

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| VPS + Docker | Propiedad total, costo fijo, escalable | Ops overhead (backups, updates, monitoreo) | ✅ Elegido |
| Híbrido (Supabase + Vercel) | Menos ops, rápido al inicio | Vendor lock-in, costos variables, datos en USA | ❌ Descartado |
| Low-code (WATI + Webflow) | Zero code | Límites de personalización, migración imposible, no escala a M3 | ❌ Descartado |
| Python para bot | RAG maduro, LangGraph, ecosistema NLP | Stack distinto a web | ✅ Elegido |
| Node.js para bot | Stack unificado con web | RAG menos maduro, más custom work | ❌ No recomendado |

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Ops overhead del VPS | Medio | Docker + Coolify/CapRover para simplificar deploys |
| Costos de API OpenAI si escala | Medio | Presupuestar GPT-4o-mini, monitorear consumo, límites configurables |
| Dependencia de WhatsApp API | Medio | Estrategia de fallback (email/web), documentar requisitos de Meta |

## Architecture

### Memory Architecture (Mini-Engram)

Tres niveles de memoria:

1. **Session Memory (Working)** — estado vivo de la conversación. Redis en RAM, se pierde al cerrar.
2. **Customer Memory (Episodic)** — `customer_memo` comprimido con embedding, se actualiza post-conversación. `equipment_memo` por equipo.
3. **Knowledge Base (Semantic)** — `knowledge_chunks` vectorizados con pgvector para RAG.

Capas extras:
- `memory_observations` — patrones detectados automáticamente (insight, pattern, risk, opportunity)
- Compression pipeline — job background que re-escribe memos cada N conversaciones

### Full Flow

```
1. LLEGA MENSAJE WHATSAPP
   │
2. IDENTIFICACIÓN (por teléfono)
   ├── ¿Cliente existe en customers?
   │   ├── Sí → CARGAR: customer_memo + equipments + últimas 3 convs + observations
   │   └── No → CREAR customer, iniciar flujo de registro
   │
3. CONSTRUIR CONTEXTO (system prompt del bot)
   │  "Eres el asistente virtual de Lumat.
   │   Personalidad: {config.persona}
   │   
   │   CLIENTE ACTUAL:
   │   {customer_memo}
   │   Equipos: {equipment_memos}
   │   Últimas conversaciones: {summaries}
   │   
   │   INSTRUCCIONES:
   │   - Sigue el flujo: {current_state}
   │   - Ya capturamos: {datos_recopilados}
   │   - Busca en knowledge_base antes de responder
   │   - Si es emergencia, activa protocolo
   │   - No inventes precios ni diagnósticos"
   │
4. RAG → buscar en knowledge_chunks (pgvector similarity)
   │
5. LLM → genera respuesta con herramientas
   │
6. GUARDAR → message + tool_calls + actualizar session state
   │
7. ¿CIERRE? → si el flujo terminó:
   ├── Generar summary con LLM
   ├── Actualizar customer_memo si aplica
   ├── Detectar patrones (background job)
   └── Cerrar sesión
```

### Customer Graph (relational)

```
Clientes ──tiene──› Equipos
  │                   │
  │                   └──historial──› Reparaciones
  │                                    │
  └──conversaciones──› Issues          │
                        │              │
                        └────relacionado_a──┘
                        
Ejemplos de queries:
- "Clientes con calefont Bosch con más de 3 visitas en 6 meses"
- "Fallos recurrentes por modelo de equipo"
- "Técnicos con mejores evaluaciones en calderas"
```

## Open Questions

- [x] Arquitectura detallada de la memoria tipo Engram en PostgreSQL
- [ ] Definir si customer graph es PostgreSQL queries o herramienta dedicada
- [ ] Plazos y costos de cada milestone
- [ ] Estructura de la cotización
- [ ] Estrategia de M3 (alcance base + cláusula de re-evaluación)

## Action Items

- [x] Discutir stack global — Decidido: VPS + Docker + Python + Next.js
- [x] Definir arquitectura de memoria tipo Engram para PostgreSQL
- [ ] Definir plazos y costos
- [ ] Producir cotización formal
