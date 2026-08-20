# Roadmap M1 — LumatAgent

> Chatbot → LumatAgent Completo
> HandCodeStudio — Stefan Miranda
> Julio 2026

---

## Resumen Ejecutivo

| Concepto | Detalle |
|----------|---------|
| **Alcance** | M1 — Sistema Multi-Agente (LumatAgent) |
| **Partida** | Chatbot WhatsApp conversacional **experto en gasfitería** |
| **Evolución** | Arquitectura multi-agente → Calendar → Automatizaciones |
| **Entrega final** | LumatAgent completo con 5 sub-agentes |
| **Plazo total** | ~14 semanas (3.5 meses) |
| **Inversión** | $2,300 – $3,000 USD |
| **Pilares** | Base de conocimiento experta desde el día 1 + Seguridad (servidor + prompt injection) |

---

## Timeline General

```text
MES 1                MES 2                MES 3                MES 4
──────────────────┬────────────────────┬────────────────────┬──────────────────
                  │                    │                    │
██ Fase 0-1 ██████│██ Fase 2 ██████████│██ Fase 3 ██████████│██ Fase 4 ████████
██ Setup+Bot █████│██ Multi-Agente ████│██ Calendar+Notif ██│██ Auto+Report ███
                  │                    │                    │
◉ Hito 1          │◉ Hito 2            │◉ Hito 3            │◉ Hito 4
Bot operativo     │Arquitectura lista  │Agenda automática   │LumatAgent 100%
en WhatsApp       │p/conectar web      │sin gestión humana  │completamente
                  │                    │                    │autónomo
```

---

## Fase 0 — Setup (Semana 1)

### Actividades

| # | Actividad | Detalle |
|---|-----------|---------|
| 0.1 | Aprovisionamiento VPS | Hetzner CX21/CX31 — SO, Docker, seguridad base |
| 0.2 | Base de datos | PostgreSQL + pgvector + migraciones iniciales |
| 0.3 | Estructura del proyecto | FastAPI + LangGraph skeleton + repositorio |
| 0.4 | Autenticación | JWT + roles (dueño, admin, técnico) |
| 0.5 | CI/CD | Deploy automatizado + Docker Compose |
| 0.6 | Panel admin base | Login + layout + navegación |
| 0.7 | **Seguridad del servidor** | Firewall (solo puertos necesarios), SSH por llave, fail2ban, contenedor sin `--privileged`, secretos en variables de entorno (nunca en el repo), backups automáticos |

### Seguridad del servidor (desde el día 1)

- **Red**: firewall solo con puertos 80/443 y SSH. Todo lo demás cerrado.
- **Contenedor**: Docker **sin `--privileged`**, filesystem read-only para el agente.
- **Secrets**: API keys de Meta/OpenAI/Google en variables de entorno del servidor, nunca en código ni en el repo.
- **Accesos**: SSH solo por llave, sin password. Monitoreo de intentos fallidos.
- **Backups**: automáticos diarios de PostgreSQL a volumen externo.
- **HTTPS**: TLS obligatorio en todas las comunicaciones.

### Entregable

> **Servidor seguro y listo, DB operativa, panel admin con login funcionando.**
> El proyecto está preparado para recibir código de todas las fases siguientes.

---

## Fase 1 — Chatbot WhatsApp (Semanas 2-5)

### Actividades

| # | Actividad | Horas |
|---|-----------|-------|
| 1.1 | State machine conversacional (LangGraph) | 25h |
| 1.2 | Integración WhatsApp Cloud API (Meta) | 20h |
| 1.3 | Pipeline RAG (embeddings + pgvector + KB) | 18h |
| 1.4 | **Base de conocimiento experta en gasfitería** (fuentes externas desde el inicio) | 20h |
| 1.5 | **Sistema de límites de alcance del agente** (boundaries configurables por el dueño) | 8h |
| 1.6 | **Mitigación de prompt injection en el canal WhatsApp** | 10h |
| 1.7 | Detección de emergencias + protocolo + notificaciones | 10h |
| 1.8 | Derivación a humano con historial + resumen | 6h |
| 1.9 | Subida y validación de archivos (fotos, audio) | 6h |
| 1.10 | CRUD de base de conocimiento + gestor | 10h |
| 1.11 | Panel admin: clientes, conversaciones, casos | 22h |
| 1.12 | Dashboard básico + exportación CSV/Excel | 8h |
| 1.13 | Tests de integración + funcionales + **tests de prompt injection** | 16h |

