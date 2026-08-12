# LumatAgent — Arquitectura del Sistema Multi-Agente

> Documento interno para diseño y cotización.
> Post-reunión Lumat — 20 julio 2026.

---

## 1. Visión general

El LumatAgent NO es un chatbot. Es un **coworker digital** que vive en el servidor,
entiende procesos de negocio, delega tareas a sub-agentes especializados, y puede
crear automatizaciones por instrucción del dueño en lenguaje natural.

```
Dueño ──▶ LumatAgent (orquestador) ──▶ Sub-agentes ──▶ Tools → DB/APIs
              │
              └── También accesible por: Admin (web), Técnico (web), Cliente (WhatsApp)
```

---

## 2. Stack tecnológico

| Componente | Tecnología |
|---|---|
| Servidor | VPS Hetzner (CX21/CX31) |
| Contenedor | Docker (no `--privileged`) |
| API Gateway | FastAPI (Python) |
| Orquestador | LangGraph (state machine) |
| Base de datos | PostgreSQL + pgvector |
| Almacenamiento | Volumen Docker (imágenes, documentos) |
| WhatsApp | WhatsApp Cloud API (Meta) |
| Calendario | CalDAV (iPhone calendar) + Google Calendar API |
| Email | SMTP / SendGrid |
| Pagos | Webpay / Transbank (M3) |

---

## 3. Arquitectura en el servidor

```
┌─────────────────────────────────────────────────────────────┐
│                       VPS (Hetzner)                          │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Docker Container (app)                     │ │
│  │                                                         │ │
│  │  ┌──────────────────┐   ┌──────────────────────────┐   │ │
│  │  │  API Gateway      │   │  LumatAgent Core         │   │ │
│  │  │  (FastAPI)        │──▶│                          │   │ │
│  │  │  ─ Webhooks       │   │  ┌────────────────────┐ │   │ │
│  │  │  ─ Admin API      │   │  │  Orchestrator      │ │   │ │
│  │  │  ─ Tech API       │   │  │  (LangGraph)       │ │   │ │
│  │  └──────────────────┘   │  └────────┬───────────┘ │   │ │
│  │                          │           │              │   │ │
│  │                          │     ┌─────┴──────────┐   │   │ │
│  │                          │     │  Router de      │   │   │ │
│  │                          │     │  sub-agentes    │   │   │ │
│  │                          │     └──┬──┬──┬──┬──┬──┘   │   │ │
│  │                          │        │  │  │  │  │       │   │ │
│  │                          │  ┌─────┘  │  │  │  └──┐    │   │ │
│  │                          │  │   ┌────┘  │  └──┐  │    │   │ │
│  │                          │  ▼   ▼       ▼   ▼  ▼    │   │ │
│  │                          │ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ │   │ │
│  │                          │ │WA│ │CA│ │AA│ │NA│ │RA│ │   │ │
│  │                          │ └──┘ └──┘ └──┘ └──┘ └──┘ │   │ │
│  │                          └──────────────────────────┘   │ │
│  │                                                         │ │
│  │  ┌────────────────────┐   ┌────────────────────────┐   │ │
│  │  │  PostgreSQL         │   │  File Storage           │   │ │
│  │  │  + pgvector         │   │  (imágenes, docs)       │   │ │
│  │  └────────────────────┘   └────────────────────────┘   │ │
│  │                                                         │ │
│  │  ┌──────────────────────────────────────────────────┐   │ │
│  │  │  Workers de Automatización (proceso aparte)       │   │ │
│  │  │  ─ Revisa la tabla automations cada N minutos     │   │ │
│  │  │  ─ Ejecuta acciones programadas                   │   │ │
│  │  │  ─ Envía recordatorios, seguimientos, etc.        │   │ │
│  │  └──────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Volumen Docker (persistente)                          │ │
│  │  ─ backups PostgreSQL                                  │ │
│  │  ─ uploads (imágenes, documentos)                      │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Sub-agentes**:
- **WA** — WhatsApp Agent: mensajes entrantes/salientes, plantillas Meta
- **CA** — Calendar Agent: disponibilidad, agendamiento, CalDAV + Google Calendar
- **AA** — Automation Agent: crea y gestiona automatizaciones
- **NA** — Notification Agent: recordatorios, seguimientos, alertas
- **RA** — Report Agent: resúmenes, KPIs, exportaciones
- _(Futuro) Client Agent: CRUD de fichas (hoy lo maneja el orquestador directo)_

---

## 4. Cómo funciona el WhatsApp Agent (primera funcionalidad)

```
Cliente escribe a WhatsApp
        │
        ▼
WhatsApp Cloud API → Webhook → API Gateway
        │
        ▼
