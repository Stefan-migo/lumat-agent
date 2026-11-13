# Integración 2Workers × Lumat — Roadmap

> **Estado:** evaluación, sin implementación. Ninguna fase ha comenzado.
> **Fecha:** 2026-11-06
> **Documento hermano:** [fase-0-descubrimiento.md](fase-0-descubrimiento.md)

---

## 1. Resumen ejecutivo

Lumat contrató 2Workers para la gestión de su empresa y quiere conectar el chatbot a esa
plataforma. La intención original era trasladar la gestión de clientes, horarios y técnicos.

La conclusión de este análisis es que **sí conviene integrar, pero no ceder la propiedad de todo**.
2Workers resuelve bien la ejecución en terreno (app del técnico, check-in con GPS, fotos, firma,
cierre de visita). No resuelve el cálculo de horarios, porque su API no expone disponibilidad.

La recomendación es un **híbrido con espejo local**: 2Workers es dueño de la operación de campo,
Lumat sigue siendo dueño de la conversación y del cálculo de cupos, y el panel guarda una copia
local de lo que dice 2Workers para no depender de la red en el camino crítico del chatbot.

Alcance estimado: **36 días de desarrollo** (más 3 de descubrimiento), en 3 fases entregables.

---

## 2. Qué es 2Workers

`api.2workers.me/v2` es la API de **Auvo**, una plataforma de gestión de servicios en terreno
(FSM). El contrato es el mismo que `api.auvo.com.br/v2`; el propio blueprint manda el soporte a
`help@auvo.com.br` y la app en App Store está publicada por *Auvo Tecnologia Ltda*.

Esto importa por una razón práctica: **el contrato no lo negocia Lumat**. Lo fija un tercero, y
puede cambiarlo. Ese riesgo es parte del presupuesto.

## 3. Qué expone la API

| Recurso | Métodos | Uso |
|---|---|---|
| `/login` | GET, POST | Bearer token, **válido 30 minutos** |
| `/customers` | GET, POST, PUT, PATCH, DELETE | Clientes. `PUT` es upsert por `id` **o `externalId`** |
| `/customerGroups` | GET, POST, DELETE | Agrupaciones de clientes |
| `/users` | GET, POST, PUT, PATCH, DELETE | Técnicos, jornada semanal, base de operaciones |
| `/teams` | GET, POST | Equipos y participantes |
| `/tasks` | GET, POST, PUT, PATCH, DELETE | Visitas (la orden de trabajo) |
| `/taskTypes` | GET, POST, PATCH, DELETE | Tipos de servicio, con `standardTime` |
| `/tickets` | GET, POST | Tickets de soporte |
| `/webHooks` | GET, POST, DELETE | Eventos salientes |
| `/equipments`, `/equipmentCategories` | CRUD parcial | Activos del cliente |
| `/products`, `/quotations`, `/segments`, `/keywords`, `/expenses` | lectura y algo de escritura | Catálogo, presupuestos, segmentos |
| `/gps`, `/satisfactionSurveys` | solo lectura | Posiciones, encuestas |

### Lo que no existe

Esto define el alcance completo del proyecto:

- **No hay endpoint de disponibilidad, agenda, slots ni calendario.** El agendamiento es un campo:
  `taskDate` (datetime sin offset) + `idUserTo` (técnico) + `teamId`.
- **No hay endpoint de ausencias, vacaciones, bloqueos ni feriados.** Solo el patrón semanal del
  usuario: `workDaysOfWeek`, `startWorkHour`, `endWorkHour`, `startLunchHour`, `endLunchHour`,
  `unavailableForTasks`, `BasePoint`.
- **No hay duración por tarea.** La duración sale de `taskTypes.standardTime`.
- **No hay reasignación ni optimización de rutas expuestas.** Viven en el motor de Auvo, detrás de
  la interfaz, no en el contrato.
- **Webhooks solo de tres entidades**: `User`(1), `Task`(4), `Customer`(7) ×
  `Inclusao`/`Alteracao`/`Exclusao`. Nada de equipos ni de disponibilidad.
- En el blueprint público **no aparecen** `/services`, `/invoices`, `/receivables` ni `/routes`,
  aunque el sitio de Auvo los menciona. Verificar en F0.

**Traducción:** 2Workers permite escribir y leer la agenda resultante. No permite preguntarle si hay
hueco. La pregunta "¿qué horarios tienes libres el jueves?" no se puede delegar.

---

## 4. Qué tiene Lumat hoy

