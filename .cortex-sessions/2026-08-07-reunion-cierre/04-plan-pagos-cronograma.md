# LumatAgent — Plan de pagos y cronograma

> Documento de propuesta para la etapa de contrato — Lumat (Maximiliano) / HandCodeStudio (Stefan Miranda)
> Fecha: 7 de agosto de 2026
> **Estatus: propuesta de negociación. Los montos, porcentajes y fechas son tentativos hasta la firma del contrato.**

---

## Resumen

| Concepto | Valor |
|----------|-------|
| Presupuesto total | **USD 3,000** (construcción completa de los 4 hitos del plan) |
| Construcción del core | ~2 meses de desarrollo |
| Pruebas y ajustes | ~4 semanas adicionales con número prepago, antes de migrar al número real |
| Forma de trabajo | Por hitos, con entregable funcional y aprobación al cierre de cada hito |
| Garantía | 60 días corridos desde la entrega |

El proyecto se desarrolla por hitos con entregables visibles. Cada hito se aprueba formalmente por Lumat antes de avanzar, y **cada pago está asociado a la aprobación de un hito** (ver condiciones).

---

## Plan de pagos

El proyecto se paga en **5 pagos de igual monto (USD 600 cada uno)**. El **Pago 1 corresponde a la seña** al firmar el contrato, y los **Pagos 2 a 5** se asocian a la **aprobación formal de cada hito** (Hito 1, 2, 3 y 4).

| Pago | Momento | Monto |
|------|---------|-------|
| Pago 1 | Seña al firmar el contrato | USD 600 |
| Pago 2 | Aprobación del Hito 1 | USD 600 |
| Pago 3 | Aprobación del Hito 2 | USD 600 |
| Pago 4 | Aprobación del Hito 3 | USD 600 |
| Pago 5 | Aprobación del Hito 4 | USD 600 |
| **Total** | **5 pagos** | **USD 3,000** |

Si el proyecto se atrasa o avanza más rápido, los pagos siguen atados a la **APROBACIÓN** de cada hito, no a fechas de calendario.

---

## Descuentos y condiciones

- **Pago único adelantado (5% de descuento)**: el total queda en **USD 2,850** (3,000 × 0.95), en 5 pagos de **USD 570** cada uno (2,850 ÷ 5).
- **Alternativa de precio redondeado USD 2,800**: 5 pagos de **USD 560** cada uno (2,800 ÷ 5). Ese precio equivale a un descuento del **6.67%** sobre los USD 3,000 (200 ÷ 3,000); si se elige esta opción, presentarla como "≈7% de descuento".
- **Descuento por continuidad**: si Lumat contrata la web (M2) luego de validar el agente, se acuerda un descuento sobre el valor de la web al momento de cotizarla.
- **Los pagos están asociados a la APROBACIÓN de cada hito**: la aceptación formal del entregable por parte de Lumat habilita el pago correspondiente. El "listo" de cada hito se define en `01-plan-hitos-detallado.md` (criterio de aceptación de cada fase).
- Los ajustes o cambios de alcance que excedan lo pactado se evalúan y cotizan por separado.
- **Garantía**: 60 días corridos desde la entrega final.

---

## Cronograma tentativo

> Fechas asumidas con kickoff el **lunes 17 de agosto de 2026**. Son tentativas y se ajustan según la fecha de firma del contrato y el avance del trámite de Meta. La construcción del core son ~12 semanas y las pruebas/ajustes ~4 semanas (16 semanas totales).

