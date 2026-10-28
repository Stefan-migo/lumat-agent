# Conversaciones de la corrida `agenda-pref-4`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `simple-horario-sabado` [simple]

**persona:** Cliente que trabaja de lunes a viernes y solo puede recibir al técnico un sábado.
**objetivo:** Saber si puede agendar una visita para el sábado.

**1. cliente** `[scripted]` — hola, buenas
> *bot:* Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar.

**2. cliente** `[scripted]` — necesito una visita, el calefont no calienta. vivo en ñuñoa y solo puedo un sabado
> *bot:* ¿Cuál es tu nombre?

**3. cliente** `[scripted]` — carlos. pero dime altiro si atienden sabado, eso es lo que necesito saber
> *bot:* Sí, Carlos: agendamos de lunes a sábado, de 09:00 a 18:00, según disponibilidad de técnicos, y Ñuñoa está dentro de nuestra cobertura habitual. La visita técnica tiene un valor de $30.000. Para orientarte mejor: ¿el calefont no calienta nada, o calienta un rato y se apaga?

> *bot:* Gracias Carlos. ¿Cuál es tu correo electrónico?

**estado final:** `bot` · **juez:** 3.33 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G6 ✓, G8 ✓, G9 ✓
**dispersión entre repeticiones:** closure ±2, conversational ±1, escalation ±1

## `simple-dia-especifico` [simple]

**persona:** Cliente que solo puede recibir al técnico un día concreto de la semana y lo dice de entrada, sin ofrecer alternativas.
**objetivo:** Agendar la mantención del calefont para el día que el cliente pidió.

**1. cliente** `[scripted]` — hola, necesito una mantencion de calefont, vivo en ñuñoa, puedo el jueves en la mañana
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. ¿Cuál es tu nombre?

**2. cliente** `[scripted]` — me llamo paula, paula@mail.com, calle siempre viva 123, ñuñoa
> *bot:* ¿Autorizas que guardemos tus datos para gestionar tu solicitud? Responde sí o no.

**3. cliente** `[scripted]` — si
> *bot:* Tengo estos horarios disponibles para la visita técnica: 1. 29/10/2026 a las 09:00 2. 29/10/2026 a las 09:30 3. 29/10/2026 a las 10:00 Responde con el número del horario que prefieres.

**estado final:** `bot` · **juez:** 2.83 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G6 ✓, G8 ✓
**dispersión entre repeticiones:** policy ±1, tone ±1
