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

- Cliente: **scripted en YAML por defecto**, simulado por LLM con `--live`. Los turnos scripted son
  la **apertura**: en `--live` el simulador tiene además `SIMULATED_TURNS` turnos de margen, salvo que
  el escenario declare un techo (`max_turns`), y para en cuanto reporta `goal_reached` (mecanismo y
  medición en L12).
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
juez discrepa sistemáticamente, se ajusta la rúbrica; el juez es apoyo, no veredicto. **Primera
calibración hecha: ver L13** — dos dimensiones se corrigieron por defecto (insumo faltante y ancla
ausente), no por corrimiento de escala.

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
| T1 | E0 | `scripts/seed_kb_docs.py` + preflight de KB | `3fabe88a` (+`20a40d17`) |
| T2 | E1 | `scripts/conv_eval_corpus.yaml` (14 escenarios) + validador | `156a0884` + `aa870cc4` |
| T3 | E2 | runner scripted sobre `run_conversation` | `e1f87914` |
| T4 | E3 | gates deterministas + reporte JSON/MD + diff + sello | `aa870cc4` + `e1f87914` |
| T5 | E4 | juez LLM por rúbrica con hard-fail caps | `efffdf2c` (+`70b7c531`) |
| T6 | E5 | modo `--live` con cliente simulado | `e1f87914` (cableado; falta ejercitarlo) |
| T7 | — | corridas live y scripted sobre la rama, y medición del piso de ruido | `d585f384` + `01084054` |
| T8 | E5 | presupuesto de turnos del cliente simulado: margen por defecto, techo declarado y la excepción deliberada | este PR |
| T9 | E5 | reintento del cliente simulado: prosa no es un turno (defecto #9) | `dd86925d` |

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
unidades que este plan preveía, sin agregar comportamiento nuevo: `c1504067` (este doc),
`3fabe88a` (`seed_kb_docs.py`, T1) y `156a0884` (`conv_eval_corpus.yaml`, T2). Slice acumulado
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
   KB sí responde. G9 ahora lee el texto configurado (`1c5d2c46`).
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

El baseline scripted salió **5/14** con sello limpio (`d585f384`), y era **inválido**. La prueba:
`complejo-agendar-calefont` es un escenario de 5 turnos y su conversación tenía **20 mensajes**. La
corrida que mató el SIGTERM dejó sus filas en la base, y la repetición con el mismo `--run-tag` reusó
los mismos clientes y replayó los turnos **encima de conversaciones que ya habían escalado a `human`**.
De ahí los 4 `G1`, los 4 `G4` y los 10 `handoff:cobertura`: era la corrida anterior hablando.

Consecuencia para el plan de comparar versiones del bot: un crash a mitad de corrida habría hecho
concluir "empeoró" con datos que nunca midieron al bot. Tres arreglos, todos con test:

1. **`8e7f9a5d` — un tag con clientes existentes se rechaza** (`exit 2`, stderr con la lista de
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

Dos corridas idénticas, mismo código (`caf0109e`), mismo corpus, **`--reset` antes de cada una** para
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

### L10 — alineación con main, corte de entrega y política de `odd/evals` (2026-10-23)

`origin/main` entró a la rama sin conflictos (`606138ca`, sobre `94e6921c`): la rama **solo agrega
archivos**, no modifica ninguno existente. Entraron la política de tiers (`AGENTS.md` → "Test tiers"),
`scripts/test.sh`, `openspec/config.yaml` y el aislamiento de `MEDIA_DIR` en `tests/conftest.py`.
Verificación de ese merge: `bash scripts/test.sh full` → **exit 0** y
`bash scripts/test.sh shape origin/main` → **exit 0**. Regla operativa nueva que afecta a este
instrumento: **una suite por worktree** — las corridas de `conv_eval.py` y `pytest` comparten la base
de test derivada y se bloquean en el `TRUNCATE`, así que van serializadas.

**Entrega: tres PRs encadenados, decidido.** Un PR de 25 commits no se revisa. El corte se midió sobre
la rama ya limpia de JSON (L11); las líneas son las del diff de tres puntos, que es el que muestra el
PR:

| PR | Contenido | Commits | Diff |
|---|---|---|---|
| 1 · instrumento que todavía no corre | doc, seed de KB, corpus, juez, gates y scoring, con sus tests | 8, hasta `70b7c531` | 8 archivos, 2.575 |
| 2 · runner y reporte | runner scripted, reporte JSON/MD, diff y sello, más los tres defectos que la primera corrida destapó | 5, hasta `9a7319f8` | 4 archivos, 951 (+17) |
| 3 · robustez y evidencia | transcripts, guarda de `--run-tag`, `--reset` admin, sello limpio, artefactos y docs | 13 | 15 archivos, 2.154 (+21) |

Ninguno de los tres entra en la guía de ~400 líneas, y no hay un corte más fino que no separe un
script de sus tests: de las ~5,5k líneas del diff neto, ~2,2k son los tres scripts, ~1,2k sus tests,
370 el corpus y ~1,3k la evidencia Markdown. Se entrega este corte con `size:exception` y el número
medido, antes que romper la cohesión código↔test.

**`odd/evals/`: decidido.** El `.md` — reporte y transcripción de conversaciones — es el registro
permanente: con `--reset` la base se vacía, pero el transcript se reconstruye del log de mensajes. El
JSON de 40–70 KB solo alimenta el diff contra la corrida anterior, así que **no se commitea** y queda
ignorado por `.gitignore` (`05bc719a`). `conv-eval-baseline.*` se borra: es la corrida contaminada de
L8 y no debe viajar en el PR.

`origin/main` volvió a avanzar mientras se armaba la entrega (`497875af`, PRs #668 y #669 del worktree
`chatbot-oferta`), así que la rama se realineó otra vez antes de abrir nada — primero con un merge, y
después con un **rebase sobre `origin/main`**. El rebase no es cosmético: con el merge adentro del
tercer PR, su diff arrastraba 33 archivos con medio `main`; sin él, cada slice muestra solo lo suyo.
El diff neto contra `main` son 20 archivos — 19 nuevos y `.gitignore` con 4 líneas —, 5.642
inserciones y cero borrados.

### L11 — la evidencia se limpia, y el sello medía los reportes (2026-10-23)

Aplicar la política de `odd/evals` de L10 destapó un séptimo defecto, y era el que invalidaba la
evidencia que se estaba por entregar: **el sello medía los reportes, no el código**.

`git_state()` decidía `dirty` con un `git status --porcelain` sobre todo el repo. El sello se toma
*antes* de escribir el reporte, así que una corrida no se ensuciaba a sí misma: la ensuciaba **la
corrida anterior**. Medido en los reportes ya commiteados: `baseline`, la primera del día, selló
`dirty: no`; `baseline-2`, `live-baseline-2`, `clean-1` y `clean-2` sellaron `dirty: sí` por el JSON y
el `.md` que había dejado la anterior. Como S8.6 hace no citable una corrida sucia, **ninguna de las
corridas que se iban a commitear servía como baseline**, y commitear los `.md` —justo la política de
L10— habría garantizado que ninguna futura tampoco: cada corrida reescribe archivos trackeados.

Arreglado antes de commitear la evidencia (`dd5dcf91`): el sello excluye el directorio de reporte,
resuelto contra el árbol medido, así que un `--out-dir` fuera del repo no excluye nada. Cuatro tests lo
fijan: un reporte sin trackear y un reporte commiteado que una corrida nueva reescribe dejan el árbol
limpio; una edición en `app/` y un archivo sin trackear fuera del reporte lo siguen ensuciando. El
primer run posterior a este arreglo es el primer baseline citable.

Sobre la evidencia, con las dos decisiones de L10 aplicadas:

- Se reescribió la historia de la rama (nada estaba pusheado) para que los JSON **nunca entren**:
  salieron 7.358 líneas de `odd/evals/` de los cuatro commits que los agregaban. El árbol fuera de
  `odd/evals/` quedó **idéntico** al anterior, verificado con `git diff` contra el tip previo.
- Se borró `conv-eval-baseline.*` (la corrida contaminada de L8). Quedan el reporte y la transcripción
  de `baseline-2`, `live-baseline-2` y las dos `clean-*`, más la planilla de calibración.
- `odd/evals/*.json` quedó en `.gitignore` (`05bc719a`), fuera del bloque administrado por rapso.
- La historia se reescribió **dos veces**: primero para sacar los JSON, después un rebase sobre
  `origin/main` para que cada PR encadenado muestre solo su slice (con el merge de main adentro del
  tercer PR, su diff se llevaba medio `main`). La segunda reescritura cambió **todos** los SHA, así
  que la tabla de Tasks cita los vigentes.
- Los sellos que los `.md` ya commiteados imprimen (`3cd0406a`, `6cf76f59`, `fb5220fe`) apuntan a la
  historia previa a las reescrituras, preservada en la rama local `backup/pre-evals-cleanup`. El
  código medido es bit a bit el mismo: el árbol del tip no cambió en ninguna de las dos
  reescrituras. Equivalencias vigentes: `3cd0406a`→`4a4df426`, `6cf76f59`→`caf0109e`,
  `fb5220fe`→`de48307e`. Los sellos se dejan como están: reescribirlos sería falsificar el reporte.

### L12 — el cliente simulado vuelve a tener turnos (2026-10-23)

> "ok puedes hacerte cargo de 1."

En el cierre de la entrega ese "1" era el trabajo pendiente #2: darle espacio al cliente simulado, que
sin turnos no actúa como cliente.

El defecto cabía en una línea. `max_turns` se resolvía en el parser como
`entry.get("max_turns", len(turns))`, y `plan_turns` llena el presupuesto primero con los turnos
scripted y solo después, bajo `--live`, con turnos simulados. Con el presupuesto igual al largo del
guion, la rama simulada era **inalcanzable**: 10 de los 14 escenarios no dejaban hablar al simulador ni
una vez (9 por el default y el saludo), y los otros 4 declaraban `turns + 1`, o sea exactamente un
turno. La planilla S9 lo dejaba ver: en `super-enojo-reclamo` el único turno con la amenaza de reseña lo
escribió el LLM, porque ese escenario era uno de los cuatro con techo declarado.

Arreglo (`resolve_budget`, T8): manda el `--max-turns` explícito; después el techo que declare el
escenario; si no declara nada, un run scripted corta en su guion y uno `--live` suma
`SIMULATED_TURNS = 3`. Es un **techo, no un objetivo** — el simulador reporta `goal_reached` y la
corrida termina ahí, así que el margen no alarga un escenario corto.

Consecuencias medidas, y deliberadas:

- **13 de 14 escenarios planean 3 turnos simulados.** `simple-saludo-variante` queda en 0 con techo
  declarado 1: su objetivo se cumple en el saludo y seguir midiendo persistencia es lo que S3 y L5
  dejaron fuera del corpus. Es la única excepción y un test la nombra.
- **Las corridas scripted no cambian en nada**: `plan_turns` corta en el guion y un test fija el plan
  exacto de los 14. El margen existe solo en `--live`.
- Se sacaron los cuatro `max_turns: turns + 1` que quedaban: eran el parche del default viejo y, con
  el arreglo, dejaban a esos escenarios con **menos** margen que los que no declaraban nada.
- El `corpus_fingerprint` cambia, y `compare_runs` ya marca no comparable un diff contra otro corpus:
  `live-baseline-2` no se puede comparar contra una corrida nueva, y el reporte lo dice.

El otro punto del pendiente —"que no escriba como el bot"— ya estaba cubierto por construcción:
`_SIMULATOR_INSTRUCTIONS` abre con "You are NOT the assistant and you never write as one". No tenía
test; ahora tiene dos, que fijan ese guard y el corte por `goal_reached`.

### L13 — la calibración, hecha: dos dimensiones no eran offset, eran dos defectos (2026-10-23)

> "ya los puntajes esta hechos 'odd/evals/calibracion-s9.md'"

El owner puntuó las tres conversaciones a mano antes de abrir el puntaje del juez. Cada celda es
`owner / juez`:

| Dimensión | simple | complejo | super | Owner | Juez | Delta |
|---|---|---|---|---|---|---|
| grounding | 4/4 | 4/4 | 3/3 | 11 | 11 | **0** |
| policy | 4/4 | 4/4 | **1/4** | 9 | 12 | **−3** |
| conversational | 4/4 | 1/1 | 2/0 | 7 | 5 | +2 |
| escalation | 4/4 | 4/2 | **4/0** | 12 | 6 | **+6** |
| tone | 4/4 | 3/3 | 3/2 | 10 | 9 | +1 |
| closure | 4/4 | 1/1 | 2/1 | 7 | 6 | +1 |

12 de las 18 celdas son exactas. `grounding` coincide en las tres; `tone` y `closure` desvían ±1 una
vez cada una, y `conversational` discrepa solo en el caso super, donde **los dos ven la misma
repetición** y difieren en cuánto castigarla. Eso es un juez usable.

Las dos restantes son **inversiones**, no ruido, y tienen causas distintas:

1. **`escalation` (+6): el juez no tenía los datos.** `judge_conversation` recibía rúbrica, persona,
  goal, `hard_fails`, tarifario, KB y el texto de la conversación — nunca el estado final ni los
  eventos. En el caso super la corrida terminó en `human` con **dos** eventos `escalation` y el juez
  puntuó **0**, porque "Un asesor revisará su caso y te contactará a la brevedad" leído como prosa es
  una promesa ambigua; en el complejo, que **no** debía escalar y no escaló, puntuó 2. Le pedíamos
  juzgar un hecho que no podía ver.
2. **`policy` (−3): la rúbrica no cubría reclamos.** Acá los `hard_fails` del escenario **sí** llegaban,
  incluido "Seguir vendiendo un servicio en vez de hacerse cargo del reclamo", y aun así el juez puso
  4 con `hard fail: False`. Las anclas hablaban de precio, IVA, garantía, comuna y fecha; nada sobre
  hacerse cargo de un reclamo ni sobre insistir con el diagnóstico a alguien que ya lo describió.

Correcciones (decisión del owner: las dos):

- **Los hechos persistidos van al juez** (`facts_of` + `_render_facts`): estado final y log de eventos
  como **evidencia**, no como veredicto, con la regla explícita de que un `escalation` registrado o un
  estado `human` significa que el traspaso ocurrió y no se puede afirmar lo contrario. Es la misma
  regla que ya se aplicó a G9 cuando leía el evento en vez del texto.
- **Ancla de reclamo en `policy`** y una regla explícita: un `hard_fail` declarado por el escenario
  obliga a `hard_fail true` y a puntuar 0 la dimensión que rompe, porque `score_scenario` ya capa el
  caso a 0 con ese flag. El miss más caro de la calibración era justamente un hard fail no reportado.

Pendiente de medir: la corrección está fijada por tests del prompt, pero **no se volvieron a juzgar
las tres conversaciones con la rúbrica nueva**. Ese re-juzgue es el paso siguiente y necesita la clave
del proveedor; hasta que se haga, la calibración dice "el juez viejo fallaba en dos dimensiones", no
"el juez nuevo está calibrado".

### L14 — el juez no es estable, así que una llamada no es una medición (2026-10-23)

Después de L13 quedaba una pregunta abierta: ¿la rúbrica nueva arregló las dos dimensiones? Corrí el
re-juzgue de las tres conversaciones de la planilla con la rúbrica nueva, y a la segunda corrida —mismos
transcripts, mismos hechos, mismo prompt— aparecieron puntajes distintos. Eso obligó a medirlo en vez de
interpretarlo.

**Medición:** tres repeticiones idénticas por caso, 18 celdas.

| Caso | Dimensión | Owner | Juez (3 reps) | Dispersión |
|---|---|---|---|---|
| complejo-agendar-calefont | **escalation** | 4 | **[3, 1, 1]** | **2** |
| super-enojo-reclamo | policy | 1 | [0, 1, 0] | 1 |
| super-enojo-reclamo | escalation | 4 | [3, 2, 2] | 1 |
| super-enojo-reclamo | conversational | 2 | [1, 1, 0] | 1 |
| complejo-agendar-calefont | policy / conversational | 4 / 1 | [4,4,3] / [1,1,2] | 1 |
| simple-precio-calefont | tone | 4 | [3, 4, 4] | 1 |
| super-enojo-reclamo | grounding | 3 | [4, 4, 3] | 1 |

**8 de 18 celdas se mueven entre llamadas idénticas**, y el `hard_fail` del caso super osciló
`[True, False, True]`. Como `score_scenario` capa el escenario a 0 con ese flag, **la misma
conversación puntuaba 0 o no según la suerte de la llamada**.

Es el hallazgo de L9 una capa más abajo: no sólo el bot varía, también el instrumento que lo mide. Con
esa varianza, comparar **una** llamada contra el puntaje humano no puede distinguir un defecto de
rúbrica del ruido — los dos primeros re-juzgues que corrí dieron tablas distintas, y cualquiera de las
dos me habría alcanzado para escribir una conclusión falsa.

Lo que sí convergió, y se sostiene en las tres repeticiones: **`policy` del caso super quedó en 0–1
contra el 1 del owner** (el juez viejo daba 4), y **`escalation` dejó de negar el traspaso registrado**
—el caso super ya no da 0 y cita el `handoff:persona`—. Los hechos persistidos de L13 funcionan.

**Decisión del owner:** el juez repite y agrega. `JUDGE_REPETITIONS = 3`, la **mediana** por dimensión es
el puntaje, la **dispersión** viaja en la fila y en el reporte, y el `hard_fail` se decide por
**mayoría**. La lógica de agregado vive en `conv_eval.py` (model-free, con tests); `conv_eval_judge.py`
sigue haciendo una llamada y devolviendo un veredicto. Se puede ajustar por corrida con
`--judge-repetitions`.

Queda sin resolver, y ahora se sabe por qué: **`escalation` del caso complejo**, mediana 1 contra 4 del
owner con dispersión 2. Una diferencia de 3 puntos entre llamadas idénticas no autoriza a decir que la
rúbrica está mal ahí; hay que volver cuando el número estabilice, y si no estabiliza, el problema es la
rúbrica de esa dimensión y no el azar.

### L15 — el baseline no se corrió, y el cliente simulado es la razón (2026-10-26)

Tras L14 quedó cerrado lo del juez: repeticiones con mediana, spread y `hard_fail` por mayoría (#679,
`ce1042f7`), y la re-calibración con ese código dio **11/18 exactas** contra el owner, con `policy` del
caso super ya en 1/1. Después se cerró otra brecha: el sello **no decía qué bot medía** —`deepseek-chat`
es el default del código y `deepseek-flash` lo del harness, y los dos producían reportes idénticos—. Ahora
estampa `bot_provider`/`bot_model` y escribe `judge_repetitions` en el reporte (`0d9c4b6c`).

La clave del bot no está en la base de test: vive en el **entorno del contenedor del harness**
(`lumat-harness-api-1`). Se toma de ahí sin imprimirla y se pasa como `DEEPSEEK_API_KEY`, que es el
fallback de `Settings`. Con eso, un smoke de un escenario (`--only … --no-judge`) pasó 1/1.

**Entonces el baseline falló, y no por el bot.** El cliente simulado devolvió prosa en vez del JSON que
se le pide —un turno de cliente impecable, pero sin sobre— y `_parse_json` reventó:

```
✗ simple-horario-sabado: la corrida falló: no JSON object in verdict:
  'me llamo carlos, la calefaccion no calienta nada. pero lo importante, pueden el sabado?…'
```

Reproducido dos veces con nombres distintos, o sea defecto y no casualidad: **defecto #9, el simulador
no reintenta.** El juez recibió su reintento en `fb5220fe` por este mismo accidente; el simulador quedó
sin él. Y hay una asimetría que lo empeora: un veredicto faltante del juez se registra como "no medido" y
la corrida continúa, pero **un escenario que falla aborta la corrida entera** (`exit 2`, sin reporte), así
que un hipo del simulador tira 14 escenarios.

Dos trampas operativas medidas en este tramo, y las dos cuestan evidencia falsa:

1. **`pytest` vacía `kb_documents`** en la base compartida del worktree. Tras `quick` o `full`, el juez
   ve la KB vacía y `grounding` se cae al piso: la primera re-calibración dio 1 donde el owner puso 4 por
   esto. El runner aborta solo por el preflight, pero un script suelto no. **Re-sembrar después de
   cualquier suite y antes de cada corrida.**
2. **Un `--run-tag` puede pisar evidencia histórica.** El tag `baseline-2` habría sobrescrito
   `conv-eval-baseline-2.md`, commiteado y citado en L8/L9. Los tags del baseline son `citable-1/2/3`
   justamente por eso: antes de elegir uno, mirar qué hay en `odd/evals/`.

Estado al cerrar: **no existe ningún baseline corrido con este instrumento**. Lo que falta, en orden:
arreglar el reintento del simulador (defecto #9) con sus tests, decidir si un escenario fallido debe
abortar la corrida o registrarse como no medido, y recién entonces correr `citable-1/2/3` y commitear la
evidencia. Sigue abierto además `escalation`: caso complejo con **spread 4** (el juez no decide entre 0 y
4) y caso super estable 2 puntos abajo del owner.

### L16 — el simulador reintenta, y el reintento no es un replay (2026-10-26)

> "arranca con #9"

El defecto #9 de L15, cerrado (`dd86925d`). `simulate_customer_turn` recibió el mismo presupuesto que
el juez —dos intentos— y el contrato de "respuesta inválida" quedó en un solo lugar
(`_read_simulated_turn`): **prosa** (lo que reventó el baseline: un turno de cliente impecable sin
sobre) o **JSON válido sin turno** (ni `message` ni `goal_reached`). Las dos se reintentan igual,
porque las dos dejan la conversación sin el turno que el guion esperaba.

Una desviación deliberada del patrón del juez, y con motivo: `_chat` pide `temperature=0`, así que un
replay a ciegas tiende a reproducir la misma respuesta equivocada. El segundo intento devuelve el
intento rechazado como turno del asistente y reafirma el contrato (`_SIMULATOR_RETRY`). El juez
conserva su reintento ciego tal como está: tocarlo es otro cambio, y no hay evidencia de que falle.

Cinco tests nuevos, sin red —`_chat` está mockeado, que es el seam determinista de este módulo—: prosa
reintentada una vez y usada; dos prosa levantan `JudgeError("… after 2 attempts")` sin inventar turno;
el segundo intento lleva la respuesta rechazada; un JSON sin turno se reintenta; y una respuesta
contratada sigue costando **una** llamada, que es la garantía de que no se agregó un reintento
gratuito a la corrida.

Verificación observada: `uv run pytest tests/unit/test_conv_eval_judge.py` 36/36, los dos archivos de
conv-eval 142/142, `scripts/test.sh quick` exit 0 y `shape origin/main` exit 0 (sin superficie de forma
tocada: `scripts/` no está en la lista).

**Lo que este arreglo no decide**, y sigue abierto: un escenario que falla igual —dos intentos
malos— **aborta la corrida entera** (`exit 2`, sin reporte), mientras un veredicto faltante del juez se
registra como no medido y la corrida sigue. Es la asimetría que L15 dejó nombrada, y la decisión es del
owner: abortar, o registrar el escenario como no medido y terminar con el reporte de los otros 13.
