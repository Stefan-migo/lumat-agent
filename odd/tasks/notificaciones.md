# ODD: notificaciones

**Branch**: `odd/notificaciones` · **Worktree**: `../lumat-agent-odd-notificaciones`
**Base**: `main` @ `a9670c92` · **Status**: in progress

## Objective

Que una notificación del panel lleve a donde corresponde, que su estado se actualice solo, y que le
llegue a quien tiene que atenderla — no sólo a los admins.

## Specs

- **S1** (auditoría de la que sale todo esto, no normativa) El click no navega porque
  `PanelNotification` no guarda destino (`app/models.py:979-991`, `serializers.py:473-480`) y el código
  lo dice: «PanelNotification has no destination entity id; rows intentionally do not navigate»
  (`web/src/components/domain/PanelShell.tsx:640`). «Marcar todas» sólo actualiza la copia de
  `AppShell` (`AppShell.tsx:164-169`); el centro tiene su propio fetch y sólo refresca al cambiar el
  filtro (`NotificationCenter.tsx:44`).

- **S2** Una visita agendada, cancelada, reagendada o no realizada notifica a **todos los usuarios con
  rol `ADMIN`** más el **`Appointment.technician_id` de esa visita**. Una sola fila de panel por
  usuario: si el técnico además es admin, no recibe dos.

- **S3** Una emergencia del chat notifica a todos los `ADMIN` más el **`Conversation.responsible_id`
  de la conversación que la originó**. Si la conversación no tiene responsable, sólo los admins.

- **S4** Una alerta de costo y un fallo permanente de notificación siguen siendo **sólo de admins**.

- **S5** Las notificaciones leen la asignación que el panel **ya tenía**: `Conversation.responsible_id`
  y `Case.responsible_id`, con su endpoint, sus reglas de operador y su auditoría. **No se agrega
  ninguna columna ni migración**: un segundo concepto de propiedad junto al existente es un defecto,
  no una mejora heredada.

- **S6** Esta unidad **no emite** un aviso nuevo al asignar una conversación o un caso. Deja el dato y
  la regla probados; el aviso es producto nuevo y no fue pedido.

- **S7** `GET /panel/api/notification-operations` y `POST /panel/api/notification-operations/{id}/retry`
  exigen rol admin (`require_admin_json`). El listado se pagina: `limit` con default 50 y máximo 200,
  más `offset`.

- **S8** Guardar una suscripción push cuyo `endpoint` ya pertenece a otro usuario responde **409** con
  un código explícito y **no** reasigna `user_id`. Un endpoint nunca cambia de dueño por el solo hecho
  de guardarlo.

- **S9** El payload de una notificación expone `source_entity` y `source_id` de su operación. El
  frontend navega a las entidades conocidas y no navega para el resto. **Sin migración ni backfill**:
  las filas viejas también navegan porque el dato ya existía en la operación.

- **S10** Un click en una notificación —en el popover y en el centro— **navega y la marca leída** en el
  mismo gesto, y el estado se refleja en los dos lugares.

- **S11** Hay **una sola fuente de verdad** del estado de notificaciones para badge, popover y centro.
  «Marcar todas como leídas» actualiza los tres de inmediato; un fallo del POST se muestra y revierte;
  mientras corre hay estado pendiente que impide el doble click; se re-consulta la lista ante un evento
  realtime (con debounce de al menos 500 ms), al reconectar el socket y al recuperar el foco de la
  ventana; y un fetch anterior con `read_at` nulo **no** borra una lectura local ya confirmada.

- **S12** Íconos y etiquetas cubren las cuatro fuentes que realmente se emiten (`appointment`,
  `emergencia`, `cost_alert`, `notification_failure`). El copy no promete avisos de conversaciones ni de
  documentos mientras esos avisos no existan.

## Tasks

| ID | Specs | Route | Commit |
|---|---|---|---|
| T1 | S5 | writer — migración `069` + modelos | _pendiente_ |
| T2 | S2, S3, S4, S6 | writer — audiencia en el fan-out y en los cuatro puntos de emisión | _pendiente_ |
| T3 | S7, S8 | writer — permisos de operaciones, paginación y suscripción push | _pendiente_ |
| T4 | S9, S10 | writer — destino en el payload, mapeo y click | _pendiente_ |
| T5 | S11 | writer — fuente única de verdad y refresco | _pendiente_ |
| T6 | S12 | writer — vocabulario y copy | _pendiente_ |
| T7 | S1-S12 | inline — verificación por spec, verificador independiente y cierre | _pendiente_ |

