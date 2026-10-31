# artifact-revisions

El asistente puede reescribir los artefactos que él mismo creó, sin pisar versiones anteriores ni
crear archivos al lado. Revisiones append-only por artefacto, no un git. Riesgo alto: migración de
esquema (item 1) y concurrencia en el append (item 4).

## Specs

**S1 — Cada edición es una fila nueva, nunca un UPDATE y nunca un DELETE.**
`assistant_artifacts` gana `root_id` (bigint, raíz del artefacto) y `version` (integer, arranca en 1).
Un artefacto nuevo es su propia raíz en `version = 1`. Una edición inserta una fila nueva con el mismo
`root_id` y `version = max(version) + 1` dentro de esa raíz. Ninguna fila existente se modifica ni se
borra: el blob anterior sigue en disco y su `sha256` sigue verificando integridad.

**S2 — La vigente es la de mayor `version` por `root_id`, y es la única que ve el hilo.**
`GET /panel/api/chat/threads/{id}` devuelve **una sola** fila por `root_id` — la de mayor `version`.
Un artefacto con tres revisiones no aparece tres veces en el sidebar ni en el contexto del hilo.

**S3 — El download sirve la vigente salvo que se pida una revisión.**
`GET /panel/api/chat/threads/{t}/artifacts/{id}/download` sin parámetros sirve la vigente de la raíz a
la que pertenece `id` — cualquiera sea la revisión que ese `id` nombre. Con `?version=N` sirve esa
revisión exacta de la misma raíz. Un `version` inexistente devuelve 404 con `detail = "artifact
version not found"`. Un `id` de otro hilo sigue devolviendo `detail = "artifact not found"`.

**S4 — Una referencia escrita en el hilo apunta a la vigente (decisión del owner, 2026-10-31).**
Los mensajes ya guardados contienen el path literal
`` `/panel/api/chat/threads/{t}/artifacts/{id}/download` `` de la revisión que existía al escribirse.
Ese path resuelve a la **vigente** de esa raíz y el chip muestra el nombre y el tamaño de la vigente.
Una referencia arrastrada desde el sidebar viaja con el `id` de la fila listada, que es la vigente.

**S5 — En el hilo se ve la vigente con badge `vN` e historial colapsado (decisión del owner, 2026-10-30).**
La fila del artefacto muestra `vN` sólo desde la revisión 2; un artefacto de una sola revisión no
muestra badge. El historial arranca colapsado, lista las revisiones de mayor a menor, y abrir una
revisión la muestra en el visor **sin** cambiarla por la vigente ni escribir nada en el servidor.

**S6 — `artifact.update` sólo puede reescribir artefactos del asistente en el hilo actual.**
Herramienta nueva `artifact.update` con argumentos `{artifact_id: int, content: str}`. Falla cerrada
con `"no accessible chat thread for artifacts"` cuando el hilo no es del owner, con `"artifact not
found"` cuando el `artifact_id` no pertenece a ese hilo, y con `"artifact content is empty"` /
`"artifact size exceeds the configured limit"` igual que `artifact.save`. Cada fila de
`assistant_artifacts` fue creada por el asistente (los adjuntos humanos viven en
`assistant_attachments`), así que el alcance «sólo artefactos del asistente» es la pertenencia al hilo
más la pertenencia del hilo al owner: no se agrega una columna de autor. La herramienta queda
autónoma como `artifact.save`, porque no alcanza nada fuera de los artefactos que el propio asistente
produjo en el hilo que ya posee.

**S7 — Reenviar el contenido idéntico no crea una revisión.**
Si el `sha256` del contenido nuevo es igual al de la vigente, no se inserta fila, no se escribe blob y
no se registra auditoría: la herramienta devuelve la vigente con `changed: false` y `version` igual.

**S8 — La nueva versión reusa los límites de `store_artifact`.**
Contenido no vacío y `<= assistant_artifact_max_bytes`; el `filename` y el `content_type` se heredan
de la fila editada, así que una edición nunca renombra el artefacto.

**S9 — La edición deja auditoría con la versión anterior y la nueva.**
`record_audit(action="assistant_artifact.updated", entity="assistant_artifact", entity_id=<nuevo id>,
after={"thread_id", "filename", "size", "root_id", "version", "previous_version"})`. `store_artifact`
mantiene su `assistant_artifact.created`.

**S10 — El serializer publica la identidad de la raíz y el historial.**
`to_assistant_artifact_dict` agrega `root_id`, `version` y `versions: [{version, id, size,
created_at}]` ordenado por `version` ascendente, con todas las revisiones de esa raíz del mismo hilo.
Los campos actuales (`id`, `thread_id`, `filename`, `content_type`, `size`, `created_at`) no cambian de
nombre ni de tipo, y `id` sigue siendo el de la **vigente**.

