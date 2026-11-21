# Conversaciones de la corrida `captura-sliceAB9`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `real-solo-sabados` [complejo]

**persona:** Arrendataria que necesita coordinar según su disponibilidad de fin de semana.
**objetivo:** Saber si hay atención los sábados sin recibir una promesa de agenda.

**1. cliente** `[scripted]` — Hola buen dia!
Su contacto me lo dieron en efificio Rivera donde estoy en [dirección]
Me dijeron los antigüos arrendatarios que le hacian la mantención de la caldera en mayo de cada año
No tengo más información por eso quería consultar
Valor aprox de la mantención , y días en que ud trabaja..yo no paso mucho en dpto por razones laborales , por lo general trato de coordinar para sábado ¿ usted trabaja sábados?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Buen día. La mantención de caldera tiene un valor de $60.000, e incluye la revisión del equipo por un técnico autorizado. Sobre el día: las visitas se agendan según la disponibilidad real de técnicos y el día exacto se confirma al coordinar. Podemos buscar un sábado, así que dígame en qué comuna está para revisar la cobertura y coordinar la visita.

**2. cliente** `[scripted]` — Buen dia
> *bot:* Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar.

**3. cliente** `[scripted]` — Este sábado 27 ud tiene disponibilidad?
> *bot:* Entiendo. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**4. cliente** `[scripted]` — No me encuentro en stgo llegamos viernes tarde al dpto
> *bot:* Anoté no está en Santiago; llega el viernes en la tarde al departamento como preferencia; la visita la confirmamos al coordinar, todavía no queda agendada. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**estado final:** `bot` · **juez:** 2.50 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G8 ✓, G9 ✓
**dispersión entre repeticiones:** conversational ±1, escalation ±1, tone ±1

## `real-repuesto-agotado` [supercomplejo]

**persona:** Cliente que consulta por el estado de un repuesto ya buscado.
**objetivo:** Obtener una respuesta honesta sin una promesa infundada de stock o fecha.

**1. cliente** `[scripted]` — Hola [nombre], ¿cómo estás? Te quería preguntar si finalmente pudiste conseguir la electroválvula. Si es así, ¿cuándo podrías venir a instalarla? Muchas gracias 👍
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**2. cliente** `[scripted]` — Perfecto [nombre] 👍 muchas gracias. Entonces quedamos atentos hasta el lunes. Apenas llegue me avisas por favor y coordinamos para instalarla.
> *bot:* Anoté lunes como preferencia; la visita la confirmamos al coordinar, todavía no queda agendada. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**3. cliente** `[scripted]` — super, gracias
> *bot:* Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**estado final:** `bot` · **juez:** 1.17 · **hard fail:** False
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** escalation ±1, grounding ±2, tone ±1

## `real-varias-reparaciones` [complejo]

**persona:** Cliente que pide reparar dos problemas distintos: tapas de excusados sueltas que pierden agua y un lavaplatos que se está despegando.
**objetivo:** Dejar ambas necesidades claras para obtener el siguiente paso.

**1. cliente** `[scripted]` — Manutención de excusados: tapas sueltas y pierden agua.
Reparación de lavaplatos. Hay que volver a pegar la superficie y el lavaplatos que está cayéndose
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo. ¿En qué comuna te encuentras?

**2. cliente** `[scripted]` — Eso!
> *bot:* Todavía no tenemos visitas técnicas en Eso! para tu excusados, lavaplatos, un asesor de Lumat se contactará contigo para ayudarte a la brevedad.

**estado final:** `human` · **juez:** 1.33 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, escalation ±1, policy ±1

## `real-reagenda-mantencion` [complejo]

**persona:** Clienta que debe cambiar una mantención por un compromiso laboral y ofrece el martes siguiente.
**objetivo:** Solicitar el cambio de fecha sin recibir una confirmación de agenda inventada.

**1. cliente** `[scripted]` — Para cuando tienen disponibilidad??
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**2. cliente** `[scripted]` — Martes pm por favor 🙏
> *bot:* Anoté martes pm como preferencia; la visita la confirmamos al coordinar, todavía no queda agendada. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**3. cliente** `[scripted]` — Entre las 14:30 y 17:30 por favor
> *bot:* Sobre tu horario: las 14:30 en adelante. Queda anotada y la confirmamos al coordinar la visita. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**4. cliente** `[scripted]` — Me confirma si hay costo asociado?
> *bot:* Sí. La visita técnica tiene un valor de $30.000, y si en el domicilio se determina que hace falta un trabajo adicional, eso se presupuesta aparte según lo que encuentre el técnico. Para orientarte mejor: ¿qué pasa con el equipo, no enciende, no calienta o muestra algún código de error?

**5. cliente** `[scripted]` — Hola buenos dias,
Favor cambiar la fecha de la manutención para el próximo martes por favor,
Por temas laborales no  estaré en casa hoy pm
> *bot:* Entiendo que necesitas cambiar la fecha y lamento el inconveniente. No encontré un horario que nos sirva en la agenda, así que no te voy a dejar esperando: un asesor de Lumat te contacta para coordinar la visita directamente.

**estado final:** `human` · **juez:** 3.17 · **hard fail:** False
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** conversational ±1, policy ±1, tone ±1
