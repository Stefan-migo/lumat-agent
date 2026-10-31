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
- `bash scripts/test.sh full`: **verde** (2026-10-31, `PYTEST_EXIT=0`, progreso al `[100%]`, sin
  `FAILED`/`ERROR`). Ojo con este repo: corre `-q` sin línea de resumen, y `cmd | tail` devuelve el
  exit de `tail`, así que la corrida se captura redirigiendo a archivo y leyendo `$?` de pytest.
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

**L6 — defecto encontrado por el suite completo de frontend y corregido (`0d263a50`):** la fila de
artefacto hacía `[...artifact.versions]` y un payload sin `versions` —el que entrega el panel antes de
que corra la migración, y el de los fixtures existentes— tiraba `TypeError: artifact.versions is not
iterable` y tumbaba el árbol de React. El fallback deriva una revisión única de la fila: un contrato
obligatorio en TypeScript no protege el runtime de un JSON viejo. Después del arreglo, `web/`:
`npm run build` (tsc -b) verde y `npm test` **119 archivos / 1381 tests** verdes.

**L7 — `full` de backend (2026-10-31): 2 rojos, uno corregido y uno que necesita decisión.**

1. *Corregido*: `tests/integration/test_assistant_write_chain_timeline_verifier_probes.py::test_s3_class_b_set_is_exactly_agreed_and_chains_without_approval`
   afirma por igualdad el conjunto autónomo de escritura; `artifact.update` entra en ese conjunto
   (S6), así que la lista esperada se actualiza con él. Verde.
2. *Decidido por el owner y corregido*: `tests/integration/test_assistant_chat.py::test_a_capped_read_only_turn_responder_receives_combined_tool_evidence`
   fallaba porque `_TOOL_EVIDENCE_LIMIT` (`app/chat/assistant/nodes.py:40`) acota la evidencia del
   responder por caracteres y el payload de `assistant.capabilities` **cita el catálogo entero**.
   Medido con la misma prueba en `main` y en la rama: el turno de 4 pasos conservaba 3 payloads con 33
   herramientas (`[1 earlier tool result(s) omitted]`) y sólo 2 con 34. El owner eligió **deduplicar
   resultados idénticos del mismo turno**, así que `_render_tool_evidence` ya no cita dos veces el mismo
   payload (misma herramienta + mismos argumentos + mismo resultado), y cada ejecución sigue nombrada
   en el inventario. Medición posterior: la evidencia quedó en **3.980 caracteres** con el catálogo de
   34 herramientas, y el payload de `dashboard.summary` todavía no entraba, así que el tope subió a
   **4.500** — el mínimo que deja entrar los tres payloads del turno. `main` va a 4.000 y este cambio
   agrega como máximo 500 caracteres de evidencia por turno (≈125 tokens).
   Tests nuevos/actualizados: `test_a_repeated_identical_tool_call_is_quoted_once_in_the_responder_evidence`
   (dedupe), y los dos unitarios de `_TOOL_EVIDENCE_LIMIT` ahora miden el bloque contra la constante en
   lugar de un literal o de la cola del prompt.

**L8 — review nativo (RDD, `review-0bc06157a229cb9a`, tier high, 4 lentes) encontró un defecto real
del candidato y la corrección quedó aplicada, pero el flujo no se puede cerrar por el facade.**

Hallazgo **R3-001** (lente reliability, CRITICAL, `causal_disposition: introduced`): `store_artifact`
escribía el blob **antes** de reservar la identidad e insertar la fila, así que un fallo en el
`nextval` o en el insert dejaba un archivo huérfano en disco sin fila. Corregido en `ec1f4874`: la fila
entra primero, los bytes después, y una escritura fallida borra su archivo parcial
(`_write_blob`). Dos tests nuevos lo prueban y **verifiqué el RED**: con el orden anterior los dos
fallan; con el fix, verdes. Diff de la corrección: 72 líneas de diff (13+/6- servicio, 53+ tests),
dentro del presupuesto de 200.

**Bloqueo**: el provider pasó la autoridad a `correction_required` y emitió el slot
`review.capture-correction-plan` (request hash `sha256:64f7c045…`). `gentle_review_capture` rechaza ese
binding exacto con `capture-binding-rejected / "collectBinding is missing or stale for current
STATUS"` en cinco formas: objeto tal cual lo emite STATUS, string serializado, con el árbol limpio
(`git stash`), con el árbol sucio, y tras un STATUS fresco inmediato. No se manipuló ni se reconstruyó
ningún binding. La autoridad queda en `correction_required`; el trabajo está commiteado y verificado,
pero el review no se puede cerrar por esta vía. Decisión del owner: reintentar el review más tarde,
entregar por política ordinaria del repo dejando el review registrado como bloqueado en corrección, o
reportar el defecto del facade.

