# Conversaciones de la corrida `t4-schedule-answers`

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
> *bot:* Carlos, te respondo directo: los sábados se coordinan con un asesor según disponibilidad, no se agendan de forma automática. La visita técnica tiene un valor de $30.000. ¿Te parece si un asesor te contacta para ver la disponibilidad del sábado en Ñuñoa?

> *bot:* Gracias carlos. ¿Cuál es tu correo electrónico?

**estado final:** `bot` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G6 ✓, G8 ✓, G9 ✓

## `complejo-agendar-calefont` [complejo]

**persona:** Cliente de Ñuñoa que quiere agendar la mantención de su calefont y da los datos en desorden: primero la comuna, después el nombre, y el email recién al final. Mensajes cortos, varias ideas por mensaje.
**objetivo:** Agendar una mantención de calefont en Ñuñoa y quedar con la visita coordinada.

**1. cliente** `[scripted]` — hola, necesito mantener mi calefont, vivo en ñuñoa
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Hola, qué bueno que nos escribes. La mantención de calefont tiene un valor de $50.000 y en Ñuñoa atendemos normalmente. ¿Qué marca es tu calefont y hace cuánto tiempo no le haces mantención?

**2. cliente** `[scripted]` — me llamo carolina, atiendan cuando puedan
> *bot:* Hola Carolina, gusto en conocerte. La mantención de calefont tiene un valor de $50.000 y en Ñuñoa atendemos normalmente. Para orientarte mejor: ¿qué marca es tu calefont y hace cuánto tiempo no le haces mantención?

**3. cliente** `[scripted]` — el calefont es junkers, tiro natural
> *bot:* Gracias, Carolina. Un Junkers tiro natural se puede mantener sin problema; la mantención incluye limpieza de componentes accesibles, revisión de quemadores, encendido, filtros, fugas sin cambio de piezas y evacuación de gases. ¿Hace cuánto tiempo no le haces mantención y en qué horario te acomoda que vayamos?

**4. cliente** `[scripted]` — si, me sirve cualquier dia en la mañana
> *bot:* Gracias Carolina. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**5. cliente** `[scripted]` — carolina.p@gmail.com
> *bot:* Gracias, Carolina. Anoto tu correo para el contacto. Para cerrar la visita en la mañana, ¿me confirmas tu dirección en Ñuñoa y un teléfono de contacto? Con eso queda todo listo para coordinar.

> *bot:* Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**estado final:** `bot` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G6 ✓, G8 ✓

## `complejo-fuera-de-cobertura-insiste` [complejo]

**persona:** Cliente de Temuco que necesita una mantención de caldera y no acepta un no como respuesta. Pregunta dos veces si de verdad no pueden.
**objetivo:** Conseguir que alguien coordine la mantención de su caldera en Temuco.

**1. cliente** `[scripted]` — hola, necesito mantencion de caldera, estoy en temuquito
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Todavía no tenemos visitas técnicas en Temuco para tu caldera, un asesor de Lumat se contactará contigo para ayudarte a la brevedad. El precio vigente de Mantención de caldera es $80.000. Un asesor coordinará contigo la visita; todavía no puedo confirmar fecha ni hora.

**2. cliente** `[scripted]` — pero ustedes no van a ir hasta aca? es una caldera grande
> *bot:* Entiendo tu duda. Temuco no está dentro de nuestra cobertura habitual, así que no puedo confirmarte que vayamos hasta allá; por eso un asesor revisará tu caso y te dirá si es posible coordinar la visita. Que la caldera sea grande no cambia el valor de la mantención, que es $80.000, pero sí conviene que el asesor lo sepa. ¿Qué marca y modelo es la caldera?

**3. cliente** `[scripted]` — y quien me va a contactar entonces
> *bot:* Un asesor de Lumat te va a contactar al número desde el que estás escribiendo para coordinar la visita y confirmar si es posible ir hasta Temuco. No puedo decirte su nombre ni un plazo exacto, pero el caso queda registrado con lo que ya me contaste. Si quieres, déjame la marca y modelo de la caldera para que el asesor llegue con esa información.

**estado final:** `human` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G10 ✓, G6 ✓, G7 ✓, G8 ✓, G9 ✓

## `super-burst-contradiccion` [supercomplejo]

**persona:** Cliente que manda tres mensajes seguidos sin esperar respuesta y se contradice: primero calefont, después caldera, y la comuna tampoco es la que dijo al principio.
**objetivo:** Coordinar la mantención del equipo correcto en la comuna correcta.

**1. cliente** `[scripted]` — hola
> *bot:* Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar.

**2. cliente** `[scripted]` — necesito arreglar un calefont
> *bot:* Entiendo, es un problema con tu calefont. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**3. cliente** `[scripted]` — no era calefont, es una caldera, y estoy en providencia
> *bot:* Todavía no tenemos visitas técnicas en Providencia para tu caldera, un asesor de Lumat se contactará contigo para ayudarte a la brevedad. El valor de este trabajo requiere cotización. Un asesor coordinará contigo la visita; todavía no puedo confirmar fecha ni hora.

**4. cliente** `[scripted]` — cuanto sale y cuando pueden venir
> *bot:* No tengo ese dato. ¿Prefieres que te tome los datos para coordinar una visita, o que te atienda una persona?

**estado final:** `human` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G10 ✓, G4 ✓, G6 ✓, G8 ✓
