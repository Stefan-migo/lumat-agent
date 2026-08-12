# Cotización Lumat — Sistema Digital de Atención y Gestión

> Preparado para: **Lumat**  
> Fecha: Julio 2026  
> Documento confidencial

---

## Resumen ejecutivo

Tres milestones progresivos para construir el sistema digital de Lumat: un agente inteligente de atención al cliente y gestión (M1), página web institucional (M2), y catálogo de servicios con agenda, pagos y postventa (M3).

Cada milestone es independiente y puede contratarse por separado. El Milestone 1 se presenta en tres opciones con distinta profundidad tecnológica para que Lumat elija según su presupuesto y plan de crecimiento.

**Stack tecnológico**: VPS propio de Lumat + Docker + PostgreSQL + Python + LangGraph (IA) + Next.js + WhatsApp Cloud API. Sin dependencia de proveedor — los datos y el código quedan bajo control de Lumat.

---

## Milestone 1 — LumatAgent

El M1 es el componente central del sistema: un agente de inteligencia artificial que atiende clientes por WhatsApp, recopila datos, clasifica solicitudes, detecta emergencias, deriva a una persona cuando es necesario y registra toda la actividad.

Se presenta en **tres opciones** según la profundidad arquitectónica y las capacidades futuras.

---

### Opción A — Chatbot IA

| Campo | Información |
|-------|-------------|
| **Alcance** | Bot conversacional con IA vía WhatsApp. Flujo completo: saludo → categorías de atención → captura de datos del cliente → orientación técnica → clasificación → derivación a humano → registro. Incluye base de conocimiento (RAG), detección de emergencias, panel administrativo y exportación de datos. |
| **Exclusiones** | Contenido de la base de conocimiento (lo redacta Lumat), aprobación de Meta WhatsApp Business, diseño gráfico/branding |
| **Entregables** | Bot funcional en WhatsApp productivo, panel administrativo web, base de conocimiento inicial cargada, manual de uso y capacitación |
| **Plazo** | 6 a 8 semanas desde la firma |
| **Costo inicial** | **$1,000 – $1,500 USD** |
| **Costo mensual** | ~$22–59 USD/mes (ver sección Costos Operativos) |
| **Costo variable** | ~$0.001–0.003 por conversación adicional. Templates WhatsApp fuera de ventana 24h: ~$0.04–0.08 |
| **Garantía** | 60 días desde la aceptación |
| **Soporte** | Opcional. Retén mensual $50–100 USD o pago por evento $30–50/hora |
| **Propiedad** | Código, datos, cuentas, y accesos pertenecen a Lumat |
| **Dependencias** | Cuenta de WhatsApp Business (Meta), cuenta OpenAI API, VPS (Hetzner), dominio .cl |

**Componentes incluidos:**

- [x] Bot IA con flujo conversacional completo
- [x] Integración WhatsApp Business Cloud API
- [x] Base de conocimiento con búsqueda inteligente (RAG + pgvector)
- [x] Detección de emergencias + protocolo de seguridad
- [x] Derivación a persona con resumen de la conversación
- [x] Captura estructurada de datos del cliente
- [x] Reconocimiento de clientes existentes por número de teléfono
- [x] Subida y almacenamiento de fotos y audio
- [x] Panel administrativo (login, clientes, conversaciones, estados, exportación)
- [x] Dashboard con indicadores básicos
- [x] Editor de base de conocimiento
- [x] Configuración del bot (tono, reglas, mensajes)

**Nota importante**: Esta opción es la más rápida y económica. Funciona correctamente para atención por WhatsApp. Sin embargo, si en el futuro Lumat desea agregar automatizaciones, agendamiento o que el agente gestione procesos internos, será necesario reestructurar la arquitectura (con costo adicional).

---

### Opción B — Base Multi-Agente + WhatsApp *(Recomendada)*

