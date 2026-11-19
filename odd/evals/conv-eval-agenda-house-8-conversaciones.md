# Conversaciones de la corrida `agenda-house-8`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `real-dato-mas-pregunta` [complejo]

**persona:** Clienta que ya entregó datos y agrega una pregunta sobre el horario.
**objetivo:** Obtener respuesta a la pregunta manteniendo los datos previamente entregados.

**1. cliente** `[scripted]` — 18:30 comienzo con los chicos
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso.

**2. cliente** `[scripted]` — Yo creo qje no alcanza, y mañana?
> *bot:* Anoté que mañana; lo tengo en cuenta para la visita. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**3. cliente** `[scripted]` — es factible que pases tipo 14 horas?
> *bot:* Sobre tu horario: las 14:00 en adelante. Queda anotada y la confirmamos al coordinar la visita. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**estado final:** `bot` · **juez:** 2.67 · **hard fail:** False
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, conversational ±1, grounding ±2, policy ±1, tone ±1

## `real-reagenda-familiar` [complejo]

**persona:** Clienta con hijos que necesita mover una visita y plantea una hora alternativa.
**objetivo:** Resolver la solicitud de cambio sin perder la restricción de horario.

**1. cliente** `[scripted]` — Mi marido acaba de llegar y tenemos que salir a una deligencia
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso.

**2. cliente** `[scripted]` — Es factible que vengas un dia pero a las.9 am
> *bot:* Anoté que 9:00 am; lo tengo en cuenta para la visita. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**3. cliente** `[scripted]` — En las tardes me complica por los ñiños
> *bot:* Sobre tu horario: 9:00 am. Queda anotada y la confirmamos al coordinar la visita. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**4. cliente** `[scripted]` — No tengo con quien dejarlos
> *bot:* ¿Qué equipo es? Si sabes la marca y el modelo, mejor.

**estado final:** `bot` · **juez:** 2.00 · **hard fail:** False
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±2, conversational ±1, escalation ±2, policy ±3, tone ±2

## `real-diego-precio-y-duracion` [complejo]

**persona:** Cliente que consulta el costo de una mantención y cuánto demora, porque debe salir y volver a una hora determinada.
**objetivo:** Resolver la consulta de precio y considerar la restricción horaria sin prometer una duración o visita no confirmada.

**1. cliente** `[scripted]` — Cuánto es el costo de la mantención?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. La mantención de calefont tiene un valor de $40.000, y la de caldera $60.000. ¿Cuál de los dos equipos tienes?

**2. cliente** `[scripted]` — En todo caso estaba de más, si el precio es 130
> *bot:* No tengo ese dato. ¿Prefieres que te tome los datos para coordinar una visita, o que te atienda una persona?

**3. cliente** `[scripted]` — Maximiliano, te pregunto. Cuánto se demora en el trabajo?
> *bot:* No tengo publicado un tiempo exacto de duración: depende del equipo y de lo que encuentre el técnico en el domicilio, y eso se confirma al coordinar la visita. Si me dices si es calefont o caldera, te orientо mejor y vemos la coordinación.

**4. cliente** `[scripted]` — Tengo que salir a las 2, volviendo a las 4pm
> *bot:* Anoté que Tengo que salir a las 2, volviendo a las 4pm; lo tengo en cuenta para la visita. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**5. cliente** `[scripted]` — Para que lo puedan considerar
> *bot:* Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**estado final:** `bot` · **juez:** 2.83 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±2, escalation ±2, tone ±1
