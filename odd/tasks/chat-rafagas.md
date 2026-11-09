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
| T1 | S4 | inline — lock por conversación en el sweep, RED de concurrencia primero | — |
| T2 | S1 | inline — ventana de silencio + drenaje de la conversación + ráfaga colapsada en el turno | — |
| T3 | S3 | inline — contador de turnos por conversación (migración 064) | — |
| T4 | S2 | inline — familia social: clave `messages.social`, detección determinista, respuesta fusionada | — |
| T5 | S2 | inline — campo en el panel de configuración + doc de superficies | — |
| T6 | S5 | inline — cerrar: `quick`, `db` focalizado, `full` de frontera, CHANGELOG | — |

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
