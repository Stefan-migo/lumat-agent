# ODD — chatbot-experiencia (agenda, saludo, cortesía, derivaciones y panel)

Origen: rapso-session `.rapsodia-code/sessions/open/2026-10-23-chatbot-experiencia/session.md` (decisiones D1–D15).
Branch: `odd/chatbot-experiencia` · Runner: `uv run pytest tests/` · Panel: `cd web && npm run build && npm test`
Base: `main` = `e354f563` (S1–S4 del backlog `chatbot-backlog` ya mergeados).
Un release único al final: estos slices entran junto con S1–S4 (D15).

## Specs

### S1 · Agenda — grilla, anticipación, más horarios y técnico

> Grilla de 30 minutos, con servicios de 60 minutos. Anticipación de 2 horas. Cuando "más horarios" no
> tiene, aclarar que no hay más para ese día en específico y ofrecer otros días. Sólo si no logra
> agendar pasar a humano (como salvataje). La cita nombra al técnico que va a ir.
> Asignación de técnico: round-robin por carga diaria.

Alcance:

- Los candidatos de `scheduling.open_slots` se alinean a una grilla de **30 minutos** y se descartan los
  segundos (hoy la cita quedó guardada a las `:04:32`).
- Anticipación mínima de **2 horas** (configurable), medida contra `now`.
- "Más horarios" entrega los siguientes 3 de la misma oferta congelada; si no hay más para ese día, lo
  dice y ofrece otros días. No deriva por pedir otro horario.
- **Aviso de día agotado** (texto aprobado, verbatim): `Para ese día no me quedan más horarios. Te
  propongo estos otros días:` + `{{opciones}}` + `Responde con el número del horario que prefieres.`
- Sólo cuando no queda ningún horario más se deriva, con `booking_unavailable` (el texto S4.5 llega en
  T7).
- Derivación de salvataje con el texto S4.5 sólo si no se logra agendar.
- Asignación **round-robin por carga diaria**: entre los técnicos libres para el horario, gana quien
  tenga menos visitas agendadas ese día; empate → alterna por id.
- La confirmación puede nombrar al técnico (`{{tecnico}}`), con fallback cuando `users.name` está vacío.
- **Confirmación** (texto aprobado, verbatim): `Tu visita técnica quedó confirmada para el {{fecha}} con
  {{tecnico}}.` — si el técnico no tiene nombre cargado, `{{tecnico}}` se completa con `nuestro equipo
  técnico` para que la oración no quede coja.

Riesgo: **item 1** (escribe citas en la agenda; un error agenda una visita real en un horario inválido)
y **item 3** (cambia el contrato de `open_slots`, que tiene otros consumidores).

### S2 · Saludo por nombre

> Si el chatbot ya dispone del nombre del cliente, saludar por nombre. Si no lo dispone, saludar
> consultando el nombre ("¿Con quién tengo el gusto?").

Textos (verbatim, aprobados):

- **Saludo con nombre:** `Hola, {{nombre}}. Soy Max, el asistente virtual de Lumat. ¿En qué te puedo ayudar?`
- **Saludo pidiendo el nombre:** `Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar.`
- **Saludo corto con nombre:** `Hola, {{nombre}}. Soy Max, de Lumat. Ya te ayudo con eso.`
- **Saludo corto sin nombre:** `Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso.`

Alcance: `customers.name` resuelve el slot; sin nombre se usa la variante que pregunta. El grupo de
saludo acepta `{{nombre}}`. El saludo corto **no** necesita una segunda respuesta: `run_conversation` lo
fusiona con la primera pregunta del turno (CM-1).

Los cuatro textos aprobados no son una plantilla con un hueco: cuando falta el nombre **cambia la
oración** (pregunta el nombre y no repite "¿En qué te puedo ayudar?"). Por eso son cuatro claves:
`messages.greeting`, `messages.greeting_name`, `messages.greeting_short` y
`messages.greeting_short_name`. El bot pasa a llamarse **Max** en el saludo por decisión del owner.

