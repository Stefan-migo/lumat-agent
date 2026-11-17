# Conversaciones de la corrida `antes-complejo`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `complejo-agendar-calefont` [complejo]

**persona:** Cliente de Ñuñoa que quiere agendar la mantención de su calefont y da los datos en desorden: primero la comuna, después el nombre, y el email recién al final. Mensajes cortos, varias ideas por mensaje.
**objetivo:** Agendar una mantención de calefont en Ñuñoa y quedar con la visita coordinada.

**1. cliente** `[scripted]` — hola, necesito mantener mi calefont, vivo en ñuñoa
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**2. cliente** `[scripted]` — me llamo carolina, atiendan cuando puedan
> *bot:* Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**3. cliente** `[scripted]` — el calefont es junkers, tiro natural
> *bot:* Veo que esa pregunta no te acomoda. Un asesor de Lumat te contacta para terminar de coordinar los datos.

**4. cliente** `[scripted]` — si, me sirve cualquier dia en la mañana
> *bot:* Veo que esa pregunta no te acomoda. Un asesor de Lumat te contacta para terminar de coordinar los datos.

**5. cliente** `[scripted]` — carolina.p@gmail.com
> *bot:* Veo que esa pregunta no te acomoda. Un asesor de Lumat te contacta para terminar de coordinar los datos.

**estado final:** `human` · **juez:** 0.00 · **hard fail:** True
**gates:** G1 ✓, G4 ✓, G6 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, grounding ±1, policy ±1

## `complejo-dos-temas` [complejo]

**persona:** Cliente que primero pregunta un precio y después, sobre ese mismo servicio, pregunta por la garantía. No repite el nombre del servicio.
**objetivo:** Saber el precio del lavado de red y después cuánta garantía tiene.

**1. cliente** `[scripted]` — hola, cuanto cuesta el lavado de red?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Hola. El lavado de red de calefacción cuesta $120.000. Es una limpieza profunda del circuito para eliminar lodos, óxido y sedimentos, y así recuperar la circulación y eficiencia térmica. ¿Es para una casa o un edificio, y cuántos radiadores tiene aproximadamente la red?

**2. cliente** `[scripted]` — y eso cuanto de garantia tiene?
> *bot:* El lavado de red tiene garantía de 6 meses y cubre la mano de obra del trabajo realizado; no incluye repuestos. ¿Es para una casa o un edificio, y cuántos radiadores tiene la red?

**estado final:** `bot` · **juez:** 0.00 · **hard fail:** False
**gates:** G1 ✗ (state=bot, esperado uno de: human), G10 ✗ (ninguna derivación esperada (esperaba persona); se registró: ninguna), G6 ✓, G8 ✓, G9 ✓

## `complejo-no-quiere-email` [complejo]

**persona:** Cliente desconfiado que quiere coordinar una visita pero se niega a entregar su correo. Insiste en que le basten el nombre y el teléfono.
**objetivo:** Coordinar una visita técnica sin dar el email.

**1. cliente** `[scripted]` — hola necesito una visita tecnica, tengo una fuga de agua en el baño
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo. ¿Qué equipo es? Si sabes la marca y el modelo, mejor.

**2. cliente** `[scripted]` — me llamo jorge, vivo en la reina
> *bot:* ¿Qué equipo es? Si sabes la marca y el modelo, mejor.

**3. cliente** `[scripted]` — no te voy a dar mi correo, con el telefono basta
> *bot:* ¿Qué días y horarios te acomodan para la visita?

**4. cliente** `[scripted]` — si, cualquier dia despues de las 6
> *bot:* ¿Cuál es tu dirección?

**estado final:** `bot` · **juez:** 0.00 · **hard fail:** False
**gates:** G1 ✗ (state=bot, esperado uno de: human), G10 ✗ (ninguna derivación esperada (esperaba booking_unavailable, persona); se registró: ninguna), G4 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, conversational ±2, escalation ±1, grounding ±1, policy ±1, tone ±1

## `complejo-fuera-de-cobertura-insiste` [complejo]

