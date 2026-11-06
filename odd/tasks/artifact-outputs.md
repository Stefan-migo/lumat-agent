# ODD — artifact-outputs: el artifact deja de morir en el hilo

Worktree `../lumat-agent-odd-artifact-outputs`, rama `odd/artifact-outputs`, base `main` (`47c6d0ba`).

Tres defectos medidos en la DB de dev (`infra-db-1`, proyecto `test`, usuario 1) sobre el asistente del
panel, no recitados:

1. El turno hace el trabajo y contesta que no pudo (`PANEL_GROUNDING_REFUSAL`).
2. El mismo entregable se crea repetido: `artifact.save` nunca deduplica.
3. El artifact vive y muere en su hilo: no hay inventario en el contexto ni superficie en el proyecto.

## Specs

**S1 — La frase fija deja de ser una respuesta del panel.**
`PANEL_GROUNDING_REFUSAL` desaparece como respuesta. Un turno no conversacional cuyo retrieval vuelve
vacío termina en el nodo responder, no en una constante. El texto
"No encontré evidencia suficiente en la base de conocimiento para responder con seguridad. Reformula la
consulta o aporta más contexto." no se emite nunca más desde el grafo.

**S2 — La evidencia de tool del turno manda sobre la base de conocimiento.**
Un turno con al menos un paso de tool ejecutado (`tool_steps > 0`, `tool_results` no vacío) que replanifica
como `respond` va a `respond_stream` con su evidencia, sin pasar por `retrieve_kb` y sin importar
`_is_conversational_turn`. Un paso con error también cuenta: cuando la tool falló, el responder explica el
fallo en vez de buscar en la KB.

**S3 — Sin respaldo, el agente explica; no corta.**
Cuando no hay evidencia de tool y el retrieval vuelve vacío, el responder corre con una directiva de
`no_evidence` que le exige: decir qué entendió del pedido, qué buscó o qué fuente necesitaría, afirmar que
no tiene respaldo para eso, y dar el paso concreto al operador. La directiva prohíbe afirmar precios,
políticas, horarios o cualquier dato de negocio sin evidencia, y prohíbe declarar hechos ejecutados sin
resultado de tool. Un retrieval que **falla** sigue siendo `kb_unavailable` (estado degradado honesto), no
"sin respaldo": un fallo no es una ausencia de evidencia.

**S4 — El asistente ve el inventario de artifacts del hilo.**
El contexto del turno incluye una línea por artifact vigente del hilo con su `artifact_id`, nombre,
versión y tamaño, y la instrucción de editar con `artifact.update`. Es determinista: no depende de que el
planner elija una tool. Acotado a `_ARTIFACT_INVENTORY_LIMIT` líneas.

**S5 — `artifact.save` no duplica el mismo entregable.**
Mismo hilo + mismo `filename` + mismo `sha256` que la revisión vigente de una raíz existente devuelve esa
revisión con `changed: false`: no inserta fila, no escribe blob, no audita. Es el caso de los artifacts 5,
6 y 7 del hilo 116, creados una y otra vez para el mismo entregable.

**S6 — `artifact.save` sobre un `filename` existente con contenido distinto agrega una revisión.**
Mismo hilo + mismo `filename` + `sha256` distinto inserta `version = max + 1` bajo la **misma** raíz y
devuelve `changed: true`. Nunca abre una segunda raíz con el mismo nombre: en el hilo 116, #6 (3109 B) y #7
(5361 B) comparten `checklist-capacidades-lumat-agent.md`, y el nombre es la identidad del entregable
dentro del hilo. `store_artifact` conserva su contrato (siempre `version = 1` de una raíz nueva); el
comportamiento nuevo vive en `save_or_append`.

**S7 — El artifact se publica solo en `outputs/` del proyecto.**
Al crearse y en cada revisión, el artifact se escribe como archivo del proyecto del hilo dentro de la
carpeta `outputs` (se crea on demand como `ProjectFolder`). Es automático: sin aprobación y sin una tool
extra. Nunca lanza: si el proyecto no resuelve, si el tipo de archivo no está permitido, o si el owner no
existe, el artifact queda solo en el hilo y la operación termina igual.

**S8 — La publicación es idempotente y sigue a la revisión vigente.**
Un archivo publicado por artifact, identificado por `project_files.source_artifact_root_id` (columna
nullable, índice único parcial por proyecto). Una revisión nueva sobrescribe el mismo archivo publicado
(bytes, `size`, `sha256`) en vez de agregar un segundo. El nombre de archivo nunca es la identidad: dos
raíces distintas pueden compartir nombre y cada una conserva su archivo.

