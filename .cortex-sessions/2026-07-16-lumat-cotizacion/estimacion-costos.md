# Estimación de Costos — Lumat

> Documento de trabajo para la cotización. Las horas son estimación inicial, sujetas a ajuste según feedback del cliente y definiciones pendientes (ver preguntas-cliente.md).

---

## Supuestos generales

- Stack ya definido: VPS + Docker + PostgreSQL/pgvector + Python (FastAPI/LangChain) + Next.js
- Tarifa horaria de referencia: **$20 USD/h** (para la comparación solicitada)
- Las horas incluyen desarrollo, testing y documentación
- No incluyen tiempos de aprobación de Meta WhatsApp API, obtención de cuentas, o contenido del cliente

---

## Milestone 1 — LumatAgent (3 opciones)

### Opción A — Solo Chatbot (~200-220h)

#### Backend — FastAPI + LangChain + PostgreSQL

| Ítem | Horas |
|------|-------|
| Setup del proyecto (FastAPI, Docker, estructura base) | 6h |
| Modelos de datos + migraciones (clientes, conversaciones, mensajes, knowledge base, usuarios) | 8h |
| Auth + roles básicos (JWT, admin/operador) | 6h |
| State machine conversacional con LangGraph (flujo completo: saludo → categorías → datos → diagnóstico → derivación/cierre) | 25h |
| Integración WhatsApp Business Cloud API | 20h |
| Pipeline RAG (embeddings + pgvector + búsqueda semántica + system prompt dinámico) | 18h |
| CRUD de base de conocimiento + gestor de contenidos | 10h |
| Detección de emergencias + protocolo de seguridad + notificaciones | 10h |
| Derivación a humano (transferencia con historial + resumen) | 6h |
| Subida y validación de archivos (fotos, audio) | 6h |
| Reconocimiento de clientes + prevención de duplicados | 6h |
| Exportación de datos (CSV/Excel) | 4h |
| Compression pipeline post-conversación (background jobs) | 5h |
| **Subtotal backend** | **~130h** |

#### Frontend — Panel Administrativo (Next.js)

| Ítem | Horas |
|------|-------|
| Setup del proyecto + layout + login | 8h |
| Listado de clientes + búsqueda + ficha de cliente | 12h |
| Visor de conversaciones + historial | 10h |
| Bandeja de casos + cambio de estados + asignación | 10h |
| Editor de base de conocimiento | 8h |
| Dashboard con indicadores básicos | 6h |
| Configuración del bot (tono, reglas, mensajes) | 6h |
| UI de exportación | 2h |
| **Subtotal frontend** | **~62h** |

#### Infraestructura + Calidad

| Ítem | Horas |
|------|-------|
| Tests de integración + funcionales | 14h |
| Deploy en VPS + Docker compose + CI básico | 6h |
| Documentación + manual de uso | 6h |
| **Subtotal infra/calidad** | **~26h** |

#### Total Opción A

| Concepto | Valor |
|----------|-------|
| **Rango de horas** | **200 – 220h** |
| **Costo a $20/h** | **$4,000 – $4,400 USD** |
| **Plazo** | **6 – 8 semanas** |

---

### Opción B — Base Multi-Agente + WhatsApp (~300-340h)

Incluye todo lo de la Opción A, más:

#### Arquitectura multi-agente

| Ítem | Horas |
|------|-------|
| Orquestador LangGraph supervisor + router de sub-agentes | 20h |
| Tools layer (whitelist, validación, binding de permisos) | 15h |
| Sistema de roles completo (dueño, admin, técnico, cliente) | 10h |
| Ciclo de vida + estado compartido entre sub-agentes | 10h |
| **Subtotal arquitectura** | **~55h** |

#### Estructura de sub-agentes (scaffold)

| Ítem | Horas |
|------|-------|
| Calendar Agent (schema DB + estructura + scaffold) | 10h |
| Automation Agent (schema DB + estructura + scaffold) | 10h |
| Notification Agent (scaffold) | 5h |
| Report Agent (scaffold) | 5h |
| Worker de automatizaciones (scaffold funcional) | 10h |
| **Subtotal sub-agentes** | **~40h** |

#### Seguridad + calidad

