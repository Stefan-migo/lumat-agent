# ODD — chatbot-backlog (cola unificada del hilo chatbot)

Origen único: `.rapsodia-code/sessions/archived/2026-10-22-chatbot-decision-dossier/report.md`.
Branch: `odd/chatbot-backlog` · Runner: `uv run pytest tests/` · Panel: `cd web && npm test && npm run build`
Estrategia: un slice por commit; el orden `S1 → S2 → S3 → S4 → S5` **no es negociable** porque hay archivos compartidos.

## Specs

### S1 · Saludos

> `is_greeting_only` por variantes, no lista exacta: saludos, variantes con puntuación/relleno y despedidas
> ("eso fue todo gracias"). Un saludo **nunca** suma `unknown_intent`.

Evidencia RED del reporte: *"Hola buenas tardes" → `intent=unknown` en `main`, medido en harness.
11 de 18 unknowns de producción son saludos.* Riesgo: none.

Alcance verificado el 2026-10-23 sobre `7a15e54d` (el código de `app/` es idéntico a `v2026.10.6`):

- La mitad **despedidas** ya está entregada y deployada por `app/chat/nodes/closure_gate.py`
  (`is_farewell`, corre antes de `classify_intent`): "gracias", "chau", "eso fue todo gracias" ya no
  clasifican ni suman `unknown_intent`. S1 **no** la reimplementa: la cubre con una regresión.
- Lo rojo es el **saludo**: `is_greeting_only` (`app/chat/nodes/receive.py:52`) compara el texto
  normalizado contra un `frozenset` de 7 strings exactos, así que `"hola buenas tardes"`,
  `"hola como va"`, `"alo"` caen a `classify_intent` y suman `unknown_intent`.
- Y es rojo **en cualquier turno**: `_flow_start` (`app/chat/graph.py:136`) sólo corta con
  `turn <= 1`, así que un "Hola" en el turno 4 también clasifica y suma. En producción hay
  "Hola" ×3.
- Despedidas y saludos son deterministas: **cero costo LLM** en este slice.

### S2 · Entrada

> Un detector determinista de pedido humano (D5): petición + rol, guarda de negación, token suelto
> sólo si es el mensaje entero, roles ampliados. Errores técnicos fuera del contador de
> `unknown_intent`. Conteo consecutivo. Mensajes de plataforma de Meta no se clasifican como clientes.

Evidencia RED: *tabla de detectores medida; `_record_unknown_intent` cuenta todos los eventos; un
mensaje de plataforma generó `unknown_intent` en producción.* Riesgo: none.

### S3 · Desenlace

> Salida 3 en el segundo fallo y oferta en `kb_miss` (D17, D18), con contador que resetea al entender.
> Dos textos configurables, expuestos en los tres lugares del panel.

Evidencia RED: *transcripciones de producción: la conversación muere en el fallo 2 y en el `kb_miss`.*
Riesgo: none.

Texto D17 (verbatim): *"Perdón, no te entendí. ¿Prefieres que te tome tus datos para coordinar una
visita, o que te atienda una persona?"* · Texto D18 (verbatim): *"No tengo ese dato. ¿Prefieres que
te tome los datos para coordinar una visita, o que te atienda una persona?"*

Los tres lugares del panel: `MESSAGE_DEFAULTS` (`app/services/settings.py`), el body model de
`/settings/messages` (`app/panel/api/routes/settings.py`) y la lista de campos de
`web/src/components/pages/Settings.tsx`.

### S4 · Instrumentación

> `kb_fidelity` usa la misma recuperación que producción (`global_only` + fallback a `service`) o
> registra la real; un resultado de recuperación por turno en `state`, consumido por `respond`.

Evidencia RED: *`_retrieved_chunks:316` difiere de `respond.retrieve_chunks`; `_kb_check` y `respond`
recuperan dos veces.* Riesgo: none.

### S5 · KB de cliente

> Cargar los 4 documentos de `docs/kb` con `visibility=customer` y proyecto vacío, y **re-medir** el
> desglose de handoffs.

Evidencia RED: *cero documentos `customer` en producción.* Riesgo: **item 5** (delivery/environment):
es una escritura en producción y la ejecuta el owner.

## Non-goals

- No re-litigar `D1–D11` (2026-10-21), `min_sim = 0.50`, los cinco invariantes de `D8` ni `S17`.
- Los 44 handoffs untracked de `odd/handoffs/` **no son backlog**: varios están cumplidos.
- No tocar retrieval (H03/H05/H09, chunking) antes de S4 y de la re-medición.
- Todo lo diferido a B2 (H07, H08, H10, H11, H12, S10, S11, S14, U4, derivaciones sin lector, negocio/legal)
  queda fuera de esta cola hasta tener evidencia por slice.

