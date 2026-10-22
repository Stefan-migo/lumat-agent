# HANDOFF — hilo chatbot: unificación de dos threads

**Escrito**: 2026-10-22, al cerrar el hilo A (retrieval/KB).
**Para**: el próximo chat, que recibirá **este handoff + el del otro agente** y debe producir **un solo plan**.
**Regla de entrada**: no escribir código hasta terminar la deduplicación de la sección 7.

---

## 1. Estado verificado del repo (no asumir, confirmar)

- Repo: `/home/stefan/repos/lumat-agent`. **Un solo worktree**; sin worktrees ODD activos.
- `main` = **`fd2e4341`** (`Merge pull request #657`), sincronizado con `origin/main`.
- Mergeado hoy: **#656** (`docs(odd): correct the message-catalog slot contract`, 16:56Z) y **#657** (este hilo).
- Branch `fix/chat-retrieval-service-query` mergeada (se puede borrar).
- Suite completa hoy: **2727 passed, 3 failed**. Los 3 son ambientales y pre-existentes (`media/` es de root → `PermissionError: media/projects`), verificados con `git stash` sobre el baseline. **No** son del código.
- Harness aislado vivo: `docker compose -p lumat-harness -f infra/docker-compose.yml -f infra/docker-compose.harness.yml`, api en 8001, db en 5433, monta **este** worktree (`..:/app`, uvicorn `--reload`). KB sembrada con los 4 documentos de `docs/kb` en `visibility=customer`.

---

## 2. Qué cerró este hilo (hilo A)

### 2.1 Diagnóstico

`me dieron tu contacto para una mantencion de caldera` derivaba a humano en el segundo mensaje. Evidencia en `conversation_events`: `intent:consulta` → `handoff:kb_miss`. Causa: el retrieval embebía **solo el texto crudo**, que con relleno conversacional cae bajo `min_sim = 0.50`.

| query embebida | similitud | resultado |
|---|---|---|
| `me dieron tu contacto para una mantencion de caldera` | 0.2686 | miss → handoff |
| `mantención de caldera` (el `service` que el clasificador **ya** extraía) | 0.6070 | hit → responde |

### 2.2 Fix mergeado (PR #657, `fd2e4341`)

`app/chat/nodes/respond.py` gana `retrieval_queries(state)` y `retrieve_chunks(session, state)`: intenta el **texto crudo primero** y cae al `service` clasificado **solo en el miss**. `respond()` y `research_triage._kb_check()` usan el helper. No se tocó `DEFAULT_MIN_SIM` ni `top_k`.

Por qué crudo primero (medido, 12 consultas, clasificador y embedder reales): crudo 5/12 · `service` 7/12 · `service+crudo` 9/12 · **crudo→`service` 9/12**. `service` solo pierde el *aspecto* de la pregunta (`"tienen garantia por la mantencion?"` 0.510 crudo vs 0.341 service; `"reparan calderas de agua caliente sanitaria"` 0.610 vs 0.390). Crudo-primero es aditivo: ningún turno que ya respondía cambia.

Tests nuevos: `tests/integration/test_kb_query_fallback.py` (3). Guard no obvio: un `service` de un turno `unknown` es de un tema anterior y se ignora.

### 2.3 Correcciones de registro que este hilo dejó asentadas

- **El bot resuelve solo por hit de KB.** No hay tool calling en el bot de cliente; el resto es intake o handoff. (Engram `chatbot/architecture/chatbot-resolvability`.)
- **`min_sim` es el trigger de escalación**, no solo un gate: sin chunks, `respond`/`research_triage` derivan sin llamar al modelo.
- **El invariante es `no inventar`**, no "responder sin KB". El LLM escribe solo la respuesta informativa; todo lo transaccional es código.
- **`case=#N` en el harness no prueba derivación**: `get_or_create_case` corre en toda clasificación. La prueba es `state=human` + `conversation_events`.

---

## 3. Unidades abiertas que este hilo deja (con evidencia)

### U1 — Ruteo del miss genuino ("unidad 2")

**Qué**: cuando el KB miss es real, hoy siempre `handoff`. Decidir si ofrece/arranca captura de visita.

**Por qué existe**: la persona de Max promete tres salidas (`"ofrece el siguiente paso: una visita técnica, un asesor, o los datos que faltan"`) y el código implementa una. Además ya estaba declarada fuera de alcance en `odd/tasks/kb-min-sim.md` ("any escalation redesign — separate unit, **KB-2 spec delta**") y `odd/tasks/cm4-linear-path-scope.md` quedó **pausada en una decisión humana** por el mismo motivo.

**Advertencia medida**: tras #657, en el corpus de 12 consultas los 3 misses restantes son **informativos, no pedidos de servicio**: `cual es la garantia del lavado de red` 0.487, `hacen instalacion de cocina a gas?` 0.491, `atienden en ñuñoa?` 0.296. Mandarlos a captura sería **peor**. La unidad solo sirve para pedidos de servicio fuera de KB, y esa población en el corpus actual es ~0.