### Base de conocimiento experta (desde el día 1)

El agente de WhatsApp debe ser **un experto en gasfitería desde la primera conversación** — no un bot genérico. Para eso:

- **Fuentes externas cargadas desde el inicio**: manuales de fabricantes (calefonts, calderas), procedimientos de Lumat, tarifarios, FAQ, guías de troubleshooting, códigos de error.
- **Formatos soportados**: PDF, texto, páginas web, hojas de cálculo → se procesan y cargan en pgvector para búsqueda semántica.
- **Capacidad de guiar**: el agente puede ayudar a un cliente a diagnosticar un problema simple ("¿el piloto se apagó?", "¿sale agua fría?") con pasos seguros de verificación.
- **Siempre dentro de los límites del dueño**: si la consulta excede lo configurado (por ejemplo, algo que requiere diagnóstico en terreno), el agente deriva a humano. **Nunca sugiere acciones peligrosas o fuera de su alcance.**
- El dueño/admin define qué temas puede resolver el agente solo y cuáles derivar siempre.

### Seguridad del canal WhatsApp (prompt injection)

El bot tiene **contacto directo con clientes desconocidos** — cualquiera puede escribirle. Eso lo hace vulnerable a prompt injection:

- **Aislamiento de instrucciones**: el system prompt del agente está separado de cualquier contenido del usuario. Los mensajes del cliente se tratan como **datos**, nunca como instrucciones.
- **Validación de entrada**: se detectan y neutralizan intentos de inyección ("ignorá tus instrucciones", "actuá como si fueras...", comandos embebidos en el texto).
- **Whitelist de tools**: el agente solo puede llamar las tools permitidas para su rol. Un cliente de WhatsApp **no puede** ejecutar acciones de admin.
- **Nunca revelar datos sensibles**: regla hardcodeada — el agente no revela datos de otros clientes, contraseñas, configuraciones internas ni llaves.
- **Escalamiento controlado**: ante consultas fuera de alcance o intentos de manipulación → derivar a humano, nunca ejecutar.
- **Auditoría**: toda conversación y toda llamada a tool queda en `audit_log`.

### Flujo del bot (para mostrar al cliente)

```text
Cliente escribe a WhatsApp
        │
        ▼
WhatsApp Cloud API → Webhook → API Gateway
        │
        ▼
Validación de entrada (anti prompt injection)
        │
        ▼
Orquestador recibe → Clasifica intención
        │
        ├── ¿Emergencia? → Protocolo → Notifica dueño/técnico
        ├── ¿Cliente nuevo? → Crea ficha en DB
        ├── ¿Cliente existente? → Busca historial
        ├── ¿Agendar? → Calendar Agent check disponibilidad
        ├── ¿Pregunta? → Base de conocimiento experta + RAG
        │       └── ¿Dentro de límites? → Responde y guía
        │       └── ¿Fuera de límites? → Deriva a humano
        └── ¿Derivar? → Resumen → Notifica a humano
```

### Entregable

> **Bot experto en gasfitería conversando por WhatsApp con clientes reales.**
> Base de conocimiento de Lumat cargada. Límites de alcance configurados.
> Protegido contra prompt injection. Panel administrativo operativo.

### 🟢 Hito 1 — Bot operativo

> "Los clientes de Lumat ya pueden pedir presupuestos, consultar servicios,
> agendar visitas y recibir atención por WhatsApp — automatizado."

---

## Fase 2 — Arquitectura Multi-Agente (Semanas 6-8)

### Actividades

| # | Actividad | Horas |
|---|-----------|-------|
| 2.1 | Orquestador LangGraph supervisor | 20h |
| 2.2 | Router de sub-agentes + ciclo de vida + estado compartido | 10h |
| 2.3 | Tools layer (whitelist + validación + binding de permisos) | 15h |
| 2.4 | Sistema de roles completo (dueño, admin, técnico, cliente) | 10h |
| 2.5 | Sistema de auditoría (audit_log + consulta por rol) | 10h |
| 2.6 | **Aislamiento entre sub-agentes** (un agente comprometido no arrastra al resto) | 8h |
| 2.7 | Scaffold Calendar Agent (schema + estructura) | 10h |
| 2.8 | Scaffold Automation Agent (schema + estructura) | 10h |
| 2.9 | Scaffold Notification Agent | 5h |
| 2.10 | Scaffold Report Agent | 5h |
| 2.11 | Worker de automatizaciones (scaffold) | 10h |
| 2.12 | Tests multi-agente (routing, permisos, aislamiento, **prompt injection entre agentes**) | 17h |
| 2.13 | **Bandeja humana (reply-from-panel)** — estado por conversación (bot/human/closed) + assignee + endpoints de envío por el MISMO número vía Cloud API + wiring del inbox del panel | 18h |

