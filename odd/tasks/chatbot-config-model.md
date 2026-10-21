# Chatbot Max — modelo de configuración en 4 capas

Branch `odd/chatbot-config-model` · Delivery `ask-on-risk` (forecast ≈1.300 líneas autoradas; cortar en slices al pasar ~400) · Runner `uv run pytest tests/`
Origen: rapso session `2026-10-21-chatbot-config-brain` (`.rapsodia-code/sessions/archived/`), decisiones D1–D11 cerradas. Este documento las convierte en tareas; no se re-litigan.

## Specs

### Capa 1 — Datos (F1)

**S1 — Tarifario en settings, con temporadas.**
`tarifa.precios` vive en el KV de settings con las cuatro prestaciones y sus dos temporadas: visita técnica `$30.000`; mantención de calefont `$50.000` de marzo a octubre y `$40.000` de noviembre a febrero; mantención de caldera `$80.000` / `$60.000`; lavado de red `$140.000` / `$120.000`.
Validación al guardar: montos enteros positivos, las dos temporadas presentes en cada prestación, sin huecos ni solapamientos de meses, y meses en rango 1–12. Un valor inválido no se persiste y devuelve error legible.
La sección **Tarifas** del panel expone el editor en F1 (no espera al rediseño de F6): cuatro prestaciones con sus rangos de meses visibles y un input por rango. En F1 se editan los valores, no los rangos de meses. Criterio de aceptación: cambiar un precio desde el panel y guardar persiste la fila; un valor inválido se rechaza con el mensaje del backend.

**S2 — Resolución por fecha e inyección al prompt.**
El servidor resuelve la temporada vigente con la fecha en `America/Santiago` (`hours.timezone`), no con la fecha del cliente ni con la del LLM.
El prompt de `respond` recibe la fecha del día y un bloque `<tarifario>` con **solo** los precios vigentes. Criterio de aceptación: para una fecha de marzo y otra de diciembre, el bloque contiene solo la temporada correspondiente; la palabra `temporada`, `invierno` y `verano` no aparece en el prompt ni en la respuesta.
Si `tarifa.precios` no está configurado, no se inyecta el bloque y el prompt mantiene la regla de no inventar precios.

**S3 — Cobertura en settings.**
`coverage.communes` contiene exactamente las siete comunas: Las Condes, Ñuñoa, Lo Barnechea, La Reina, Peñalolén, Colina y Huechuraba.
Normalización: comparación sin tildes, sin mayúsculas y con alias razonables (`ñuñoa`, `nunoa`). Una comuna fuera de la lista no se rechaza: se coordina con un asesor (ver S15).
La sección **Cobertura** del panel edita la lista (una comuna por línea) y guarda vía `POST /settings/coverage`. Los duplicados que colisionan al normalizar se rechazan.

**S4 — Duraciones y horarios validados.**
`booking.service_durations` y `hours.schedule` ya existen; se les agrega validación de panel y valores por defecto coherentes. `hours.schedule` vacío significa atención 24/7 y sigue siendo el default deseado; la agenda real sigue limitada por disponibilidad de técnicos.
Duraciones: minutos enteros entre 1 y 1440 (un día), claves no vacías y sin dos claves que colisionen al normalizar (una taparía a la otra en `get_service_duration`). `POST /settings/durations` valida y audita; `GET /settings` las expone.
Horarios: el panel y la ruta del asistente comparten un único validador (`validate_hours_schedule`), sin reglas duplicadas.
El editor de duraciones desde el panel queda para F6: el espacio de claves es abierto (el nombre del servicio viene de la conversación), y un formulario de cuatro campos fijos borraría en silencio cualquier clave propia.

**S5 — La KB de cliente baja a cuatro documentos.**
`docs/kb/lumat-precios.md` deja de ser documento de cliente. Los precios viven solo en settings.
El descuento de la visita y la emisión de boleta/factura se conservan en `docs/kb/lumat-garantias-pagos.md`. La KB de cliente queda en cuatro documentos: identidad, servicios, cobertura-horarios, garantías-pagos.
Criterio de aceptación: ninguna cifra de precio aparece en un documento con `visibility=customer`.
`lumat-precios.md` se **elimina**, no se conserva como documento `internal`: dejar una tabla paralela en la KB crea una segunda fuente de precios que se desactualiza en silencio. El descuento de la visita y la frase de detalle tributario se movieron a `lumat-garantias-pagos.md`; "otros trabajos se presupuestan" ya estaba en `lumat-servicios.md`.
La suite T01–T12 dejó de sembrar un documento de cliente con precios: el bloque `<tarifario>` ya viene de settings.