| Campo | Información |
|-------|-------------|
| **Alcance** | Toda la funcionalidad de la Opción A, **más** la arquitectura completa de LumatAgent: orquestador multi-agente, sistema de roles (dueño, admin, técnico, cliente), herramientas con permisos granulares, auditoría de cada acción, y estructura preparada de los agentes de Calendario, Automatizaciones, Notificaciones y Reportes. Solo el agente de WhatsApp está funcional — los demás existen y pueden activarse sin reescribir código. |
| **Exclusiones** | Mismas que Opción A + automatizaciones y agendamiento no están operativos (solo su estructura base) |
| **Entregables** | Mismos que Opción A + arquitectura multi-agente documentada + estructura de agentes lista para activar |
| **Plazo** | 10 a 12 semanas desde la firma |
| **Costo inicial** | **$1,500 – $2,000 USD** |
| **Costo mensual** | ~$22–59 USD/mes |
| **Costo variable** | Igual que Opción A |
| **Garantía** | 60 días desde la aceptación |
| **Soporte** | Opcional. Retén mensual $50–100 USD o pago por evento $30–50/hora |
| **Propiedad** | Código, datos, cuentas, y accesos pertenecen a Lumat |
| **Dependencias** | Mismas que Opción A |

**Componentes incluidos (todo lo de Opción A más):**

- [x] Arquitectura multi-agente (orquestador + router de agentes especializados)
- [x] Sistema de herramientas con permisos granulares (el agente solo ejecuta acciones autorizadas)
- [x] Sistema de roles completo: dueño, administrador, técnico, cliente
- [x] Registro de auditoría de cada acción del agente
- [x] Agente de Calendario (estructura lista para activar)
- [x] Agente de Automatizaciones (estructura lista para activar)
- [x] Agente de Notificaciones (estructura lista para activar)
- [x] Agente de Reportes (estructura lista para activar)
- [x] Motor de automatizaciones (base lista, sin reglas de negocio configuradas)

**Ventaja clave**: Cuando Lumat quiera agregar agendamiento, automatizaciones o gestión avanzada (M3), no se reescribe nada — solo se implementa la lógica de negocio sobre la arquitectura ya construida. Esta opción es la base para que el agente evolucione de "asistente" a "miembro del equipo".

---

### Opción C — LumatAgent Completo

| Campo | Información |
|-------|-------------|
| **Alcance** | Todo lo de la Opción B, **más** todos los agentes plenamente funcionales: el dueño puede crear automatizaciones en lenguaje natural ("cuando un servicio termine, enviá seguimiento en 3 días"), el sistema agenda visitas y sincroniza con calendarios (iPhone y Google Calendar), envía notificaciones y recordatorios automáticos, y genera reportes de gestión. El agente se convierte en un coworker digital que entiende procesos de negocio. |
| **Exclusiones** | Mismas que Opción B |
| **Entregables** | Mismos que Opción B + todos los agentes operativos + panel de automatizaciones + vista de agenda + manual de automatizaciones |
| **Plazo** | 14 a 18 semanas desde la firma |
| **Costo inicial** | **$2,300 – $3,000 USD** |
| **Costo mensual** | ~$22–59 USD/mes |
| **Costo variable** | Igual que Opción A |
| **Garantía** | 60 días desde la aceptación |
| **Soporte** | Opcional. Retén mensual $50–100 USD o pago por evento $30–50/hora |
| **Propiedad** | Código, datos, cuentas, y accesos pertenecen a Lumat |
| **Dependencias** | Mismas que Opción A + cuenta Google Calendar (para sincronización) |

**Componentes incluidos (todo lo de Opción B más):**

- [x] Agente de Automatizaciones funcional — el dueño crea reglas en lenguaje natural
- [x] Agente de Calendario funcional — integración con iPhone Calendar (CalDAV) y Google Calendar
- [x] Agente de Notificaciones funcional — recordatorios, seguimientos, alertas
- [x] Agente de Reportes funcional — KPIs, resúmenes, exportaciones
- [x] Panel de automatizaciones (ver, editar, activar/desactivar reglas)
- [x] Vista de agenda en panel admin (disponibilidad, asignación de técnicos)

