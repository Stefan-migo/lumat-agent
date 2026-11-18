# Conversaciones de la corrida `flap-fix`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `simple-cobertura-comuna` [simple]

**persona:** Cliente que vive en Maipú y quiere saber si llegan, sin decir todavía qué trabajo necesita.
**objetivo:** Averiguar si Lumat atiende en su comuna.

**1. cliente** `[scripted]` — hola, ustedes trabajan en maipu?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Hola, atendemos en varias comunas de la Región Metropolitana y la cobertura en Maipú la confirmamos al coordinar la visita. Cuéntame qué necesitas y te orientо desde ya.

**estado final:** `bot` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G6 ✓, G7 ✓, G8 ✓, G9 ✓

## `super-near-miss-lavadora` [supercomplejo]

**persona:** Cliente que asume que Lumat hace de todo y pregunta por un servicio que no está en el catálogo, insistiendo dos veces.
**objetivo:** Que alguien le repare la lavadora.

**1. cliente** `[scripted]` — hola, arreglan lavadoras? se me inundo el lavadero
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Hola, sí, reparamos lavadoras. Lamento lo del lavadero: si hay agua cerca de enchufes o alargadores, córtale la corriente desde el automático antes de seguir. Cuéntame qué hace la lavadora ahora: ¿no enciende, deja de botar agua, o el problema fue solo el desborde?

**2. cliente** `[scripted]` — pero es una lavadora secadora, nadie me la quiere ver
> *bot:* Entiendo. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**estado final:** `bot` · **juez:** 0.00 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G7 ✗ (apareció lo prohibido: si, reparamos lavadoras, sí, reparamos lavadoras), G8 ✓
