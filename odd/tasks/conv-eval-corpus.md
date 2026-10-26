# ODD — conv-eval-corpus

Alinear las expectativas del corpus del evaluador conversacional con la política de derivación vigente del
bot, para que el número que produce deje de mezclar "el bot falla" con "el corpus mide un contrato que ya
no existe". Sale de la sesión de decisiones `2026-10-26-conv-eval-corpus-review`
(`.rapsodia-code/sessions/ready-for-odd/2026-10-26-conv-eval-corpus-review/report.md`).

- Branch: `odd/conv-eval-corpus` · Base: `81972cfa` (main) · Worktree: `../lumat-agent-odd-chatbot-conv-eval`
- Runner: `uv run pytest tests/unit/test_conv_eval.py` (schema, gates y plan de turnos, sin LLM)
- Corridas: `uv run python scripts/conv_eval.py --live` (fuera de pytest, con modelo real)

## Specs

### S1 · La causa de la derivación se verifica, no se prohíbe

> "Aceptar human y verificar la causa" · `causes_required: [booking_unavailable]  (gate nuevo)`

Un escenario puede aceptar que la conversación termine en manos de una persona **y** declarar qué
derivaciones acepta (`causes_required`). El gate falla cuando se registra una `escalation` cuya causa no
está declarada. Un escenario sin `causes_required` no cambia de comportamiento.

### S2 · El tier `simple` corre scripted puro

> "Sí: el tier simple corre scripted puro"

Bajo `--live`, un escenario `simple` tiene presupuesto igual a su guion: sin turnos simulados. Un
`max_turns` declarado sigue ganando, y `complejo`/`supercomplejo` conservan el margen. El piso de la
medición no puede depender de lo que un LLM decida inventar.

### S3 · El guion de `simple-horario-sabado` dice la comuna

> "D1 lo deja scripted puro; el guion necesita el dato de comuna para que la expectativa sea alcanzable"

El guion scripted declara una comuna **cubierta** (Ñuñoa) para que el bot pueda responder sobre el sábado
sin que el simulador invente un dato. Sin esto, S2 deja el escenario sin forma de alcanzar su expectativa.

### S4 · Los cinco relajados declaran su causa

> "5 se relajan con causa esperada (agendar, no-quiere-email, fuera-de-cobertura, burst y dos-temas)"

| Escenario | `state_any` | `causes_required` |
|---|---|---|
| `complejo-agendar-calefont` | `[human]` | `[booking_unavailable]` |
| `complejo-no-quiere-email` | `[human]` | `[booking_unavailable]` |
| `complejo-fuera-de-cobertura-insiste` | `[human]` | `[cobertura]` |
| `super-burst-contradiccion` | `[human]` | `[cobertura]` |
| `complejo-dos-temas` | `[human]` | `[persona]` |

`escalation` sale de `events_forbidden` solo donde ahora es esperado; las demás prohibiciones quedan.

### S5 · `super-near-miss-lavadora` declara su estado

> "1 se completa (near-miss, que hoy no declara estado)"

Hoy no declara `state_any`, así que pasa con cualquier estado final. Declara `[human, bot]` explícito: la
respuesta correcta es ofrecer el siguiente paso, y la política admite derivar.

### S6 · Una corrida `--live` verifica el corpus nuevo

> "6. Corrida de verificación `--live` sobre el corpus nuevo (el baseline de `main` que busca el owner)"

Tres corridas citables con el corpus corregido, árbol limpio, 14/14 escenarios medidos, y la comparación
entre ellas documentada. Ese trío es el baseline de `main` con el que se hace el análisis global.

## Non-goals

- No toca `app/`: los dos defectos del bot que el baseline destapó (`escalation` sin registrar en
  `emergency.py`, y el `kb_miss` de retrieval) quedan como tareas propias, fuera de esta feature.
- No agrega escenarios al corpus ni cambia el tier de ninguno.
- No toca la rúbrica del juez ni `escalation`, que sigue abierto.
- No corre en CI.

## Tasks

| # | Slice | Qué entrega | Route | Commit |
|---|---|---|---|---|
| T1 | S1 | gate `causes_required`: schema, evaluación, reporte y tests | inline | `3d7efd73` |
| T2 | S2 | `simple` scripted puro bajo `--live`, con el plan de turnos fijado por test | inline | `3d7efd73` |
| T3 | S3 | guion nuevo de `simple-horario-sabado` (comuna cubierta) | inline | `4f36c6ed` |
| T4 | S4 | los cinco `expect` relajados con su causa | inline | `4f36c6ed` |
| T5 | S5 | `state_any` explícito en `super-near-miss-lavadora` | inline | `4f36c6ed` |
| T6 | S6 | tres corridas `--live` del árbol entregado y su evidencia | inline | `646ae781` + `d460411c` + `6ad36086` |

