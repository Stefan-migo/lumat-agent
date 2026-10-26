# Conversaciones — chat multimedia (imagen, documento, audio, video)

Frente 2 de los tres frentes de frontend pedidos por el owner. Alcance: el hilo de conversación
(`/panel/app/conversations/<id>`) debe comportarse como un chat de WhatsApp cuando lo toma un humano:
enviar y recibir multimedia, con grabación y reproducción de audio en el panel.

## Specs

- **S1** — "conversaciones ... cuando lo toma un humano. el chat debe tener todas las funcionalidades de
  un chat de whatsapp": un mensaje multimedia entrante se ve dentro del hilo (imagen, audio, video o
  documento), servido por el panel. Nunca un enlace a la URL lookaside de Meta, que es temporal y exige
  token.
- **S2** — "enviar y recibir multimedia principalmente": el operador puede adjuntar y enviar una imagen,
  un documento, un audio o un video desde el panel, y el mensaje queda con su estado de entrega
  (`pending`/`sent`/`failed`) igual que el texto, incluido el reintento de un `failed`.
- **S3** — "Todo (imagen, doc, audio, video) ... Incluye grabar y reproducir audio": el compositor permite
  grabar un audio y el hilo permite reproducir los audios, entrantes y salientes.
- **S4** — el comportamiento que ya existe se conserva: envío de texto, reintento de `failed`, ventana de
  24 h con su rechazo auditado, y el gate de evidencia multimedia del handoff. Un envío multimedia con la
  ventana cerrada se rechaza igual que el texto.
- **S5** — un archivo que no se pudo bajar de Meta no se reintenta para siempre: tras un número acotado de
  intentos el mensaje queda con la media marcada como no disponible y el hilo lo dice, en vez de mostrar
  para siempre un archivo que nunca va a llegar.

## Decisiones de diseño (con su razón)

- **Columnas en `messages`, no tabla aparte.** Se copia la forma que ya existe en `ProjectFile` /
  `AssistantAttachment`: `stored_path`, `content_type`, `filename`, `size_bytes`, `caption`,
  `media_attempts`. `messages` es shape surface, así que el cierre de la feature paga `full`.
- **Servir con un endpoint autenticado, no un mount estático.** `GET
  /panel/api/conversations/{conversation_id}/messages/{message_id}/media` con la misma dependencia de auth
  que el resto del panel, `FileResponse` y verificación de que el path resuelto queda dentro de
  `settings.media_dir`. Un `StaticFiles` sobre `media/` expondría archivos de clientes sin auth.
- **Dos pasos de Meta para enviar media.** `POST /{phone_number_id}/media` (subida → media id) y después el
  mensaje por id. `send.py` solo compone `type: text` hoy.
- **Audio: se graba en un formato que Meta acepta o no se graba.** `MediaRecorder` en Chromium suele dar
  `audio/webm`, que Meta rechaza. Se elige en orden `audio/ogg;codecs=opus`, `audio/mp4` (AAC), y si
  ninguno está soportado el botón de grabar queda deshabilitado con un mensaje, en vez de mandar un
  archivo que va a fallar.

## Tasks

| ID | Spec | Route | Commit |
| --- | --- | --- | --- |
| T1 | S1, S5 | inline (migration 058 + ingest + endpoint autenticado) | — |
| T2 | S1 | inline (serializer + hilo: imagen/video/audio/documento y fallback) | — |
| T3 | S2, S4 | inline (send.py subida + `send_operator_media` + endpoint multipart) | — |
| T4 | S3 | inline (compositor: adjuntar, grabar audio, reproducir) | — |
| T5 | S1-S5 | inline (verificación: shape/full + gate frontend + evidencia) | — |

## Log

**L1 — pedido original del owner (verbatim)**

> - conversaciones (aqui tenemos que hacer implementaciones para mejorar el funcionamiento del chat), cuando lo toma un humano. el chat debe tener todas las funcionalidades de un chat de whatsapp. enviar y recibir multimedia principalmente. 

**L2 — decisión del owner (verbatim)**

- Conversaciones: "Todo (imagen, doc, audio, video)" — "Incluye grabar y reproducir audio. Es el slice más grande y de más riesgo."

**L3 — diagnóstico verificado (`path:line`)**

Entrante:
- `app/webhook/ingest.py:135` — de Meta solo se guarda la URL lookaside; sin mime, filename, tamaño ni caption.
- `app/webhook/ingest.py:365-370` — `process_message` llama `download_media(...)` y **descarta el `Path`**: el archivo queda en disco y nada lo referencia.
- `app/webhook/ingest.py:408-443` — el barrido (`sweep_received`) corre como BackgroundTask del webhook y en el arranque; un fallo devuelve el mensaje a `received` y reintenta sin tope (S5).
- `app/main.py:99-123` — no hay ningún mount estático: nada sirve `media/` hoy.
- `app/panel/api/serializers.py:96-114` — `to_message_dict` expone `media_url` (la de Meta) y nada más.
- `web/src/components/pages/ConversationThread.tsx:40` — el hilo pinta `📎` en lugar del archivo.

Saliente:
- `app/services/send.py:37-60` — `send_text` arma solo `type: text`; no existe subida de media a Meta.
- `app/services/send.py:187-241` — `deliver_outbound` salta filas con `request_id` y manda `row.text`: una fila de media saldría como texto vacío.
- `app/services/conversations.py:201-241` — `send_operator_message` exige `state == HUMAN`, ventana de 24 h e idempotencia por `request_id`, y fija `msg_type=MessageType.TEXT`.
- `app/services/send.py:63-159` — `deliver_message` + `_finalize_delivery` manejan estados y auditoría: el camino que la media debe reusar.

Datos y frontend:
- `app/models.py:314-365` — `Message` solo tiene `media_url`.
- `db/migrations/` — última `057_grant_automation_installation_delete.sql`; la nueva es `058`.
- `web/src/components/pages/ConversationThread.tsx:196-206` — el compositor es solo `Textarea`.
- `web/src/components/primitives/` — no hay primitiva de audio (`MediaRecorder`/`getUserMedia` no aparece en `web/src`).
- `web/src/api.ts:118-124,179` — ya hay precedentes de subida con `FormData`.