### Capa 2 — Copy (F2)

**S6 — Los seis mensajes y `greeting_short` editables.**
`MessagesBody` (`app/panel/api/routes/settings.py:74`) acepta `greeting_short` además de `greeting`, `cannot_answer`, `clarification`, `farewell` y `out_of_hours`.
La UI del panel expone el campo y persiste con el mismo endpoint. Criterio de aceptación: guardar `greeting_short` desde el panel cambia el saludo de `receive.py:67` sin deploy.
Los defaults de `MESSAGE_DEFAULTS` (`app/services/settings.py`) son el fallback cuando no hay fila guardada.

**S7 — Preguntas de captura en settings.**
`capture.questions` guarda el texto de cada campo en el orden de S11. El código decide qué campo falta; el texto configurado es el fallback cuando el LLM no redacta (modelo caído, costo bloqueado, modo texto fijo).
Validación: toda clave del orden tiene texto no vacío y sin slots desconocidos.

**S8 — Textos de agenda, cancelación y derivación.**
Los textos deterministas de agendar, cancelar, reagendar y derivar son settings con defaults, en la misma superficie que los seis mensajes.
Criterio de aceptación: cambiar un texto en settings cambia el mensaje al cliente sin tocar código.

**S9 — Respuestas prediseñadas: extender, no re-litigar.**
Se reutiliza el catálogo existente (`messages.templates`, `odd/tasks/chatbot-message-catalog.md`): solo se disparan en intenciones informativas, reemplazan la respuesta del modelo y sus slots se validan. Un slot vacío no se renderiza como texto incompleto.
Este slice **no** rediseña el catálogo ni la selección por `classify`.

### Capa 3 — Conducta (F3)

**S10 — Objeto de conducta con opciones cerradas.**
Una sola clave de settings (`chat.conduct`) con:
- `orden`: lista de campos, default `failure → equipment → comuna → availability → name → email → address`;
- `redaccion`: `llm` | `plantilla`, default `llm`;
- `max_preguntas_por_mensaje`: `1` | `2`, default `1`;
- `derivaciones`: reglas activas de la lista cerrada (cobertura, pedido explícito, garantía, servicio sin tarifa, presupuesto especial).
Validación al guardar: todo campo del orden existe en el modelo de captura, sin repetidos y con `name/email/address` después de `availability`; valores fuera del enum se rechazan; al menos una derivación queda alcanzable. Config inválida no se persiste.

**S11 — Orden de captura.**
El orden efectivo es `failure → equipment → comuna → availability → name → email → address`.
`availability` se pregunta solo después de que el cliente aceptó la visita. Los campos de diagnóstico se preguntan de a uno; el bloque de 2–3 queda para los datos de reserva.

### Capa 4 — Persona y seguridad (F5)

**S12 — Persona editable con versión, diff y restaurar.**
La persona de Max es editable desde el panel sobre `agent/personas/orchestrator.md`, con historial de versiones, diff entre versiones y "restaurar default".
El prompt sigue siendo un contrato espejado con `prompts.FALLBACKS`: `tests/unit/test_prompts.py:162` debe seguir pasando. Guardar una persona que rompe el contrato no se persiste.

**S13 — Protocolo de emergencia editable.**
`emergency.safety_instructions`, `emergency.contacts` y `emergency.notify_message` son editables con la misma superficie de versión/restaurar.
El gate determinista de emergencia (`app/chat/nodes/emergency.py`) sigue ejecutándose **antes** del LLM y no depende de estas filas para disparar.

### Conducta (F4)

**S14 — Una pregunta por mensaje, nunca repetir.**
Con `max_preguntas_por_mensaje=1` el bot pregunta un solo campo por mensaje.
Dos mensajes en un turno se permiten solo si el contenido difiere: el mensaje configurado (informativo) y la pregunta de captura del campo pendiente.
Nunca se repite la misma pregunta en el turno; si el cliente no respondió el campo, se reformula una vez y luego se ofrece derivación.

