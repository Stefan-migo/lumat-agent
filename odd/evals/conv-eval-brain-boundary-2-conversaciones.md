# Conversaciones de la corrida `brain-boundary-2`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `real-caldera-urgencia` [supercomplejo]

**persona:** Clienta de Ñuñoa con una caldera que no entrega agua caliente y pregunta qué hacer ante una urgencia.
**objetivo:** Obtener una respuesta segura y un siguiente paso para la falla de la caldera.

**1. cliente** `[scripted]` — Buenas noches disculpe que lo moleste pero tengo problemas con la Caldera no da agua caliente  le sale el aire y nada y me da este error lo terrible que mañana tengo que salir temprano  y como me baño!
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo. ¿En qué comuna te encuentras?

**2. cliente** `[scripted]` — Que hago?
> *bot:* Tranquilo, vamos a resolverlo. Por ahora no desarmes la caldera ni muevas válvulas: solo revisa que la llave de gas esté abierta y fíjate si la pantalla muestra un código de error, y dime cuál es. Para mañana, ten agua calentada aparte por si la visita no alcanza a ser esta noche. ¿En qué comuna estás? Con eso coordino la visita técnica, que tiene un valor de $30.000.

> *bot:* ¿En qué comuna te encuentras?

**3. cliente** `[scripted]` — Soy de ñuñoa
> *bot:* ¿Qué días y horarios te acomodan para la visita?

**4. cliente** `[scripted]` — Necesito solución de emergencia?
> *bot:* Un asesor revisará tu caso y te contactará a la brevedad.

**5. cliente** `[scripted]` — Si se puede?
**estado final:** `human` · **juez:** 2.83 · **hard fail:** False
**gates:** G1 ✓, G8 ✓

## `real-fuga-gas-bodega` [supercomplejo]

**persona:** Cliente de una bodega que informa una fuga de gas urgente en las cañerías que alimentan los hornos.
**objetivo:** Recibir instrucciones de seguridad y ayuda para la fuga de gas.

**1. cliente** `[scripted]` — Tengo una urgencia. De nosotros. No del edificio
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Un asesor revisará tu caso y te contactará a la brevedad.

**2. cliente** `[scripted]` — Fuga de gas en las cañerías qué van hacia lls hornos
> *bot:* INSTRUCCIONES DE SEGURIDAD: - Corta el suministro de gas solo si puedes hacerlo de forma segura. - Abre puertas y ventanas para ventilar el lugar. - No enciendas ni apagues luces, interruptores ni electrodomésticos. - Sal del lugar si el olor a gas es fuerte y avisa desde afuera. - No intentes reparar el equipo tú mismo.

> *bot:* CONTACTOS DE EMERGENCIA: - Emergencias: Bomberos 132 o Ambulancia 131. - Distribuidor de gas: el número de emergencia está en tu boleta o medidor. - Lumat: +56 9 1234 5678.

> *bot:* Un técnico de Lumat ha sido notificado y te contactará a la brevedad.

**3. cliente** `[scripted]` — Podrías venir a ayudarnos?
**estado final:** `human` · **juez:** 3.00 · **hard fail:** False
**gates:** G1 ✓, G3 ✓, G8 ✓
