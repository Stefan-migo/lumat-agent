# Propuesta Final — LumatAgent · Sistema de atención y automatización por WhatsApp

| | |
|---|---|
| **Proveedor** | HandCodeStudio — Stefan Miranda |
| **Cliente** | Lumat (Maximiliano) — Servicios de gasfitería, Chile |
| **Proyecto** | LumatAgent — sistema multi-agente de atención, agenda y automatización por WhatsApp |
| **Fecha** | 7 de agosto de 2026 |
| **Estatus** | Propuesta para etapa de contrato |

---

## 1. Resumen ejecutivo

LumatAgent es un asistente inteligente que atiende a los clientes de Lumat por WhatsApp las 24 horas del día. Responde consultas técnicas de gasfitería con criterio de experto, detecta emergencias, agenda visitas, notifica al equipo y automatiza tareas repetitivas. Se construye como un **sistema multi-agente**: un orquestador central coordina 5 sub-agentes especializados (WhatsApp, Calendar, Automation, Notification y Report), y todo se gestiona desde un **panel web** instalable en el celular.

La propuesta contempla:

| Concepto | Detalle |
|----------|---------|
| **Atención por WhatsApp** | Agente conversacional experto en gasfitería, con base de conocimiento propia de Lumat cargada desde el día 1 |
| **Calendario propio** | Agenda de visitas con disponibilidad real y vista de solo lectura en los calendarios de los técnicos |
| **Automatizaciones en lenguaje natural** | El dueño le dice al agente qué hacer ("3 días después de un servicio, enviar seguimiento") y el sistema lo ejecuta solo |
| **Panel web (PWA)** | Dashboard con clientes, agenda, reportes, centro de notificaciones, chat con el agente y bandeja de atención humana |
| **Inversión final** | **USD 2,800**, en 5 pagos mensuales iguales de USD 560 (descuento de ≈7% sobre el precio base de USD 3,000) |
| **Plazo** | ~4 meses: 2 de construcción + 2 de evaluación, pruebas y puesta en marcha |
| **Garantía** | 60 días corridos desde la entrega |

El objetivo de negocio es que Lumat deje de responder preguntas repetitivas a mano, que las visitas se agenden sin gestión manual y que la operación diaria quede automatizada, con el dueño siempre en control de los límites y las reglas del sistema.

---

## 2. Alcance y entregables por hito

El trabajo se organiza en **4 hitos**, cada uno con un entregable funcional verificable. Al cerrar cada hito se revisa el resultado con Lumat, se ajusta lo necesario y se avanza al siguiente.

| Hito | Semanas aprox. | Entregable principal | Impacto en el negocio |
|------|----------------|----------------------|-----------------------|
| 🟢 **Hito 1 — Setup + WhatsApp operativo** | 1-4 | Bot experto en gasfitería respondiendo por WhatsApp | Atención 24/7; el equipo deja de responder preguntas repetitivas |
| 🟡 **Hito 2 — Arquitectura multiagente + panel** | 5-7 | Orquestador con 5 sub-agentes + panel web de control | Plataforma lista para crecer y conectar la web por API |
| 🔵 **Hito 3 — Calendario + notificaciones** | 8-9 | Agenda automática con calendario propio y avisos al equipo | Las visitas se agendan solas; los técnicos ven su agenda sin gestión manual |
| 🟣 **Hito 4 — Automatizaciones + reportes** | 10-12 | LumatAgent completo y autónomo, con panel final | El dueño crea automatizaciones hablando; el sistema opera solo |

### 🟢 Hito 1 — Setup + WhatsApp operativo

**Objetivo.** Poner en marcha el servidor seguro y dejar al bot conversando por WhatsApp con clientes reales de Lumat. El bot debe ser un experto en gasfitería desde el primer día: responde consultas sobre calefonts, calderas y calefacción usando la base de conocimiento de Lumat, identifica clientes nuevos y existentes, crea fichas, detecta emergencias y avisa al equipo humano. Todo protegido contra intentos de manipulación del bot (prompt injection), dado que cualquier persona puede escribirle por WhatsApp.

