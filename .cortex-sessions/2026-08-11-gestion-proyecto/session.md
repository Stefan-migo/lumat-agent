# Session: Plan de gestión, organización y orquestación — Proyecto LumatAgent
Goal: Definir el plan de organización, orquestación y gestión del desarrollo de LumatAgent (4 hitos, ~4 meses) para ejecutar con calidad y sin fallas de entrega.

## Context
- 2026-08-11: Contrato FIRMADO y Pago 1 (USD 560) recibido hoy. El proyecto está oficialmente en ejecución desde el 11-ago-2026.
- Calendario de pagos anclado: P1 11-ago ✓, P2 ~10-sep, P3 ~10-oct, P4 ~9-nov, P5 ~9-dic.
- Kickoff: lunes 17-ago-2026 según propuesta (semana siguiente a la firma).
- CRONOGRAMA FINAL (decisión 11-ago): construcción de 12 semanas (17-ago → 8-nov) + pruebas/puesta en marcha (9-nov → 16-dic). Aceptación ~16-dic. Se descartó el 2+2 comprimido por prioridad de calidad.
- Propuesta final: `.cortex-sessions/2026-08-07-reunion-cierre/propuesta-final-lumatagent.md` (etapa de contrato).
- Condiciones: USD 2,800 en 5 pagos mensuales de USD 560. Los pagos NO están atados a hitos.
- Timeline contractual: ~2 meses de construcción (4 hitos, semanas 1-12) + ~2 meses de pruebas y puesta en marcha.
- Kickoff tentativo en propuesta: lunes 17-ago-2026 (sujeto a firma + pago 1).
- Alcance: M1 completo (LumatAgent multi-agente). M2 (web) en standby 3 meses.
- Stack definido: FastAPI + LangGraph, PostgreSQL + pgvector, WhatsApp Cloud API, calendario propio + ICS read-only, panel PWA, Docker en VPS (Hostinger KVM 2 recomendado).
- Dependencias críticas del cliente: trámite Meta API (puede tardar semanas), base de conocimiento inicial, SIM prepago, decisiones operativas (roles, calendario, retención de datos).

## Decisions
| # | Decision | Rationale | Alternatives |
|---|----------|-----------|-------------|
| 1 | Inicio oficial: 11-ago-2026 (firma + pago 1 mismo día) | Contrato firmado y pago recibido hoy; pagos mensuales calendario, no atados a hitos | Kickoff diferido (descartado: no hay motivo) |
| 2 | Capacidad: ~20 h/sem (medio tiempo, 4 h/día promedio), Lumat prioridad sobre otros proyectos | Única fuente de capacidad de desarrollo; ~240 h para las 12 semanas de construcción | Full-time (no disponible), bajar scope (no aceptable) |
| 3 | Orquestación: un change SDD por hito (4 changes), criterios de aceptación contractuales → specs | Trazabilidad contrato ↔ código; cada hito cierra con verify contra sus criterios | Pipeline único grande (riesgo de deriva), trabajo ad-hoc (sin trazabilidad) |
| 4 | Gobernanza cliente: reporte semanal escrito (viernes) + reunión-demo de cierre de hito (4 total) | Pagos no atados a hitos → el ritmo se sostiene con visibilidad, no con entregas forzadas | Reuniones semanales (sobrecoste), sin reportes (cliente a ciegas) |
| 5 | Dependencias del cliente se piden por escrito con 2 semanas de anticipación | Meta API, KB y SIM son cuellos de botella externos al desarrollo | Pedir al momento (bloqueos), asumir que llegan solas (ingenuo) |
| 6 | Cronograma: 12 semanas construcción + 5 semanas pruebas (no 2+2) | Prioridad de calidad; con 20 h/sem el 2+2 no da para el scope del contrato sin recortar seguridad | 2+2 comprimido (descartado 11-ago: riesgo de calidad), 4 hitos en 8 sem (inviable con scope completo) |
| 7 | Estimación ~200 h del H1 se MANTIENE como línea base; no se recorta scope | Decisión de calibración: medir estimación LLM vs ejecución real con codificación agéntica. Los tiempos se ajustan en el camino según avance real | Estirar H1 (no elegido), recortar scope (no elegido), combinación (no elegido) |
| 8 | Sin backlog de alto nivel H2-H4; el detalle fino se planifica por hito (rolling-wave) | El roadmap + plan de hitos + propuesta firmada ya cubren la visión de los 4 hitos; el detalle fino se hace justo antes de cada hito, calibrado con datos reales | Backlog por hito (no elegido: innecesario, el proyecto ya está bien pensado desde el principio) |

## Tradeoffs
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|

## Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| Meta API se atrasa (verificación empresa, semanas) | Sin número real para puesta en marcha de dic | Trámite inicia HOY (lado cliente); desarrollo y pruebas con test number + prepago en paralelo; no bloquea código |
| Base de conocimiento llega tarde o incompleta | Bot no es "experto desde el día 1" en H1 | Arrancar con FAQ mínimo; el gestor de KB (feature H1) permite carga incremental; deadline escrito: sem 2 (28-ago) |
| Scope creep de Max ("ya que estás, agregá...") | Come las 240 h; cronograma se rompe | Cambios fuera de propuesta → cotización separada (cláusula ya pactada); registro de cambios en session files |
| Capacidad real < 20 h/sem (otros proyectos muerden) | H1 se estira, efecto dominó | H1 como prueba de velocidad: checkpoint en sem 2 (28-ago); si no va a ritmo, renegociar expectativas TEMPRANO, no en sem 8 |
| Meta cobra service messages desde 1-oct-2026 | Costo operativo visible desde el arranque de operación real | Comunicar a Max en el primer reporte; impacto bajo al volumen esperado, pero no debe ser sorpresa |

## Open Questions
- [x] ¿Contrato firmado? ¿Fecha real de kickoff y pago 1? → Firmado y pagado el 11-ago-2026. Kickoff 17-ago.
- [x] ¿Capacidad semanal real? → ~20 h/sem (4 h/día promedio), Lumat prioridad #1.
- [x] ¿Cadencia de comunicación? → Propuesta: reporte escrito viernes + demo por hito. Pendiente OK de Stefan.
- [x] ¿Orquestación? → Propuesta: un change SDD por hito. Pendiente OK de Stefan.
- [x] ¿Ubicación del repo de código? → Se define al arrancar el apply del batch 0 (mañana).

## Action Items
- [ ] CLIENTE: iniciar trámite Meta API esta semana (cuenta de negocio, verificación empresa, registro de número) — cuello de botella #1 del cronograma
- [ ] CLIENTE: comprar SIM prepago de pruebas
- [ ] CLIENTE: comenzar a reunir base de conocimiento (manuales, procedimientos, tarifario, FAQ) — deadline 28-ago
- [ ] CLIENTE: pedir temprano decisiones de H2 (roles del equipo, política de datos) y H3 (calendario, zonas, técnicos) — gestión de dependencias
- [x] Plan de gestión completo definido (report.md)
- [x] Planificación SDD Hito 1 completa (explore → propose → spec → design → tasks)
- [ ] **MAÑANA (12-ago): arrancar apply del batch 0** — repo scaffold + app factory + webhook verify (checkpoint 24-ago)
