# Conversaciones de la corrida `despues-simple`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `simple-saludo-variante` [simple]

**persona:** Persona adulta que abre el chat con un saludo largo y coloquial, sin decir todavía qué necesita. Escribe con minúsculas y sin tildes.
**objetivo:** Saludar y esperar a que el asistente se presente y pregunte en qué puede ayudar.

**1. cliente** `[scripted]` — hola buenas tardes
> *bot:* Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar.

**estado final:** `bot` · **juez:** 4.00 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G6 ✓, G8 ✓
**dispersión entre repeticiones:** conversational ±1

## `simple-precio-calefont` [simple]

**persona:** Dueña de casa en Ñuñoa que pregunta el precio derecho, sin rodeos, y escribe rápido con faltas de tilde.
**objetivo:** Saber cuánto cuesta la mantención de su calefont.

**1. cliente** `[scripted]` — hola
> *bot:* Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar.

**2. cliente** `[scripted]` — cuanto sale la mantencion de calefont?
> *bot:* La mantención de calefont tiene un valor de $40.000. Incluye inspección general, limpieza de componentes accesibles, revisión de quemadores, encendido, filtros y conexiones, más pruebas de funcionamiento. Según lo que veo, tienes una mantención de calefont pendiente. ¿Quieres que coordinemos la visita?

**estado final:** `bot` · **juez:** 4.00 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G6 ✓, G8 ✓

## `simple-cobertura-comuna` [simple]

**persona:** Cliente que vive en Maipú y quiere saber si llegan, sin decir todavía qué trabajo necesita.
**objetivo:** Averiguar si Lumat atiende en su comuna.

**1. cliente** `[scripted]` — hola, ustedes trabajan en maipu?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Hola. Atendemos con cobertura habitual en varias comunas de la Región Metropolitana, y si estás fuera de ella igual podemos coordinar la visita. Para confirmarte Maipú, cuéntame qué trabajo necesitas y lo reviso con un asesor.

**estado final:** `bot` · **juez:** 2.83 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G6 ✓, G7 ✓, G8 ✓, G9 ✓
**dispersión entre repeticiones:** escalation ±2, grounding ±1, policy ±1, tone ±1

## `simple-horario-sabado` [simple]

**persona:** Cliente que trabaja de lunes a viernes y solo puede recibir al técnico un sábado.
**objetivo:** Saber si puede agendar una visita para el sábado.

**1. cliente** `[scripted]` — hola, buenas
> *bot:* Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar.

**2. cliente** `[scripted]` — necesito una visita, el calefont no calienta. vivo en ñuñoa y solo puedo un sabado
> *bot:* Entiendo. ¿Cuál es tu nombre?

**3. cliente** `[scripted]` — carlos. pero dime altiro si atienden sabado, eso es lo que necesito saber
> *bot:* Hola Carlos. Los sábados se coordinan con un asesor según la disponibilidad real de técnicos; no puedo confirmarte un horario de antemano, pero Ñuñoa está dentro de nuestra cobertura habitual. La visita técnica tiene un valor de $30.000. Si te parece, indícame la dirección y un par de horarios posibles del sábado para dejarlo en coordinación.

> *bot:* ¿Cuál es tu correo electrónico?

**estado final:** `bot` · **juez:** 2.50 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G6 ✓, G8 ✓, G9 ✓
**dispersión entre repeticiones:** closure ±2, escalation ±4, grounding ±2, tone ±1

## `simple-dia-especifico` [simple]

**persona:** Cliente que solo puede recibir al técnico un día concreto de la semana y lo dice de entrada, sin ofrecer alternativas.
**objetivo:** Agendar la mantención del calefont para el día que el cliente pidió.

**1. cliente** `[scripted]` — hola, necesito una mantencion de calefont, vivo en ñuñoa, puedo el jueves en la mañana
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo. ¿Cuál es tu nombre?

**2. cliente** `[scripted]` — me llamo paula, paula@mail.com, calle siempre viva 123, ñuñoa
> *bot:* ¿Cuál es tu dirección?

**3. cliente** `[scripted]` — si
> *bot:* ¿Cuál es tu dirección o, si te es más fácil, puedes enviarme tu ubicación con el pin de WhatsApp?

**estado final:** `bot` · **juez:** 0.00 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G6 ✗ (ninguna respuesta contiene: horario, visita, agend), G8 ✓
**dispersión entre repeticiones:** escalation ±4

