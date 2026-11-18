# Verdad de alcance

Familia 1 del juez: el bot afirma alcance comercial y hechos del historial del cliente que la KB no sostiene. Dos defectos con causa compartida y gravedad distinta, por eso dos specs y un solo arreglo de base.

Rama `odd/verdad-alcance`. Autoridad de alcance: `docs/kb/lumat-servicios.md` (lista cerrada). Autoridad del historial: `app/services/case_ficha.py`.

## Specs

### S1 — Ningún servicio fuera de la lista cerrada de la KB

El veredicto del juez sobre `real-vocabulario-impreciso`:

> afirma que trabajan con quemadores de cocina a gas y ofrece la visita, sin que ese servicio esté listado en la base de conocimiento

El bot respondió, literal:

> Sí, lo vemos: trabajamos con quemadores de cocina a gas, con técnicos autorizados SEC. La visita técnica tiene un valor de $30.000. ¿En qué comuna estás y qué días te acomodan para coordinar la visita?

La KB es una lista cerrada, literal:

> **Otros servicios que cotizamos.** Reparación de calderas y calefont, instalaciones y reemplazos, gasfitería y filtraciones de agua, redes de gas, aire acondicionado, calefactores eléctricos, ductos y trabajos eléctricos. Estos trabajos se cotizan según lo que necesites: un asesor revisa tu caso y te contacta con el presupuesto. No reparamos lavadoras, lavadoras-secadoras ni refrigeradores. Tampoco reparamos artefactos que no estén en esta lista.

Regla: un artefacto, pieza o trabajo que no esté en esa lista no puede presentarse como algo que Lumat hace. Decirlo, y ofrecer el siguiente paso que la KB ya autoriza (un servicio del catálogo o un asesor). Ejemplos que hoy fallan y deben pasar: «quemadores de cocina a gas», «bomba de calor de piscina».

### S2 — Ningún hecho del historial del cliente que la ficha no sostenga

El veredicto del juez sobre `real-consulta-otros-equipos`:

> afirma que Lumat realiza mantención de bomba de calor de piscina sin respaldo en la base de conocimiento e inventa un "caso abierto" del cliente por ese equipo y por aire acondicionado

El bot respondió, literal, en tres turnos:

> Sí, trabajamos con aire acondicionado, y en tu caso ya tenemos un trabajo abierto por ese equipo.

> Sí, también trabajamos con bomba de calor de piscina, y de hecho tienes un caso abierto de hoy justamente por ese equipo.

> La mantención no es una obligación: lo que tengo registrado es un caso abierto hoy por la bomba de calor de piscina, así que si no la pediste tú, lo aclaramos sin problema.

Regla: el bot no afirma que el cliente tiene un caso, un trabajo o un antecedente por un equipo salvo que la ficha lo registre para ese equipo. «Aire acondicionado» sí está en la lista de S1; el defecto de este turno es el hecho inventado, no el alcance.

Nota de causa, medida: la ficha de esta misma conversación se renderiza como antecedente (ver L3). La regla es sobre lo que se le dice al cliente; el arreglo de la causa va en T4.

### S3 — Un servicio del catálogo no se niega por no tener tarifa publicada

Medido en `real-consulta-otros-equipos` después de S1: el bot respondió

> En climatización sí trabajamos, pero el aire acondicionado no aparece entre los servicios con tarifa publicada, así que no quiero darte un valor inventado.

«Aire acondicionado» **sí** está en la lista de la KB. Decir que no aparece «entre los servicios con tarifa publicada» confunde «no lo hacemos» con «no tiene precio publicado», que son cosas distintas (L13).

Decisión del owner, verbatim:

> En este caso en particular. podria decir si lo trabajamos pero se calcula el valor segun el diagnostico. y puede mencionar el valor de la visita tecnica y la logica de la visita tecnica, o sea que ahi investiga y segun lo evaluado se hace el presupuesto. o algo asi por el estilo

