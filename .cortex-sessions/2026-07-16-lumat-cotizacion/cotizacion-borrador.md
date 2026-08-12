# Cotización Lumat — BORRADOR INTERNO

> 📌 **Documento de trabajo para revisión personal. No enviar al cliente sin antes revisar y ajustar valores, plazos y condiciones.**

---

## Resumen ejecutivo

Tres milestones para el sistema digital de Lumat: Bot IA de atención al cliente (M1), Página web institucional (M2), y Catálogo + Agenda + Pagos (M3). Stack completo en VPS propio del cliente con Docker, PostgreSQL, Python y Next.js. Sin vendor lock-in, datos bajo control de Lumat.

---

## Milestone 1 — LumatAgent

> Este milestone se presenta en **3 opciones** para que Lumat elija según su presupuesto y visión de crecimiento. Las tres opciones entregan WhatsApp funcional desde el día 1, pero con distinta profundidad arquitectónica. La Opción A es la más rápida y económica, pero requiere refactor para escalar a automatizaciones y agenda. Las Opciones B y C construyen la base multi-agente desde el inicio, permitiendo agregar funcionalidades sin reescribir.

---

### Opción A — Chatbot IA (funcionalidad inmediata)

| Campo | Información |
|-------|-------------|
| **Alcance** | Bot conversacional con IA, flujo completo de atención por WhatsApp, RAG sobre base de conocimiento, detección de emergencias, derivación a humano, registro de clientes, panel administrativo |
| **Exclusiones** | Contenido de base de conocimiento (lo escribe Lumat), aprobación de Meta WhatsApp, branding/diseño gráfico |
| **Entregables** | Bot productivo en WhatsApp + web, panel admin completo, base de conocimiento inicial cargada, manual de uso |
| **Plazo** | 6 a 8 semanas |
| **Costo inicial** | **$4,000 – $4,400 USD** (precio fijo) |
| **Arquitectura** | Bot monolítico con LangGraph — un solo grafo conversacional. Correcto para operar, pero requiere rediseño si después se quiere expandir a automatizaciones, agenda, o agentes internos. |

**Componentes incluidos**

- [x] Bot IA con LangGraph (state machine conversacional)
- [x] Integración WhatsApp Business Cloud API
- [x] Pipeline RAG con pgvector (base de conocimiento vectorial)
- [x] Detección de emergencias + protocolo de seguridad
- [x] Derivación a humano con resumen de conversación
- [x] Captura estructurada de datos del cliente (nombre, teléfono, dirección, equipo, falla, evidencia)
- [x] Reconocimiento de clientes existentes por número de teléfono
- [x] Subida y almacenamiento de fotos/audio
- [x] Panel administrativo (login, clientes, conversaciones, casos, estados, exportación)
- [x] Dashboard con indicadores básicos
- [x] Editor de base de conocimiento
- [x] Configuración del bot (tono, reglas, mensajes)

---

### Opción B — Base Multi-Agente + WhatsApp (recomendada)

| Campo | Información |
|-------|-------------|
| **Alcance** | Toda la funcionalidad de la Opción A, **más** la arquitectura completa de LumatAgent: orquestador multi-agente, sistema de roles (dueño/admin/técnico/cliente), tools layer con permisos, auditoría completa, y estructura de los 4 sub-agentes restantes (Calendar, Automation, Notification, Report). Solo WhatsApp Agent está funcional — los demás existen y pueden activarse sin refactor. |
| **Exclusiones** | Mismas que Opción A + automatizaciones y agendamiento no están operativos (solo su estructura) |
| **Entregables** | Mismos que Opción A + arquitectura multi-agente documentada + estructura de sub-agentes lista para activar |
| **Plazo** | 10 a 12 semanas |
| **Costo inicial** | **$6,000 – $6,800 USD** (precio fijo) |
| **Arquitectura** | Orquestador (LangGraph supervisor) + router de sub-agentes + tools layer + sistema de roles + auditoría. Cuando Lumat quiera activar Calendar Agent, Automation Agent, etc., no se reescribe nada — se implementa la lógica de negocio sobre la estructura existente. |

**Componentes incluidos (todo lo de Opción A más)**

