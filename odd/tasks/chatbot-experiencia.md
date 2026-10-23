# ODD — chatbot-experiencia (agenda, saludo, cortesía, derivaciones y panel)

Origen: rapso-session `.rapsodia-code/sessions/open/2026-10-23-chatbot-experiencia/session.md` (decisiones D1–D15).
Branch: `odd/chatbot-experiencia` · Runner: `uv run pytest tests/` · Panel: `cd web && npm run build && npm test`
Base: `main` = `e354f563` (S1–S4 del backlog `chatbot-backlog` ya mergeados).
Un release único al final: estos slices entran junto con S1–S4 (D15).

## Specs

### S1 · Agenda — grilla, anticipación, más horarios y técnico

> Grilla de 30 minutos, con servicios de 60 minutos. Anticipación de 2 horas. Cuando "más horarios" no
> tiene, aclarar que no hay más para ese día en específico y ofrecer otros días. Sólo si no logra
> agendar pasar a humano (como salvataje). La cita nombra al técnico que va a ir.
> Asignación de técnico: round-robin por carga diaria.

Alcance:

- Los candidatos de `scheduling.open_slots` se alinean a una grilla de **30 minutos** y se descartan los
  segundos (hoy la cita quedó guardada a las `:04:32`).
- Anticipación mínima de **2 horas** (configurable), medida contra `now`.
- "Más horarios" entrega los siguientes 3 de la misma oferta congelada; si no hay más para ese día, lo
  dice y ofrece otros días. No deriva por pedir otro horario.
- Derivación de salvataje con el texto S4.5 sólo si no se logra agendar.
- Asignación **round-robin por carga diaria**: entre los técnicos libres para el horario, gana quien
  tenga menos visitas agendadas ese día; empate → alterna por id.
- La confirmación puede nombrar al técnico (`{{tecnico}}`), con fallback cuando `users.name` está vacío.

Riesgo: **item 1** (escribe citas en la agenda; un error agenda una visita real en un horario inválido)
y **item 3** (cambia el contrato de `open_slots`, que tiene otros consumidores).

### S2 · Saludo por nombre

> Si el chatbot ya dispone del nombre del cliente, saludar por nombre. Si no lo dispone, saludar
> consultando el nombre ("¿Con quién tengo el gusto?").

Textos (verbatim, aprobados):

- **Saludo con nombre:** `Hola, {{nombre}}. Soy Max, el asistente virtual de Lumat. ¿En qué te puedo ayudar?`
- **Saludo pidiendo el nombre:** `Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar.`
- **Saludo corto con nombre:** `Hola, {{nombre}}. Soy Max, de Lumat. Ya te ayudo con eso.`
- **Saludo corto sin nombre:** `Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso.`

Alcance: `customers.name` resuelve el slot; sin nombre se usa la variante que pregunta. El grupo de
saludo acepta `{{nombre}}` (hoy lo rechaza). El saludo corto **no** necesita una segunda respuesta:
`run_conversation` lo fusiona con la primera pregunta del turno (CM-1).

Riesgo: **item 3** (el grupo de mensajes fijos gana un slot; cambia el contrato de validación del panel).

### S3 · Cortesía (smalltalk)

> La cortesía no puede consumir un fallo de comprensión ni disparar la aclaración. `unknown` significa
> "no entiendo qué quiere", no "esto no es ninguno de mis temas". El vocabulario lo pone el LLM; el
> grafo decide el flujo.

Alcance: categoría `smalltalk` en `agent/personas/classify.md`; rama explícita en `respond` (o en
`_dispatch`) con texto configurable; no suma `unknown_intent` (la racha se corta sola); `unknown`
redefinido en la persona como incomprensión real. La lista determinista `_SOCIAL_ONLY` **no** se
extiende como sustituto.

Riesgo: **item 3** (la persona del clasificador está acoplada byte a byte a `prompts.FALLBACKS` y a los
tests que la fijan).

### S4 · Derivaciones: información + 5 textos

> En el panel tiene que quedar claro en qué casos deriva el bot, y poder modificar el texto sólo de los
> 5 casos que el cliente lee.

Textos (verbatim, aprobados):

- **S4.1 Cobertura** (necesita `{{comuna}}`): `Todavía no tenemos visitas técnicas en {{comuna}}, un asesor de Lumat se contactará contigo para ayudarte a la brevedad.`
- **S4.2 Pedido de persona:** `Listo, te paso con una persona del equipo. En cuanto esté disponible te escribe por acá.`
- **S4.3 Tres fallos:** `No quiero seguir dándote vueltas con esto. Te dejo con una persona del equipo para que te ayude directamente.`
- **S4.4 Campo sin respuesta:** `Veo que esa pregunta no te acomoda. Un asesor de Lumat te contacta para terminar de coordinar los datos.`
- **S4.5 Salvataje de agenda:** `No encontré un horario que nos sirva en la agenda, así que no te voy a dejar esperando: un asesor de Lumat te contacta para coordinar la visita directamente.`