Corrección de mecanismo (medida en T5): el rechazo de llaves no estaba en el panel ni en el guardado
de `messages.*`, sino en `validate_assistant_setting()` —la lista curada de claves que el asistente
puede escribir—. El cambio acota el slot `{{nombre}}` a las dos claves con nombre y rechaza llaves en
las demás claves de mensaje que escribe el asistente. **Brecha conocida, para T8:** la ruta del panel
(`POST /settings/messages`) no valida llaves, así que un `{{nombre}}` guardado desde el panel en otra
clave llegaría literal al cliente.

Riesgo: **item 3** (el grupo de mensajes fijos gana un slot; cambia el contrato de validación del panel).

### S3 · Cortesía (smalltalk)

> La cortesía no puede consumir un fallo de comprensión ni disparar la aclaración. `unknown` significa
> "no entiendo qué quiere", no "esto no es ninguno de mis temas". El vocabulario lo pone el LLM; el
> grafo decide el flujo.

Alcance: categoría `smalltalk` en `agent/personas/classify.md`; rama explícita en `respond` (o en
`_dispatch`) con texto configurable; no suma `unknown_intent` (la racha se corta sola); `unknown`
redefinido en la persona como incomprensión real. La lista determinista `_SOCIAL_ONLY` **no** se
extiende como sustituto.

Riesgo: **item 3** (la persona del clasificador está acoplada byte a byte a `prompts.FALLBACKS` y a los
tests que la fijan).

### S4 · Derivaciones: información + 5 textos

> En el panel tiene que quedar claro en qué casos deriva el bot, y poder modificar el texto sólo de los
> 5 casos que el cliente lee.

Textos (verbatim, aprobados):

- **S4.1 Cobertura** (necesita `{{comuna}}`): `Todavía no tenemos visitas técnicas en {{comuna}}, un asesor de Lumat se contactará contigo para ayudarte a la brevedad.`
- **S4.2 Pedido de persona:** `Listo, te paso con una persona del equipo. En cuanto esté disponible te escribe por acá.`
- **S4.3 Tres fallos:** `No quiero seguir dándote vueltas con esto. Te dejo con una persona del equipo para que te ayude directamente.`
- **S4.4 Campo sin respuesta:** `Veo que esa pregunta no te acomoda. Un asesor de Lumat te contacta para terminar de coordinar los datos.`
- **S4.5 Salvataje de agenda:** `No encontré un horario que nos sirva en la agenda, así que no te voy a dejar esperando: un asesor de Lumat te contacta para coordinar la visita directamente.`

Alcance: selección del texto por `escalate_reason` en `handoff.py`; las demás razones siguen con el
texto genérico. Las 4 reglas de `chat.conduct.derivaciones` sin lector se sacan del panel.

Riesgo: **item 3** (cambia lo que el cliente recibe en toda derivación; los tests fijan el texto único).

### S5 · Panel: respuestas prediseñadas y horarios de técnicos

> Configurar el chatbot desde el panel es difícil. No hace falta cambiar el código de id a categoría; lo
> importante es hacerlo más entendible en el UI/UX.

Alcance: mostrar y autogenerar el `id` de una plantilla, explicar que el cliente nunca lo ve, vista
previa con datos reales y advertencia de que una plantilla con un slot vacío se salta (S9). Mover la
configuración de horarios de técnicos de Agenda a Configuración. Exponer la anticipación mínima y los
textos nuevos.

Riesgo: **item 3** (mueve superficies del panel que tienen tests y `tsc -b`).

## Non-goals

- No se delega el ruteo al modelo: el grafo decide, el LLM clasifica y redacta (D1, tradeoff rechazado).
- No se cambian los límites de costo (D14).
- No se responde "qué técnico está disponible" (D8): expone agenda interna.
- No se asocia cada plantilla a una categoría del clasificador (D10).
- No se mueve `name` al inicio del orden de captura: el validador lo prohíbe y contradice S11/D8.
- T7 (re-medir handoffs) queda fuera hasta el deploy.

## Tasks

