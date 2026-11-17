# Conversaciones de la corrida `gates-uno`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `simple-dia-especifico` [simple]

**persona:** Cliente que solo puede recibir al técnico un día concreto de la semana y lo dice de entrada, sin ofrecer alternativas.
**objetivo:** Agendar la mantención del calefont para el día que el cliente pidió.

**1. cliente** `[scripted]` — hola, necesito una mantencion de calefont, vivo en ñuñoa, puedo el jueves en la mañana
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo. ¿Cuál es tu nombre?

**2. cliente** `[scripted]` — me llamo paula, paula@mail.com, avenida irarrazaval 40, ñuñoa
> *bot:* ¿Autorizas que guardemos tus datos para gestionar tu solicitud? Responde sí o no.

**3. cliente** `[scripted]` — si
> *bot:* No encontré un horario que nos sirva en la agenda, así que no te voy a dejar esperando: un asesor de Lumat te contacta para coordinar la visita directamente.

**estado final:** `human` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G6 ✓, G8 ✓

## `complejo-dos-temas` [complejo]

**persona:** Cliente que primero pregunta un precio y después, sobre ese mismo servicio, pregunta por la garantía. No repite el nombre del servicio.
**objetivo:** Saber el precio del lavado de red y después cuánta garantía tiene.

**1. cliente** `[scripted]` — hola, cuanto cuesta el lavado de red?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. El lavado de red tiene un valor de $120.000. Incluye la limpieza profunda del circuito de calefacción central (tuberías, radiadores y componentes) para sacar lodos, óxido y sedimentos. Eso sí, te aclaro algo importante: el lavado de red no incluye reparación de calderas. Si el problema es que la caldera no entrega agua caliente, eso se ve aparte, con una visita técnica de $30.000. ¿El lavado de red lo necesitas para la misma propiedad de Ñuñoa donde está la caldera?

**2. cliente** `[scripted]` — y eso cuanto de garantia tiene?
> *bot:* El lavado de red tiene garantía de 6 meses, y cubre la mano de obra del trabajo realizado; los repuestos no están incluidos. Ahora, lo que me contabas de la caldera sin agua caliente no entra en el lavado de red: eso requiere una visita técnica de $30.000, que se descuenta si después contratas la mantención o reparación. ¿Te coordino esa visita para hoy?

**estado final:** `bot` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G6 ✓, G8 ✓, G9 ✓

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

## `real-precio-mantencion-ciclo` [simple]

**persona:** Clienta recurrente que pregunta por el ciclo de mantención.
**objetivo:** Aclarar si corresponde realizar la mantención y cada cuánto.

**1. cliente** `[scripted]` — Corresponde hacerla??
Es cada 6 meses??
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Sí, en su caso la mantención de caldera quedó pendiente desde hoy. Sobre cada cuánto corresponde, no tengo esa frecuencia confirmada en nuestra información: la pauta la define el fabricante del equipo y prefiero no inventarla. Ahora, si la caldera sigue sin dar agua caliente y le muestra un error, eso ya es una falla más que una mantención. ¿Coordinamos una visita técnica para revisarla? Así también le decimos si alcanza a tener agua caliente para mañana temprano.

**estado final:** `bot` · **juez:** 0.00 · **hard fail:** False
**gates:** G1 ✓, G2 ✗ (intents vistos ['consulta'], esperaba alguno de: valores), G4 ✓, G8 ✓

## `real-dato-mas-pregunta` [complejo]

**persona:** Clienta que ya entregó datos y agrega una pregunta sobre el horario.
**objetivo:** Obtener respuesta a la pregunta manteniendo los datos previamente entregados.

**1. cliente** `[scripted]` — 18:30 comienzo con los chicos
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso.

**2. cliente** `[scripted]` — Yo creo qje no alcanza, y mañana?
> *bot:* No tienes visitas próximas para reagendar.

**3. cliente** `[scripted]` — es factible que pases tipo 14 horas?
> *bot:* No tienes visitas próximas para reagendar.

**estado final:** `bot` · **juez:** 0.00 · **hard fail:** False
**gates:** G1 ✓, G4 ✗ (se registró lo prohibido: unknown_intent), G8 ✓

## `real-mantencion-caldera` [simple]

**persona:** Clienta que solicita la mantención de su caldera y deja el equipo funcionando.
**objetivo:** Coordinar la mantención de la caldera.

**1. cliente** `[scripted]` — Mantencion
Esta funcionando bien la calefacción.
Quiero mantencion
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo. ¿En qué comuna te encuentras?

**2. cliente** `[scripted]` — Me avisas a que hora puedes venir .
> *bot:* ¿En qué comuna te encuentras?

**estado final:** `bot` · **juez:** 0.00 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G6 ✗ (ninguna respuesta contiene: mantenci, caldera), G8 ✓

## `real-claudio-caldera-valvula` [complejo]

**persona:** Cliente que sigue una falla de caldera, aporta un error nuevo y pregunta si debe cortar una llave después de enviar un video.
**objetivo:** Obtener un siguiente paso seguro sin un diagnóstico remoto ni instrucciones improvisadas sobre las válvulas.

**1. cliente** `[scripted]` — Vale gracias, voy a esperar que termine la lavadora (20 min) y corto… te aviso como me fue, te parece?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Con gusto. ¿En qué más te puedo ayudar?

**2. cliente** `[scripted]` — Como dato, corte la calefacción central hace 1 semana desde la caldera y no intervine el termostato… influirá eso?
> *bot:* No debería influir: dejar la calefacción cortada desde la caldera no altera el termostato ni deja el circuito en mala condición para lo que vas a hacer. Si acaso, tener el sistema apagado estos días hace que el agua esté más fría, nada más. Cuando termines, cuéntame cómo te fue y qué notaste, y vemos el siguiente paso.

**3. cliente** `[scripted]` — 
> *bot:* Recibí tu archivo, lo guardé para el técnico.

**4. cliente** `[scripted]` — Aumentamos… pasamos de E25 a E26 😂
> *bot:* Entiendo. ¿En qué comuna te encuentras?

**5. cliente** `[scripted]` — Corto la llave de agua de la caldera?
> *bot:* No tengo ese dato. ¿Prefieres que te tome los datos para coordinar una visita, o que te atienda una persona?

**estado final:** `bot` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G8 ✓
