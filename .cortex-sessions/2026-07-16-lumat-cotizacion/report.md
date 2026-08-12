# Session Report: Lumat — Evaluación y Cotización

**Fecha**: 2026-07-16
**Estado**: Cerrada
**SDD Readiness**: ✅ Listo para continuar con costos/plazos y cotización formal

---

## Executive Summary

Sesión de planeamiento inicial para el proyecto Lumat. Se analizó el requerimiento completo (LumatRequest.md, 380 líneas), se definió el stack tecnológico global, la arquitectura del bot y el modelo de memoria. Quedó pendiente la definición de costos, plazos y la cotización formal.

**Stack decidido**: VPS (Hetzner) + Docker + PostgreSQL/pgvector + Python (FastAPI/LangChain) + Next.js

---

## Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **VPS + Docker como infraestructura base** | Propiedad total de datos y código, costos predecibles (~$30-40/mes), escalabilidad sin vendor lock-in. Requisito explícito del cliente. |
| 2 | **Bot con arquitectura agéntica** (LLM + Harness + Config + Memoria) | Mismo patrón que los coding agents. Chatbot tradicional es muy rígido para lo que Lumat necesita. |
| 3 | **Python (FastAPI + LangChain/LlamaIndex) para bot engine** | Mejor ecosistema RAG y agentes del mercado. LangGraph para state machines. |
| 4 | **Next.js para admin panel + Web M2** | UI moderna, conecta vía REST al backend Python. Stacks mixtos es la norma hoy. |
| 5 | **Memoria tipo Engram en PostgreSQL con pgvector** | 3 niveles: sesión (working), cliente (episodic), knowledge base (semantic). Compression pipeline post-conversación. |

## Tradeoffs Considered

| Option | Verdict |
|--------|---------|
| VPS + Docker | ✅ Elegido |
| Híbrido Supabase + Vercel | ❌ Descartado (vendor lock-in, costos variables, datos en USA) |
| Low-code WATI + Webflow | ❌ Descartado (no escala, migración imposible, viola requisito de propiedad) |
| Node.js para bot engine | ❌ Descartado (ecosistema RAG menos maduro que Python) |

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Ops overhead del VPS | Medio | Docker + Coolify/CapRover para simplificar deploys |
| Costos de API OpenAI si escala | Medio | GPT-4o-mini como default, monitoreo de consumo, límites configurables |
| Dependencia de WhatsApp API | Medio | Estrategia de fallback (web/email), documentar requisitos de aprobación de Meta |

## Architecture Overview

### Stack por milestone

```
                 VPS (Hetzner CX22 ~€15/mes)
                          │
        ┌─────────────────┼─────────────────┐
        │                  │                  │
     M1: Bot            M2: Web           M3: Gestión
    ┌──────────┐    ┌──────────┐     ┌──────────────┐
    │ FastAPI  │    │  Astro   │     │  FastAPI +   │
    │LangChain │    │ + React  │     │  Next.js     │
    │pgvector  │    │          │     │  + pagos     │
    │Redis     │    │          │     │  + agenda    │
    └────┬─────┘    └────┬─────┘     └──────┬───────┘
         │               │                  │
         └───────────────┼──────────────────┘
                         │
              ┌──────────┴──────────┐
              │   PostgreSQL 16     │
              │   + pgvector        │
              └─────────────────────┘
```

### Memory Architecture (Mini-Engram)

Tres niveles de memoria:

1. **Session Memory** (working) — estado vivo de la conversación en Redis
2. **Customer Memory** (episodic) — `customer_memo` comprimido + embedding, se actualiza post-conversación
3. **Knowledge Base** (semantic) — `knowledge_chunks` vectorizados para RAG con pgvector

Extra: `memory_observations` para patrones automáticos (insight, pattern, risk, opportunity).

### Full Flow del Bot

Documentado en `flujo-bot.md` — incluye identificación por teléfono, construcción de contexto con historial, RAG, respuesta del LLM con tools, y compression pipeline post-cierre.

## Open Questions (para próxima sesión)

- [ ] Costos de desarrollo por milestone (M1, M2, M3)
- [ ] Costos mensuales (VPS, APIs, dominio, soporte)
- [ ] Costos variables (WhatsApp, OpenAI por uso)
- [ ] Plazos y entregables por milestone
- [ ] Exclusiones y garantía
- [ ] Estrategia M3: alcance base + cláusula de re-evaluación (posible evolución a software de gestión)
- [ ] Formato de la cotización

## SDD Readiness

La sesión generó suficiente definición arquitectónica para iniciar SDD:
- **sdd-new**: "Lumat — Bot IA (M1)" → primer cambio con stack definido
- **sdd-propose**: propuesta basada en las decisiones de stack y arquitectura
- Pendiente: costos y plazos antes de cotización formal

## Assets

- `.cortex-sessions/2026-07-16-lumat-cotizacion/session.md` — sesión viva
- `.cortex-sessions/2026-07-16-lumat-cotizacion/flujo-bot.md` — flujo para cliente
- `.cortex-sessions/2026-07-16-lumat-cotizacion/report.md` — este reporte
- `Enagram #973` — decisión de stack
