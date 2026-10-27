# Conversaciones de la corrida `t4-agendar-3`

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
> *bot:* Gracias, Carolina. Un Junkers a tiro natural se puede mantener sin problema; la mantención incluye limpieza de componentes accesibles, revisión de quemadores, encendido y evacuación de gases. ¿Hace cuánto tiempo no le haces mantención y en qué horario te acomoda que vaya el técnico?

**4. cliente** `[scripted]` — si, me sirve cualquier dia en la mañana
> *bot:* Gracias Carolina. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**5. cliente** `[scripted]` — carolina.p@gmail.com
> *bot:* Gracias, Carolina. Anoto tu correo para el contacto. Para cerrar la visita: ¿me confirmas que el calefont está funcionando bien y solo quieres la mantención preventiva, o hay algún problema como que no encienda o no caliente?

> *bot:* Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**estado final:** `bot` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G6 ✓, G8 ✓
