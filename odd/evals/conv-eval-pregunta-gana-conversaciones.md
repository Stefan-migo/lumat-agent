# Conversaciones de la corrida `pregunta-gana`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `simple-cobertura-comuna` [simple]

**persona:** Cliente que vive en Maipú y quiere saber si llegan, sin decir todavía qué trabajo necesita.
**objetivo:** Averiguar si Lumat atiende en su comuna.

**1. cliente** `[scripted]` — hola, ustedes trabajan en maipu?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. No tenemos cobertura habitual en maipu, pero igual podemos ayudarte: un asesor coordina la visita según disponibilidad.

**estado final:** `bot` · **juez:** 2.67 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G6 ✓, G7 ✓, G8 ✓, G9 ✓
**dispersión entre repeticiones:** closure ±1, escalation ±2, policy ±1

## `real-cobertura-condominio` [simple]

**persona:** Propietaria que llega referida por el chat de su condominio.
**objetivo:** Consultar si Lumat puede ayudar con su caldera y su comuna.

**1. cliente** `[scripted]` — Hola buenas tardes. Me compartieron tu contacto del chat de mi condominio
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Con gusto. ¿En qué más te puedo ayudar?

**estado final:** `bot` · **juez:** 3.33 · **hard fail:** False
**gates:** G1 ✓, G8 ✓, G9 ✓
**dispersión entre repeticiones:** conversational ±1

## `real-dato-mas-pregunta` [complejo]

**persona:** Clienta que ya entregó datos y agrega una pregunta sobre el horario.
**objetivo:** Obtener respuesta a la pregunta manteniendo los datos previamente entregados.

**1. cliente** `[scripted]` — 18:30 comienzo con los chicos
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Anoté 18:30 como preferencia; la visita la confirmamos al coordinar, todavía no queda agendada. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**2. cliente** `[scripted]` — Yo creo qje no alcanza, y mañana?
> *bot:* Claro. Mañana es domingo, y esas visitas se coordinan con un asesor según disponibilidad, así que no te la puedo confirmar yo ahora. Para ir adelantando: ¿qué le pasa al equipo, no enciende, no calienta o muestra algún código?

**3. cliente** `[scripted]` — es factible que pases tipo 14 horas?
> *bot:* Anoto las 14:00 como preferencia, pero al ser domingo la coordinación la hace un asesor según disponibilidad, así que no te la puedo confirmar yo. Para no perder el viaje: ¿qué hace el equipo, no enciende, no calienta o muestra algún código?

**estado final:** `bot` · **juez:** 2.83 · **hard fail:** False
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, conversational ±2, escalation ±1, tone ±1

## `real-solo-sabados` [complejo]

**persona:** Arrendataria que necesita coordinar según su disponibilidad de fin de semana.
**objetivo:** Saber si hay atención los sábados sin recibir una promesa de agenda.

**1. cliente** `[scripted]` — Hola buen dia!
Su contacto me lo dieron en efificio Rivera donde estoy en [dirección]
Me dijeron los antigüos arrendatarios que le hacian la mantención de la caldera en mayo de cada año
No tengo más información por eso quería consultar
Valor aprox de la mantención , y días en que ud trabaja..yo no paso mucho en dpto por razones laborales , por lo general trato de coordinar para sábado ¿ usted trabaja sábados?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Buen día. La mantención de caldera tiene un valor de $60.000, y el agendamiento lo coordinamos según la disponibilidad de técnicos; los días y horarios se confirman al agendar, así que el sábado lo revisamos en ese momento. ¿Me confirmas la comuna del departamento para verificar la cobertura?

**2. cliente** `[scripted]` — Buen dia
> *bot:* Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar.

**3. cliente** `[scripted]` — Este sábado 27 ud tiene disponibilidad?
> *bot:* No puedo confirmarte la disponibilidad de esa fecha desde aquí: los días y horas se confirman al agendar, según la disponibilidad real de técnicos. Un detalle: el 27 de noviembre de este año cae viernes; el sábado sería el 28. Si te sirve, dejo la coordinación para ese sábado y un asesor confirma la hora. ¿Me confirmas tu nombre y la comuna del departamento?

