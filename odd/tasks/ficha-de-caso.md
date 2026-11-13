# Ficha de caso — Fase 3 del chatbot de WhatsApp

Feature de la Fase 3 del roadmap del chatbot, alcance fijado en
`odd/handoffs/chatbot-fase-3-ficha-de-caso.md`. Una sola unidad: **el caso existe**.
Riesgo alto declarado en el handoff: item 1 (migración) e item 3 (`respond` corre en cada mensaje).

## Specs

**S1 · La ficha del caso existe y es determinista.**
«Bloque estructurado y acotado (≈1.500 caracteres), **determinista**, reconstruido de la base e
inyectado antes del transcript: qué equipos, qué propiedad, qué se intervino y cuándo, qué quedó
pendiente, qué garantía corre». Sin llamada a modelo para construirla; cota dura de 1.500 caracteres
con recorte determinista.

**S2 · Se inyecta antes del transcript, en `respond`.**
«la ficha se inyecta en el prompt de `respond`, que corre en cada mensaje». La ventana de turno no se
toca: «la ventana de turno se queda como está, es correcta para el tono» (`conversation_transcript`,
`limit=6` sin cambios).

**S3 · La ficha cuelga de la propiedad, no del cliente.**
«Ocho de 34 propiedades reales son de otro. Por eso la ficha cuelga de la **propiedad**, no del
cliente». Cada trabajo anterior se muestra con la dirección donde se hizo; cuando esa dirección no es
la del cliente actual, la ficha la nombra explícitamente para que el bot no la confunda con «mi casa».
No se inventa un modelo de propiedad: el ancla es la dirección registrada en el caso.

**S4 · Linaje de casos.**
«`Case` con `origin_case_id`: un caso nuevo **declara** de dónde viene. No reabre el anterior». Un caso
nuevo de un cliente con casos previos guarda el id del caso previo más reciente; la fila previa no se
modifica (estado, `summary`, `closed_at`, `conversation_id` intactos).

**S5 · `decide_spending`: tres valores, default `si`.**
«Campo de tres valores con **default `si`**; se baja sólo si la conversación lo demuestra». Valores:
`si`, `duda`, `no`. `si` es el default y el valor ante cualquier ausencia de evidencia.

**S6 · La bajada es un extractor determinista de 5-6 frases.**
«La regla de bajada es un extractor de 5-6 frases («soy arrendatario/a», «consulto con el dueño», «el
dueño es X», «te escribo de parte de», «administro», «no es mi casa»)». Determinista, sin modelo,
insensible a tildes y mayúsculas, con límite de palabra. La ausencia de evidencia nunca cambia el valor.

**S7 · No confirmar precio ni autorizar trabajo a quien no decide.**
«La capacidad mínima no es «conocer el rol»: es **no confirmar precio ni autorizar trabajo a quien no
decide**». El hecho viaja en la ficha y en la persona.

**S8 · Una sola pregunta, sólo cuando hay plata en juego.**
«Una sola pregunta, sólo cuando hay plata en juego». Con `decide_spending = duda` y un turno que toca
dinero, `respond` hace una única pregunta determinista y registra el evento; nunca la repite en la
misma conversación.

**S9 · Fuera de alcance.**
«promesas (Fase 4), rescate de hilos (Fase 5), cotización (Fase 6), media/visión (Fase 7), clasificador
(Fase 8)». Tampoco entra la UI del panel: el handoff dice que la sección de casos «es consecuencia, no
trabajo aparte», y la consecuencia empieza cuando la base tiene linaje.

### Decisiones de diseño (no fijadas al detalle en el handoff)

- **D1 · Tokens de `decide_spending`**: `si` | `duda` | `no`. `duda` es el estado «hay indicio, no
  prueba» (nombrar a un dueño distinto del que escribe): es el que dispara S8.
- **D2 · La subida existe, pero sólo por autodeclaración explícita** («soy el dueño», «yo decido»,
  «yo pago»). Sin ella, un falso positivo del extractor bloquearía precios a un propietario para
  siempre. Es una decisión, no una lectura del handoff: queda sujeta a veto del owner.
- **D3 · La garantía que corre** sale de una tabla en código con las tres garantías publicadas en
  `docs/kb/lumat-garantias-pagos.md` (mantención de calefont y de caldera: 1 año o hasta la próxima
  mantención; lavado de red: 6 meses). La ficha dice el vencimiento; nunca lo inventa para un servicio
  sin garantía publicada.

## Tasks

| ID | Specs | Route | Commit | Estado |
|---|---|---|---|---|
| T1 | S4, S5 | Migración `065_case_ficha.sql` + modelos (`cases.origin_case_id`, `customers.decide_spending`) | `3192ab77` `feat(db):` | hecho |
| T2 | S1, S3, D3 | `app/services/case_ficha.py` + tests: constructor determinista, cota, propiedad, garantía | `13c6684f` `feat(chat):` | hecho |
| T3 | S2 | Inyección `<ficha>` antes de `<conversation>` en `respond` + persona | `dd0dcd99` `feat(chat):` | hecho |
| T4 | S4 | Linaje en `app/services/cases.py` (`get_or_create_case`, `create_manual_case`) + tests | `a8e6c648` `feat(cases):` | hecho |
| T5 | S5, S6, S7, S8 | `decide_spending`: extractor, persistencia por turno, pregunta única, hecho en ficha y persona | `a79631ce` `feat(chat):` | hecho |

## Log

