# LumatAgent — Plan de trabajo por hitos

> Propuesta de trabajo preparada por HandCodeStudio (Stefan Miranda)
> Documento orientado al cliente — Lumat (Maximiliano y equipo)
> Fecha: 7 de agosto de 2026
> **Estatus: propuesta sujeta a negociación y firma de contrato**

---

## Introducción

LumatAgent es un asistente inteligente que atiende a los clientes de Lumat por WhatsApp las 24 horas: responde consultas técnicas de gasfitería, detecta emergencias, agenda visitas, notifica al equipo y automatiza tareas repetitivas. Se construye como un sistema multi-agente (un orquestador que coordina 5 sub-agentes especializados) gestionado desde un panel web instalable en el celular. El objetivo es que Lumat deje de responder preguntas repetitivas a mano, que las visitas se agenden sin gestión manual y que la operación diaria quede automatizada — con el dueño siempre en control de los límites y las reglas.

El trabajo se organiza en **4 hitos**, cada uno con un entregable funcional verificable. Al cerrar cada hito se revisa el resultado, se valida y se avanza al siguiente. Este documento detalla el contenido de cada hito, lo que se necesita de Lumat en cada etapa y cómo se trabaja.

---

## Resumen de hitos

| Hito | Semanas aprox. | Entregable principal | Impacto en el negocio |
|------|----------------|----------------------|-----------------------|
| 🟢 **Hito 1 — Setup + WhatsApp operativo** | Semanas 1-4 | Bot experto en gasfitería respondiendo por WhatsApp | Los clientes reciben atención 24/7; el equipo deja de responder preguntas repetitivas |
| 🟡 **Hito 2 — Arquitectura multiagente + panel** | Semanas 5-7 | Orquestador con 5 sub-agentes + panel web de control | La plataforma queda lista para crecer y conectar la web por API |
| 🔵 **Hito 3 — Calendario + notificaciones** | Semanas 8-9 | Agenda automática con calendario propio y avisos al equipo | Las visitas se agendan solas; los técnicos ven su agenda sin gestión manual |
| 🟣 **Hito 4 — Automatizaciones + reportes** | Semanas 10-12 | LumatAgent completo y autónomo con panel final | El dueño crea automatizaciones hablando; el sistema opera solo |

---

## 🟢 Hito 1 — Setup + WhatsApp operativo (semanas 1-4)

### Objetivo

Poner en marcha el servidor seguro y dejar al bot conversando por WhatsApp con clientes reales de Lumat. El bot debe ser un **experto en gasfitería desde el primer día** (no un bot genérico): responde consultas sobre calefonts, calderas y calefacción usando la base de conocimiento de Lumat, identifica si un cliente es nuevo o existente, crea la ficha cuando corresponde y detecta emergencias para avisar al equipo humano. Todo esto protegido contra intentos de manipulación del bot (prompt injection), dado que cualquiera puede escribirle por WhatsApp.

### Entregables concretos

- Servidor seguro y listo: firewall, acceso por llave SSH, cifrado TLS, backups automáticos diarios.
- Base de datos operativa con la estructura inicial.
- Bot de WhatsApp conectado a la API de Meta, con gestor de conversaciones y fichas de clientes.
- Base de conocimiento experta de Lumat cargada (manuales de fabricantes, procedimientos, tarifarios, FAQ).
- Límites de alcance configurables: el dueño define qué temas resuelve el bot solo y cuáles deriva siempre a humano.
- Detección de emergencias con aviso inmediato al dueño/técnico.
- Derivación a humano con historial y resumen de la conversación.
- Gestor de base de conocimiento (agregar y editar documentos desde el panel).
- Panel administrativo inicial: clientes, conversaciones, casos y exportación CSV/Excel.
- Pruebas de integración, funcionales y de prompt injection.

### Lo que se necesita de Lumat en este hito

- Iniciar el trámite de la API de Meta (ver `03-checklist-meta-api.md`) y aportar el número de teléfono prepago de pruebas.
- Entregar la base de conocimiento inicial: manuales de fabricantes, procedimientos de Lumat, tarifario y preguntas frecuentes. Si faltan documentos, el agente puede partir con lo disponible y el resto se carga por el gestor de KB.

### Criterio de aceptación (para pasar al Hito 2)

El bot atiende consultas reales de clientes por WhatsApp dentro de los límites configurados, crea y actualiza fichas, detecta emergencias y deriva a humano cuando corresponde. El panel permite ver conversaciones y gestionar la base de conocimiento. El cliente valida el comportamiento con casos de prueba reales.

---

## 🟡 Hito 2 — Arquitectura multiagente + panel de control (semanas 5-7)

### Objetivo

Transformar el bot en una **arquitectura multiagente**: un orquestador central que coordina 5 sub-agentes especializados (WhatsApp, Calendar, Automation, Notification y Report). El objetivo es que la plataforma quede preparada para sumar capacidades nuevas (agenda, automatizaciones, reportes) sin reescribir lo existente, y que la web externa pueda conectarse por API cuando Lumat lo decida. En paralelo se consolida el panel web como centro de control.