Regla: si el trabajo está en el catálogo pero no tiene tarifa publicada, se afirma que lo hacemos y se dice que el valor se calcula según el diagnóstico. Se puede mencionar el valor de la visita técnica (está en `<tarifario>`) y su lógica: el técnico evalúa el equipo en el domicilio y, según lo que encuentre, el trabajo se presupuesta aparte. La negación por catálogo queda reservada a lo que no está en la lista (S1).

Tres estados, para que no se mezclen: en catálogo con precio publicado → se informa el precio; en catálogo sin precio publicado → S3; fuera de catálogo → S1.

## Tasks

| ID | Spec | Ruta | Commit |
|---|---|---|---|
| T1 | S1 | test RED: reclamo de alcance fuera de la lista cerrada | `e7215aa1e` |
| T2 | S1 | guard determinista + regla de prompt | `e7215aa1e` · `789b404dd` |
| T3 | S2 | test RED: la ficha no presenta el caso en curso como antecedente | `544783bba` |
| T4 | S2 | `case_ficha` + regla de prompt | `544783bba` |
| T5 | S1, S2 | aserciones de eval por turno en el corpus | `f84e6f6f2` |
| T6 | S1, S2 | medición de los dos escenarios | `98489e6f5` (sello) |
| T7 | S3 | regla de prompt + hard fail de negación de catálogo | `248f160cd` |
| T8 | S1, S3 | corrección del guard: negación y lista acotada a lo medido | `531f3eb01` |
| T9 | todas | `bash scripts/test.sh full` | sin commit (gate) |
| T10 | todas | re-medición con el árbol final | sello `531f3eb0` |
| T11 | todas | tabla de commits, veredicto por S# y entrega | este commit |

Ruta: inline en el padre. Cada unidad es un módulo (`respond.py`, `case_ficha.py`) y el diagnóstico ya está cargado; delegar duplicaría la lectura.

## Log

**L1 — pedido del owner, verbatim:**

```
│ Familia 1 — el bot inventa alcance fuera de la KB.
│ - real-vocabulario-impreciso: «afirma que trabajan con quemadores de cocina a gas y ofrece la visita, sin que ese servicio esté
│   listado en la base de conocimiento».
│ - real-consulta-otros-equipos: «afirma que Lumat realiza mantención de bomba de calor de piscina sin respaldo en la KB e inventa
│   un "caso abierto" del cliente por ese equipo y por aire acondicionado».
```

```
Ojo con la familia 1: los dos escenarios comparten causa pero no son iguales. Prometer un servicio inexistente es una afirmación
comercial falsa; inventar un «caso abierto» del cliente es peor, porque afirma un hecho sobre su historial. La spec debería
separarlos aunque el arreglo sea uno.
```

```
Está bastante bien, vamos a seguir con el orden de lo que venimos trabajando, con el awareness, el evaluador
```

**L2 — evidencia de la corrida.** `odd/evals/conv-eval-con-juez-conversaciones.md` líneas 281-292 (`real-vocabulario-impreciso`, juez 0.00, hard fail) y 634-651 (`real-consulta-otros-equipos`, juez 0.00, hard fail). Turnos del cliente literales del corpus, `scripts/conv_eval_corpus.yaml:497` y `:879`.

**L3 — causa de S1.** El guard determinista `_APPLIANCE_REPAIR_CLAIM` (`app/chat/nodes/respond.py:553`) sólo reconoce lavadoras, lavadoras-secadoras y refrigeradores. La línea del prompt (`agent/personas/orchestrator.md`) nombra los mismos tres y agrega «ni artefactos fuera del catálogo de servicios», pero no existe ninguna representación de la lista positiva: ni el guard ni el prompt saben qué servicios sí están. Un reclamo sobre un artefacto fuera de catálogo no dispara nada.

**L4 — causa de S2.** `classify_intent.py:223` crea o actualiza el caso de esta conversación con `status` de clasificación (`abierto` por defecto), y `respond.py:847` arma la ficha después. `case_ficha.build_case_ficha` selecciona todo caso abierto (`case_is_open`) y lo renderiza como:

```
Pendiente de nuestra parte:
- <servicio> (abierto desde el <hoy>)
```

