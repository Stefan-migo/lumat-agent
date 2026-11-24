# planner-presupuesto

El asistente gasta la cadena de pasos releyendo y nunca llega a escribir, y las páginas de un mismo archivo se
expulsan entre sí de la evidencia. Corte medido sobre lo que pasó en producción (hilo 54, 2026-11-21).
Riesgo: alto por alcance compartido — toca la proyección de evidencia y el prompt del planner, que usan
todos los turnos del asistente; sin migraciones y sin contrato público nuevo.

## Specs

**S1 — Las páginas de un mismo archivo son un solo documento para la evidencia.**
Medido: con `PROJECT_READ_FILE_PAGE_LIMIT = 3.890` y `_TOOL_EVIDENCE_LIMIT = 5.500`, leer las dos páginas de
un archivo de 5.899 B deja en la evidencia **sólo 2.323 caracteres**: la página nueva entra y la anterior se
descarta. El planner no puede tener las dos mitades a la vez, así que vuelve a pedir la que le falta y la
evidencia expulsa la otra. Resultado medido en producción: seis `read_project_file` por turno, cinco turnos,
cero `project_file.update`.
Las lecturas consecutivas del mismo `file_id` se agrupan en **un** bloque de evidencia, con las porciones en
orden de `offset` y un solo encabezado; el bloque se recorta por el final, nunca por el medio, y el marcador
dice cuánto quedó afuera.

**S2 — El presupuesto de evidencia alcanza para un documento real.**
`_TOOL_EVIDENCE_LIMIT` sube de 5.500 a 12.000 caracteres, y la porción de un resultado de detalle pasa a
`0.85`. Un archivo de hasta ~10 KB entra completo en un turno. El costo es tokens de prompt por paso, no
dinero: se mide en el test con el tamaño renderizado, no con una impresión.

**S3 — Un turno que pidió escribir no puede terminar leyendo.**
Si el pedido del operador nombra una escritura (`escribe`, `guarda`, `actualiza`, `crea`, `edita`, `agrega`)
y la cadena ya ejecutó pasos, el último paso disponible no puede ser una lectura: `tool_loop_head` corta la
cadena en vez de pedir otra lectura, y el turno cierra con lo que haya de evidencia declarando que quedó
trabajo pendiente. Hoy ese corte produce la promesa «lo escribo el próximo turno».

**S4 — El bucle se detecta por archivo, no por llamada idéntica.**
`guardrails` rechaza una lectura de un `file_id` que ya se leyó dos veces en esta cadena, aunque cambie el
`offset`, con un mensaje que empuja a actuar sobre lo leído. El guard actual sólo frena la llamada
consecutiva con argumentos idénticos, y paginar cambia el `offset`.

**S5 — La paginación es una decisión, no un objetivo.**
El prompt del plan deja de pedir «seguí leyendo hasta que el archivo termine o se te acaben los pasos» y pasa
a pedir **como máximo dos páginas por turno**; si el archivo continúa, el turno reporta cuánto leyó y qué
falta. Se enmienda `agent/prompts/assistant_plan.md` en el mismo corte.

**S6 — El tope de pasos es configurable y sube con la dirección ya arreglada.**
`MAX_ASSISTANT_TOOL_STEPS` deja de ser una constante fija y sale de settings
(`assistant_tool_step_limit`, por defecto **8**). Subirlo sin S3 y S4 sólo habría dado más vueltas: el
problema no era el tope sino que cada vuelta gastaba el presupuesto en releer.

**S7 — Los adjuntos del turno tienen prioridad sobre la historia, y el planner sabe cuánto entró.**
En `assemble_context` los adjuntos se ubican **antes** que la historia: si el presupuesto de inyección
(`assistant_context_injection_budget = 4.000` tokens) no alcanza para todo, se recorta historia, nunca el
adjunto. El prompt del plan recibe, por adjunto, cuántos caracteres entraron y si quedó truncado, así no
planifica a ciegas sobre un documento que no vio completo.

**S8 — Los argumentos de cada paso quedan auditables sin guardar contenido.**
`internal_chat.execution` registra, por paso, `arguments_sha256` y las claves de cursor seguras
(`file_id`, `offset`, `limit`, `artifact_id`, `folder_id`) cuando existen. Nunca el contenido ni valores de
dominio (nombres, teléfonos). Sin esto, la secuencia de seis lecturas del hilo 54 fue irreconstruible.