### Entregables concretos

- Orquestador (LangGraph) con router de sub-agentes y estado compartido controlado.
- Capa de herramientas (tools) con permisos por rol: un cliente por WhatsApp no puede ejecutar acciones de admin.
- Sistema de roles completo (dueño, admin, técnico, cliente).
- Auditoría de todo: cada conversación y cada acción queda registrada con quién, qué y cuándo.
- Aislamiento entre sub-agentes: un agente comprometido no contamina al resto.
- Estructura inicial (scaffold) de los agentes de Calendar, Automation, Notification y Report.
- Panel web de administración: clientes, agenda, dashboard, automatizaciones y chat con el agente.
- **Bandeja humana (inbox) de conversaciones con derivación a humano**: el equipo de Lumat ve los hilos, toma una conversación que el bot derivó, responde al cliente por el mismo número de WhatsApp desde el panel y puede devolverle la conversación al bot cuando se cierra el caso.
- Pruebas multiagente: enrutamiento, permisos, aislamiento y prompt injection entre agentes.

**Qué significa para Lumat**: cuando el bot deriva (emergencia, consulta fuera de sus límites o pedido del cliente), Max y su equipo ven el hilo en la bandeja del panel y escriben la respuesta directamente; el cliente la recibe desde el número de WhatsApp de Lumat, como si hubiera respondido el propio bot. No hace falta equipo especial ni un SIM adicional: la misma cuenta de WhatsApp de la empresa se usa para las respuestas del bot y de las personas.

### Lo que se necesita de Lumat en este hito

- Definir los roles de las personas del equipo que usarán el panel (quién es dueño, quién admin, quién técnico).
- Definir la política de datos: qué conversaciones se conservan y por cuánto tiempo (ver nota de retención en `03-checklist-meta-api.md`, Sección C).

### Criterio de aceptación (para pasar al Hito 3)

El orquestador enruta correctamente las consultas entre sub-agentes, los permisos por rol funcionan, y el panel permite gestionar clientes y conversaciones. La bandeja humana funciona: una conversación derivada aparece en el panel, un miembro del equipo responde desde ahí y el cliente recibe la respuesta por el número de WhatsApp de Lumat. La plataforma está lista para agregar Calendar, Automation, Notification y Report sin tocar el código existente. El cliente valida el funcionamiento del panel con su equipo.

---

## 🔵 Hito 3 — Calendario + notificaciones (semanas 8-9)

### Objetivo

Que el agente **agende visitas solo**. Se construye un calendario propio en la base de datos como única fuente de verdad (visitas, disponibilidad, bloqueos, reglas de zona y técnicos), con exportación de solo lectura hacia los calendarios de iPhone/Google de los técnicos. Las visitas entran por 4 canales distintos pero todas respetan las mismas reglas. El sistema además notifica al equipo según la prioridad de cada evento, respetando las reglas de ventana de 24 horas de Meta.

### Entregables concretos

- Calendario propio en PostgreSQL (fuente de verdad: visitas, disponibilidad, bloqueos, reglas).
- Exportación ICS de solo lectura por técnico (ven su agenda en iPhone/Google, no pueden modificar desde ahí; los cambios se hacen por WhatsApp o el panel).
- Agendamiento y reprogramación por WhatsApp y por el panel, con reglas de disponibilidad.
- 4 canales de entrada de visitas: WhatsApp (cliente), panel dueño/admin, panel técnico, y carga manual (cliente llama por teléfono y la secretaria la registra).
- Notificaciones programadas: recordatorios de visita y seguimientos post-servicio.
- Cola de notificaciones con plantillas preparadas.
- Panel: vista de agenda con asignación visual de técnicos.
- Pruebas de integración de calendario y notificaciones.

### Notificaciones al equipo según prioridad

| Prioridad | Ejemplos | Canal |
|-----------|----------|-------|
| 🔴 Inmediata | Emergencia de cliente, sistema caído | WhatsApp al dueño de inmediato + aviso en el panel |
| 🟠 Alta / 🟡 Media | Visita agendada/cancelada, cliente nuevo, automatización ejecutada | WhatsApp (resumen) + panel (detalle) |
| 🔵 Programada | Reportes diarios/semanales, KPIs | Email + panel |

Se respeta la ventana de 24 horas de Meta: dentro de la ventana los mensajes son libres; fuera de ella solo se envían plantillas aprobadas (recordatorios, alertas), con costo referencial por mensaje.

### Lo que se necesita de Lumat en este hito

- Decidir el **calendario de trabajo**: horarios de atención, zonas, técnicos y reglas de asignación.
- Confirmar a qué WhatsApp del equipo llegan las alertas de emergencia.

### Criterio de aceptación (para pasar al Hito 4)