**Bifurcación que exige decisión del owner**:
- **A** determinista a `capture` (barato, sin LLM, pega interrogatorio).
- **B** oferta determinista con mensaje configurable y captura solo si acepta (**recomendada**).
- **C** el LLM decide sin KB (rompe el guardrail de costo y T17).

**T1 propuesta (no código)**: medir misses reales por `handoff_reasons` / `kb_misses` del panel y clasificarlos (hueco de KB / umbral / fuera de alcance). Sin eso se diseña a ciegas.

**Toca**: spec KB-2 (escenario "No relevant content" dice literal *follows escalation rules*), tests pinneados de `test_chat_capture.py`, y probablemente `chat.conduct.derivaciones` (`app/services/settings.py:70-81`: 5 reglas declaradas, **solo `cobertura` tiene lector**).

### U2 — Variantes de saludo no reconocidas

`is_greeting_only` compara contra una lista exacta (`app/chat/nodes/receive.py:22-54`). Verificado con la función real: devuelven `False` → `"Hola buenas tardes"`, `"Hola, buenas tardes!"`, `"hola buenas noches"`, `"buen día"`. Sí devuelven `True` `"Hola"`, `"Buenas tardes"`, `"hola buenas"`.

**Consecuencia real** (no cosmética): el turno se clasifica por LLM, suma `unknown_count = 1` (a 2 deriva por HH-3) y `has_content()` da `True`, así que recibe el saludo **corto** (`greeting_short`, sin "¿En qué te puedo ayudar?") como si ya hubiera dicho qué necesita. Es exactamente lo que mostró el harness.

**Matiz**: no viola `odd/tasks/chatbot-first-turn-greeting.md` — su S1 enumera una lista cerrada y el código la cumple. Es **extensión de S1** (variantes naturales del habla chilena), no regresión.

### U3 — El retry de `research_triage` es un no-op

`_kb_check` devuelve `retry` y vuelve con la **misma** query: el resultado es idéntico por construcción. Antes repetía una retrieval; ahora repite la cascada (2). Está pinneado por AO-8 (`MAX_TRIAGE_RETRIES = 1`). Decisión pendiente: darle sentido o documentar que es un guard.

### U4 — El branch CM-4 de `respond` es inalcanzable

Documentado y probado en `odd/tasks/cm4-linear-path-scope.md`; la unidad quedó pausada en una decisión humana. Probablemente solo documentación + mapeo de tests, no código.

---

## 4. Inventario de hilos chatbot que ya existen (base para el dedupe)

| Hilo | Doc | Entrega | Estado |
|---|---|---|---|
| Mensajes predeterminados (el bot elige uno y el sistema llena slots) | `odd/tasks/chatbot-message-catalog.md` | **#591** (2026-10-14) + #656 (docs) | Mergeado. Doc dice "falta delivery" → **stale**: verificar contra git, no contra el doc. **D9: sin match → `cannot_answer` + handoff**. Intersecta U1 |
| Modelo de configuración en 4 capas | `odd/tasks/chatbot-config-model.md` | #644–#654, T19 = #655 | F1–F6 cerrados, T19 cerrado |
| Bug del saludo del primer turno | `odd/tasks/chatbot-first-turn-greeting.md` | — | S1 cerrada con lista acotada; U2 es extensión |
| Backlog KB (audiencia, calibración, triage scope, fidelidad) | `kb-*.md` | varias | Calibración de `min_sim` **cerrada** (0.50, decisión humana 2026-09-20); `kb-retrieval-calibration.md` **congelado** por receipt policy |
| Cerebro Max V4 / persona | `chatbot-cerebro-max-v4.md` | #643 | Cerrado |
| Asistente de panel (tools, inspección) | `assistant-*.md`, `chatbot-assistant-*.md` | #596, #621 | Superficie distinta (operador autenticado, sí tiene tools). Baja intersección |

### 4.1 El otro hilo: lo que ya está registrado (no adivinar, verificar)

El otro agente dejó un puntero consolidado en Engram: topic **`chatbot/thread-pending-work`**, observación **#6640** (2026-10-15). Resumen:

- **Hallazgo 1**: reacción del bot a la respuesta de un mensaje automático — `bot` contesta, `human` no (el operador es dueño del canal), `closed` crea conversación nueva que nace en `bot`. Un `"ok"` **no** se suprime hoy.
- **Hallazgo 2 (el de fondo)**: `notify.send_template` es un POST directo y **no** se registra como `Message` de la conversación. Por eso el LLM no sabe que se acaba de mandar la plantilla y el visor del panel tampoco lo muestra.
- **Diseño propuesto, NO decidido ni construido**: A) persistir el envío de plantilla como `Message` saliente; B) que el bot decida — B1 supresión determinista de acks pre-LLM (reusando `is_ack_message` y el patrón de gate de `acknowledge_emergency_if_ack`) o B2 que decida el LLM. Recomendación registrada: **A + B1**, gate conservador, y línea fija antes que silencio.
- **Fuera**: el footer "Este es un mensaje automático" no impide responder.