**S9 — La omisión de evidencia queda contada, no sólo dicha.**
Cuando la caja de evidencia descarta contenido, se emite **exactamente una** fila
`audit_log(action="assistant.evidence_truncated")` por proyección, con
`after={"run_id", "surface", "tools", "dropped_chars", "kept_results", "omitted_results", "budget"}`.
Nunca contenido, nunca valores de dominio (nombres, teléfonos, texto de un documento). Sin omisión no hay
fila: el evento cuenta lo que se perdió, no lo que se proyectó. `surface` distingue la caja que arma el
prompt del planner de la que arma el del responder, porque el mismo documento se proyecta para prompts
distintos y sumarlas confundiría la lectura.
La fila se escribe dentro de un `SAVEPOINT` y su fallo degrada a log: la contabilidad no puede romper el
turno, igual que `internal_chat.run_failed` (contrato de `pool-safety` S4). No agrega una tabla ni un
contador nuevo; `audit_log` ya tiene la forma.

**Criterio de decisión fijado ANTES de medir** (para no elegir el número después de ver el resultado):
- `read_project_file` domina y el `dropped_chars` **mediano** de esos casos supera ~4.000 → el paso 3 está
  justificado;
- las omisiones son de listados (`customers.list`, `conversations.list`, `conversations.search`) → **no**
  tocar la caja: `_LISTING_EVIDENCE_SHARE = 0.45` ya las cubre;
- casi no hay omisiones → cerrar el tema y dejarlo en 12.000.
Consulta de lectura:
```sql
select after->>'surface', after->>'tools', count(*) as filas,
       percentile_cont(0.5) within group (order by (after->>'dropped_chars')::int) as mediana,
       max((after->>'dropped_chars')::int) as peor
from audit_log
where action = 'assistant.evidence_truncated' and created_at > now() - interval '7 days'
group by 1, 2 order by 3 desc;
```

## Tasks

| ID | Spec | Route | Commit |
| --- | --- | --- | --- |
| T1 | S1, S2 | backend · `_coalesce_file_reads` + presupuesto 12.000 / página 9.800 | this commit |
| T2 | S3, S4 | backend · reserva del último paso y bucle por `file_id` | this commit |
| T3 | S5, S6 | prompt + settings · dos páginas por turno y `assistant_tool_step_limit = 8` | this commit |
| T4 | S7 | backend · adjuntos antes que historia + aviso de truncado | this commit |
| T5 | S8 | backend · `arguments_sha256` + claves de cursor en `internal_chat.execution` | this commit |
| T6 | S9 | backend · fila `assistant.evidence_truncated` por proyección con omisión | `e74be186e` |

## Log

**L1 — pedido del owner (2026-11-24), verbatim:**

> si quiero que lo hagas.
>
> respecto al punto 1. me salta una duda. sera muy poco el Max 6 tools? o el presupuesto de caracteres sera muy peque;o? la cantidad de tools sigue creciendo por ende. es probable que el asistente necesite hacer tareas mas largas con mas tools utilizadas.
>
> tendria sentido aumentar el presupuesto y la cantidad de max tool steps?
>
> 2. me parece bien tu sugerencia procede asi.

**L2 — diagnóstico medido (2026-11-24, sobre `main` `f926e6dc7`):**
- Archivo real: `herramientas-probadas-hilo-84.md`, 5.899 B → 2 páginas de 3.890 y 2.009 caracteres.
- `_render_tool_evidence` con la página 1 sola: **4.063** caracteres de evidencia.
- Con las dos páginas: **2.323** caracteres, la página 1 desaparece (`"A"*50 in rendered == False`), la
  página 2 queda. La proyección conserva lo más nuevo y descarta lo anterior.
- Producción (hilo 54, mensajes 249-257): cada turno ejecutó **6** `read_project_file` — el tope exacto — y
  **0** `project_file.update`. El `audit_log` sólo guarda `tool` y `status`, así que la secuencia de
  argumentos no se puede reconstruir: eso es S8.
- Respuesta a la pregunta del owner, medida: el tope de 6 pasos no es la causa, es el contador de vueltas.
  La causa es que **cada vuelta expulsaba la mitad del archivo** del presupuesto de caracteres, así que el
  planner nunca podía tener el documento completo en vista.

**L3 — decisión de alcance (2026-11-24):** los dos cortes van juntos en un documento porque tocan el mismo
prompt y la misma proyección; separarlos en dos PRs los haría pisarse. S6 sube el tope a 8 **después** de S3
y S4, y queda configurable para ajustarlo en producción sin un release.

