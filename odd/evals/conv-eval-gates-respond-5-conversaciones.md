# Conversaciones de la corrida `gates-respond-5`

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
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Qué lata lo que pasó. Te cuento al tiro: no reparamos lavadoras, así que ese servicio no lo podemos tomar. Si el agua llegó cerca de enchufes o del enchufe de la lavadora, no los toques: corta la electricidad desde el automático si puedes hacerlo con seguridad. ¿El agua alcanzó algún artefacto eléctrico o quedó solo en el piso del lavadero?

**2. cliente** `[scripted]` — pero es una lavadora secadora, nadie me la quiere ver
> *bot:* Entiendo la frustración, y prefiero decírtelo claro: las lavadoras-secadoras no están dentro de nuestros servicios, así que no te voy a ofrecer algo que no hacemos. Lo que sí puedo coordinar es una visita técnica ($30.000) para revisar la instalación del lavadero, aguas y conexiones, por si el origen del problema está ahí y no en el equipo. ¿El agua llegó hasta las conexiones del lavadero o quedó solo en el piso?

**estado final:** `bot` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G7 ✓, G8 ✓

## `real-caldera-urgencia` [supercomplejo]

**persona:** Clienta de Ñuñoa con una caldera que no entrega agua caliente y pregunta qué hacer ante una urgencia.
**objetivo:** Obtener una respuesta segura y un siguiente paso para la falla de la caldera.

**1. cliente** `[scripted]` — Buenas noches disculpe que lo moleste pero tengo problemas con la Caldera no da agua caliente  le sale el aire y nada y me da este error lo terrible que mañana tengo que salir temprano  y como me baño!
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo. ¿En qué comuna te encuentras?

**2. cliente** `[scripted]` — Que hago?
> *bot:* Tranquilo, vamos a resolverlo. Mientras coordinamos, revisa que la llave de paso de agua esté abierta y que el gas esté habilitado, y fíjate en el manual qué significa el código de error que aparece; si el equipo se puede reiniciar según el fabricante, hazlo una vez. La visita técnica tiene un valor de $30.000. Cuéntame qué código de error muestra y en qué comuna estás, y vemos la coordinación para hoy o primera hora.

> *bot:* ¿En qué comuna te encuentras?

**3. cliente** `[scripted]` — Soy de ñuñoa
> *bot:* ¿Qué días y horarios te acomodan para la visita?

**4. cliente** `[scripted]` — Necesito solución de emergencia?
> *bot:* Un asesor revisará tu caso y te contactará a la brevedad.

**5. cliente** `[scripted]` — Si se puede?
**estado final:** `human` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G8 ✓
