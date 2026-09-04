# Capacidades del agente Lumat — inventario actual y comparativa por hito

> Estado: relevamiento a 2026-09-04 · Rama `main` (HEAD `f3859d07`) · Suite de verificación: 22/22 requisitos y 41/41 escenarios H4 verificados (ver `openspec/changes/archive/2026-09-03-hito-4-automations-chat-pwa/verify-report.md`).
> Propósito: inventario de referencia para (re)construir el frontend del panel sobre las capacidades reales del agente.

---

## 1. Resumen ejecutivo

Lumat es un asistente de inteligencia artificial por WhatsApp para una empresa chilena de gasfitería y calefacción. El sistema completo incluye:

- **Bot conversacional** que atiende clientes reales: captura datos, clasifica solicitudes, responde desde una base de conocimientos experta, detecta emergencias, deriva a humano y registra todo.
- **Panel de administración** (doble superficie: Jinja HTML + SPA React) para que un equipo operativo monitoree demanda, tome conversaciones, administre clientes/casos/KB, agende visitas y controle reglas, costos y automatizaciones.
- **Plataforma operativa** (H4): outbox de eventos, worker acotado, reglas de automatización, centro de notificaciones, push del navegador, chat interno con el agente, dashboards operacionales y PWA instalable.

Los cuatro hitos del contrato están **implementados y verificados** (H1 activo/completo, H2/H3/H4 archivados). Los gaps restantes son de **despliegue externo** (credenciales reales de Meta, DNS/VPS, TLS real, SMTP real), no de código.

---

## 2. Capacidades actuales del agente (estado H4)

### 2.1 Atención al cliente por WhatsApp

| Capacidad | Detalle | Evidencia |
|---|---|---|
| Ingreso de mensajes | Webhook Meta con verificación HMAC, deduplicación por WAMID, tolerancia a retry-storms, persistir-antes-de-procesar, descarga de media, recuperación ante crash | `app/webhook/` |
| Motor conversacional | Flujo LangGraph determinista: menú de 8 categorías, captura progresiva de datos, clasificación de intención, enrutamiento, respuesta con base en KB, resumen | `app/chat/graph.py` |
| Captura de cliente | Ficha, normalización/dedup de teléfono, estados de ciclo de vida, notas, historial, consentimiento | `app/services/customers.py` |
| Orientación inicial | Respuesta fundamentada en la KB antes de decidir derivación | `app/chat/nodes/respond.py` |
| Detección de emergencias | Gate determinista antes del LLM; instrucciones de seguridad, alerta a dueño/técnico, pase a humano | `app/chat/nodes/emergency*.py` |
| Derivación a humano | Bundles de derivación con historial + resumen; estados `bot`/`human`/`closed`; continúa registrando inbound | `app/services/cases.py` |
| Defensa anti-inyección | Detección de prompt injection con rechazo/escalada antes de ejecutar tools | `app/chat/nodes/classify_intent.py` |
| Límites de costo | Límite por conversación y diario, modo conservador, bloqueo duro, alertas al dueño | `app/services/costs.py` |

### 2.2 Memoria persistente del cliente

- Memorias tipadas por cliente con embeddings, búsqueda híbrida vectorial/FTS, pin/estado/revisión.
- Observaciones automáticas (recurrencia, no-respuesta, riesgo, oportunidad) y memo de cierre de conversación.
- Evidencia: `app/services/memory.py`, `app/models.py` (`Memory`, `MemoryObservation`).

### 2.3 Base de conocimientos (KB)

- Ingesta de PDF/Markdown/TXT/CSV, chunking, embeddings locales 384d, recuperación semántica.
- Versionado, edición, deshabilitar/restaurar, métricas de costo por documento.
- Evidencia: `app/services/kb.py`, `app/panel/api/routes/kb.py`.

### 2.4 Emergencias

