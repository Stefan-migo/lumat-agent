# Conversaciones de la corrida `verdad-alcance-s3`

`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.
Estado final, gates y puntaje del juez al pie de cada caso.

## `real-vocabulario-impreciso` [simple]

**persona:** Propietaria que usa vocabulario coloquial e impreciso para describir una pieza.
**objetivo:** Saber si se puede revisar el quemador descrito sin asumir qué significa.

**1. cliente** `[scripted]` — Mira, tengo un quemador d ella cocina agripado y quería saber si ustedes arreglan eso
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Hola, gracias por escribir a Lumat. Trabajamos en servicios de gas, así que lo mejor es que un técnico autorizado SEC revise el quemador en el domicilio: ahí evalúa el equipo y, según lo que encuentre, el trabajo se presupone aparte. La visita técnica tiene un valor de $30.000. ¿En qué comuna estás y desde cuándo empezó a ponerse duro el quemador?

**estado final:** `bot` · **juez:** 3.00 · **hard fail:** False
**gates:** G1 ✓, G11 ✓, G4 ✓, G8 ✓
**dispersión entre repeticiones:** closure ±1, conversational ±2, grounding ±1, policy ±1, tone ±1

## `real-consulta-otros-equipos` [complejo]

**persona:** Cliente que pregunta si el técnico revisa aire acondicionado y bomba de calor de piscina además de los equipos que ya atiende.
**objetivo:** Saber si Lumat puede realizar la mantención de esos otros equipos.

**1. cliente** `[scripted]` — aire acondicionado ves igual o no?
> *bot:* Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso. Sí, la climatización está dentro de lo que trabajamos, incluido el aire acondicionado. El valor depende del equipo y de lo que necesites, así que se evalúa en una visita técnica de $30.000 y, según lo que se encuentre, el trabajo se presupuesta aparte. ¿Es un equipo split y qué necesitas: mantención, instalación o revisar alguna falla?

**2. cliente** `[scripted]` — y bomba de calor de piscina?
> *bot:* La bomba de calor de piscina no aparece en los servicios que tenemos listados, así que no puedo confirmarte que la trabajemos. Para no darte información equivocada, puedo dejar tu consulta para que un asesor la revise y te confirme si es algo que cubrimos. ¿Me dejas tu nombre y la comuna donde está la piscina?

**3. cliente** `[scripted]` — pq tengo que hacer la mantención de esa
> *bot:* Ojo con un punto: la bomba de calor de piscina no está en los servicios que tenemos listados, así que no puedo confirmarte que hagamos su mantención ni explicarte qué corresponde en ese equipo. ¿Te refieres a la mantención del aire acondicionado o a la de la bomba de calor? Según eso te orienta un asesor o coordinamos la visita técnica.

**estado final:** `bot` · **juez:** 2.58 · **hard fail:** False
**gates:** G1 ✓, G11 ✓, G8 ✓
**dispersión entre repeticiones:** conversational ±1, policy ±1, tone ±1
