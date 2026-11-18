# Conversaciones de la corrida `captura-eval-limpio`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `real-vocabulario-impreciso` [simple]

**persona:** Propietaria que usa vocabulario coloquial e impreciso para describir una pieza.
**objetivo:** Saber si se puede revisar el quemador descrito sin asumir qué significa.

**1. cliente** `[scripted]` — Mira, tengo un quemador d ella cocina agripado y quería saber si ustedes arreglan eso
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Sí, lo reparamos: los quemadores de cocina están dentro de nuestros servicios de gasfitería. De hecho tengo registrado un trabajo abierto por reparación de quemador de cocina de hoy, así que ese caso ya está en curso. Cuéntame, ¿el quemador no gira para nada, o gira pero está duro y no pasa bien el gas?

**estado final:** `bot` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G8 ✓

## `real-arrendatario-no-decide` [complejo]

**persona:** Arrendataria que explica su rol y consulta si puede enviarse un presupuesto al dueño.
**objetivo:** Pedir un presupuesto sin atribuirse la autorización del propietario.

**1. cliente** `[scripted]` — Yo estoy arrendando la casa a la señora [nombre]
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso.

**2. cliente** `[scripted]` — Entonces le podría enviar un presupuesto
> *bot:* Claro, te preparo el presupuesto para que se lo puedas enviar. Cuéntame qué equipo es y qué problema tiene, así sé qué servicio corresponde. Si el trabajo requiere revisión en terreno, la visita técnica está en $30.000.

**3. cliente** `[scripted]` — Por favor 🙏🏻🙏🏻
> *bot:* Con gusto te lo preparo. Para armarlo necesito solo un dato: ¿qué artefacto es y qué necesita? Por ejemplo, mantención de calefont, revisión de caldera o alguna falla puntual.

**4. cliente** `[scripted]` — Yo arriendo hace 7 años esta casa
> *bot:* Con gusto. ¿En qué más te puedo ayudar?

**5. cliente** `[scripted]` — Y vivo con tres niños
> *bot:* Con gusto. ¿En qué más te puedo ayudar?

**estado final:** `bot` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G8 ✓

## `real-cotizacion-fuera-catalogo` [supercomplejo]

**persona:** Propietaria referida que pregunta por un trabajo que requiere cotización.
**objetivo:** Obtener el siguiente paso para cotizar el cambio de caldera.

**1. cliente** `[scripted]` — Hola [nombre]
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Con gusto. ¿En qué más te puedo ayudar?

**2. cliente** `[scripted]` — Todo bien
> *bot:* Con gusto. ¿En qué más te puedo ayudar?

**3. cliente** `[scripted]` — Ok
> *bot:* Con gusto. ¿En qué más te puedo ayudar?

**4. cliente** `[scripted]` — No hay problema
> *bot:* ¿Te puedo ayudar en algo más?

**5. cliente** `[scripted]` — Hola [nombre], si muchas gracias.
De todas maneras me gustaría cotizar el cambio de caldera por favor
> *bot:* Con gusto te ayudamos con la cotización del cambio de caldera. Para orientarla necesito saber qué caldera tienes hoy (marca y modelo si los tienes) y qué tipo de combustible usa, gas natural o licuado. Con esos datos la revisa un asesor y te la hace llegar.

**estado final:** `bot` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G8 ✓

## `real-maria-jesus-evaluacion-caldera` [supercomplejo]

**persona:** Clienta que pide una segunda evaluación porque la presión del sistema de calefacción sigue bajando tras una intervención anterior.
**objetivo:** Obtener una evaluación y un siguiente paso sin diagnóstico remoto ni maniobras sobre la caldera.

**1. cliente** `[scripted]` — La persona que me hizo la mantención el año pasado me dijo lo de la microfuga. De hecho el año pasado  le pasó liquido sellante y me dijo qie con eso andaria bien pero nunca quedó bien.
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo, y gracias por contarlo: si le pusieron sellante y nunca quedó bien, esa microfuga sigue ahí. Tengo registrado un caso de postventa abierto justamente hoy, así que lo vamos a revisar por esa vía. Para orientarte mejor: ¿cómo está funcionando el equipo ahora? ¿Pierde agua, baja la presión, se apaga solo, o el problema es otro?

**2. cliente** `[scripted]` — Esto fue el año pasado al final de la temporada, el sistema nunca se estabilizó completamente y me dijo que probablemente habria que hacer de nuevo el procedimiento. Por eso me gustaría tener una nueva evaluación y cotización
> *bot:* Entiendo, quieres hacer mantención de sistema de calefacción. ¿En qué comuna te encuentras?

**3. cliente** `[scripted]` — Una semana...10 dias
> *bot:* Entiendo, quieres una nueva evaluación con cotización. ¿En qué comuna te encuentras?

**4. cliente** `[scripted]` — El problema es que no se como rellenar  tampoco, ahora esta en rojo otra vez 🥺
> *bot:* ¿Cuál es tu nombre?

**5. cliente** `[scripted]` — Cuando recien se enciende vuelve a subir y luego baja
> *bot:* ¿Cuál es tu nombre?

**estado final:** `bot` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G6 ✓, G8 ✓
