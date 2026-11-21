# Conversaciones de la corrida `sin-guarda-s4`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `real-dato-mas-pregunta` [complejo]

**persona:** Clienta que ya entregó datos y agrega una pregunta sobre el horario.
**objetivo:** Obtener respuesta a la pregunta manteniendo los datos previamente entregados.

**1. cliente** `[scripted]` — 18:30 comienzo con los chicos
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso.

**2. cliente** `[scripted]` — Yo creo qje no alcanza, y mañana?
> *bot:* Anoté mañana como preferencia; la visita la confirmamos al coordinar, todavía no queda agendada. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**3. cliente** `[scripted]` — es factible que pases tipo 14 horas?
> *bot:* Anoté las 14:00 para mañana como preferencia, pero la hora exacta se confirma al coordinar con la disponibilidad de técnicos; por ahora no queda agendada. Para ir cerrando: ¿la visita es por la mantención del calefont que consultaste?

**estado final:** `bot` · **juez:** 3.67 · **hard fail:** False
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, conversational ±3, grounding ±3, tone ±1
