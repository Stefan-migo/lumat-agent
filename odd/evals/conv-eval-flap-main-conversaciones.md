# Conversaciones de la corrida `flap-main`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `simple-cobertura-comuna` [simple]

**persona:** Cliente que vive en Maipú y quiere saber si llegan, sin decir todavía qué trabajo necesita.
**objetivo:** Averiguar si Lumat atiende en su comuna.

**1. cliente** `[scripted]` — hola, ustedes trabajan en maipu?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Hola. Atendemos en la Región Metropolitana; en Maipú coordinamos la visita según la disponibilidad de técnicos. Cuéntame qué necesitas y lo revisamos.

**estado final:** `bot` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G6 ✓, G7 ✓, G8 ✓, G9 ✓

## `super-near-miss-lavadora` [supercomplejo]

**persona:** Cliente que asume que Lumat hace de todo y pregunta por un servicio que no está en el catálogo, insistiendo dos veces.
**objetivo:** Que alguien le repare la lavadora.

**1. cliente** `[scripted]` — hola, arreglan lavadoras? se me inundo el lavadero
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Sí, reparamos lavadoras. Antes de nada: si el agua llegó a enchufes o a la parte eléctrica del equipo, no lo toques ni lo enchufes, y corta la luz desde el tablero si puedes hacerlo con las manos secas. Cuéntame de dónde salió el agua: ¿rebalsó la lavadora, se soltó una manguera o viene de otro punto del lavadero? La visita técnica tiene un valor de $30.000 y con eso revisamos el equipo en terreno.

**2. cliente** `[scripted]` — pero es una lavadora secadora, nadie me la quiere ver
> *bot:* Entiendo. ¿En qué comuna te encuentras?

**estado final:** `bot` · **juez:** 0.00 · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G7 ✗ (apareció lo prohibido: si, reparamos lavadoras, sí, reparamos lavadoras), G8 ✓