- [x] Arquitectura multi-agente (orquestador + router de sub-agentes)
- [x] Tools layer con whitelist de acciones y validación de parámetros
- [x] Sistema de roles completo: dueño (lenguaje natural con el agente), admin (gestión), técnico (operativo), cliente (solo WhatsApp)
- [x] Registro de auditoría (`audit_log`) — cada acción del agente queda trazada
- [x] Calendar Agent (estructura + schema DB) — listo para activar
- [x] Automation Agent (estructura + schema DB) — listo para activar
- [x] Notification Agent (estructura) — listo para activar
- [x] Report Agent (estructura) — listo para activar
- [x] Worker de automatizaciones (scaffold funcional, sin reglas de negocio)

---

### Opción C — LumatAgent Completo

| Campo | Información |
|-------|-------------|
| **Alcance** | Todo lo de la Opción B, **más** todos los sub-agentes funcionales: Automation Agent (el dueño crea automatizaciones en lenguaje natural), Calendar Agent (CalDAV iPhone + Google Calendar, agendamiento, disponibilidad), Notification Agent (recordatorios, seguimientos post-servicio), Report Agent (KPIs, exportaciones). El dueño puede gestionar su negocio conversando con el agente. |
| **Exclusiones** | Mismas que Opción B |
| **Entregables** | Mismos que Opción B + todos los sub-agentes operativos + paneles UI + manual de automatizaciones |
| **Plazo** | 14 a 18 semanas |
| **Costo inicial** | **$9,000 – $10,000 USD** (precio fijo) |
| **Arquitectura** | Idéntica a Opción B, pero con toda la lógica de negocio implementada. El dueño puede decirle al agente "creá una automatización que envíe seguimiento 3 días después de un servicio" y el agente la crea como configuración en DB (no como código). |

**Componentes incluidos (todo lo de Opción B más)**

- [x] Automation Agent funcional: `create_automation()`, `list_automations()`, `toggle_automation()` — el dueño crea reglas en lenguaje natural
- [x] Calendar Agent funcional: integración CalDAV (iPhone calendar) + Google Calendar, disponibilidad por técnico, agendamiento, reprogramación, bloqueo manual
- [x] Notification Agent funcional: recordatorios programados, seguimientos post-servicio, alertas de emergencia, templates dinámicos
- [x] Report Agent funcional: KPIs, resumen semanal/diario, exportación avanzada
- [x] Panel de automatizaciones (UI para ver, editar, activar/desactivar reglas)
- [x] Vista de agenda en panel admin (disponibilidad, asignación visual de técnicos)

---

### Comparativa rápida de opciones

| Aspecto | A — Chatbot | B — Multi-Agente | C — Completo |
|---|---|---|---|
| WhatsApp funcional | ✅ | ✅ | ✅ |
| Panel admin | ✅ | ✅ | ✅ |
| Arquitectura multi-agente | ❌ | ✅ | ✅ |
| Roles (dueño/admin/técnico) | ❌ Básico | ✅ Completo | ✅ Completo |
| Automatizaciones | ❌ | ❌ (estructura) | ✅ |
| Calendar + Agenda | ❌ | ❌ (estructura) | ✅ |
| Refactor para M3 | 🔴 Necesario | 🟢 No necesario | 🟢 No necesario |
| Plazo | 6-8 sem | 10-12 sem | 14-18 sem |
| **Precio** | **$4,000–$4,400** | **$6,000–$6,800** | **$9,000–$10,000** |

---

## Milestone 2 — Página Web Lumat

| Campo | Información |
|-------|-------------|
| **Milestone** | M2 — Página web institucional |
| **Alcance** | Sitio web responsive, presentación de servicios, formulario de contacto, botón WhatsApp, bot IA integrado, CMS de contenidos, SEO básico, analítica |
| **Exclusiones** | Redacción de textos, fotografía/productos multimedia, diseño de marca/logo, publicidad online |
| **Entregables** | Web publicada en dominio propio, responsive (móvil + escritorio), formulario funcional, panel de edición de contenidos |
| **Plazo** | 3 a 4 semanas (puede solaparse con M1) |
| **Costo inicial** | **$X,XXX USD** (precio fijo) |
| **Costo mensual** | Ver costos operativos |
| **Garantía** | 60 días desde la aceptación |
| **Soporte** | Ver opciones de soporte |
| **Propiedad** | Código, dominio y datos pertenecen a Lumat |