- Detección determinista por keywords configurables + instrucciones de seguridad editables.
- Alerta inmediata por WhatsApp (template) con fallback email, acuse de recibo y recordatorios.
- En H3 se elevó a entrega durable no bloqueante con reintento visible.
- Evidencia: `app/services/notify.py`, settings `emergency.*`.

### 2.5 Bandeja humana / conversaciones (H2)

- Inbox con filtros (estado, asignado, ventana), lista y thread con mensajes cronológicos.
- Comandos `tomar` / `devolver` / `cerrar` con validación de asignación y concurrencia segura.
- Respuesta del operador por WhatsApp solo en estado `human`; retry explícito; estados pending/sent/failed.
- Política de ventana de 24 h impuesta por backend; sin reapertura no autorizada.
- Evidencia: `app/services/conversations.py`, `app/panel/api/routes/conversations.py`.

### 2.6 Casos

- Casos con servicio, prioridad, estado, responsable, emergencia con acuse (`Reconocer emergencia`).
- Orden: emergencias y no-acusados primero.
- Evidencia: `app/panel/api/routes/cases.py`.

### 2.7 Agenda y calendario (H3)

- Citas locales: cliente/caso/técnico, duración fija, validación de timezone/DST, cancelación y re-agenda con historial.
- Disponibilidad de técnicos con prevención atómica de conflictos.
- Sincronización ICS no autoritativa: UID estable, idempotencia, cancelación/export con zona horaria, estado de falla visible y reconciliación.
- Evidencia: `app/services/scheduling.py`, `app/services/calendar.py`, `app/panel/api/routes/appointments.py`.

### 2.8 Notificaciones y plantillas (H3)

- Operaciones de notificación durables y atribuibles: contenido renderizado, canal, fuente, intentos, límites de retry, agotamiento auditable.
- Plantillas inmutables versionadas con variables, locale, estado de aprobación y política por canal (WhatsApp/SMTP).
- Evidencia: `app/services/notifications.py`, `app/services/templates.py`, `app/models.py` (`NotificationOperation`, `NotificationTemplateVersion`).

### 2.9 Plataforma de automatización (H4)

- **Outbox de eventos**: eventos durables de transiciones de mensaje/caso/cita, identidad estable, deduplicación y vínculo con operaciones de notificación.
- **Worker acotado**: leases, recuperación de leases expirados, procesamiento repeat-safe, estados de retry, health counts.
- **Reglas de automatización**: reglas deterministas evaluadas antes del LLM, condiciones, enqueue de notificación validado por política, cooldowns, claves de ejecución estables, reutilización de retry, deshabilitación y auditoría.
- Evidencia: `app/services/events.py`, `app/services/automation.py`, `app/ops/worker.py`.

### 2.10 Centro de notificaciones + push (H4)

- Centro de notificaciones por usuario: filtros (no leídas), orden newest-first, estado de lectura independiente.
- Push del navegador con manejo explícito de permiso, auditoría y fallback a WhatsApp/SMTP.
- Evidencia: `app/panel/api/routes/notifications.py`, `app/models.py` (`PanelNotification`, `PushSubscription`).

### 2.11 Chat interno con el agente (H4)

- Threads internos persistidos, solo admin/owner, mensajes auditados.
- Usa el mismo modelo/grafo acotado; **sin tools y sin datos de cliente** (frontera explícita); rechazo de acciones privilegiadas.
- Evidencia: `app/services/agent_chat.py`, `app/chat/graph.py`, `app/panel/api/routes/chat.py`.

### 2.12 Dashboards operacionales (H4)

- KPIs de ventana configurable (`/panel/api/kpis`): contactos, derivados, solicitudes de visita, motivos.
- Resumen operacional por período (contactos/casos/citas/salud de notificaciones/outcomes de automatización), tendencia diaria con buckets cero y drill-down por métrica.
- Evidencia: `app/services/dashboard.py`, `app/panel/api/routes/advanced_dashboard.py`.

### 2.13 Roles y permisos