**S9 — Otro hilo del mismo proyecto ve y lee lo publicado.**
`list_project_files` muestra el archivo dentro de `outputs/` y `read_project_file` devuelve su contenido,
sin mediar ningún handle del hilo de origen.

**S10 — Un hilo sin proyecto no publica y no falla.**
`proyecto = "default"` o sin `Project` que resuelva para el owner: el artifact queda thread-scoped como
hoy, el resultado de la tool es el mismo y no se registra error.

**S11 — La publicación deja auditoría.**
`record_audit(action="assistant_artifact.published", entity="project_file", entity_id=<project_file id>,
after={"project_id", "artifact_root_id", "artifact_id", "version", "filename"})`. Una sobrescritura usa
`assistant_artifact.republished` con la misma forma.

**S12 — El contrato de escrituras no cambia.**
`artifact.save`, `artifact.update` y `artifact.delete` siguen siendo autónomas, thread-scoped y del owner
del hilo. Publicar en `outputs` no abre una escritura nueva de clase A: es la consecuencia declarada de un
artifact que el owner ya autorizó en su hilo, y su alcance es solo el proyecto de ese hilo.

## Fuera de alcance

- `PANEL_KB_UNAVAILABLE`: un fallo de retrieval sigue cortando con su mensaje degradado. Es honesto, no es
  el defecto reportado.
- Indexar el archivo publicado en la base de conocimiento del proyecto (`kb_document_id`).
- El desorden de evidencia del hilo 84 (el agente confundió memoria de contexto con evidencia de tool) y
  el error crudo en inglés que se filtró en el mensaje 151 (`Tool execution failed: ...`).
- La UI del panel para `outputs`: el archivo publicado aparece como una fila normal de
  `project_files`, dentro de una carpeta normal.

## Tasks

- [ ] **T1 — Slice 1 RED.** Tests que fallan: `guardrails` rutea a `respond_stream` cuando el turno ya
      ejecutó una tool y replanifica `respond`; `retrieve_kb` con chunks vacíos produce `decision: respond`
      y `no_evidence` en vez de la frase fija; `_after_retrieve_kb` manda a `respond_stream`; el prompt del
      responder incluye la directiva `no_evidence`. *Check:* comando exacto y salida de fallo.
- [ ] **T2 — Slice 1 GREEN.** `guardrails`, `retrieve_kb`, `_after_guardrails`, `_after_retrieve_kb`,
      `PANEL_GROUNDING_REFUSAL` fuera, `NO_EVIDENCE_DIRECTIVE`, `{{no_evidence}}` en
      `agent/prompts/assistant_respond.md`. *Check:* los tests de T1 pasan.
- [ ] **T3 — Slice 1 spec.** `openspec/specs/internal-agent-chat/spec.md`: reescribir **IAC-14** (el
      escenario "sin evidencia" deja de ser "clarificación determinista sin responder"); ajustar el
      escenario de AT-12 en `assistant-tools/spec.md` que hoy clava el refusal. *Check:* lectura completa del
      archivo y coherencia con el código.
- [ ] **T4 — Slice 1 commit.** `fix(assistant): answer from the turn's evidence instead of a grounded refusal`.
- [ ] **T5 — Slice 2 RED.** Tests: el contexto incluye el inventario de artifacts del hilo (id, nombre,
      versión, tamaño) acotado; `save_or_append` con contenido idéntico devuelve la vigente sin fila nueva;
      con nombre igual y contenido distinto agrega `version+1` bajo la misma raíz y no crea segunda raíz.
- [ ] **T6 — Slice 2 GREEN.** `assemble_context_node` inyecta el bloque `thread_artifacts`;
      `assistant_artifacts.save_or_append`; `_save_artifact` la usa y publica el `changed` real.
- [ ] **T7 — Slice 2 spec + commit.** AT-15 en `openspec/specs/assistant-tools/spec.md`.
      `feat(assistant): make the thread artifact an editable, deduplicated deliverable`.
- [ ] **T8 — Slice 3 RED.** Tests: crear un artifact publica un `ProjectFile` en la carpeta `outputs` del
      proyecto del hilo; una revisión nueva sobrescribe ese mismo archivo (un solo archivo por raíz, nuevo
      `sha256`); hilo `default` no publica y no falla; archivo de tipo no permitido no publica y no falla;
      listar y leer desde otro hilo del proyecto devuelve el contenido; auditoría `published`/`republished`.