**S15 — Cobertura fuera de las siete comunas.**
Una comuna fuera de `coverage.communes` no se rechaza: se responde que se coordina con un asesor y se crea el caso de derivación correspondiente. Criterio de aceptación: la conversación no queda en punto muerto y no se promete una visita.

**S16 — Responder preguntas durante la captura.**
Si el cliente pregunta algo mientras hay un campo pendiente, el bot responde la pregunta y **no** la guarda como respuesta del campo. El campo pendiente se vuelve a pedir en el turno siguiente, sin perder lo ya capturado.

**S17 — No duplicar respuesta por turno.**
Una sola respuesta informativa por turno: el texto del modelo y una respuesta prediseñada no se envían ambos. Si una plantilla reemplaza al modelo, no se agrega además la respuesta del LLM.

### Panel (F6)

**S18 — Rediseño del panel sobre el modelo existente.**
La UI expone las cuatro capas con validación en línea y errores legibles. Los cinco invariantes no aparecen como configurables.
Criterio de aceptación: cada capa se puede editar y guardar desde el panel; un valor inválido se rechaza con el mensaje del backend.

### Invariantes (no configurables)

**S19 — Cinco invariantes fuera de la configuración.**
Ninguna capa expone ni permite desactivar:
1. Gate de emergencia antes del LLM.
2. Límites de costo (`cost.conversation_limit`, `cost.daily_limit`).
3. Consentimiento antes de reservar.
4. No inventar y `<user_input>` tratado como dato (anti-inyección).
5. Takeover humano: con control humano activo, el bot calla.
Criterio de aceptación: un test de contrato falla si alguna de estas claves aparece como escribible desde el panel, y las pruebas existentes de emergencia, costo, consentimiento y takeover siguen verdes.

## Tasks

| ID | Task | Specs | Ruta | Estado |
|---|---|---|---|---|
| T1 | `tarifa.precios`, validación y editor del panel | S1 | inline | ✅ |
| T2 | Resolución por fecha, fecha y `<tarifario>` en el prompt | S2 | inline | ✅ |
| T3 | `coverage.communes`, normalización y editor del panel | S3 | inline | ✅ |
| T4 | Validación de duraciones y horarios | S4 | inline | ✅ |
| T5 | Sacar precios de la KB de cliente | S5 | inline | ✅ |
| T6 | `greeting_short` en `MessagesBody` y UI | S6 | inline | ✅ |
| T7 | `capture.questions` como fallback | S7 | inline | ✅ |
| T8 | Textos de agenda/cancelación/derivación | S8 | inline | ✅ |
| T9 | Contrato del catálogo de plantillas (sin rediseño) | S9 | inline | ✅ |
| T10 | Objeto `chat.conduct` + validación | S10 | inline | ✅ |
| T11 | Orden de captura efectivo desde configuración | S11 | inline | ✅ |
| T12 | Persona editable con versión/diff/restaurar | S12 | inline | pendiente |
| T13 | Protocolo de emergencia editable | S13 | inline | pendiente |
| T14 | Una pregunta por mensaje y no repetir | S14 | inline | pendiente |
| T15 | Cobertura fuera de las siete comunas | S15 | inline | pendiente |
| T16 | Responder preguntas durante la captura | S16 | inline | pendiente |
| T17 | No duplicar respuesta por turno | S17 | inline | pendiente |
| T18 | Rediseño del panel (último) | S18 | inline | pendiente |
| T19 | Test de contrato de los cinco invariantes | S19 | inline | pendiente |

## Restricciones técnicas

- Strict TDD ON (`openspec/config.yaml:28,38`): RED observado antes de cada cambio de comportamiento.
- `agent/*.md` está byte-acoplado a `prompts.FALLBACKS` (`tests/unit/test_prompts.py:162`).
- Test DB por worktree: `cp ../lumat-agent/infra/.env infra/.env` y `eval "$(bash infra/test-db.sh env)"`.
- La suite depende del orden: correr `tests/unit`, `tests/integration` y `tests/functional` en invocaciones separadas.
- Pre-merge: traer `origin/main`, esperar los checks `test` + `panel`, sin `--admin`.
- No hay auto-merge. Cada task cierra con commit convencional en la branch.

