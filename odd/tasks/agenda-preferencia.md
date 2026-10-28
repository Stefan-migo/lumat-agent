# ODD — agenda con preferencia (agenda-preferencia)

El flujo de reserva es determinista y ofrece siempre los 3 slots más tempranos de la ventana de 7 días,
sin leer el día ni la franja que el cliente pidió. Este documento cubre (a) la preferencia en la oferta,
(b) la colisión de vocabulario que manda a un humano, (c) la pregunta de día durante la selección, y la
regla de fin de semana que hoy la agenda y la KB contradicen.

Evidencia medida (2026-10-27/28): prod `conv 22` acertó el miércoles por casualidad; harness local
`conv 37` (pidió jueves) → handoff sin cita, `conv 38` (pidió sábado, luego viernes) → cita el miércoles,
`conv 39` (pidió "viernes en la tarde") → cita el miércoles. El jueves 29/10 estaba libre en la agenda.

## Specs

**S1 — La oferta respeta el día y la franja pedidos.**
Owner: *"como cliente le solicite mas dias. o dias especificos y no fue capaz de ayudarme."* (L1) ·
*"(a) + (b) + (c) + fin de semana, en slices"* (L4)
Cuando `captured_data["availability"]` resuelve a un día (fecha explícita o nombre de día de la semana)
o a una franja (mañana/tarde), **la primera oferta contiene únicamente slots de ese día y franja**. Si el
texto no resuelve, o dice *"cualquier dia"* / *"cuando puedan"*, la oferta queda sin restricción (comportamiento
actual, que ya cubre `complejo-agendar-calefont`). Los slots ofrecidos siguen viniendo de
`scheduling.open_slots_for_assignment`, con lead time y duración vigentes.

**S2 — Día sin cupo: avisar y ofrecer el día hábil más cercano.**
Owner: *"Ofrecer el día hábil más cercano y avisar"* (L2)
Si el día (o la franja) pedida no deja ningún slot reservable, la respuesta (1) dice que ese día no tiene
cupo, (2) ofrece el día local más cercano **posterior** con al menos un slot dentro de la ventana de 7 días,
y (3) nunca termina en un loop de aclaración ni en un handoff mientras exista algún slot en la ventana.
La misma ampliación aplica cuando la franja pedida no deja nada (p. ej. *"cualquier dia despues de las 6"*,
un turno real del corpus). Una preferencia que no deja cupo **nunca** produce un dead-end.

**S3 — Una respuesta a una oferta activa nunca se lee como reclamo.**
Owner: *"(a) + (b) + (c) + fin de semana, en slices"* (L4), causa (b).
Con `_booking_offer` o `_manage_offer` activo, un mensaje que sea número de opción, pedido de día/ventana, o
marcador de "más horarios" llega al nodo de la oferta y **no** dispara `handoff:complaint`. Evidencia:
`"No me sirve ninguno de los horarios que me ofreces"` es marcador en `booking.py:42` y frase de reclamo en
`handoff_gate.py:66`; `graph.py:166` hace ganar al gate, así que el universo de 30 slots quedó sin paginar y
Miguel fue derivado a un humano con el jueves libre. Un mensaje que es reclamo y **no** es respuesta a una
oferta sigue escalando igual que hoy.

**S4 — Preguntar por un día durante la selección se responde, no se castiga.**
Owner: causa (c) de L4 · evidencia: *"para el proximo jueves tienes algun tecnico disponible_"* y
*"tienes horarios disponibles para el viernes 30?"*
Un mensaje que nombra un día o pregunta disponibilidad mientras hay oferta activa produce una oferta
filtrada por ese día (o el fallback de S2). Nunca produce `booking_unclear`, y nunca consume el único
intento de aclaración que hoy lleva al handoff.

**S5 — Fin de semana: la agenda manda.**
Owner: *"Alinear la KB a la agenda (sábado sí)"* (L3)
El sábado sigue en `technician_weekly_schedule` y es agendable en línea; `docs/kb/lumat-cobertura-horarios.md:9`
se reescribe para decirlo (hoy dice que sábados, domingos y festivos se coordinan con un asesor). Domingo y
festivos siguen con asesor. El escenario `simple-horario-sabado` del corpus deja de declarar como fallo
prometer el sábado: pasa a ser fallo prometerlo sin consultar la agenda.

**S6 — Reagendar usa la misma ventana y un formato legible.**
Owner: L4, misma causa (a). Evidencia: `conv 38` pidió *"tienes horarios disponibles para el viernes 30?"* y
recibió `"1. 2026-10-28 10:00:00"` — día ignorado y formato crudo (`manage.py:124`).
El reagendado aplica S1/S2 sobre la preferencia declarada en el mensaje y lista los horarios con el mismo
formato que la reserva (`dd/mm/aaaa a las HH:MM`).

## Tasks

