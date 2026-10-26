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
(c) el extractor solo puede llenar campos presentes en `_pending`; lo extraído fuera del batch se descarta.

**S3 — La pregunta va precedida por un reconocimiento determinista.**
Precedente ya en el código: `if batch == ["failure"] and label: ask = f"Entiendo, es un problema con tu {label}. {ask}"` (`capture.py:374-375`). Se generaliza con un texto configurable (`capture.ack`) construido solo con datos ya capturados y no sensibles (nunca `email`/`address`).

**S4 — En un servicio preventivo no se pregunta por la falla.**
Evidencia `#13` msg 43: a "quiero hacer mantencion de caldera" respondió "Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?". Regla determinista: `capture.preventive_keywords` (default `mantencion`, `mantención`, `mantenimiento`, `revision`, `revisión`, `limpieza`, `preventiva`), normalizado con `_normalize`; si el pedido del cliente es preventivo y `failure` no fue capturado, `failure` se saltea y se registra en `captured_data["_skipped"]`.

**S5 — Redacción asistida: la plantilla es el contrato y el validador es la puerta.**
`chat.conduct.redaccion` existe hoy (`CONDUCT_REDACCIONES = ("llm", "plantilla")`) y **ningún código lo lee**; en ambas bases no hay fila guardada. Pasa a ser el interruptor real: default `"plantilla"` (= comportamiento actual), `"llm"` reescribe **solo** textos de captura y smalltalk. Si el validador rechaza, o hay excepción, timeout o falta de proveedor → se responde la plantilla. El modelo nunca decide qué campo pedir ni inventa valores.

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
| T7 | S5,S6 | `app/chat/phrasing.py` (facts, rewrite, validate, fallback) + wiring en `replies.py` solo para captura/smalltalk + `redaccion` default `"plantilla"` | worker | C2 |
| T8 | S7 | Tests de ida y vuelta + validadores + fallback (sin red) | worker | C2 |
| T9 | — | Verificación: `bash scripts/test.sh quick`, replay de `#13`–`#17` en el harness, `npm run build` si toca `web/` | parent | C1+C2 |
| T10 | — | Commits C1 y C2 con mensaje convencional | parent | — |

## Log

**L1** — "ok puedes revisar los casos que estuve testeando? hay una mejora considerable pero seguimos teniendo errores. Necesito que revises las conversaciones testeadas en el main. y dame un overview de los problemas que puede presentar"

**L2** — "#13. este caso fue mio. le pregunte por agenda pero no habia configurado los horarios del tecnico. lo hice minutos despues." → `booking_unavailable` en `#13` es comportamiento correcto; sale del diagnóstico.

**L3** — "Necesito que me explique claramente y sencillamente cuales son los problemas y como solucionarlos desde el codigo." + "siento que cuando entra en capture es un poco rigido. se sintio mucho mas fluido cuando el llm escribia el mensaje." + "existe la posibilidad sin romper lo deterministico, que la respuesta de la captura de datos (preguntas), sean una referencia y que si aplican se utilicen como estan. pero sino aplican se reescriban por el llm?"

**L4** — "ademas todas las cosas que obersvaste estan bien. los 8 puntos que detallaste"

**L5** — "si va lo agregamos para que entre en el primero PR junto con la captura"

**L6** — "1. confirmo [split en dos commits] 2. doy el consentimiento [worktree]"

**L7** — Revisión del parent sobre C1: dos defectos del agente corregidos antes del commit, con RED propio. (a) `capture_ack` estaba duplicado en `REPLY_TEXT_DEFAULTS` y en `SETTINGS_DEFAULTS["capture.ack"]`, con `get_capture_ack` leyendo el segundo: la fila que el panel edita no hacía nada. (b) El ack se anteponía a **cada** pregunta posterior, repitiendo "Gracias Ana." — el tic que la feature viene a eliminar; ahora se recuerda `_acked` y se suprime la repetición idéntica.

**L12** — Reversión de S1d (orden del consentimiento), con evidencia. Se intentó preguntar el consentimiento ANTES de email/dirección. El CI y la suite completa mostraron que ese cambio rompe el contrato documentado `chat.conduct.orden` y trece tests de integración y funcionales: secuencias fijas desincronizadas, la pregunta de evidencia que deja de caber en el último batch y la ficha escrita antes de tener los campos. El objetivo real —no guardar ni reservar sin un sí— se cumple con el gate y con `_persist_captured` sincronizando la ficha solo con consentimiento verdadero. El orden vuelve al del owner; el gate se queda.

**L13** — Dos falsos positivos que destapó la suite, corregidos: (a) la regla preventiva leía "revisión" dentro de una **pregunta** de precio y marcaba `failure` como salteada, con lo que la respuesta siguiente ("No enciende") terminaba guardada como equipo; ahora la detección ignora mensajes interrogativos y sigue evaluando la ventana completa. (b) El fallback de respuesta terse asignaba texto libre a cualquier campo; queda acotado a `comuna`, `email` y `name`, donde el propio validador decide, y los campos de texto libre ya no se adivinan.