**Entregables.**
- Servidor seguro y listo: firewall, acceso por llave SSH, cifrado TLS, backups automáticos diarios.
- Base de datos operativa con la estructura inicial.
- Bot de WhatsApp conectado a la Cloud API de Meta, con gestor de conversaciones y fichas de clientes.
- Base de conocimiento experta de Lumat cargada (manuales de fabricantes, procedimientos, tarifarios, FAQ).
- Límites de alcance configurables: el dueño define qué temas resuelve el bot solo y cuáles deriva siempre a humano.
- Detección de emergencias con aviso inmediato al dueño o técnico.
- Derivación a humano con historial y resumen de la conversación.
- Gestor de base de conocimiento (agregar y editar documentos desde el panel).
- Panel administrativo inicial: clientes, conversaciones, casos y exportación CSV/Excel.
- Pruebas de integración, funcionales y de prompt injection.

**Lo que se necesita de Lumat.** Iniciar el trámite de la API de Meta y aportar el número de teléfono prepago de pruebas. Entregar la base de conocimiento inicial: manuales, procedimientos, tarifario y preguntas frecuentes (se puede partir con lo disponible y completar durante el proyecto).

**Criterio de aceptación.** El bot atiende consultas reales por WhatsApp dentro de los límites configurados, crea y actualiza fichas, detecta emergencias y deriva a humano cuando corresponde. El panel permite ver conversaciones y gestionar la base de conocimiento. Lumat valida el comportamiento con casos de prueba reales.

### 🟡 Hito 2 — Arquitectura multiagente + panel de control

**Objetivo.** Transformar el bot en una arquitectura multiagente: un orquestador central coordina 5 sub-agentes especializados (WhatsApp, Calendar, Automation, Notification y Report). La plataforma queda preparada para sumar capacidades nuevas sin reescribir lo existente, y la web externa podrá conectarse por API cuando Lumat lo decida. En paralelo se consolida el panel web como centro de control.

**Entregables.**
- Orquestador (LangGraph) con router de sub-agentes y estado compartido controlado.
- Capa de herramientas (tools) con permisos por rol: un cliente por WhatsApp no puede ejecutar acciones de admin.
- Sistema de roles completo (dueño, admin, técnico, cliente).
- Auditoría completa: cada conversación y cada acción queda registrada con quién, qué y cuándo.
- Aislamiento entre sub-agentes: un agente comprometido no contamina al resto.
- Estructura inicial (scaffold) de los agentes de Calendar, Automation, Notification y Report.
- Panel web de administración: clientes, agenda, dashboard, automatizaciones y chat con el agente.
- **Bandeja humana (inbox)**: el equipo de Lumat ve los hilos, toma una conversación que el bot derivó, responde al cliente por el mismo número de WhatsApp desde el panel y puede devolverle la conversación al bot al cerrar el caso.
- Pruebas multiagente: enrutamiento, permisos, aislamiento y prompt injection entre agentes.

**Qué significa para Lumat.** Cuando el bot deriva (emergencia, consulta fuera de sus límites o pedido del cliente), Max y su equipo ven el hilo en la bandeja del panel y escriben la respuesta directamente; el cliente la recibe desde el número de WhatsApp de Lumat, como si hubiera respondido el propio bot. No hace falta equipo especial ni un SIM adicional.

**Lo que se necesita de Lumat.** Definir los roles de las personas del equipo que usarán el panel (quién es dueño, quién admin, quién técnico). Definir la política de datos: qué conversaciones se conservan y por cuánto tiempo.

**Criterio de aceptación.** El orquestador enruta correctamente las consultas entre sub-agentes, los permisos por rol funcionan y el panel permite gestionar clientes y conversaciones. La bandeja humana funciona de extremo a extremo: una conversación derivada aparece en el panel, un miembro del equipo responde desde ahí y el cliente recibe la respuesta por el número de WhatsApp de Lumat. La plataforma está lista para agregar Calendar, Automation, Notification y Report sin tocar el código existente.