| Ítem | Horas |
|------|-------|
| Sistema de auditoría (audit_log + consulta por rol) | 10h |
| Tests de integración multi-agente (routing, permisos, aislamiento) | 15h |
| **Subtotal seguridad/calidad** | **~25h** |

#### Total Opción B

| Concepto | Valor |
|----------|-------|
| **Rango de horas** | **300 – 340h** |
| **Costo a $20/h** | **$6,000 – $6,800 USD** |
| **Plazo** | **10 – 12 semanas** |

---

### Opción C — LumatAgent Completo (~450-500h)

Incluye todo lo de la Opción B, más:

#### Sub-agentes funcionales

| Ítem | Horas |
|------|-------|
| Automation Agent funcional: `create_automation()`, validación de triggers/acciones, confirmación al dueño, worker ejecutor real | 35h |
| Calendar Agent funcional: integración CalDAV (iPhone calendar) + Google Calendar API, disponibilidad, agendamiento, reprogramación, bloqueo manual | 40h |
| Notification Agent funcional: recordatorios programados, seguimientos post-servicio, cola de notificaciones, templates dinámicos | 20h |
| Report Agent funcional: KPIs, resumen semanal/diario, exportación avanzada | 18h |
| **Subtotal sub-agentes** | **~113h** |

#### Paneles UI

| Ítem | Horas |
|------|-------|
| Panel de automatizaciones (ver, editar, activar/desactivar reglas) | 18h |
| Vista de agenda en panel admin (disponibilidad, asignación visual de técnicos) | 15h |
| Dashboard avanzado + reportes | 10h |
| **Subtotal UI** | **~43h** |

#### Tests + Buffer

| Ítem | Horas |
|------|-------|
| Tests de integración (automatizaciones, calendario, notificaciones) | 20h |
| Buffer general | ~20h |
| **Subtotal calidad** | **~40h** |

#### Total Opción C

| Concepto | Valor |
|----------|-------|
| **Rango de horas** | **450 – 500h** |
| **Costo a $20/h** | **$9,000 – $10,000 USD** |
| **Plazo** | **14 – 18 semanas** |

---

## Milestone 2 — Página Web Lumat

### Frontend — Web (Astro o Next.js)

| Ítem | Horas |
|------|-------|
| Diseño + maquetación responsive (Inicio, Servicios, Cobertura, FAQ, Contacto) | 24h |
| Formulario de contacto + integración con bot | 8h |
| Botón WhatsApp + llamada + integración bot IA | 4h |
| SEO básico + SSL + analítica | 6h |
| Panel de edición de contenidos (CMS simple) | 14h |
| Política de privacidad + tratamiento de datos | 2h |

### Testing + Deploy

| Ítem | Horas |
|------|-------|
| Testing cross-browser + responsive | 6h |
| Deploy + dominio + SSL | 4h |
| Documentación | 2h |

### Total M2

| Concepto | Valor |
|----------|-------|
| **Horas totales** | **70h** |
| **Costo a $20/h** | **$1,400 USD** |
| **Costo a $30/h** | **$2,100 USD** |
| **Rango sugerido precio fijo** | **$1,800 – $2,500 USD** |

---

## Milestone 3 — Catálogo, Agenda, Pagos e Integraciones

### Backend

| Ítem | Horas |
|------|-------|
| Catálogo de servicios (CRUD + categorías) | 10h |
| Motor de agendamiento (bloques, técnicos, disponibilidad, prevención doble reserva) | 24h |
| Sincronización Google Calendar | 10h |
| Gestión de técnicos (asignación, disponibilidad, zonas) | 8h |
| Módulo de pagos (integración MercadoPago/Transbank + registro manual) | 18h |
| Postventa + garantías + reclamos | 10h |
| Notificaciones automáticas (WhatsApp + correo: confirmaciones, recordatorios, alertas) | 10h |
| Botón de emergencia + notificación inmediata | 4h |
| **Subtotal backend** | **94h** |

### Frontend — Extensiones del Panel