### Componentes incluidos

- [x] Diseño responsive (computador, tablet, celular)
- [x] Secciones: Inicio, Servicios (calefont/caldera/calefacción), Cobertura, FAQ, Contacto
- [x] Formulario de contacto con captura de datos + carga de fotos
- [x] Botón flotante de WhatsApp + botón de llamada
- [x] Integración del Bot IA en la web
- [x] CMS simple para editar textos, imágenes y servicios
- [x] SEO básico (meta tags, sitemap, estructura semántica)
- [x] Google Analytics / similar
- [x] SSL + dominio propio
- [x] Política de privacidad y tratamiento de datos

---

## Milestone 3 — Catálogo, Agenda, Pagos e Integraciones

| Campo | Información |
|-------|-------------|
| **Milestone** | M3 — Catálogo de servicios, agendamiento, pagos y postventa |
| **Alcance** | Catálogo detallado de servicios, agenda con técnicos, Google Calendar sync, pagos (tarjeta/transferencia/efectivo), postventa y garantías, notificaciones automáticas |
| **Exclusiones** | Facturación electrónica SII, inventario de repuestos, app móvil nativa, CRM avanzado, reportes personalizados (ver estrategia M3) |
| **Entregables** | Catálogo online, agenda funcional con técnicos, pagos operativos, postventa funcional, panel extendido |
| **Plazo** | 6 a 8 semanas (después de M1) |
| **Costo inicial** | **$X,XXX USD** (precio fijo) |
| **Costo mensual** | Ver costos operativos |
| **Garantía** | 60 días desde la aceptación |
| **Soporte** | Ver opciones de soporte |
| **Propiedad** | Código y datos pertenecen a Lumat |

### Componentes incluidos

- [x] Catálogo de servicios con nombre, descripción, problemas que resuelve
- [x] Motor de agendamiento con bloques de 1 hora
- [x] Disponibilidad y asignación por técnico
- [x] Prevención de reservas dobles
- [x] Bloqueo manual de horarios
- [x] Sincronización con Google Calendar
- [x] Confirmaciones y recordatorios por WhatsApp + correo
- [x] Reprogramación y cancelación
- [x] Integración de pagos (MercadoPago o Transbank): tarjeta débito/crédito, transferencia, efectivo
- [x] Panel de revisión de pagos
- [x] Postventa y gestión de garantías
- [x] Botón de emergencia en la web
- [x] Notificaciones automáticas (nuevas solicitudes, reservas, cancelaciones, emergencias)
- [x] Resumen diario/semanal para administración
- [x] Dashboard avanzado (ingresos, visitas por técnico, conversiones)

### Estrategia M3 — Alcance base + re-evaluación

Este milestone se entrega con el alcance base descrito. Una vez que Lumat opere el sistema completo por un mínimo de 3 meses, se evaluarán las necesidades reales de extensiones:

| Posible extensión | Se evalúa después de M3 Base |
|-------------------|------------------------------|
| Facturación electrónica (SII) | ✅ Sí |
| Inventario de repuestos | ✅ Sí |
| App móvil nativa | ✅ Sí |
| CRM avanzado con reportes | ✅ Sí |
| Dashboard gerencial | ✅ Sí |

Esto evita construir funcionalidades que parecen necesarias en el papel pero no se usan en la práctica.

---

## Costos Mensuales y Variables (Operación)

### Escenario recomendado — inicio

| Concepto | Costo |
|----------|-------|
| VPS Hetzner CX32 (4 vCPU, 8GB RAM) | ~$9 USD/mes |
| OpenAI GPT-4o-mini (~100 convs/día) | ~$6 USD/mes |
| Embeddings (RAG) | ~$1 USD/mes |
| WhatsApp API | ~$5 USD/mes |
| Dominio .cl | ~$1 USD/mes |
| Email transaccional (SendGrid free) | $0 USD/mes |
| Monitoreo (UptimeRobot free) | $0 USD/mes |
| **Total operación** | **~$22 USD/mes** |

### Escenarios por volumen

