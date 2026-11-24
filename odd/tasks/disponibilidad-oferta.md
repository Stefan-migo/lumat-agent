# ODD — disponibilidad-oferta

Que la pregunta «¿tienen hora disponible?» se conteste con la agenda real de los técnicos, sin
inventar horarios y sin cerrar el chat por horario.

- Branch: `odd/disponibilidad-oferta` · Base: `14b297daa` (main) · Worktree: `../lumat-agent-odd-disponibilidad-oferta`

## Specs

### S1 · El chat responde siempre

> "la idea de la gente de lumat es que el chatbot pueda stender 24/7, pero que solo oueda agendar con
> los horarios de los tecnicos"

El bot no cierra por horario: `hours.schedule` expresa la ventana de atención del *chat* (hoy 24/7 en
producción) y `hours.closure_enabled` queda en `false`, así que el mensaje `out_of_hours` no se manda.

### S2 · Solo se agenda con la disponibilidad de los técnicos

> "el chatbot esta disponible para responder siempre pero solo agenda segun los horarios de los
> tecnicos"

Ningún horario ofrecido al cliente cae fuera de la disponibilidad cargada de un técnico, ni promete un
slot que `scheduling.book` vaya a rechazar. Ya lo cumplen `scheduling.open_slots_for_assignment` y
`scheduling.book`; el corte no las relaja.

### S3 · La pregunta por días y horas se contesta con la agenda

Una pregunta directa por disponibilidad («¿tienen hora disponible esta semana?») recibe días y horas
reales de la agenda, no una política. Forma exacta de la respuesta: **decisión del owner, abierta en
L2** — el corte no la inventa.

### S4 · El arnés mide con agenda

La base de evaluación tiene cero técnicos y cero bloques de disponibilidad, así que una respuesta
basada en agenda no puede existir ahí. Sembrar técnicos con horario es el equivalente de lo que
`hours.schedule` necesitó en el corte anterior: sin datos, el escenario mide el vacío.

## Tasks

| ID | Task | Spec | Route | Commit |
| --- | --- | --- | --- | --- |
| T1 | Decidir la forma de la respuesta y el seam (oferta informativa vs entrar al flujo de agendamiento) | S3 | decisión del owner | — |
| T2 | Implementar la respuesta desde `open_slots_for_assignment` sin crear oferta comprometida | S1, S2, S3 | inline | — |
| T3 | Tests RED/GREEN de la respuesta y del no-cierre por horario | S1-S3 | inline | — |
| T4 | Sembrar técnicos y disponibilidad en el arnés, y sellarlo | S4 | inline | — |
| T5 | Correr `real-disponibilidad-dias` y sus vecinos de agenda | S3, S4 | corrida | — |
| T6 | Re-baseline citable del corpus | S3, S4 | corrida | — |

## Log

### L1 — pedido del owner (2026-11-24)

> "pk respecto a los horarios. la idea de la gente de lumat es que el chatbot pueda stender 24/7, pero
> que solo oueda agendar con los horarios de los tecnicos

o sea, el chatbot esta disponible para responder siempre pero solo agenda segun los horarios de los
tecnicos. esta bien eso?"

> "si arranca con eso. luego continuamos con familia 4"

Verificado en ese intercambio: producción tiene 3 técnicos, 82 bloques de disponibilidad y 23 visitas;
`hours.schedule` es todos los días `00:00-23:59` y `hours.closure_enabled` es `false`. El camino de
*pedido* ya se acota con la agenda (`booking.py:146` → `open_slots_for_assignment`, `scheduling.book`,
`booking.lead_minutes` = 120). Lo que no existía era la respuesta a la pregunta por disponibilidad:
`configured_answers.hours_reply` contesta con la política.

### L2 — la forma de la respuesta: horarios reales, sin oferta comprometida (2026-11-24)

> Decisión del owner ante la pregunta: **«Horarios reales (día y hora) + invitar a reservar»** — texto
> aprobado en la vista previa: «Esta semana tengo jueves 27 a las 10:00 y sábado 29 a las 11:00. Si
> quieres, te tomo los datos y te la reservo.»

Se descartaron las otras dos: **solo días** (dice «jueves» aunque no queden horas útiles del jueves, y
el cliente no sabe a qué hora) y **dejarlo como está** (el cliente pregunta disponibilidad y recibe una
política; el escenario se queda en 1.67).

Tres precisiones medidas que el texto aprobado no podía decir:

1. **El horizonte son 7 días desde ahora, no la semana calendario.** `open_slots_for_assignment` usa
   `days=7` y lo extiende si el cliente nombró un día. La clave dice «Tengo estos horarios disponibles:»
   y no «Esta semana tengo», porque un viernes incluiría la semana siguiente.
2. **Es informativa, no una oferta.** Nada se persiste en `captured_data["_booking_offer"]`: el cliente
   que elige un día entra al capture normal y la oferta real se congela al final, como hoy. Reusar
   `booking_offer` habría dejado un callejón sin salida — dice «responde con el número» y no habría
   oferta guardada que resolver.
3. **Sin horarios, no se inventa nada**: si la agenda no devuelve slots, la respuesta cae en la política
   que ya existe (`hours_reply`). No hace falta una segunda clave de mensaje.

Costo asumido: **una clave nueva en `reply.texts`** (`availability_preview`), que toca el catálogo, el
editor del panel, los fixtures y el test que fija las claves. Se elige `reply.texts` y no `messages.*`
porque el cuerpo Pydantic y el tipo TS de `reply.texts` son mapas abiertos: la clave nueva entra sin
campo nuevo en la API.