| ID | Spec | Alcance | Ruta | Commit |
|---|---|---|---|---|
| T1 | S1 | Grilla de 30 min + anticipación 2 h en `scheduling` | inline, test-first | `e934a261` |
| T2 | S1 | Round-robin por carga diaria en la asignación | inline, test-first | `d473ee74` |
| T3 | S1 | "Más horarios" paginado + aviso "no hay más para ese día" + otros días | inline, test-first | `ae02f872` |
| T4 | S1 | Salvataje de agenda y `{{tecnico}}` en la confirmación | inline, test-first | `50ed958b` |
| T5 | S2 | Saludo con `{{nombre}}` y variante que pregunta el nombre | inline, test-first | pendiente |
| T6 | S3 | Categoría `smalltalk` + rama + texto configurable | worker + inline, test-first | pendiente |
| T7 | S4 | Textos por motivo de derivación (5) + panel | inline, test-first | pendiente |
| T8 | S5 | UX de respuestas prediseñadas + horarios de técnicos a Configuración | worker + inline, test-first | pendiente |

## Log

**L1 — textos aprobados por el owner (verbatim, 2026-10-23):**

> 1. Saludo con nombre: Hola, {{nombre}}. Soy Max, el asistente virtual de Lumat. ¿En qué te puedo ayudar?
> 2. Saludo pidiendo el nombre: Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar.
> 3. Saludo corto con nombre: Hola, {{nombre}}. Soy Max, de Lumat. Ya te ayudo con eso.
> 4. Saludo corto sin nombre: Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso.
>
> 1 y 2 estan bien.
> 3 y 4. no estoy seguro. pero requeririan mas de una respuesta por turno? dos al menos?
>
> modificaciones:
> 5. Todavía no tenemos visitas técnicas en {{comuna}}, un asesor de Luamt se contactará contigo para ayudarte a la brevedad.
> 6. correcto asi.
> 7. correcto asi
> 8. correcto asi.
> 9. correcto asi.

Resolución de la duda 3/4: no hacen falta dos respuestas — `run_conversation` fusiona el saludo con la
primera pregunta del turno (CM-1). Texto 5: "Luamt" se corrige a "Lumat" (typo confirmado por contexto).

**L2 — asignación de técnico (verbatim):** `si round robin` → round-robin por carga diaria.

**L3 — release y costo (verbatim):**

> los slices entran en el release asi que lo postergamos.
> no es necesario si llegara a ser necesario lo subimos.por ahora esta bien. era solo para dejar en claro
> que el costo no debe ser factor para el rendimiento del chatbot.

**L4 — decisiones previas de la sesión (verbatim, 2026-10-23):**

> grilla de 30, con servicios de 60 minutos. ... anticipacion de 2 horas, cuando mas horarios no tiene,
> aclarar que no hay mas para ese dia en especifico ofrecer otro dias. solo si no logra agendar pasar a
> humano (como salvataje)
>
> si el chatbot ya dispone del nombre del cliente. saludar por nombre. si no lo dispone, saludar
> consultando el nombre (con quien tengo el gusto?)
>
> quizas no es necesario cambiar el codigo de id a categoria. lo importante es hacerlo mas entendible en
> el ui/ux, actualmente es super dificil configurar el chatbot desde el panel.
>
> que es mover la configuracion de los horarios de los tecnicos a la seccion de configuracion. quiero
> centralizar toda la configuracion en la seccion cofiguracion

**L5 — T1 cerrado (2026-10-23), evidencia observada.** Commit `e934a261` (código) + este commit
(docs, el papeleo que el crash dejó a medias).

- Cambio: `open_slots` alinea los candidatos a una grilla de 30 minutos, descarta los segundos y
  rechaza lo que esté a menos de `lead_minutes` de `now`; `booking` pasa `booking.lead_minutes`
  (default 120, en `settings`). `open_slots` acepta `now` del caller para que el camino de asignación
  sea testeable en vez de leer el reloj a espaldas del test.
- Focales: `uv run pytest tests/unit/test_scheduling_unit.py tests/integration/test_scheduling.py` →
  32 tests, exit 0.
