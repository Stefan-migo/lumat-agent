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
| T1 | S1, S5 | inline (migration 058 + ingest + endpoint autenticado) | `a2f997b7`, `40e8d3c5` |
| T2 | S1 | inline (serializer + hilo: imagen/video/audio/documento y fallback) | `b0bd2001` |
| T3a | S2, S4 | worker (send.py subida + `send_operator_media` + delivery por tipo) | `68e896c2`, `7610c2a9` |
| T3b | S2, S4 | worker (endpoint multipart + higiene de temporales) | `f71030e5` |
| T4 | S3 | worker (compositor: adjuntar, grabar audio, reproducir) | — |
| T5 | S1-S5 | inline (verificación: shape/full + gate frontend + evidencia) | — |

**Corte de entrega (decidido al pasar las ~400 líneas autoradas):**

- **Slice 1 — media entrante** (persistida, servida, renderizada y endurecida): `a2f997b7`,
  `40e8d3c5`, `b0bd2001`, `4026be6e`, `0406fe88`, `2c67e0bd`.
- **Slice 2 — media saliente** (subida a Meta, envío por id, endpoint multipart y compositor con
  audio): `68e896c2`, `7610c2a9`, `f71030e5`, más T4.

Los dos slices se pueden entregar como PRs encadenados; abrirlos es decisión del owner.

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

**L4 — verificación del frente 2**

- **Slice 1 (entrante).** RED→GREEN en `tests/integration/test_api_conversations_media.py`
  (persistencia + endpoint + traversal + symlink + auth 401/403) y
  `tests/integration/test_webhook_ingest.py` (tope de 5 intentos, evento `media_unavailable`,
  metadata sobrevive a un fallo posterior del grafo).
- **Revisión de seguridad independiente** (`gentle-ai-verify`): sin bloqueantes. Confirmó con
  ejecución real auth (401 sin sesión), contención de path (12 formas: `..`, absolutos, symlink de
  archivo y de directorio, prefijo engañoso `mediaX/`), scoping por conversación+mensaje, 404
  byte-idéntico y `Content-Disposition` no inyectable. Único hallazgo Medium: `inline` derivado de
  un `content_type` externo dejaba pasar `image/svg+xml` → cerrado en `0406fe88`.
- **Slice 2 (saliente).** RED→GREEN en `tests/integration/test_operator_media.py` (subida única,
  reuso de `meta_media_id` en el reintento, media nunca como texto vacío, fallo cerrado sin
  `stored_path`, límites de tamaño antes de la red) y
  `tests/functional/test_api_conversation_media_send.py` (200 con `delivery_status: failed`,
  higiene del temporal, 401/403/409/422).
- **Gate frontend:** `npm run build` (`tsc -b`) verde; `npm test` → 112 archivos, **1285 tests**,
  todos verdes.
- **Backend:** `scripts/test.sh shape origin/main` → exit 3 (`app/models.py`,
  `app/panel/api/serializers.py`, `db/migrations/058_message_media.sql` son shape surfaces) →
  `scripts/test.sh full` **verde (8m49s)**.
- **Defectos propios que cazó la verificación** (los tres corregidos, no del agente que reporta):
  `NormalizedMessage.caption` requerido rompía tres tests existentes (`4026be6e`); la lista de
  migraciones aplicadas sin `058`; `MessageType` sin importar en `send.py` tras el cambio de
  delivery; y el endpoint devolvía 502 ante un rechazo de Meta mientras el texto devuelve 200 con la
  fila `failed` (`f71030e5`, alineado y pinneado con test).
- **Residuales aceptados y documentados:** carrera entre el chequeo de contención y la apertura del
  archivo; escritura sobre el volumen `media/`; y `audio/webm` sigue siendo imposible de grabar en
  navegadores que solo lo soportan (ahí el botón queda deshabilitado, por diseño).
- **Entrega:** push y PRs quedan en manos del owner; el corte slice 1 / slice 2 está arriba.