## Tasks

| ID | Spec | Alcance | Ruta | Commit |
|---|---|---|---|---|
| T1 | S1–S5 | Crear este doc desde el reporte y archivar la sesión | inline | este commit |
| T2 | S1 | `is_greeting_only` por variantes, en cualquier turno, sin sumar `unknown_intent` | inline, test-first | `31f4b4e7` |
| T3 | S2 | Detector único de pedido humano, contador consecutivo, errores técnicos fuera, filtro de plataforma | worker + inline, test-first | `9a2777b1` |
| T4a | S3 | Salida 3 (D17): reformular, ofrecer y derivar, con la oferta editable en el panel | worker + inline, test-first | `a82b4e8f` |
| T4b | S3 | `kb_miss` no terminal (D18): ofrece los dos caminos en vez de derivar | worker + inline, test-first | `b1d77f46` |
| T5 | S4 | Recuperación única por turno y fidelidad del medidor | inline, test-first | `9f0d7be8` |
| T6 | S5 | Cargar los 4 documentos `customer` y re-medir (owner, Risk item 5) | owner | pendiente |
| T7 | — | Re-medir el desglose de handoffs con tráfico nuevo sobre `v2026.10.6` | lectura | pendiente |

Mapa de archivos compartidos (un slice a la vez):

| Archivo | Slices |
|---|---|
| `app/chat/nodes/receive.py` | S1 |
| `app/chat/nodes/handoff_gate.py`, `app/chat/nodes/classify_intent.py` | S2 |
| `app/webhook/ingest.py`, `app/chat/nodes/orchestrate.py` | S2, S3 |
| `app/chat/state.py`, `app/chat/subgraphs/research_triage.py`, `app/chat/nodes/respond.py` | S3, S4 |
| `app/services/settings.py`, `app/panel/api/routes/settings.py`, `web/src/components/pages/Settings.tsx` | S3 |
| `scripts/kb_fidelity.py` | S4 |
| `app/services/conversations.py` (D15) | S3 |
| `tests/**` | cada slice |

## Log

**L1 — pedido original del owner (verbatim, 2026-10-23):**

> Continuamos el hilo chatbot de lumat-agent. Leé en este orden, completo:
>
> 1. odd/handoffs/chatbot-continuacion-dossier.md
> 2. .rapsodia-code/sessions/ready-for-odd/2026-10-22-chatbot-decision-dossier/report.md
> 3. .rapsodia-code/sessions/ready-for-odd/2026-10-22-chatbot-decision-dossier/session.md
>
> Reglas: no re-litigar lo cerrado (D5, D12–D18, D1–D11 del 21-oct, min_sim=0.50, los invariantes de D8, S17);
> no usar los handoffs viejos de odd/handoffs/ como backlog; local-first, se testea en el harness y
> producción sólo con algo concreto ya validado.
>
> Arrancá con el primer paso del handoff: worktree ODD ../lumat-agent-odd-chatbot-backlog en branch
> odd/chatbot-backlog, crear odd/tasks/chatbot-backlog.md desde el reporte (eso archiva la sesión), y
> después implementar S1 (saludos), que ya tiene RED medido.
>
> dame un overview antes de continuar

**L2 — corrección del owner sobre el modelo (verbatim, 2026-10-23):**

> Respecto a esto no le des tantas vueltas produccion y lcal utilizaremos flash. es la mejor version
> actualmnete de deepseek flash 4.1

