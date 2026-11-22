# Conversaciones de la corrida `pregunta-gana-sched`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `simple-cobertura-comuna` [simple]

**persona:** Cliente que vive en Maipú y quiere saber si llegan, sin decir todavía qué trabajo necesita.
**objetivo:** Averiguar si Lumat atiende en su comuna.

**1. cliente** `[scripted]` — hola, ustedes trabajan en maipu?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. No tenemos cobertura habitual en maipu, pero igual podemos ayudarte: un asesor coordina la visita según disponibilidad.

**estado final:** `bot` · **juez:** 2.33 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G6 ✓, G7 ✓, G8 ✓, G9 ✓
**dispersión entre repeticiones:** closure ±1, conversational ±1, escalation ±2, policy ±3, tone ±1

## `simple-horario-sabado` [simple]

**persona:** Cliente que trabaja de lunes a viernes y solo puede recibir al técnico un sábado.
**objetivo:** Saber si puede agendar una visita para el sábado.

**1. cliente** `[scripted]` — hola, buenas
> *bot:* Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar.

**2. cliente** `[scripted]` — necesito una visita, el calefont no calienta. vivo en ñuñoa y solo puedo un sabado
> *bot:* Anoté solo sábado como preferencia; la visita la confirmamos al coordinar, todavía no queda agendada. ¿Cuál es tu nombre?

**3. cliente** `[scripted]` — carlos. pero dime altiro si atienden sabado, eso es lo que necesito saber
> *bot:* Las visitas se agendan según la disponibilidad de los técnicos.

> *bot:* Sobre tu horario: el sábado 21/11. Queda anotada y la confirmamos al coordinar la visita. ¿Cuál es tu correo electrónico?

**estado final:** `bot` · **juez:** 2.33 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G6 ✓, G8 ✓, G9 ✓
**dispersión entre repeticiones:** conversational ±1, escalation ±2, grounding ±1, policy ±1, tone ±1

## `real-cobertura-condominio` [simple]

**persona:** Propietaria que llega referida por el chat de su condominio.
**objetivo:** Consultar si Lumat puede ayudar con su caldera y su comuna.

**1. cliente** `[scripted]` — Hola buenas tardes. Me compartieron tu contacto del chat de mi condominio
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Con gusto. ¿En qué más te puedo ayudar?

**estado final:** `bot` · **juez:** 3.17 · **hard fail:** False
**gates:** G1 ✓, G8 ✓, G9 ✓
**dispersión entre repeticiones:** closure ±1, conversational ±2, tone ±1

## `real-dato-mas-pregunta` [complejo]

**persona:** Clienta que ya entregó datos y agrega una pregunta sobre el horario.
**objetivo:** Obtener respuesta a la pregunta manteniendo los datos previamente entregados.

**1. cliente** `[scripted]` — 18:30 comienzo con los chicos
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso.

**2. cliente** `[scripted]` — Yo creo qje no alcanza, y mañana?
> *bot:* No tengo ese dato. ¿Prefieres que te tome los datos para coordinar una visita, o que te atienda una persona?

**3. cliente** `[scripted]` — es factible que pases tipo 14 horas?
> *bot:* Anoté 14:00 como preferencia; la visita la confirmamos al coordinar, todavía no queda agendada. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**estado final:** `bot` · **juez:** 3.33 · **hard fail:** False
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, conversational ±3, escalation ±1, grounding ±2, policy ±1, tone ±1

## `real-solo-sabados` [complejo]

**persona:** Arrendataria que necesita coordinar según su disponibilidad de fin de semana.
**objetivo:** Saber si hay atención los sábados sin recibir una promesa de agenda.

**1. cliente** `[scripted]` — Hola buen dia!
Su contacto me lo dieron en efificio Rivera donde estoy en [dirección]
Me dijeron los antigüos arrendatarios que le hacian la mantención de la caldera en mayo de cada año
No tengo más información por eso quería consultar
Valor aprox de la mantención , y días en que ud trabaja..yo no paso mucho en dpto por razones laborales , por lo general trato de coordinar para sábado ¿ usted trabaja sábados?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. ¡Buen día! La mantención de caldera tiene un valor de $60.000. Respecto a los sábados, las visitas se agendan dentro de la ventana de atención según la disponibilidad real de técnicos, así que el día y la hora se confirman al coordinar la visita. Para confirmarte la cobertura y ver disponibilidad de sábado, ¿en qué comuna está el departamento?

**2. cliente** `[scripted]` — Buen dia
> *bot:* Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar.

**3. cliente** `[scripted]` — Este sábado 27 ud tiene disponibilidad?
> *bot:* Las visitas se agendan según la disponibilidad de los técnicos.

**4. cliente** `[scripted]` — No me encuentro en stgo llegamos viernes tarde al dpto
> *bot:* Entiendo. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**estado final:** `bot` · **juez:** 2.50 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G8 ✓, G9 ✓
**dispersión entre repeticiones:** conversational ±1, escalation ±1, policy ±1

## `real-disponibilidad-dias` [complejo]

**persona:** Cliente que quiere coordinar una visita y pregunta de forma directa qué días tienen hora disponible esta semana.
**objetivo:** Recibir información sobre los días de atención y disponibilidad sin que le vuelvan a preguntar por la falla del equipo.

**1. cliente** `[scripted]` — Hola, buenas
> *bot:* Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar.

**2. cliente** `[scripted]` — ¿Tienen hora disponible esta semana?
> *bot:* Las visitas se agendan según la disponibilidad de los técnicos.

**estado final:** `bot` · **juez:** 2.17 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G6 ✓, G7 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, conversational ±2, escalation ±3, policy ±1, tone ±1

## `real-reagenda-mantencion` [complejo]

**persona:** Clienta que debe cambiar una mantención por un compromiso laboral y ofrece el martes siguiente.
**objetivo:** Solicitar el cambio de fecha sin recibir una confirmación de agenda inventada.

**1. cliente** `[scripted]` — Para cuando tienen disponibilidad??
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. No tengo ese dato. ¿Prefieres que te tome los datos para coordinar una visita, o que te atienda una persona?

**2. cliente** `[scripted]` — Martes pm por favor 🙏
> *bot:* Anoté Martes pm como preferencia; la visita la confirmamos al coordinar, todavía no queda agendada. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**3. cliente** `[scripted]` — Entre las 14:30 y 17:30 por favor
> *bot:* Sobre tu horario: las 14:30 en adelante. Queda anotada y la confirmamos al coordinar la visita. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**4. cliente** `[scripted]` — Me confirma si hay costo asociado?
> *bot:* Sí. La visita técnica tiene un valor de $30.000, y se puede pagar al momento del servicio. Si el técnico detecta que hace falta un trabajo adicional, eso se presupuesta aparte según el diagnóstico. Para dejar coordinada la visita del martes entre 14:30 y 17:30, cuéntame qué está pasando con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**5. cliente** `[scripted]` — Hola buenos dias,
Favor cambiar la fecha de la manutención para el próximo martes por favor,
Por temas laborales no  estaré en casa hoy pm
> *bot:* Entiendo que necesitas cambiar la fecha y lamento el inconveniente. No encontré un horario que nos sirva en la agenda, así que no te voy a dejar esperando: un asesor de Lumat te contacta para coordinar la visita directamente.

**estado final:** `human` · **juez:** 3.17 · **hard fail:** False
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** conversational ±2, escalation ±1, grounding ±1, policy ±1, tone ±1
