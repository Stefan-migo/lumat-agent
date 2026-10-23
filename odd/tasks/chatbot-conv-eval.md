# ODD — chatbot-conv-eval

Instrumento de evaluación conversacional del cerebro del chat: un corpus versionado de conversaciones
tipo cliente, un runner que las corre contra `run_conversation` sin canal, y una evaluación en dos
capas (gates deterministas + juez LLM por rúbrica) que produce un reporte comparable entre versiones.

- Branch: `odd/chatbot-conv-eval` · Base: `e354f563` (main) · Worktree: `../lumat-agent-odd-chatbot-conv-eval`
- Runner: `uv run pytest tests/unit/test_conv_eval.py` (schema y matemática de scoring, sin LLM)
- Corridas: `uv run python scripts/conv_eval.py` (fuera de pytest, con modelo real)

## Specs

### S1 · Corpus mínimo

> "la automatizacion seria crear al menos 10 conversaciones tipo. para testear lo que el chatbot responde."

El corpus tiene **14** escenarios. Un escenario es reproducible: mismos turnos scripted, mismo teléfono
derivado, misma semilla de limpieza.

### S2 · Temas del producto

> "conversaciones tipo cliente obvio. con diferentes saludos, con agendamientos, con consultas, todas
> relacionadas y posibles conversaciones de lumat."

Cada escenario cubre un saludo distinto (incluye "hola buenas", "alo", con y sin tilde), un
agendamiento, o una consulta que se responde desde la KB o el tarifario. Nada fuera de los servicios
de Lumat salvo el caso near-miss, que es deliberado.

### S3 · Tres niveles de dificultad

> "podemos crear conversaciones simples, complejas y supercomplejas."

El tier mide **dificultad de la demanda, no largo del guion** (decisión del owner, L5). Los conteos de
abajo son los que el corpus realmente tiene, medidos:

- `simple` (5 casos, **1–2 turnos**): un solo intent, respuesta directa. Es el piso: si esto falla, el
  problema es el núcleo, no la conversación.
- `complejo` (4 casos, **2–5 turnos**): dos temas en el mismo hilo, o datos que el bot tiene que
  pedir, o una negativa del cliente que obliga a un segundo camino.
- `supercomplejo` (5 casos, **1–4 turnos**): pocos turnos, pero cada uno carga una trampa que no se
  resuelve con más texto — emergencia y precio en el mismo mensaje, enojo con amenaza de reseña,
  inyección de instrucciones, contradicción dentro de un burst, y near-miss de vocabulario.

Consecuencia deliberada: la corrida dura minutos, no una hora, y el instrumento se puede usar en
cada cambio. Lo que se pierde es medir persistencia en conversaciones largas; si eso pasa a importar,
se agregan escenarios `supercomplejo` largos, no se estira este corpus.

### S4 · Evaluación real del estado, orientada a mejorar

> "para hacer una evaluacion real del estado el chatbot y poder entender que necesitamos mejorar."

La evaluación separa lo que el bot **hizo** (gates deterministas, gratis, sin LLM) de lo que
**respondió** (juez por rúbrica). Un gate duro fallido no se compensa con puntaje alto del juez.

### S5 · Automatización dev, sin frontend, mismo harness

> "esta es una automatizacion dev. no es necesario que tenga frontend. es lo mismo que el harness."

Sin cambios en `app/` y sin pantalla nueva: `scripts/` + reporte en `odd/evals/`. Mismo seam que el
harness, `run_conversation`.

### S6 · Decisiones de diseño del owner (2026-10-23)

> "1. si doy mi consentimiento. 2. si para el cliente simulado y el juez esta perfecto."

- Cliente: **scripted en YAML por defecto**, simulado por LLM con `--live`.
- Corpus: lo escribe el agente desde la KB y el tarifario; **el owner corrige** antes de usarlo como
  línea base.
