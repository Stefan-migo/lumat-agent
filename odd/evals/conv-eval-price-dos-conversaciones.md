# Conversaciones de la corrida `price-dos`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `complejo-dos-temas` [complejo]

**persona:** Cliente que primero pregunta un precio y después, sobre ese mismo servicio, pregunta por la garantía. No repite el nombre del servicio.
**objetivo:** Saber el precio del lavado de red y después cuánta garantía tiene.

**1. cliente** `[scripted]` — hola, cuanto cuesta el lavado de red?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Hola, el lavado de red de calefacción tiene un valor de $30.000. Es una limpieza profunda del circuito que elimina lodos, óxido y sedimentos, y suele tomar entre 3 y 6 horas según el tamaño de la red. ¿Es para una casa o un edificio?

**2. cliente** `[scripted]` — y eso cuanto de garantia tiene?
> *bot:* El lavado de red tiene garantía de 6 meses, y cubre la mano de obra del trabajo realizado, no los repuestos. ¿Te sirve que coordinemos una visita para revisar tu red?

**estado final:** `bot` · **juez:** 0.00 · **hard fail:** False
**gates:** G1 ✗ (state=bot, esperado uno de: human), G10 ✗ (ninguna derivación esperada (esperaba persona); se registró: ninguna), G6 ✓, G8 ✓, G9 ✓