| Ítem | Horas |
|------|-------|
| Catálogo visible desde web + admin | 6h |
| Calendario + agendamiento UI | 8h |
| Panel de pagos + estados | 6h |
| Ficha de cliente extendida (equipos, visitas, pagos, garantías) | 8h |
| Dashboard avanzado (ingresos, visitas, técnicos) | 6h |
| **Subtotal frontend** | **34h** |

### Testing + Deploy

| Ítem | Horas |
|------|-------|
| Tests de integración (agenda, pagos, notificaciones) | 10h |
| Deploy + configuración | 4h |
| Documentación | 4h |

### Total M3

| Concepto | Valor |
|----------|-------|
| **Horas totales** | **146h** |
| **Costo a $20/h** | **$2,920 USD** |
| **Costo a $30/h** | **$4,380 USD** |
| **Rango sugerido precio fijo** | **$3,800 – $5,000 USD** |

---

## Totales Globales

### Por hora ($20/h)

| Milestone | Horas | Costo |
|-----------|-------|-------|
| **M1 — LumatAgent** (3 opciones) | | |
| &nbsp;&nbsp;Opción A — Chatbot | 200–220h | $4,000 – $4,400 |
| &nbsp;&nbsp;Opción B — Multi-Agente + WhatsApp | 300–340h | $6,000 – $6,800 |
| &nbsp;&nbsp;Opción C — LumatAgent Completo | 450–500h | $9,000 – $10,000 |
| **M2 — Web** | 70h | $1,400 |
| **M3 — Agenda/Pagos** | 146h | $2,920 |

### Precio fijo (rango sugerido)

| Milestone | Precio Fijo |
|-----------|-------------|
| **M1 — LumatAgent** | |
| &nbsp;&nbsp;Opción A — Chatbot | $4,000 – $4,400 USD |
| &nbsp;&nbsp;Opción B — Multi-Agente + WhatsApp | $6,000 – $6,800 USD |
| &nbsp;&nbsp;Opción C — LumatAgent Completo | $9,000 – $10,000 USD |
| **M2 — Web** | $1,800 – $2,500 USD |
| **M3 — Agenda/Pagos** | $3,800 – $5,000 USD |
| **Proyecto completo** (depende de opción M1) | **$9,600 – $17,500 USD** |

---

---

## Costos Mensuales y Variables

### Infraestructura base

| Concepto | Proveedor | Costo mensual | Notas |
|----------|-----------|---------------|-------|
| VPS (4 vCPU, 8GB RAM, 80GB SSD) | Hetzner CX32 | **~$9 USD** | Suficiente para bot + web + DB + Redis liviano |
| Dominio .cl | NIC Chile | **~$1 USD** ($10-12/año) | A nombre del cliente |
| Certificado SSL | Let's Encrypt | **$0** | Automático con Docker/Caddy |
| Backups adicionales | Hetzner Storage Box | **~$3 USD** | Opcional, 100GB |
| **Subtotal infraestructura** | | **~$10-13 USD/mes** | |

### APIs y servicios externos

| Concepto | Proveedor | Costo estimado | Notas |
|----------|-----------|----------------|-------|
| OpenAI API | GPT-4o-mini | **$5 – $20 USD/mes** | ~100-500 conversaciones/día. Input $0.15/1M tokens, output $0.60/1M |
| Embeddings | OpenAI text-embedding-3-small | **~$1 USD/mes** | $0.02/1M tokens. Solo para RAG |
| WhatsApp Business API | Meta | **$5 – $15 USD/mes** | Conversaciones de servicio iniciadas por cliente son gratis dentro de ventana 24h. Solo se cobra templates fuera de ventana |
| **Subtotal APIs** | | **~$11 – $36 USD/mes** | |

### Servicios complementarios

| Concepto | Proveedor | Costo | Notas |
|----------|-----------|-------|-------|
| Email transaccional | Resend / SendGrid | **$0 – $5 USD/mes** | Free tier cubre 100 emails/día. Para notificaciones |
| Monitoreo uptime | UptimeRobot | **$0** | Free tier: 5 monitores cada 5 min |
| **Subtotal complementos** | | **~$0 – $5 USD/mes** | |

### Soporte y mantenimiento