## Delivery

Neto de la rama contra `main`: **23 archivos, +1068/−388**, en 9 commits. El motor de slices avisa a
partir de ~400 líneas; entregar como **un solo PR** es decisión del owner.

| Commit | Archivos | Cambio | Contenido |
|---|---|---|---|
| `7115f022` | 4 | +166/−12 | audiencia: admins + el responsable de la conversación o el técnico de la visita |
| `f28de340` | 2 | +105/−12 | permisos de operaciones/retry, paginación, push sin secuestro (ítem 2) |
| `66444e10` | 13 | +499/−210 | destino, click, fuente única de estado, vocabulario (backend + `web/`) |
| `85071241` | 1 | +7/−4 | el test de automations, alineado a la audiencia nueva |
| `8875bbc6` | 6 | +170/−155 | destino explícito en la emisión: la operación deja de nombrar el canal |
| `fc03b3e6` | 6 | +27/−81 | revierte mi migración duplicada y lee `responsible_id` |
| `7fad152b`, `3489c9a3` | 2 | +112 | esta ficha y el límite de slice |

`b2da79c1` (la migración `069`) **no forma parte del neto**: la revierte `fc03b3e6`. Consecuencia
para el riesgo declarado: **el ítem 1 ya no aplica** — la rama no cambia el esquema. Queda el
**ítem 2** (permisos), con su verificador independiente.

## Log

- **L1** (2026-11-16, pedido del owner, verbatim):
  > ok perfecto me gustaria tambien mejorar la seccion de notificaciones, las notificaciones actualmente aparecen pero si doy click en alguna notificacion no redirige a donde deberia redirigir, ademas si aprieto el bpton marcar como leida, o marcar todas como leidas, no se actualiza automaticamente el estado de las notificaciones. puedes revisar el estado actual y darme un overvirw del estado actuañ de notificaciones y que otros bugs de fubcioalidad puedes encontear?

- **L2** (2026-11-16, decisiones del owner, verbatim de la opción elegida):
  1. Alcance: **«Las tres juntas»** — permisos, coherencia de estado y destino navegable en un trabajo.
  2. Audiencia: **«Todos los roles, cada uno lo suyo»**.
  3. Visitas: **«Admin + técnico asignado»**.
  4. Emergencias: **«Admin + técnico asignado»**.
  5. Conversaciones y casos: **«Sumar asignado ahora, con migración»**.
  6. Worktree: **«Sí, worktree ODD y rama odd/»**.

- **L3** (2026-11-16, decisiones del agente con derecho a veto del owner, confirmadas): el «asignado»
  de una emergencia es el de **la conversación que la originó** (`Conversation.assigned_user_id`), no el
  técnico de una visita, porque la emergencia nace en el chat; y el click **navega y marca leída** en el
  mismo gesto.

- **L4** (2026-11-16, hallazgo que evitó una migración): el destino no necesita columna propia.
  `PanelNotification.operation_id` es obligatorio y `NotificationOperation` ya guarda `source_entity` y
  `source_id` (`app/models.py:960-961`), así que exponerlos alcanza y hace navegar también las filas
  viejas.

- **L5** (2026-11-16, corrección de un defecto del plan, no de la implementación): la S5 original pedía
  crear `assigned_user_id` en `conversations` y `cases`. **Ya existían** `Conversation.responsible_id`
  y `Case.responsible_id`, con `POST /conversations/{id}/assignment`, reglas (un operador sólo se
  asigna a sí mismo, el destino debe ser un operador activo), control de versión e idempotencia por
  `request_id`, más UI en `ClientFicha`, `ConversationsList` y `CaseActions`. Mi auditoría los perdió
  porque el grep buscó `technician_id|assignee|operator|user_id` y `responsible_id` no estaba en esa
  lista. Consecuencia: la migración 069 y sus dos columnas se revierten, la audiencia lee
  `responsible_id`, y la unidad «asignación manual» desaparece porque **ya estaba hecha**. Lección:
  antes de agregar un campo, buscar el concepto por sus sinónimos, no sólo por el nombre que elegí.

- **L6** (2026-11-16, artefacto de mi propia base): al revertir la 069, la fila
  `069_notification_assignment` quedó en `schema_migrations` del test-db y `test_schema_migrations_records_version`
  empezó a fallar por una versión registrada sin archivo. Limpiada a mano. Es exactamente el riesgo
  que el verificador había marcado en el rollback, ocurriendo en vivo.