El activo que hay que proteger:

| Componente | Dónde | Qué hace |
|---|---|---|
| `Customer`, `Case`, `CustomerEquipment`, `CustomerNote` | `app/models.py` | Ficha del cliente, casos, equipos, notas internas |
| `Appointment` | `app/models.py` | Visita con `local_start` + `timezone` + `starts_at` UTC + `duration_minutes` + historial |
| `TechnicianWeeklySchedule`, `TechnicianAvailability` | `app/models.py` | Jornada semanal y bloques materializados |
| `app/services/scheduling.py` | 589 líneas | `open_slots`, `open_slots_for_assignment`, `book`, `reschedule`, `cancel`, `close`. Balanceo por carga diaria, rotación, ventana de negocio, lead time |
| `app/chat/nodes/booking.py` | ~400 líneas | Oferta determinista de 3 cupos, universo congelado de 30, TTL de 30 min, paginación, fallback a 7 días |
| `app/services/calendar.py` | 80 líneas | Patrón adaptador de proveedor externo + tabla de estado de sincronización |
| `app/services/events.py` + `app/ops/worker.py` | — | Outbox transaccional con lease, reintentos y backoff |
| Panel técnico | `app/panel/api/routes/technician.py` + 2 pantallas | Agenda, en ruta, llegó, cerrar |

Dos detalles que sostienen la recomendación:

1. `booking.py:214` llama a `technician_schedule.ensure_horizon()` **antes** de ofrecer cupos.
   Materializa la jornada semanal local en `technician_availability`. Si esa información viviera
   solo en 2Workers, ofrecer horarios en el chat exigiría una llamada de red y un token vigente en
   cada turno de conversación.
2. `calendar.py` ya es un adaptador de proveedor externo con `idempotency_key`, `status`,
   `attempts` y `error`. Es el molde exacto para esta integración.

---

## 5. Arquitectura recomendada: híbrido con espejo local

**Un dueño por campo.** Ningún campo se edita libremente en ambos lados.

| Dato | Dueño | Dirección | Mecanismo |
|---|---|---|---|
| Cliente (nombre, dirección, contacto) | Ambos | **Bidireccional** | `PUT /customers/` con `externalId` |
| Visita (fecha, técnico, dirección, estado) | Lumat | Lumat → 2Workers | Outbox `DomainEvent` → `POST/PATCH /tasks` |
| Técnico (alta, datos, jornada semanal) | 2Workers | 2Workers → Lumat | Sincronización periódica + webhook `User/*` |
| Estado de visita (llegó, cerró, informe) | 2Workers | 2Workers → Lumat | Webhook `Task/*` |
| Cálculo de cupos, ventana de negocio, cobertura, precios | Lumat | — | Se queda donde está |

### Por qué el espejo y no lectura directa

El panel guarda una copia local de lo que dice 2Workers. El chatbot lee local. La API se consulta en
segundo plano.

Si el chatbot leyera directo de 2Workers:

- un token vencido o una caída de Auvo a las 21:00 deja al bot sin poder agendar;
- cada oferta de horarios suma latencia de red desde Santiago a Brasil;
- el turno de conversación depende de un servicio que no controlamos.

Con espejo local, el chat sigue funcionando y solo se atrasa la sincronización.

### Lo que el espejo no resuelve

Sigue habiendo dos agendas. Alguien puede mover una tarea en la interfaz de 2Workers y el panel
enterarse unos minutos después. Por eso la fase de visitas incluye un **cruce de ocupación**: los
cupos que ofrece el bot se calculan sobre la unión de `appointments` de Lumat y `tasks` de 2Workers.
Ese cruce es lo que evita la doble reserva.

---

## 6. Fases

### F0 — Descubrimiento y verificación (3 días)

Documento separado: [fase-0-descubrimiento.md](fase-0-descubrimiento.md).

Compuerta del proyecto. Convierte el rango de días en una cifra firme. Sin código de producción.

### F1 — Adaptador base y técnicos (12 días)

**Adaptador (3 días)**

- `app/services/twoworkers/` con `client.py`, `auth.py`, `mapping.py`, `errors.py`.
- Caché de token con renovación proactiva (vida útil 30 minutos).
- Timeout, reintentos y clasificación de errores.
- Credenciales en `panel_secrets`, cifradas con `app/services/crypto.py`.
- Flag de activación en settings y un botón "probar conexión" en Configuración.

**Técnicos (9 días)**

