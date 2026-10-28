# ODD — asistente-detalles (asistente-detalles)

Worktree: `../lumat-agent-odd-asistente-detalles` · rama `odd/asistente-detalles` · base `11ba8433`
Cuatro unidades independientes: **A** pestañas + segundo plano + avisos, **B** robustez del planificador,
**C** archivos de proyecto vs KB, **D** retiro de planificación.

## Specs

### A — pestañas, segundo plano y avisos

- **S1** Al cambiar de sección del panel (Conversaciones, Clientes, …) y volver a Asistente Lumat, la lista
  de pestañas abiertas se conserva completa, en el mismo orden, con la misma pestaña activa. Sobrevive
  también a recargar la página.
- **S2** La lista persistida es por usuario y por navegador. Un deep link (`?thread_id=…`, `?context=…`,
  `?history=…`, `?sessions=…`) siempre gana: se agrega a la lista restaurada y pasa a ser la activa; nunca
  se descarta por lo persistido.
- **S3** Al abrir una pestaña de hilo cuyo último run sigue en curso, el cliente reabre el stream de ese
  `run_id` y muestra progreso y respuesta final. Hoy solo se reabre al enviar un mensaje o al aprobar un plan.
- **S4** Si un run termina mientras su pestaña no está a la vista, aparece un toast con el nombre del hilo:
  éxito al completar, peligro si falló.
- **S5** Con permiso de notificaciones ya concedido, además se emite una notificación web con el nombre del
  hilo. Sin permiso se emite solo el toast y **nunca** se pide el permiso automáticamente.
- **S6** Cerrar una pestaña la quita de la lista persistida, y borrar un hilo quita su pestaña. Las pestañas
  cerradas no reaparecen al volver a la sección.

### B — planificador

Evidencia: stack local del main worktree, hilos 79 y 80 (`assistant_state.planner.failure`).

- **S7** Un plan cuyo JSON trae un carácter de control sin escapar dentro de un string (el caso real: un salto
  de línea en `response`, `Invalid control character at: line 1 column 541 (char 540)`) se parsea y el turno
  respeta el plan del modelo. No cae al mensaje genérico.
- **S8** Un plan seguido de texto extra (el caso real: primer objeto JSON y después prosa,
  `Extra data: line 3 column 1 (char 168)`) se parsea tomando el primer objeto JSON completo.
- **S9** Si el plan sigue sin validar tras S7–S8, hay **un** reintento acotado que vuelve a pedir solo el
  objeto JSON; recién si ese reintento falla el turno degrada.
- **S10** El turno degradado conserva el texto exacto `No pude planificar esa solicitud de forma segura. Inténtalo nuevamente.`
  y sigue persistiendo el diagnóstico completo (`reason`, `stage`, `exception_type`, `raw_excerpt`) más la línea de
  log con `reason`, `stage` y `exception_type`. La causa no se inventa en el copy: se conserva en datos y logs,
  para no romper el contrato que ya fijan `tests/integration/test_assistant_chat.py` y
  `tests/integration/test_assistant_harness_production.py`. Un fallo del proveedor no se reintenta (no se
  duplica el costo); solo un plan inválido del modelo paga **un** reintento.
- **S11** ~~Un pedido de análisis que encadena métricas → conversaciones → transcripciones se completa en un
  turno: el tope de pasos encadenados sube de 4 a 8.~~ **Retirada (L6):** sin evidencia; el tope nunca se
alcanzó. No se sube un techo de llamadas pagadas por hipótesis.

### C — archivos de proyecto vs KB

- **S12** Subir un archivo a "Archivos del proyecto" no crea ni modifica ningún documento de la KB: queda
  almacenado local, con `kb_document_id` nulo, y la fila no muestra badge de KB. La KB se alimenta solo desde
  "Conocimiento del proyecto".
- **S13** Los documentos de KB creados por la ruta vieja no se borran ni se migran; la tarjeta de conocimiento
  deja de ocultarlos con el filtro `indexedDocIds`.
- **S14** El asistente sigue leyendo cualquier archivo de proyecto con `list_project_files` y
  `read_project_file`; no se pierde acceso al contenido.

### D — retiro de planificación

