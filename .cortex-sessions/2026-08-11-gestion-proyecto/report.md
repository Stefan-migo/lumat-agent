# Reporte de sesión — Plan de gestión, organización y orquestación LumatAgent

> Sesión: 2026-08-11 · Proyecto: LumatAgent (cliente Lumat — Max)
> Estado: CERRADA · Siguiente paso: planificación SDD del Hito 1

---

## Resumen ejecutivo

El contrato con Lumat está **firmado** y el **Pago 1 (USD 560) recibido el 11-ago-2026**. El proyecto está oficialmente en ejecución con **kickoff el lunes 17-ago-2026**.

Se definió el plan completo de organización, orquestación y gestión: gobernanza con el cliente por reporte semanal escrito + demo por hito, desarrollo orquestado con un change SDD por hito (trazabilidad contrato → spec → tareas → código), y gestión de riesgos con los cuellos de botella externos identificados y fechas límite.

**Cronograma final (decisión de calidad):** 12 semanas de construcción (17-ago → 8-nov) + 5 semanas de pruebas y puesta en marcha (9-nov → 16-dic). Se descartó el plan comprimido 2+2 por riesgo de calidad: con ~20 h/sem no alcanza para el scope contractual completo sin recortar seguridad.

**Capacidad:** ~20 h/sem (medio tiempo, 4 h/día promedio), Lumat como prioridad sobre otros proyectos. Total ~240 h para las 12 semanas de construcción.

---

## Decisiones

| # | Decisión | Rationale |
|---|----------|-----------|
| 1 | Inicio oficial 11-ago-2026 (firma + pago 1 el mismo día) | Contrato firmado y pagado; pagos mensuales por calendario, no atados a hitos |
| 2 | Capacidad ~20 h/sem, Lumat prioridad #1 | Única fuente de desarrollo; ~240 h para la construcción |
| 3 | Orquestación: un change SDD por hito (4 changes) | Trazabilidad contrato ↔ código; cada hito cierra con verify contra sus criterios |
| 4 | Gobernanza cliente: reporte escrito viernes + demo de cierre de hito | El ritmo se sostiene con visibilidad, no con entregas forzadas |
| 5 | Dependencias del cliente por escrito, 2 semanas de anticipación | Meta API, KB y SIM son cuellos de botella externos |
| 6 | Cronograma: 12 sem construcción + 5 sem pruebas (no 2+2) | Calidad primero; el 2+2 no da con el scope completo |

---

## Riesgos (top 5) y mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Meta API se atrasa (semanas, externo) | Sin número real para dic | Trámite inicia esta semana (lado cliente); desarrollo con test number + prepago en paralelo |
| Base de conocimiento llega tarde | Bot no "experto" en H1 | FAQ mínimo + gestor de KB incremental; deadline escrito: 28-ago |
| Scope creep de Max | Come las 240 h | Cotización separada (cláusula pactada); registro de cambios |
| Capacidad real < 20 h/sem | Efecto dominó | Checkpoint de velocidad en sem 2 (28-ago): renegociar temprano |
| Meta cobra service messages desde 1-oct | Costo operativo | Comunicar a Max en el primer reporte |

---

## Calendario de pagos (independiente de hitos)

| Pago | Fecha | Monto |
|------|-------|-------|
| P1 | 11-ago ✓ | USD 560 |
| P2 | ~10-sep | USD 560 |
| P3 | ~10-oct | USD 560 |
| P4 | ~9-nov | USD 560 |
| P5 | ~9-dic | USD 560 |

Todos los pagos caen antes de la aceptación final (~16-dic). Flujo de caja asegurado.

---

## Cronograma de construcción

| Hito | Semanas | Ventana | Núcleo entregable |
|------|---------|---------|-------------------|
| 🟢 H1 Setup + WhatsApp | 1-4 | 17-ago → 13-sep | Servidor seguro + webhook + bot experto con KB + derivación a humano + panel inicial |
| 🟡 H2 Multiagente + panel | 5-7 | 14-sep → 4-oct | Orquestador LangGraph + 5 sub-agentes + bandeja humana + panel de control |
| 🔵 H3 Calendario + notif | 8-9 | 5-oct → 18-oct | Calendario propio + ICS read-only + notificaciones |
| 🟣 H4 Auto + reportes | 10-12 | 19-oct → 8-nov | Event bus + worker determinístico + automatizaciones + reportes + PWA |
| 🔧 Pruebas y puesta en marcha | 13-17 | 9-nov → 16-dic | Pruebas con prepago, ajustes, capacitación, migración al número real |

---

## Gobernanza con el cliente

- **Reporte semanal escrito (viernes):** qué se hizo, qué sigue, qué se necesita del cliente.
- **Demo de cierre de hito (4 total, 30-45 min):** validación del criterio de aceptación; libera el hito siguiente.
- **Dependencias del cliente por escrito con 2 semanas de anticipación.**
- **Control de alcance:** cambios fuera de la propuesta → cotización separada (cláusula pactada).

---

## Acciones inmediatas

**Lado cliente (mensaje a Max esta semana):**
- [ ] Iniciar trámite de la API de Meta (cuenta de negocio, verificación, registro de número) — cuello de botella #1
- [ ] Comprar SIM prepago de pruebas
- [ ] Comenzar a reunir base de conocimiento (manuales, procedimientos, tarifario, FAQ)

**Lado desarrollo (semana del 17-ago):**
- [ ] Repo nuevo de código
- [ ] Contratar VPS (Hostinger KVM 2) + dominios `agente.lumat.cl` / `panel.lumat.cl`
- [ ] Docker base + seguridad del servidor (firewall, SSH por llave, backups)
- [ ] App en Meta for Developers + esqueleto del webhook
- [ ] Checkpoint de velocidad: servidor + webhook vivos antes del 24-ago

---

## SDD Readiness

Listo para iniciar **`sdd-new` del Hito 1 (Setup + WhatsApp operativo)** con las specs derivadas de:
- Criterios de aceptación del contrato (`propuesta-final-lumatagent.md`, sección Hito 1)
- Plan de hitos detallado (`01-plan-hitos-detallado.md`)
- Requerimientos de servidor (`02-requerimientos-servidor.md`)
- Checklist de Meta API (`03-checklist-meta-api.md`)

Pendiente menor: definir ubicación del repo de código (subdirectorio de esta carpeta vs. repo separado).

---

## Próximos pasos

1. Planificar SDD del Hito 1 (proposal → spec → design → tasks)
2. Enviar a Max las acciones del lado cliente
3. Kickoff 17-ago: semana 1 de construcción
