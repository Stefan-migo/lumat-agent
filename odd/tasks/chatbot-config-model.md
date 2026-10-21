# Chatbot Max — modelo de configuración en 4 capas

Branch `odd/chatbot-config-model` · Delivery `ask-on-risk` (forecast ≈1.300 líneas autoradas; cortar en slices al pasar ~400) · Runner `uv run pytest tests/`
Origen: rapso session `2026-10-21-chatbot-config-brain` (`.rapsodia-code/sessions/archived/`), decisiones D1–D11 cerradas. Este documento las convierte en tareas; no se re-litigan.

## Specs

### Capa 1 — Datos (F1)

**S1 — Tarifario en settings, con temporadas.**
`tarifa.precios` vive en el KV de settings con las cuatro prestaciones y sus dos temporadas: visita técnica `$30.000`; mantención de calefont `$50.000` de marzo a octubre y `$40.000` de noviembre a febrero; mantención de caldera `$80.000` / `$60.000`; lavado de red `$140.000` / `$120.000`.
Validación al guardar: montos enteros positivos, las dos temporadas presentes en cada prestación, sin huecos ni solapamientos de meses, y meses en rango 1–12. Un valor inválido no se persiste y devuelve error legible.

**S2 — Resolución por fecha e inyección al prompt.**
El servidor resuelve la temporada vigente con la fecha en `America/Santiago` (`hours.timezone`), no con la fecha del cliente ni con la del LLM.
El prompt de `respond` recibe la fecha del día y un bloque `<tarifario>` con **solo** los precios vigentes. Criterio de aceptación: para una fecha de marzo y otra de diciembre, el bloque contiene solo la temporada correspondiente; la palabra `temporada`, `invierno` y `verano` no aparece en el prompt ni en la respuesta.
Si `tarifa.precios` no está configurado, no se inyecta el bloque y el prompt mantiene la regla de no inventar precios.

**S3 — Cobertura en settings.**
`coverage.communes` contiene exactamente las siete comunas: Las Condes, Ñuñoa, Lo Barnechea, La Reina, Peñalolén, Colina y Huechuraba.
Normalización: comparación sin tildes, sin mayúsculas y con alias razonables (`ñuñoa`, `nunoa`). Una comuna fuera de la lista no se rechaza: se coordina con un asesor (ver S15).

**S4 — Duraciones y horarios validados.**
`booking.service_durations` y `hours.schedule` ya existen; se les agrega validación de panel y valores por defecto coherentes. `hours.schedule` vacío significa atención 24/7 y sigue siendo el default deseado; la agenda real sigue limitada por disponibilidad de técnicos.

**S5 — La KB de cliente baja a cuatro documentos.**
`docs/kb/lumat-precios.md` deja de ser documento de cliente. Los precios viven solo en settings.
El descuento de la visita y la emisión de boleta/factura se conservan en `docs/kb/lumat-garantias-pagos.md`. La KB de cliente queda en cuatro documentos: identidad, servicios, cobertura-horarios, garantías-pagos.
Criterio de aceptación: ninguna cifra de precio aparece en un documento con `visibility=customer`.

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

| ID | Task | Specs | Ruta | Estado | Commit |
|---|---|---|---|---|---|
| T1 | `tarifa.precios` + validación de temporadas | S1 | inline | pendiente | — |
| T2 | Resolución por fecha, fecha y `<tarifario>` en el prompt | S2 | inline | pendiente | — |
| T3 | `coverage.communes` + normalización | S3 | inline | pendiente | — |
| T4 | Validación de duraciones y horarios | S4 | inline | pendiente | — |
| T5 | Sacar precios de la KB de cliente | S5 | inline | pendiente | — |
| T6 | `greeting_short` en `MessagesBody` y UI | S6 | inline | pendiente | — |
| T7 | `capture.questions` como fallback | S7 | inline | pendiente | — |
| T8 | Textos de agenda/cancelación/derivación | S8 | inline | pendiente | — |
| T9 | Contrato del catálogo de plantillas (sin rediseño) | S9 | inline | pendiente | — |
| T10 | Objeto `chat.conduct` + validación | S10 | inline | pendiente | — |
| T11 | Orden de captura efectivo desde configuración | S11 | inline | pendiente | — |
| T12 | Persona editable con versión/diff/restaurar | S12 | inline | pendiente | — |
| T13 | Protocolo de emergencia editable | S13 | inline | pendiente | — |
| T14 | Una pregunta por mensaje y no repetir | S14 | inline | pendiente | — |
| T15 | Cobertura fuera de las siete comunas | S15 | inline | pendiente | — |
| T16 | Responder preguntas durante la captura | S16 | inline | pendiente | — |
| T17 | No duplicar respuesta por turno | S17 | inline | pendiente | — |
| T18 | Rediseño del panel (último) | S18 | inline | pendiente | — |
| T19 | Test de contrato de los cinco invariantes | S19 | inline | pendiente | — |

## Restricciones técnicas

- Strict TDD ON (`openspec/config.yaml:28,38`): RED observado antes de cada cambio de comportamiento.
- `agent/*.md` está byte-acoplado a `prompts.FALLBACKS` (`tests/unit/test_prompts.py:162`).
- Test DB por worktree: `cp ../lumat-agent/infra/.env infra/.env` y `eval "$(bash infra/test-db.sh env)"`.
- La suite depende del orden: correr `tests/unit`, `tests/integration` y `tests/functional` en invocaciones separadas.
- Pre-merge: traer `origin/main`, esperar los checks `test` + `panel`, sin `--admin`.
- No hay auto-merge. Cada task cierra con commit convencional en la branch.

## Pendientes (no bloquean)

- Redacción default exacta de cada pregunta de captura (T7).
- Derivaciones activas por defecto (T10).
- Si el saludo se personaliza con el nombre (producto).
- Si `lumat-precios.md` se conserva como documento `internal` (T5).
- De Lumat: IVA de los cuatro precios, exigibilidad del 15%, matriz de garantías, documentos SEC emitibles.

## Log

**L1 (2026-10-21, autorización de esta feature):**
> si abre el pr de lo que ya tenemos merge limpieza y continuamos con chatbot-config-model

**L0 (2026-10-21, origen):** rapso session `2026-10-21-chatbot-config-brain`. Decisiones D1–D11, tradeoffs, riesgos y preguntas abiertas en `.rapsodia-code/sessions/archived/2026-10-21-chatbot-config-brain/`. Engram: topic `cortex-session/2026-10-21-chatbot-config-brain`.

**Hecho antes de esta feature (PR #643, merge `99e407f8`):** contrato V4↔repo, cinco documentos de KB comercial, persona de Max espejada, suite T01–T12 en verde, fix de conducta (diagnóstico primero, `persona` explícito, voseo, keyword de emergencia).