**persona:** Cliente de Temuco que necesita una mantención de caldera y no acepta un no como respuesta. Pregunta dos veces si de verdad no pueden.
**objetivo:** Conseguir que alguien coordine la mantención de su caldera en Temuco.

**1. cliente** `[scripted]` — hola, necesito mantencion de caldera, estoy en temuquito
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Todavía no tenemos visitas técnicas en temuquito para tu caldera, un asesor de Lumat se contactará contigo para ayudarte a la brevedad.

**2. cliente** `[scripted]` — pero ustedes no van a ir hasta aca? es una caldera grande
> *bot:* No descartamos el trabajo: Temuquito no está dentro de la cobertura habitual, así que la visita se coordina caso a caso con un asesor, sin costo de evaluación por adelantado. La mantención de caldera tiene una tarifa de $60.000; si el equipo es de mayor tamaño o de uso comercial, el alcance lo confirma el asesor antes de agendar. ¿Esa caldera calienta solo una casa o abastece un edificio o recinto más grande?

**3. cliente** `[scripted]` — y quien me va a contactar entonces
> *bot:* Te contactaría un asesor de Lumat, del área comercial, por este mismo número o por el teléfono que me indiques. Para dejar el caso registrado y que te ubiquen, ¿me das tu nombre y un número de contacto?

**estado final:** `human` · **juez:** 2.33 · **hard fail:** False
**gates:** G1 ✓, G10 ✓, G6 ✓, G7 ✓, G8 ✓, G9 ✓
**dispersión entre repeticiones:** conversational ±1, escalation ±1, policy ±1, tone ±1

## `real-dato-mas-pregunta` [complejo]

**persona:** Clienta que ya entregó datos y agrega una pregunta sobre el horario.
**objetivo:** Obtener respuesta a la pregunta manteniendo los datos previamente entregados.

**1. cliente** `[scripted]` — 18:30 comienzo con los chicos
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso.

**2. cliente** `[scripted]` — Yo creo qje no alcanza, y mañana?
> *bot:* Entiendo. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**3. cliente** `[scripted]` — es factible que pases tipo 14 horas?
> *bot:* Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**estado final:** `bot` · **juez:** 0.00 · **hard fail:** True
**gates:** G1 ✓, G4 ✗ (se registró lo prohibido: unknown_intent), G8 ✓
**dispersión entre repeticiones:** escalation ±1, policy ±2, tone ±2

## `real-arrendatario-no-decide` [complejo]

**persona:** Arrendataria que explica su rol y consulta si puede enviarse un presupuesto al dueño.
**objetivo:** Pedir un presupuesto sin atribuirse la autorización del propietario.

**1. cliente** `[scripted]` — Yo estoy arrendando la casa a la señora [nombre]
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso.

**2. cliente** `[scripted]` — Entonces le podría enviar un presupuesto
> *bot:* Sí, claro. Cuéntame qué trabajo hay que presupuestar y en qué comuna, así un asesor lo prepara y lo envía a la señora. Si es alguno de los servicios con tarifa publicada, te lo digo de inmediato: visita técnica, mantención de calefont o caldera, y lavado de red.

**3. cliente** `[scripted]` — Por favor 🙏🏻🙏🏻
> *bot:* Con gusto. Para armarlo, cuéntame qué hay que hacer en la casa —una mantención, una instalación, una revisión— y en qué comuna está. Con eso le pido el presupuesto a un asesor para la señora.

**4. cliente** `[scripted]` — Yo arriendo hace 7 años esta casa
> *bot:* Con gusto. ¿En qué más te puedo ayudar?

**5. cliente** `[scripted]` — Y vivo con tres niños
> *bot:* Con gusto. ¿En qué más te puedo ayudar?

**estado final:** `bot` · **juez:** 2.33 · **hard fail:** False
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** conversational ±1, escalation ±3, tone ±1

## `real-multi-equipo-un-mensaje` [complejo]

**persona:** Clienta que reporta problemas en más de un equipo en el mismo mensaje.
**objetivo:** Dejar registrados ambos equipos sin mezclarlos.

