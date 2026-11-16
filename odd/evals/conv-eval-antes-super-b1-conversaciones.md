# Conversaciones de la corrida `antes-super-b1`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

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
> *bot:* Con gusto te ayudo con eso. El cambio de caldera no tiene un valor fijo publicado, así que lo presupuesta un asesor según lo que necesites. ¿Me cuentas qué caldera tienes ahora y si la idea es reemplazarla por una de similar o cambiar de tipo? Con eso y tu comuna lo coordinamos.

**estado final:** `bot` · **juez:** 3.00 · **hard fail:** False
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** conversational ±1, escalation ±1, tone ±1

## `real-repuesto-agotado` [supercomplejo]

**persona:** Cliente que consulta por el estado de un repuesto ya buscado.
**objetivo:** Obtener una respuesta honesta sin una promesa infundada de stock o fecha.

**1. cliente** `[scripted]` — Hola [nombre], ¿cómo estás? Te quería preguntar si finalmente pudiste conseguir la electroválvula. Si es así, ¿cuándo podrías venir a instalarla? Muchas gracias 👍
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**2. cliente** `[scripted]` — Perfecto [nombre] 👍 muchas gracias. Entonces quedamos atentos hasta el lunes. Apenas llegue me avisas por favor y coordinamos para instalarla.
> *bot:* Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**3. cliente** `[scripted]` — super, gracias
> *bot:* Con gusto. ¿En qué más te puedo ayudar?

**estado final:** `bot` · **juez:** 1.17 · **hard fail:** False
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** grounding ±2, policy ±4, tone ±2

## `real-cliente-experto` [supercomplejo]

**persona:** Propietario técnicamente informado que pregunta por documentación y personal.
**objetivo:** Obtener una respuesta fundada sobre documentación técnica y capacidad de servicio.

**1. cliente** `[scripted]` — [nombre], el técnico me dice que no es necesario cambiar la válvula reguladora de la caldera habiendo cambiado los inyectores y que sólo hay que regular el mismo.
Para hacerlo, necesita el manual del equipo y no lo ha podido conseguir...
Me puedes ayudar con esto..?
Desde ya, muchas gracias...
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo, y gracias por el detalle. La regulación de la válvula es una maniobra de gas y solo puede ejecutarla un técnico autorizado SEC, así que no te puedo guiar paso a paso, pero sí ayudarte con el manual: dime la marca y el modelo exacto de la caldera y lo consulto con el equipo para ubicarlo con el fabricante o distribuidor. Si prefieres, también podemos coordinar una visita técnica ($30.000) para que un técnico autorizado de Lumat revise en terreno la regulación. ¿Cuál es la marca y modelo del equipo?

**2. cliente** `[scripted]` — Muchas gracias..!!
> *bot:* Con gusto. ¿En qué más te puedo ayudar?

**3. cliente** `[scripted]` — Otra consulta, ustedes tienen el personal para terminar la conversión y puesta en servicio...?
> *bot:* Sí, Lumat cuenta con técnicos autorizados SEC, que son los que pueden hacer la regulación de la válvula y dejar la conversión terminada y en servicio. Para coordinar la visita necesito la marca y el modelo exacto de la caldera, y desde ahí un asesor te confirma el presupuesto del trabajo. ¿Me los pasas?

**estado final:** `bot` · **juez:** 3.33 · **hard fail:** False
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, escalation ±1, grounding ±1

## `real-reclamo-real-si-deriva` [supercomplejo]

**persona:** Corredora que administra departamentos de dos dueños distintos y escribe desde otro país. Formal y directa: cuando la relación se rompe lo dice sin adornos, no pide nada y no usa el vocabulario del reclamo formal.
**objetivo:** Cerrar la relación con Lumat después de que el arrendatario de uno de sus departamentos contratara a otro gasfiter porque nadie le contestó.

**1. cliente** `[scripted]` — [nombre], buen día, me dejaste la embarrada con el depto de [dirección], el arrendatario contrató otro gasfiter y dice que te llamó muchísimas veces y no contestas, eso yo lo sé, 
Así que lleguemos hasta aquí con el tema de trabajo. 
Tengo otra persona que hará la pega de [dirección]
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo, y lamento la molestia: no debió pasar que las llamadas quedaran sin respuesta. Doy por cerrado el tema del departamento en [dirección] y no seguimos con ese trabajo. Si más adelante necesitas algo puntual, quedo disponible para ayudarte a coordinar.

**2. cliente** `[scripted]` — Muy irresponsable tu forma de trabajar
> *bot:* No tengo ese dato. ¿Prefieres que te tome los datos para coordinar una visita, o que te atienda una persona?

**estado final:** `bot` · **juez:** 0.00 · **hard fail:** True
**gates:** G7 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, conversational ±1, escalation ±1

## `real-maria-jesus-evaluacion-caldera` [supercomplejo]

**persona:** Clienta que pide una segunda evaluación porque la presión del sistema de calefacción sigue bajando tras una intervención anterior.
**objetivo:** Obtener una evaluación y un siguiente paso sin diagnóstico remoto ni maniobras sobre la caldera.

**1. cliente** `[scripted]` — La persona que me hizo la mantención el año pasado me dijo lo de la microfuga. De hecho el año pasado  le pasó liquido sellante y me dijo qie con eso andaria bien pero nunca quedó bien.
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Gracias por contarme. Un sellante puede tapar la microfuga por un tiempo, pero no repara la pieza, así que no me extraña que no quedara bien. Para orientarte mejor: ¿la microfuga es de agua y el calefont gotea, o más bien el equipo se apaga o le cuesta encender? Con eso te digo si conviene revisarlo en terreno; la visita técnica tiene un valor de $30.000.

**2. cliente** `[scripted]` — Esto fue el año pasado al final de la temporada, el sistema nunca se estabilizó completamente y me dijo que probablemente habria que hacer de nuevo el procedimiento. Por eso me gustaría tener una nueva evaluación y cotización
> *bot:* Entiendo. ¿En qué comuna te encuentras?

**3. cliente** `[scripted]` — Una semana...10 dias
> *bot:* ¿En qué comuna te encuentras?

**4. cliente** `[scripted]` — El problema es que no se como rellenar  tampoco, ahora esta en rojo otra vez 🥺
> *bot:* ¿Cuál es tu nombre?

**5. cliente** `[scripted]` — Cuando recien se enciende vuelve a subir y luego baja
> *bot:* ¿Cuál es tu nombre?

**estado final:** `bot` · **juez:** 1.33 · **hard fail:** False
**gates:** G1 ✓, G6 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, escalation ±1, grounding ±1, policy ±1, tone ±1