## Pendientes (no bloquean)

- Redacción default exacta de cada pregunta de captura (T7).
- Señal de "aceptó la visita" para gatear `availability` (S11): no existe hoy; falta la decisión de producto.
- Si el saludo se personaliza con el nombre (producto).
- De Lumat: IVA de los cuatro precios, exigibilidad del 15%, matriz de garantías, documentos SEC emitibles.

## Log

**L1 (2026-10-21, autorización de esta feature):**
> si abre el pr de lo que ya tenemos merge limpieza y continuamos con chatbot-config-model

**L2 (2026-10-21, alcance del editor):**
> en F1

El editor de tarifas entra en F1; el rediseño visual de F6 lo reutiliza.

**L3 (2026-10-21, alcance de T8):**
> cobertura completa

Todo texto determinista que el cliente puede leer en agenda, cancelación, reagendamiento, derivación y cierre queda editable, no solo las ocho anclas del handoff.

**T1 (2026-10-21) — cerrado.** Commits `5d40c6de` (settings, validación, `POST /settings/tarifa`, tests) y `9f6198ff` (sección Tarifas del panel). Verde: `tests/unit`, `tests/integration`, `tests/functional`, `npm test` (110 archivos / 1247 tests) y `npm run build` (`tsc -b`). La forma elegida es una lista de rangos de meses por prestación que debe particionar el año; `visita_tecnica` usa un rango 1–12 y las tres estacionales dos rangos.

**T2 (2026-10-21) — cerrado.** `tarifa_vigente(tarifa, fecha)` resuelve el mes contra los rangos (incluye el rango que cruza diciembre) y omite un servicio sin precio en vez de inventarlo. `respond` inyecta `<fecha>` y `<tarifario>` con solo los precios vigentes, resueltos en `hours.timezone`. La persona dejó de instruir "entrega ambos valores con su rango de meses": ahora dice que los precios vigentes vienen en `<tarifario>` y prohíbe nombrar temporadas. Verde: `tests/unit` (con la DB de test migrada), `tests/integration` y `tests/functional` en ese orden.

**T3 (2026-10-21) — cerrado.** `coverage.communes` con las siete comunas; `normalize_comuna` pliega mayúsculas, tildes y espacios internos; `comuna_cubierta` devuelve `False` para vacío o `None`; la validación rechaza strings vacíos y duplicados que colisionan al normalizar. `POST /settings/coverage` + `GET /settings` y la sección Cobertura del panel. La conducta fuera de cobertura sigue siendo T15. Verde: las tres suites en orden, panel (110 archivos / 1248 tests) y `npm run build`.

**T4 (2026-10-21) — cerrado.** `validate_service_durations` (entero 1–1440, claves no vacías, sin colisiones al normalizar), `get_service_durations` con fallback a mapa vacío, `POST /settings/durations` y su lugar en `GET /settings`. La validación de horarios quedó en un solo lugar: el panel ya no duplica las reglas de días y horas, usa `validate_hours_schedule`. Editor de duraciones diferido a F6 con razón registrada. Verde: las tres suites en orden, panel (110 archivos / 1248 tests) y `npm run build`.

**T5 (2026-10-21) — cerrado.** `docs/kb/lumat-precios.md` eliminado; la KB de cliente queda en cuatro documentos. Descuento de la visita y detalle tributario movidos a `lumat-garantias-pagos.md`. El contrato de la KB ahora exige lo inverso: ningún documento de cliente puede citar una cifra ni un `$`. La suite T01–T12 ya no siembra precios en la KB. Verde: unit (también contra una `DATABASE_URL` inalcanzable), integration y functional.

