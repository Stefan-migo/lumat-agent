# ODD — la configuración como fuente, no la prosa (agenda-config-fuente)

Worktree: `/home/stefan/repos/lumat-agent-odd-agenda-config-fuente` · rama `odd/agenda-config-fuente` · base `a443588c`
Cierra lo que `odd/kb-drift` dejó enumerado: el motor de agenda no conoce la ventana comercial (ofrece domingo aunque la KB prometa un asesor), y la KB enuncia valores que la configuración ya posee (comunas, horario, duraciones). Dos slices: A = motor, B = respuestas desde configuración.

## Specs

### Slice A — el motor respeta la ventana comercial (E3)

- **S1 — La ventana acota toda oferta.** Ningún horario ofrecido a un cliente cae fuera de `hours.schedule` (día de la semana y franja horaria), ni en la oferta de un día pedido ni en la oferta general. Con `hours.schedule` vacío la oferta se comporta **exactamente** como hoy (sin restricción): es el caso que hay que cubrir con un test propio, porque vacío significa "sin restricción" y así está hoy en la base.
- **S2 — Un día pedido fuera de la ventana no inventa horarios.** Pedir un domingo no devuelve domingos. Se mantiene la ampliación existente de `slots_for_window` (buscar hacia adelante y responder `booking_window_unavailable` nombrando el momento pedido con `window_label`), de modo que el cliente reciba días reales en vez de un "no tengo ese dato".
- **S3 — La ventana tiene que existir.** S1 y S2 no cambian nada mientras `hours.schedule` esté vacío, así que la ventana real (lunes a sábado, 09:00–18:00) debe quedar configurada y verificable en el harness y documentada para producción. **Decisión abierta D1** (abajo): `hours.schedule` alimenta además el gate de cierre del chat.

### Slice B — los valores salen de la prosa (E2)

- **S4 — Cobertura desde la configuración.** Una pregunta por comunas se responde determinísticamente desde `coverage.communes` (lista de las que se atienden), sin llamada al modelo. Una comuna fuera de la lista mantiene el comportamiento de derivación que ya existe para `_out_of_coverage`.
- **S5 — Horario desde la configuración.** Una pregunta por días u horas de atención se responde desde `hours.schedule`, sin modelo, nombrando los días y el rango vigentes. Si la ventana está vacía, no se inventa un horario: se mantiene el camino actual.
- **S6 — Duración desde la configuración.** Una pregunta por lo que dura un servicio se responde desde `booking.service_durations`. Un servicio sin duración configurada conserva el camino actual (KB), nunca una duración inventada.
- **S7 — La KB deja de enunciar valores.** `docs/kb/lumat-cobertura-horarios.md` pierde la lista de comunas y los rangos `09:00`–`18:00`; `docs/kb/lumat-servicios.md` pierde las duraciones. Se conserva la **política** (fuera de horario y domingos los coordina un asesor, emergencias, qué incluye cada servicio). `docs/kb/drift-baseline.json` queda vacío y `scripts/kb_doc_drift.py` pasa a tolerancia cero.
- **S8 — Dependencia de entrega.** S7 sólo tiene sentido con el control de deriva mergeado (#718, `odd/kb-drift-control`), porque es lo que verifica que la lista quede en cero.

## Decisión abierta

- **D1 — ¿Una ventana o dos?** `hours.schedule` hoy hace dos cosas potenciales: acotar la oferta (S1) y cerrar el chat fuera de horario (`app/chat/nodes/closure_gate.py`, que responde `out_of_hours`). Configurarla para S1 también hace que el bot deje de responder de noche y los domingos. Hay que decidir si eso es lo buscado (una sola ventana, coherente con la KB) o si la oferta debe tener su propia clave y el chat sigue contestando siempre. Slice A no arranca hasta resolverlo.

## Tasks

| # | Tarea | Specs | Ruta | Commit |
|---|---|---|---|---|
| A1 | Ventana comercial como filtro en `open_slots_for_assignment`, con `hours.schedule` vacío = sin restricción | S1 | por decidir | — |
| A2 | Día pedido fuera de ventana: ampliación y mensaje existentes, sin domingos | S2 | por decidir | — |
| A3 | Configurar y verificar la ventana en el harness + procedimiento para prod | S3 | por decidir | — |
| B1 | `coverage_reply` determinista desde `coverage.communes` | S4 | por decidir | — |
| B2 | `hours_reply` determinista desde `hours.schedule` | S5 | por decidir | — |
| B3 | `duration_reply` determinista desde `booking.service_durations` | S6 | por decidir | — |
| B4 | Limpiar valores de `docs/kb/*.md`, baseline a cero, control en tolerancia cero | S7, S8 | por decidir | — |

## Log

- **L1 (pedido original, verbatim):** "si la abrimos como feature aparte/. puedes explicarmela?"
- **L2 (decisión, verbatim):** "Abrir E3 + E2, E3 primero (recomendado)" — un doc con los dos slices, E3 (motor y ventana comercial) primero; E2 (valores deterministas desde configuración) después.
- **L3 (contexto heredado de `odd/kb-drift`):** la contradicción de sábado de la conversación 42 se arregló en la prosa y en el ruteo (`odd/kb-drift`, PRs #717/#718), pero la clase de defecto sobrevive al domingo: la KB manda domingo a un asesor y el motor ofrece domingo 01/11 09:00, 09:30, 10:00 (verificado contra la base del harness el 2026-10-28). El motor obedece `technician_weekly_schedule` y no lee la KB ni `hours.schedule`.