## `simple-despedida` [simple]

**persona:** Cliente que ya obtuvo lo que necesitaba y cierra amablemente. Sigue escribiendo con faltas de tilde.
**objetivo:** Recibir el dato de la mantención de caldera y terminar la conversación.

**1. cliente** `[scripted]` — hola, cuanto sale la mantencion de caldera?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Hola. La mantención de caldera tiene un valor de $60.000 e incluye inspección general, revisión de combustión, control de presión, limpieza de filtros, purgado y puesta en marcha. ¿Quieres que coordinemos la visita para revisar tu equipo?

**2. cliente** `[scripted]` — dale, muchas gracias, eso era todo
> *bot:* ¡Gracias por escribirnos! Que tengas buen día.

**estado final:** `closed` · **juez:** 3.83 · **hard fail:** False
**gates:** G4 ✓, G6 ✓, G8 ✓

## `real-cortesia-no-es-reclamo` [simple]

**persona:** Cliente recurrente que escribe con cercanía y cortesía chilena.
**objetivo:** Consultar sin que una expresión de cortesía se clasifique como reclamo.

**1. cliente** `[scripted]` — [nombre] como estas?, te molesto con la última pls?, el agua de duchas está impecable
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Con gusto. ¿En qué más te puedo ayudar?

**estado final:** `bot` · **juez:** 3.33 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G5 ✓, G8 ✓
**dispersión entre repeticiones:** conversational ±1, tone ±1

## `real-precio-mantencion-ciclo` [simple]

**persona:** Clienta recurrente que pregunta por el ciclo de mantención.
**objetivo:** Aclarar si corresponde realizar la mantención y cada cuánto.

**1. cliente** `[scripted]` — Corresponde hacerla??
Es cada 6 meses??
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Sí, la mantención quedó registrada como pendiente de hoy. Sobre la frecuencia, la pauta exacta la indica el manual del fabricante: en general se recomienda una vez al año, y cada 6 meses en equipos de uso muy intensivo. ¿Es un calefont o una caldera lo que necesitas mantener?

**estado final:** `bot` · **juez:** 0.00 · **hard fail:** True
**gates:** G1 ✓, G2 ✗ (intents vistos ['consulta'], esperaba alguno de: valores), G4 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, conversational ±1, policy ±2

## `real-cobertura-condominio` [simple]

**persona:** Propietaria que llega referida por el chat de su condominio.
**objetivo:** Consultar si Lumat puede ayudar con su caldera y su comuna.

**1. cliente** `[scripted]` — Hola buenas tardes. Me compartieron tu contacto del chat de mi condominio
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Con gusto. ¿En qué más te puedo ayudar?

**estado final:** `bot` · **juez:** 3.33 · **hard fail:** False
**gates:** G1 ✓, G8 ✓, G9 ✓
**dispersión entre repeticiones:** tone ±1

## `real-vocabulario-impreciso` [simple]

**persona:** Propietaria que usa vocabulario coloquial e impreciso para describir una pieza.
**objetivo:** Saber si se puede revisar el quemador descrito sin asumir qué significa.

**1. cliente** `[scripted]` — Mira, tengo un quemador d ella cocina agripado y quería saber si ustedes arreglan eso
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Sí, reparamos quemadores de cocina. Para orientarte mejor, ¿el quemador está pegado o duro para girar la perilla, o más bien no enciende o prende con llama irregular? Si prefieres, coordinamos una visita técnica ($30.000) para revisarlo en tu domicilio.

**estado final:** `bot` · **juez:** 3.50 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G8 ✓
**dispersión entre repeticiones:** policy ±1

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
**dispersión entre repeticiones:** closure ±1, conversational ±1, escalation ±2, grounding ±2, tone ±1

## `real-hector-discrepancia-valor` [simple]

**persona:** Cliente que pregunta por una diferencia entre el valor que recuerda y el precio que le comunicaron.
**objetivo:** Aclarar la discrepancia sin inventar un precio individual ni afirmar un pago.

**1. cliente** `[scripted]` — Hola Max pero no era 60.000?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. No tengo ese dato. ¿Prefieres que te tome los datos para coordinar una visita, o que te atienda una persona?

**estado final:** `bot` · **juez:** 3.33 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G8 ✓
**dispersión entre repeticiones:** escalation ±2, tone ±1