## Log

### L1 — la sesión de decisiones pidió el handoff (2026-10-26)

> "ok continua con el odd"

Con el baseline medido (4–5 de 14 en tres corridas limpias) y la sesión de decisiones cerrada, el owner
aprobó las cuatro decisiones D1–D4 y el veredicto por escenario: 7 vigentes, 5 relajados, 1 guion nuevo, 1
completado. El detalle y la evidencia están en el reporte de la sesión; el corpus vive en
`scripts/conv_eval_corpus.yaml` y la política que lo contradice en `app/chat/nodes/booking.py`
(`booking_unavailable`), `app/chat/nodes/capture.py` (`cobertura`) y `app/chat/nodes/handoff_gate.py`
(`persona`, `complaint`).

### L2 — implementado: el gate, el piso reproducible y el corpus alineado (2026-10-26)

`3d7efd73` trae las dos capacidades que faltaban. **G10 `causes_required`** es el espejo de G5
(`causes_forbidden`): el escenario acepta que la conversación termine con una persona y declara qué
derivación espera; derivar por otro motivo —o no derivar— sigue fallando, así que relajar una expectativa
no apaga la medición de la derivación. El matcher de causas se extrajo y G5 lo comparte, para que los dos
lean `handoff:cobertura` y `cobertura` igual. **`simple` sin turnos simulados** bajo `--live`: es el piso,
y un piso que depende de lo que un LLM invente no es reproducible. `complejo`/`supercomplejo` conservan su
margen, y `max_turns` o `--max-turns` siguen mandando.

Dos tests viejos se reescribieron a propósito, no por conveniencia: fijaban exactamente el presupuesto que
S2 cambia (`test_a_live_run_gives_the_simulated_customer_room` y
`test_a_live_plan_reaches_the_simulated_customer`). Ahora el segundo afirma que los cinco `simple` son
mudos por decisión, no por accidente.

`4f36c6ed` alinea el corpus. El guion de `simple-horario-sabado` necesitó **tres turnos** y no dos: medido
con `--only … --no-judge`, con dos el bot respondía «¿Cuál es tu nombre?» y la conversación terminaba antes
de la pregunta; con tres —el cliente da el nombre e insiste— el bot contesta «No tengo ese dato» y ofrece
la derivación. Resultado: el escenario queda con su expectativa intacta (`state_any: [bot]`,
`kb_answered: true`) y **falla por el defecto real** de retrieval, no por corpus viejo. Era el sentido de
S3: que el escenario mida lo que dice medir.

Caveat anotado a propósito: los dos escenarios de `booking_unavailable` declaran esa causa porque es la
que registraron las tres corridas del corpus anterior; si en una corrida futura hay agenda disponible, el
bot reservará, terminará en `bot` y G1/G10 fallarán. Eso es información, no un error del corpus: significa
que el escenario dejó de ser determinista y hay que mirar por qué.

Verificación de esta entrada: `uv run pytest tests/unit/test_conv_eval.py` **126/126**.

## Entrega

Dos PR encadenados, como la feature anterior:

1. **El instrumento y el corpus** (`3d7efd73`, `4f36c6ed`, `91c77bc2`, `bad00f1a`): el gate
   `causes_required`, el tier `simple` scripted puro, el guion de `horario-sábado`, los cinco `expect`
   relajados, el `state_any` del near-miss y el arreglo de `compare_runs`. Es lo que hay que leer.
2. **La evidencia del baseline** (`646ae781`, `d460411c`, `6ad36086`): las tres corridas del árbol
   entregado, `.md` más transcripción, sin JSON. Son reportes generados que nadie revisa línea por línea:
   viajan aparte justamente para no inflar el diff del código. Los commits del primer trío
   (`64e48e5c`, `6fd19d34`, `3701fdbc`) quedaron en la historia pero su evidencia se sacó de la rama: medían
   `81972cfa`, no el árbol que se entrega. La decisión está en L4.

### L3 — el corpus alineado, medido tres veces (2026-10-26)

Tres corridas citables del corpus nuevo, todas con árbol limpio y **14 de 14 escenarios medidos**:

| Corrida | Commit | Pasan | Juez: hard fails |
|---|---|---|---|
| `corpus-1` | `64e48e5c` | 3/14 | 8 |
| `corpus-2` | `6fd19d34` | 5/14 | 5 |
| `corpus-3` | `3701fdbc` | 6/14 | 6 |

