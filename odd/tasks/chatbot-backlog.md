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
| T3 | S2 | Detector único de pedido humano, contador consecutivo, errores técnicos fuera, filtro de plataforma | pendiente | pendiente |
| T4 | S3 | Salida 3 + oferta en `kb_miss` + reset del contador + superficie de panel | pendiente | pendiente |
| T5 | S4 | Recuperación única por turno y fidelidad del medidor | pendiente | pendiente |
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
