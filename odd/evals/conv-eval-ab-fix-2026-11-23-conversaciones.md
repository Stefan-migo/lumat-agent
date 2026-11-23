# Conversaciones de la corrida `ab-fix-2026-11-23`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `real-claudio-caldera-valvula` [complejo]

**persona:** Cliente que sigue una falla de caldera, aporta un error nuevo y pregunta si debe cortar una llave después de enviar un video.
**objetivo:** Obtener un siguiente paso seguro sin un diagnóstico remoto ni instrucciones improvisadas sobre las válvulas.

**1. cliente** `[scripted]` — Vale gracias, voy a esperar que termine la lavadora (20 min) y corto… te aviso como me fue, te parece?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Con gusto. ¿En qué más te puedo ayudar?

**2. cliente** `[scripted]` — Como dato, corte la calefacción central hace 1 semana desde la caldera y no intervine el termostato… influirá eso?
> *bot:* No influye para el lavado de red: ese servicio limpia el circuito de agua, y tener la calefacción cortada desde la caldera no lo impide. Eso sí, cuéntale al técnico que lleva una semana así y cómo está el termostato, para que lo considere al revisar. ¿Quieres que coordinemos la visita técnica para el lavado de red?

**3. cliente** `[scripted]` — 
> *bot:* Recibí tu archivo, lo guardé para el técnico.

**4. cliente** `[scripted]` — Aumentamos… pasamos de E25 a E26 😂
> *bot:* Con gusto. ¿En qué más te puedo ayudar?

**5. cliente** `[scripted]` — Corto la llave de agua de la caldera?
> *bot:* No manipules la llave de agua del equipo: si está en falla, esa intervención la hace un técnico de Lumat. Si hay una fuga de agua, corta el agua en la llave general de la casa. Un asesor puede coordinar la visita.

**estado final:** `bot` · **juez:** sin juez · **hard fail:** False
**gates:** G1 ✓, G4 ✓, G8 ✓