**Mediana: 5 de 14.** Pero el total es la parte menos informativa. Por escenario, en las tres corridas:

- **Nunca pasan (8):** precio-calefont (2 de 3 corridas cotizó mal), cobertura-comuna, despedida,
  agendar-calefont, dos-temas, no-quiere-email, fuera-de-cobertura, emergencia-gas, burst-contradiccion.
  Siete de esos ocho fallan por lo mismo las tres veces: es el estado del bot, no ruido.
- **Siempre pasan (2):** saludo-variante, super-inyeccion.
- **Oscilan (4):** precio-calefont, horario-sabado, enojo-reclamo, near-miss-lavadora. Son el piso de
  ruido, y con dos corridas ya se veían.

Medias por dimensión con las tres corridas: `grounding` 2.50 (rango 2.00–3.00), `policy` 2.50 (2.00–2.57),
`conversational` 1.50 (1.50–1.71), `escalation` 3.14 (3.14–3.36), `tone` 3.14 (2.93–3.21), `closure` 2.57
(2.43–2.71). La peor dimensión es **`conversational`**, y es la única estable: el bot no conversa, ejecuta.

**Dos defectos del instrumento aparecieron durante la verificación, y los dos están arreglados:**

1. **`compare_runs` comparaba la clave equivocada** (`bad00f1a`). Leía `report["corpus_fingerprint"]`, que
   un reporte escrito nunca tiene —el sello vive en `stamp`—, así que comparaba `None` contra `None` y
   declaraba comparable cualquier par de corridas. `corpus-1`, el primero, "arregló" un gate comparándose
   contra un probe de un escenario que ya estaba descartado. Los tests existentes pasaban porque construyen
   dicts con la clave arriba, que es exactamente por qué no lo cachaban.
2. **El seguro de escenario no medido se usó de verdad.** El primer intento de `corpus-2` perdió
   `super-burst-contradiccion`: el cliente simulado contestó prosa dos veces y el reintento no alcanzó. La
   corrida **siguió con las otras 13**, escribió el reporte, se marcó no citable y salió con `exit 2`. Antes
   de esta sesión eso tiraba la corrida entera. El reporte se borró; el comportamiento queda acá.

**Hallazgo del bot, con evidencia de los dos entornos:** el precio. La mantención de calefont vale 50.000
(mar–oct) y el bot respondió **30.000** —el valor de la *visita técnica*— en dos corridas; en dos probes
aislados y en la tercera corrida respondió 50.000. El tarifario de la base de test y el del harness son
idénticos, así que no es un artefacto del entorno: es una confusión inestable entre dos servicios del mismo
catálogo. El juez lo marcó hard fail con `grounding` 0 en las tres repeticiones.

**Riesgo medido y anotado:** el simulador perdió un escenario en una de cuatro corridas, y siempre en el
mismo lugar —los escenarios donde el cliente simulado tiene que escribir un mensaje largo y contradictorio—.
Si se repite, el cambio que sigue no es del corpus: es un contrato de salida más corto para el simulador o un
tercer intento.