El modelo lee el caso de la conversación en curso como antecedente del cliente y lo adjudica al artefacto que el cliente acaba de mencionar. No es alucinación libre: es un hecho real del sistema presentado como historial.

**L5 — hallazgo del evaluador.** `must_include_any` se evalúa sobre la conversación entera y no por turno, así que un turno secuestrado o una afirmación inventada pasan si otro turno cumple el token. Los dos escenarios de este corte midieron 0.00 por el juez, no por las gates. T5 corrige eso con aserciones por turno.

**L6 — Graph Check.** Nodos consultados: `Servicios de Lumat KB Document` (`docs/kb/lumat-servicios.md`), `Deterministic Configured Answers (S4-S6)` y `Unrestricted Window Not Announced as Hours (S9)` (`odd/tasks/agenda-config-fuente.md`), `Lumat Agent (asistente WhatsApp)` (`docs/capacidades-agente-lumat.md`). Aristas: `Chatbot Agenda Config Fuente Handoff --references--> Servicios de Lumat KB Document`, `Deterministic Configured Answers --conceptually_related_to--> Cobertura y horarios de Lumat KB Document`. El grafo no tiene nodo de `case_ficha.py`; el camino de llamada se leyó en fuente.

**L7 — forma del arreglo de S1.** El guard existente (`_affirms_excluded_appliance_repair`) sólo registra observaciones para el panel: no reemplaza la respuesta. La que sí reemplaza es `_gas_manipulation_instruction`, y S1 copia ese patrón: predicado + texto configurable + `ConversationEvent`. El predicado exige las dos condiciones juntas (marco de reclamo en primera persona Y artefacto fuera de catálogo) porque con una sola hay falsos positivos: la KB escribe «revisión de quemadores» dentro de la mantención de calefont, y reemplazar una respuesta correcta es peor que el defecto. Se descartó representar el catálogo completo en el prompt: `docs/kb/lumat-servicios.md` es la única fuente y duplicarlo en la persona crea deriva. En cambio la persona ahora dice que la lista es cerrada, que es lo que faltaba.

**L8 — por qué G11 y no `must_not_include`.** `must_not_include` (G7) busca la cadena en cualquier lado, así que no distingue la afirmación de su rechazo: «no trabajamos con quemadores de cocina» contiene «trabajamos con quemadores de cocina». Los dos defectos de este corte tienen exactamente esa forma, y anclar la frase habría castigado la respuesta correcta. G11 (`must_not_affirm`) lee la negación delante del ancla. Además el corpus evalúa por conversación, no por turno: G11 cierra el hueco de L5 porque cualquier turno con el reclamo afirmativo falla, sin necesidad de indexar turnos.

**L9 — estado de la verificación.** S1 commiteado con `quick` en verde. S2 delegado; T5 escrito y validado en estático (el corpus carga 42 escenarios con las anclas nuevas). La suite no se puede correr en paralelo: `clean_db` es `autouse` y trunca la DB compartida del worktree, así que las corridas se serializan por worktree.

**L10 — límite de slice.** 408 líneas autoradas en 6 commits: pasado el slice de ~400 de revisión. El corte es una sola familia de defectos con causa compartida y los seis commits ya son atómicos y legibles uno por uno. Entrega propuesta: una PR con los seis commits, o una cadena `S1` → `S2+T5` si el revisor prefiere dos ventanas. La decisión es del owner; acá sólo se deja el hecho medido.

**L11 — verificación de la gate.** Muteo de `_affirms_anchor` a `return True`: fallan exactamente los dos tests que dependen de la negación, y ninguno más. Además, alimentando las respuestas medidas de la corrida original, G11 marca `trabajamos con quemadores` en la primera y `trabajamos con bomba de calor` + `caso abierto` en la segunda; dos rechazos correctos pasan. Sin ese chequeo la gate podía pasar por la razón equivocada.

**L12 — medición (T6).** Corrida `verdad-alcance-s1s2`, sello `98489e6f5`, KB `34670f5b3d75` (4 documentos), juez `deepseek-v4.1-flash`, 2 repeticiones. Árbol limpio. Resultado: **2/2 pasan, ningún gate falla**.