### Seguridad multi-agente

- **Boundaries por rol**: cada sub-agente hereda los permisos del rol que lo invocó. Un cliente (WhatsApp) no puede pedirle al orquestador acciones de admin.
- **Estado compartido controlado**: los sub-agentes comparten contexto solo cuando el orquestador lo decide — nunca acceso libre a datos sensibles.
- **Aislamiento de contexto**: si un sub-agente recibe un prompt inyectado, no puede contaminar el contexto de los demás.

### Arquitectura (para mostrar al cliente)

```text
LumatAgent Core
┌────────────────────────────────────────────┐
│             Orquestador                     │
│           (LangGraph)                       │
│                │                            │
│     ┌──────────┴──────────┐                 │
│     │   Router de          │                 │
│     │   sub-agentes        │                 │
│     └──┬──┬──┬──┬──┬──────┘                 │
│        │  │  │  │  │                        │
│  ┌─────┘  │  │  │  └──────┐                 │
│  │   ┌────┘  │  └────┐    │                 │
│  ▼   ▼       ▼       ▼    ▼                 │
│ WA   CA      AA      NA   RA                │
│                                              │
│ ┌──────────────────────────────────────────┐ │
│ │ Tools Layer (whitelist + validación)      │ │
│ └──────────────────────────────────────────┘ │
│                                              │
│ ┌──────────────────────────────────────────┐ │
│ │ PostgreSQL + pgvector + File Storage      │ │
│ └──────────────────────────────────────────┘ │
└────────────────────────────────────────────┘

Sub-agentes:
  WA — WhatsApp Agent
  CA — Calendar Agent
  AA — Automation Agent
  NA — Notification Agent
  RA — Report Agent
```

### Entregable

> **Arquitectura multi-agente operativa.**
> El chatbot ahora es un sub-agente del orquestador.
> La bandeja humana del panel opera (reply-from-panel): hilos derivados con estado/assignee y respuestas por el mismo número.
> La plataforma está lista para agregar capacidades sin reescribir nada.

### 🟡 Hito 2 — Arquitectura lista

> "La arquitectura del LumatAgent está completa. Ahora se pueden agregar
> Calendar, Automation, Notification y Report Agents sin tocar el código
> existente. La web externa también puede conectarse vía API."

---

## Fase 3 — Calendar + Notificaciones (Semanas 9-11)

### Actividades

| # | Actividad | Horas |
|---|-----------|-------|
| 3.1 | **Calendario propio en PostgreSQL** (fuente de verdad: visitas, disponibilidad, bloqueos, reglas) | 15h |
| 3.2 | **Exportación ICS read-only** (los técnicos ven sus visitas en el calendario de su iPhone/Google sin poder modificarlas) | 8h |
| 3.3 | Calendar Agent — disponibilidad + agendamiento (WhatsApp + panel) | 20h |
| 3.4 | Calendar Agent — reprogramación + bloqueo manual | 10h |
| 3.5 | **4 canales de entrada de visitas** (WhatsApp cliente, panel dueño/admin, panel técnico, carga manual) | 8h |
| 3.6 | Notification Agent — recordatorios programados | 10h |
| 3.7 | Notification Agent — seguimientos post-servicio | 5h |
| 3.8 | Notification Agent — cola de notificaciones + templates | 5h |
| 3.9 | Panel — vista de agenda + asignación visual de técnicos | 15h |
| 3.10 | Tests de integración (calendario + notificaciones) | 10h |

### Decisión de arquitectura: calendario propio + exportación read-only

El LumatAgent usa **su propia base de datos como única fuente de verdad** para visitas y disponibilidad. El calendario externo (iPhone/Google) es solo una **vista de solo lectura**:

```
LumatAgent (PostgreSQL)  ←  fuente de verdad
        │
        ├── Exportación ICS / CalDAV (read-only)
        │       → Los técnicos VEN sus visitas en su
        │         calendario (iPhone/Google) sin poder
        │         modificarlas desde ahí
        │
        └── Notificaciones WhatsApp (canal principal)
                → Recordatorios, confirmaciones, avisos
```