| Concepto | Costo mensual | Notas |
|----------|---------------|-------|
| Mantenimiento básico (bugs, updates, backups) | **$50 – $100 USD/mes** | Opcional. Incluye horas de revisión/resolución |
| Soporte reactivo (pago por evento) | **$30-50 USD/hora** | Alternativa sin retención mensual |

### Total por mes (sin soporte mantenido)

| Escenario | VPS | APIs | Complementos | **Total** |
|-----------|-----|------|--------------|-----------|
| **Bajo uso** (~100 conv/día) | $10 | $11 | $0 | **~$21 USD/mes** |
| **Uso medio** (~300 conv/día) | $13 | $25 | $3 | **~$41 USD/mes** |
| **Uso alto** (~500+ conv/día) | $13 | $41 | $5 | **~$59 USD/mes** |

### Total por mes (con soporte incluido)

| Escenario | Operación | Soporte | **Total** |
|-----------|-----------|---------|-----------|
| **Básico** | $21/mes | $50/mes | **~$71 USD/mes** |
| **Medio** | $41/mes | $75/mes | **~$116 USD/mes** |
| **Alto** | $59/mes | $100/mes | **~$159 USD/mes** |

### Costos variables a considerar

| Concepto | Costo | Impacto al escalar |
|----------|-------|--------------------|
| OpenAI por conversación extra | ~$0.001 – $0.003 | Lineal. 1000 conv/día ~ $40-60/mes |
| WhatsApp template fuera de 24h | ~$0.04 – $0.08 por template | Depende de cuántos recordatorios/campañas |
| Ancho de banda VPS | Incluido con Hetzner (20TB) | No preocupa a menos que sea streaming |
| Almacenamiento extra | ~$3/mes cada 100GB | Fotos de clientes pueden sumar |

---

## Plazos y Entregables

### Supuestos de plazo

- Dedicación **full-time** (~40h/semana) en cada milestone
- No considera tiempos muertos por aprobaciones del cliente, demora de Meta, o contenido pendiente
- M2 puede solaparse parcialmente con M1 (el frontend web es independiente del backend del bot)

### Milestone 1 — Bot IA

**Plazo estimado: 6–8 semanas**

| Semana | Entregable |
|--------|------------|
| 1–2 | Setup del proyecto, modelos de datos, auth, Docker base |
| 3–4 | State machine conversacional (LangGraph), flujo completo |
| 5 | Integración WhatsApp API, detección de emergencias, derivación |
| 6 | RAG + base de conocimiento + subida de archivos |
| 7 | Panel administrativo funcional (clientes, conversaciones, casos) |
| 8 | Dashboard, exportación, tests, deploy, documentación |

**Entregables finales:**
- Bot funcional en ambiente de prueba (enlace web)
- Conexión a WhatsApp Business productivo
- Base de conocimiento inicial cargada
- Captura estructurada de datos y archivos
- Detección de emergencia + derivación humana con resumen
- Ficha de clientes + registro de conversaciones
- Panel administrativo completo (login, clientes, conversaciones, casos, estados)
- Exportación CSV/Excel
- Dashboard con indicadores básicos
- Pruebas funcionales + manual de uso + capacitación
- Cuentas, accesos y documentación técnica entregada a Lumat

### Milestone 2 — Página Web

**Plazo estimado: 3–4 semanas** *(puede solaparse con semanas 6–9 de M1)*

| Semana | Entregable |
|--------|------------|
| 1 | Diseño + maquetación de todas las secciones |
| 2 | Formulario de contacto + integraciones (WhatsApp, bot IA) |
| 3 | CMS de contenidos + SEO + analítica + SSL |
| 4 | Tests responsive, deploy, documentación |

**Entregables finales:**
- Diseño web aprobado por Lumat
- Página publicada en el dominio (responsive móvil + escritorio)
- Formulario de contacto funcional
- Botones WhatsApp + llamada
- Bot IA integrado en la web
- Configuración de dominio, SSL y analítica
- Panel de edición de contenidos (CMS simple)
- Pruebas + capacitación

### Milestone 3 — Catálogo, Agenda, Pagos

**Plazo estimado: 6–8 semanas**