- Suite completa: `uv run pytest tests/ -q --timeout=300` → 2820 tests, 0 `FAILED`/`ERROR`,
  `PYTEST_EXIT=0`, 6m20s, sobre la base de test del worktree
  (`lumat-test-lumat-agent-odd-chatbot-experiencia-db-test-1`). Esa corrida excluyó con `-k` los dos
  tests RED de T2 que ya estaban escritos, para que la evidencia corresponda al árbol de `e934a261`.
- Primera corrida descartada: la lancé con `| tail -40`, que se comió el resumen y el exit code real
  (devolvió el de `tail`), y mostró un `pytest-timeout` en
  `tests/functional/test_seed_dev.py` (subprocess de `seed_dev.py`) con el host en carga ~4 y 15 GB
  de RAM casi llenos. Repetida con captura completa: limpia. Es el artefacto de carga del host ya
  anotado, no un fallo del slice; queda registrado porque un timeout también es evidencia.
- Pins movidos, no debilitados: el test de asignación ahora espera los tres candidatos de la grilla,
  y el test del paso por defecto se renombró (el paso por defecto es la grilla, ya no la duración del
  servicio).
- Pendiente de T8 (S5): `booking.lead_minutes` existe en `settings` pero todavía no se expone en el
  panel.

**L6 — T2 cerrado (2026-10-23), evidencia observada.** Commit `d473ee74` (código + tests) + este
commit (docs).

- RED: los dos tests nuevos fallaban con la regla vieja —
  `test_open_slots_for_assignment_alternates_between_equally_loaded_technicians` (esperaba
  `[lower, higher, lower]`, daba `[lower, lower, lower]`) y
  `test_open_slots_for_assignment_prefers_the_technician_with_fewer_visits_that_day` (esperaba los
  tres slots al técnico libre, el último caía al técnico cargado).
- GREEN: `uv run pytest tests/integration/test_scheduling.py tests/unit/test_scheduling_unit.py
  tests/integration/test_technician_schedule.py` → 38 tests, exit 0.
- Suite completa: `uv run pytest tests/ -q --timeout=300` → 2822 tests, 0 `FAILED`/`ERROR`,
  `PYTEST_EXIT=0`, 5m52s. Incluye los dos consumidores de la función (`booking.py` y el reschedule de
  `manage.py`), así que la regresión sobre ellos queda cubierta por la corrida, no por inspección.
- Regla: cada slot lo cubren **todos** los técnicos que pueden atenderlo; gana el que tenga menos
  visitas `BOOKED` ese día local; empate → alterna por id con una rotación por slot asignado. La carga
  se cuenta desde la agenda y no desde las ofertas de la misma llamada, porque una oferta no es una
  visita hasta que el cliente la toma.
- Pin movido: `test_open_slots_for_assignment_uses_lowest_free_technician_and_never_mutates` →
  `..._skips_the_busy_technician_and_never_mutates`. El pin que importa (un técnico con una visita
  10:00–11:00 no se ofrece en esa hora) sigue vivo y en verde; sólo cambió la expectativa de las 11:00.
- Sin migración y sin cambio de contratos de panel: la firma de `open_slots_for_assignment` no cambió.
- Límite de slice: con `d473ee74` la rama acumula 484 líneas autoradas, pasado el objetivo de ~400.
  No se parte la entrega porque D15 fija **un solo release** al final; los commits por task siguen
  siendo las unidades revisables (feat + docs por task).

**L7 — copy de T3/T4 aprobado por el owner (2026-10-23), verbatim de las opciones elegidas:**

> Para ese día no me quedan más horarios. Te propongo estos otros días:
> {{opciones}}
> Responde con el número del horario que prefieres.

> Tu visita técnica quedó confirmada para el {{fecha}} con {{tecnico}}.
>
> Con técnico sin nombre cargado: "…con nuestro equipo técnico."

El primero se implementa en T3; el segundo en T4 (la parte `{{tecnico}}`), y el salvataje de agenda
reusa el motivo `booking_unavailable` cuyo texto S4.5 entra en T7.

