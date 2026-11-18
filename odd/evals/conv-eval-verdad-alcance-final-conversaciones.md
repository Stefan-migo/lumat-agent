# Conversaciones de la corrida `verdad-alcance-final`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `real-vocabulario-impreciso` [simple]

**persona:** Propietaria que usa vocabulario coloquial e impreciso para describir una pieza.
**objetivo:** Saber si se puede revisar el quemador descrito sin asumir qué significa.

**1. cliente** `[scripted]` — Mira, tengo un quemador d ella cocina agripado y quería saber si ustedes arreglan eso
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Hola, gracias por escribir a Lumat. El quemador agripado no aparece como trabajo con valor fijado en nuestro catálogo, así que no quiero darte una respuesta al azar: lo que sí podemos hacer es coordinar una visita técnica ($30.000), donde el técnico revisa el quemador en el domicilio y, según lo que encuentre, el arreglo se presupuesta aparte. ¿En qué comuna está la cocina?

**estado final:** `bot` · **juez:** 3.67 · **hard fail:** False
**gates:** G1 ✓, G11 ✓, G4 ✓, G8 ✓

## `real-consulta-otros-equipos` [complejo]

**persona:** Cliente que pregunta si el técnico revisa aire acondicionado y bomba de calor de piscina además de los equipos que ya atiende.
**objetivo:** Saber si Lumat puede realizar la mantención de esos otros equipos.

**1. cliente** `[scripted]` — aire acondicionado ves igual o no?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Sí, la climatización está dentro de nuestros servicios. El trabajo específico en el equipo lo evalúa un técnico en el domicilio y, según lo que encuentre, el presupuesto se calcula aparte; la visita técnica tiene un valor de $30.000. ¿Qué equipo tienes y qué está pasando con él?

**2. cliente** `[scripted]` — y bomba de calor de piscina?
> *bot:* Sobre la bomba de calor de piscina prefiero no darte una respuesta equivocada: no tengo ese trabajo en nuestro catálogo publicado, que cubre calefacción, gas, calderas, calefont, climatización y gasfitería de domicilio. Si quieres, lo consulto con un asesor para confirmar si lo cubrimos, y mientras tanto te ayudo con el aire acondicionado. ¿Qué le pasa al equipo?

**3. cliente** `[scripted]` — pq tengo que hacer la mantención de esa
> *bot:* No te dije que fuera obligatorio: la mantención de una bomba de calor de piscina la pide normalmente el fabricante para mantener la garantía, y eso lo define su manual, no nosotros. Como ese equipo no está en nuestro catálogo publicado, prefiero confirmarte con un asesor si lo cubrimos. ¿Te sirve que lo consulte y te respondo por acá?

**estado final:** `bot` · **juez:** 2.58 · **hard fail:** False
**gates:** G1 ✓, G11 ✓, G8 ✓
**dispersión entre repeticiones:** policy ±1