| Semana | Entregable |
|--------|------------|
| 1 | Catálogo de servicios (CRUD + frontend) |
| 2–3 | Motor de agendamiento + calendario + disponibilidad de técnicos |
| 4 | Google Calendar sync + notificaciones (WhatsApp/correo) |
| 5 | Integración de pagos (MercadoPago/Transbank) + panel |
| 6 | Postventa + garantías + emergencia |
| 7 | Automatizaciones + dashboard avanzado |
| 8 | Tests integrados, deploy, documentación final |

**Entregables finales:**
- Catálogo completo de servicios
- Agenda integrada con Google Calendar
- Asignación de técnicos + prevención de dobles reservas
- Confirmaciones y recordatorios automáticos
- Base de clientes consolidada (con equipos, visitas, pagos)
- Integración de pagos (tarjeta débito/crédito, transferencia, efectivo)
- Módulo de postventa y garantías
- Automatizaciones y notificaciones
- Panel administrativo extendido (dashboard de ingresos/técnicos/visitas)
- Pruebas + manuales + capacitación

### Línea de tiempo consolidada

#### Opción A — Chatbot (M1 más rápido)

```
Semana:  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16
M1-A:    ██████████████████████████████████░░░░░░░░░░░░░░░░
M2:      ░░░░░░░░░░░░░░░░████████████████░░░░░░░░░░░░░░░░░
M3:      ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░████████████████
         └── M1: 8 sem ──┘ M2: 4 sem └── M3: 7 sem ──┘
         └────────── Proyecto total: ~16 semanas (~4 meses) ──┘
```

#### Opción B — Base Multi-Agente + WhatsApp

```
Semana:  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18
M1-B:    ████████████████████████████████████████████████░░░░░░░
M2:      ░░░░░░░░░░░░░░░░░░████████████████░░░░░░░░░░░░░░░░░░░░░
M3:      ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░███████████
         └── M1: 12 sem ────┘ M2: 4 sem └── M3: 7 sem ──┘
         └────────── Proyecto total: ~19 semanas (~5 meses) ──┘
```

#### Opción C — LumatAgent Completo

```
Semana:  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19 20 21 22
M1-C:    ████████████████████████████████████████████████████████████████░░
M2:      ░░░░░░░░░░░░░░░░░░░░░░░░████████████████░░░░░░░░░░░░░░░░░░░░░░░░░
M3:      ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██████████
         └── M1: 18 sem ──────────┘ M2: 4 sem └── M3: 7 sem ──┘
         └────────── Proyecto total: ~22 semanas (~5.5 meses) ──┘
```

*M2 en paralelo parcial con M1. Secuencia exacta depende de si el cliente quiere la web antes o después del agente.*

| Escenario | Opción A | Opción B | Opción C |
|-----------|----------|----------|----------|
| **M1 solamente** | 6–8 sem | 10–12 sem | 14–18 sem |
| **M1 + M2 solapados** | ~10–12 sem | ~14–16 sem | ~18–22 sem |
| **Proyecto completo secuencial** | ~17–20 sem | ~22–25 sem | ~27–33 sem |

---

---

## Exclusiones

Lo siguiente **NO está incluido** en los valores cotizados por milestone. Se puede cotizar por separado si el cliente lo requiere.

