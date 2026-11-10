# chat-rafagas — una ráfaga de mensajes es UN turno

Worktree `../lumat-agent-odd-chat-rafagas`, rama `odd/chat-rafagas`, base `main 341dc1c8`.
Origen: conversación de producción del 2026-11-06 17:12 con el cliente Max Escanilla (dos mensajes
seguidos rompieron el turno). Diagnóstico completo en Engram `chat/burst-de-mensajes`.

## Specs

**S1 — Una ráfaga de mensajes produce UNA respuesta fusionada.**
Decisión del owner, verbatim: `Una sola respuesta fusionada`.
La conversación que lo originó, verbatim:

```
6 de noviembre de 2026
Hola
17:12
Lumat
Hola, Max Escanilla. Soy Max, el asistente de Lumat. ¿En qué te puedo ayudar?
17:12
Cómo estás?
17:12
Lumat
Con gusto. ¿Te puedo ayudar en algo más?
17:12
```

Un cliente que escribe N mensajes seguidos recibe **un solo** mensaje de WhatsApp que atiende la
ráfaga completa, no N respuestas. El bot espera una ventana corta de silencio antes de responder; la
ventana es configurable y su valor por defecto queda documentado.

**S2 — Un turno social sin contenido se responde con una línea fija cálida y configurable.**
Decisión del owner, verbatim: `Línea fija cálida configurable`.
`¿Cómo estás?`, `¿qué tal?` y variantes que no plantean una necesidad de servicio se responden con
ese texto, editable desde el panel. Nunca vuelven a recibir la línea de cortesía
`Con gusto. ¿Te puedo ayudar en algo más?`, que no responde la pregunta.

**S3 — El primer contacto se reconoce también cuando llega en ráfaga.**
Un cliente nuevo que escribe `Hola` y `Cómo estás?` seguidos conserva el tratamiento de primer
contacto (saludo con su nombre y una sola apertura), tal como si hubiera escrito un solo mensaje.

**S4 — Restricción de implementación (no es requisito de producto): una conversación nunca corre dos
turnos a la vez.**
Hoy dos webhooks seguidos pueden ejecutar dos `run_conversation` concurrentes sobre la misma
conversación, con historial incompleto y dos llamadas al LLM. La fusión de S1 exige un solo turno
por ráfaga, así que la exclusividad por conversación es condición de S1, no un extra.

**S5 — Nada de lo existente se degrada.**
Estado humano (HH-5), captura, emergencia, KB, handoff y el contrato del webhook (200 antes de
procesar, dedup por wamid, retry por sweep) siguen igual. Los tests que fijan "N mensajes = N
respuestas" se actualizan al comportamiento nuevo, no se borran.

## Tasks

| ID | S# | Route | Commit |
|---|---|---|---|
| T1 | S4 | inline — lock por conversación en el sweep, RED de concurrencia primero | `88a1cd22` |
| T2 | S1 | inline — ventana de silencio + drenaje de la conversación + ráfaga colapsada en el turno | `9a0ad123` |
| T3 | S3 | inline — contador de turnos por conversación (migración 064) | `9a0ad123` |
| T4 | S2 | worker + parent — familia social: clave `messages.social`, detección determinista, respuesta fusionada | `c17cda89` |
| T5 | S2 | worker + parent — campo en el panel de configuración + tipo de la API + stories | `c17cda89` |
| T6 | S5 | inline — cerrar: `quick`, `db` focalizado, `full` de frontera, CHANGELOG | — |

Frontera de entrega: el feature acumula ~1394 líneas sobre `origin/main`, muy por encima del slice de ~400.
Se entrega en PR encadenados: **slice 1** `88a1cd22` + `9a0ad123` (lock por conversación, ráfaga = un turno,
contador de turnos), **slice 2** `c17cda89` + `42599426` (línea social configurable y sus variantes), **slice 3**
`9e777d0f` (caminos de falla del burst que encontró la verificación independiente), con este documento y el
CHANGELOG en el slice que abra la entrega.

