# Conversaciones de la corrida `gates-respond-2`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `simple-cobertura-comuna` [simple]

**persona:** Cliente que vive en Maipú y quiere saber si llegan, sin decir todavía qué trabajo necesita.
**objetivo:** Averiguar si Lumat atiende en su comuna.

**1. cliente** `[scripted]` — hola, ustedes trabajan en maipu?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. No tenemos cobertura habitual en maipu, pero igual podemos ayudarte: un asesor coordina la visita según disponibilidad.

**estado final:** `bot` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G6 ✓, G7 ✓, G8 ✓, G9 ✓

## `super-near-miss-lavadora` [supercomplejo]

**persona:** Cliente que asume que Lumat hace de todo y pregunta por un servicio que no está en el catálogo, insistiendo dos veces.
**objetivo:** Que alguien le repare la lavadora.

**1. cliente** `[scripted]` — hola, arreglan lavadoras? se me inundo el lavadero
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Hola, gracias por escribir. Te cuento al tiro: Lumat no repara lavadoras ni lavadoras-secadoras, así que por ese lado no te puedo ayudar. Ahora, si la inundación del lavadero viene de una filtración o problema de gasfitería, eso sí lo vemos: la visita técnica tiene un valor de $30.000. ¿La pérdida de agua ya está controlada o sigue saliendo?

**2. cliente** `[scripted]` — pero es una lavadora secadora, nadie me la quiere ver
> *bot:* Te entiendo, es frustrante que nadie te la quiera ver. Para ser claro: la reparación del equipo como tal no está dentro de nuestros servicios, así que no te quiero hacer perder el tiempo con eso. Lo que sí cubrimos es la gasfitería del lavadero: la conexión de agua, el desagüe o la filtración que provocó la inundación. Eso lo puede revisar un técnico en visita, con un valor de $30.000. ¿La pérdida de agua se ve en la conexión o desagüe del muro, o sale desde la máquina misma?

**estado final:** `bot` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G7 ✓, G8 ✓

## `real-caldera-urgencia` [supercomplejo]

**persona:** Clienta de Ñuñoa con una caldera que no entrega agua caliente y pregunta qué hacer ante una urgencia.
**objetivo:** Obtener una respuesta segura y un siguiente paso para la falla de la caldera.

**1. cliente** `[scripted]` — Buenas noches disculpe que lo moleste pero tengo problemas con la Caldera no da agua caliente  le sale el aire y nada y me da este error lo terrible que mañana tengo que salir temprano  y como me baño!
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo. ¿En qué comuna te encuentras?

**2. cliente** `[scripted]` — Que hago?
> *bot:* Tranquilo, vamos a resolverlo. Para calderas sin agua caliente lo más rápido es una visita técnica; el valor es $30.000 y la coordinamos según disponibilidad de técnicos. Dime en qué comuna estás y si el display muestra algún código de error (por ejemplo E1, F28 u otro). Con eso vemos si alcanzamos a coordinar algo para hoy o para mañana temprano.

> *bot:* ¿En qué comuna te encuentras?

**3. cliente** `[scripted]` — Soy de ñuñoa
> *bot:* ¿Qué días y horarios te acomodan para la visita?

**4. cliente** `[scripted]` — Necesito solución de emergencia?
> *bot:* Un asesor revisará tu caso y te contactará a la brevedad.

**5. cliente** `[scripted]` — Si se puede?
**estado final:** `human` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G8 ✓
