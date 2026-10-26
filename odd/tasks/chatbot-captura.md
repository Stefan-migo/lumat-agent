# chatbot-captura — consentimiento real, captura validada y superficie redactada

**Rama:** `odd/chatbot-captura` (worktree `../lumat-agent-odd-chatbot-captura`) · **Base:** `origin/main` `4b24e71b`
**Origen:** QA manual de 5 conversaciones (`#13`–`#17`) en el stack aislado `lumat-harness` sobre `main` @ `456a0294`.
**Entrega:** dos slices encadenados — (1) captura y consentimiento, (2) redacción asistida detrás de un flag.

## Specs

**S1 — El consentimiento es una decisión, no un campo más, y nada se guarda ni se reserva sin un sí explícito.**
Hoy la evidencia de `#15`: la cita se confirmó con `consent = "quiero hacer mantencion de caldera"`, y en `#16`/`#17` el email y la dirección se guardaron ANTES de preguntar. Reglas:
(a) `sí` (allowlist existente `_YES_WORDS`) → `record_consent` + seguir al booking;
(b) `no` (`_NO_WORDS`) → **no** reservar, **no** persistir `email`/`address`, responder `capture_consent_refused` y derivar `consent_declined`;
(c) dudoso o `is_skip` → repreguntar el consentimiento, máximo 2 veces (`MAX_ASKS_PER_FIELD`), después derivar `consent_unclear`;
(d) el **orden** de preguntas sigue siendo el del owner (`chat.conduct.orden`) y el consentimiento se pregunta al final, después de los campos de datos y antes de la reserva. La protección no viene del orden: la ficha del cliente y la cita solo se escriben con un sí explícito (`_persist_captured` sincroniza la ficha únicamente cuando el consentimiento es verdadero). Ver L12.
Hoy `app/chat/nodes/capture.py:258-272` guarda la respuesta y devuelve `next_step: booking` **sin mirarla nunca**.