| # | Exclusión | Detalle |
|---|-----------|---------|
| 1 | **Contenido del cliente** | Textos, fotos, logos, procedimientos técnicos, códigos de error, tarifarios. Nosotros creamos la estructura y cargamos lo que el cliente entregue. |
| 2 | **Aprobación de Meta WhatsApp** | El proceso de aprobación del número de WhatsApp Business depende de Meta y sus tiempos. Si hay rechazo, se re-aplica sin costo, pero el plazo se corre. |
| 3 | **Cuentas de terceros** | Las cuentas de OpenAI, Meta, Google, dominio, servidor, etc. van a nombre y costo del cliente. Nosotros configuramos y entregamos accesos. |
| 4 | **Diseño gráfico / branding** | Si el cliente no tiene logo, colores ni identidad visual definida, se entrega con diseño limpio y profesional pero sin marca personalizada. El diseño de marca se cotiza aparte. |
| 5 | **Redacción de base de conocimiento** | La estructura, el método de carga y la herramienta de edición están incluidos. El contenido técnico (FAQ, troubleshooting, procedimientos) lo escribe Lumat. |
| 6 | **App móvil nativa** | Todo es web responsive + WhatsApp. No hay app iOS/Android nativa. |
| 7 | **Facturación electrónica (SII)** | Registro de pagos sí incluido. Emisión de facturas electrónicas, boletas o integración con SII NO. |
| 8 | **Inventario / stock de repuestos** | No hay control de inventario de repuestos ni piezas. |
| 9 | **Migración de datos existentes** | Si Lumat tiene datos en Excel, otro CRM o papel, migrarlos se cotiza aparte (depende del volumen y estado). |
| 10 | **Capacitación presencial** | Manual de uso + capacitación remota (videollamada) incluida. Presencial en domicilio del cliente no. |
| 11 | **Cambios de alcance** | Cualquier funcionalidad no listada en los entregables de cada milestone se cotiza como extra. El alcance se congela al firmar. |
| 12 | **Contenido multimedia** | Fotografías, videos o audio promocional para la web. El cliente debe proveerlos o se cotiza producción aparte. |
| 13 | **Publicidad / Google Ads / Meta Ads** | Solo integración con analítica. Gestión de campañas no incluida. |
| 14 | **Módulos contables o de gestión empresarial** | M3 incluye agenda + pagos + postventa. Un ERP o software de gestión completo no está en alcance (ver estrategia M3). |

---

## Garantía

| Ítem | Condición |
|------|-----------|
| **Período** | **60 días corridos** desde la entrega y aceptación de cada milestone |
| **Cobertura** | Corrección de errores de funcionamiento, bugs, desviaciones del alcance acordado |
| **No cubre** | Cambios de alcance, contenido nuevo, modificaciones no acordadas, problemas por intervención de terceros, rotura por mal uso, caídas de servicios externos (API OpenAI, WhatsApp, VPS) |
| **Tiempo de respuesta** | Errores críticos (bot caído, no responde): **máx. 24h hábiles**. Errores menores: **máx. 72h hábiles** |
| **Post-garantía** | Soporte continuado vía retén mensual (ver costos mensuales) o pago por evento a tarifa de $30-50/h |

---

## Estrategia M3 — Alcance base + cláusula de re-evaluación

### El problema

El Milestone 3 del LumatRequest.md es ambicioso: catálogo + agenda + pagos + postventa + automatizaciones. Si el cliente después quiere facturación electrónica, inventario, CRM completo o reportes avanzados, M3 se desborda.

### La solución

**Dos fases dentro de M3:**

| Fase | Alcance | Incluido en M3 |
|------|---------|----------------|
| **M3 Base** | Catálogo de servicios + agendamiento + Google Calendar + pagos (tarjeta/transferencia/efectivo) + postventa + automatizaciones + notificaciones | ✅ Sí |
| **M3 Extendido** | Facturación electrónica SII, inventario de repuestos, CRM avanzado, reportes personalizados, app móvil, dashboard gerencial | ❌ No incluido. Se evalúa después deoperar M3 Base por 3-6 meses |

### Cláusula sugerida para la cotización

> "El Milestone 3 se cotiza con el alcance base descrito. Una vez que Lumat opere el sistema completo por un período mínimo de 3 meses, se evaluarán las necesidades reales de extensiones (facturación electrónica, inventario, reportes avanzados) y se cotizarán por separado en función de la experiencia de uso. Esto evita construir funcionalidades que parecen necesarias en el papel pero no se usan en la práctica."

---

## Notas importantes

1. **$20/h es extremadamente barato** para desarrollo especializado (Python + IA + infra). Un desarrollador freelance latinoamericano está en $30-50/h, uno US/EU en $80-150/h. Usé $20/h porque lo pediste como referencia, pero no es sostenible como tarifa real.
2. **Precio fijo** incluye un factor de riesgo por alcance — por eso es ~20-30% más alto que el cálculo por hora.
3. **Horas no incluyen**: contenido del cliente (textos, fotos, procedimientos), aprobación de Meta, gestión de cuentas, correcciones por cambios de alcance no contemplados.
4. **M3** puede escalar bastante si el cliente quiere facturación electrónica, inventario, o módulos contables — sugerí alcance base con cláusula de re-evaluación.