**¿Por qué no sincronizar bidireccionalmente con iPhone/Google Calendar?**
- La sincronización bidireccional es un proyecto en sí mismo: conflictos, duplicados, loops, latencia.
- Apple NO tiene API pública de calendario (solo CalDAV frágil). Google tiene OAuth, rate limits y latencia.
- Con fuente de verdad propia: las reglas de negocio (zonas, técnicos, horarios) viven en la DB, la auditoría es trazable, y el sistema no depende de terceros.

**¿Cómo llega el read-only al técnico?** El servidor genera un archivo ICS por técnico (`https://agente.lumat.cl/calendario/tecnico-juan.ics`). El técnico se suscribe a esa URL desde su iPhone/Google Calendar y ve sus visitas actualizadas cada 15-30 min. Es unidireccional por diseño: el técnico solo mira; cualquier cambio se hace por WhatsApp o el panel.

### ¿Quién crea visitas? (canales de entrada)

| Canal | Quién | Cómo |
|-------|-------|------|
| WhatsApp | Cliente | "Necesito revisión de mi calefont" → agendamiento automático |
| Panel web | Dueño/Admin | Escribe la visita o se la pide al agente por chat |
| Panel web | Técnico | Reprograma, cancela, marca completada |
| Teléfono | Admin (manual) | Cliente llama → la secretaria crea la visita en el panel |

Todas las entradas escriben en la misma tabla `visits` y respetan las mismas reglas de disponibilidad.

### Entregable

> **El LumatAgent agenda visitas solo.**
> Fuente de verdad propia + exportación ICS read-only para los técnicos.
> Recordatorios automáticos. Sin intervención humana para la gestión de agenda.

### 🔵 Hito 3 — Agenda automática

> "Un cliente pide hora por WhatsApp. El agente revisa disponibilidad
> en el calendario del técnico, agenda la visita, y envía recordatorio
> 24h antes — todo automático."

---

## Fase 4 — Automatizaciones + Reportes (Semanas 12-14)

### Actividades

| # | Actividad | Horas |
|---|-----------|-------|
| 4.1 | **Event bus** (eventos del sistema: visita_creada, servicio_completo, cliente_nuevo...) | 8h |
| 4.2 | Automation Agent — `create_automation()` vía lenguaje natural | 15h |
| 4.3 | Automation Agent — validación de triggers/acciones | 10h |
| 4.4 | Automation Agent — confirmación al dueño antes de crear | 5h |
| 4.5 | **Worker ejecutor determinístico** (no-LLM, corre siempre) | 12h |
| 4.6 | Report Agent — KPIs + resumen semanal | 10h |
| 4.7 | Report Agent — exportación avanzada | 8h |
| 4.8 | Panel — automatizaciones (ver, editar, activar/desactivar) | 18h |
| 4.9 | **Panel — módulo de chat con el agente** (dueño/admin conversan con LumatAgent) | 12h |
| 4.10 | **Panel como PWA** (instalable en home, notificaciones push, experiencia app móvil) | 12h |
| 4.11 | **Centro de notificaciones del panel** (inbox, filtros, leídas, historial) | 10h |
| 4.12 | Dashboard avanzado + reportes gráficos | 10h |
| 4.13 | Buffer general + tests finales | 20h |
| 4.14 | Documentación + manual de uso + capacitación remota | 10h |

### Arquitectura de automatizaciones

```
┌─────────────────────────────────────────────────────────────┐
│              ARQUITECTURA DE AUTOMATIZACIONES                │
│                                                             │
│  EVENTOS DEL SISTEMA (event bus)                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  visita_creada | visita_cancelada | servicio_completo │  │
│  │  cliente_nuevo | mensaje_recibido | pago_registrado   │  │
│  └─────────────────────────────────────────────────────┘   │
│                        │                                   │
│                        ▼                                   │
│  TABLA: automations (configuración, NO código)              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  id | trigger          | condition | action   | params│  │
│  │  1  | servicio_complet | —         | send_whats| plant.│  │
│  │  2  | lunes_9am (cron) | —         | send_email| report│  │
│  │  3  | visita_creada    | zona=Ñuñoa| notify   | Juan   │  │
│  └─────────────────────────────────────────────────────┘   │
│                        │                                   │
│                        ▼                                   │
│  WORKER (proceso aparte, determinístico, NO usa LLM)        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Trigger scanner (eventos) + Trigger cron (tiempo)   │   │
│  │  → Matcher: ¿condición cumple?                       │   │
│  │  → Ejecutor: tools del tools layer                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                        │                                   │
│                        ▼                                   │
│  TODO registrado en audit_log                              │
└─────────────────────────────────────────────────────────────┘
```