**S2 — La captura no guarda texto que no responde la pregunta.**
Se elimina el fallback `app/chat/nodes/capture.py:291-295` (`captured[target] = _current_text(state)`), que produjo literalmente:
`#14 comuna = "Soy Felipe. estoy con un problema con mi calefont, dejo de funcionar hace un par de dias"`;
`#16 address = "Soy Braulio, me dieron este numero. tengo un problema con mi calefont. Necesito que lo vengan a ver."`;
`#16 consent = "dejo de prender hace un par de dias."`;
`#15 failure = "quiero hacer mantencion de caldera"`.
Reglas:
(a) si el turno no extrajo nada para el batch `_pending` y no es skip → **repreguntar** el mismo batch (incrementa `_asked`) y al llegar a `MAX_ASKS_PER_FIELD = 2` derivar `campo_sin_respuesta` (mecanismo que ya existe);
(b) validación por campo antes de aceptar un valor: `comuna` normalizada (acentos/mayúsculas/espacios) contra `coverage.communes` —hoy `comuna_cubierta` compara igualdad exacta— o `unknown`; `email` contra regex; `consent` solo allowlist; `failure`/`address` nunca reutilizan un mensaje previo del cliente ni el texto completo del primer turno;
(c) el extractor puede llenar **cualquier** campo, pero solo si el valor pasa el validador de ese campo (`comuna` en cobertura, `email` con forma válida, `name` sin texto de relleno ni el mensaje entero, etc.), y ningún campo acepta como valor el mensaje completo del cliente. Lo que se elimina es el fallback que copiaba el mensaje entero, **no** la extracción válida fuera del batch: descartarla hace que el flujo repita la misma pregunta hasta derivar cuando el cliente contesta otro dato primero (replay T9, conversación #20).

**S3 — La pregunta va precedida por un reconocimiento determinista.**
Precedente ya en el código: `if batch == ["failure"] and label: ask = f"Entiendo, es un problema con tu {label}. {ask}"` (`capture.py:374-375`). Se generaliza con un texto configurable (`capture.ack`) construido solo con datos ya capturados y no sensibles (nunca `email`/`address`).

**S4 — En un servicio preventivo no se pregunta por la falla.**
Evidencia `#13` msg 43: a "quiero hacer mantencion de caldera" respondió "Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?". Regla determinista: `capture.preventive_keywords` (default `mantencion`, `mantención`, `mantenimiento`, `revision`, `revisión`, `limpieza`, `preventiva`), normalizado con `_normalize` y evaluado sobre **toda la ventana de mensajes del cliente**, no solo el turno actual; si el pedido es preventivo y `failure` no fue capturado, `failure` se saltea y se registra en `captured_data["_skipped"]`. La marca se calcula una vez en `capture()`, antes de cualquier camino de pregunta, para que `_ask_next` y `_reask_pending` la respeten por igual (replay T9, conversación #19).

**S5 — Redacción asistida: la plantilla es el contrato y el validador es la puerta.**
`chat.conduct.redaccion` existe hoy (`CONDUCT_REDACCIONES = ("llm", "plantilla")`) y **ningún código lo lee**; en ambas bases no hay fila guardada. Pasa a ser el interruptor real: default `"plantilla"` (= comportamiento actual). Con `"llm"` se reescribe la **superficie de captura**: (a) los textos fijos de captura (`capture_consent`, `capture_consent_refused`, `capture_consent_unclear`, `capture_ack`, `capture_evidence`) y (b) **la pregunta dinámica de campo** que arma `_ask_text` sobre `capture.questions` — que es, precisamente, lo que se sentía rígido en `#13`–`#17`. La máquina sigue decidiendo **qué campos** se preguntan; el modelo solo redacta. Si el validador rechaza, o hay excepción, timeout o falta de proveedor → se responde la plantilla. El modelo nunca decide qué campo pedir ni inventa valores.

El validador mecánico no intenta verificar "misma intención" (no es verificable): exige batch cerrado (solo campos pendientes), forma interrogativa, sin markdown/emojis, largo acotado, y hechos de la allowlist. La equivalencia de intención la cubre S7: si el texto reescrito no hace que el extractor llene el campo correcto, esa clave vuelve a plantilla.

**S6 — Los validadores son funciones puras y testeables sin modelo.**
Cuatro reglas: (a) batch cerrado — la respuesta no puede preguntar por un campo fuera de `_pending`; (b) hechos permitidos — solo puede mencionar lo que está en `facts` (nombre, equipo, comuna ya capturada, campos pendientes); ninguna cifra, precio, plazo, horario ni técnico que no venga de `facts`; (c) forma — largo máximo, sin markdown ni emojis; (d) no repetir la respuesta del turno anterior.

**S7 — La redacción no puede degradar la extracción.**
Test de ida y vuelta obligatorio: con un extractor falso, el texto reescrito por el modelo hace que el campo correcto se llene. Si ese test falla para una clave, la clave queda en plantilla.

**Non-goals (van a un feature posterior):** disponibilidad pedida por el cliente (P3), preguntas en prosa en el selector de horarios (P4), hechos de la cita en el respond (P5), formato único de fecha (P6), despedida (P7), estabilidad de intención (P8), y la salida estructurada `not_applicable`.

## Tasks

| ID | Spec | Qué | Route | Commit |
|---|---|---|---|---|
| T1 | S1 | RED: `tests/unit/test_capture_consent.py` — sí/reserva, no/no-reserva/no-PII, dudoso→repregunta→deriva | worker | C1 |
| T2 | S1 | Gate real en `capture.py` + textos `capture_consent_refused`/`capture_consent_unclear` en `settings.py` | worker | C1 |
| T3 | S2 | RED: `tests/unit/test_capture_validation.py` con los 5 mensajes reales como fixtures | worker | C1 |
| T4 | S2 | Quitar el fallback del mensaje entero; validadores por campo; merge solo del batch | worker | C1 |
| T5 | S3 | `capture.ack` generalizado | worker | C1 |
| T6 | S4 | `capture.preventive_keywords` + `_skipped` | worker | C1 |
| T7 | S5,S6 | `app/chat/phrasing.py` (facts, rewrite, validate, fallback) + wiring en `replies.py` solo para captura/smalltalk + `redaccion` default `"plantilla"` | worker + parent | C2 |
| T8 | S7 | Tests de ida y vuelta + validadores + fallback (sin red) | worker + parent | C2 |
| T9 | — | Verificación: `bash scripts/test.sh quick`, replay de `#13`–`#17` en el harness, `npm run build` si toca `web/` | parent | C1+C2 |
| T10 | — | Commits C1 y C2 con mensaje convencional | parent | — |

## Evidence

| Slice | Commit | Contenido | Líneas autoradas | Verificación |
|---|---|---|---|---|
| C1 | `feat(chat): gate consent and validate capture answers` | S1–S4: consentimiento, captura validada, ack, preventivo | 539 | 14 focales + `quick` |
| C2 | `feat(chat): let the model word capture questions behind a validator` | S5–S7: redacción asistida detrás de `redaccion` | ~324 | 20 focales de phrasing + `quick` |
| C3 | `fix(chat): keep valid capture answers and honour a preventive request` + `fix(chat): hold the capture contract the full suite pins` | R1/R2 del replay + rechazo explícito de consentimiento | 140 | 41 focales + `quick` + replay |
| docs | `docs(chatbot): record the capture replay evidence and the slice boundary` | L10/L11 y esta tabla | — | — |

**Replay de aceptación (v3, teléfonos frescos por corrida):** `FALLAS: ninguna`.

| Conv | Escenario | Resultado medido |
|---|---|---|
| #28 | falla completa | cita 26/10 16:00, `comuna`/`email` válidos, `consent="si"` |
| #30 | mantención pidiendo visita | `_skipped=["failure"]`, nunca preguntó la falla, cita 26/10 17:00 |
| #31 | consentimiento negado | sin cita, `consent="no"`, sin `email` ni `address`, deriva |
| #32 | dato fuera de turno ("vivo en Ñuñoa, no cacho el equipo") | `comuna="Ñuñoa"` guardada, cita 27/10 09:00 |
| #29 | mantención por consulta libre | no entra a captura: la intercepta una respuesta libre del LLM → **P8, fuera de alcance** |

Línea base para comparar: 2/5 conversaciones con cita, una de ellas con `consent` falso y varias con datos corruptos.

**Frontera de slice:** el PR 1 quedó en 704 líneas autoradas en 4 commits (el doble del presupuesto de ~400), muy por encima del presupuesto de ~400 de una revisión. Estrategia propuesta (decisión del owner): **dos PRs encadenados** — (1) captura y consentimiento = C1 + C3, que es la historia de compliance y corrección, y (2) redacción asistida = C2, que es una mejora de superficie reversible por flag. Eso requiere reordenar C3 antes de C2 en la rama (historia local, sin push). Alternativa: un PR único de 1003 líneas con guía de review por commit.

## Log

**L1** — "ok puedes revisar los casos que estuve testeando? hay una mejora considerable pero seguimos teniendo errores. Necesito que revises las conversaciones testeadas en el main. y dame un overview de los problemas que puede presentar"

**L2** — "#13. este caso fue mio. le pregunte por agenda pero no habia configurado los horarios del tecnico. lo hice minutos despues." → `booking_unavailable` en `#13` es comportamiento correcto; sale del diagnóstico.

**L3** — "Necesito que me explique claramente y sencillamente cuales son los problemas y como solucionarlos desde el codigo." + "siento que cuando entra en capture es un poco rigido. se sintio mucho mas fluido cuando el llm escribia el mensaje." + "existe la posibilidad sin romper lo deterministico, que la respuesta de la captura de datos (preguntas), sean una referencia y que si aplican se utilicen como estan. pero sino aplican se reescriban por el llm?"

**L4** — "ademas todas las cosas que obersvaste estan bien. los 8 puntos que detallaste"

**L5** — "si va lo agregamos para que entre en el primero PR junto con la captura"

**L6** — "1. confirmo [split en dos commits] 2. doy el consentimiento [worktree]"

**L7** — Revisión del parent sobre C1: dos defectos introducidos por el agente y corregidos antes del commit, con RED propio. (a) `capture_ack` estaba duplicado en `REPLY_TEXT_DEFAULTS` y en `SETTINGS_DEFAULTS["capture.ack"]`, con `get_capture_ack` leyendo el segundo: la fila que el panel edita no hacía nada. Ahora hay una sola fuente (`reply.texts`). (b) El ack se anteponía a **cada** pregunta posterior, repitiendo "Gracias Ana." — el tic que la feature viene a eliminar. Ahora se recuerda `_acked` y se suprime la repetición idéntica. Ajuste de alcance: S5 se limita a textos de captura; smalltalk entra con P7 y el control de panel queda como follow-up.

**L8** — El agente detecta un conflicto real entre S5 y S7: el allowlist original de cinco claves dejaba afuera la pregunta dinámica de campo (`capture.questions` vía `_ask_text`), que es justamente lo que el owner señaló como rígido, y sin ella el round-trip de S7 no se puede ejercitar. Decisión del parent: **ampliar S5** a la pregunta de campo, manteniendo que la máquina decide qué campos se preguntan y que el validador exige batch cerrado; la verificación de intención queda en el round-trip, no en una comparación mecánica imposible.

**L9** — Revisión del parent sobre C2, tres correcciones antes del commit. (a) El validador usaba una tabla de palabras clave por campo para "batch cerrado": rechazaba "Entiendo, tu caldera no enciende. ¿En qué comuna está?" y "Para coordinar la visita, ¿en qué comuna te encuentras?" — o sea, descartaba casi toda reescritura natural y el feature pagaba una llamada para devolver la plantilla. Se reemplazó por dos reglas decidibles: el draft conserva exactamente el número de signos de interrogación de la plantilla, y una guarda angosta solo para `email`/`address` cuando esos campos no están en el batch. Verificado con RED propio sobre las dos reescrituras naturales. (b) Una sola llamada por mensaje: `capture_ack` y `capture_evidence` salen de la superficie fraseable porque viajan dentro del mismo mensaje que la pregunta; fraseando cada fragmento eran hasta tres llamadas por turno sin cambiar una palabra de lo que el cliente lee. (c) Hueco de presupuesto conocido: la llamada de redacción no pasa por `costs.record_llm_cost` porque el estado del grafo no lleva el `message_id` que esa función requiere; threadearlo toca `state.py` + `run_conversation` y va como slice propio. Mitigación actual: máximo una llamada por turno y default `plantilla` (cero llamadas).

**L10** — Replay de aceptación (T9) contra el código de C1+C2, misma base y misma KB del harness, 5 escenarios: **0 citas** contra 2 de la línea base. El replay encontró lo que los tests unitarios no veían (probaban campos aislados, no una conversación):
- **R1** `#19` (mantención): preguntó la falla dos veces y derivó `campo_sin_respuesta`. La detección de preventivo vivía solo en `_ask_next` (salteada por `_reask_pending`) y miraba solo el turno actual. Enmendado S4: se evalúa sobre la ventana y se calcula una vez en `capture()`.
- **R2** `#20` y `#22`: "Ñuñoa" (o el email) respondido mientras se preguntaba otro campo se **descartaba**, el bot repetía la pregunta y terminaba derivando. Mi S2c sobrerreaccionó al bug de corrupción. Enmendado: se acepta lo extraído si pasa el validador del campo; ningún campo acepta el mensaje entero.
- `#18` (A) validó el arreglo principal: con un cliente que no sabe su comuna ya no hay `comuna` inventada ni `handoff:cobertura` falso.
- Fuera de alcance, hallazgo para el backlog: en `#19` la respuesta libre afirmó "Las Condes está dentro de nuestra cobertura" cuando el cliente nunca dijo la comuna, y el flujo alternó respuestas libres del LLM con preguntas de captura, desordenando la secuencia.

**L11** — Replay v3 (`FALLAS: ninguna`) tras corregir tres bugs de **mi driver**, no del bot: los teléfonos se reusaban entre corridas (el escenario A medía una conversación vieja ya derivada), `"qué"` con acento no matcheaba la tabla de respuestas y a la lista de horarios se le contestaba `"no se"` en vez de un número. Medición final: 3/3 escenarios que entran a captura terminan en cita (A #28, B2 #30, D #32), C #31 rechaza sin guardar PII, y B #29 queda bloqueado por P8 (la respuesta libre intercepta la captura). En C3 también se amplió `_NO_WORDS` con rechazos explícitos (`no autorizo`, `no quiero`, `no acepto`, `prefiero no`, `no gracias`): antes `"no autorizo"` caía en `consent_unclear` y el cliente era repreguntado; el match sigue siendo exacto para no romper `is_skip` (`"no enciende"` no es un skip de la falla).

**L12** — Reversión de S1d (orden del consentimiento), con evidencia. Se intentó preguntar el consentimiento ANTES de email/dirección. El CI y la suite completa mostraron que ese cambio rompe el contrato documentado `chat.conduct.orden` y trece tests de integración y funcionales: secuencias fijas desincronizadas, la pregunta de evidencia que deja de caber en el último batch, la ficha escrita antes de tener los campos y, al enrutar el consentimiento aprobado por `_ask_next`, una segunda evaluación de cobertura que derivaba comunas ya aceptadas. El objetivo real —no guardar ni reservar sin un sí— se cumple con el gate y con `_persist_captured` sincronizando la ficha solo con consentimiento verdadero. El orden vuelve al del owner; el gate se queda.

**L14** — #687 (`limpieza de configuración`) llegó a `main` mientras esta rama estaba en revisión y **retiró `chat.conduct.redaccion`** por ser configuración muerta. S5 le da un lector (`phrasing.phrase`), así que la clave vuelve con el merge de main: se reintroducen su allowlist (`CONDUCT_REDACCIONES`), la marca de opcional al guardar (`CONDUCT_OPTIONAL_KEYS`, para payloads de un panel que no la renderiza) y su lugar en la proyección de `validate_conduct`/`get_conduct`. Los tests de `main` que afirmaban su ausencia se reescribieron al contrato nuevo: la proyección lleva el valor, un modo desconocido se rechaza, y un payload sin la clave se acepta aplicando el default `plantilla`.

**L13** — Correcciones que destapó la suite completa, todas visibles sólo en conversaciones: la regla preventiva leía "revisión" dentro de una **pregunta** de precio y marcaba `failure` como salteada (ahora ignora turnos interrogativos); el fallback de respuesta terse —que es el mecanismo real de captura, porque el clasificador no corre durante ella— volvió a aplicar a cualquier campo, con guardas de prosa y de pregunta en vez de una lista de campos; `_pending` guardado como string se iteraba por caracteres y pedía campos llamados "n"; y saltear el consentimiento ya no reserva: repregunta y deriva.
