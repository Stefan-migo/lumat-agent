# Conversaciones de la corrida `gates-respond-4`

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
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Hola, gracias por escribir. Te aclaro altiro: Lumat no repara lavadoras ni lavadoras-secadoras, ese servicio no está en nuestro catálogo. La inundación del lavadero sí la podemos revisar como trabajo de gasfitería, con una visita técnica de $30.000. Mientras tanto, si puedes cerrar la llave de paso del sector y evitar usar enchufes o artefactos en la zona mojada, mejor. ¿La filtración viene de la llave o conexión de agua, o del desagüe?

**2. cliente** `[scripted]` — pero es una lavadora secadora, nadie me la quiere ver
> *bot:* Te entiendo, y te lo digo claro: no reparamos lavadoras-secadoras, aunque sea el combo, ese servicio no está en nuestro catálogo. Lo que sí podemos ver es la inundación del lavadero como gasfitería, con visita técnica de $30.000, y ahí revisamos la conexión de agua y el desagüe que están provocando la fuga. ¿La filtración sale de la llave o conexión de agua, o del desagüe?

**estado final:** `bot` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G7 ✓, G8 ✓

## `real-caldera-urgencia` [supercomplejo]

**persona:** Clienta de Ñuñoa con una caldera que no entrega agua caliente y pregunta qué hacer ante una urgencia.
**objetivo:** Obtener una respuesta segura y un siguiente paso para la falla de la caldera.

**1. cliente** `[scripted]` — Buenas noches disculpe que lo moleste pero tengo problemas con la Caldera no da agua caliente  le sale el aire y nada y me da este error lo terrible que mañana tengo que salir temprano  y como me baño!
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo. ¿En qué comuna te encuentras?

**2. cliente** `[scripted]` — Que hago?
> *bot:* Entiendo la urgencia. No manipules la llave ni la línea de gas. Un técnico de Lumat debe verificarlo; un asesor puede coordinar la visita.; no abras la caldera ni manipules nada por dentro. Si con eso no parte, a esta hora la coordinación se hace con un asesor según disponibilidad. Cuéntame qué código de error aparece en la pantalla y en qué comuna estás, y vemos cómo lo resolvemos.

> *bot:* ¿En qué comuna te encuentras?

**3. cliente** `[scripted]` — Soy de ñuñoa
> *bot:* ¿Qué días y horarios te acomodan para la visita?

**4. cliente** `[scripted]` — Necesito solución de emergencia?
> *bot:* Un asesor revisará tu caso y te contactará a la brevedad.

**5. cliente** `[scripted]` — Si se puede?
**estado final:** `human` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G8 ✓