**L8 — T3 cerrado (2026-10-23), evidencia observada.** Commit `ae02f872` (código, tests y panel) +
este commit (docs).

- RED: los tres tests nuevos de `tests/integration/test_chat_booking.py` fallaban — página siguiente
  el mismo día, día agotado con aviso, y sin horarios restantes. Antes, pedir otro horario daba
  `booking_unclear` y después derivación.
- GREEN: `tests/integration/test_chat_booking.py` → 12 tests, exit 0.
- Panel: `npm run build` (tsc -b) exit 0 y `npm test` → 111 archivos / 1264 tests, exit 0, con un pin
  nuevo de que el campo "Sin más horarios para ese día" se renderiza en el grupo Agendar y viaja al
  endpoint `reply-texts` bajo su propia clave. La primera corrida del panel murió con el crash y se
  repitió completa.
- Suite backend, corrida 1: 2837 tests, **1 FAILED** —
  `test_reply_texts.py::test_the_catalog_covers_booking_manage_handoff_and_capture`, porque el
  catálogo de respuestas es cerrado y la clave nueva no estaba declarada. Se movió el pin (entrada
  explícita) y se agregó un pin byte a byte del copy aprobado.
- Suite backend, corrida 2: 2825 tests, 0 `FAILED`/`ERROR`, `PYTEST_EXIT=0`, 6m57s.
- Diseño: la oferta se congela al crearse (universo de 30 candidatos guardado en `_booking_offer`);
  "más horarios" sirve la página siguiente de 3 y reinicia la numeración y los intentos. Si la página
  ya no cae en el día de la oferta respondida, se dice con el texto aprobado. Sin más candidatos →
  `handoff` con `booking_unavailable`.
- Detector: lista acotada de marcadores (`más horarios`, `otros horarios`, `otra hora`, `otros días`,
  `no me sirve`, `no puedo en esos`, …). Falla cerrado: lo que no matchea sigue con la aclaración y
  después la persona.
- No se tocó la TTL de 30 minutos: la oferta congelada vence igual, y como la anticipación mínima
  (2 h) es mayor que la TTL, ninguna página puede ofrecer un horario ya pasado.

**L9 — T4 cerrado (2026-10-23), evidencia observada.** Commit `50ed958b` (código, tests y mock de
stories) + este commit (docs).

- Delegado a `gentle-ai-worker`, que se frenó primero por un falso bloqueo de Graph Check: corrió
  `find graphify-out -maxdepth 2 -type f` y no atravesó el symlink a `../lumat-agent/graphify-out`.
  El grafo estaba ahí (`graph.json` 15 MB, `GRAPH_REPORT.md` 208 KB); se le indicó `find -L` y siguió.
  **Regla para próximos workers:** en este repo el check es `ls -la graphify-out/` o `find -L`.
- RED (evidencia del worker): `tests/integration/test_chat_booking.py tests/unit/test_reply_texts.py`
  → 6 fallos, `KeyError: 'tecnico'` en los tres caminos de confirmación, antes de implementar.
- GREEN: los mismos dos archivos → 34 tests, exit 0. Re-corridos verdes después del refactor de
  revisión (extraer `_technician_name()` y la constante `TEAM_FALLBACK` fuera de `booking()`, que ya
  era larga).
- Panel: `npm run build` exit 0 y `npm test` → 111 archivos / 1264 tests, exit 0.
- Suite backend: 2828 tests, 0 `FAILED`/`ERROR`, `PYTEST_EXIT=0`, 8m41s.
- Pins movidos: la expectativa de `booking_confirmed` pasa al texto aprobado y el vocabulario cerrado
  de slots suma `tecnico` explícito. `EXPECTED_KEYS` no cambió.
- Alcance respetado: nada de `handoff.py` ni de textos de derivación. El motivo `booking_unavailable`
  ya existe desde T3/T4; su texto S4.5 entra en T7.
- Deuda conocida para T8: el fallback `nuestro equipo técnico` vive en código como constante, no en
  `settings`; si el owner quiere editarlo desde el panel, es una clave nueva y su slot.