Alcance: selección del texto por `escalate_reason` en `handoff.py`; las demás razones siguen con el
texto genérico. Las 4 reglas de `chat.conduct.derivaciones` sin lector se sacan del panel.

Riesgo: **item 3** (cambia lo que el cliente recibe en toda derivación; los tests fijan el texto único).

### S5 · Panel: respuestas prediseñadas y horarios de técnicos

> Configurar el chatbot desde el panel es difícil. No hace falta cambiar el código de id a categoría; lo
> importante es hacerlo más entendible en el UI/UX.

Alcance: mostrar y autogenerar el `id` de una plantilla, explicar que el cliente nunca lo ve, vista
previa con datos reales y advertencia de que una plantilla con un slot vacío se salta (S9). Mover la
configuración de horarios de técnicos de Agenda a Configuración. Exponer la anticipación mínima y los
textos nuevos.

Riesgo: **item 3** (mueve superficies del panel que tienen tests y `tsc -b`).

## Non-goals

- No se delega el ruteo al modelo: el grafo decide, el LLM clasifica y redacta (D1, tradeoff rechazado).
- No se cambian los límites de costo (D14).
- No se responde "qué técnico está disponible" (D8): expone agenda interna.
- No se asocia cada plantilla a una categoría del clasificador (D10).
- No se mueve `name` al inicio del orden de captura: el validador lo prohíbe y contradice S11/D8.
- T7 (re-medir handoffs) queda fuera hasta el deploy.

## Tasks

| ID | Spec | Alcance | Ruta | Commit |
|---|---|---|---|---|
| T1 | S1 | Grilla de 30 min + anticipación 2 h en `scheduling` | inline, test-first | pendiente |
| T2 | S1 | Round-robin por carga diaria en la asignación | inline, test-first | pendiente |
| T3 | S1 | "Más horarios" paginado + aviso "no hay más para ese día" + otros días | inline, test-first | pendiente |
| T4 | S1 | Salvataje de agenda y `{{tecnico}}` en la confirmación | inline, test-first | pendiente |
| T5 | S2 | Saludo con `{{nombre}}` y variante que pregunta el nombre | inline, test-first | pendiente |
| T6 | S3 | Categoría `smalltalk` + rama + texto configurable | worker + inline, test-first | pendiente |
| T7 | S4 | Textos por motivo de derivación (5) + panel | inline, test-first | pendiente |
| T8 | S5 | UX de respuestas prediseñadas + horarios de técnicos a Configuración | worker + inline, test-first | pendiente |

## Log

**L1 — textos aprobados por el owner (verbatim, 2026-10-23):**

> 1. Saludo con nombre: Hola, {{nombre}}. Soy Max, el asistente virtual de Lumat. ¿En qué te puedo ayudar?
> 2. Saludo pidiendo el nombre: Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar.
> 3. Saludo corto con nombre: Hola, {{nombre}}. Soy Max, de Lumat. Ya te ayudo con eso.
> 4. Saludo corto sin nombre: Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso.
>
> 1 y 2 estan bien.
> 3 y 4. no estoy seguro. pero requeririan mas de una respuesta por turno? dos al menos?
>
> modificaciones:
> 5. Todavía no tenemos visitas técnicas en {{comuna}}, un asesor de Luamt se contactará contigo para ayudarte a la brevedad.
> 6. correcto asi.
> 7. correcto asi
> 8. correcto asi.
> 9. correcto asi.

Resolución de la duda 3/4: no hacen falta dos respuestas — `run_conversation` fusiona el saludo con la
primera pregunta del turno (CM-1). Texto 5: "Luamt" se corrige a "Lumat" (typo confirmado por contexto).

**L2 — asignación de técnico (verbatim):** `si round robin` → round-robin por carga diaria.

**L3 — release y costo (verbatim):**

> los slices entran en el release asi que lo postergamos.
> no es necesario si llegara a ser necesario lo subimos.por ahora esta bien. era solo para dejar en claro
> que el costo no debe ser factor para el rendimiento del chatbot.

**L4 — decisiones previas de la sesión (verbatim, 2026-10-23):**

> grilla de 30, con servicios de 60 minutos. ... anticipacion de 2 horas, cuando mas horarios no tiene,
> aclarar que no hay mas para ese dia en especifico ofrecer otro dias. solo si no logra agendar pasar a
> humano (como salvataje)
>
> si el chatbot ya dispone del nombre del cliente. saludar por nombre. si no lo dispone, saludar
> consultando el nombre (con quien tengo el gusto?)
>
> quizas no es necesario cambiar el codigo de id a categoria. lo importante es hacerlo mas entendible en
> el ui/ux, actualmente es super dificil configurar el chatbot desde el panel.
>
> que es mover la configuracion de los horarios de los tecnicos a la seccion de configuracion. quiero
> centralizar toda la configuracion en la seccion cofiguracion