**Regla de oro**: el agente **no escribe código**. Escribe configuraciones (trigger + condición + acción). El worker las ejecuta SIEMPRE, aunque el LLM esté caído. El LLM solo interviene al crear la regla desde lenguaje natural.

### Flujo de automatizaciones (para mostrar al cliente)

```text
Dueño dice: "Pasado 3 días de un servicio, enviá plantilla
de seguimiento preguntando cómo le fue."

                  │
                  ▼
1. LumatAgent entiende el requerimiento
2. Propone la automatización al dueño
   ┌────────────────────────────────────────────┐
   │ ¿Confirmás esta automatización?             │
   │                                             │
   │ Trigger: 3 días después de servicio         │
   │ Acción:  Enviar template seguimiento        │
   │                                            │
   │ [ Confirmar ]  [ Modificar ]  [ Cancelar ] │
   └────────────────────────────────────────────┘
3. Dueño confirma
4. Worker ejecuta automáticamente cuando corresponde
5. Report Agent registra y reporta ejecuciones
```

### Entregable

> **LumatAgent COMPLETO y autónomo.**
> Dueño crea automatizaciones hablando en lenguaje natural. El worker las ejecuta solo.
> Reportes automáticos semanales. Panel con chat con el agente.
> Cero intervención técnica diaria.

### 🟣 Hito 4 — LumatAgent 100% operativo

> "El LumatAgent trabaja solo. El dueño le dice 'cada vez que pase X,
> hace Y' y el agente lo ejecuta. Los reportes llegan solos.
> La operación diaria de Lumat está automatizada."

---

## Integraciones posibles (crecen con la arquitectura)

Una vez que existe el **event bus + tools layer**, agregar una integración nueva es plug-and-play:
**1 tool nueva = integración nueva disponible en todo el sistema** (chat, automatizaciones, panel).

| Integración | Fase | Qué permite |
|-------------|------|-------------|
| **WhatsApp Cloud API** | 1 | Canal principal de clientes |
| **Base de conocimiento externa** | 1 | Manuales, PDFs, web → el agente es experto en gasfitería |
| **Calendario propio + ICS read-only** | 3 | Visitas, disponibilidad, técnicos |
| **Email (SMTP/Resend)** | 3-4 | Reportes, notificaciones formales |
| **Google Calendar / CalDAV** | 3 | Ver disponibilidad externa de los técnicos |
| **Webpay/Transbank** | M3 | Pagos (el agente nunca ve datos de tarjeta) |
| **Web externa (API REST)** | M2/M3 | El agente "habla" con la página (lo definido con Lumat) |
| **Google Sheets/Drive** | Futuro | Exportar reportes a hojas que el equipo ya usa |
| **Slack/Teams** | Futuro | Alertas al equipo |
| **SMS** | Futuro | Respaldo cuando no hay WhatsApp |
| **Bases de conocimiento adicionales** | Futuro | Conectar FAQs, manuales, catálogos nuevos |

---

## Notificaciones para Dueño/Admin

El LumatAgent **informa proactivamente** — el dueño no tiene que mirar un panel todo el día.
El agente avisa cuando algo importa.

### Categorías

| # | Categoría | Eventos | Prioridad |
|---|-----------|---------|-----------|
| 1 | **Emergencias** | Cliente reporta emergencia, detección de riesgo | 🔴 Inmediata |
| 2 | **Operativas** | Visita agendada/cancelada/reprogramada, servicio completado, visita próxima | 🟠 Alta |
| 3 | **Clientes** | Cliente nuevo, sin respuesta, consulta sin resolver, interesado sin agenda | 🟡 Media |
| 4 | **Automatizaciones** | Ejecutada, fallida, creada, desactivada | 🟡 Media |
| 5 | **Reportes** | Resumen diario/semanal, alertas de KPI | 🔵 Programada |
| 6 | **Técnicos** | Atraso, sobrecarga de visitas, zona sin cobertura | 🟠 Alta |
| 7 | **Sistema** | Bot caído, API externa caída, backup fallido | 🔴 Inmediata |

### Canales según prioridad