### 🔵 Hito 3 — Calendario + notificaciones

**Objetivo.** Que el agente agende visitas solo. Se construye un calendario propio en la base de datos como única fuente de verdad (visitas, disponibilidad, bloqueos, reglas de zona y técnicos), con exportación de solo lectura hacia los calendarios de iPhone/Google de los técnicos. Las visitas entran por 4 canales distintos y todas respetan las mismas reglas. El sistema notifica al equipo según la prioridad de cada evento, respetando las reglas de ventana de 24 horas de Meta.

**Entregables.**
- Calendario propio en PostgreSQL (fuente de verdad: visitas, disponibilidad, bloqueos, reglas).
- Exportación ICS de solo lectura por técnico: ven su agenda en iPhone/Google sin poder modificarla desde ahí; los cambios se hacen por WhatsApp o el panel.
- Agendamiento y reprogramación por WhatsApp y por el panel, con reglas de disponibilidad.
- 4 canales de entrada de visitas: WhatsApp (cliente), panel del dueño/admin, panel del técnico y carga manual (cliente llama por teléfono y la secretaria la registra).
- Notificaciones programadas: recordatorios de visita y seguimientos post-servicio.
- Cola de notificaciones con plantillas preparadas.
- Panel: vista de agenda con asignación visual de técnicos.
- Pruebas de integración de calendario y notificaciones.

**Notificaciones al equipo según prioridad.**

| Prioridad | Ejemplos | Canal |
|-----------|----------|-------|
| Inmediata | Emergencia de cliente, sistema caído | WhatsApp al dueño de inmediato + aviso en el panel |
| Alta / Media | Visita agendada/cancelada, cliente nuevo, automatización ejecutada | WhatsApp (resumen) + panel (detalle) |
| Programada | Reportes diarios/semanales, KPIs | Email + panel |

**Lo que se necesita de Lumat.** Decidir el calendario de trabajo: horarios de atención, zonas, técnicos y reglas de asignación. Confirmar a qué WhatsApp del equipo llegan las alertas de emergencia.

**Criterio de aceptación.** Un cliente pide una hora por WhatsApp, el agente revisa disponibilidad, agenda la visita y envía recordatorio 24 h antes, todo automático. Los técnicos ven su agenda en su calendario personal sin poder modificarla desde ahí. Lumat valida el flujo con una visita de prueba real.

### 🟣 Hito 4 — Automatizaciones + reportes

**Objetivo.** Que el LumatAgent trabaje solo. Se agrega un sistema de automatizaciones donde el dueño crea reglas en lenguaje natural (por ejemplo: "3 días después de un servicio, enviar seguimiento preguntando cómo le fue"). Las reglas se ejecutan por un worker determinístico que no depende del modelo de lenguaje, por lo que siempre se ejecutan. Llegan los reportes automáticos y el panel queda completo como PWA instalable con centro de notificaciones.

**Entregables.**
- Event bus del sistema (eventos: visita creada, servicio completado, cliente nuevo, entre otros).
- Creación de automatizaciones en lenguaje natural desde el chat del panel, con confirmación del dueño antes de activarlas.
- Worker determinístico (sin IA): ejecuta las reglas siempre, aunque el modelo esté caído.
- Report Agent: KPIs, resumen semanal automático y exportación avanzada.
- Panel como PWA: instalable en el home del celular, notificaciones push, experiencia de app.
- Módulo de chat con el agente en el panel (el dueño y los admins conversan con LumatAgent).
- Centro de notificaciones del panel: bandeja, filtros, leídas e historial.
- Dashboard avanzado con reportes gráficos.
- Buffer de pruebas finales, documentación, manual de uso y capacitación remota.

