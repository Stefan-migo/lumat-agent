# ODD — chatbot-first-turn-greeting (bug del saludo del primer turno)

Objetivo: en el primer turno el cliente recibe **un solo mensaje**, y el bot **no pregunta
"¿En qué te puedo ayudar?" cuando el cliente ya dijo qué necesita**.
Branch: `odd/chatbot-first-turn-greeting` · Estrategia de entrega: `ask-on-risk` (forecast < 400 líneas → PR único).
Runner: `uv run pytest tests/` · Strict TDD ON.

## Specs

- **S1 — saludo pelado, sin cambios.** Primer turno con saludo pelado (`hola`, `BUENAS`,
  `hola buenas`, `hola, buenas`, `buenos días`, `buenas tardes`, `buenas noches`, `hey!`):
  la respuesta es **un solo mensaje** con el saludo completo de siempre —
  `"Hola, soy el asistente virtual de Lumat. ¿Cómo estás?\n¿En qué te puedo ayudar?"` — y el
  flujo **no** clasifica (`_flow_start` → `END`). CM-1 se mantiene: identifica y pregunta.

- **S2 — el cliente ya dijo su necesidad.** Primer turno cuyo mensaje trae **contenido** (con o
  sin saludo delante), ej. `"hola necesito reagendar una visita que hice ayer, la quiero cambiar
  para mañana"` o `"necesito reagendar una visita"`: la respuesta es **un solo mensaje** =
  saludo breve **sin la pregunta redundante** (`"Hola, soy el asistente virtual de Lumat. ¿Cómo estás?"`)
  + `"\n\n"` + la respuesta normal del flujo. El mensaje **no** contiene `"¿En qué te puedo ayudar?"`
  (el cliente ya dijo qué necesita) y **sí** contiene `"soy el asistente virtual de Lumat"` (CM-1).

- **S3 — un solo mensaje por turno.** En el primer turno con texto, `replies` contiene exactamente
  **un** ítem. Hoy `"hola, tengo un calefont que no calienta"` produce **2** mensajes separados
  (`receive` agrega el saludo y el flujo agrega la respuesta) → el "me saluda y recién después da
  las horas".

- **S4 — turno ≥ 2 sin cambios.** Del segundo turno en adelante no se agrega saludo; CM-1 y los
  tests de resume (`test_cm1_*`) se preservan sin regresión.

- **S5 — copy configurable.** El saludo breve vive en `MESSAGE_DEFAULTS` (`"greeting_short"` =
  `"Hola, soy el asistente virtual de Lumat. ¿Cómo estás?"`) y se resuelve con
  `get_message(session, "greeting_short", ...)`, editable desde el panel como los demás
  (`messages.*`, ver `app/panel/api/routes/settings.py:200-202`). El saludo completo
  (`messages.greeting`) **no** cambia.

**Separador de la combinación:** `"\n\n"` (línea en blanco entre saludo y respuesta).

**Detección de "contenido":** el texto inbound normalizado (sin acentos, colapsado) **no** es un
saludo pelado y **no** está vacío. Un saludo pelado o un mensaje sin texto (media) usan el saludo
completo.

**No-objetivos:** no se cambia el texto del saludo completo; no se quita la auto-presentación
(CM-1 intacto); no se toca la duplicación ya resuelta por `_triage_node` (`graph.py:225-247`).

## Tasks

- T1 — RED unit: `has_content` / `is_greeting_only` — route: inline — **DONE**.
  RED: `ImportError: cannot import name 'has_content'`. GREEN: 12 unit tests en
  `tests/unit/test_chat_greeting.py`.
- T2 — RED integration: S1–S3 — route: inline — **DONE**.
  RED: `KeyError: 'greeting_short'` en colección. GREEN: 3 tests en
  `tests/integration/test_first_turn_greeting.py`.
- T3 — GREEN: `app/services/settings.py`, `app/chat/state.py`, `app/chat/nodes/receive.py`,
  `app/chat/graph.py` — route: inline — **DONE**.
- T4 — actualizar tests existentes — route: inline — **DONE**:
  `test_conversation_flows.py`, `test_triage_reply_duplication.py`, `test_api_kb_settings.py`,
  `test_ss5_overrides.py`, `test_chat_capture.py`, `test_kb_triage_scope.py`.
- T5 — verificar (suite completa) + commit de work-unit — **DONE**:
  `2044 passed, 2 warnings in 436.22s`; commit `54db098e`.
- T6 — consumidor extra: `scripts/kb_fidelity.py` clasificaba por igualdad exacta y esperaba el
  saludo como elemento aparte — route: inline — **DONE**: `_strip_greeting` maneja la forma
  fusionada (saludo completo y breve); 2 tests nuevos en `tests/unit/test_kb_fidelity.py`.

## Log