**T6 (2026-10-21) — cerrado.** RED observado primero: `test_settings_update_messages_audited` con seis claves fallaba con `AttributeError` sobre la fila `messages.greeting_short` ausente (Pydantic ignora el campo extra, así que el endpoint respondía 200 y solo se perdía el dato), y el panel no tenía tab "Saludo corto". `MessagesBody` ahora exige las seis claves; `types.ts`, el mock, `SETTINGS_KEYS`, los dos fixtures de test, `EMPTY_MESSAGES` y `MESSAGE_TEMPLATES` suman `greeting_short`. La lectura ya existía (`MESSAGE_DEFAULTS` → `GET /settings` → `receive.py:67`), así que el trabajo fue la escritura. Commits `7173839a` (endpoint) y `c67a22b4` (panel). El commit del panel toca siete archivos y supera la guía de cinco: el contrato obliga a mover `types.ts`, el mock, los dos fixtures y la UI en el mismo cambio, o `tsc -b` queda rojo entre commits. Verde: `tests/unit`, `tests/integration`, `tests/functional` en ese orden, `npm test` (110 archivos / 1249 tests) y `npm run build`.

**T7 (2026-10-21) — cerrado.** RED primero: el test unitario no importaba (`CAPTURE_QUESTIONS_KEY` inexistente) y el de integración moría en el mismo símbolo. `capture.questions` guarda `{campo: texto}`; `get_capture_questions` devuelve `{}` sin fila y `capture.py` mezcla sobre `_FIELD_QUESTIONS`, así que los defaults siguen en el nodo y el orden en `CAPTURE_FIELD_ORDER` (T10 lo mueve a `chat.conduct.orden`). `validate_capture_questions(value, fields)` exige texto en cada campo del orden, rechaza campos desconocidos y slots fuera de `ALLOWED_MESSAGE_TEMPLATE_SLOTS`; los slots los llena la redacción por LLM en F3, no esta slice. `POST /settings/capture-questions` va **antes** del catch-all: el path es de un solo segmento (`/settings/{section}`) y sin ese orden el catch-all se lo come con un 400 engañoso. Sin UI todavía: F6. Commits `f8b830d8` (validación), `615d58c7` (lectura en el nodo), `f6fc55a4` (ruta). Verde: `tests/unit` (DB-free), `tests/integration` y `tests/functional`.

**T8 (2026-10-21) — cerrado.** RED primero: 19 claves inexistentes (`REPLY_TEXTS_KEY`), el endpoint en 404 y el test de booking fallando por la firma nueva de `_offer_text`. `reply.texts` guarda `{clave: texto}`; los defaults viven en `REPLY_TEXT_DEFAULTS` y son byte por byte el texto anterior, y `REPLY_TEXT_SLOTS` fija qué slots acepta cada clave (el owner puede quitar un slot, nunca inventar uno que la llamada no rellena). `render_reply` rellena solo lo declarado, así que un texto sin `{{fecha}}` no recibe un valor que no usa. Los cuatro nodos leen una vez por turno con `get_reply_texts` y renderizan: booking (3 textos), manage (13), handoff (1) y capture (`capture_evidence`, `capture_consent`). Commits `4194bd8f` (catálogo y validador), `b8a63b54`, `e9a3a18e`, `74444123`, `40a41a43` y `5aa1624a` (ruta). Verde: `tests/unit`, `tests/integration`, `tests/functional` y `tests/injection`.
Hallazgos de la auditoría, fuera de estas cinco áreas y por eso sin configurar: `_SOCIAL_REPLY` (respuesta social a mitad de captura) y el prefijo "Entiendo, es un problema con tu {equipo}." de `_ask_next`; ambos son copy de captura, candidatos a S7 o a una slice de cierre. `COMPLETION_REPLY` no lo emite ningún flujo: solo lo usa `scripts/kb_fidelity.py` como fixture, quedó marcado con `ponytail:` en vez de borrarlo. `HANDOFF_REPLY`, `EVIDENCE_QUESTION` y `CONSENT_QUESTION` quedan como alias de los defaults para no tocar ocho archivos de test y script.

**T9 (2026-10-21) — cerrado.** RED primero: el test nuevo de integración recibía "Hola , atendemos de ." (el `""` del slot vacío) y el unitario viejo `test_respond_template_slot_unknown_is_empty_and_visita_uses_booking_label` fijaba justamente ese contrato, así que se reescribió a propósito. `_render_template_reply` ahora devuelve `None` cuando algún slot declarado resuelve vacío (clave ausente, valor `"unknown"` o `{{visita}}` sin reserva) y el turno sigue por el camino normal: KB si tiene contenido, `cannot_answer` + derivación si no. La selección por `classify` y el catálogo no se tocaron. Commit `adbfa21e`. Verde: `tests/unit`, `tests/integration`, `tests/functional` y `tests/injection`.
Trade-off registrado: una plantilla que dependa de un dato no se dispara hasta que ese dato exista en la ficha; es el precio de no mandar texto incompleto. Ojo: `odd/tasks/chatbot-message-catalog.md` todavía documenta que un slot desconocido se renderiza como `""`; S9 supersede esa línea y el doc del catálogo queda desactualizado (decisión del owner si se corrige).

