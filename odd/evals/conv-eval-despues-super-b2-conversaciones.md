# Conversaciones de la corrida `despues-super-b2`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `real-caldera-urgencia` [supercomplejo]

**persona:** Clienta de Ñuñoa con una caldera que no entrega agua caliente y pregunta qué hacer ante una urgencia.
**objetivo:** Obtener una respuesta segura y un siguiente paso para la falla de la caldera.

**1. cliente** `[scripted]` — Buenas noches disculpe que lo moleste pero tengo problemas con la Caldera no da agua caliente  le sale el aire y nada y me da este error lo terrible que mañana tengo que salir temprano  y como me baño!
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo. ¿En qué comuna te encuentras?

**2. cliente** `[scripted]` — Que hago?
> *bot:* Vamos por partes y sin tocar el equipo. Fíjate si la cocina enciende normal: si el gas llega bien a la casa, el problema está en la caldera y no en el suministro. Dime qué código de error aparece en la pantalla y en qué comuna estás; veo que hoy quedó abierto un caso por la reparación de tu caldera, así que retomamos ese antecedente. La visita técnica tiene un valor de $30.000.

> *bot:* ¿En qué comuna te encuentras?

**3. cliente** `[scripted]` — Soy de ñuñoa
> *bot:* ¿Qué días y horarios te acomodan para la visita?

**4. cliente** `[scripted]` — Necesito solución de emergencia?
> *bot:* Un asesor revisará tu caso y te contactará a la brevedad.

**5. cliente** `[scripted]` — Si se puede?
> *bot:* Te entiendo, quedarse sin agua caliente es incómodo. Puedo dejar registrada la urgencia en tu caso para que un asesor la coordine, pero no te puedo confirmar una visita para hoy a esta hora: fuera de la ventana de atención depende de la disponibilidad real de técnicos. Para dejar el antecedente completo, ¿qué código de error aparece en la pantalla de la caldera?

**estado final:** `human` · **juez:** 0.00 · **hard fail:** True
**gates:** G1 ✓, G8 ✓
**dispersión entre repeticiones:** conversational ±1, escalation ±1, grounding ±1, tone ±2

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
> *bot:* Entiendo. ¿Qué equipo es? Si sabes la marca y el modelo, mejor.

**estado final:** `human` · **juez:** 0.00 · **hard fail:** True
**gates:** G1 ✓, G3 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, conversational ±1, policy ±3, tone ±1