**1. cliente** `[scripted]` — Hola [nombre] como estas?
Para saber si podrías realizar mantencion anual con garantía a calefont y caldera de casa en [condominio], lo ubicas? Saludos!
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. ¡Hola! Todo bien, gracias. Sí, hacemos mantención anual de calefont ($40.000) y de caldera ($60.000), ambas con garantía de un año o hasta la próxima mantención, lo que ocurra primero; cubre la mano de obra, no los repuestos. No me queda claro el sector: ¿me confirmas la comuna o el condominio para verificar la cobertura?

**2. cliente** `[scripted]` — Arrendatario me pide un certificado o algo que acredite la mantención, se puede dejar algo así?
> *bot:* No tengo en la información el detalle de un certificado formal, así que no te quiero prometer algo que no está confirmado. Puedo dejar registrada la solicitud para que un asesor te confirme qué documento se puede entregar al arrendatario, indicando fecha, equipo y dirección del servicio. Y para ir avanzando con la mantención, ¿me confirmas la comuna o el condominio?

**3. cliente** `[scripted]` — Cual es el precio aprox?
> *bot:* La mantención de calefont está en $40.000 y la de caldera en $60.000; si haces las dos, suman $100.000. Ambas incluyen garantía de un año o hasta la próxima mantención, y cubren mano de obra, no repuestos. Para confirmarte la cobertura y coordinar, ¿me dices la comuna o el nombre del condominio?

**estado final:** `bot` · **juez:** 3.33 · **hard fail:** False
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** conversational ±1, escalation ±1

## `real-solo-sabados` [complejo]

**persona:** Arrendataria que necesita coordinar según su disponibilidad de fin de semana.
**objetivo:** Saber si hay atención los sábados sin recibir una promesa de agenda.

**1. cliente** `[scripted]` — Hola buen dia!
Su contacto me lo dieron en efificio Rivera donde estoy en [dirección]
Me dijeron los antigüos arrendatarios que le hacian la mantención de la caldera en mayo de cada año
No tengo más información por eso quería consultar
Valor aprox de la mantención , y días en que ud trabaja..yo no paso mucho en dpto por razones laborales , por lo general trato de coordinar para sábado ¿ usted trabaja sábados?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. ¡Buen día! La mantención de caldera tiene un valor de $60.000. Respecto a los sábados, las visitas se agendan según la disponibilidad real de técnicos, así que el día y la hora los confirmamos al coordinar. Para revisar la cobertura y ver la opción de un sábado, ¿me confirma en qué comuna está el departamento?

**2. cliente** `[scripted]` — Buen dia
> *bot:* Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar.

**3. cliente** `[scripted]` — Este sábado 27 ud tiene disponibilidad?
> *bot:* Entiendo. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**4. cliente** `[scripted]` — No me encuentro en stgo llegamos viernes tarde al dpto
> *bot:* Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**estado final:** `bot` · **juez:** 1.83 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G8 ✓, G9 ✓
**dispersión entre repeticiones:** closure ±1, escalation ±3, policy ±3, tone ±1

## `real-reagenda-familiar` [complejo]

**persona:** Clienta con hijos que necesita mover una visita y plantea una hora alternativa.
**objetivo:** Resolver la solicitud de cambio sin perder la restricción de horario.

**1. cliente** `[scripted]` — Mi marido acaba de llegar y tenemos que salir a una deligencia
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso.

**2. cliente** `[scripted]` — Es factible que vengas un dia pero a las.9 am
> *bot:* No tienes visitas próximas para reagendar.

**3. cliente** `[scripted]` — En las tardes me complica por los ñiños
> *bot:* Entiendo. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**4. cliente** `[scripted]` — No tengo con quien dejarlos
> *bot:* ¿Qué equipo es? Si sabes la marca y el modelo, mejor.

**estado final:** `bot` · **juez:** 0.00 · **hard fail:** True
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** escalation ±2, policy ±1

## `real-varias-reparaciones` [complejo]

**persona:** Cliente que pide reparar dos problemas distintos: tapas de excusados sueltas que pierden agua y un lavaplatos que se está despegando.
**objetivo:** Dejar ambas necesidades claras para obtener el siguiente paso.

