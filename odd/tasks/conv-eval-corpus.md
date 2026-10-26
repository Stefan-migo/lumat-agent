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
| T6 | S6 | tres corridas `--live` del corpus nuevo y su evidencia | inline | — |

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