Riesgo alto declarado: T1 (concurrencia, ítem 4) y T3 (migración, ítem 1). Cada uno va en su propio
commit para que la revisión pueda tomarlos solos.

## Log

**L1 — pedido del owner, verbatim:**

```
Necesito que revises la conversacion con Max Escanilla. en esa conversacion se demostro algo interesante y un bug. Aqui la conversacion:

[transcripción del 6 de noviembre de 2026 arriba]

Max saludo con dos mensajes. Hola. y luego muy rapido antes que el agente contestara dijo (como estas?) entonces paso lo de la conversacion de arriba. se rompio y no supo mantener la conversacion el chat. como podemos solucionarlo?
```

**L2 — decisiones del owner (2026-11-09), verbatim:**
- Ráfaga: `Una sola respuesta fusionada`.
- Social: `Línea fija cálida configurable`.

**L3 — diagnóstico que fija el alcance (código de `main 341dc1c8`):**
`is_greeting_only` (`app/chat/nodes/receive.py:87`) exige una palabra de `GREETING_WORDS`, así que
`como estas` no es saludo; el clasificador lo manda a `smalltalk` (`app/services/prompts.py:93`) y
`respond` (`app/chat/nodes/respond.py:468`) devuelve la línea enlatada sin LLM. En paralelo, cada
POST encola su propio `sweep_received` (`app/webhook/router.py:69`), no hay lock por conversación, y
`state.turn` cuenta mensajes persistidos (`app/chat/state.py:269`), no turnos: el primer contacto se
pierde con una ráfaga.

**L4 — decisiones de implementación tomadas al escribir T1–T3 (2026-11-09):**
- La exclusividad por conversación es un lock en proceso, como `RateLimiter`: el diseño corre un solo
  worker (D1). Un advisory lock de Postgres queda como camino de salida documentado; un row lock no
  sirve porque el grafo persiste en sesiones separadas y se bloquearía contra su propia escritura
  (medido: el primer intento con la transacción del claim abierta colgó la suite).
- El colapso de la ráfaga es sobre la corrida entrante **en vuelo** (`status = processing`), no sobre
  todo historial: un takeover humano deja muchos inbound seguidos sin outbound y no debe reescribirse
  en un solo bloque. Medido: sin ese filtro fallaban `test_chat_state` y los 25 de `test_chat_booking`.
- `state.turn` pasa a `turn_count + 1` (migración 064 con backfill desde el historial inbound), así el
  primer contacto en ráfaga sigue siendo turno 1.

**L5 — revisión de la entrega del worker (2026-11-09):** el worker dejó T4/T5 en `partial`. Tres defectos
reales, corregidos por el parent:
1. `is_greeting_only` devolvía `True` para un turno social: rompía el nombre del predicado y arrastraba
   `has_content`, que decide si el saludo es el corto o el largo. Se separó: `is_greeting_only` vuelve a su
   semántica y `_flow_start` corta la clasificación con `is_greeting_only(state) or is_social_only(state)`.
2. El test de frontera del panel dejaba `social: ""` en el fixture: la validación del panel exige todo mensaje
   no vacío, así que el guardado no llamaba a `fetch` y el test fallaba con "Number of calls: 0". El fixture
   ahora trae un texto real y el cuerpo esperado lo refleja.
3. `types.ts` no tenía `social`, así que el worker lo había resuelto con un tipo local y un `as`; `tsc -b`
   después falló en `SettingsEmail.test.tsx` por el campo faltante. Se agregó al tipo de la API, se quitaron
   los casts y se arreglaron los dos fixtures restantes.
También hubo que actualizar `test_retry_storm_single_processing_pass`: con el contador de turnos esos tres
mensajes son el primer contacto, así que la respuesta es el saludo corto y no una aclaración.

**L6 — lo que encontró la suite completa (2026-11-09), y la corrección:**
1. `test_greeting_variants[hola cómo va?]`: la familia social se comía un modismo de saludo. "¿cómo va?" y
   "¿qué tal?" son cómo este cliente dice *hola*, no preguntas sobre el asistente. `_SOCIAL_QUESTION_ENDINGS`
   queda sólo con `como estas` y `todo bien`; el resto sigue siendo saludo.