**T10 (2026-10-21) — cerrado.** RED primero: el unitario moría en `ImportError` de `CHAT_CONDUCT_DEFAULTS` y la ruta respondía 400 porque el catch-all `/settings/{section}` se comía `/settings/conduct` antes de que existiera la ruta literal. `chat.conduct` guarda los cuatro campos; `validate_conduct(value, fields)` recibe los campos de captura como parámetro —igual que `validate_capture_questions`— así que `settings` no importa `capture`; `get_conduct` cae al default por clave. Las tres preguntas abiertas del handoff quedaron resueltas: (1) `derivaciones` es **lista de slugs activos**, precedente `coverage.communes`, porque la validación de "al menos una alcanzable" pide lista no vacía; (2) **sin GET y sin UI**, igual que T7 y T8 — F6 expone el contrato completo de una sola vez; (3) el validador recibe el orden, sin ciclo `settings → capture`. Decisiones propias de T10, registradas: las **cinco derivaciones quedan activas por default** (desactivar una borra el caso que cubre, y S15 exige que una comuna fuera de cobertura llegue a un asesor sin tocar el panel); `orden` puede ser **subconjunto** del modelo de captura —sacar un campo es apagar esa pregunta— pero no vacío ni con repetidos, y la regla "`name/email/address` después de `availability`" solo aplica si `availability` está en el orden. Commit `74bafd3a`. Verde: `tests/unit` (DB-free, con `DATABASE_URL` inalcanzable), `tests/integration`, `tests/functional` y `tests/injection` en invocaciones separadas.

**T11 (2026-10-21) — cerrado.** RED primero: `_missing_fields()` recibía un argumento y el test le pasaba dos (`TypeError`), y en integración el orden configurado seguía preguntando `failure` primero y `address` aunque estuviera fuera del orden. `_missing_fields(captured, order)` recibe la secuencia; `_ask_next` lee `get_conduct(session)["orden"]` una vez por turno y **funde los dos `session_scope()`** que abría (uno por rama) en uno solo. El empaquetado quedó en código, como manda S11: `MAX_ASKS` y `_DIAGNOSIS_FIELDS` no se configuran. El acoplamiento menos obvio, resuelto: `POST /settings/capture-questions` valida contra el **orden efectivo** (`get_conduct(session)["orden"]`), no contra el de envío; si no, cambiar el orden dejaba el mapa guardado inválido o guardable con claves que ya no se preguntan. `CAPTURE_FIELD_ORDER` queda como modelo de captura y default, y un test unitario fija que `CHAT_CONDUCT_DEFAULTS["orden"] == CAPTURE_FIELD_ORDER` para que las dos listas no se separen. **Gating fuera de alcance, con razón registrada:** "`availability` solo después de que el cliente aceptó la visita" no tiene señal hoy — el consentimiento es un paso posterior a todos los campos y la reserva viene después—, así que T11 entrega el orden configurable y el gating espera decisión de producto. Commit `c2a910b9`. Verde: `tests/unit` (también DB-free), `tests/integration`, `tests/functional` y `tests/injection` en invocaciones separadas.

**L0 (2026-10-21, origen):** rapso session `2026-10-21-chatbot-config-brain`. Decisiones D1–D11, tradeoffs, riesgos y preguntas abiertas en `.rapsodia-code/sessions/archived/2026-10-21-chatbot-config-brain/`. Engram: topic `cortex-session/2026-10-21-chatbot-config-brain`.

**Hecho antes de esta feature (PR #643, merge `99e407f8`):** contrato V4↔repo, cinco documentos de KB comercial, persona de Max espejada, suite T01–T12 en verde, fix de conducta (diagnóstico primero, `persona` explícito, voseo, keyword de emergencia).