- **S15** Se eliminan las tools `planning.open`, `planning.close`, `planning.record_decision`,
  `planning.record_note` y `planning.read_report`, el servicio `app/services/planning.py`, las rutas
  `/planning/sessions`, la página `PlanningSessions` y la pestaña de planificación del workspace. Decisiones y
  notas del owner se guardan con `memory.write` / `memory.update`.
- **S16** Ninguna sesión existente se destruye: sus hilos siguen legibles como chats normales y la memoria
  `agent` ya escrita sigue consultable por `memory.read`.
- **S17** El planificador ya no recibe el overlay de planificación; `planning_facilitator.md` y el estado
  `cortex_*` dejan de existir en el camino del turno.
- **S18** El handoff SDB no se toca: `sdb_requested` y `sdb_*` siguen funcionando como hoy.

## Tasks

- **T1** (S7–S10) Parseo tolerante del plan + reintento acotado + causa visible · inline · commit `3e35c819`
- ~~**T2** (S11) Tope de pasos encadenados 4 → 8~~ · **dropped** (L6)
- **T3** (S1–S2, S6) Store de pestañas persistido por usuario con deep link ganador · inline · commit `fc2b20e2`
- **T4** (S3) Reanudar stream de un run vivo al montar el hilo · worker · commit `1fedac79`
- **T5** (S4–S5) Toast + notificación web al terminar un run fuera de vista · worker · commit `42cbfe63`
- **T6** (S12–S14) Quitar la indexación automática de la KB en archivos de proyecto · worker · commit `c01b9bae`
- **T7** (S15–S18) Retirar planificación (backend, rutas, UI, prompts, tests) · worker · commit 7
- **T8** Ayuda, docs y `scripts/test.sh full` + `web` build/test antes del PR · inline · commit 8

## Log

- **L1** (2026-10-28, pedido original, verbatim):

  > hey chat quiero que armes un nuevo worktree para trabajar en unos detalles del asistente virtual de lumat. necesitamos cerrar los ultimos detalles principalmente de funcionalidad.
  >
  > cosas que ya tengo identificadas:
  >
  > - cuando se abre un tab con un chat/hilo nuevo este debe persistir si se cambia de seccion en el panel. o sea, si abro un nuevo hilo/chat y no lo cerre y me cambie a la seccion conversaciones, o clientes. pero luego vuelvo al asistente lumat, la tab de esa chat/hilo debe continuar abierto. tiene que tener procesos en segundo plano, para mayor comodidad de continuidad de conversaciones. Quizas tambien seria bueno un sistema de toast notifications.
  >
  > - hay tools que el asistente aun no puede utilizar. por ejemplo le pedia que hiciera un analisis del chatbot y me respondido:
  > ```
  > Administrador
  > tienes herramientas para hacer una evaluacion seria del chatbot de whatsapp?
  >
  > 27-10-26, 10:18 p. m.
  >
  > AL
  > Agente Lumat
  > No pude planificar esa solicitud de forma segura. Inténtalo nuevamente.
  >
  > 27-10-26, 10:18 p. m.
  > ```
  >
  > - cuando subo archivos al Archivos del proyecto, y son pdf estos se marcan como si se hubieran subido a la kb. y los archivos del proyecto son locales. no son parte de la kb. esta bien eso? o debe subirse a la kb? por que por ejemplo si subo un archivo md, no se sube a la kb.
  >
  > - el sistema de planificacion no esta funcionando. estoy pensando en elminarlo. ya que el agente no es capaz de seguir la logica de la planificacion.
  >
  > eso por ahora. puedes darme un overview

- **L2** (2026-10-28, hallazgo de diagnóstico): la conversación fallida **no está en producción**: está en el
  stack local del main worktree (`infra-db-1`), hilos **79** y **80**. Ambas fallas son `invalid_json` en
  `stage=parse`: hilo 79 `Invalid control character at: line 1 column 541 (char 540)`; hilo 80
  `Extra data: line 3 column 1 (char 168)`. El modelo (DeepSeek; local `deepseek-flash`, prod `deepseek-chat`)
  no honra `response_format={"type":"json_object"}` de forma confiable. Las tools para el análisis del chatbot
  **sí existen** (`analytics.chatbot_metrics`, `analytics.chatbot_conversations`, `conversations.transcript`):
  el planificador cayó al fallback. Producción no usa el asistente desde el 2026-10-21 (hilo máximo 37).