2. `test_chat_manage::test_preset_answer_preempts_the_kb_miss_path`: el seeder insertaba un inbound "ya
   contestado" sin tocar `turn_count`, así que el turno invocado se veía como primer contacto y recibía el
   saludo. El seeder ahora declara `turn_count = 1`, que es lo que de verdad representa.
3. El cierre con `full` se trabó una vez por correr dos suites a la vez contra la misma base de test
   (`suite-truncate-stall`): una transacción `idle in transaction` bloqueando el `TRUNCATE` del fixture. No era
   código; se limpiaron los backends y se corrió sola.

**L7 — verificación independiente (`gentle-ai-verify`, 2026-11-09).** PASS en los cinco focos de riesgo
(concurrencia, ciclo del lock, semántica del burst, migración, colapso), con dos bloqueantes y varios avisos.
Resuelto en `9e777d0f` y `42599426`:

1. **B1** — `test_processing_failure_marks_failed` parcheaba `process_message`, que el sweep ya no llama: el
   test corría el turno real de primer contacto y llegaba a un `httpx.post` sin mockear a graph.facebook.com,
   pasando sólo porque la llamada fallaba. Parcha `process_turn`.
2. **B2** — `¿qué tal?` no recibía la línea social: S2 lo nombra explícitamente. La detección ahora cubre
   `como estas`, `como anda(s)`, `que tal`, `como va` y `todo bien`, con dos guardas: un modismo precedido por
   palabra de saludo sigue siendo saludo (`hola cómo va?`), y `todo bien` sólo cuenta como pregunta social si
   el mensaje trae signo de interrogación (es también como el cliente cierra un trabajo).
3. **Estado humano** marcaba `PROCESSED` un mensaje cuya descarga de media falló, sin reintento ni evento:
   ahora sólo se consumen los mensajes cuya media se resolvió.
4. **Texto de sistema de Meta** (`MessageType.OTHER`) podía colarse en la ráfaga: el colapso lo excluye, igual
   que ya lo hacía la corrida del grafo.
5. **Sin test para la ventana de silencio**: borrar el `sleep` dejaba la suite verde. Se agregó el test de
   "el segundo mensaje llega durante la espera y la respuesta es una sola".

Avisos que quedan abiertos, aceptados y documentados: la espera de silencio corre dentro del lock (10
conversaciones pendientes ≈ 30 s de cola), el lock es de proceso y nada en código impone el worker único
(D1), y no hay test del backfill de la migración 064 ni uno que garantice `turn_count` exacto con turnos
fallidos. El verificador dejó listas las propuestas para esos tres.

**L8 — cierre (2026-11-09).** Evidencia real, no intención:
- `bash scripts/test.sh full` sobre `f46e6b37`, sola, base de test limpia: **exit 0**, cero `FAILED`/`ERROR`.
- `bash scripts/test.sh db` focalizado: `test_webhook_ingest.py` (43), `test_chat_state.py`, `test_smalltalk.py`,
  `test_greeting_variants.py`, `test_chat_booking.py`, `test_chat_manage.py`, `test_functional_api_kb_settings.py`.
- Panel: `npm ci` → `npm run build` (tsc -b + vite) → `npx vitest run` = **1408 passed**.
- `gentle-ai review assess` con `workspaceRoot` del worktree: `risk: high` (escalación ítem 4), `nativeRisk:
  passive`, `reviewDue: false` → no corresponde review nativo; sí corresponde el verificador independiente,
  que corrió y cuyos hallazgos están en L7.
- Commits: `bda51a0b` doc, `88a1cd22` lock, `9a0ad123` ráfaga = un turno + migración 064, `c17cda89` social +
  panel, `ba656943` modismos de saludo, `8217a0f1` seeders, `42599426` variantes de S2, `9e777d0f` caminos de
  falla, `f46e6b37` este registro.

Sin push, sin PR, sin merge: la entrega es decisión del owner. El worktree y la rama `odd/chat-rafagas` quedan
en pie para los PR encadenados.