**Nota**: Con esta opción, Lumat obtiene desde el día 1 un sistema que no solo atiende clientes, sino que gestiona activamente el negocio. El dueño puede delegar tareas operativas al agente y concentrarse en hacer crecer la empresa.

---

### 📊 ¿Chatbot o LumatAgent? — Qué resuelve cada uno

El chatbot (Opción A) y el LumatAgent (Opciones B y C) no compiten entre sí: resuelven **problemas diferentes**. La pregunta no es "¿cuál es mejor?", sino **"¿qué necesita Lumat hoy y qué va a necesitar mañana?"**.

---

#### 🔹 Chatbot (Opción A) — El asistente que nunca duerme

Resuelve problemas **operativos inmediatos** de atención al cliente:

| Problema de Lumat | Cómo lo resuelve el Chatbot |
|---|---|
| *"Perdemos clientes porque no siempre podemos contestar"* | El bot responde **24/7**, incluso fuera de horario laboral. Cada mensaje recibe una respuesta inmediata. |
| *"Cada vez que un cliente escribe, tengo que pedirle los mismos datos otra vez"* | El bot **captura todos los datos de forma estructurada**: nombre, teléfono, dirección, tipo de equipo, problema. Quedan registrados desde el primer contacto. |
| *"A veces se me pasan mensajes o los pierdo en el historial de WhatsApp"* | **Cada conversación queda guardada** en el panel administrativo. Buscable por cliente, estado, fecha. Nada se pierde. |
| *"Me da miedo que un cliente reporte una fuga de gas y no me entere a tiempo"* | El bot **detecta emergencias automáticamente** (gas, fuga, incendio) y notifica al equipo de inmediato con instrucciones de seguridad. |
| *"Cuando derivo un cliente a un técnico, el técnico no tiene contexto de lo que ya hablamos"* | Al derivar, el bot **genera un resumen automático** de toda la conversación. El técnico lee eso y ya sabe todo. |
| *"No sé cuántos clientes nos contactan, por qué motivo, ni cuántos se convierten"* | El panel administrativo tiene **indicadores básicos**: contactos recibidos, motivos principales, casos derivados, solicitudes de visita. |

**Ideal si**: Lumat solo necesita atender mejor a sus clientes por WhatsApp **hoy**.

---

#### 🟦 LumatAgent (Opciones B y C) — El miembro del equipo

Resuelve problemas **de gestión y crecimiento** del negocio:

| Problema de Lumat | Cómo lo resuelve el LumatAgent |
|---|---|
| *"Quiero crecer contratando más técnicos, pero no tengo tiempo para gestionarlos"* | El agente **organiza la agenda de cada técnico**, asigna visitas, previene dobles reservas y notifica cambios. Escalar el equipo no escala el caos. |
| *"Los clientes quedan contentos con la visita, pero después no les hacemos seguimiento"* | El dueño puede decirle al agente: *"cuando un servicio termine, enviá un WhatsApp 3 días después preguntando cómo le fue"*. El agente **crea la automatización y la ejecuta siempre**. |
| *"Pierdo tiempo todos los días coordinando horarios, confirmando y reprogramando"* | El agente maneja **confirmaciones, recordatorios, reprogramaciones y cancelaciones** automáticamente. El cliente agenda desde la web y todo se sincroniza. |
| *"Uso el calendario del iPhone para todo, no quiero aprender otra herramienta"* | El agente se sincroniza **directamente con el calendario de iPhone** (CalDAV) y con Google Calendar. El dueño sigue usando la herramienta que ya conoce. |
| *"No sé cómo va el negocio — ¿cuánto facturamos esta semana? ¿cuál es el técnico con más visitas?"* | El agente genera **reportes y KPIs**: ingresos, visitas por técnico, servicios más solicitados. El dueño pregunta en lenguaje natural y el agente responde. |
| *"Tengo ideas de procesos que quiero automatizar, pero no sé programar ni tengo tiempo"* | El dueño **describe el proceso en lenguaje natural** y el agente lo convierte en una automatización. Sin código, sin depender de un programador. |
| *"Hoy crecemos por boca a boca. Necesito que el sistema me acompañe cuando crezcamos"* | La arquitectura multi-agente está **diseñada para crecer**. Agregar más técnicos, más servicios, o más integraciones no requiere reescribir el sistema. |