**S11 — El append es seguro bajo concurrencia.**
Índice único `uq_assistant_artifacts_root_version (root_id, version)`. El servicio toma
`SELECT ... FOR UPDATE` sobre la fila raíz antes de calcular `max(version) + 1`, de modo que dos
ediciones simultáneas del mismo artefacto producen las versiones N+1 y N+2, no dos filas con la misma
`version`.

**S12 — La migración es aditiva y reversible.**
`db/migrations/061_artifact_revisions.sql` agrega las dos columnas como nullable, hace backfill
(`root_id = id`, `version = 1`) y recién entonces aplica `NOT NULL` + default, más el índice único.
Ninguna columna existente se borra ni se renombra. El rollback escrito en el archivo devuelve la tabla
a su forma anterior sin perder filas.

**S13 — El costo en disco se mide, no se adivina (decisión del owner, 2026-10-31).**
Ninguna revisión se purga en esta entrega. Se documenta en la guía de operación la consulta que
devuelve, por hilo, cantidad de revisiones y bytes totales de `assistant_artifacts`, para decidir una
política de retención con datos reales.

## Tasks

| ID | Specs | Route | Commit |
|---|---|---|---|
| T1 | S1, S12, S11 | inline | `e672fd6f` — migración 061 + tests de migración |
| T2 | S1, S2, S7, S8, S9, S11 | inline | `e18a6c87` — servicio `assistant_artifacts` |
| T3 | S6, S7, S8, S9 | inline | `194ecade` — `artifact.update` + superficies declaradas |
| T4 | S2, S3, S10 | inline | `155a91d4` — API: `?version=` y serializer |
| T5 | S4, S5, S10 | inline | `20bb0b13` — frontend: badge `vN`, historial, referencias |
| T6 | S13 | inline | `e672fd6f` — consulta de costo en `docs/ops.md` §2.9.1 |
| T7 | todas | inline | verificación de cierre (abajo) |

Cortes de entrega, por unidad revisable: `32335328` (doc) → `e672fd6f` (esquema) →
`e18a6c87` (servicio) → `194ecade` (herramienta) → `155a91d4` (API) → `20bb0b13` (panel). El corte
del esquema va solo porque su `Risk` nombra alto riesgo (item 1), para que la revisión nativa pueda
tomarlo aparte.

### Verificación de cierre (T7)

- `bash scripts/test.sh quick` por iteración: verde.
- `bash scripts/test.sh shape origin/main` → **3** (migración, `models.py`, `serializers.py`,
  `registry.yaml`, `personas/assistant.md`): `full` obligatorio.
- `bash scripts/test.sh full`: ver el registro del cierre.
- `web/`: `npm ci` → `npm run build` (`tsc -b`) → `npm test`.

## Log

**L1 — pedido del owner (2026-10-30, textual):** *"darle una herramienta al asistente para que pueda
modificar los artifacts que ya creo. para que no tenga que crear uno sobre otro. seria posible?
tendriamos que crear una especie de git o versionador para que pueda hacerlo correctamente??"*

**L2 — decisiones del owner en el picker del 2026-10-30:** en el hilo se ve sólo la versión vigente,
con badge `vN` e historial colapsado, no todas las versiones como filas separadas; la herramienta puede
reescribir sólo artefactos que creó el asistente, nunca archivos del proyecto ni adjuntos subidos por
una persona; no hace falta un git completo, sí revisiones.

**L3 — evidencia medida (2026-10-31, sobre `main` `48654387`):** `AssistantArtifact`
(`app/models.py:979-990`) no tiene `version` ni padre; `store_artifact`
(`app/services/assistant_artifacts.py:40`) siempre inserta; `_save_artifact`
(`app/chat/assistant/tools/registry.py:790`) es el único punto de creación y `artifact.save` está en
`AUTONOMOUS_WRITE_ALLOWLIST` (`:37`); único endpoint de artefactos en
`app/panel/api/routes/chat.py:415`; el listado sale de `chat.py:350`; serializer en
`app/panel/api/serializers.py:558`; última migración `060_capture_ack_plain.sql`; `db/migrate.sh`
ejecuta cada archivo entero dentro de una transacción, así que un archivo multi-statement es válido;
las fichas de referencia llevan el `id` de la fila concreta (`AssistantWorkspace.tsx:713`) y el path
literal queda escrito en el mensaje (`AgentChat.tsx:114-129`).

**L4 — decisiones del owner (2026-10-31, cuatro preguntas del arranque):** la referencia apunta a la
vigente siempre; append-only sin límite ahora, medir y decidir después; editar es una herramienta
aparte y `artifact.save` sigue creando siempre (mismo nombre = artefacto distinto); se crea el worktree
`artifact-revisions` desde `main`.

**L5 — decisiones técnicas del orquestador (sin consulta, por ser aditivas):** `?version=N` sobre el
endpoint de download existente en lugar de un endpoint nuevo, para no romper ninguna URL ya emitida;
reenviar contenido idéntico no crea revisión (S7); el append se serializa con `SELECT ... FOR UPDATE`
sobre la raíz más el índice único (S11).