**L1 — pedido del owner (verbatim).**

```
Retomamos el hilo del chatbot de Lumat en Fase 3. Leé odd/handoffs/chatbot-fase-3-ficha-de-caso.md y
odd/analysis/lumatdata/03-defectos-y-mejoras.md (D1, D5, D7). Arrancá con la ficha del caso.
```

**L2 — cortes de revisión (slice boundaries).** La unidad se entrega en cortes de ~400 líneas
autoradas: corte 1 = T1 (migración + modelos) + T2 (constructor de la ficha) + T3 (inyección en
`respond`), cerrado en `dd0dcd99` con 847 líneas sobre `origin/main`. Corte 2 = T4 (linaje) y T5
(`decide_spending`), que van en commits propios. Si el corte 2 supera el tamaño razonable, se abre
como PR encadenado sobre el corte 1 en vez de engordar el mismo PR.

**L3 — verificación independiente: cuatro defectos que la implementación no veía.** La verificación
read-only sobre el diff completo devolvió veredicto por spec y cuatro bloqueantes, todos corregidos en
el mismo corte antes de la suite final:

1. **B1, la garantía se anunciaba siempre «vigente».** `_work_line` estampaba `garantía vigente hasta
   ...` sin comparar con hoy ni mirar el estado del caso: una mantención de hace 916 días se anunciaba
   vigente, y una abierta (trabajo aún no hecho) también. Es exactamente la afirmación de plata que S7
   existe para evitar, y viajaba como hecho al prompt. Ahora: sólo casos cerrados, y `vigente` /
   `vencida` según el vencimiento contra la fecha del turno.
2. **B2, el corte se comía «Decide el gasto» y «Pendiente».** El tope cortaba en la primera línea que
   no entraba, y la cola de seguridad iba al final: con el propio escenario de la prueba, 1.388
   caracteres y 112 libres dejaban fuera la línea de 68. Ahora la cola se **reserva primero** y lo que
   se corta es el historial de trabajos, del más viejo al más nuevo, con el marcador `…` donde se
   cortó.
3. **B3, una negación se leía como autodeclaración.** «no soy propietaria» contiene «soy propietaria»,
   así que el descargo del cliente lo re-autorizaba y pisaba un `no` probado. Se agregaron las
   variantes negadas al grupo `no` (que se evalúa primero), incluida la femenina.
4. **B4, «¿cuánto demora?» quemaba la pregunta única.** El término suelto `cuanto` marcaba dinero en un
   turno que pregunta tiempo, y como el evento queda registrado, la pregunta legítima ya no salía
   nunca en esa conversación. Ahora son frases de precio («cuanto cuesta/sale/vale/cobra»).

Además se corrigieron dos hallazgos menores que no bloqueaban: la evidencia del turno se observa
**antes** del grafo (A2: responder «yo decido» y que la ficha siga diciendo «sin confirmar» era
incoherente) y la inserción del evento lleva el mismo guardia de conversación persistida que usa
`kb_miss` en la misma función (A3).

Quedan como decisión del owner, no como deuda de este corte: **A1** con `decide_spending = no` un turno
de precio sigue respondiendo desde el tarifario publicado, sin pasar por ficha ni persona — es
deliberado porque informar un precio publicado no es confirmar un precio para ese trabajo; **A4**
«arriendo la casa» es ambiguo (un propietario también arrienda) y quedó en el grupo `no`, sujeto a
medición con el corpus.

**L4 — el gate `full` no cerraba, y no era el cambio.** La primera corrida de `bash scripts/test.sh
full` murió sin resumen: `pytest-timeout` con `timeout_method = "thread"` mata el proceso entero, así
que no imprime qué test colgó, y el `exit 0` que se veía era el del `tail` del pipe. Con el log
completo redirigido a archivo, el frame culpable era
`tests/spec/test_projects_spec.py::test_project_slug_is_normalized_and_unique`: `projects.create`
embebe de verdad, `app/services/kb.py` construye `TextEmbedding` sin `cache_dir`, fastembed busca el
modelo en su ruta por defecto —que en este host no está poblada— e intenta bajarlo de HuggingFace.
El modelo sí está en `/home/stefan/.cache/lumat-fastembed` (241 MB): con
`FASTEMBED_CACHE_PATH=/home/stefan/.cache/lumat-fastembed` el archivo pasa (18 passed en 65 s).

Es preexistente y ajeno a esta feature: el diff no toca `kb.py`, `projects.py` ni nada de embeddings.
El gate se corre con esa variable exportada.

**L5 — resultado del gate `full`.** Con `FASTEMBED_CACHE_PATH` exportado la suite corrió completa en
9m59s: **una sola falla**, `tests/integration/test_assistant_artifacts.py::test_artifact_pdf_saves_and_publishes_idempotently`
(`assert second["changed"] is False` → `True`), y todo lo demás en verde.

No es de esta feature y no es contaminación entre archivos — pasa sola y pasa con su archivo completo
(20 passed). La causa es que WeasyPrint no produce bytes estables: el mismo HTML renderizado dos veces
con un segundo de diferencia da hashes distintos, y `app/services/assistant_artifacts.py` decide
«cambió» comparando el `sha256` de los bytes. Es una prueba dependiente del reloj, preexistente, en
código que este diff no toca (`reports.py`, `assistant_artifacts.py`).

Queda como defecto del arnés de tests, a decisión del owner: congelar el reloj o comparar el contenido
lógico en vez del PDF.