| ID | Spec | Qué | Ruta | Commit |
|---|---|---|---|---|
| T1 | S1 | Parser determinista de ventana (día / weekday / franja) en módulo propio + tests unitarios | inline | `02fc240c` |
| T2 | S1 | `scheduling.open_slots_for_assignment` acepta filtro de ventana + tests unit | inline | `bcf54727` |
| T3 | S1, S2, S4 | `booking._new_offer` lee `availability`; fallback al día más cercano con texto nuevo; `_more_slots` atiende día pedido | inline | `b236476b` |
| T4 | S3 | Precedencia: `handoff_gate` y `_after_handoff_gate` ceden ante oferta activa | inline | `c6f880d7` |
| T5 | S6 | `manage._new_reschedule_offer` con ventana y formato legible | writer | `a325d36c` |
| T6 | S5 | KB de horarios, corpus `simple-horario-sabado`, pin de la KB | inline | `0d0cc3a8`, `263bfd00`, `d03eb506`, `ec60fd19` |
| T7 | S1–S6 | Verificación de cierre: focused + `quick`, `full` al cerrar, y corpus real-model de los escenarios de agenda | inline | — |

### Slices de revisión

La feature se entrega como **siete PRs apilados a `main`**, cada uno ≤400 líneas:

| # | Rama | Líneas | Contenido |
|---|---|---|---|
| 1 | `odd/agenda-preferencia-1-window-parser` | 309 | parser de ventana + tests unitarios |
| 2 | `odd/agenda-preferencia-2-assignment-window` | 224 | filtro en `open_slots_for_assignment` + este documento |
| 3 | `odd/agenda-preferencia-3-booking-preference` | 243 | la oferta lee `availability` y cae hacia adelante |
| 4 | `odd/agenda-preferencia-4-offer-precedence` | 96 | precedencia del gate de reclamo |
| 5 | `odd/agenda-preferencia-5-reschedule-window` | 212 | reagendado con ventana + `slots_for_window` compartido |
| 6 | `odd/agenda-preferencia-6-kb-saturday` | 118 | KB del sábado + corpus + pins |
| 7 | `odd/agenda-preferencia-7-record` | 287 | cierre del registro + evidencia real |

Para armar el stack la historia se rehízo **una sola vez**: el commit original del primitivo (531 líneas) se
partió en parser (309) y filtro (224), y los slices se reordenaron para que cada rama sea un prefijo del
stack —el reagendado quedó antes del cambio de KB—. El árbol final es **byte-idéntico** al de la historia
previa: `git diff` contra ella da 0 líneas. Los sellos de las corridas de evaluación se tomaron sobre la
historia anterior, por eso `agenda-pref-4` cita `e90c5a3d`.

El trabajo de T5 volvió de un writer y se revisó antes de aceptarlo: la búsqueda con fallback hacia adelante
estaba duplicada (~30 líneas) y se extrajo a `booking.slots_for_window`, que ahora usan los dos caminos;
`window_label` se movió junto al parser en vez de importarse como privado; y un assert que concatenaba
`"202"` con `"-10-31"` (nunca podía coincidir con un ISO) se corrigió a `isodate not in reply`.

### Verificación (T7)

- `bash scripts/test.sh full` — primera corrida: **1 falla**, `tests/integration/test_kb.py:375`
  (`test_topic_routing_recovers_named_answers_below_global_cutoff`), porque el caso parametrizado
  esperaba el encabezado que S5 renombra. La expectativa correcta para la pregunta por el sábado pasó
  a ser el horario de agendamiento (`"lunes a sábado"`), no el encabezado viejo. Reintento: `EXIT=0`,
  sin `FAILED` ni `ERROR`.
- **Aviso de proceso**: la primera corrida reportó `exit 0` porque el comando terminaba en
  `| tail -40` sin `pipefail`, así que el código de salida era el de `tail`. Un job verde no prueba un
  suite verde; el re-run escribe a un log y reporta `EXIT=$?` real.
- Tests preexistentes modificados en toda la rama: exactamente dos, los dos porque la spec los cambia —
  `test_kb_hours_and_guarantees` (regla vieja de la KB) y `test_the_slot_vocabulary_is_closed` (el
  vocabulario cerrado gana `momento`). Ninguna aserción preexistente se borró ni se debilitó.
- Corpus: **no existía ningún escenario que pidiera un día concreto** — el defecto medido no tenía
  guarda. Se agregó `simple-dia-especifico` (tier simple, con hard_fail sobre ofrecer otro día sin
  avisar) y se actualizaron los dos pins de conteo (14 → 15 escenarios, simple 5 → 6).
- Entorno de la corrida real: KB sembrada (4 documentos, 22 chunks) y un técnico con weekly schedule
  lunes a sábado 09:00–18:00. `--reset` trunca `technician_availability` pero preserva el weekly
  schedule, así que `ensure_horizon` vuelve a materializar los bloques.

### Verificación con modelo real

Corrida `agenda-pref-4` — sello `e90c5a3d` (historia previa al stack; árbol idéntico a `ec60fd19`), corpus `1735bb01b90e`, KB `6fbd06e66d2a`, bot
`deepseek/deepseek-flash`, juez `deepseek-v4.1-flash`: **2 de 2 escenarios, ningún gate en falla**.