```
┌─────────────────────────────────────────────────────────┐
│  URGENTE (emergencia, bot caído)                        │
│    → WhatsApp al dueño INMEDIATAMENTE                   │
│    → + notificación push en el panel (PWA)              │
│                                                         │
│  IMPORTANTE (visitas, clientes, automatizaciones)       │
│    → WhatsApp (resumen) + panel (detalle)               │
│                                                         │
│  INFORMATIVO (reportes, KPIs)                           │
│    → Email + panel (dashboard)                          │
└─────────────────────────────────────────────────────────┘
```

**El dueño decide el nivel**: en el panel configura qué recibe por WhatsApp, qué por email,
y qué solo en el panel. Ejemplo: "las emergencias SIEMPRE por WhatsApp, los reportes
semanales solo por email, los resúmenes diarios cuando le pregunto al agente".

### El panel como centro de notificaciones

```
┌────────────────────────────────────────────┐
│  PANEL WEB                                 │
│                                            │
│  🔔 Notificaciones (campanita)             │
│  ├── 📥 Inbox: TODAS las notificaciones    │
│  ├── 🔴 No leídas (badge rojo)             │
│  ├── Filtros: emergencias / visitas /      │
│  │   clientes / automatizaciones / sistema │
│  ├── Marcar leída / resuelta               │
│  └── Historial completo con auditoría      │
│                                            │
│  + Notificaciones push (PWA)               │
└────────────────────────────────────────────┘
```

**WhatsApp es el aviso rápido (voz del agente), el panel es el registro completo (memoria del sistema).**

### Notificaciones por WhatsApp — reglas de Meta

El agente puede escribirle al WhatsApp del dueño (es el mismo WhatsApp Cloud API), pero Meta
tiene reglas sobre mensajes salientes:

| Situación | Qué permite Meta |
|-----------|------------------|
| Dueño interactuó hace menos de 24h | **Ventana libre**: cualquier mensaje, sin plantilla, sin costo |
| Pasaron más de 24h | **Solo plantillas aprobadas** por Meta (costo ~$0.04-0.08/mensaje) |
| **Plantillas de utilidad** (recordatorios, alertas, resúmenes) | Se aprueban MUY rápido — a veces pre-aprobadas automáticamente |

**Patrón del "ping"**: el dueño le manda "hola" al bot (o el agente le recuerda por email)
→ se reabre la ventana de 24h gratis. Para notificaciones estructuradas, las plantillas son
en realidad el formato correcto: mensajes limpios con parámetros variables (nombre, hora,
dirección). Se preparan una vez, se aprueban, y el agente las usa siempre.

---

## Resumen de Fases

```text
Fase       Duración   Horas    Hito                         Inversión
─────────────────────────────────────────────────────────────────────
Fase 0     1 sem      20h     Setup seguro listo             ~$400
Fase 1     4 sem     189h     🟢 Bot experto operativo       ~$3,780
Fase 2     3 sem     148h     🟡 Arquitectura lista          ~$2,960
Fase 3     3 sem     106h     🔵 Agenda automática           ~$2,120
Fase 4     3 sem     160h     🟣 LumatAgent 100%             ~$3,200
─────────────────────────────────────────────────────────────────────
Total     14 sem     623h     Completo                      $2,300-3,000
```

> **Nota**: las horas estimadas (~623h) superan la tarifa de referencia ($20/h). La inversión
> al cliente se mantiene en el rango pactado **$2,300 – $3,000 USD** porque el desarrollo usa
> coding agents (AI-assisted) que multiplican la productividad — el costo real al cliente
> NO es horas × tarifa, es el valor del entregable. Las horas son referencia interna de esfuerzo.

---

## Panel web — Administración del agente

El panel es la **interfaz de gestión** del LumatAgent. No es una réplica de ChatGPT — es un
dashboard operativo con un módulo de chat integrado:

```
┌────────────────────────────────────────────────┐
│         PANEL WEB (dashboard operativo)         │
│                                                │
│  ┌────────────┬───────────────┬──────────────┐ │
│  │ Clientes   │  Agenda       │  Dashboard   │ │
│  │ (fichas,   │  (visitas,    │  (KPIs,      │ │
│  │ historial) │  técnicos)    │  reportes)   │ │
│  └────────────┴───────────────┴──────────────┘ │
│  ┌──────────────────────────────────────────┐  │
│  │  Automatizaciones (ver/crear/activar)    │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │  [ Chat con LumatAgent ]  ← complemento   │  │
│  │  "Mostrame los servicios de hoy"          │  │
│  │  "Creá una automatización..."             │  │
│  └──────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
```

