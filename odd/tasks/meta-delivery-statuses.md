# ODD — estados de entrega de Meta (meta-delivery-statuses)

Worktree `../lumat-agent-odd-meta-delivery-statuses`, rama `odd/meta-delivery-statuses`, base `main` (`6298582d`).
Un solo defecto, medido en producción el 2026-11-04.

## Specs

### S1 — el `failed` de Meta llega a la fila del mensaje

> «al enviar. se envia bien casi toda la multimedia excepto el audio. no llega ala whatsapp el audio»

Cuatro audios salientes en producción están en `delivery_status = sent`, `delivery_attempts = 1`,
`delivery_error` vacío y con `wamid` (ids 276, 278, 347, 348). Nuestro lado cree que se entregaron y el
cliente no los recibe.

Causa: `app/webhook/ingest.py:163-166` filtra por `change["field"] != "messages"` y después exige
`"messages" in value`. Un callback de estado de Meta llega como `value.statuses` (sin clave `messages`), así
que `_change_is_message_event` lo descarta y el router responde 200 sin mirarlo. El error de entrega que Meta
sí nos manda se pierde.

Cuando Meta reporta `status: "failed"` para un `wamid` que ya enviamos, la fila tiene que quedar en
`delivery_status = failed` con `delivery_error` legible para el operador — el panel ya lo muestra y ya ofrece
reintentar (`web/src/components/pages/ConversationThread.tsx:65,291`), así que el arreglo es de backend y no
toca la UI.

`delivery_error` se compone con lo que Meta manda en `errors[]`: `code`, `title` y `message` /
`error_data.details`, en una línea, sin superar 2000 caracteres (el límite que ya usa
`_finalize_delivery`). Un `failed` sin `errors[]` igual actualiza el estado y deja el motivo como
«Meta no informó el motivo».

### S2 — un estado nunca resucita ni degrada una entrega confirmada

Los callbacks llegan fuera de orden y se repiten. Reglas:

- `failed` sobre una fila `sent` **sí** la pasa a `failed`: es exactamente el caso que hoy se pierde.
- `sent` sobre una fila `failed` **no** la devuelve a `sent`: Meta confirma el envío antes de intentar la
  entrega, así que un `sent` tardío no es evidencia de que el fallo no ocurrió.
- Cualquier estado sobre una fila `failed` distinto de `failed` la deja como está.
- Un `wamid` desconocido (mensaje que no salió de este sistema) se ignora con log, sin crear filas.
- Un payload de statuses sin `id` o sin `status` se ignora con log.
- Repetir el mismo `failed` es idempotente: no duplica auditoría ni cambia `delivery_error` si es idéntico.

### S3 — `delivered` y `read` dejan la marca sin inventar un estado nuevo

`DeliveryStatus` (`app/models.py:110-115`) no tiene `delivered` y agregarlo es una migración del tipo enum de
Postgres. Este cambio **no** migra: `delivered` y `read` escriben `messages.delivered_at` (la columna ya
existe) cuando la fila está en `sent`, y no tocan `delivery_status`. El panel sigue mostrando el tilde de
entregado con `sent`, como hoy.

Un `delivered_at` ya escrito no se sobrescribe con un timestamp más viejo.

### S4 — el silencio deja de ser silencioso

Cada `failed` registra `record_audit(..., action="message.delivery_failed", entity="message", ...)` con el
`wamid`, el código y el motivo, siguiendo la convención de `_finalize_delivery` (`app/services/send.py:181`).
El router sigue respondiendo 200 aunque el status no se pueda procesar: Meta reintenta ante un no-200 y
convertiría un payload raro en una tormenta de reintentos.

## Tasks

| ID | Spec | Qué | Verificación |
|---|---|---|---|
| T1 | S1, S4 | Parsear `value.statuses` en el webhook y aplicar `failed` con su motivo y auditoría | integración: POST firmado con un status `failed` → fila en `failed`, `delivery_error` con el código, un solo `audit_log` |
| T2 | S2 | Reglas de orden e idempotencia | integración: `sent` después de `failed` no revierte; `failed` repetido es idempotente; `wamid` desconocido no crea filas |
| T3 | S3 | `delivered`/`read` escriben `delivered_at` sin tocar el estado | integración: `delivered` sobre `sent` deja `sent` + `delivered_at`; sobre `failed` no toca nada |
| T4 | S1 | Documentar el callback en `docs/ops.md` §2.1.2 o la sección de webhook, y el límite aceptado | lectura del doc + `quick` |

Una migración **no** es parte de esta feature. Si el implementador concluye que hace falta, se detiene y lo
reporta: cambiaría el alcance y obligaría a `full` en el deploy.

## Log

### L1 — pedido original, verbatim

> por otra parte tambien necesito que verifiques por que no funciona el enviar audios desde el panel. se
> reciben audios correctamente y tambien multimiedia. pero al enviar. se envia bien casi toda la multimedia
> excepto el audio. no llega ala whatsapp el audio. sera algo del WABA? quizas es meta el que no permite
> enviar audios para cuentas empresa con chastbot?

### L2 — diagnóstico medido

- Producción: los cuatro audios salientes están `sent` con `wamid` y sin error. El panel los da por enviados
  porque Meta aceptó el envío.
- `app/webhook/ingest.py:163-166`: los `statuses` se descartan antes de existir cualquier manejo.
- `tests/integration/test_operator_media.py:46-53`: el único test de audio saliente mockea un 200 de Meta y
  afirma sólo `delivery_status == SENT` y el `wamid`. No verifica contenedor ni códec; para
  `app/services/audio_format.py` no hay ningún test.
- Hipótesis viva, **no** afirmada: el `audio/mp4` que graba el `MediaRecorder` de Chrome moderno (segunda
  preferencia en `web/src/components/pages/ConversationThread.tsx:189`) se sube sin remux
  (`app/services/audio_format.py:98`) y Meta lo acepta en la subida para fallar después. Sólo se puede
  confirmar con S1 implementado.

### L3 — decisión del owner

«Primero los estados de entrega (recomendado)»: se procesa `value.statuses` y se guarda el error antes de
tocar la normalización de audio. La normalización obligatoria a ogg/opus se decide con el error real en la
mano, no antes.