- [ ] **T9 — Slice 3 GREEN.** `db/migrations/063_artifact_outputs.sql`, `ProjectFile.source_artifact_root_id`
      en `app/models.py`, `publish_artifact` en `app/services/assistant_artifacts.py`, cableado en
      `_save_artifact` y `_update_artifact`.
- [ ] **T10 — Slice 3 spec + commit.** AT-16. `feat(assistant): publish artifacts into the project outputs
      folder`. Commit propio: la migración es riesgo alto (ítem 1).
- [ ] **T11 — Cierre.** `bash scripts/test.sh full` y `bash scripts/test.sh shape origin/main`; verificación
      independiente del diff completo (riesgo alto declarado en T9).

## Log

**L1 — pedido original del owner (verbatim).**

> hey chat. necesito que sigamos trabajando en el asistente lumat. ha mejorado harto pero aun nos quedan
> cosas por mejorar.
>
> necesito que revises el proyecto Test del agente. en el usuario Stefan. ahi hay un hilo donde estuvimos
> trabajando con un artifact para testear todas las tools disponibles.
>
> pero el agente en un momento dejo de actualizar el artifact creado.
>
> ---
>
> despues al abrir un nuevo chat, el artifact ya no estaba disponible para el agente. aun cuando el chat
> fue abierto en el mismo proyecto.
>
> lo ideal seria aqui es que cuando se crea un artifact, este quede aun disponible para futuras
> conversaciones. una vez que el artifact es creado. se puede transformar en un archivo del proyecto.
> (debe crear un nuevo directorio outputs, y ahi debe estar disponible el artifact creado en el hilo asi
> se mantiene disponible para proximas conversaciones dentro del mismo proyecto).
>
> ---
>
> hay situaciones donde el agente sigue diciendo: "No encontré evidencia suficiente en la base de
> conocimiento para responder con seguridad. Reformula la consulta o aporta más contexto." Por que dice
> eso el agente? en que caso tiene esa respuesta? por que da esa respuesta? yo creo que no deberia
> tenerla . si algo pasa deberia explicar por que no es capaz de realizar la tarea solicitada en el
> prompt. Eso por ahora

**L2 — corrección del owner (verbatim).**

> bueno eso tambien vi. en un momento el asistente creaba el artifact. lo creaba repetido 3 veces. puedes
> revisar eso tambien?

**L3 — decisión del owner sobre la persistencia.** "Automático: se publica solo en `outputs/`" — cada
artifact se publica al crearse y en cada edición, sin aprobación ni pedido explícito (S7).

**L4 — pregunta del owner sobre el gate y decisión.** "siento que este es un gate necesario para el chatbot.
pero para el asistente no se si la necesitamos?" → elegido "Garantía sí, cortacircuitos no (recomendado)".
Se conserva la garantía de que un dato de negocio no se afirma sin evidencia; se elimina el cortocircuito
que sustituye al agente por una frase fija (S1-L3).

**L5 — autorización de worktree y alcance.** "Sí, un feature con tres slices" → worktree
`../lumat-agent-odd-artifact-outputs`, rama `odd/artifact-outputs`, tres unidades revisables con commit
propio.

**L6 — evidencia medida (2026-11-06) sobre la DB de dev `infra-db-1`, proyecto `test`, usuario 1.**

```
select count(*) from assistant_artifacts where version > 1;   ->  0
audit_log: 7 x assistant_artifact.created | 0 x assistant_artifact.updated

#4  capacidades-lumat-agent.md         3827 B  2026-10-30 19:51:48  (respuesta normal)
#5  capacidades-lumat-agent.md         5333 B  2026-10-31 16:57:01  (respuesta: la frase fija)
#6  checklist-capacidades-lumat-agent.md 3109 B 2026-10-31 16:58:40 (respuesta: la frase fija)
#7  checklist-capacidades-lumat-agent.md 5361 B 2026-10-31 16:59:10  (respuesta normal)
```

Reproducción determinista sobre el código de la base, sin LLM:

```
conv=False | 'Referencia: capacidades-lumat-agent.md ... modifiques este archivo ...'
conv=False | 'que por que estas buscando informacioon en la base de conocimiento?'
conv=False | 'hola? estas?'
--- turno con un tool ya ejecutado, plan final = respond ---
decision: retrieve_kb        <- la evidencia del tool se descarta
```

Consecuencia: `odd/tasks/assistant-grounding-gate.md:201-221` ya había declarado esta salida como el
primer item a revisar "if the panel assistant starts refusing questions it should answer", y pidió como
evidencia el uso real. L6 es esa evidencia.