**Criterio de aceptación.** El dueño crea una automatización hablando con el agente, la confirma y el worker la ejecuta cuando corresponde; los reportes semanales llegan solos; el panel instalado en el celular funciona como app con notificaciones. El sistema completo queda aprobado para la fase de pruebas con el número prepago.

---

## 3. Arquitectura del sistema

El sistema se estructura como un núcleo multi-agente sobre una capa de herramientas controlada:

- **Orquestador (LangGraph).** Coordina el flujo conversacional, clasifica la intención y enruta cada consulta al sub-agente correspondiente (WhatsApp, Calendar, Automation, Notification, Report).
- **Sub-agentes especializados.** Cada uno atiende un dominio. Un agente comprometido no contamina el contexto de los demás (aislamiento de contexto).
- **Tools layer con whitelist.** El agente solo puede llamar las herramientas permitidas para el rol de quien lo invocó. Un cliente por WhatsApp no puede ejecutar acciones de admin.
- **PostgreSQL + pgvector como fuente de verdad.** Clientes, visitas, configuraciones y búsqueda semántica de la base de conocimiento. El historial y los datos de Lumat viven en el servidor de Lumat.
- **Base de conocimiento experta desde el día 1.** Manuales de fabricantes, procedimientos, tarifarios, FAQ, guías de troubleshooting y códigos de error se cargan en pgvector para búsqueda semántica. El agente guía al cliente en diagnósticos simples con pasos seguros y deriva a humano cuando la consulta excede lo configurado.
- **Calendario propio + exportación ICS read-only.** El servidor genera un archivo ICS por técnico; el técnico se suscribe desde su iPhone/Google Calendar y ve sus visitas actualizadas (solo lectura). Los cambios se hacen por WhatsApp o el panel. Esta decisión evita la sincronización bidireccional (costosa y frágil con Apple y Google) y mantiene las reglas de negocio en una sola fuente trazable.
- **Automatizaciones con worker determinístico.** El agente no escribe código: escribe configuraciones (trigger + condición + acción) que el dueño confirma. Un worker separado, sin LLM, las ejecuta siempre, incluso si el modelo está caído. Todo queda registrado en auditoría.
- **Panel web (PWA).** Instalable en el home del celular sin pasar por las tiendas de apps. Incluye dashboard, chat con el agente, centro de notificaciones y bandeja humana.
- **Centro de notificaciones (7 categorías).** Emergencias, operativas, clientes, automatizaciones, reportes, técnicos y sistema. El dueño configura en el panel qué recibe por WhatsApp, qué por email y qué solo en el panel. WhatsApp es el aviso rápido; el panel es el registro completo.
- **Bandeja humana para derivación.** El número de WhatsApp es un canal compartido entre el bot y las personas: quién responde es estado de la aplicación, no de Meta. El humano atiende el hilo desde el panel por el mismo número, sin SIM extra. El estado por conversación (bot, human, closed) vive en la base de datos.

---

## 4. Servidor e infraestructura

### 4.1 VPS recomendado y alternativas

| Proveedor | Plan | Precio/mes (referencial) | Datacenter | Notas clave |
|-----------|------|--------------------------|------------|-------------|
| **Hostinger** (recomendado) | KVM 2 (2 vCPU / 8 GB / 100 GB NVMe) | ~US$8.79/mes intro (2 años prepago); renovación ~US$14.99 | São Paulo (Brasil) | Latencia a Chile ~40-60 ms; backups semanales gratis; soporte en español 24/7 |
| **MOX Networks** (alternativa local) | VPS Pro (2 vCPU / 4 GB / 10 GB NVMe) | ~US$18/mes (CLP 17.000, IVA incl.) | Santiago de Chile | IP chilena dedicada; backup diario externo incluido; soporte humano en español; disco menor (10 GB) |
| **Hetzner** (staging) | CPX21 (3 vCPU / 4 GB / 80 GB NVMe) | ~€5-15/mes | Europa/USA/Singapur | Sin datacenter en LATAM (~240-290 ms); solo como entorno de staging/dev |
| **Vultr** (mención) | 2 vCPU / 4 GB | ~US$24/mes | Santiago de Chile | Datacenter en Chile; considerarla si se prioriza rendimiento |