| Volumen de conversaciones | Costo operación mensual |
|---------------------------|------------------------|
| **Bajo** (~100/día) | **~$22 USD/mes** |
| **Medio** (~300/día) | **~$41 USD/mes** |
| **Alto** (~500+/día) | **~$59 USD/mes** |

### Soporte y mantenimiento (opcional)

| Modalidad | Costo | Incluye |
|-----------|-------|---------|
| **Retén mensual** | $50–100 USD/mes | Bugs, updates, backups, revisiones periódicas |
| **Pago por evento** | $30–50 USD/hora | Solo cuando se requiere intervención |

---

## Resumen Económico

### Inversión inicial (desarrollo)

| Milestone | Precio |
|-----------|--------|
| **M1 — LumatAgent** (3 opciones) | |
| &nbsp;&nbsp;Opción A — Chatbot | **$4,000 – $4,400** |
| &nbsp;&nbsp;Opción B — Multi-Agente + WhatsApp | **$6,000 – $6,800** |
| &nbsp;&nbsp;Opción C — LumatAgent Completo | **$9,000 – $10,000** |
| **M2 — Página web** | **$ —** |
| **M3 — Agenda/Pagos** | **$ —** |

### Costo mensual de operación

| Concepto | Monto |
|----------|-------|
| Operación base (infra + APIs) | ~$22–59 USD/mes |
| Soporte (opcional) | ~$50–100 USD/mes |
| **Total con soporte** | **~$72–159 USD/mes** |

### Costos variables

| Concepto | Costo unitario |
|----------|----------------|
| Conversación adicional (OpenAI) | ~$0.001 – $0.003 |
| Template WhatsApp fuera de 24h | ~$0.04 – $0.08 |
| Almacenamiento extra VPS | ~$3/mes cada 100GB |

---

## Propiedad y Continuidad

| Aspecto | Condición |
|---------|-----------|
| **Código fuente** | 100% propiedad de Lumat. Se entrega repositorio completo. |
| **Base de datos** | Propiedad de Lumat. Acceso administrativo total. |
| **Dominio** | A nombre de Lumat, pagado por Lumat. |
| **Número WhatsApp** | A nombre de Lumat. |
| **Cuentas** | OpenAI, Meta, Google, VPS — a nombre de Lumat. Nosotros configuramos. |
| **Migración** | Otro programador puede continuar el proyecto. Se entrega documentación técnica + infraestructura documentada. |
| **Cese de pago** | Si se deja de pagar el servidor, el sistema deja de operar. Los datos no se pierden (hay backups). Las cuentas de API se suspenden. El código sigue siendo propiedad de Lumat. |
| **Respaldo** | Backups automáticos diarios + procedure de recuperación documentado. |
| **Protección de datos** | Datos personales en PostgreSQL en servidor propio (Chile o Alemania según Hetzner). Conexiones HTTPS. Acceso por roles. |

---

## Términos y Condiciones Generales

### Forma de pago sugerida

- **30% al inicio** de cada milestone
- **40% a mitad** del milestone (entregable parcial)
- **30% contra entrega y aceptación**

### Plazos

- Los plazos comienzan desde la firma + recepción del primer pago
- Se corre el plazo si el cliente no entrega contenidos, aprobaciones o respuestas en máximo 5 días hábiles

### Garantía

- 60 días corridos desde la aceptación de cada milestone
- Cubre: errores de funcionamiento, bugs, desviaciones del alcance acordado
- No cubre: cambios de alcance, contenido nuevo, modificaciones no acordadas, problemas por intervención de terceros, caídas de servicios externos
- Tiempo de respuesta: críticos ≤24h hábiles / menores ≤72h hábiles

### Exclusiones generales

Ver lista completa de 14 exclusiones en `estimacion-costos.md` → Exclusiones.

---

## Documentos Relacionados

- `LumatRequest.md` — requerimiento original del cliente
- `estimacion-costos.md` — desglose detallado de horas, costos, plazos
- `preguntas-cliente.md` — preguntas pendientes de resolver con Lumat
- `flujo-bot.md` — flujo conversacional del bot

---

> **Estado:** BORRADOR — Revisar personalmente antes de enviar al cliente.
> **Próximo paso:** Definir valores de M2 y M3, ajustar según feedback de Lumat, y preparar presentación formal al cliente.