- Evaluación: **gates deterministas + juez LLM** por rúbrica 0–4 por dimensión.
- Salida: **JSON + reporte Markdown** en `odd/evals/`, con **diff contra la corrida anterior**.

### S7 · Modelos del cliente simulado y del juez

> "vamos a utilizar deepseek flash v4.1 opencode go."

Cliente simulado y juez usan `deepseek-v4.1-flash` vía `https://opencode.ai/inference/go/v1`
(protocolo OpenAI chat-completions). El **bot bajo prueba no cambia**: corre con su
`CHAT_PROVIDER`/`CHAT_MODEL` configurados (`deepseek-flash` en el harness).

Riesgo aceptado y registrado: el juez comparte familia con el bot. Mitigación: la rúbrica exige
evidencia citada por dimensión, los hard-fails son deterministas y no negociables, y la calibración
contra lectura humana es parte de E4 (S9).

### S8 · Trampas que el instrumento no puede permitir

> "respecto a las trampas puedes asegurarte que no caigamos en esas trampas?"

No se asegura por disciplina, se asegura por construcción:

1. **KB ausente o desactualizada** → preflight obligatorio: cuenta `kb_documents` con
   `visibility='customer'` y compara el hash del contenido contra `docs/kb/*.md`. Si no cuadra,
   **aborta**. `scripts/seed_kb_docs.py` carga la KB en cualquier stack nuevo, idempotente.
2. **Estado sucio / memoria por cliente** → el teléfono se deriva de `sha256(id:run_tag)`, así que
   cada corrida estrena cliente por construcción. No se borra nada.
3. **No determinismo en CI** → los LLM viven en `scripts/`; en `pytest` solo entran el schema y la
   matemática de scoring.
4. **Contención que premia inventar** → piso de cero daño como gate duro.
5. **Confundir cerebro con canal** → el webhook, el dedup, la ventana de 24 h y las plantillas quedan
   fuera de alcance, y el reporte lo declara en su encabezado.
6. **Medir un árbol a medio editar** → el reporte estampa `git rev-parse HEAD` y el flag `dirty`; una
   corrida sobre árbol sucio se marca **no citable como baseline**.

### S9 · Calibración del juez

Antes de usar los puntajes para decidir, el owner puntúa 3 conversaciones a mano y se compara. Si el
juez discrepa sistemáticamente, se ajusta la rúbrica; el juez es apoyo, no veredicto.

## Non-goals

- No toca `app/`: no agrega ningún seam de producción.
- No reemplaza `tests/integration/test_chatbot_cerebro_qa.py` (T01–T12): esa suite asserta con
  classifier mockeado; esta mide con el modelo real.
- No corre en CI. No es determinista y no debe bloquear un merge.
- No prueba el webhook, el dedup, la ventana de 24 h ni las plantillas de Meta.
- No decide delivery: produce evidencia.

## Tasks

| # | Slice | Qué entrega | Commit |
|---|---|---|---|
| T1 | E0 | `scripts/seed_kb_docs.py` + preflight de KB | `62166951` (+`64ba173a`) |
| T2 | E1 | `scripts/conv_eval_corpus.yaml` (14 escenarios) + validador | `580b8f2b` + `dcfe57aa` |
| T3 | E2 | runner scripted sobre `run_conversation` | `b98719c8` |
| T4 | E3 | gates deterministas + reporte JSON/MD + diff + sello | `dcfe57aa` + `b98719c8` |
| T5 | E4 | juez LLM por rúbrica con hard-fail caps | `d55a203d` (+`0bab2a53`) |
| T6 | E5 | modo `--live` con cliente simulado | `b98719c8` (cableado; falta ejercitarlo) |
| T7 | — | corrida baseline sobre `e354f563` | pendiente de la corrida |

## Log

### L1 — pedido original (verbatim)