| Escenario | Antes | Ahora | hard fail |
|---|---|---|---|
| `real-vocabulario-impreciso` | 0.00 | **2.83** | no |
| `real-consulta-otros-equipos` | 0.00 | **2.00** | no |

La KB estaba vacía en la base del worktree: hubo que sembrarla con `scripts/seed_kb_docs.py --apply` antes de medir, o `kb_answered` habría fallado por la razón equivocada.

**L13 — deriva nueva que la medición destapó.** El bot dejó de inventar alcance, pero ahora responde con la regla del **tarifario** en vez de la del catálogo: «el aire acondicionado no aparece entre los servicios con tarifa publicada». Dos problemas: (a) confunde «no lo hacemos» con «no tiene precio publicado», que son cosas distintas; y (b) el aire acondicionado **sí** está en la lista de la KB (`docs/kb/lumat-servicios.md`, «Otros servicios que cotizamos»), así que ahora sub-declara un servicio que Lumat ofrece. No es el defecto de S1 y no rompe ninguna aserción; queda registrado como observación medida, no como tarea de este corte. Los 2.00 de cierre y 2.00 de `conversational` vienen de ahí: el tercer turno se pone defensivo («no te estoy pidiendo que le hagas mantención…»).

**L14 — corrección del owner sobre L13, verbatim:**

```
En este caso en particular. podria decir si lo trabajamos pero se calcula el valor segun el diagnostico. y puede mencionar el valor de la visita tecnica y la logica de la visita tecnica, o sea que ahi investiga y segun lo evaluado se hace el presupuesto. o algo asi por el estilo
```

Se abre S3 y la tarea T7. La medición de T6 queda como línea base de S1+S2 y **no** cubre S3: el prompt cambió después, así que T8 vuelve a medir.

**L15 — por qué S3 entra en este corte y no en el siguiente.** S1 y S3 son las dos mitades de la misma regla: el catálogo es cerrado, y dentro de él no tener precio publicado no significa que no lo hagamos. Arreglar sólo S1 produjo justamente el vaivén que midió L13: el bot pasó de sobre-declarar a sub-declarar. Escribir las dos mitades en el mismo bloque de la persona es más probable que se sostenga que arreglarlas en cortes separados, y comparten autoridad (la lista de la KB) y escenario de medición.

**L16 — medición tras S3.** Corrida `verdad-alcance-s3`, 2 repeticiones, KB `34670f5b3d75` (sembrada de nuevo, idempotente). **2/2 pasan, ningún gate falla, sin regresiones** contra la corrida anterior.

| Escenario | Antes de S1 | Tras S1+S2 | Tras S3 |
|---|---|---|---|
| `real-vocabulario-impreciso` | 0.00 (hard fail) | 2.83 | **3.00** |
| `real-consulta-otros-equipos` | 0.00 (hard fail) | 2.00 | **2.58** |

Delta por dimensión contra S1+S2: grounding **+1.25**, policy **+1.00**, tone +0.50, closure +0.25, escalation 0, conversational **−0.75**. La caída de conversational es longitud: explicar la lógica de la visita alarga la respuesta. El juez premia concisión, así que ese número mide largo, no corrección.

La conducta pedida en L14 aparece literal en la corrida:

> Sí, la climatización está dentro de lo que trabajamos, incluido el aire acondicionado. El valor depende del equipo y de lo que necesites, así que se evalúa en una visita técnica de $30.000 y, según lo que se encuentre, el trabajo se presupuesta aparte.

Queda una blandura medida, no un defecto: para la bomba de calor el bot dice «no aparece en los servicios que tenemos listados, así que no puedo confirmarte que la trabajemos» en vez del «tampoco reparamos» de la KB. Es más suave de lo que la KB autoriza, pero no afirma nada falso y no costó puntaje.

**L17 — `full` encontró una regresión que `quick` y el evaluador no vieron.** Cuatro fallas en `tests/integration/test_chat_harness.py`, todas del guard de S1:

1. **Ceguera a la negación.** El predicado miraba el marco de reclamo sin leer lo que había delante, así que «No reparamos lavadoras» disparaba el reemplazo: el bot reemplazaba su propio rechazo correcto por el texto enlatado.
2. **Lista demasiado ancha.** El rewrite cubría también lavadoras, refrigeradores, hornos, lavaplatos y campanas, y eso rompe una decisión previa del owner. `f9e29596b` («the guard only replaces what the corpus measured») nació de un incidente real —un guard borró una respuesta correcta y el escenario pasó de 41/42 a fallar— y dejó escrito: *«replace only what was measured, observe the rest»*, con el reclamo de artefacto excluido nombrado explícitamente como observar y no reescribir.

El corte repitió el mismo error que ese commit documenta. Arreglo: la lista de rewrite queda en las dos familias medidas (`bombas de calor`, `quemadores`) y el predicado lee la negación delante del marco. Sin ensanchar la lista, que es cómo un guard empieza a borrar respuestas correctas.

Consecuencia registrada y no escondida: un reclamo de alcance sobre un artefacto fuera de catálogo **no medido** (hornos, lavaplatos, lavadoras) no se reescribe; su instrumento son la persona y el juez, igual que antes de este corte. Es la doctrina vigente, no una omisión.

Nota de proceso: esto es la clase de escape que AGENTS.md ya tenía documentada — `quick` verde, `focused` verde, el evaluador verde, y la regresión apareció sólo en `full`.

**L18 — medición final y veredicto.** Corrida `verdad-alcance-final`, sello `531f3eb0170a0bd33095ef56b0236cfac6a3587e`, **árbol sucio: no**, corpus `8adb94421f45`, KB `34670f5b3d75`, juez `deepseek-v4.1-flash`, 2 repeticiones. **2/2 pasan, ningún gate falla, sin regresiones.**

| Escenario | Antes de S1 | Tras S1+S2 | Tras S3 | **Final (código entregado)** |
|---|---|---|---|---|
| `real-vocabulario-impreciso` | 0.00 (hard fail) | 2.83 | 3.00 | **3.67** |
| `real-consulta-otros-equipos` | 0.00 (hard fail) | 2.00 | 2.58 | **2.58** |

Delta por dimensión contra la corrida con S3: conversational **+1.25**, escalation +0.50, policy +0.25, closure +0.25, tone 0, grounding −0.25. La suba de `conversational` es la que había bajado: acotar el rewrite a lo medido devolvió respuestas más naturales.

`bash scripts/test.sh full`: **exit 0** sobre `531f3eb01` (11m 02s). La corrida previa sobre el mismo árbol de tests había fallado con 4 errores, que es lo que produjo L17.

**Veredicto por spec:**

- **S1 — alcance sólo desde la lista cerrada.** ✅ El juez ya no marca `hard fail` en ninguno de los dos escenarios, G11 no dispara, y el guard reescribe sólo las dos familias medidas y nunca un rechazo. Límite declarado en L17: fuera de esas dos familias el instrumento es la persona y el juez, no el rewrite.
- **S2 — ningún hecho del historial que la ficha no sostenga.** ✅ Causa raíz corregida en `case_ficha.build_case_ficha`; el «caso abierto» desapareció de los tres turnos de la corrida y se conserva el historial de otras conversaciones (test cubre las dos mitades).
- **S3 — un servicio del catálogo no se niega por no tener tarifa publicada.** ✅ Conducta pedida presente en la corrida: «Sí, la climatización está dentro de nuestros servicios… la visita técnica tiene un valor de $30.000… el presupuesto se calcula aparte».

**Observación final, para decisión del owner y no como tarea:** el patrón de S3 ahora también moldea las respuestas sobre artefactos fuera de catálogo. Para el quemador de cocina la corrida final dice «no aparece como trabajo con valor fijado en nuestro catálogo… lo que sí podemos hacer es coordinar una visita técnica ($30.000), donde el técnico revisa el quemador y, según lo que encuentre, el arreglo se presupuesta aparte». No es un `hard fail` y el juez lo puntuó 3.67, pero ofrece una visita pagada por un trabajo que puede no estar en el catálogo. El spec S1 se cumple (no afirma que lo hace); la conveniencia comercial es otra pregunta.
