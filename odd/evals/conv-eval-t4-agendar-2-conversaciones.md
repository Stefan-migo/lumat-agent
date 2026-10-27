# Conversaciones de la corrida `t4-agendar-2`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `complejo-agendar-calefont` [complejo]

**persona:** Cliente de Ñuñoa que quiere agendar la mantención de su calefont y da los datos en desorden: primero la comuna, después el nombre, y el email recién al final. Mensajes cortos, varias ideas por mensaje.
**objetivo:** Agendar una mantención de calefont en Ñuñoa y quedar con la visita coordinada.

**1. cliente** `[scripted]` — hola, necesito mantener mi calefont, vivo en ñuñoa
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Hola, qué bueno que nos escribes. La mantención de calefont tiene un valor de $50.000 y en Ñuñoa atendemos normalmente. ¿Qué marca es tu calefont y hace cuánto tiempo no le haces mantención?

**2. cliente** `[scripted]` — me llamo carolina, atiendan cuando puedan
> *bot:* Hola Carolina, gusto en conocerte. La mantención de calefont tiene un valor de $50.000 y en Ñuñoa atendemos normalmente. Para orientarte mejor: ¿qué marca es tu calefont y hace cuánto tiempo no le haces mantención?

**3. cliente** `[scripted]` — el calefont es junkers, tiro natural
> *bot:* Entiendo, es un problema con tu calefont. Gracias Carolina. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**4. cliente** `[scripted]` — si, me sirve cualquier dia en la mañana
> *bot:* Entiendo, es un problema con tu calefont. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**5. cliente** `[scripted]` — carolina.p@gmail.com
> *bot:* Veo que esa pregunta no te acomoda. Un asesor de Lumat te contacta para terminar de coordinar los datos.

**estado final:** `human` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G6 ✓, G8 ✓