**1. cliente** `[scripted]` — Manutención de excusados: tapas sueltas y pierden agua.
Reparación de lavaplatos. Hay que volver a pegar la superficie y el lavaplatos que está cayéndose
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo. ¿En qué comuna te encuentras?

**2. cliente** `[scripted]` — Eso!
> *bot:* ¿En qué comuna te encuentras?

**estado final:** `bot` · **juez:** 2.83 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, conversational ±2, escalation ±2, grounding ±1, policy ±1, tone ±1

## `real-reagenda-mantencion` [complejo]

**persona:** Clienta que debe cambiar una mantención por un compromiso laboral y ofrece el martes siguiente.
**objetivo:** Solicitar el cambio de fecha sin recibir una confirmación de agenda inventada.

**1. cliente** `[scripted]` — Para cuando tienen disponibilidad??
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**2. cliente** `[scripted]` — Martes pm por favor 🙏
> *bot:* Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**3. cliente** `[scripted]` — Entre las 14:30 y 17:30 por favor
> *bot:* Veo que esa pregunta no te acomoda. Un asesor de Lumat te contacta para terminar de coordinar los datos.

**4. cliente** `[scripted]` — Me confirma si hay costo asociado?
> *bot:* Sí, la visita técnica tiene un valor de $30.000. Si lo que necesitas es mantención, el calefont son $40.000 y la caldera $60.000. Para confirmarte el horario del martes entre 14:30 y 17:30, cuéntame qué equipo tienes y qué está pasando con él.

> *bot:* Veo que esa pregunta no te acomoda. Un asesor de Lumat te contacta para terminar de coordinar los datos.

**5. cliente** `[scripted]` — Hola buenos dias,
Favor cambiar la fecha de la manutención para el próximo martes por favor,
Por temas laborales no  estaré en casa hoy pm
> *bot:* No tienes visitas próximas para reagendar.

**estado final:** `human` · **juez:** 0.00 · **hard fail:** True
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, escalation ±2, grounding ±1, policy ±2, tone ±1

## `real-revision-bano-ruidoso` [complejo]

**persona:** Clienta que pide revisar un baño que se rellena intermitentemente y hace ruido.
**objetivo:** Obtener el siguiente paso para revisar el problema sin un diagnóstico inventado.

**1. cliente** `[scripted]` — Necesito ver un baño que se rellena a ratos y es una lata porque mete ruido
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo. ¿En qué comuna te encuentras?

**2. cliente** `[scripted]` — Me podrías avisar
> *bot:* Todavía no tenemos visitas técnicas en Me podrías avisar para tu baño, un asesor de Lumat se contactará contigo para ayudarte a la brevedad.

**3. cliente** `[scripted]` — Cuando puede
> *bot:* Todavía no tenemos visitas técnicas en Me podrías avisar para tu baño, un asesor de Lumat se contactará contigo para ayudarte a la brevedad.

**estado final:** `human` · **juez:** 0.83 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G8 ✓
**dispersión entre repeticiones:** escalation ±1, policy ±1, tone ±1

## `real-consulta-otros-equipos` [complejo]

**persona:** Cliente que pregunta si el técnico revisa aire acondicionado y bomba de calor de piscina además de los equipos que ya atiende.
**objetivo:** Saber si Lumat puede realizar la mantención de esos otros equipos.

**1. cliente** `[scripted]` — aire acondicionado ves igual o no?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Sí, en Lumat también trabajamos climatización, así que podemos ayudarte con aire acondicionado. Eso sí, la mantención o instalación de equipos de aire no tiene tarifa publicada, así que un asesor lo presupuesta según el equipo. ¿Qué necesitas: una mantención, una instalación o revisar una falla?

**2. cliente** `[scripted]` — y bomba de calor de piscina?
> *bot:* Podemos revisarlo, aunque la bomba de calor de piscina tampoco tiene tarifa publicada: el valor depende del equipo y del trabajo, así que lo presupuesta un asesor. ¿Se trata de una instalación, de una mantención o de una falla que está dando ahora?