- Estado de la rama al cerrar T4: 8 commits, 832 líneas autoradas. T5–T8 quedan **bloqueados** por
  pedido explícito del owner ("detente cuando termines T4. no comiences T5").

**L10 — merge de `main` y corte en dos PRs (2026-10-23), evidencia observada:**

- `origin/main` avanzó a `94e6921c` (6 commits: política de test tiers con `scripts/test.sh`, aislamiento
  de `MEDIA_DIR` en `tests/conftest.py` y el fix del flake de `test_time_triggers`). Merge limpio en la
  rama, sin conflictos: main tocó `AGENTS.md`, `scripts/`, `openspec/` y el harness de tests; esta
  feature tocó `app/`, `web/src` y este doc.
- Gates con la política **nueva** (no con la vieja "siempre la suite completa"):
  `bash scripts/test.sh shape origin/main` → exit 0 (sin superficie de forma); `bash scripts/test.sh
  full` → **2834 tests, 0 fallos, exit 0** (8m11s); panel `npm ci` → `build` exit 0 → `npm test` →
  **111 archivos / 1264 tests, exit 0**.
- Corte en dos slices encadenados, en vez de un PR de 819 líneas: **#668** `odd/chatbot-agenda` (T1–T2,
  base `main`, 491 líneas con `size:exception` porque 208 son este doc) y **#669** `odd/chatbot-oferta`
  (T3–T4, base `odd/chatbot-agenda`, 328 líneas).
- Las ramas se **rearmaron por cherry-pick sobre el `main` actual** (`odd/chatbot-agenda` desde
  `origin/main`, `odd/chatbot-oferta` encima) para que cada diff muestre sólo su slice y para cumplir
  `strict` (rama al día) sin commits de merge en la cadena. Verificado: el árbol de `odd/chatbot-oferta`
  es idéntico al de la rama previa al corte (`git diff` vacío), así que el `full` corre sobre el mismo
  contenido que el tip de la cadena.
- `odd/chatbot-agenda` verificado en su propio árbol: `bash scripts/test.sh quick` exit 0 y `db
  tests/integration/test_scheduling.py` 20 tests exit 0.
- `odd/chatbot-experiencia` queda como respaldo local, sin pushear. **Continuación de T5 en adelante:
  desde `odd/chatbot-oferta`**, que después del merge de #668 se rebasa sobre `main` y pasa a ser la
  rama de trabajo.

**L11 — T5 cerrado (2026-10-23), evidencia observada.** Commit `0b2b9e09` (código, tests y panel) +
este commit (docs). Rama rearmada desde `main` (`497875af`) después de mergear #668 y #669.

- Delegado a `gentle-ai-worker`, que se frenó dos veces por autorización: pidió `web/src/types.ts`
  (correcto: `Settings.messages` no compilaba sin las claves nuevas) y después se detuvo por una
  contradicción mía —dije "esta lista reemplaza la anterior" y me olvidé `types.ts` en ella—. Un writer
  que frena ante una autorización ambigua es preferible a uno que adivina.
- RED inicial (worker): 10 fallos en
  `test_settings.py` + los cuatro archivos de saludo/configuración. GREEN del worker: 141 tests.
- La escalera de gates encontró cuatro cosas que `focused` no ve, y por eso no se salteó ningún nivel:
  1. `quick` → `test_assistant_delegation::test_panel_planner_catalog_matches_pre_delegation_bytes`,
     porque `settings.update` publica la lista de claves escribibles. Se probó que el catálogo cambia
     **sólo** por las dos claves nuevas (quitar ambas reproduce el hash viejo) antes de moverlo:
     `c73d185d…` → `48e5af3c…`.
  2. `npm test` completo → tres pins de stories/mock del panel (etiquetas renombradas y el set de
     claves del mock de 8 a 10).
  3. `full` → cinco pins de copy viejo en `test_api_kb_settings`, `test_conversation_flows`,
     `test_chat_harness`, `test_chat_state` y `test_first_turn_greeting`.
  4. `full` → **un defecto real, no un pin**: `test_settings_update_messages_audited` devolvía **422**
     porque `MessagesBody` exige las dos claves nuevas. Se mantuvo el body requerido (el panel siempre
     manda el mapa completo, igual que en `reply.texts`) y se actualizó el payload del test. Tomarlo
     como "test viejo" habría dejado el panel sin poder guardar mensajes.
