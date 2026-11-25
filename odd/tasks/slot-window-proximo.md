# slot-window-proximo — el día que el cliente pidió, no el que el parser eligió

Pendiente 2 del handoff post-`v2026.11.19`. Dos defectos medidos con la función en la mano:
«próximo martes» resuelve al martes de hoy, y `am`/`pm` no son franja, así que «a las 3 pm» se
ofrece como las 03:00.

## Specs

- **S1** — «slot_window: «próximo martes» resuelve al martes de hoy». Medido con
  `resolve_window("el próximo martes", today=martes)`: devuelve `day = hoy`. Un cliente que dice
  «próximo» no está pidiendo hoy; el día ofrecido tiene que ser estrictamente posterior.
- **S2** — «am/pm no son franja». Medido:
  `resolve_window("el martes a las 3 pm")` → `desde = 03:00`. El cliente pidió las tres de la
  tarde y el bot ofrece la madrugada. `10 am` resuelve bien por accidente; `12 am` y `12 pm` son
  las dos esquinas del reloj de doce horas y necesitan su propia regla.
- **S3** — Lo que hoy funciona no cambia: «martes» sin marca sigue incluyendo hoy, «el proximo
  miercoles» desde un martes sigue siendo el miércoles siguiente, y las dos frases que ya fijan
  el reloj de doce por la franja («a las 3 de la tarde») conservan su valor. Base:
  `test_today_matches_its_own_weekday`, `test_proximo_weekday_from_the_production_conversation`,
  `test_an_hour_inside_a_stated_franja_is_twelve_hour_clock`.

## Tasks

- T1 → S1, S2, S3 · RED: los tests del día estrictamente posterior y del reloj de doce horas · `c00bb76fd`
- T2 → S1, S2 · GREEN: la marca de «próximo» y el meridiem en `app/chat/slot_window.py` · `c00bb76fd`
- T3 → S3 · chequeo diferencial contra el commit base sobre el resto de las frases · `c00bb76fd`
- T4 → S1-S3 · verificación y cierre del corte · `c00bb76fd`

## Log

L1 — pedido del owner, verbatim (pendiente 2 del handoff, más la decisión):

> 2. slot_window: «próximo martes» resuelve al martes de hoy; am/pm no son franja. Verificado con la
> función en la mano.

> vamos con el orden sugerido

L2 — reproducción propia antes de tocar nada (`resolve_window`, hoy = martes 2026-11-24 y
miércoles 2026-11-25): «el próximo martes» → hoy; «el martes que viene» → hoy; «el martes a las
3 pm» → `desde 03:00`; «el martes a las 3 de la tarde» → `desde 15:00` (correcto, sirve de
control); «a las 10 am» → `desde 10:00` (correcto por accidente).

L3 — alcance: la marca estricta se aplica a «próximo/próxima/siguiente» y a «que viene», porque
la reproducción de L2 muestra que las dos formas resuelven al mismo día de hoy: es el mismo
defecto, no una función nueva. El reloj de doce horas se limita a `am`/`pm` con o sin puntos: el
módulo sigue sin adivinar una hora suelta («a las 3» sin marca no es 15:00 ni 03:00 por decreto),
que es la regla que el docstring del módulo defiende.

L4 — `resolve_window` no es exclusivo del agendamiento: lo leen `booking`, `manage`, `capture` y
`configured_answers`, así que el cambio entra en la regla de código compartido y T3 corre el
diferencial contra el commit base antes de cerrar.

L5 — cierre y verificación observada: RED con 9 casos fallando (los dos de «próximo/que viene» y
seis del meridiem; «10 am» y «12 pm» pasaban por accidente, y `test_a_bare_weekday_still_includes_today`
pasaba como control), GREEN con `bash scripts/test.sh focused tests/unit/test_slot_window.py`
(exit 0), `quick` (exit 0) y `shape` (exit 0, «no shape surface touched»).

L6 — diferencial (T3): 49 frases × 3 días = 147 comparaciones entre `app/chat/slot_window.py` del
commit base y el del corte. **13 diferencias, todas la regla pedida**: «el próximo martes», «mejor el
martes que viene» y «la próxima semana el martes» desde un martes pasan de hoy a +7; «el próximo
miércoles en la mañana» desde un miércoles pasa de hoy a +7; y `a las 3 pm` / `a las 3 p.m.` /
`3:30 pm` pasan de 03:00 a 15:00 en los tres días. Ninguna otra frase se movió, incluidos «el jueves»,
«mañana», «cualquier día en la mañana», «después de las 6», «después de las 6 hrs» y las de
reagendamiento. El diferencial es un script de una pasada en `mktemp -d`; no se commitea.