**Ideal si**: Lumat quiere que la tecnología no solo atienda clientes, sino que **gestione el negocio** y libere al dueño para hacerlo crecer.

---

#### Comparativa funcional

| Aspecto | A — Chatbot | B — Multi-Agente | C — Completo |
|---|---|---|---|
| WhatsApp funcional | ✅ | ✅ | ✅ |
| Panel admin | ✅ | ✅ | ✅ |
| Arquitectura multi-agente | ❌ | ✅ | ✅ |
| Roles (dueño/admin/técnico) | Básico | Completo | Completo |
| Automatizaciones | ❌ | ❌ (estructura) | ✅ |
| Calendario + Agenda | ❌ | ❌ (estructura) | ✅ |
| Dueño crea procesos en lenguaje natural | ❌ | ❌ | ✅ |
| Preparado para M3 sin refactor | 🔴 No | 🟢 Sí | 🟢 Sí |
| Plazo | 6–8 sem | 10–12 sem | 14–18 sem |
| **Precio** | **$1,000–$1,500** | **$1,500–$2,000** | **$2,300–$3,000** |

---

## Milestone 2 — Página Web Lumat

| Campo | Información |
|-------|-------------|
| **Alcance** | Sitio web profesional, responsive (computador, tablet, celular), orientado a presentar los servicios de Lumat, generar contactos y conectar clientes con el Bot IA y WhatsApp. Incluye CMS simple para que Lumat edite contenidos sin depender del programador. |
| **Exclusiones** | Redacción de textos institucionales, fotografía profesional, diseño de marca/logo, publicidad online, gestión de campañas |
| **Entregables** | Sitio web publicado en dominio propio, diseño responsive, formulario de contacto funcional, integración con WhatsApp y Bot IA, panel de edición de contenidos |
| **Plazo** | 3 a 4 semanas (puede solaparse con M1) |
| **Costo inicial** | **$800 – $1,200 USD** |
| **Costo mensual** | ~$1 USD/mes (dominio .cl). El servidor ya está cubierto en M1. |
| **Costo variable** | Ninguno |
| **Garantía** | 60 días desde la aceptación |
| **Soporte** | Opcional. Retén mensual o pago por evento (ver sección Soporte) |
| **Propiedad** | Código, dominio y datos pertenecen a Lumat |
| **Dependencias** | Dominio .cl, VPS (el mismo de M1) |

**Secciones incluidas:**

- [x] Inicio con propuesta de valor y llamados a la acción
- [x] Presentación de Lumat
- [x] Servicios: calefont, calderas, calefacción
- [x] Cobertura geográfica
- [x] Preguntas frecuentes
- [x] Formulario de contacto con carga de fotografías
- [x] Botón flotante de WhatsApp + botón de llamada
- [x] Acceso visible al Bot IA
- [x] CMS simple para editar textos, imágenes y servicios
- [x] SEO básico (meta tags, sitemap, estructura semántica)
- [x] SSL + certificado de seguridad
- [x] Google Analytics
- [x] Política de privacidad y tratamiento de datos

---

## Milestone 3 — Catálogo, Agenda, Pagos y Postventa

