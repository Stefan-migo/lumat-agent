# saludo-retorno — un saludo en medio del hilo no reinicia la presentación

Rama `odd/saludo-retorno` · worktree `../lumat-agent-odd-saludo-retorno` · base `ff58e4813`.

Residuo declarado del corte `captura-pregunta` (#854): aquel arregló el saludo **con** captura
pendiente y dejó abierto el saludo **sin** captura pendiente, que necesita una decisión de producto.
La decisión está tomada (L2) y este es el corte que la implementa.

Riesgo: **bajo**. Sin migraciones, sin contrato público nuevo, un texto configurable más y una rama
que ya existe. El riesgo real es de producto, no técnico: el texto que elige el dueño es lo que el
cliente lee.

## Contexto medido

Escenario `real-solo-sabados`, turno 2, verbatim del corpus: un mensaje que es sólo `Buen dia`,
después de que la clienta ya contó el edificio, el tema (mantención de caldera en mayo) y su pregunta
por los sábados. Hoy el bot contesta con el saludo de primer contacto:

> `Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar.`

Le vuelve a preguntar el nombre a alguien que ya se presentó. El mecanismo son dos piezas:

- `receive` (`app/chat/nodes/receive.py:292`): en turno > 1, sin `_pending`, con saludo puro, responde
  `_greeting(..., short=False)` — el mismo texto del primer contacto.
- `_flow_start` (`app/chat/graph.py:173`): con saludo y sin `_pending`, termina el turno (`END`).

## Specs

- **S1 — Un saludo puro en un turno posterior no reinicia la presentación.** La respuesta no puede
  contener `soy Max` ni `¿Con quién tengo el gusto?`. Debe devolver el saludo y retomar en una línea,
  sin repetir el ritual de apertura. Decisión del owner, verbatim en L2.

- **S2 — Nombra el tema cuando ya lo tiene, y no inventa cuando no.** Si hay una visita agendada, el
  tema es el servicio de esa visita; si no, el `equipment` capturado; si no hay ninguno de los dos, la
  respuesta retoma sin nombrar tema. Nunca nombra un tema que el estado no sostiene: un tema
  equivocado es peor que ninguno.

- **S3 — Lo que ya estaba cerrado no se toca.** El saludo del **primer** turno sigue presentándose
  (CM-1) y el saludo **con** captura pendiente sigue yendo a `capture` (#854): `_flow_start` conserva
  su `"capture" if "_pending" in ...` sin cambios. Un test por cada uno.

- **S4 — El texto es del dueño, el flujo no.** El saludo de retorno es un mensaje fijo configurable
  desde el panel como los otros. El marcador de tema es exactamente `{{tema}}` y sólo en esa clave: el
  validador de mensajes fijos rechaza cualquier otra llave, para que un `{{fecha}}` sin lector nunca
  llegue al cliente.

- **S5 — La detección de saludo no se ensancha.** Qué cuenta como saludo puro lo decide
  `is_greeting_only` y no cambia: `hola, necesito una visita` sigue siendo contenido y sigue yendo a
  clasificación.

## Tasks

| ID | Spec | Ruta | Commit |
| --- | --- | --- | --- |
| T1 | S1-S5 | este documento | `por commitear` |
| T2 | S1, S2, S3, S4, S5 | test primero en `tests/unit/test_chat_greeting.py` y `tests/unit/test_reply_texts.py`, ver RED | `por commitear` |
| T3 | S1, S2, S4 | `app/chat/nodes/receive.py` + `app/services/settings.py`, ver GREEN | `por commitear` |
| T4 | S1 | medir `real-solo-sabados` y `simple-saludo-variante` con `--only`, sin juez, y leer el turno | `por commitear` (L8) |
| T5 | — | gates `quick`, `full` y el panel si toca `web/` | `por commitear` (L9) |

## Log

- **L1** — Pedido del owner, verbatim: «puedes explicarme cada caso del saludo. donde tengo que tomar
  desicion asi cerramos la desicion ahora? explicalo de forma sencilla porfavor».
- **L2 — Decisión del owner, verbatim** (opción elegida sobre las tres explicadas): «b) Saludar de
  nuevo y retomar en una línea — `Hola de nuevo. Seguimos con la caldera: cuéntame en qué te ayudo.`
  Determinista, sin llamada al modelo, y nombra el tema cuando ya lo capturamos.»
- **L3** — Mecánica leída antes de escribir: `receive` (`app/chat/nodes/receive.py:292-300`) responde
  `_greeting(short=False)` en turno > 1 sin `_pending`; `_flow_start` (`app/chat/graph.py:173-174`)
  devuelve `END` en ese caso y `"capture"` cuando hay `_pending`. Los temas disponibles en el estado
  son `booking["service"]` y las claves de `CAPTURE_FIELDS` (`capture.py:73`), donde el equipo es
  `equipment`.
- **L4** — Restricción encontrada en el validador: `validate_fixed_messages`
  (`app/services/settings.py:1235`) sólo deja `{{nombre}}` en `greeting_name`/`greeting_short_name` y
  rechaza llaves en cualquier otro mensaje fijo. Para nombrar el tema hay que declarar el marcador
  exacto de la clave nueva, no relajar la regla.
- **L5 — Implementación.** `_resume_topic(state)` en `receive.py` (el servicio agendado manda; si no
  hay, el `equipment` capturado; si no hay ninguno, tema vacío) y `_resume_greeting(session, state)`
  que elige entre `greeting_resume` y `greeting_resume_topic`. El validador pasó de un `if` sobre dos
  claves a `_FIXED_MESSAGE_MARKERS: dict[str, str]` —cada clave declara su marcador exacto— porque
  una lista de claves permitidas no dice **qué** marcador admite cada una.
- **L6 — Trampa: el 400 no venía del validador.** Con las dos claves nuevas el POST del panel seguía
  devolviendo 400 aunque `validate_fixed_messages(dict(MESSAGE_DEFAULTS))` pasaba: el rechazo estaba
  en `MessagesBody` (`app/panel/api/routes/settings.py:107`), el modelo Pydantic de la ruta, que
  **enumera los campos** y se come el error antes de llegar al servicio. Los campos nuevos van
  opcionales con su texto embarcado, como `confusion` y `smalltalk_decline`, para que un cliente de
  panel viejo siga guardando su mapa.
- **L7 — Dos contratos pineados por tests, actualizados a propósito.**
  `test_settings_update_messages_audited` (el mapa editado) y el test que fijaba «sólo `{{nombre}}`
  en los dos saludos con nombre», que pasa a `test_settings_fixed_messages_accept_only_their_own_marker`
  y ahora recorre los tres pares clave/marcador, incluyendo que `greeting_resume_topic` rechace
  `{{nombre}}`. Ninguno se relajó para pasar: los dos describen el contrato nuevo.
- **L8 — T4, medido.** Corrida `saludo-retorno-2026-11-23`, `--only real-solo-sabados --only
  simple-saludo-variante --no-judge --reset`, `deepseek/deepseek-flash`, KB `34670f5b3d75`, base de
  test derivada del worktree (puerto 6276). `2/2` pasan, cero gates.

  Turno 2 de `real-solo-sabados` (el cliente escribe sólo `Buen dia`), **antes**:

  > Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo
  > ayudar.

  Turno 2, **ahora**:

  > Hola de nuevo. Seguimos donde quedamos: cuéntame en qué te ayudo.

  `simple-saludo-variante`, que es **primer** turno, conserva la presentación completa: «Hola, soy Max,
  el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar.» Eso es
  S3 verificado por efecto, no por lectura del código.

  Salió la variante genérica y no la del tema, y es correcto: en ese punto del hilo no hay `equipment`
  capturado ni visita agendada. La rama del tema queda cubierta por
  `test_the_resume_topic_names_only_what_the_state_holds`; el corpus no puede ejercitarla porque en
  `real-solo-sabados` el bot todavía está preguntando la comuna cuando llega el saludo. Declararlo es
  más honesto que decir que la corrida validó las dos ramas.
- **L9 — T5, gates.** Cada comando redirigido a `~/.cache/cap-gates/` con su exit leído como valor
  propio, en este orden (comparten la base derivada del worktree, puerto 6276):

  | Comando | Exit |
  | --- | --- |
  | `bash scripts/test.sh unit` | `0` |
  | `bash scripts/test.sh quick` | `0` |
  | `bash scripts/test.sh db tests/functional/test_api_kb_settings.py` | `0` |
  | `bash scripts/test.sh db tests/integration/test_greeting_variants.py tests/integration/test_db.py` | `0` |
  | `bash scripts/test.sh full` | `0` |
  | `npm run build` (`tsc -b` + vite) | `0` |
  | `npm test` | `0` |

- **L10 — seis contratos rotos, ninguno por casualidad.** Agregar dos claves de mensaje fijo rompió
  seis lugares distintos, y cada uno hubo que actualizarlo **al contrato nuevo**:

  1. `test_the_database_aborts_a_transaction_idle_beyond_the_safety_window`
     (`tests/integration/test_db.py`). No lo rompió el corte: lo rompió mi atajo. Relajé el timeout de
     la base de test con `ALTER DATABASE … 15min` para que el arnés no matara un turno largo, y ese
     test exige **180 s como default de la base** porque su docstring explica que el guard tiene que
     vivir ahí y no en la aplicación. Revertido a `180s`. El arreglo correcto para el arnés es una
     opción de sesión (`PGOPTIONS`), no tocar la base; queda anotado como deuda.
  2. `test_later_bare_greeting_without_capture_uses_named_variant` →
     `test_later_bare_greeting_without_capture_resumes_instead_of_presenting`. El test viejo fijaba
     exactamente la conducta que el owner cambió, así que se reescribió y ahora también afirma que la
     respuesta no contiene `Soy Max` ni `Con quién tengo el gusto`. El test hermano del caso con
     captura pendiente (#854) no se tocó.
  3. `web/src/types.ts` — el tipo de `messages` enumera las claves.
  4. `Settings.test.tsx` — payload explícito, fixture compartido y el conteo `13 → 15` mensajes fijos.
  5. `SettingsEmail.test.tsx` — otro fixture.
  6. `_shared/mockData/settings.test.ts` — el test que **fija la lista exacta** de claves del mock.

  Ninguno se relajó ni se borró para pasar el gate. La consecuencia práctica es que el panel ahora
  muestra **15** mensajes fijos y el dueño puede editar los dos nuevos desde Configuración.
- **L11 — Decisión declarada: el nombre no se usa en el saludo de retorno.** La variante anterior
  nombraba al cliente (`greeting_name`), y esta no. Es deliberado: el hilo ya está abierto, el bot sabe
  con quién habla, y entrelazar nombre y tema exigiría cuatro claves (con/sin nombre × con/sin tema)
  en vez de dos. Si el owner quiere el nombre, es agregar una clave más y un marcador, no rediseñar el
  flujo.