**L4 — lo que salió distinto al plan (2026-11-24):**
- La página de lectura no la fija sólo `_DETAIL_EVIDENCE_SHARE`: con el presupuesto nuevo quedó en 9.800
  caracteres, así que el archivo medido de 5.899 B entra en **una** sola página. El agrupado de páginas
  (`_coalesce_file_reads`) sigue siendo necesario para archivos más grandes o cuando el modelo pide un
  `limit` chico.
- Cuatro tests existentes fijaban los números viejos y el orden viejo, y se actualizaron como contrato, no
  para que pasaran: `test_read_project_file_page_is_clamped_and_keeps_cursor_before_text` ahora pide
  cuatro veces el techo derivado de la constante, `test_S3_every_page_over_the_ceiling_clamps_and_executes`
  parametriza sobre el techo real, `test_replan_keeps_newest_tool_evidence_within_budget` usa un payload
  dimensionado al presupuesto nuevo, y `test_context_truncates_attachments_after_history` pasó a
  `test_context_truncates_history_after_attachments` porque el orden es la regla nueva.
- `test_completed_tool_traversal_records_one_execution_audit` ahora exige el digest y verifica que el
  contenido del operador **no** viaje en la auditoría (`"Ana" not in after`), que es lo que S8 promete.
- Test-first real: S1/S2 tuvieron RED medido antes del cambio (script de 2026-11-24: página 1 sola 4.063
  caracteres, páginas 1+2 = 2.323 con la página 1 ausente). S3/S4/S6/S7/S8 se implementaron antes del test;
  el registro queda así de explícito y no se presenta como si hubieran tenido RED.
- Las fallas intermitentes de `test_panel_memory_routes` (401 en el login) que venían apareciendo en otras
  corridas son **concurrencia de suites sobre la misma base de prueba**, no un defecto del producto: pasaron
  cuando corrí `quick` mientras `full` corría en el mismo worktree, y no aparecen con la suite sola.


**L5 — pedido del owner (2026-11-24), verbatim:**

> vamos en el orden recomendado

El orden recomendado y aprobado fue: (1) el corte `provider-budget-guard` —la colisión entre el
presupuesto del proveedor y el guard de la base, que mataba turnos del panel a los ~3 min—, cerrado y
commiteado antes de este paso; (2) **este paso 2**, instrumentar y medir las omisiones de evidencia antes
de tocar cualquier número, con el criterio de S9 fijado de antemano; (3) el paso 3 sólo con el dato del
paso 2. La ventana de observación no empieza hasta que esto esté desplegado en producción: es decisión del
owner y no se simula con datos inventados.

**L6 — lo que salió distinto al plan del paso 2 (2026-11-24):**
- **S9 tuvo RED real**: 4 de 14 tests fallaron antes de implementar (`surface` no aceptado, ninguna fila
  registrada, planner y responder indistinguibles).
- **El caso "corte" no estaba cubierto**: cuando un solo resultado es más grande que la caja entera, el
  resultado se conserva y se recorta su cola. `dropped_chars` se obtenía allí **re-parseando con regex el
  marcador que el propio código acababa de escribir**, así que un cambio de redacción del marcador habría
  convertido la métrica en cero en silencio. `_cut_with_marker` ahora devuelve `(texto, dropped)` y el
  llamador recibe el número. El test derivado
  (`test_a_single_result_larger_than_the_budget_records_the_cut_chars`) ata el valor de la fila al marcador
  que vio el modelo. Ese test **pasaba antes del refactor**: no se presenta como RED, porque la conducta ya
  era correcta y lo frágil era cómo se obtenía el dato.
- **Contrato de "sólo observación" verificado**: el texto renderizado es byte-idéntico por las tres rutas
  (renderer directo, `_planner_context_text`, `_responder_prompt`), y un `record_audit` que explota no
  cambia ni una letra del prompt ni levanta excepción.
- **La fila es contable, no narrativa**: un test serializa `after` y exige que el texto del documento no
  aparezca. `dropped_chars` cuenta caracteres de la caja que se perdieron (resultados omitidos completos
  más la cola recortada), no bytes del archivo original: es la unidad que la consulta de S9 puede sumar.
- **Gates propios al cierre**: `scripts/test.sh quick` exit 0; foco (evidencia, planner, tool-loop,
  planner-budget) **149 passed**; `tests/integration/test_assistant_chat.py` **81 passed**;
  `scripts/test.sh full` **exit 0, 0 FAILED/ERROR, progreso 100%**.
- **El paso 3 no arranca hoy**: S9 fija el criterio, pero la ventana de observación empieza cuando esto esté
  desplegado en producción y haya uso real del panel. Hasta entonces el paso 3 no tiene dato, y no se
  sustituye con una medición inventada.