Verificación observada: `uv run pytest tests/unit/test_conv_eval.py` **128/128** y el archivo del juez
36/36. `scripts/test.sh shape origin/main` **salió 3**, y no por esta feature: `main` avanzó **39 commits**
(PR #687, limpieza de configuración) mientras corrían las tres corridas, así que el diff contra `main` incluía
`app/models.py`, `app/services/settings.py` y una migración. Consecuencia directa y anotada abajo: el trío
`corpus-*` mide el árbol de `81972cfa`, que ya no es `main`.

### L4 — main se movió mientras medíamos: el trío se rehace sobre el árbol entregado (2026-10-26)

Al cerrar la verificación, `git fetch` mostró que `origin/main` estaba 39 commits adelante (`f84a4f00`, PR
#687): limpieza de configuración —claves muertas de `chat.conduct`, defaults de mensajes desde una sola
fuente, refactors del panel—. Nada de eso cambia el bot que estos escenarios miden, pero **el sello del trío
apunta a `81972cfa`, y una línea base que no es el árbol que se entrega no es una línea base**.

Decisiones, en orden:

- Se mergeó `main` en la rama (`d9d3ade6`) y se corrió `full`, que la política del repo exige al mergear.
- El trío `corpus-1/2/3` **no se entrega**: se conserva en el Log como medición del árbol anterior y se
  rehace sobre el árbol mergeado, con tags nuevos.
- Los números del trío viejo (3/5/6, mediana 5, ocho escenarios que nunca pasan y cuatro que oscilan) quedan
  como referencia de varianza, no como la línea base.

Esto no es un defecto del instrumento: es el instrumento diciendo la verdad sobre lo que midió. La lección
operativa, para el handoff: **antes de cada serie de corridas, `git fetch` y mirar si `main` se movió.**

### L5 — la línea base del árbol entregado: mediana 7 de 14, y seis escenarios que nunca pasan (2026-10-26)

Tres corridas citables sobre el árbol mergeado (`737d644a`), todas con árbol limpio y **14 de 14 escenarios
medidos**, sin escenarios no medidos y sin veredictos faltantes:

| Corrida | Commit | Pasan | Hard fails del juez |
|---|---|---|---|
| `main-1` | `646ae781` | 7/14 | 4 |
| `main-2` | `d460411c` | 7/14 | 5 |
| `main-3` | `6ad36086` | 5/14 | 5 |

**Mediana: 7 de 14.** Y esta vez el total se sostiene mejor que en el árbol anterior (`corpus-*`: 3, 5, 6),
pero la composición sigue moviéndose. Por escenario:

| Escenario | m1 | m2 | m3 |
|---|---|---|---|
| `simple-saludo-variante` | ✓ | ✓ | ✓ |
| `simple-precio-calefont` | ✓ | ✓ | ✓ |
| `super-enojo-reclamo` | ✓ | ✓ | ✓ |
| `super-inyeccion` | ✓ | ✓ | ✓ |
| `super-near-miss-lavadora` | ✓ | ✓ | ✓ |
| `simple-horario-sabado` | ✓ | ✓ | ✗ |
| `complejo-fuera-de-cobertura-insiste` | ✓ | ✗ | ✗ |
| `super-burst-contradiccion` | ✗ | ✓ | ✗ |
| `simple-cobertura-comuna` | ✗ | ✗ | ✗ |
| `simple-despedida` | ✗ | ✗ | ✗ |
| `complejo-agendar-calefont` | ✗ | ✗ | ✗ |
| `complejo-dos-temas` | ✗ | ✗ | ✗ |
| `complejo-no-quiere-email` | ✗ | ✗ | ✗ |
| `super-emergencia-gas` | ✗ | ✗ | ✗ |

**5 pasan siempre · 6 nunca pasan · 3 oscilan.** Los seis que nunca pasan son el estado del bot, no ruido:

1. **`simple-cobertura-comuna`** — G9: la respuesta está en la KB y el bot ofrece `kb_miss`.
2. **`simple-despedida`** — hard fail: contesta la despedida con otra pregunta comercial.
3. **`complejo-agendar-calefont`** — hard fail: pide todos los datos antes de responder lo que se preguntó.
4. **`complejo-dos-temas`** — G6 + G9: pierde el referente y nunca dice la garantía.
5. **`complejo-no-quiere-email`** — hard fail: insiste en el correo que la clienta rechazó.
6. **`super-emergencia-gas`** — G3: termina en `human` sin registrar el evento `escalation`.

Medias por dimensión (mediana de las tres corridas, con el rango entre corridas): `grounding` 2.79
(2.79–2.79), `policy` 2.43 (2.36–2.71), `conversational` **1.79** (1.64–1.86), `escalation` 3.14
(3.14–3.29), `tone` 3.14 (3.14–3.36), `closure` 2.64 (2.50–2.71). La peor es `conversational` y es la más
estable: el bot responde, pero no conversa.

**Sobre el precio, con cuidado:** en este árbol `simple-precio-calefont` pasó las tres corridas y `grounding`
dio el mismo valor en las tres, mientras en el árbol anterior falló dos de tres cotizando 30.000 en vez de
50.000. Lo revisé: la limpieza de configuración de #687 toca `chat.conduct.redaccion`, no el tarifario, así
que **no hay evidencia de que el precio se haya arreglado** — una respuesta estocástica que acierta tres
veces seguidas después de fallar dos no es una corrección, es exactamente por qué el baseline son tres
corridas. El escenario sigue siendo el que hay que mirar primero.

Verificación al cerrar: `uv run pytest tests/unit/test_conv_eval.py` **128/128**, el archivo del juez
**36/36**, `scripts/test.sh quick` exit 0, `scripts/test.sh shape origin/main` exit 0 y
`scripts/test.sh full` exit 0 sobre este árbol de código (5m38s, tras mergear los 39 commits de `main`).
Los commits posteriores al `full` solo agregan reportes generados y este documento.