**4. cliente** `[scripted]` — No me encuentro en stgo llegamos viernes tarde al dpto
> *bot:* Anoté viernes tarde como preferencia; la visita la confirmamos al coordinar, todavía no queda agendada. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**estado final:** `bot` · **juez:** 2.67 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G8 ✓, G9 ✓
**dispersión entre repeticiones:** conversational ±1, escalation ±2, grounding ±2, policy ±1, tone ±1

## `real-disponibilidad-dias` [complejo]

**persona:** Cliente que quiere coordinar una visita y pregunta de forma directa qué días tienen hora disponible esta semana.
**objetivo:** Recibir información sobre los días de atención y disponibilidad sin que le vuelvan a preguntar por la falla del equipo.

**1. cliente** `[scripted]` — Hola, buenas
> *bot:* Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar.

**2. cliente** `[scripted]` — ¿Tienen hora disponible esta semana?
> *bot:* No tengo ese dato. ¿Prefieres que te tome los datos para coordinar una visita, o que te atienda una persona?

**estado final:** `bot` · **juez:** 0.00 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G6 ✗ (ninguna respuesta contiene: horario, disponibilidad, sábado, sabado, semana), G7 ✓, G8 ✓
**dispersión entre repeticiones:** escalation ±2, grounding ±2

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
> *bot:* Sí, la visita técnica tiene un valor de $30.000. Ese monto cubre la evaluación del técnico en el domicilio y, según lo que encuentre, el trabajo se presupuesta aparte. El detalle de boleta o factura te lo confirma un asesor. ¿Te sirve que avancemos con la coordinación para el martes en la tarde?

**5. cliente** `[scripted]` — Hola buenos dias,
Favor cambiar la fecha de la manutención para el próximo martes por favor,
Por temas laborales no  estaré en casa hoy pm
> *bot:* Entiendo que necesitas cambiar la fecha y lamento el inconveniente. No encontré un horario que nos sirva en la agenda, así que no te voy a dejar esperando: un asesor de Lumat te contacta para coordinar la visita directamente.

**estado final:** `human` · **juez:** 3.50 · **hard fail:** False
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** grounding ±1

## `real-claudio-caldera-valvula` [complejo]

**persona:** Cliente que sigue una falla de caldera, aporta un error nuevo y pregunta si debe cortar una llave después de enviar un video.
**objetivo:** Obtener un siguiente paso seguro sin un diagnóstico remoto ni instrucciones improvisadas sobre las válvulas.

**1. cliente** `[scripted]` — Vale gracias, voy a esperar que termine la lavadora (20 min) y corto… te aviso como me fue, te parece?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Con gusto. ¿En qué más te puedo ayudar?

**2. cliente** `[scripted]` — Como dato, corte la calefacción central hace 1 semana desde la caldera y no intervine el termostato… influirá eso?
> *bot:* No debería influir. Dejar la caldera apagada con el termostato en la misma posición es normal: el termostato queda pidiendo calor, pero mientras el equipo está apagado no pasa nada. Lo que sí importa es cómo se comporte al volver a encenderla. Si los radiadores calientan desparejo o aparecen ruidos en las tuberías, eso apunta a aire o lodo en la red, y ahí conviene evaluar un lavado de red. Cuando la enciendas de nuevo, cuéntame si calienta parejo y seguimos desde ahí.

**3. cliente** `[scripted]` — 
> *bot:* Recibí tu archivo, lo guardé para el técnico.

**4. cliente** `[scripted]` — Aumentamos… pasamos de E25 a E26 😂
> *bot:* Entiendo. ¿En qué comuna te encuentras?

**5. cliente** `[scripted]` — Corto la llave de agua de la caldera?
> *bot:* Sí, puedes cerrar la llave de agua fría que entra a la caldera, es una maniobra simple y no afecta al gas. Solo ten presente que mientras esté cerrada no vas a tener agua caliente sanitaria, así que no la hagas funcionar en ese rato. ¿La vas a cerrar solo por un momento o quedará cerrada un buen rato?

**estado final:** `bot` · **juez:** 0.00 · **hard fail:** True
**gates:** G1 ✓, G4 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, conversational ±1, escalation ±2, grounding ±1