- GREEN final: `quick` exit 0; `focused` de los cinco archivos de pins → 111 tests, exit 0; panel
  `npm run build` exit 0 y `npm test` → 111 archivos / **1265 tests**, exit 0; `full` → **2846 tests,
  0 fallos**, exit 0, 5m43s.
- Contrato: `MessagesBody` gana dos campos requeridos; `ASSISTANT_WRITABLE_SETTINGS` gana
  `messages.greeting_name` y `messages.greeting_short_name`; `validate_assistant_setting()` acota
  `{{nombre}}` a esas dos claves y rechaza llaves en las demás claves de mensaje que escribe el
  asistente. `Settings.messages` en `web/src/types.ts` exige las diez claves (se descartó dejarlas
  opcionales: la API las devuelve siempre).
- Deuda registrada: el camino del panel (`POST /settings/messages`) no valida llaves — va a T8.
- Duplicado conocido, no podado: el caso "saludo sin contenido" de `test_first_turn_greeting.py` se
  solapa con `test_greeting_variants.py`. Se dejó anotado: podar tests es una decisión aparte, no un
  efecto colateral de mover pins.

**L12 — decisión del owner sobre los acuses (2026-10-23), verbatim de la opción elegida:**

> Completar S3 ahora: acuses fuera, despedida sólo explícita. La despedida queda sólo para cierres
> explícitos (chao, adiós, hasta luego). "Gracias" pasa a recibir el texto de cortesía. Costo: si el
> cliente se despide con un "gracias" final, el bot le pregunta si necesita algo más en vez de cerrar.

**L13 — T6 cerrado (2026-10-23), evidencia observada.** Commit `702f8a8e` (código, tests y panel) +
este commit (docs).

- RED: `test_smalltalk.py` fallaba con la oferta de KB-miss en vez del texto de cortesía. Además se
  observó que un `gracias` pelado tomaba la despedida del `closure_gate` **antes** de clasificarse.
- GREEN: `quick` exit 0; `focused` de smalltalk/intent/unknown-streak/settings/persona → 130 tests;
  panel `npm run build` exit 0 y `npm test` → 111 archivos / 1265 tests; `full` → **2852 tests,
  0 fallos**, exit 0 (7m8s), corrida propia después del cambio del gate.
- Diseño: `smalltalk` en la persona del clasificador (con `unknown` redefinido como incomprensión
  real); `classify_intent` registra `classified/intent:smalltalk`, **no** toca `unknown_count` ni las
  scope-rules; `orchestrate` rutea explícito a `respond` también en captura; `respond` responde con
  `messages.smalltalk` antes de templates, aclaración y KB.
- `_SOCIAL_ONLY` **no** se extendió, como manda la spec: el vocabulario lo pone el clasificador.
- `closure_gate`: `CLOSING_TOKENS` queda sólo con cierres explícitos (`adios`, `bye`, `chao`, `chau`,
  `hasta`, `luego`, `nos`, `pronto`, `vemos`) y "eso fue todo" gana su propio camino (frase matcheada
  sin tokens restantes = despedida), porque dependía del agradecimiento que la seguía.
- Pins movidos: hash del catálogo del planner (`721dfa2b…`, probado quitando sólo la clave nueva),
  catálogo de mensajes del panel de 10 a 11, `MessagesBody` con la clave requerida, fixtures y pins de
  stories/mock.
- Decisión de empaquetado: un solo commit aunque el cambio tenga dos mitades (cortesía + gate), porque
  los tests de acuses dependen del gate y un commit intermedio quedaría con la suite en rojo.
- Consecuencia declarada y aceptada por el owner: un "gracias" final ya no cierra la conversación; el
  bot ofrece seguir. Es el precio de no usar una lista determinista para decidir cuándo terminar.