- **L3** (2026-10-28, decisión del owner): planificación → **eliminar** (S15–S18). Avisos → **toast +
  notificación del navegador** (S4–S5). Lectura read-only de producción → **autorizada** (usada en L2, sin
  hallazgos porque la conversación era local).

- **L4** (2026-10-28, decisión tomada por el agente con derecho a veto del owner): archivos de proyecto dejan de
  indexarse automáticamente en la KB (S12–S14). Razón: hoy subir un documento de texto crea dos cosas —un
  archivo y un `KbDocument`— y la UI ya tiene que deduplicarlas con `indexedDocIds`; el agente no necesita la KB
  para leer un archivo (`read_project_file` devuelve el texto exacto), y la ingesta automática convierte una
  falla del proveedor de embeddings en un upload "exitoso" con `status="failed"` y sin causa visible.
  No es destructivo: los `KbDocument` ya creados quedan como están.

- **L5** (2026-10-28, corrección de spec durante T1): S10 pedía a la vez "mensaje que distingue la clase de falla"
  y "conservar el texto exacto". Se conserva el texto exacto y la distinción queda en el diagnóstico persistido y
  el log, que es donde se diagnostica. Motivo: tres tests de integración fijan ese texto como contrato.

- **Evidencia T1** (`3e35c819`): RED observado con los payloads reales de los hilos 79 y 80 (`invalid_json`,
  cuatro tests en rojo) antes de tocar `plan_llm`. GREEN con `uv run pytest tests/unit/test_assistant_planner.py
  tests/unit/test_assistant_planner_json.py`; `bash scripts/test.sh quick` verde;
  `bash scripts/test.sh db tests/integration/test_assistant_chat.py tests/integration/test_assistant_harness_production.py`
  verde; `bash scripts/test.sh shape` → "no shape surface touched". Frontera de slice: 534 líneas autoradas en 2
  commits — el próximo commit abre el slice siguiente. **Pendiente**: re-test en vivo con el modelo real exige
  levantar el stack de este worktree (hoy choca en puertos con el stack del main worktree).

- **L6** (2026-10-28, spec retirada durante T2): S11 (subir el tope de pasos de 4 a 8) se retira por falta de
  evidencia. El evento real del hilo 79 muestra `tool_steps=3` (máximo observado en el stack local, 60 hilos con
  0), el tope es 4 y nunca se alcanzó: el turno no se cortó por el tope sino por el parseo del plan de
  seguimiento. Además el propio hilo 79 prueba que el encadenamiento funciona: plan válido →
  `analytics.chatbot_conversations` ejecutada y en `evidence` → el segundo plan (el que redactaba la respuesta)
  llegó con JSON inválido y ahí se perdió el turno. Subir un techo de llamadas pagadas sin evidencia es costo sin
  causa; T2 se marca **dropped**, no done. `MAX_ASSISTANT_TOOL_STEPS` queda en 4.

- **L7** (2026-10-28, ruido de suite, no regresión): la suite del panel reportó 17 fallas en 10 archivos con el diff
de T3. Evidencia de que es carga y no código: `load average` 66.00 en los 15 min de esa corrida (3.48 al repetir);
  `MutationObserver is not a constructor` + `[vitest-worker]: Timeout calling "onTaskUpdate"` = worker de Vitest
  caído; los 15 s de timeout llegan en cascada. El mismo comando agrupado, mismo árbol, con la máquina descargada:
  **3 fallas en vez de 30 y 122 s en vez de 642 s**, y las 3 que quedan son timeouts en
  `ClientesList.test.tsx` — archivo que este diff no toca (6 archivos, ninguno de esa página), así que no puede
  ser una regresión de T3. `vite.config.ts` ya documenta la familia: *"Under parallel load a single test that
  runs in ~1s alone can blow past the 5s default and flake the whole suite"*. **Pendiente**: `npm test` completo
  verde sin carga (va en T8 y en CI, que corre `npm ci` → `npm run build` → `npm test`).

- **Evidencia T3** (`fc2b20e2`): `npx vitest run src/components/domain/assistantTabs.test.ts
  src/components/pages/AssistantWorkspace.test.tsx` → 41 tests verdes; `npm run build` (tsc -b + Vite) verde.
  Correcciones de revisión aplicadas antes del commit: una sola función de identidad de pestaña
  (`workspaceTabIdentity` exportada, se borró la copia `workspaceTabKey` del componente) y dos tests nuevos de
  aislamiento por usuario + id no entero.