Un cliente pide una hora por WhatsApp, el agente revisa disponibilidad, agenda la visita y envía recordatorio 24 h antes, todo automático. Los técnicos ven su agenda en su calendario personal sin poder modificarla desde ahí. El cliente valida el flujo con una visita de prueba real.

---

## 🟣 Hito 4 — Automatizaciones + reportes (semanas 10-12)

### Objetivo

Que el LumatAgent **trabaje solo**. Se agrega un sistema de automatizaciones donde el dueño crea reglas en lenguaje natural (por ejemplo: "3 días después de un servicio, enviar seguimiento preguntando cómo le fue" o "mantención anual a clientes que cumplen un año"). Las reglas se ejecutan por un worker determinístico que no depende del modelo de lenguaje, por lo que **siempre se ejecutan**. Además llegan los reportes automáticos y el panel queda completo como PWA instalable con centro de notificaciones.

### Entregables concretos

- Event bus del sistema (eventos: visita creada, servicio completado, cliente nuevo, entre otros).
- Creación de automatizaciones en lenguaje natural desde el chat del panel, con confirmación del dueño antes de activarlas.
- Worker determinístico (sin IA): ejecuta las reglas siempre, aunque el modelo esté caído.
- Report Agent: KPIs, resumen semanal automático y exportación avanzada.
- Panel como PWA: instalable en el home del celular, notificaciones push, experiencia de app.
- Módulo de chat con el agente en el panel (dueño/admin conversan con LumatAgent).
- Centro de notificaciones del panel: bandeja, filtros, leídas e historial.
- Dashboard avanzado con reportes gráficos.
- Buffer de pruebas finales, documentación, manual de uso y capacitación remota.

### Criterio de aceptación (para pasar a pruebas en producción)

El dueño crea una automatización hablando con el agente, la confirma y el worker la ejecuta cuando corresponde; los reportes semanales llegan solos; el panel instalado en el celular funciona como app con notificaciones. Se aprueba el sistema completo para la fase de pruebas con el número prepago.

---

## Requisitos del cliente (responsabilidades de Lumat)

Para que el proyecto avance en plazo, Lumat debe cubrir:

1. **Trámite de la API de Meta**: crear la cuenta de negocio, verificar la empresa y registrar el número (ver `03-checklist-meta-api.md`). Puede tardar semanas por trámites burocráticos, por eso se inicia apenas se firme el contrato.
2. **Base de conocimiento técnica**: entregar manuales de fabricantes, procedimientos de Lumat, tarifario y preguntas frecuentes. Se puede partir con lo disponible; el resto se carga durante el proyecto.
3. **Decidir el calendario**: horarios de atención, zonas, técnicos y reglas de asignación de visitas.
4. **Política de datos**: definir cuánto tiempo se conserva el historial de conversaciones (la retención es responsabilidad de Lumat, dato alojado en su servidor; corresponde verificar la normativa chilena aplicable, p. ej. Ley 19.628).
5. **Humano de respaldo durante las pruebas**: una persona de Lumat disponible para atender las derivaciones que el bot escale durante la fase de pruebas con el número prepago. No requiere equipo especial: la persona responde desde el panel web, por el mismo número de WhatsApp de Lumat.

---

## Cómo trabajamos

- **Fases cortas con entregables funcionales**: cada hito dura entre 2 y 4 semanas y termina con algo visible y usable, no con código "a medio camino".
- **Revisión al cierre de cada hito**: al final de cada fase se revisa el entregable, se ajusta lo necesario y recién ahí se avanza. Los cambios de alcance se evalúan y cotizan por separado si exceden lo pactado.
- **Comunicación fluida**: avance visible en el panel de pruebas y reunión breve al cierre de cada hito. Las dudas que bloquean (por ejemplo, documentos de la base de conocimiento) se piden por anticipado para no detener el desarrollo.
- **Pruebas antes de producción**: todo se valida primero con un número prepago de pruebas y con casos reales controlados, antes de migrar al número principal de WhatsApp.
- **El dueño manda**: los límites del agente, las reglas de agenda y las automatizaciones los define Lumat. Stefan construye y configura; el control operativo queda en manos del dueño.

---

## Nota honesta sobre plazos

El núcleo del sistema (los 4 hitos) se construye en **aproximadamente 2 meses** de trabajo de desarrollo. A eso se suma un **período de pruebas y ajustes** de aproximadamente 4 semanas con el número prepago, que incluye probar el flujo con clientes reales controlados, ajustar respuestas, capacitar al equipo y recién entonces **migrar al número real de WhatsApp**.

La experiencia con trámites de Meta indica que **la aprobación de la API puede demorar semanas** y no depende de nosotros; por eso se inicia en paralelo desde el día uno y las pruebas arrancan con el número prepago mientras tanto. Los plazos de este documento son **tentativos** y se ajustan según la firma del contrato y el avance del trámite de Meta.
