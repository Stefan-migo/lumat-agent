# Conversaciones de la corrida `captura-s4-revisado`

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
> *bot:* Anoto las 14:00 como preferencia para mañana, pero la hora exacta se confirma al coordinar, así que todavía no queda agendada. Te cuento que los domingos y festivos se coordinan con un asesor según disponibilidad. Para ir adelantando: ¿el calefont Bosch no enciende en absoluto o alcanza a encender y se apaga?

**estado final:** `bot` · **juez:** 2.50 · **hard fail:** False
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, conversational ±1, escalation ±1, policy ±1

## `real-solo-sabados` [complejo]

**persona:** Arrendataria que necesita coordinar según su disponibilidad de fin de semana.
**objetivo:** Saber si hay atención los sábados sin recibir una promesa de agenda.

**1. cliente** `[scripted]` — Hola buen dia!
Su contacto me lo dieron en efificio Rivera donde estoy en [dirección]
Me dijeron los antigüos arrendatarios que le hacian la mantención de la caldera en mayo de cada año
No tengo más información por eso quería consultar
Valor aprox de la mantención , y días en que ud trabaja..yo no paso mucho en dpto por razones laborales , por lo general trato de coordinar para sábado ¿ usted trabaja sábados?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. ¡Buen día! La mantención de caldera tiene un valor de $60.000. Sobre los sábados: las visitas se agendan según la disponibilidad real de técnicos, así que el día y la hora se confirman al coordinar; puedes dejarnos la preferencia por sábado. ¿En qué comuna queda el departamento, para confirmar cobertura?

**2. cliente** `[scripted]` — Buen dia
> *bot:* Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar.

**3. cliente** `[scripted]` — Este sábado 27 ud tiene disponibilidad?
> *bot:* Anoté sábado 27 como preferencia; la visita la confirmamos al coordinar, todavía no queda agendada. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**4. cliente** `[scripted]` — No me encuentro en stgo llegamos viernes tarde al dpto
> *bot:* Sobre tu horario: la tarde del viernes 27/11. Queda anotada y la confirmamos al coordinar la visita. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**estado final:** `bot` · **juez:** 2.33 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G8 ✓, G9 ✓
**dispersión entre repeticiones:** escalation ±1, grounding ±2, tone ±1

## `real-repuesto-agotado` [supercomplejo]

**persona:** Cliente que consulta por el estado de un repuesto ya buscado.
**objetivo:** Obtener una respuesta honesta sin una promesa infundada de stock o fecha.

**1. cliente** `[scripted]` — Hola [nombre], ¿cómo estás? Te quería preguntar si finalmente pudiste conseguir la electroválvula. Si es así, ¿cuándo podrías venir a instalarla? Muchas gracias 👍
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**2. cliente** `[scripted]` — Perfecto [nombre] 👍 muchas gracias. Entonces quedamos atentos hasta el lunes. Apenas llegue me avisas por favor y coordinamos para instalarla.
> *bot:* Anoté lunes como preferencia; la visita la confirmamos al coordinar, todavía no queda agendada. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**3. cliente** `[scripted]` — super, gracias
> *bot:* Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**estado final:** `bot` · **juez:** 1.67 · **hard fail:** False
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** grounding ±1, policy ±2, tone ±1

## `real-reclamo-real-si-deriva` [supercomplejo]

**persona:** Corredora que administra departamentos de dos dueños distintos y escribe desde otro país. Formal y directa: cuando la relación se rompe lo dice sin adornos, no pide nada y no usa el vocabulario del reclamo formal.
**objetivo:** Cerrar la relación con Lumat después de que el arrendatario de uno de sus departamentos contratara a otro gasfiter porque nadie le contestó.

**1. cliente** `[scripted]` — [nombre], buen día, me dejaste la embarrada con el depto de [dirección], el arrendatario contrató otro gasfiter y dice que te llamó muchísimas veces y no contestas, eso yo lo sé, 
Así que lleguemos hasta aquí con el tema de trabajo. 
Tengo otra persona que hará la pega de [dirección]
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo la molestia y lamento que la experiencia haya sido así. Le aclaro una cosa para que no quede confusión: la atención es por WhatsApp, no recibo llamadas, y por eso el arrendatario no iba a encontrar respuestas por esa vía. Si ya decidió que otra persona hará la pega en ese depto, lo respeto. Le confirmo también que no tengo una visita agendada a ese domicilio, así que no queda nada pendiente que cancelar de mi lado. Si quiere que un asesor revise lo que pasó con las coordinaciones, se lo puedo gestionar.