> hey chat sigo trabajando en la configuracion del chat bot. he realizado varios cambios y estoy
> cercano a testear. quiero testear primero en el harness de forma local.
>
> entonces pienso si es posible crear una automatizacion, esta es una automatizacion dev. no es
> necesario que tenga frontend. es lo mismo que el harness.
>
> la automatizacion seria crear al menos 10 conversaciones tipo. para testear lo que el chatbot
> responde.
>
> conversaciones tipo cliente obvio. con diferentes saludos, con agendamientos, con consultas, todas
> relacionadas y posibles conversaciones de lumat.
>
> asi no tener que yo inventar cada vez una conversacion al pedido. y podemos crear conversaciones
> simples, complejas y supercomplejas. para hacer una evaluacion real del estado el chatbot y poder
> entender que necesitamos mejorar. par alograr mejores respuestas y rendimiento del chatbot?
>
> necesito que investigues eso. que busques en internet tambien. como se configuran hoy chatbots de
> whatsapp funcionales y eficientes.

### L2 — decisiones de diseño (2026-10-23)

> 1. ¿Cómo se genera el lado cliente? → **Ambos: scripted por defecto, simulado con `--live`**
> 2. ¿Quién escribe el corpus? → **Las escribo yo desde la KB, vos corregís**
> 3. ¿Evaluación? → **Gates deterministas + juez LLM**
> 4. ¿Salida? → **JSON + reporte MD en odd/, diff vs corrida previa**

### L3 — consentimiento y modelos (2026-10-23)

> "1. si doy mi consentimiento. 2. si para el cliente simulado y el juez esta perfecto. vamos a
> utilizar deepseek flash v4.1 opencode go."

Worktree autorizado: `../lumat-agent-odd-chatbot-conv-eval`, branch `odd/chatbot-conv-eval`.

### L4 — estado del entorno al arrancar (medido, no inferido)

- `lumat-harness-db-1` (5433) tiene las 4 filas `kb_documents` con `visibility=customer` y 22 chunks.
- Tarifario vigente en ese stack: visita técnica 30.000 · mantención calefont 50.000 · mantención
  caldera 80.000 · lavado de red 140.000 (mes 10 ⇒ tramo mar–oct). El corpus **no** hardcodea montos:
  el juez recibe el tarifario en vigor.
- Otro agente trabaja en `/home/stefan/repos/lumat-agent-odd-chatbot-experiencia`
  (`odd/chatbot-experiencia`, base `e354f563`). Por eso el baseline se corre sobre el SHA, no sobre
  "main".

### L5 — el corpus no se estira, se corrige la spec (2026-10-23)

> "lo dejamos como esta corrige S1 y S3"

Decisión del owner tras la recuperación del worktree: el corpus queda con los 14 escenarios que ya
tiene, y S1/S3 se reescriben para describir lo que hay en vez de al revés. S3 deja de prometer
`supercomplejo` de 9+ turnos: el tier mide la trampa, no el largo del guion. Si algún día importa medir
persistencia en hilos largos, se agregan escenarios nuevos a ese tier en vez de alargar los actuales.

### L6 — slice de recuperación y estrategia de entrega (2026-10-23)

Tras el crash, los tres primeros commits recuperan lo que ya estaba escrito en disco como las
unidades que este plan preveía, sin agregar comportamiento nuevo: `b21f5b4d` (este doc),
`62166951` (`seed_kb_docs.py`, T1) y `580b8f2b` (`conv_eval_corpus.yaml`, T2). Slice acumulado
medido: **796 líneas autoradas** en 3 commits.

Estrategia de entrega, decidida acá porque el acumulado pasa la guía de ~400 líneas: **una sola
rama y review commit por commit**. Si el owner prefiere PRs encadenados, el corte natural es
(a) el instrumento que no corre todavía — doc, seed, corpus, juez y matemática de gates — y
(b) el runner, el reporte y la primera corrida. La decisión de PR y merge sigue siendo del owner.

### L7 — primera corrida real (`--live`, 2026-10-23) y lo que rompió