| Campo | Información |
|-------|-------------|
| **Alcance** | Completar la operación digital de Lumat: catálogo detallado de servicios, sistema de agendamiento de visitas con asignación de técnicos, integración con Google Calendar, pagos en línea (tarjeta, transferencia, efectivo), seguimiento postventa, garantías y notificaciones automáticas. |
| **Exclusiones** | Facturación electrónica SII, inventario de repuestos, app móvil nativa, CRM avanzado, reportes personalizados complejos |
| **Entregables** | Catálogo de servicios online, agenda funcional con técnicos, sistema de pagos operativo, módulo de postventa, panel administrativo ampliado |
| **Plazo** | 6 a 8 semanas (después de M1) |
| **Costo inicial** | **$1,500 – $2,000 USD** |
| **Costo mensual** | ~$22–59 USD/mes (misma infraestructura que M1) |
| **Costo variable** | Comisión de pasarela de pago (Transbank/Webpay): ~2-4% por transacción |
| **Garantía** | 60 días desde la aceptación |
| **Soporte** | Opcional. Retén mensual o pago por evento |
| **Propiedad** | Código y datos pertenecen a Lumat |
| **Dependencias** | Google Calendar, pasarela de pagos (Transbank o Webpay) |

**Componentes incluidos:**

**Catálogo de servicios**
- [x] Listado completo de servicios de calefont, calderas y calefacción
- [x] Cada servicio con: nombre, descripción, problemas que resuelve, botón de contacto y opción de agendar

**Agendamiento**
- [x] Calendario con bloques de 1 hora para visitas técnicas
- [x] Disponibilidad por técnico y asignación manual o automática
- [x] Prevención de reservas dobles
- [x] Bloqueo manual de horarios
- [x] Sincronización con Google Calendar
- [x] Confirmaciones y recordatorios por WhatsApp y correo
- [x] Reprogramación y cancelación desde el panel
- [x] Registro del servicio en la ficha del cliente

**Pagos**
- [x] Pago con tarjeta de débito y crédito (Transbank/Webpay)
- [x] Registro manual de transferencia bancaria
- [x] Registro manual de efectivo
- [x] Vinculación automática del pago con el cliente y la visita
- [x] Confirmación y comprobante para el cliente
- [x] Estados: pendiente, pagado, anulado, reembolsado
- [x] Panel de revisión de pagos

**Postventa y automatizaciones**
- [x] Registro y seguimiento de reclamos y garantías
- [x] Estados de postventa (abierto, en revisión, resuelto, cerrado)
- [x] Notificaciones automáticas: nuevas solicitudes, reservas, cancelaciones, pagos, emergencias
- [x] Recordatorios de visita (24h antes)
- [x] Solicitud de evaluación post-servicio
- [x] Resumen diario o semanal para administración

---

## 📊 Resumen de inversión

| Milestone | Precio |
|-----------|--------|
| **M1 — LumatAgent** | |
| &nbsp;&nbsp;&nbsp;&nbsp;Opción A — Chatbot | **$1,000 – $1,500** |
| &nbsp;&nbsp;&nbsp;&nbsp;Opción B — Multi-Agente + WhatsApp | **$1,500 – $2,000** |
| &nbsp;&nbsp;&nbsp;&nbsp;Opción C — LumatAgent Completo | **$2,300 – $3,000** |
| **M2 — Página Web** | **$800 – $1,200** |
| **M3 — Agenda, Pagos y Postventa** | **$1,500 – $2,000** |

| Combinación recomendada | Total |
|--------------------------|-------|
| M1 Opción A + M2 + M3 | **$3,300 – $4,700** |
| M1 Opción B + M2 + M3 *(recomendado)* | **$3,800 – $5,200** |
| M1 Opción C + M2 + M3 | **$4,600 – $6,200** |

---

## Costos Operativos Mensuales

### Infraestructura y servicios

| Concepto | Costo |
|----------|-------|
| VPS Hetzner (4 vCPU, 8GB RAM) | ~$9 USD/mes |
| OpenAI API (GPT-4o-mini, ~100 conversaciones/día) | ~$6 USD/mes |
| Embeddings para base de conocimiento (RAG) | ~$1 USD/mes |
| WhatsApp Business API | ~$5 USD/mes |
| Dominio .cl | ~$1 USD/mes |
| Email transaccional | $0 /mes (plan gratuito) |
| Monitoreo de disponibilidad | $0 /mes |
| **Total operación mensual** | **~$22 USD/mes** |

### Escenarios por volumen de uso