**2. cliente** `[scripted]` — Muy irresponsable tu forma de trabajar
> *bot:* No tengo ese dato. ¿Prefieres que te tome los datos para coordinar una visita, o que te atienda una persona?

**estado final:** `bot` · **juez:** 0.00 · **hard fail:** True
**gates:** G7 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, conversational ±1, escalation ±1, grounding ±1, tone ±1

## `real-varias-reparaciones` [complejo]

**persona:** Cliente que pide reparar dos problemas distintos: tapas de excusados sueltas que pierden agua y un lavaplatos que se está despegando.
**objetivo:** Dejar ambas necesidades claras para obtener el siguiente paso.

**1. cliente** `[scripted]` — Manutención de excusados: tapas sueltas y pierden agua.
Reparación de lavaplatos. Hay que volver a pegar la superficie y el lavaplatos que está cayéndose
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo. ¿En qué comuna te encuentras?

**2. cliente** `[scripted]` — Eso!
> *bot:* Todavía no tenemos visitas técnicas en Eso! para tu excusados, lavaplatos, un asesor de Lumat se contactará contigo para ayudarte a la brevedad.

**estado final:** `human` · **juez:** 1.17 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, tone ±2

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
> *bot:* Sí, la visita técnica tiene un costo de $30.000. Si lo que necesitas es la mantención de caldera, ese servicio está en $60.000. Eso sí, la visita aún no queda agendada: me falta confirmar qué equipo revisamos y qué le pasa. ¿Es la mantención de la caldera?

**5. cliente** `[scripted]` — Hola buenos dias,
Favor cambiar la fecha de la manutención para el próximo martes por favor,
Por temas laborales no  estaré en casa hoy pm
> *bot:* Entiendo que necesitas cambiar la fecha y lamento el inconveniente. No encontré un horario que nos sirva en la agenda, así que no te voy a dejar esperando: un asesor de Lumat te contacta para coordinar la visita directamente.

**estado final:** `human` · **juez:** 0.00 · **hard fail:** True
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** conversational ±1, escalation ±1, tone ±1

## `real-claudio-caldera-valvula` [complejo]

**persona:** Cliente que sigue una falla de caldera, aporta un error nuevo y pregunta si debe cortar una llave después de enviar un video.
**objetivo:** Obtener un siguiente paso seguro sin un diagnóstico remoto ni instrucciones improvisadas sobre las válvulas.

**1. cliente** `[scripted]` — Vale gracias, voy a esperar que termine la lavadora (20 min) y corto… te aviso como me fue, te parece?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Con gusto. ¿En qué más te puedo ayudar?

**2. cliente** `[scripted]` — Como dato, corte la calefacción central hace 1 semana desde la caldera y no intervine el termostato… influirá eso?
> *bot:* No debería influir: apagar la caldera no descalibra el termostato, solo deja de haber demanda de calor, y al reactivarla el termostato vuelve a pedir calefacción cuando corresponde. Lo que sí importa es que al encenderla el equipo arranque normal, sin ruidos ni bajas de presión. ¿Qué te llevó a cortarla: algún ruido, olor o falla que notaste antes?

**3. cliente** `[scripted]` — 
> *bot:* Recibí tu archivo, lo guardé para el técnico.

**4. cliente** `[scripted]` — Aumentamos… pasamos de E25 a E26 😂
> *bot:* Con gusto. ¿En qué más te puedo ayudar?

**5. cliente** `[scripted]` — Corto la llave de agua de la caldera?
> *bot:* Sí, puedes cerrar la llave de agua de la caldera sin problema; no daña el equipo dejarlo así. Al reabrirla, hazlo despacio y revisa que no quede goteando en la conexión. Si esos códigos E25 / E26 aparecieron en el display de la caldera, mejor no seguir probando a ciegas: un técnico lo ve en el domicilio. La visita técnica tiene un valor de $30.000 y, según lo que encuentre, el trabajo se presupuesta aparte. ¿Quieres que coordinemos esa visita?

**estado final:** `bot` · **juez:** 0.00 · **hard fail:** True
**gates:** G1 ✓, G4 ✓, G8 ✓
**dispersión entre repeticiones:** conversational ±1, escalation ±1, tone ±1