**3. cliente** `[scripted]` — pq tengo que hacer la mantención de esa
> *bot:* Buena pregunta. La mantención periódica evita que se acumule suciedad o sarro en el intercambiador, mantiene el rendimiento y alarga la vida del equipo; además ayuda a detectar a tiempo fugas o fallas que después salen más caras. No es una obligación, pero sí es la forma de que la bomba siga calentando bien y no te dé sorpresas en pleno verano. ¿Hace cuánto que no le hacen una mantención?

**estado final:** `bot` · **juez:** 0.00 · **hard fail:** True
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** escalation ±1, grounding ±2, policy ±3

## `real-claudio-caldera-valvula` [complejo]

**persona:** Cliente que sigue una falla de caldera, aporta un error nuevo y pregunta si debe cortar una llave después de enviar un video.
**objetivo:** Obtener un siguiente paso seguro sin un diagnóstico remoto ni instrucciones improvisadas sobre las válvulas.

**1. cliente** `[scripted]` — Vale gracias, voy a esperar que termine la lavadora (20 min) y corto… te aviso como me fue, te parece?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Con gusto. ¿En qué más te puedo ayudar?

**2. cliente** `[scripted]` — Como dato, corte la calefacción central hace 1 semana desde la caldera y no intervine el termostato… influirá eso?
> *bot:* No debería influir. Con la caldera apagada el termostato queda sin efecto, porque no hay equipo encendido que reciba la orden de calentar; tampoco se desconfigura por estar una semana así. Cuando retomes, enciende la caldera y el termostato vuelve a mandar con normalidad. ¿El servicio que quieres coordinar es mantención de caldera o lavado de red? Así te orientо con el valor y los tiempos.

**3. cliente** `[scripted]` — <video omitido>
> *bot:* Disculpa, no te entendí bien. ¿Me cuentas un poco más qué necesitas? Puedo ayudarte con una consulta, coordinar una visita técnica o revisar un trabajo ya hecho.

**4. cliente** `[scripted]` — Aumentamos… pasamos de E25 a E26 😂
> *bot:* Entiendo. ¿En qué comuna te encuentras?

**5. cliente** `[scripted]` — Corto la llave de agua de la caldera?
> *bot:* No te puedo indicar cómo manipular las llaves del equipo: para eso conviene que lo revise un técnico autorizado SEC y así se evita un daño o una fuga. Si en la pantalla te aparecen códigos como E25 o E26, eso ya amerita revisión en terreno. La visita técnica tiene un valor de $30.000. ¿En qué comuna estás, para orientarte con la coordinación?

**estado final:** `bot` · **juez:** 0.00 · **hard fail:** False
**gates:** G1 ✓, G4 ✗ (se registró lo prohibido: unknown_intent), G8 ✓
**dispersión entre repeticiones:** conversational ±1, tone ±2

## `real-diego-precio-y-duracion` [complejo]

**persona:** Cliente que consulta el costo de una mantención y cuánto demora, porque debe salir y volver a una hora determinada.
**objetivo:** Resolver la consulta de precio y considerar la restricción horaria sin prometer una duración o visita no confirmada.

**1. cliente** `[scripted]` — Cuánto es el costo de la mantención?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. La mantención de calefont tiene un valor de $40.000, y la de caldera $60.000. ¿Cuál de los dos necesitas mantener?

**2. cliente** `[scripted]` — En todo caso estaba de más, si el precio es 130
> *bot:* No tengo ese dato. ¿Prefieres que te tome los datos para coordinar una visita, o que te atienda una persona?

**3. cliente** `[scripted]` — Maximiliano, te pregunto. Cuánto se demora en el trabajo?
> *bot:* Gracias, Maximiliano. No tengo un dato oficial de cuánto dura la mantención: depende del tipo de equipo y de su estado. Puedo tomar tus datos para coordinar la visita y ahí el técnico te indica el tiempo estimado. ¿Es calefont o caldera?

**4. cliente** `[scripted]` — Tengo que salir a las 2, volviendo a las 4pm
> *bot:* Entiendo. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**5. cliente** `[scripted]` — Para que lo puedan considerar
> *bot:* Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**estado final:** `bot` · **juez:** 0.00 · **hard fail:** True
**gates:** G1 ✓, G4 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, escalation ±3, policy ±1, tone ±1