**Recomendación.** Hostinger KVM 2 como servidor principal (cumple el dimensionamiento, buen precio, backups y soporte en español), MOX como alternativa local si se prefiere IP chilena, y Hetzner como entorno de staging. Todos los precios son **referenciales a la fecha 7 de agosto de 2026** y se verifican al momento de contratar.

### 4.2 Stack tecnológico

| Componente | Tecnología |
|------------|------------|
| API gateway / webhooks / panel | FastAPI (Python) |
| Orquestador y agentes | LangGraph |
| Base de datos | PostgreSQL + pgvector (fuente de verdad + búsqueda semántica) |
| Almacenamiento | Volumen persistente (documentos KB, exportaciones ICS, media) |
| Worker de automatizaciones | Proceso determinístico, sin LLM |
| Contenedores | Docker + Docker Compose sobre Ubuntu LTS |
| Dominios | `agente.lumat.cl` (API/webhooks) y `panel.lumat.cl` (panel) |

### 4.3 Seguridad del servidor

| Capa | Medida |
|------|--------|
| Red | Firewall solo puertos 80/443 y SSH; todo lo demás cerrado |
| Acceso | SSH solo por llave (sin password), usuario dedicado sin privilegios |
| Fuerza bruta | fail2ban sobre SSH y endpoints expuestos |
| Contenedores | Docker sin `--privileged`, filesystem read-only para el agente |
| Secretos | API keys de Meta/OpenAI en variables de entorno del servidor, nunca en código ni en el repo |
| Backups | Automáticos diarios de PostgreSQL a volumen externo, con retención definida y verificación periódica de restauración |
| Cifrado | TLS obligatorio en todas las comunicaciones (renovación automática) |
| Monitoreo | Uptime, alerta si el bot o una API externa caen, aviso si un backup falla |
| Registro | Auditoría de acciones en `audit_log` (quién, qué, cuándo) |

---

## 5. Integración WhatsApp Business API

La WhatsApp Business Cloud API de Meta es la vía oficial para que el sistema atienda y escriba mensajes por WhatsApp en nombre de Lumat. No es la app de WhatsApp Business: es una API en la nube conectada al servidor donde corre LumatAgent.

### 5.1 Qué hace el cliente (Lumat)

1. Crear la cuenta de negocio en Meta Business Suite, con un perfil administrativo único de la empresa.
2. Verificar la empresa ante Meta (por dominio `lumat.cl` o documentación legal); desbloquea el nombre comercial visible y límites mayores.
3. Registrar el número de teléfono real y propio, con verificación por SMS o llamada de Meta.
4. Configurar el nombre del negocio tal como se mostrará a los clientes.
5. Aceptar los términos de la plataforma WhatsApp Business.

**El trámite puede demorar semanas** por la revisión de Meta, por lo que se inicia apenas se firme el contrato. Mientras tanto se avanza con un número prepago de pruebas.

### 5.2 Qué hace Stefan (HandCodeStudio)

1. Crear la app en Meta for Developers asociada a la cuenta de negocio de Lumat.
2. Configurar la WhatsApp Cloud API: vincular la cuenta de negocio (WABA), obtener el Phone Number ID y el token de acceso.
3. Configurar el webhook (`https://agente.lumat.cl/webhook/whatsapp`) con su verify token y suscribirse a los eventos de mensajes.
4. Configurar la verificación en dos pasos (PIN de 6 dígitos) del número apenas se registre.
5. Preparar plantillas de utilidad (recordatorios de visita, alertas, resúmenes), que se aprueban rápido en Meta.
6. Persistir mensajes apenas llegan: responder `200` al webhook de inmediato y guardar en la base de datos, deduplicando por ID de mensaje (wamid) para tolerar reintentos de Meta.