- `simple-dia-especifico`: el cliente pidió "puedo el jueves en la mañana" y la oferta fue
  **`29/10/2026` 09:00 / 09:30 / 10:00** — jueves por la mañana.
- **Diferencial contra el código previo**: el harness del main worktree (`conv 37`, código anterior a esta
  rama) recibió el mismo pedido ("el jueves por la mañana") y ofreció `28/10/2026` 09:00/09:30/10:00 —
  miércoles. Mismo pedido, mismo formato de respuesta, día distinto: eso es el defecto y su arreglo.
- `simple-horario-sabado`: el bot responde "agendamos de lunes a sábado, de 09:00 a 18:00", ya no
  "el sábado se coordina con un asesor".

Corrida `agenda-pref-2` (los cuatro escenarios de agenda, con juez): **2 de 4**; las dos fallas no son de
esta feature — ver "Hallazgos fuera de alcance". Antes de eso, dos corridas más no midieron nada: una sin
`DEEPSEEK_API_KEY` (el proveedor no estaba configurado) y una con el escenario propio trabado en el
consentimiento. Las dos se descartaron y se repitieron, no se reportaron.

## Log

- **L1** (owner, 2026-10-28): *"hey chat. necesito que revises en servidor solo lectura y revises la ultima
  conversacion que probre con el chatbot de produccion. despues revisa el main worktree hice un par de
  conversaciones para testear. y veo que hay un problema grande con la agenda. el chatbot esta cerrado a
  agendar solo cuando quiere. como cliente le solicite mas dias. o dias especificos y no fue capaz de
  ayudarme. puedes revisarlo?"*
- **L2** (owner, decisión): *"Ofrecer el día hábil más cercano y avisar"* — para el caso de día pedido sin cupo.
- **L3** (owner, decisión): *"Alinear la KB a la agenda (sábado sí)"* — la agenda manda sobre la KB.
- **L4** (owner, decisión de alcance): *"(a) + (b) + (c) + fin de semana, en slices"*.
- **E1** (evidencia, solo lectura): prod `conv 22` pidió "el proximo miercoles en la mañana" y recibió
  28/10 09:00/09:30/10:00 — acierta porque el 28/10 era el primer día de la ventana, no porque lea la
  preferencia. Cita confirmada 28/10 10:00.
- **E2**: harness `conv 37` availability="jueves por la mañana" → oferta 28/10; pregunta por el jueves →
  *"No pude identificar un único horario"*; *"No me sirve ninguno…"* → `conversation_events` 252
  `state_change bot->human: handoff:complaint`; sin cita (customer 36).
- **E3**: harness `conv 38` availability="un dia sabado" → respuesta "El sábado se coordina con un asesor";
  después confirmó **miércoles** 28/10 09:00 (appointment 14) y al pedir el viernes recibió otra vez el 28/10.
- **E4**: harness `conv 39` availability="viernes en la tarde" → confirmó **miércoles** 28/10 11:00
  (appointment 15).
- **E5**: repetición determinista de la colisión, sin DB: para `"No me sirve ninguno de los horarios que me
  ofreces"` → `_requests_more_slots=True` **y** `_COMPLAINT_PATTERN` matchea. Para
  `"para el proximo jueves tienes algun tecnico disponible_"` → ambos `False` y `_resolve=None`.
- **E6**: `technician_availability` del harness tiene bloque el 2026-10-29 (jueves) 09:00–18:00 local,
  `available=true`, sin citas: el pedido de Miguel era servible. `technician_weekly_schedule` del harness
  incluye weekday 7 (domingo); el de prod llega al 6 (sábado).

## Hallazgos fuera de alcance (no se tocan en esta feature)

Encontrados durante la verificación real; se reportan, no se arreglan acá porque son
otra conducta y merecen su propia feature.

- **El consentimiento acepta negativas compuestas y no afirmativas compuestas.**
  `app/chat/nodes/capture.py:122` exige que el mensaje completo sea exactamente
  `si`/`ok`/`claro`/`confirmo`/`acepto`, mientras que `_NO_WORDS` (línea 126) ya incluye
  `no autorizo`, `no quiero`, `no acepto`, `no gracias`. Resultado: "si, autorizo" no se
  entiende y el bot vuelve a preguntar (`capture_consent_unclear`), pero "no autorizo" sí.
  Evidencia en tres conversaciones independientes: harness `conv 37` ("sio"), `conv 38`
  ("y parsi") y el escenario `simple-dia-especifico` en la corrida `agenda-pref-2`.
- **`complejo-agendar-calefont` deriva antes de la agenda.** Turno 3: el bot pregunta por la
  falla y la respuesta ("el calefont es junkers, tiro natural") no la contesta, así que
  escala con `campo_sin_respuesta`. Es captura y clasificación, no agenda.
- **`complejo-no-quiere-email` tiene la expectativa vieja.** Declara 4 turnos y espera
  derivación, pero desde que el email es omitible el flujo avanza y necesita más turnos
  para llegar a la oferta. Ya estaba registrado como falla de expectativa del corpus el
  2026-10-27; no es una regresión de este cambio.