- **L1 (2026-10-14)** — pedido del owner, verbatim:
  > hey chat continuamos desde aca. dame un overview antes de continuar - Archivo: odd/handoffs/chatbot-first-turn-greeting.md (main worktree, untracked) - Engram: #6544 · tema handoff/chatbot-first-turn-greeting

- **L2 (2026-10-14)** — primera lectura del owner, verbatim:
  > Si creo que va con la combinacion. el saludo siempre debe ir. pero no de la forma que me saludo a mi. que me dice Hola soy el asistente lumat.... cuando yo habia saludado de una forma mucho mas sencilla.
  >
  > entonces debe estar el saludo siempre. y respuesta si es necesario.

- **L3 (2026-10-14)** — alcance del saludo (respuesta del owner, verbatim):
  > Saludo adaptado según cómo saludó el cliente

- **L4 (2026-10-14)** — confirmación inicial del contrato (respuesta del owner, verbatim):
  > Confirmo, arrancá el ODD

- **L5 (2026-10-14)** — evidencia de código (main = `6d7988b2`, drift vs. handoff que decía
  `ac86159e`). Bug vivo: `receive.py:26-29` agrega el greeting si `turn <= 1` y no corta el flujo;
  `graph.py:136-157` `_flow_start`/`_greeting_only`. `replies` con reducer `add` (`state.py:180`);
  `persist_replies` (`graph.py:335`) y `deliver_outbound` (`send.py:184-188`) mandan **una fila por
  ítem** → el "saluda y después responde" son dos mensajes de WhatsApp.

- **L6 (2026-10-14)** — mirror a Engram **pendiente**: `mem_save` falló con
  `multiple active runtime sessions match the current project and directory`. Progreso local preservado;
  reintentar el espejo (`topic_key: odd/chatbot-first-turn-greeting/tasks`) al cierre.

- **L7 (2026-10-14)** — **corrección de contrato del owner** (respuesta al conflicto con CM-1,
  verbatim):
  > Creo qu CM1 esta bien. pero lo que me imporat aqui es que tenga consistencia. si en el primer mensaje el clinete saluda y ademas menciona su problema o necesidad. el agente no deberia preguntar en que te puedo ayudar si el cliente ya se lo esta diciendo.

  Decisión aceptada: **CM-1 se mantiene** (el bot se identifica). El problema real no es la
  auto-presentación sino la **pregunta redundante** "¿En qué te puedo ayudar?" cuando el cliente ya
  dijo su necesidad. Se descarta el saludo `"¡Hola!"` sin identificación de L2/L3. Specs
  reescritas: S1 (saludo pelado) queda igual; S2 cambia el saludo por uno **sin la pregunta** y
  fusiona con la respuesta en un mensaje.

- **L8 (2026-10-14)** — blast radius verificado. Tests que hoy asumen el comportamiento viejo:
  `tests/functional/test_conversation_flows.py:102-116` (el caso exacto del owner: 2 mensajes),
  `tests/integration/test_triage_reply_duplication.py:106-134` (espera `[greeting, answer]`),
  `tests/functional/test_api_kb_settings.py:834-840` (set exacto de claves `messages`),
  `tests/integration/test_ss5_overrides.py:126` (`receive(state)["replies"][0]`).
  Los tests con saludo pelado (`"hola"`) **no** cambian: `test_chat_state.py:117/268/297`,
  `test_chat_harness.py:127`, `test_webhook_ingest.py:330`, `test_conversation_flows.py:94/133/239`,
  `test_golden_threads.py:52`.

- **L9 (2026-10-14)** — implementación y evidencia. Commit de work-unit `54db098e`
  (`fix(chat): fuse the first-turn greeting with the answer`). VERIFY: `uv run pytest tests/`
  → **2044 passed, 2 warnings in 436.22s** (las 2 warnings son preexistentes: `_publish_all`
  never awaited y el pooling de `paraphrase-multilingual-MiniLM`). No hay lint/typecheck
  configurado en el repo (sin ruff/mypy en `pyproject.toml` ni en CI).
  Mecánica: `receive` guarda el saludo elegido en `first_turn_greeting` (ya no lo agrega a
  `replies`); `run_conversation` lo fusiona con la respuesta del turno en un solo mensaje.

- **L10 (2026-10-14)** — consumidor corregido: `scripts/kb_fidelity.py` (`terminal_reply` /
  `greeting_emitted`) comparaba por igualdad exacta y asumía `[greeting, <respuesta>]`; con la
  fusión habría reportado turnos `declined`/`handed_off` como `answered`. Nuevo `_strip_greeting`
  cubre la forma fusionada (saludo completo y `greeting_short`) sin romper la forma vieja.

- **L11 (2026-10-14)** — nota de proceso: tres ediciones (`settings.py`, `state.py`, `graph.py`)
  se aplicaron por error en el worktree **main** y se revirtieron con `git restore` antes de
  tocar el commit; el árbol de `main` quedó limpio y todos los cambios viven en la branch.