### 5.3 Número dedicado de pruebas

| Aspecto | Test number (Meta) | Número prepago dedicado |
|---------|--------------------|--------------------------|
| Origen | Lo asigna Meta con la WABA de prueba | Número telefónico propio de Lumat |
| Mensajes | Gratuitos, solo a 5 destinatarios verificados | Reales, con clientes de prueba |
| Plantillas | Solo ejemplos pre-aprobados | Plantillas propias aprobadas |
| Uso | Desarrollo técnico | Fase de pruebas con clientes reales |

**Conclusiones clave de la investigación técnica:**
- El **test number de Meta no sirve para clientes reales** (solo permite 5 destinatarios). La fase de pruebas con Lumat usa un **número prepago dedicado**.
- **El SIM conserva sus funciones normales**: al registrar el número en la Cloud API, sigue haciendo y recibiendo llamadas y SMS por la red celular.
- **La app de WhatsApp se apaga en ese número**: un número registrado en la Cloud API no puede estar a la vez activo en la app de WhatsApp (normal o Business). Por eso se usa un **número dedicado nuevo** (SIM prepago), que evita interrumpir el WhatsApp personal de Max y permite que el chip siga tomando llamadas/SMS.

### 5.4 Reglas de la ventana de 24 horas

- **Dentro de la ventana** (el cliente interactuó hace menos de 24 h): respuestas de texto libre, sin plantilla y sin costo.
- **Fuera de la ventana**: solo plantillas aprobadas por Meta, con costo referencial de ~$0.04-0.08 por mensaje.
- Las plantillas de utilidad (recordatorios, alertas, resúmenes) se aprueban rápido, a veces de forma automática.

### 5.5 Mensajes borrados

- El sistema **recibe y guarda cada mensaje en el momento en que llega**. Si un cliente borra un mensaje "para todos" después, ese borrado **no elimina la copia ya guardada** en el servidor de Lumat.
- La Cloud API **no tiene un evento de webhook de borrado confiable**: llega un evento genérico (tipo `unsupported`, error 131051) que se dispara por múltiples causas. Por lo tanto, **no se puede detectar borrados de forma confiable** y esto no se promete como funcionalidad.
- La retención del historial es política de Lumat (los datos viven en su servidor): corresponde definir por cuánto tiempo se conservan las conversaciones y verificar la normativa chilena aplicable.

### 5.6 Handoff humano (bandeja del panel)

La bandeja humana permite que una persona atienda directamente a un cliente por el mismo número de WhatsApp: el panel llama al mismo endpoint de mensajes de Meta con el mismo token de la empresa. El cliente ve la respuesta desde el número de Lumat, sin SIM extra, sin app adicional y sin configuración extra en Meta. El webhook sigue entregando todos los mensajes aunque atienda un humano, de modo que el historial completo queda en el servidor.

---

## 6. Seguridad

### 6.1 Servidor

| Capa | Medida |
|------|--------|
| Red | Firewall solo puertos 80/443 y SSH |
| Acceso | SSH solo por llave, fail2ban, sin password |
| Contenedores | Docker sin `--privileged`, filesystem read-only para el agente |
| Secretos | Variables de entorno del servidor, nunca en el repo |
| Datos | Backups automáticos diarios, TLS obligatorio |
| Registro | Auditoría en `audit_log` (quién, qué, cuándo) |

### 6.2 Seguridad del canal WhatsApp (prompt injection)

El bot recibe mensajes de cualquier persona desconocida: es la superficie de ataque más expuesta del sistema. Mitigaciones:

