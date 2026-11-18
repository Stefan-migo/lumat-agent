# Conversaciones de la corrida `verdad-alcance-s1s2`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `real-vocabulario-impreciso` [simple]

**persona:** Propietaria que usa vocabulario coloquial e impreciso para describir una pieza.
**objetivo:** Saber si se puede revisar el quemador descrito sin asumir qué significa.

**1. cliente** `[scripted]` — Mira, tengo un quemador d ella cocina agripado y quería saber si ustedes arreglan eso
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Entiendo, un quemador agripado es incómodo. Te cuento con franqueza: la reparación de quemadores de cocina no está entre los servicios con tarifa publicada, así que no puedo confirmarte que lo hagamos ni darte un valor. Lo que sí puedo hacer es que un asesor revise el caso y te presupueste la visita. Para orientarlo mejor, ¿el problema es que la perilla no gira, o que el quemador no enciende?

**estado final:** `bot` · **juez:** 2.83 · **hard fail:** False
**gates:** G1 ✓, G11 ✓, G4 ✓, G8 ✓
**dispersión entre repeticiones:** escalation ±1, grounding ±1, policy ±2

## `real-consulta-otros-equipos` [complejo]

**persona:** Cliente que pregunta si el técnico revisa aire acondicionado y bomba de calor de piscina además de los equipos que ya atiende.
**objetivo:** Saber si Lumat puede realizar la mantención de esos otros equipos.

**1. cliente** `[scripted]` — aire acondicionado ves igual o no?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. En climatización sí trabajamos, pero el aire acondicionado no aparece entre los servicios con tarifa publicada, así que no quiero darte un valor inventado. Cuéntame qué equipo tienes y qué necesita (¿mantención, instalación, una falla?), y con eso coordino que un asesor lo revise y te presupueste.

**2. cliente** `[scripted]` — y bomba de calor de piscina?
> *bot:* La bomba de calor de piscina tampoco está entre nuestros servicios, así que no podría tomarla. Lo que sí cubrimos es calefont, caldera, lavado de red y visitas técnicas de gasfitería y climatización. Si lo que necesitas es algo de eso, dime y lo coordinamos.

**3. cliente** `[scripted]` — pq tengo que hacer la mantención de esa
> *bot:* Creo que no me expliqué bien: no te estoy pidiendo que le hagas mantención a la bomba de calor ni al aire acondicionado. Solo te decía que esos dos equipos no están entre los servicios que hacemos, así que no puedo presupuestarte ni recomendarte su mantención. Si quieres, un asesor puede orientarte sobre un servicio de nuestro catálogo (calefont, caldera, lavado de red o visita técnica de gasfitería y climatización). ¿Hay algo de eso que necesites revisar?

**estado final:** `bot` · **juez:** 2.00 · **hard fail:** False
**gates:** G1 ✓, G11 ✓, G8 ✓
**dispersión entre repeticiones:** escalation ±1, grounding ±3, policy ±2