Efecto: la mitigación de `D14` ("una pasada final con `deepseek-chat` antes de deployar cambios de
clasificación o generación") **deja de aplicar**: producción y harness usarán el mismo modelo, la
mejor versión vigente de DeepSeek Flash (4.1). El cambio de modelo en el VPS es un paso de delivery
propio, separado de estos slices, y se valida aparte. `D14` en sí (el harness no es espejo de
producción) no se reabre.

**L3 — base verificado (2026-10-23):** `main` = `7a15e54d`; `app/` y `web/src/` idénticos a
`v2026.10.6`, que es lo que corre producción; harness `lumat-harness` vivo. S1 arranca sobre esa base.

**L4 — S1 cerrado (2026-10-23), evidencia observada:**

- RED: 22 tests fallando en `tests/unit/test_chat_greeting.py` y
  `tests/integration/test_greeting_variants.py` (`"Hola buenas tardes"` → `classify_intent`; el turno
  de saludo hacía una llamada al modelo, devolvía la aclaración y escribía `unknown_intent`).
- GREEN: los dos archivos completos en verde (exit 0), y `uv run pytest tests/` completo en verde
  (exit 0, 0 `FAILED`/`ERROR`) sobre la base de test del worktree (`lumat-test-lumat-agent-odd-chatbot-backlog`, puerto 6266).
- Cambio: `GREETING_WORDS` + `GREETING_FILLERS` con tope de 40 caracteres reemplazan la lista exacta;
  `_flow_start` corta en cualquier turno; un saludo en turno > 1 se responde con `messages.greeting`
  (copy ya configurado, cero LLM) en vez de dejar el turno en silencio.
- Despedidas: no se reimplementaron. `closure_gate` sigue ganando antes del saludo (regresión en
  `test_greeting_variants.py::test_farewell_still_wins_before_the_greeting`).
- Costo LLM del slice: cero (camino determinista).
- No se corrió `scripts/chat_harness.py`: el harness monta el worktree principal y S1 no llama al
  modelo; los tests de integración ejercitan la misma entrada (`run_conversation`). Para S2/S3 la
  pasada por harness es obligatoria.

**L5 — S2 cerrado (2026-10-23), evidencia observada.** Cuatro unidades, test-first cada una:

- **S2a — detector único.** RED: 20 fallos en `tests/unit/test_human_request.py`. GREEN: 32 verdes. Un solo módulo, `app/chat/human_request.py::is_human_request`, y los dos call sites delegando (`_PERSONA_PATTERN` borrado del gate; `is_explicit_human_request` delega). Cuatro reglas de D5: petición + rol (verbo de contacto a ≤3 palabras del rol), guarda de negación (2 palabras antes del verbo), token suelto sólo si **todas** las palabras son roles, y roles ampliados. `tecnico/tecnica` son roles sólo-con-contacto, porque "necesito una visita técnica" es necesidad de servicio, no pedido de persona; y los verbos de contacto van en infinitivo e imperativo para que "una persona me atendió muy bien" no dispare.
- **Differential viejo vs nuevo (38 mensajes reales)**: 17 veredictos cambian. Dieciséis son los buscados. **Uno fue una regresión detectada acá**: `"asesor humano"` era frase literal del patrón viejo y el detector nuevo la perdía; se corrigió generalizando la regla del token suelto a "todas las palabras son roles". Después del fix, el gate y el classifier coinciden en el 100% de los casos.
- **S2b — racha y errores técnicos.** RED: 3 fallos en `tests/integration/test_unknown_streak.py` (+1 control que ya pasaba). GREEN: 4/4 y suite verde. `unknown_streak()` en `state.py` recorre eventos del más nuevo al más viejo (tope 50), cuenta `unknown_intent` y corta en el primer `classified` con `cause` distinto de `intent:unknown`; `from_db` y `_record_unknown_intent` lo usan. Una excepción del modelo escribe `classify_failed` y **no** suma ni escala. El control fija que dos fallos consecutivos **sí** escalan, con causa `handoff:unknown_intent_twice` verificada.
- **S2d — plataforma.** RED: 1 fallo (`tests/integration/test_platform_messages.py`); el test de la guarda pasaba por accidente porque hoy el body se descarta. GREEN: 7/7. Los tipos `system`, `unsupported`, `ephemeral` y `request_welcome` guardan su `body` como `text` para el registro y `process_message` no corre el grafo para `MessageType.OTHER`. El worker demostró la guarda quitándola: el test falla. `test_webhook_ingest.py`: 30 verdes.

Decisiones y límites de este slice:

- **No se agregó dedupe de "reintento con la misma consulta" (U3)**: el grafo corre una vez por mensaje y Meta deduplica por `wamid`, así que no hay camino que duplique el conteo; un dedupe por texto rompería la secuencia de D17 (el cliente que repite la frase **sí** debe recibir la oferta).
- **No se agregó guarda de "mensaje propio de la empresa"**: el payload del mensaje de onboarding no está capturado y `META_PHONE_NUMBER_ID` es un id interno de Meta, no un teléfono. La regla implementada es la defendible: sólo el contenido escrito por el cliente se clasifica.
- **Incidente de proceso**: una corrida de suite se lanzó en paralelo con los tests de un worker y murió en un `TRUNCATE` por contienda de base. Se descartó y se repitió sola. Regla: una sola corrida de tests por worktree.
- Costo LLM del slice: cero en S2a y S2d (deterministas); S2b cambia cuándo se escala, no cuántas llamadas se hacen.

**L6 — S3a cerrado (2026-10-23), evidencia observada.** Salida 3 (D17):

- **RED**: `tests/integration/test_unknown_offer.py` falla al colectar con `KeyError: 'cannot_understand_offer'`
  (el setting no existe) y, una vez creado, los cuatro casos describen la conducta que hoy está mal: dos
  fallos derivaban.
- **GREEN**: 4/4 verdes. Secuencia: fallo 1 `messages.clarification` · fallo 2
  `messages.cannot_understand_offer` y sigue en `bot` · fallo 3 deriva con causa
  `unknown_intent_thrice`. El texto es configurable y se lee por `get_message`.
- **Superficie de panel, cuatro archivos y no tres**: `MESSAGE_DEFAULTS` + registry de defaults en
  `app/services/settings.py`, `MessagesBody` en `app/panel/api/routes/settings.py`,
  `EMPTY_MESSAGES` + lista de campos en `web/src/components/pages/Settings.tsx`, y el tipo compartido
  `web/src/types.ts`. El `npm run build` (`tsc -b`) fue el que destapó dos fixtures más
  (`SettingsEmail.test.tsx`, `stories/.../mockData/settings.ts`) y el pin de claves del mock
  (`mockData/settings.test.ts`): la suite de Vitest no los ve, el type gate sí.
- **Pins movidos a propósito** (afirmaban la derivación en el segundo fallo): `test_chat_intent`,
  `test_handoff`, `test_conversation_flows`, `test_chat_capture::...cm4_refusal`,
  `test_unknown_streak::...consecutive...` y `test_webhook_ingest::retry_storm`. Ninguno se debilitó:
  ahora verifican también el estado intermedio (en el fallo 2 la conversación sigue en `bot`).
- **Causa renombrada**: `unknown_intent_twice` → `unknown_intent_thrice`. Cambia lo que se ve en
  analítica y en la ficha de la conversación; el nombre viejo habría quedado mintiendo.
- **Hallazgo**: en `retry_storm` no hay saludo porque los tres inbound se persisten antes del sweep y
  ninguno es primer contacto. Las tres respuestas son la secuencia completa.
- **Verificación**: backend completo exit 0 · `npm test` 1263 verdes · `npm run build` exit 0.
- Costo LLM del slice: cero en los fallos 1 y 2 (deterministas); la clasificación de cada turno es la
  única llamada, igual que antes.

**L7 — S3b cerrado (2026-10-23), evidencia observada.** `kb_miss` no terminal (D18):

- **RED**: `tests/integration/test_kb_miss_offer.py` falla al colectar (`KeyError: 'kb_miss_offer'`).
- **GREEN**: oferta configurable `messages.kb_miss_offer` en las cuatro superficies; `respond` la usa
  en la rama sin chunks y **no escala** (sigue registrando CM-6); `research_triage` conserva el retry
  acotado de AO-8 y después delega en `respond` en vez de derivar, así el texto vive en un solo lugar
  y queda **una** fila CM-6 por turno.
- **Dos cambios de ruteo del worker, revertidos**: hacía que un mensaje con `?` en el primer turno con
  `unknown` salteara la rama determinista, y que la oferta suprimiera el saludo fusionado de CM-1.
  Eran para satisfacer un test mal escrito, no una decisión. Se revirtieron y el test se corrigió.
- **El test estaba mal, no el código**: el doble de integración sólo clasifica `caldera`, `calefont`,
  `calefaccion`, `visita`, precios, `persona` y `emergencia`; `¿atienden en Ñuñoa?` es `unknown` y
  `caldera` va a captura (`CAPTURE_INTENTS`). El caso válido es un intent de `RETRIEVAL_INTENTS`
  (`valores`) en el turno 2, con un saludo primero para que CM-1 no fusione el saludo con la oferta.
- **S17 no se re-litiga**: el test sigue afirmando una sola respuesta por turno; lo que cambia es que
  esa respuesta es la oferta. `messages.cannot_answer` **no** se borra: conserva lector como fallback
  del LLM en `_answer_from_kb`.
- **La suite completa encontró 8 pins en 5 archivos fuera de las superficies del worker**
  (`test_api_kb_settings` ×2, `test_conversation_flows`, `injection_suite`, `test_chat_intent` ×2,
  `test_chat_manage` ×2). Todos afirmaban el desenlace viejo; ninguno se debilitó: ahora afirman la
  oferta, el estado `bot` y la causa de escalada ausente.
- **Verificación**: backend completo exit 0 · `npm run build` exit 0 · `npm test` 1263 verdes.
- Costo LLM del slice: cero en el miss (camino determinista); el único gasto es la clasificación del
  turno, igual que antes.

**L8 — S4 cerrado (2026-10-23), evidencia observada.** Recuperación única por turno y fidelidad del
medidor (commit `9f0d7be8`):

- **RED**: 4 fallos, los cuatro por el camino viejo, no por el test. `test_kb_fidelity.py::test_the_instrument_makes_the_retrieval_production_makes`
  (`TypeError: _retrieved_chunks() got an unexpected keyword argument 'intent'`),
  `test_respond_consumes_the_retrieval_the_triage_already_made` y `test_a_recorded_miss_is_offered_without_a_second_retrieval`
  (`KeyError: 'retrieval'` en el update de `_kb_check`), y `test_a_turn_that_skipped_triage_still_retrieves_in_respond`
  (`AttributeError: 'ConversationState' object has no attribute 'retrieval'`).
- **Una recuperación por turno (H04)**: `ConversationState.retrieval` (`list[dict] | None`) viaja en el
  estado del turno. `None` = nadie recuperó todavía (turno ruteado directo a `respond`); `[]` = recuperó y
  falló. `research_triage._kb_check` lo escribe en sus tres salidas (hit, miss con retry, miss final) y
  `respond` lo consume — vacío incluido — así que ya no vuelve a embeber ni a consultar pgvector. `from_db`
  lo deja en `None`, así que no se arrastra al turno siguiente (D2, sin checkpointer).
- **AO-8 intacto**: el retry acotado sigue haciendo su propio intento en un miss (misma consulta, mismo
  resultado, es la duplicación que el diseño ya tenía). Lo que desaparece es la re-recuperación de
  `respond`, que es la que H04 midió. Conteo: un hit cuesta una recuperación; un miss, las dos del retry
  acotado y ninguna más.
- **Fidelidad del medidor (H01)**: la recuperación tiene una sola definición,
  `respond.retrieve_for_queries` (ahí viven `top_k`, `min_sim`, `audience=CUSTOMER` y `global_only=True`),
  y el fallback a `service` vive en `respond.turn_queries(text, intent, service)`. `scripts/kb_fidelity.py`
  delega en las dos: no copia argumentos, así que no puede volver a desincronizarse. El `service` del
  fallback se lee del `case` persistido con el mismo orden que `get_or_create_case` (último `id`), y sólo
  cuando el turno clasificó — un `unknown` no dispara el fallback, igual que en producción.
- **El pin que movió la suite**: `tests/unit/test_prompts.py` construye dos dobles con `SimpleNamespace`
  (el helper `_respond_state` y uno inline). Los dos necesitaban `retrieval=None`. No se debilitó ninguno:
  el doble ahora refleja el campo nuevo, que es lo que `from_db` deja en el camino directo a `respond`.
- **Verificación**: focales (`test_kb_fidelity.py` + `test_kb_query_fallback.py`) 44 verdes · suite backend
  completa exit 0 (2817 tests) · harness real con `deepseek-flash` sobre dos conversaciones nuevas: saludo
  determinista, respuesta anclada en el chunk de precios ($80.000) y oferta de coordinar la visita. Sin
  `npm`/`web/`: el slice no toca el panel.
- **Ruido del entorno, no del code**: las corridas 1–3 de la suite murieron en timeouts de 120 s dentro de
  `psycopg.connect` y de `seed_dev.py` con el host a load ~107 (checkpoint de Postgres de 90 s con 65k syncs).
  La corrida válida es la 5, con `--timeout=300`; la 2 falló de verdad por los tres `AttributeError` del
  doble de `test_prompts.py`, que se corrigieron. Regla para la próxima: ante un timeout de suite, mirar
  primero la carga del host y el `docker logs` del contenedor de test antes de tocar el código.
- **Límite honesto que queda anotado (no es de este slice)**: `kb_fidelity` re-deriva el chunk set con el
  helper de producción; en un turno que se derivó antes de llegar a `respond` el reporte sigue mostrando
  el chunk set que ese helper devuelve para el texto (no "ninguno"), aunque sólo los turnos `answered` se
  puntúan por grounding. Cerrarlo del todo requiere un sink de sólo lectura en el grafo, que el owner
  descartó para S4 (decisión del 2026-10-23) a favor de la función compartida.
- Costo LLM del slice: **cero**. Elimina consultas locales de embed/pgvector por turno; no agrega ni
  quita llamadas al modelo.