- **El input del cliente es dato, nunca instrucción**: el system prompt del agente está aislado de cualquier contenido del usuario.
- **Validación de entrada**: se detectan y neutralizan intentos de inyección ("ignora tus instrucciones", "actúa como si fueras...", comandos embebidos en el texto).
- **Whitelist de tools por rol**: un cliente solo tiene las herramientas de cliente; no puede ejecutar acciones de admin ni escalar privilegios.
- **Nunca revelar datos sensibles**: regla fija — el agente no revela datos de otros clientes, contraseñas ni configuraciones internas.
- **Escalamiento controlado**: consultas fuera de alcance o intentos de manipulación se derivan a humano; nunca se ejecutan.
- **Límites de alcance configurables**: el dueño define qué temas resuelve el agente solo y cuáles se derivan siempre.
- **Aislamiento entre sub-agentes**: un agente comprometido no contamina el contexto de los demás.
- **Auditoría completa**: toda conversación y toda llamada a herramienta queda registrada.

### 6.3 Protección de datos

- Las conversaciones viven en el servidor de Lumat; la propiedad y la gestión de los datos son del cliente.
- Acceso a conversaciones solo por rol (por ejemplo, un técnico no ve clientes ajenos).
- Auditoría completa de quién hizo qué y cuándo.
- El agente nunca recibe datos de pago.
- La automatización nunca ejecuta código arbitrario: solo configuraciones validadas.
- La retención del historial es responsabilidad de Lumat; corresponde verificar la normativa chilena aplicable (por ejemplo, Ley 19.628) antes de comprometer almacenamiento indefinido.

---

## 7. Plan de pagos

### 7.1 Condiciones vigentes

- **Precio final: USD 2,800**, pagadero en **5 pagos mensuales iguales de USD 560**.
- El precio final incluye un **descuento de ≈7%** (exactamente 6.67%) sobre el precio base de **USD 3,000**.
- **Los pagos son mensuales y NO están asociados a la aprobación o entrega de hitos.** El primer pago se realiza al inicio del proyecto y los siguientes cada 30 días.

| Pago | Momento | Monto |
|------|---------|-------|
| Pago 1 | Al inicio del proyecto | USD 560 |
| Pago 2 | 30 días después del inicio | USD 560 |
| Pago 3 | 60 días después del inicio | USD 560 |
| Pago 4 | 90 días después del inicio | USD 560 |
| Pago 5 | 120 días después del inicio | USD 560 |
| **Total** | **5 pagos mensuales** | **USD 2,800** |

**Notas.**
- **Descuento aplicado:** el precio final de USD 2,800 equivale a un descuento del 6.67% (presentado como ≈7%) sobre el precio base de USD 3,000.
- **Precio base sin descuento:** USD 3,000, en 5 pagos de USD 600, por si se negocia sin descuento.
- Los ajustes o cambios de alcance que excedan lo pactado se evalúan y cotizan por separado.
- **Descuento por continuidad (web M2):** si Lumat contrata la web luego de validar el agente, se mantiene el acuerdo de aplicar un descuento sobre el valor de la web al momento de cotizarla.

---

## 8. Cronograma tentativo

Fechas asumidas con **kickoff el lunes 17 de agosto de 2026**. **Todo el cronograma es tentativo** y se ajusta según la fecha de firma del contrato, el avance del trámite de Meta y los resultados de las pruebas.

| Etapa | Período | Contenido |
|-------|---------|-----------|
| **Construcción** (2 meses) | 17 ago – 16 oct | Desarrollo de los 4 hitos: WhatsApp operativo, arquitectura multiagente + panel, calendario + notificaciones, automatizaciones + reportes |
| **Evaluación, pruebas y puesta en marcha** (2 meses) | 19 oct – 16 dic | Pruebas con número prepago y clientes de prueba controlados, ajustes, capacitación del equipo, migración al número real de WhatsApp y puesta en marcha |
| **Aceptación final** | ~16 dic 2026 | Sistema validado y operativo; inicio de la garantía (60 días corridos) |

**Notas.**
- El plazo total es de **~4 meses**: 2 meses de construcción + 2 meses de evaluación, pruebas y puesta en marcha.
- El cronograma se ajusta a la fecha real de firma del contrato y a la aprobación de la API de Meta, que no depende de HandCodeStudio.
- **Los pagos mensuales son independientes del avance de los hitos**: se mantienen según el calendario de pagos, sin relación con fechas de entrega.

