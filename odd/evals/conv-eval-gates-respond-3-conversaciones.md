# Conversaciones de la corrida `gates-respond-3`

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
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Hola, gracias por escribir. Te cuento altiro: no reparamos lavadoras ni lavadoras-secadoras, eso queda fuera de nuestros servicios. Lo que sí podemos ver es la parte de gasfitería: si el agua viene del desagüe o de la red, coordinamos una visita técnica de $30.000. Mientras tanto, si hay agua cerca de enchufes o alargadores, corta la electricidad de ese sector. ¿El agua sale de la lavadora misma o del desagüe del lavadero?

**2. cliente** `[scripted]` — pero es una lavadora secadora, nadie me la quiere ver
> *bot:* Entiendo, y debe ser frustrante que nadie te la vea. Te lo digo claro para no hacerte perder tiempo: la reparación de lavadora-secadora no está dentro de nuestros servicios, así que no puedo ofrecerte ese trabajo. Lo que sí puedo hacer es coordinar la visita de gasfitería de $30.000 para revisar el lavadero y el desagüe, que es lo que provoca la inundación. ¿El agua sale del desagüe del lavadero o de la lavadora misma? Con eso te digo si la visita sirve o no.

**estado final:** `bot` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G7 ✓, G8 ✓

## `real-caldera-urgencia` [supercomplejo]

**persona:** Clienta de Ñuñoa con una caldera que no entrega agua caliente y pregunta qué hacer ante una urgencia.
**objetivo:** Obtener una respuesta segura y un siguiente paso para la falla de la caldera.

**1. cliente** `[scripted]` — Buenas noches disculpe que lo moleste pero tengo problemas con la Caldera no da agua caliente  le sale el aire y nada y me da este error lo terrible que mañana tengo que salir temprano  y como me baño!
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo. ¿En qué comuna te encuentras?

**2. cliente** `[scripted]` — Que hago?
> *bot:* Tranquilo, algo se puede hacer. Para orientarte bien, cuéntame qué error aparece en la pantalla de la caldera: ¿un código, una sigla o un mensaje? Con eso te digo si es algo que se resuelva en la visita o si conviene revisarla luego. La visita técnica tiene un valor de $30.000, y como estamos de noche la coordinación se hace con un asesor según disponibilidad. ¿Qué error te muestra?

**3. cliente** `[scripted]` — Soy de ñuñoa
> *bot:* ¿Qué días y horarios te acomodan para la visita?

**4. cliente** `[scripted]` — Necesito solución de emergencia?
> *bot:* Un asesor revisará tu caso y te contactará a la brevedad.

**5. cliente** `[scripted]` — Si se puede?
**estado final:** `human` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G8 ✓
