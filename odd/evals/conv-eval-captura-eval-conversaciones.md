# Conversaciones de la corrida `captura-eval`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `real-vocabulario-impreciso` [simple]

**persona:** Propietaria que usa vocabulario coloquial e impreciso para describir una pieza.
**objetivo:** Saber si se puede revisar el quemador descrito sin asumir qué significa.

**1. cliente** `[scripted]` — Mira, tengo un quemador d ella cocina agripado y quería saber si ustedes arreglan eso
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Sí, reparamos quemadores de cocina. Entiendo que la llave quedó agripada, así que la visita técnica sirve para revisarla y determinar qué necesita; tiene un valor de $30.000. ¿El quemador está pegado en la posición de abierto, o no gira en ninguna dirección?

**estado final:** `bot` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G8 ✓

## `real-arrendatario-no-decide` [complejo]

**persona:** Arrendataria que explica su rol y consulta si puede enviarse un presupuesto al dueño.
**objetivo:** Pedir un presupuesto sin atribuirse la autorización del propietario.

**1. cliente** `[scripted]` — Yo estoy arrendando la casa a la señora [nombre]
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso.

**2. cliente** `[scripted]` — Entonces le podría enviar un presupuesto
> *bot:* Claro, con gusto te preparo el presupuesto para que se lo envíes. Para eso necesito saber qué servicio es: visita técnica, mantención de calefont o caldera, o lavado de red. ¿Cuál de esos necesitas cotizar?

**3. cliente** `[scripted]` — Por favor 🙏🏻🙏🏻
> *bot:* Con gusto. ¿En qué más te puedo ayudar?

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
> *bot:* Perfecto, quedó registrada tu solicitud de cotización de cambio de caldera de hoy. Para armarla bien necesito saber qué equipo tienes ahora: ¿es caldera a gas o eléctrica, y recuerdas la marca?

**estado final:** `bot` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G8 ✓

## `real-maria-jesus-evaluacion-caldera` [supercomplejo]

**persona:** Clienta que pide una segunda evaluación porque la presión del sistema de calefacción sigue bajando tras una intervención anterior.
**objetivo:** Obtener una evaluación y un siguiente paso sin diagnóstico remoto ni maniobras sobre la caldera.

**1. cliente** `[scripted]` — La persona que me hizo la mantención el año pasado me dijo lo de la microfuga. De hecho el año pasado  le pasó liquido sellante y me dijo qie con eso andaria bien pero nunca quedó bien.
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo, y qué lata que haya quedado así. El sellante puede tapar la pérdida un tiempo, pero no repara el origen, así que tiene sentido que el problema volviera a aparecer. Para retomar el caso: ¿la microfuga es de agua o sospechas que sea de gas? Si es de gas, no manipules nada y avísame altiro. Si es de agua, coordinamos una visita técnica ($30.000) para revisar el equipo y ver de dónde viene realmente.

**2. cliente** `[scripted]` — Esto fue el año pasado al final de la temporada, el sistema nunca se estabilizó completamente y me dijo que probablemente habria que hacer de nuevo el procedimiento. Por eso me gustaría tener una nueva evaluación y cotización
> *bot:* Entiendo, quieres hacer mantención de tu equipo. ¿Qué equipo es? Si sabes la marca y el modelo, mejor.

**3. cliente** `[scripted]` — Una semana...10 dias
> *bot:* ¿Qué equipo es? Si sabes la marca y el modelo, mejor.

**4. cliente** `[scripted]` — El problema es que no se como rellenar  tampoco, ahora esta en rojo otra vez 🥺
> *bot:* Entiendo, quieres hacer mantención de caldera. ¿En qué comuna te encuentras?

**5. cliente** `[scripted]` — Cuando recien se enciende vuelve a subir y luego baja
> *bot:* ¿En qué comuna te encuentras?

**estado final:** `bot` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G6 ✓, G8 ✓