| Rol | Puede | No puede |
|---|---|---|
| `operador` | Dashboard, clientes, conversaciones, casos, citas, plantillas, notificaciones, push, retry, export CSV | KB, settings, chat interno |
| `admin` | Todo lo del operador + KB, settings y chat interno | — |

- La SPA oculta nav de admin al operador; el backend es la autoridad real (`require_admin_json`).

### 2.14 Panel — superficie React (SPA)

Vistas cableadas en `AppShell`/`PanelShell` (estado actual en `main`):

1. `dashboard` — Dashboard (KPIs + ranking de motivos, rediseñado 2026-09-04)
2. `clients` — lista/búsqueda + ficha de cliente (historial, notas, memorias)
3. `conversations` — inbox + thread con controles de estado/retry/composer
4. `cases` — casos con emergencias y acuse
5. `notifications` — centro de notificaciones
6. `push` — configuración de notificaciones push del navegador
7. `chat` — Asistente Lumat (chat interno, admin)
8. `kb` — Base de conocimientos (admin)
9. `settings` — Configuración (admin)

Además: `AdvancedDashboard.tsx` (componente creado en H4, **no montado** en el flujo actual), Login/sesión, PWA instalable.

### 2.15 PWA

- Manifest con iconos, registro de service worker, caché de shell estático versionado; API explícitamente no cacheadas.
- Alcance actual: instalable + shell offline estático. **No** hay push offline ni sincronización offline de API.

### 2.16 Infraestructura y seguridad

- Hardening documentado y ejecutado (rehearsal VM): firewall, SSH key-only + fail2ban, usuario no-root, TLS, contenedor read-only, secrets solo por entorno.
- Autenticación de panel con bcrypt, conteo de fallos, lockout, sesiones firmadas, auditoría append-only.
- Evidencia: `docs/hardening.md`, `docs/ops.md`, `app/services/audit.py`.

---

## 3. Comparativa por hito (planificado vs actual)

### Hito 1 — Setup + WhatsApp operativo

**Planificado** (de `openspec/changes/hito-1-setup-whatsapp/`):
- Servidor seguro + bot WhatsApp con clientes reales (ingesta firmada, dedup, persistir-antes-de-procesar).
- Flujo de 8 categorías con captura progresiva, clasificación, orientación por KB, resúmenes.
- Fichas de cliente, KB semántica, emergencias deterministas, derivación humana.
- Panel mínimo, roles admin/operador, settings configurables, hardening, auditoría.

**Estado actual**: ✅ todo implementado y verificado. ⚠️ Pendientes de **despliegue externo** (no código): credenciales reales de Meta, DNS/VPS, Let's Encrypt real, SMTP real, go-live.

### Hito 2 — Bandeja humana de producción

**Planificado**: inbox autenticado con estados/asignación, comandos take/return/close con concurrencia segura, respuestas del operador atribuibles, ventana de 24 h, UI de panel.

**Estado actual**: ✅ 10/10 requisitos, 19/19 escenarios. ⚠️ Sin gaps de implementación (solo advertencias de proceso: `act(...)` warnings, evidencia histórica de PRs).

### Hito 3 — Agendamiento + notificaciones

**Planificado**: citas locales con disponibilidad/conflictos, calendario ICS no autoritativo, notificaciones durables, plantillas versionadas, emergencias con entrega durable.

**Estado actual**: ✅ 12/12 requisitos, 22/22 escenarios. ⚠️ No-goals explícitos: Google Calendar como fuente de verdad, disponibilidad recurrente libre, pagos, PWA, chat interno, event-bus H4 (pasaron a H4 o quedaron fuera).

### Hito 4 — Automatizaciones + chat + PWA

**Planificado**: outbox de eventos, worker, reglas de automatización, centro de notificaciones, push con fallback, chat interno, dashboards operacionales, PWA.

**Estado actual**: ✅ 22/22 requisitos, 41/41 escenarios (con remediación de hallazgos críticos previos). No-goals: edición offline, push universal, código autorado por el dueño, brokers/engines externos, reimplementación de inbox H2, alcance M2/M3.