- **Evidencia T6** (`c01b9bae`): RED observado en las dos capas (`kb_document_id` valía `1` en vez de `null`;
  la fila renderizaba el badge "En la KB"). `scripts/test.sh gate` verde; `scripts/test.sh db
  tests/integration/test_project_files.py` → 9 passed; `scripts/test.sh quick` verde; `npx vitest run
  src/components/pages/ProjectResources.test.tsx` → 13 passed; `npm run build` verde. Sin migración: la columna
  `kb_document_id` y el esquema quedan, solo dejan de escribirse; `app/panel/api/serializers.py` sigue
  serializando el campo, así que la forma de la API no cambia. Corrección de revisión aplicada antes del commit:
  `kbState` había sobrevivido en el diálogo de borrado y todo archivo nuevo habría dicho "No indexado" — un
  estado que ya no existe; se reemplazó por `kbNote`, que solo menciona la KB para filas legacy que sí apuntan a
  un documento que se borra junto con el archivo. Referencias históricas al auto-index dejadas como están por
  estar fuera de alcance: `db/migrations/054_project_files_kb_document.sql`, `odd/tasks/asistente-agentes-proyecto.md`
  y `odd/tasks/panel-visual-alignment.md` (registros de comportamiento pasado).

- **Evidencia T4** (`1fedac79`): RED del worker observado en el test de reenganche (esperaba 1 request de stream,
  veía 0) y GREEN con 78 tests; `npm run build` verde. Corrección de revisión **con bug real encontrado por el
  propio worker al marcar la zona sin test**: `streamKeyRef` guardaba la clave `${id}:${run}` sin la generación,
  así que al salir de un hilo y volver al mismo el reenganche se salteaba en silencio — justo el caso que esta
  feature existe para resolver. La clave pasó a `${generation}:${id}:${run}` y se agregó el test de ida y vuelta
  (A → B → A pide el stream de nuevo). **RED verificado revirtiendo el guard**: el test nuevo falla sin él y pasa
  con él (1 failed / 78 skipped, después 79 passed). El build quedó rojo un momento porque el test nuevo se
  escribió fuera del `describe` y no veía el helper `policy` — `tsc -b` type-checkea los tests, así que el gate de
  build es el que lo atrapó; se resolvió inlineando el payload del tool-policy.

- **Evidencia T5** (`42cbfe63`): el aviso vive en `AppShell` y no en `AgentChat`, porque `AgentChat` solo está
  montado para la pestaña activa y no existe cuando el usuario está en otra sección. Lógica pura en
  `assistantRunAlerts.ts` (`disappearedAssistantRuns`, `decideAssistantRunAlerts`), polling de
  `listActiveRuns()` en el shell, un solo `getChatThread` por run desaparecido para título y desenlace, toast por
  el `ToastProvider` existente, y notificación web **solo** con `Notification.permission === "granted"` más
  detección de la API: nunca se pide permiso. Verificación: 43 tests verdes (2 archivos) y `npm run build` verde.
  Dos correcciones de revisión: (1) el polling se apagaba del todo con el snapshot vacío y solo se re-armaba con
  un cambio de ruta, así que un run que terminaba después de esa pausa no avisaba — hueco directo a S4; ahora
  mantiene un heartbeat de 20 s (5 s mientras hay runs activos) y el test del hueco falla contra la versión que se
  apaga (`expected 1 to be greater than or equal to 3`, RED verificado revirtiendo el re-armado); (2) el helper
  del test devolvía `activeRunRequests` como número congelado en el `return`, así que la aserción comparaba 2
  contra 2 para siempre — ahora es un contador vivo. **Follow-up registrado, no corregido**: `AssistantWorkspace`
  ya refresca `listActiveRuns` cada 5 s mientras la vista de chat está montada, así que durante un run en esa
  vista hay dos pollers. No es incorrecto (el shell cubre las otras secciones) y unificarlos obliga a tocar
  `AssistantWorkspace.tsx`, que T7 modifica igual: se resuelve en T7 o en un follow-up, no acá.

## Delivery

Números reales por slice (`git show --shortstat`, código + docs de cada unidad). El branch es lineal y los
commits de doc quedaron intercalados, así que partir en varios PRs exige re-slicear con `cherry-pick`.

