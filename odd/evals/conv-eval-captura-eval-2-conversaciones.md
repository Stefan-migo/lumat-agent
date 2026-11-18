# Conversaciones de la corrida `captura-eval-2`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `real-maria-jesus-evaluacion-caldera` [supercomplejo]

**persona:** Clienta que pide una segunda evaluación porque la presión del sistema de calefacción sigue bajando tras una intervención anterior.
**objetivo:** Obtener una evaluación y un siguiente paso sin diagnóstico remoto ni maniobras sobre la caldera.

**1. cliente** `[scripted]` — La persona que me hizo la mantención el año pasado me dijo lo de la microfuga. De hecho el año pasado  le pasó liquido sellante y me dijo qie con eso andaria bien pero nunca quedó bien.
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo, y es frustrante que haya quedado así: el sellante puede tapar por un tiempo, pero si la microfuga sigue apareciendo, conviene revisar el punto exacto con un técnico. Para orientarte mejor: ¿dónde estás viendo la fuga ahora, en el calefont o en la red de gas, y desde cuándo volvió a aparecer? Con eso coordinamos una revisión del caso, considerando que viene de la mantención del año pasado.

**2. cliente** `[scripted]` — Esto fue el año pasado al final de la temporada, el sistema nunca se estabilizó completamente y me dijo que probablemente habria que hacer de nuevo el procedimiento. Por eso me gustaría tener una nueva evaluación y cotización
> *bot:* Entiendo: si el sellante no estabilizó el sistema, corresponde una evaluación nueva del punto y una cotización aparte del procedimiento. La visita técnica tiene un valor de $30.000. ¿Qué día y horario te acomodan para coordinar la revisión? Con eso vemos la disponibilidad de técnicos y dejamos la visita registrada.

**3. cliente** `[scripted]` — Una semana...10 dias
> *bot:* Entiendo, quieres hacer mantención de tu equipo. ¿Qué equipo es? Si sabes la marca y el modelo, mejor.

**4. cliente** `[scripted]` — El problema es que no se como rellenar  tampoco, ahora esta en rojo otra vez 🥺
> *bot:* Entiendo, quieres hacer mantención de caldera. ¿En qué comuna te encuentras?

**5. cliente** `[scripted]` — Cuando recien se enciende vuelve a subir y luego baja
> *bot:* Entiendo, quieres una nueva evaluación con cotización. ¿En qué comuna te encuentras?

**estado final:** `bot` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G6 ✓, G8 ✓