### Cambios intermedios que aportaron producto real

| Cambio | Aporte |
|---|---|
| `memoria-persistente-lumat` | Memorias de cliente + UI en ficha |
| `config-agente-lumat` | Config declarativa de agente (prompts/skills externalizados) |
| `h2-router-langgraph` | Enrutamiento supervisor + sub-agente de investigación KB |
| `panel-adoption` | Adopción del SPA React con datos reales |
| `design-system-*` / `storybook-redesign` / `v1-shell-*` / `corp-components-port` | Sistema de diseño del panel (tokens, shell, primitives) |
| `dashboard-cleanup` | Limpieza de dashboard y aserciones de mock |

---

## 4. Brechas relevantes para reconstruir el frontend

> Detectadas en el relevamiento; ninguna bloquea el rediseño, pero conviene decidir explícitamente.

1. **`AdvancedDashboard` sin montar**: el componente React existe (H4) pero no está en el flujo de vistas; sus endpoints (`/panel/api/dashboard/summary|trend|drilldown`) sí existen y están verificados. Decidir si entra al panel (y cómo) en el rediseño.
2. **Superficie Jinja + React en paralelo**: el panel sirve rutas HTML Jinja (`app/panel/routes/*`) y la SPA React (`web/`). El DESIGN_SYSTEM exige migrar por flujo y no mantener dos vocabularios. Definir qué superficie es la canónica del rediseño.
3. **Memorias en ficha**: gestión de memoria (upsert/delete/mark) existe vía API y UI; confirmar si el rediseño la expone igual de profunda.
4. **PWA**: instalable y shell offline estático; **no** hay push offline ni sync offline. No prometer offline-first en la UI.
5. **Settings**: los grupos son scope, keywords de emergencia, tone, límites, Meta cost — todos con API propia. El rediseño debe cubrir los cinco + spend snapshot.
6. **Roles**: ocultar nav admin al operador es solo la capa UI; el backend ya es autoritativo. Mantener esa separación visible en el rediseño (no renderizar controles de admin al operador).

---

## 5. Mapa capacidades ↔ vistas del panel (guía de reconstrucción)

| Capacidad de negocio | Vista/área del panel | Datos |
|---|---|---|
| Monitoreo de demanda | Dashboard | `/panel/api/kpis` + `dashboard/summary\|trend\|drilldown` |
| Clientes | Clientes (lista) + Ficha | `/panel/api/clients*` + memories |
| Conversaciones / bandeja humana | Conversaciones (inbox + thread) | `/panel/api/conversations*` |
| Emergencias y casos | Casos | `/panel/api/cases*` |
| Agenda | Citas (en ficha + acciones) | `/panel/api/appointments*`, `availability` |
| Conocimiento | Base de conocimientos | `/panel/api/kb*` |
| Reglas del agente | Configuración | `/panel/api/settings/*` |
| Notificaciones | Centro de notificaciones | `/panel/api/notifications*` |
| Push | Notificaciones push | `/panel/api/push-subscription*` |
| Asistencia al dueño | Asistente Lumat | `/panel/api/chat/threads*` |
| Exportación | CSV | `/panel/export/*.csv` |

---

## 6. Fuentes

- Código backend: `app/` (routes, services, chat, webhook, ops, models).
- Código frontend: `web/src/` (components/pages, api.ts, types.ts, pwa.ts).
- OpenSpec por hito: `openspec/changes/hito-1-setup-whatsapp/`, `openspec/changes/archive/2026-08-31-hito-2-complete/`, `.../2026-09-03-hito-3-scheduling-notifications/`, `.../2026-09-03-hito-4-automations-chat-pwa/`.
- Docs: `README.md`, `docs/ops.md`, `docs/hardening.md`, `web/DESIGN_SYSTEM.md`, `LumatRequest.md`.
- Grafo de conocimiento: `graphify-out/GRAPH_REPORT.md` (3.750 nodos; dioses: Message, Conversation, Customer, User, Case, AuditLog).