| Slice | Commits | Diff |
|---|---|---|
| S1 planificador (T1) | `3e35c819`, `0905337a`, `ca4ae481` | 6 archivos, +406 / −40 |
| S2 pestañas (T3) | `fc2b20e2`, `33f95746` | 7 archivos, +313 / −23 |
| S3 reenganche (T4) | `1fedac79`, `e5721e0c` | 3 archivos, +186 / −7 |
| S4 avisos (T5) | `42cbfe63`, `e11fd70e` | 6 archivos, +345 / −6 |
| S5 archivos vs KB (T6) | `c01b9bae`, `6170e466` | 6 archivos, +77 / −110 |
| S6 retiro de planificación (T7) | `82465575`, `9807867c` | 54 archivos, +231 / −2619 |
| Doc del feature | `e918555b` | 1 archivo, +124 |

**Recomendación: dos PRs**, cada uno una historia que se revisa de una sentada:

- **PR A — "el asistente no pierde el turno ni la conversación"**: S1 + S2 + S3 + S4. ~+1250 / −76, 22 archivos,
  un solo relato (JSON robusto, pestañas que sobreviven, reenganche del run, aviso al terminar). Todo el
  comportamiento nuevo está acá y es lo que el owner pidió probar.
- **PR B — "dos limpiezas: archivos vs KB y adiós planificación"**: S5 + S6. 60 archivos, ~+308 / −2729. La mayor
  parte son borrados mecánicos (una feature retirada, una indexación automática que nunca debió existir); se
  revisa por muestreo y por las dos invariantes: no se destruye data y el handoff SDB queda intacto.

La alternativa es **un solo PR declarando la carga** (4442 líneas autoradas, de las cuales ~2600 son borrados y
~200 son el registro del feature). Es decisión del owner, no del agente: si elige el PR único, la carga se declara
en la descripción con esta misma tabla.

- **L8** (2026-10-28, la fuga que solo atrapa un full): `scripts/test.sh full` #1 falló en
  `tests/functional/test_api_project_files.py::test_upload_text_file_ingests_project_scoped_kb_document`, que seguía
  afirmando el indexado automático que T6 retiró. Estaba fuera de las superficies que se le permitieron al worker
  de T6, así que ningún test dirigido podía verlo: habría llegado a CI **después** del merge. Se reescribió al
  contrato real (201 con `kb_document_id` nulo y `status="ready"`, cero documentos de KB, bytes en disco),
  commit `e2f4a608`. **Lección de proceso**: la selección dirigida verifica la regla que tocaste, no los
  consumidores de la regla; el full en el cierre no es ceremonia.

- **L9** (2026-10-28, el `exit 0` que mentía): la corrida #1 reportó `exit 0` con un test en rojo porque el
  comando terminaba en `| tail -30` y bash devuelve el código del último comando del pipe. La #2 se lanzó con
  `> log 2>&1; exit $code` y así se cerró. Un gate cuyo código de salida pasa por un pipe no es un gate.

## Cierre

**Verificación final, toda con el código de salida real:**

| Gate | Comando | Resultado |
|---|---|---|
| Colección e imports | `bash scripts/test.sh gate` | verde |
| Contrato unitario | `bash scripts/test.sh quick` | verde, 100% |
| Backend completo | `bash scripts/test.sh full` (job-2) | **EXIT=0**, 5m02s |
| Panel completo | `cd web && npm test` (job-3) | **EXIT=0**, 115 archivos / 1337 tests, 1m56s |
| Superficies de shape | `bash scripts/test.sh shape origin/main` | 3 superficies → full obligatorio, corrido |

La diferencia de la suite del panel cierra la discusión de L7: **1337 tests en 1m56s** con la máquina quieta,
contra **17 fallas y 1754s** bajo carga. No era el cambio, era la carga.

**Estado del branch**: 17 commits, 4648 líneas autoradas sobre `origin/main`.
**Pendiente y fuera del alcance del agente**: cortar el o los PRs, pushear y abrir la revisión — decisión del
owner. El refresh de Graphify (`graphify . --update`, una vez por sesión según `AGENTS.md`) queda para el cierre
de sesión, cuando decida si el `graphify-out/` regenerado se commitea acá o aparte.