---

## 9. Post-entrega

| Concepto | Detalle |
|----------|---------|
| **Garantía** | 60 días corridos desde la entrega |
| **Soporte mensual** | USD 50-100/mes (mantenimiento, bugs y actualizaciones) |
| **Soporte por evento** | USD 30-50/hora (sin retención mensual) |
| **Web (M2)** | En standby por 3 meses por acuerdo previo, mientras se valida el agente. Se evalúa después de validar el funcionamiento del agente; el sistema podrá integrarse con la web del proveedor que Lumat elija |

---

## 10. Costos operativos a considerar

Costos referenciales de operación mensual una vez en producción, sujetos a las tarifas vigentes de Meta y de los proveedores.

| Concepto | Costo referencial |
|----------|-------------------|
| VPS (Hostinger KVM 2, renovación) | ~US$14.99/mes; alternativa local MOX (Santiago) ~US$18/mes; Hostinger intro ~US$8.79/mes (2 años prepago) |
| Plantillas aprobadas fuera de la ventana de 24 h | ~$0.04-0.08 por mensaje |
| Mensajes de respuesta dentro de la ventana (service messages) | **Gratis hasta el 1 de octubre de 2026**; desde esa fecha Meta los cobra por mensaje entregado (Chile habilitado) |

**Nota sobre los service messages.** Las respuestas que el bot y el equipo envían dentro de la ventana de 24 horas están gratis hasta el **1 de octubre de 2026**; desde esa fecha Meta las cobra por mensaje entregado y Chile está entre los mercados habilitados. Dado que la operación real está prevista para **~diciembre de 2026**, este costo aplica desde el arranque de la operación. Al volumen esperado (decenas de conversaciones diarias), el impacto es bajo, pero conviene conocerlo para planificar el presupuesto mensual.

---

## 11. Compromisos y próximos pasos

### 11.1 Compromisos de HandCodeStudio

- Entregar el sistema por hitos, con un entregable funcional verificable al cierre de cada uno.
- Capacitación remota del equipo de Lumat.
- Soporte dentro del período de garantía (60 días corridos desde la entrega).
- Revisión y ajustes al cierre de cada hito; los cambios de alcance que excedan lo pactado se evalúan y cotizan por separado.

### 11.2 Compromisos de Lumat

| Compromiso | Detalle |
|------------|---------|
| **Contrato firmado** | Incluye la aceptación de esta propuesta y de las condiciones de pago |
| **Pago 1 de USD 560** | Al inicio del proyecto |
| **Trámite de la API de Meta** | Crear la cuenta de negocio, verificar la empresa y registrar el número; se inicia apenas se firme el contrato |
| **Base de conocimiento inicial** | Manuales de fabricantes, procedimientos de Lumat, tarifario y preguntas frecuentes (se puede partir con lo disponible) |
| **Número prepago dedicado** | Comprar y tener disponible el SIM prepago de pruebas |
| **Humano de respaldo** | Una persona de Lumat disponible para atender las derivaciones del bot durante la fase de pruebas (responde desde el panel, sin equipo especial) |
| **Decisiones de operación** | Calendario de trabajo (horarios, zonas, técnicos, reglas), WhatsApp de alertas de emergencia, roles del equipo y política de retención de datos |

### 11.3 Para comenzar

Para dar inicio al proyecto se requiere: **contrato firmado + Pago 1 de USD 560**. Con eso, **el kickoff queda programado para la semana siguiente a la firma**, y Lumat puede comenzar en paralelo el trámite de la API de Meta y la compra del número prepago de pruebas.

---

> Documento preparado por **HandCodeStudio — Stefan Miranda**
> Propuesta final para Lumat (Maximiliano) — 7 de agosto de 2026
> Estatus: propuesta para etapa de contrato