- Sincronización `2Workers → Lumat`: alta, baja, datos de contacto, `unavailableForTasks`.
- Jornada semanal: `workDaysOfWeek` + horas + almuerzo → `TechnicianWeeklySchedule`, y
  materialización a `TechnicianAvailability`.
- `SettingsTechnicians` pasa a **solo lectura**: se consulta desde el panel, se edita en 2Workers.
- `TechnicianAgenda` se reduce a un enlace a la app de 2Workers para el técnico.
- Un técnico sin espejo local no recibe visitas: regla explícita y testeada.

**Entregable visible:** los técnicos de Lumat administran su día desde la app de 2Workers, y el
panel los refleja.

### F2 — Clientes y visitas (12 días)

**Clientes (4 días)**

- `customers` → `PUT /customers/` con `externalId = customer.id`.
- Webhook `Customer/*` → reconciliación.
- Reglas de merge explícitas: `phone_e164` único de Lumat contra `phoneNumber` array de 2Workers.

**Visitas (8 días)**

- `book`, `reschedule`, `cancel`, `close` publican `DomainEvent`, no hacen HTTP.
- `app/ops/worker.py` ejecuta el push con idempotencia por `externalId = appointment.id`.
- Tabla de estado de sincronización siguiendo el molde de `AppointmentCalendarSync`.
- **Cruce de ocupación**: los cupos se calculan sobre la unión de `appointments` + `tasks`.
- Manejo de zona horaria explícito: `taskDate` no lleva offset, la zona de la cuenta se fija y se
  prueba contra el cambio de hora chileno.

**Entregable visible:** cada visita agendada por el chatbot aparece en 2Workers como tarea asignada
al técnico correcto.

### F3 — Estados de vuelta, notificaciones y panel (12 días)

**Estados de vuelta (5 días)**

- Webhook `Task/Inclusao|Alteracao|Exclusao` → `technician_state`, check-in, check-out, informe.
- Idempotencia por `EntityId + Date`, verificación de origen.
- Mapeo explícito del enum pobre de `taskStatus` a `AppointmentStatus`.
- Una tarea creada en la interfaz de 2Workers sin `externalId` se importa como visita externa y
  **bloquea el cupo**.

**Doble notificación al cliente (3 días)**

2Workers ya notifica en check-in, check-out y reprogramación. Si Lumat mantiene sus plantillas, el
cliente recibe dos mensajes por la misma visita. Decidir quién notifica y apagar el otro.

**Panel y cierre (4 días)**

- Enlace a `taskUrl` en el detalle de la visita.
- Estado de sincronización visible y botón "reintentar".
- Aviso cuando una visita no pudo empujarse.
- Plan de corte: qué pasa con las visitas ya agendadas el día que se conecta.

---

## 7. Cronograma y presupuesto

Tarifa de referencia: **CLP 320.000 por día de desarrollo**. Ajustar a la tarifa real antes de
enviar.

| Fase | Días | Precio |
|---|---:|---:|
| F1 — Adaptador base y técnicos | 12 | CLP 3.850.000 |
| F2 — Clientes y visitas | 12 | CLP 3.850.000 |
| F3 — Estados, notificaciones y panel | 12 | CLP 3.850.000 |
| **Subtotal construcción (M4)** | **36** | **CLP 11.550.000** |
| Contingencia (18%) | — | CLP 2.080.000 |
| **Total M4** | — | **CLP 13.630.000** |
| F0 — Descubrimiento (fase independiente) | 3 | CLP 950.000 |
| **Total del proyecto** | **39** | **CLP 14.580.000** |

### Sensibilidad a la tarifa

| Día | Construcción (36 d) | +18% | Total M4 | + F0 | **Total proyecto** |
|---|---:|---:|---:|---:|---:|
| CLP 250.000 | 9.000.000 | 1.620.000 | 10.620.000 | 950.000 | **CLP 11.570.000** |
| CLP 320.000 | 11.520.000 | 2.074.000 | 13.590.000 | 950.000 | **CLP 14.540.000** |
| CLP 400.000 | 14.400.000 | 2.592.000 | 16.990.000 | 950.000 | **CLP 17.940.000** |

Rango total del proyecto (incluida F0): **CLP 11.500.000 – 18.000.000**.

Referencia de mercado: una agencia chilena cotiza este alcance a CLP 450.000–550.000 por día, es
decir CLP 16–20 millones.

### Venta en dos tramos

