# agenda-horarios — repetición en las preguntas de captura, hora pedida en la agenda, formato de cupos

Rama `odd/agenda-horarios`, worktree `../lumat-agent-odd-agenda-horarios`, base `main 0318883c`.
Origen: conversación #52 del harness (`+56901000078`), revisada por el owner el 2026-11-04.

## Specs

- **S1 — Las preguntas de captura no repiten lo ya dicho.** Ninguna pregunta de captura
  (`capture_question`, `capture_consent*`) vuelve a enunciar en el mismo turno el nombre del
  cliente, el equipo, la comuna o la disponibilidad que ya se dijeron en turnos anteriores.
  Cita del owner: *"repite el Ramiro, para gestionar la visita del calefont en Huechuraba el
  viernes después del mediodía. casi en cada turno. eso es redundante y hasta molesto."*
- **S2 — La redacción natural se mantiene.** `chat.conduct.redaccion = "llm"` sigue siendo el
  modo; el arreglo es que el rewrite no repita hechos, no apagar el modelo. Un borrador que
  repita un hecho ya usado se rechaza y el turno cae a la plantilla (el `fallback` que ya
  existe en `app/chat/phrasing.py`).
- **S3 — Una hora pedida se interpreta.** "podria ser mas tarde cerca de las 17 hrs?" y
  "podria ser mas tarde despues de las 17 hrs?" piden cupos **a partir de las 17:00** del día
  pedido. Cita del owner: *"el cliente le solicita despues del medio dia. cuando el chatbot le
  da las opciones, le consulta por algo mas tarde. le especifica un horario y no es capaz de
  dar opciones en el horario que solicita el cliente."*
- **S4 — Sin cupo a esa hora, se ofrece el día siguiente y se dice por qué.** El día pedido
  manda: si no queda cupo a partir de la hora pedida, la respuesta dice que ese día ya no hay
  a esa hora y ofrece el siguiente día disponible. No se cambia de día en silencio.
- **S5 — Formato de cada cupo: con nombre del día.** `Viernes 06/11 a las 13:00`. Aplica al
  texto de la oferta y a cualquier lugar donde el cliente vea un cupo o una visita.
- **S6 — Nunca derivar a humano por no entender una hora.** `is_offer_answer` y el gate de
  handoff reconocen una hora pedida (`despues de las X`, `a las X`, `mas tarde`, `mas
  temprano`) como respuesta legítima a una oferta abierta. Cita: la conversación #52 terminó en
  `state=human` en el segundo intento.

## Tasks

| ID | Qué | Specs | Ruta | Commit |
|---|---|---|---|---|
| T1 | `phrasing`: hechos sólo nuevos en el rewrite + rechazo de borradores que repiten | S1, S2 | inline | `fix(chat): no repetir hechos ya dichos en las preguntas de captura` |
| T2 | `slot_window` gana piso de hora; `booking` filtra por hora, ofrece el día siguiente y reconoce la hora como respuesta | S3, S4, S6 | worker | `feat(chat): interpretar la hora pedida en la oferta de horarios` |
| T3 | Formato con nombre del día en `booking`, `manage` y `state`, y `_resolve` acepta el formato nuevo | S5 | inline | `feat(chat): mostrar el día de la semana en los horarios ofrecidos` |
| T4 | Verificación: tests focalizados, `bash scripts/test.sh quick`, y replay en el harness | todas | parent | — |

## Log

- **L1 (pedido original, verbatim):**

  > ok revisa este caso. hay dos cosas que me quedan dando vueltas:
  >
  > - lo repetitivo de esto:  Ramiro, para coordinar la visita por el calefont en Huechuraba, ¿qué días y horarios te acomodan?/ Luego dice  Ramiro, para coordinar el calefont en Huechuraba el viernes después del mediodía, ¿cuál es tu correo electrónico? luego continua: Ramiro, para coordinar el calefont en Huechuraba el viernes después del mediodía, ¿cuál es tu dirección?, y sigue una vez mas  Ramiro, para gestionar la visita del calefont en Huechuraba el viernes después del mediodía, necesitamos guardar tus datos. ¿Nos das tu autorización? (Responde sí o no)
  >
  > o sea repite el  Ramiro, para gestionar la visita del calefont en Huechuraba el viernes después del mediodía. casi en cada turno. eso es redundante y hasta molesto.
  >
  > - luego el segundo error que encuentro es que el chatbot no fue capaz de dar mas opciones de horarios. el cliente le solicita despues del medio dia. cuando el chatbot le da las opciones, le consulta por algo mas tarde. le especifica un horario y no es capaz de dar opciones en el horario que solicita el cliente.
  >
  > aqui tambien el formato de la agenda. podira ser con nombre del dia? por ejemplo en este caso seria Viernes 06, Noviembre a las xx:xx. ?

- **L2 (decisiones del owner, 2026-11-04):** S1/S2 → mantener `redaccion: llm` y prohibir la
  repetición (no bajar a plantilla). S3/S4 → interpretar la hora y, si ese día no hay cupo a esa
  hora, ofrecer el día siguiente **diciendo por qué**. S5 → formato `Viernes 06/11 a las 13:00`.
  Y la worktree/branch para las tres unidades.

- **L3 (diagnóstico, evidencia):** la repetición NO es una plantilla: la escribe el modelo porque
  `phrasing.phrase` le pasa `phrase_facts(captured, fields)` con todos los hechos y una instrucción
  abierta. `chat.conduct` local y de prod tienen `"redaccion": "llm"`. La hora pedida no se
  interpreta porque `SlotWindow` es sólo `(day, franja)` con `AFTERNOON = 13:00–18:00`, y "después
  de las 17" no matchea `_AFTERNOON` ni `_MORE_SLOTS_MARKERS`. El cupo de las 17:00 **sí existía**:
  el 2026-11-06 los técnicos `mgonzalez` y `jperez` tienen ventana 12:00–21:00 UTC = 09:00–18:00
  hora Chile, y la oferta sólo mostró los primeros 3 del universo (`PAGE_SIZE = 3`).