Corrida completa sobre los 14 escenarios con cliente simulado y juez: **8/14 pasan**. Gates que
fallaron: `G6`×3, `G4`×1, `G3`×1, `G1`×1. Dimensiones del juez (media): grounding 2,71 · policy 3,07 ·
conversational **1,50** · escalation 2,29 · tone 2,71 · closure 2,07. Por tier: simple 3/5,
complejo 2/4, supercomplejo 3/5. Reporte en `odd/evals/conv-eval-live-baseline-2.{json,md}`.

Los seis rojos, con la razón medida:

| Escenario | Qué pasó |
|---|---|
| `simple-horario-sabado` | G6: ignoró la pregunta del sábado y se fue por el camino de diagnóstico ("¿no enciende, no calienta…?"). |
| `simple-despedida` | G4 + hard fail: contó la despedida como `unknown_intent` y contestó con una pregunta comercial. |
| `complejo-dos-temas` | G6 + hard fail: perdió el referente del servicio y nunca respondió la garantía del lavado de red. |
| `complejo-no-quiere-email` | hard fail: insistió con el correo que el cliente rechazó, sin pedir el teléfono que sí ofreció. |
| `super-emergencia-gas` | G3: nunca registró el evento `escalation`, aunque el protocolo de emergencia sí se disparó. |
| `super-burst-contradiccion` | G1 + G6: terminó en `human` (el corpus espera `bot`) y nunca nombró la caldera corregida. |

Cuatro defectos del instrumento aparecieron al usarlo, y quedaron corregidos con test:

1. **Veredicto truncado** del juez abortaba la corrida entera → un reintento y, si vuelve a fallar,
   el escenario queda "sin veredicto" (nunca como puntaje) y la corrida sigue (`fb5220fe`).
2. **`kb_miss` blando invisible**: producción registra `kb_miss` solo cuando escala. Una respuesta con
   la oferta de `kb_miss_offer` no deja evento, así que G9 daba verde falso sobre una pregunta que la
   KB sí responde. G9 ahora lee el texto configurado (`8a3a0767`).
3. **Evidencia del juez perdida**: el reporte guardaba el puntaje y tiraba la cita por dimensión, que
   es justo lo que S9 calibra. Ahora viaja con la fila.
4. **Sin visibilidad** de una corrida larga (stdout en buffer) → progreso por escenario con `flush`.

Hallazgos de entorno, registrados y no corregidos acá (`app/` es non-goal):

- La emergencia dispara la notificación real: Meta responde 401 con los placeholders del entorno y el
  fallback de email revienta contra el SMTP ausente. El cerebro lo absorbe y sigue, pero
  `_send_email_fallback` **puede lanzar** pese al contrato documentado "never raises"
  (`app/chat/nodes/emergency.py:94`). Follow-up para `app/`, no para este instrumento.
- Reusar un `--run-tag` reusa el mismo cliente por diseño (S8.2), así que una corrida interrumpida
  necesita tag nuevo o mide la memoria de la anterior.
- Esta corrida selló `dirty: true` (un commit se cruzó con el arranque), así que **no es citable como
  baseline**: el baseline citable es una corrida nueva sobre árbol limpio.

Calibración S9 abierta: `odd/evals/calibracion-s9.md` trae tres conversaciones (un 4,00, un 2,50 y un
1,67) con el puntaje del juez plegado, para que el owner puntúe a mano sin verlo.

### L8 — el instrumento mintió una vez, y eso valió más que el número (2026-10-23)

El baseline scripted salió **5/14** con sello limpio (`aaa3e767`), y era **inválido**. La prueba:
`complejo-agendar-calefont` es un escenario de 5 turnos y su conversación tenía **20 mensajes**. La
corrida que mató el SIGTERM dejó sus filas en la base, y la repetición con el mismo `--run-tag` reusó
los mismos clientes y replayó los turnos **encima de conversaciones que ya habían escalado a `human`**.
De ahí los 4 `G1`, los 4 `G4` y los 10 `handoff:cobertura`: era la corrida anterior hablando.