| Tramo | Contenido | Precio |
|---|---|---:|
| Entrada | F0 + F1 (15 días) | **CLP 4.800.000** |
| Continuación | F2 + F3 (24 días) | **CLP 7.700.000** |
| Contingencia | Se activa por escrito solo si se materializa un bloqueo externo | CLP 2.080.000 |
| Retainer mensual | Monitoreo, cambios de contrato de Auvo, credenciales, incidentes. 5-6 horas incluidas | **CLP 180.000 – 250.000** |

**Piso: CLP 8.500.000** por el híbrido completo. Bajo esa cifra el retainer deja de ser defendible
y el primer cambio de Auvo se trabaja a pérdida.

### Por qué F0 se cobra y va separado

Produce un informe que el cliente conserva aunque decida no continuar. Es el mapa de su propia
plataforma, y es lo que permite firmar el resto con cifras en vez de con supuestos.

---

## 8. Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| **Doble notificación al cliente** | Dos WhatsApp por la misma visita. La integración empeora la experiencia | Decidir el dueño de la notificación en F0 y apagar el otro en F3 |
| **Doble reserva** | El supervisor agenda en 2Workers mientras el bot ofrece cupos | Cruce de ocupación en F2: unión de `appointments` + `tasks` |
| **Zona horaria** | `taskDate` sin offset; el cambio de hora chileno mueve visitas una hora | Fijar zona de la cuenta, conversión explícita, test en el borde de septiembre |
| **Coordenadas** | `latitude`/`longitude` aparecen como requeridas; `Customer.address` es texto libre sin coordenadas | Verificar en F0 si 2Workers geocodifica. Si no, sumar geocoding (3-4 días) |
| **Webhooks sin firma** | El blueprint no documenta firma ni reintentos | Idempotencia propia y allowlist de origen |
| **Inconsistencias del contrato** | `priority` y `checkinType` vuelven como string en Task y como número en listados; `latitude` declarada `integer` con ejemplos float | Parser tolerante a ambos tipos, con tests |
| **`PATCH` es JSON Patch** | Mandar un objeto parcial devuelve 400, no un merge | Usar RFC 6902 correctamente; el ejemplo del doc tiene un typo |
| **Cambio de contrato de Auvo** | Rompe la integración sin aviso | Retainer mensual, monitoreo, tests de contrato |
| **Riesgo político** | El técnico usa 2Workers y el panel muestra otra cosa; el dueño deja de confiar en el panel | Reconciliación visible, no silenciosa |

---

## 9. Exclusiones

- Migración del histórico de clientes a 2Workers (proyecto aparte, ~1 semana).
- Cualquier cambio del lado de Auvo o de su plan contratado.
- Plantillas de WhatsApp nuevas si el corte de notificaciones las requiere.
- Capacitación al equipo de Lumat.
- Soporte fuera de horario (contrato distinto).
- Escritura en 2Workers de cotizaciones, facturas o gastos.

**Regla de seguridad:** Lumat nunca borra registros en 2Workers. Cancelar y cerrar, sí. `DELETE`,
no.

---

## 10. Decisiones pendientes del cliente

1. ¿Los técnicos se crean en 2Workers o en el panel? (recomendado: en 2Workers)
2. ¿Quién manda el WhatsApp al cliente en check-in, check-out y reprogramación?
3. ¿Se migra el histórico de clientes, y cuántos son?
4. ¿Qué pasa con las visitas ya agendadas el día del corte?
5. ¿El supervisor entra a 2Workers o solo al panel?
6. ¿Quién administra los feriados chilenos?
7. ¿Se entrega un usuario admin dedicado a la integración, separado del usuario del dueño?

---

## 11. Criterios de aceptación por fase

| Fase | Se considera entregada cuando |
|---|---|
| F0 | El cliente recibe el informe, firma las decisiones de negocio y las credenciales quedan registradas |
| F1 | El panel muestra los técnicos sincronizados desde 2Workers, la jornada semanal coincide, y una visita asignada desde el panel aparece en la app del técnico |
| F2 | Una visita agendada por el chatbot aparece en 2Workers con el técnico correcto y la hora correcta, incluyendo el borde de cambio de hora |
| F3 | Un check-out en la app del técnico se refleja en el panel en menos de un minuto, el cliente recibe **un** solo mensaje, y el corte está ejecutado |

---

## 12. Próximo paso

Enviar F0. Es la fase más barata, la de menor riesgo, y la que habilita todo lo demás con cifras
firmes en lugar de rangos.