| Volumen | Costo estimado |
|---------|----------------|
| Bajo (~100 conversaciones/día) | **~$22 USD/mes** |
| Medio (~300 conversaciones/día) | **~$41 USD/mes** |
| Alto (~500+ conversaciones/día) | **~$59 USD/mes** |

### Soporte y mantenimiento (opcional)

| Modalidad | Costo | Descripción |
|-----------|-------|-------------|
| Retén mensual | $50–100 USD/mes | Corrección de bugs, actualizaciones, backups, revisiones periódicas |
| Pago por evento | $30–50 USD/hora | Solo cuando se requiere una intervención específica |

---

## Propiedad y Continuidad

| Aspecto | Condición |
|---------|-----------|
| **Código fuente** | 100% propiedad de Lumat. Se entrega repositorio completo. |
| **Base de datos** | Propiedad de Lumat. Acceso administrativo total. |
| **Dominio** | A nombre de Lumat, pagado por Lumat. |
| **Número WhatsApp** | A nombre de Lumat (cuenta de Meta). |
| **Cuentas externas** | OpenAI, Meta, Google, VPS — a nombre de Lumat. Configuramos y entregamos accesos. |
| **Migración a otro proveedor** | Otro programador puede continuar el proyecto. Se entrega documentación técnica completa. |
| **Cese de servicios** | Si se deja de pagar el servidor, el sistema deja de funcionar. Los datos no se pierden (backups automáticos). |
| **Respaldo** | Backups automáticos diarios. Procedimiento de recuperación documentado. |
| **Protección de datos** | Datos personales en servidor propio. Conexiones HTTPS. Acceso restringido por roles. |

---

## Términos y Condiciones

### Forma de pago

- **30% al inicio** de cada milestone
- **40% a mitad del milestone** (contra entregable parcial)
- **30% contra entrega y aceptación final**

### Plazos

- Comienzan desde la firma del acuerdo y recepción del primer pago
- Se extienden si Lumat no entrega contenidos, aprobaciones o respuestas en más de 5 días hábiles

### Garantía

- **60 días corridos** desde la aceptación de cada milestone
- **Cubre**: errores de funcionamiento, bugs, desviaciones del alcance acordado
- **No cubre**: cambios de alcance, contenido nuevo, modificaciones no acordadas, intervención de terceros, caídas de servicios externos (OpenAI, WhatsApp, VPS)
- **Tiempo de respuesta**: críticos ≤24h hábiles / menores ≤72h hábiles

### Principales exclusiones

| # | Exclusión |
|---|-----------|
| 1 | Contenido de base de conocimiento — lo redacta Lumat |
| 2 | Aprobación de Meta WhatsApp — depende de Meta, se re-aplica sin costo si hay rechazo |
| 3 | Cuentas de terceros — OpenAI, Meta, Google, dominio y VPS a nombre y costo de Lumat |
| 4 | Diseño gráfico / branding — se entrega con diseño limpio profesional |
| 5 | App móvil nativa — todo es web responsive + WhatsApp |
| 6 | Facturación electrónica SII — registro de pagos sí, emisión de facturas oficiales no |
| 7 | Inventario de repuestos — no incluido |
| 8 | Migración de datos existentes — se cotiza aparte según volumen |
| 9 | Capacitación presencial — manual + capacitación remota incluida |
| 10 | Cambios de alcance — se cotizan como extra |
| 11 | Publicidad online (Google Ads / Meta Ads) — solo analítica, no gestión de campañas |

---

## Próximos pasos

1. Lumat elige la opción de M1 que mejor se ajuste a su presupuesto y visión
2. Definimos fecha de inicio para el milestone seleccionado
3. Lumat entrega los contenidos iniciales (información de servicios, base de conocimiento básica)
4. Configuramos las cuentas necesarias (WhatsApp Business, OpenAI, VPS, dominio)

---

> *"El objetivo no es solo construir tecnología: es darle a Lumat un sistema que le permita crecer sin perder la calidad de atención que sus clientes ya conocen."*