Consecuencia para el plan de comparar versiones del bot: un crash a mitad de corrida habría hecho
concluir "empeoró" con datos que nunca midieron al bot. Tres arreglos, todos con test:

1. **`079a1129` — un tag con clientes existentes se rechaza** (`exit 2`, stderr con la lista de
   escenarios contaminados). Verificado corriéndolo.
2. **`--reset` con guarda**: vacía solo estado de conversación (clientes, conversaciones, mensajes,
   eventos, casos, memorias, visitas, notificaciones) y **solo** si `DATABASE_URL` coincide en
   host:puerto con `TEST_ADMIN_DB_URL`. Verificado en las dos direcciones: con la base de test pasa,
   con una base distinta se niega y la base queda intacta (49 conversaciones).
3. **El .md es el registro completo**: el transcript sale del **log de mensajes** de la base, no de los
   turnos, así que una respuesta que el grafo no devolvió también queda. Antes de truncar nada se
   reconstruyeron desde la base los tres transcripts existentes: 75 mensajes (`live-baseline-2`),
   110 (`baseline`, contaminado) y el de `baseline-2`.

Primera repetición limpia (`baseline-2`, teléfonos frescos, sin reset): **6/14**, gates `G6`×3,
`G9`×2, `G4`×2, `G1`×2, `G3`×1. Notablemente mejor que el contaminado, que es la confirmación del
diagnóstico: `complejo-agendar-calefont` pasa (3,33) cuando la conversación no arrastra el estado de la
corrida anterior.

Pendiente de medir: el **piso de ruido**. Dos corridas idénticas sobre estado limpio (`clean-1` y
`clean-2`, ambas con `--reset`) y el diff entre ellas: todo escenario que cambie de verde a rojo sin
tocar una línea de código es ruido del instrumento, y ese número hay que descontarlo antes de
atribuirle nada a las mejoras del otro worktree.

### L9 — el piso de ruido del instrumento, medido (2026-10-23)

Dos corridas idénticas, mismo código (`6cf76f59`), mismo corpus, **`--reset` antes de cada una** para
que el estado inicial sea el mismo: `clean-1` y `clean-2`.

| | clean-1 | clean-2 |
|---|---|---|
| Pasan | **5/14** | **6/14** |
| Gates que fallan | G6×4, G9×3, G4×3, G1×3, G3×1 | G6×3, G9×2, G4×2, G1×2, G3×1 |

**El piso de ruido es 1 escenario de 14 (~7%)**, más un gate suelto en un segundo escenario:

- `complejo-agendar-calefont`: **falla → pasa**, con tres gates moviéndose juntos (G1, G4, G6). En
  `clean-1` el bot escaló a `human`; en `clean-2` no. Un solo comportamiento distinto arrastra los
  tres gates.
- `complejo-fuera-de-cobertura-insiste`: G9 falla → pasa, sin cambiar el resultado final del escenario.
- Delta de dimensiones entre corridas: entre **+0,14 y +0,36** en las seis, siempre a favor de la
  segunda. Chico, pero del mismo orden que las diferencias que se quieren atribuir a una mejora.

Causa: los gates son deterministas, pero **sus insumos no**. El clasificador y el extractor son
llamadas al LLM, así que la misma frase puede clasificar distinto entre corridas y mover el estado, la
escalación y el enrutamiento.

Consecuencia operativa para el plan de comparar versiones del bot:

1. Una diferencia de **1 escenario está dentro del ruido**: no autoriza decir "mejoró" ni "empeoró".
2. Para atribuir algo a una versión hay que correr **N=3 por versión** y comparar la tasa, o exigir
   que la diferencia supere el piso medido (≥2 escenarios, y que el gate movido sea el mismo).
3. `complejo-agendar-calefont` es el escenario más inestable medido hasta ahora: es el primero a
   repetir cuando aparezca una diferencia.