| Vista | Rol | Qué hace |
|-------|-----|----------|
| Clientes | Dueño/Admin | Fichas, historial, estados |
| Agenda | Dueño/Admin/Técnico | Visitas, disponibilidad, asignación |
| Dashboard | Dueño/Admin | KPIs, reportes |
| Automatizaciones | Dueño | Crear, editar, activar/desactivar reglas |
| **Chat con el agente** | **Dueño/Admin** | **Conversar en lenguaje natural, crear automatizaciones, consultar el sistema** |

**¿Por qué panel + chat y no solo chat?** El panel es el caballo de batalla (datos editables,
dashboards, certeza visual). El chat es el complemento para lo que es más natural hablar
(crear automatizaciones, consultar el estado). Un chat puro estilo ChatGPT como pantalla
principal sería frágil para gestión operativa.

### El panel es un PWA (no app nativa)

El panel se desarrolla como **PWA (Progressive Web App)** — el dueño/admin lo instalan en el
home de su iPhone/Android y tienen la experiencia de app móvil **sin pagar desarrollo nativo**
ni pasar por la App Store:

| Capacidad | PWA |
|-----------|-----|
| 📱 "Instalar" en el home (iPhone/Android) | ✅ Ícono + pantalla completa, sin App Store |
| 🔔 Notificaciones push | ✅ (iOS 16.4+; Android perfecto) |
| 💾 Funcionar offline / caché | ✅ |
| 🗣️ Chat con el agente | ✅ Experiencia app de mensajería |
| 📊 Dashboard táctil | ✅ |
| Costo | $0 extra — se desarrolla una vez (web = PWA) |
| Actualizaciones | Automáticas, sin revisión de Apple/Google |

**Nota honesta (iOS)**: las notificaciones push del PWA en iPhone requieren instalar el PWA al
home y pueden tener ligeros retrasos en background. Para gestión es aceptable — y las alertas
críticas siguen yendo por WhatsApp, que no depende del push del PWA.

**Arquitectura de canales resultante**:
- **PWA en el celular** → experiencia app para gestionar y chatear
- **WhatsApp** → voz proactiva del agente (alertas, recordatorios)
- **Email** → reportes largos

---

## Atención humana — derivación y bandeja del panel

El número de WhatsApp es un **canal compartido**: tanto el bot como una persona responden por el mismo endpoint de Meta, con el mismo token del negocio. No existe "bot vs humano" en la API — **quién responde es estado de la aplicación, no de Meta**. El estado por conversación vive en PostgreSQL: `bot`, `human` o `closed`, más el `assignee` (usuario del panel que toma el hilo).

### Flujo de derivación

```text
Bot detecta: emergencia / fuera de límites / cliente pide humano / prompt injection
        │
        ▼
1. Envía aviso dentro de la ventana de 24h
2. Marca la conversación como human + asigna responsable
3. Notifica al humano (centro de notificaciones del panel)
        │
        ▼
El humano abre el hilo en la bandeja del panel y responde
        │
        ▼
Puede devolverle la conversación al bot al cerrar (closed → bot)
```

### Bandeja humana en el panel

```
┌────────────────────────────────────────────┐
│  BANDEJA HUMANA (inbox de conversaciones)  │
│                                            │
│  ├── Hilos con estado: bot / human / closed│
│  ├── Asignación de responsable (assignee)  │
│  ├── Aviso de ventana 24h: abierta/cerrada │
│  └── Historial completo de la conversación │
└────────────────────────────────────────────┘
```

El humano responde **desde el panel, por el MISMO número**: el panel llama al mismo endpoint `POST /{phone_number_id}/messages` con el mismo token → el cliente ve la respuesta desde el número de Lumat. Sin SIM extra, sin app, sin configuración adicional en Meta. El webhook sigue entregando todos los mensajes aunque atienda un humano → historial completo en el servidor.

### Reglas de Meta que aplican igual a humanos

- **Ventana 24h**: las respuestas dentro de la ventana abierta son texto libre, sin plantilla.
- **Fuera de la ventana**: solo plantilla aprobada (aplica igual a humanos).
- **No existe API de Meta para consultar si la ventana está abierta** → se trackea localmente con el último inbound por `wa_id`; el panel muestra "ventana abierta/cerrada".

### ⚠️ Nota de pricing

Los service messages (respuestas no-plantilla dentro de la ventana) están **GRATIS hasta el 1-oct-2026**; desde esa fecha Meta los cobra por mensaje entregado (Chile está en la lista de mercados habilitados). Las pruebas finales (~dic 2026) ya caen bajo este esquema. La FEP (ventana de 72h desde anuncios Click-to-WhatsApp) sigue sin cobro de delivery.