## `real-monica-diagnostico-no-confirmado` [complejo]

**persona:** Clienta que trae una explicación técnica extensa copiada desde ChatGPT y pregunta si corresponde a los ruidos de las cañerías de su casa.
**objetivo:** Recibir una respuesta prudente que no presente como comprobado un diagnóstico remoto ni la explicación copiada.

**1. cliente** `[scripted]` — Buenos días, cómo estás? vienes hoy?  mira le pregunte al chat gpt por la cañería de mi casa , te hace sentido algo?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**2. cliente** `[scripted]` — Si las cañerías de la calefacción hacen ruido, puede deberse a varias causas. Los sonidos más comunes y sus posibles motivos son:
Golpeteos o "clac-clac": las tuberías se expanden y contraen al calentarse y enfriarse. Si están muy ajustadas a soportes o atraviesan muros sin espacio suficiente, pueden producir golpes.
Ruidos de agua corriendo o burbujeo: suele indicar que hay aire atrapado en el sistema. En radiadores, normalmente se soluciona purgándolos.
Silbidos o zumbidos: pueden deberse a una válvula parcialmente cerrada, una bomba de circulación funcionando a una velocidad inadecuada o una presión excesiva del agua.
Golpes fuertes al encender o apagar: pueden estar relacionados con cambios bruscos de presión o con problemas en válvulas de cierre rápido.
Vibraciones continuas: a veces una bomba de circulación desgastada o mal fijada transmite vibraciones a las tuberías.
Para orientar mejor el diagnóstico, sería útil saber:
¿Qué tipo de calefacción tienes (radiadores, losa radiante, caldera, calefacción central del edificio, etc.)?
¿Qué tipo de ruido hace exactamente (golpes, silbidos, burbujeos, vibración)?
¿Ocurre solo cuando se enciende la calefacción o durante todo el funcionamiento?
radiadores
Si tienes radiadores, la causa más frecuente depende del tipo de ruido:
Burbujeos, gorgoteos o sonido de agua: normalmente hay aire atrapado en los radiadores. La solución suele ser purgarlos para que salga el aire.
Golpecitos metálicos o crujidos: las tuberías y los radiadores se expanden al calentarse y se contraen al enfriarse. Esto es bastante común, especialmente al encender la calefacción.
Silbidos: puede haber una válvula parcialmente cerrada o un caudal de agua demasiado alto.
Zumbido o vibración constante: puede provenir de la bomba de circulación de la caldera o de una válvula.
¿El ruido viene de los radiadores mismos o de las tuberías dentro de las paredes/suelo? ¿Y es más bien un burbujeo, un golpe metálico o un silbido? Eso ayuda a identificar la causa con más precisión.
tuberias
Si el ruido viene de las tuberías y no de los radiadores, las causas más habituales son:
Dilatación térmica de las tuberías (la más común)
Se escuchan chasquidos, crujidos o pequeños golpes cuando la calefacción arranca o se apaga.
Ocurre porque el metal o el plástico se expanden al calentarse y rozan con soportes, paredes o pisos.
Aire en el circuito
Produce sonidos de burbujeo o agua corriendo dentro de las tuberías.
Suele requerir purgar los radiadores y, en algunos casos, revisar la presión del sistema.
Velocidad de circulación demasiado alta
Puede generar silbidos o ruido de flujo de agua.
A veces se ajusta en la bomba de circulación de la caldera.
Soportes flojos o tuberías mal sujetas
Pueden vibrar y transmitir ruido a la estructura de la vivienda.
Una pregunta clave: ¿el ruido es un "toc-toc" o crujido, o más bien un sonido de agua corriendo/burbujeando? Además, ¿ocurre principalmente cuando la calefacción empieza a calentar o durante todo el tiempo que está encendida? Esto permite distinguir rápidamente entre dilatación térmica y aire en el sistema.
> *bot:* ¿En qué comuna te encuentras?

**estado final:** `bot` · **juez:** 2.50 · **hard fail:** False
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, conversational ±1, escalation ±1, grounding ±1, policy ±2, tone ±1
