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
| T1 | E0 | `scripts/seed_kb_docs.py` + preflight de KB | `feat(conv-eval): seed customer KB and refuse to run without it` |
| T2 | E1 | `scripts/conv_eval_corpus.yaml` (13 escenarios) + validador | `feat(conv-eval): conversation corpus with three difficulty tiers` |
| T3 | E2 | runner scripted sobre `run_conversation` | `feat(conv-eval): run scripted conversations against the real brain` |
| T4 | E3 | gates deterministas + reporte JSON/MD + diff + sello | `feat(conv-eval): deterministic gates, report and run diff` |
| T5 | E4 | juez LLM por rúbrica con hard-fail caps | `feat(conv-eval): rubric judge with evidence and hard-fail caps` |
| T6 | E5 | modo `--live` con cliente simulado | `feat(conv-eval): simulated customer mode` |
| T7 | — | corrida baseline sobre `e354f563` | `docs(conv-eval): baseline report on main` |

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