### Referencias cruzadas

La bandeja humana es la **actividad 2.13 (Fase 2 / Hito 2)** con horas propias. Complementa la **Fase 1 actividad 1.8** (derivación a humano con historial + resumen) y el **módulo de chat del panel (4.9)**.

---

## Seguridad — Resumen de la arquitectura

### Servidor (Fase 0)

| Capa | Medida |
|------|--------|
| Red | Firewall solo puertos 80/443/SSH |
| Contenedor | Docker sin `--privileged`, filesystem read-only para el agente |
| Secretos | Variables de entorno en el servidor, nunca en repo |
| Acceso | SSH por llave, fail2ban, sin password |
| Datos | Backups automáticos diarios, TLS obligatorio |

### Prompt injection (el canal WhatsApp es público)

El bot recibe mensajes de **cualquier persona desconocida** — es la superficie de ataque más
expuesta del sistema:

| Vector de ataque | Mitigación |
|------------------|------------|
| "Ignorá tus instrucciones / actuá como..." | System prompt aislado; el input del usuario es **dato**, nunca instrucción |
| Comandos embebidos en texto | Validación de entrada + neutralización de patrones de inyección |
| Pedir datos de otros clientes | Regla hardcodeada: el agente nunca revela datos ajenos |
| Escalar privilegios (pedir acciones de admin) | Whitelist de tools por rol — el cliente solo tiene tools de cliente |
| Contaminar el contexto de otros agentes | Aislamiento de contexto entre sub-agentes |
| Inducir acciones peligrosas | Límites de alcance configurables por el dueño; fuera de límite → deriva a humano |

### Protección de datos

- El agente nunca recibe datos de pago (van directo a Webpay/Transbank, M3)
- Conversaciones accesibles solo por rol (técnico no ve clientes ajenos)
- Auditoría completa en `audit_log` (quién, qué, cuándo)
- La automatización nunca ejecuta código arbitrario — solo configuraciones validadas

---

## Hitos Clave para el Cliente

| Hito | Semana | Impacto en el negocio |
|------|--------|-----------------------|
| 🟢 **Bot experto operativo** | 5 | Los clientes reciben atención 24/7 por WhatsApp con un agente experto en gasfitería. El equipo humano deja de responder preguntas repetitivas. |
| 🟡 **Arquitectura lista** | 8 | El sistema está preparado para crecer. La web (de cualquier proveedor) puede conectarse vía API REST. |
| 🔵 **Agenda automática** | 11 | Los técnicos reciben visitas asignadas sin que nadie las gestione (calendario propio + vista read-only en sus calendarios). |
| 🟣 **LumatAgent 100%** | 14 | El dueño crea automatizaciones hablando. El sistema opera solo. Reportes semanales automáticos. |

---

## Dependencias y Riesgos

| Riesgo | Probabilidad | Mitigación |
|--------|-------------|------------|
| Aprobación Meta WhatsApp API | Media | Iniciar trámite en semana 1. Usar entorno de pruebas mientras tanto. |
| **Contenido de base de conocimiento (gasfitería)** | Media | HandCodeStudio crea la estructura y el pipeline de carga. Lumat provee manuales, procedimientos y tarifarios. El agente puede guiar con los documentos cargados; lo que falta se agrega por el gestor de KB. |
| **Prompt injection / ataques al canal público** | Media | Validación de entrada, whitelist de tools, límites de alcance, auditoría. Tests de inyección en cada fase. |
| Cambios de alcance durante desarrollo | Baja | Fases cortas (2-3 sem) con entregables. Se evalúa y ajusta al final de cada fase. |
| Retraso por aprobaciones del cliente | Baja | Cada fase termina con un entregable funcional. No se necesita esperar aprobación para avanzar. |

---

## Post-entrega

| Concepto | Detalle |
|----------|---------|
| **Garantía** | 60 días corridos desde la entrega |
| **Soporte mensual** | $50-100 USD/mes (mantenimiento + bugs + updates) |
| **Soporte por evento** | $30-50 USD/hora (sin retención mensual) |
| **Web (M2)** | A evaluar después del hito 2 (semana 8). HandCodeStudio puede integrar el agente con la web del proveedor que Lumat elija. |

---

> Documento preparado por HandCodeStudio — Stefan Miranda
> Contacto: [tu email/teléfono]