Orquestador recibe → Clasifica intención
        │
        ├── ¿Emergencia? → Protocolo → Notifica dueño/técnico
        ├── ¿Cliente nuevo? → Crea ficha en DB
        ├── ¿Cliente existente? → Busca historial
        ├── ¿Agendar? → Calendar Agent check disponibilidad
        ├── ¿Pregunta? → Base de conocimiento + contexto
        └── ¿Derivar? → Resumen → Notifica a humano
```

Las **plantillas de seguimiento** las crea el dueño diciéndole al agente:
> "Pasado 3 días de un servicio, enviá plantilla X"

El Automation Agent guarda esto como un registro en DB, y el Worker de
Automatización lo ejecuta cuando corresponde.

---

## 5. Sistema de permisos y roles

### 5.1 El agente NO tiene acceso al sistema operativo

- Corre en contenedor Docker sin `--privileged`
- Filesystem del contenedor es **read-only** para los procesos del agente
- No puede ejecutar `sudo`, `apt`, `bash` con permisos de escritura
- No puede modificar su propio código

### 5.2 Tools controladas (whitelist)

El agente solo hace lo que tiene una tool para hacer. Cada tool:

1. Valida permisos del usuario
2. Valida parámetros
3. Ejecuta la operación
4. Loguea en `audit_log`
5. Devuelve resultado

No existe "ejecutar código arbitrario". Las automatizaciones son
configuraciones en DB que un worker aparte ejecuta.

```
create_automation(trigger, action, params) → INSERT en automations table
                                                     ↓
                                     Worker aparte lee y ejecuta
```

### 5.3 Roles de usuario

| Rol | Acceso al LumatAgent | Puede hacer |
|---|---|---|
| **Dueño** | Lenguaje natural desde panel web | Crear automatizaciones, configurar reglas, ver todo, gestionar equipo |
| **Admin** | Panel web limitado | Ver clientes, asignar técnicos, cambiar estados, ver reportes |
| **Técnico** | Panel web operativo | Ver sus visitas, marcar completado, subir evidencia |
| **Cliente** | Solo WhatsApp | NO tiene acceso directo al LumatAgent |

### 5.4 Protección de datos sensibles

- El agente nunca recibe datos de pago (van directo a Webpay/Transbank)
- Conversaciones accesibles solo por rol (técnico no ve clientes ajenos)
- Regla hardcodeada: no revelar datos de otros clientes
- Auditoría completa en `audit_log` (quién, qué, cuándo)

---

## 6. Cómo crea automatizaciones el agente

El dueño dice:

> "Che Lumat, cada vez que un servicio termine, pasados 3 días mandale
> un WhatsApp preguntando cómo le fue."

El agente:

1. **Entiende** el requerimiento (trigger, delay, acción)
2. **Propone** al dueño: confirma antes de crear
3. **Guarda** un registro en `automations` table
4. **El Worker** (no el LLM) ejecuta cuando corresponde

**El agente NO escribe código. Escribe configuraciones.**

---

## 7. Modelo de datos principales (entidades)

| Entidad | Descripción |
|---|---|
| `clients` | Fichas de clientes (datos, dirección, equipos) |
| `conversations` | Historial completo de conversaciones |
| `services` | Tipos de servicio (calefont, caldera, calefacción) |
| `visits` | Visitas agendadas (técnico, fecha, estado) |
| `technicians` | Técnicos de Lumat (disponibilidad, agenda) |
| `automations` | Reglas de automatización (trigger, acción, params) |
| `notifications` | Notificaciones programadas y enviadas |
| `templates` | Plantillas WhatsApp (para filtros Meta) |
| `users` | Usuarios del sistema (dueño, admin, técnico) |
| `audit_log` | Registro de acciones del agente |
| `kb_documents` | Base de conocimiento (RAG) |

---

## 8. Flujo de interacción completo

```
Dueño (panel web)
  │
  ├── "Mostrame los servicios de hoy"
  │     → Orquestador → Calendar Agent → responde
  │
  ├── "Creá una automatización: cuando un cliente nuevo hable,
  │     pasada 1 hora enviale la plantilla de bienvenida"
  │     → Orquestador → Automation Agent → guarda regla
  │
  └── "¿Cómo viene la semana?"
        → Orquestador → Report Agent → genera resumen

Técnico (panel web)
  │
  ├── "Mis visitas de mañana"
  │     → API directa (no pasa por LLM)
  │
  └── Marca servicio como completado
        → Actualiza DB → Notification Agent → avisa al dueño

Cliente (WhatsApp)
  │
  └── Interacción con WhatsApp Agent
        → Sin acceso directo al orquestador
```