| Etapa | Período | Contenido |
|-------|---------|-----------|
| Hito 1 — Setup + WhatsApp operativo | Semanas 1-4 (17 ago – 11 sep) | 🟢 Servidor seguro, bot experto por WhatsApp, base de conocimiento |
| Hito 2 — Arquitectura multiagente + panel | Semanas 5-7 (14 sep – 2 oct) | 🟡 Orquestador + 5 sub-agentes, panel web de control |
| Hito 3 — Calendario + notificaciones | Semanas 8-9 (5 oct – 16 oct) | 🔵 Agenda automática, calendario propio, avisos al equipo |
| Hito 4 — Automatizaciones + reportes | Semanas 10-12 (19 oct – 6 nov) | 🟣 Automatizaciones por lenguaje natural, reportes, panel PWA |
| Pruebas en producción | Semanas 13-16 (9 nov – 4 dic) | Pruebas con número prepago, ajustes, capacitación, migración al número real |
| **Entrega / aceptación final** | **~4 de diciembre de 2026** | Sistema validado y operativo; inicio de garantía (60 días) |

**Nota de decisión pendiente (la define Stefan con el cliente):**
- El roadmap interno del proyecto indica **14 semanas** totales de construcción.
- En la reunión del 7 de agosto se mencionó "construcción **≤ 2 meses** + pruebas/ajustes".
- El cronograma presentado aquí **combina ambos**: construcción ~12 semanas + pruebas/ajuste ~4 semanas (16 semanas totales).
- Si Lumat requiere comprometer **2 meses de construcción pura** (≈8-9 semanas), los hitos 2 y 3 se pueden comprimir solapando tareas, con el consecuente ajuste de fechas.
- **Pendiente confirmar con el cliente**: ¿el plazo comprometido es de 2 meses de construcción a secas, o el cronograma completo de 16 semanas con pruebas? La respuesta define la versión final de esta tabla.

---

## Post-entrega (acuerdos del roadmap)

| Concepto | Detalle |
|----------|---------|
| Garantía | 60 días corridos desde la entrega |
| Soporte mensual | $50-100 USD/mes (mantenimiento, bugs, actualizaciones) |
| Soporte por evento | $30-50 USD/hora (sin retención mensual) |
| Web (M2) | Se evalúa después del Hito 2 (semana 8); el agente puede integrarse con la web del proveedor que Lumat elija |
| Web en standby | La web (M2) queda en standby por 3 meses por acuerdo previo, mientras se valida el agente |

---

## Costos operativos a considerar

Costos referenciales de operación mensual una vez en producción, sujetos a tarifas vigentes de Meta y de los proveedores:

| Concepto | Costo referencial |
|----------|-------------------|
| VPS Hostinger KVM 2 (São Paulo) | ~US$8.79/mes intro (2 años prepago) / ~US$14.99 renovación; alternativa local MOX (Santiago): ~US$18/mes (CLP 17.000); Hetzner como staging. Referencial. |
| Plantillas aprobadas fuera de la ventana de 24 h | ~$0.04-0.08/mensaje |
| **Mensajes de respuesta (service messages, dentro de la ventana)** | **GRATIS hasta el 1-oct-2026; desde esa fecha Meta los cobra por mensaje entregado (Chile habilitado)** |

**Nota importante sobre los service messages**: las respuestas que el bot y el equipo envían dentro de la ventana de 24 horas están gratis hasta el **1 de octubre de 2026**; desde esa fecha Meta las cobra por mensaje entregado, y Chile está entre los mercados habilitados. Dado que las pruebas finales y el inicio de la operación están previstos para **~diciembre de 2026**, este costo aplica desde el arranque de la operación real. Al volumen esperado (decenas de conversaciones diarias) el impacto es bajo, pero conviene conocerlo para planificar el presupuesto mensual.

---

## Para arrancar el proyecto

Stefan necesita de Lumat para comenzar el Hito 1:

1. **Contrato firmado** (este plan de pagos con la opción elegida).
2. **Seña de inicio**: Pago 1 de USD 600 (5 pagos iguales de USD 600 en total; con descuento por pago único adelantado, USD 570 por pago).
3. **Trámite de Meta iniciado** (crear la cuenta de negocio; ver `03-checklist-meta-api.md`).
4. **Base de conocimiento inicial** (manuales, procedimientos, tarifario, FAQ — se puede partir con lo disponible).
5. **Número prepago dedicado** de pruebas adquirido y disponible.

Con eso, el kickoff queda programado para la semana siguiente a la firma.