Archivos que ese hilo toca y que **no** están en la tabla de abajo: `app/services/notify.py`, el webhook (`app/webhook/ingest.py`), la persistencia de `Message` y la vista de conversaciones del panel. Intersección con este hilo: baja en código, **alta en semántica** (ambos deciden qué hace el bot cuando "no hay nada que responder").

Si el handoff del otro agente no cubre esto, **preguntar antes de asumir** que su unidad es otra.

---

## 5. Mapa de conflicto de archivos (quién toca qué)

| Archivo | Estado vivo | Riesgo de colisión |
|---|---|---|
| `app/chat/nodes/respond.py` | Retrieval helper nuevo + `_render_template_reply` + `_answer_from_kb` | **Alto**: cualquier hilo que toque la respuesta lo toca |
| `app/chat/subgraphs/research_triage.py` | Delega el retrieval al helper | Alto |
| `app/chat/nodes/classify_intent.py` + `agent/personas/classify.md` | Vocabulario de intents + `template_id` + `fields` | **Alto**: byte-coupled a `FALLBACKS` (`prompts.py`) |
| `app/chat/nodes/orchestrate.py` | `CAPTURE_INTENTS` / `RETRIEVAL_INTENTS` / tabla de dispatch | Alto (U1 lo cambia) |
| `app/services/settings.py` | Capas copy/conducta + `MESSAGE_DEFAULTS` + `CONDUCT_DERIVACIONES` | Alto |
| `agent/personas/orchestrator.md` | Persona de Max (promete los 3 siguientes pasos) | Medio: byte-coupled |
| `app/chat/nodes/receive.py` | `GREETING_TOKENS` / `is_greeting_only` | Medio (U2) |
| `app/services/kb.py` | `DEFAULT_MIN_SIM = 0.50` / `DEFAULT_TOP_K` / `retrieve()` | Bajo: decisión cerrada, no re-litigar |
| `tests/integration/test_kb_query_fallback.py` | Nuevo de este hilo | — |

---

## 6. Decisiones cerradas que NO se re-litigan

1. **`min_sim = 0.50`** — decisión humana 2026-09-20 (`odd/tasks/kb-min-sim.md`). El óptimo medido (0.4752) es knife-edge y no se adoptó.
2. **`no inventar` + `<user_input>` como dato** — invariante intocable (Engram `#6715`).
3. **Sin KB → `kb_miss`, una sola respuesta, cero llamadas al modelo** — T17 lo fijó con test.
4. **D9 del catálogo de mensajes**: sin match → `cannot_answer` + handoff, sin redacción libre.
5. **El bot de cliente no tiene tool calling.** Las capacidades son deterministas y acotadas.
6. **El branch CM-4 de `respond` es inalcanzable** — documentado, no es un bug.

---

## 7. Qué necesito del handoff del otro agente (checklist para el próximo chat)

Sin esto, la unificación es adivinanza:

1. **Estado de repo**: `main` que ve, branch/worktree, base del branch, PRs abiertos o mergeados.
2. **Archivos tocados** (lista exacta) y si alguno está en la tabla de la sección 5.
3. **Unidades abiertas** con su `S#` y su criterio de aceptación.
4. **Decisiones cerradas** de su hilo (para no contradecirlas ni duplicarlas).
5. **Decisiones pendientes** y de quién dependen.
6. **Evidencia medida** (números, no adjetivos) y qué NO se midió.
7. **Qué NO va a hacer** (fuera de alcance explícito).

---

## 8. Protocolo de unificación propuesto (para el chat nuevo)

1. **Un solo índice**: memoria Engram con topic **`chatbot/thread-index`** (este hilo la deja escrita). Toda unidad se registra ahí: ID, `S#`, doc, branch, archivos, estado, decisión pendiente.
2. **Un task doc por unidad** en `odd/tasks/`, IDs estables, specs citando las palabras del owner. Si dos handoffs describen la misma unidad, se **funde en una** con el ID más antiguo y se anota el alias.
3. **Propiedad de archivo**: antes de tocar un archivo de la sección 5, chequear el índice. Si dos unidades necesitan el mismo archivo, se **secuencian** (no en paralelo) o se parte por función.
4. **Medir antes de construir** para cualquier unidad que dependa de tráfico o de umbrales (patrón T1 de U1).
5. **Delivery**: PR por slice, `ask-on-risk` sobre ~400 líneas, `test` + `panel` verdes, `origin/main` adentro del branch, **nunca `--admin`**.
6. **Cada handoff nuevo** repite las secciones 1, 5, 6 y 7 de este documento. Si no las repite, no es un handoff.

---

## 9. Primer paso concreto del próximo chat

Producir, **antes de tocar código**:

- (a) tabla única de unidades de ambos handoffs, deduplicada;
- (b) orden propuesto con dependencias y justificación;
- (c) mapa de propiedad de archivos con la secuencia;
- (d) **un** task doc para la cola unificada;
- (e) la lista de decisiones que le corresponden al owner, con la recomendación y el tradeoff de cada una.

Solo después: implementar la primera unidad.
