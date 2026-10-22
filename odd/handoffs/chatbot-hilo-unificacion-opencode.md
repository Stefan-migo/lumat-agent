# HANDOFF — Unificación del hilo "chatbot" (lado OpenCode/ODD)

**Fecha:** 2026-10-22 · **main:** `fd2e4341` · **Estado:** dos frentes mergeados, sin worktrees abiertos.

Este handoff es de **un lado**. El owner va a pasar dos (este + el del otro agente) al próximo chat. El objetivo de ese chat **no es codear**: es unificar proceso, backlog y ownership antes de seguir.

> **El otro handoff ya existe:** `odd/handoffs/chatbot-thread-unification.md` (+ Engram `chatbot/thread-index` #6748). Tiene el inventario de los hilos chatbot, las unidades abiertas **U1–U4** y el mapa de conflicto de archivos. **No los repito acá.** Este documento agrega lo que solo tiene este lado: el proceso ODD verificado, el resultado de T19 y las decisiones de producto/negocio de `chatbot-config-model`. Si algo se contradice, gana el estado del repo, no el handoff.

---

## 1. Qué pasó, verificado

### Lado OpenCode/ODD (este agente)

Feature **`chatbot-config-model`** — cerrada completa.

| Slice | Tarea | PR | Merge |
|---|---|---|---|
| F1–F5 | tarifa, cobertura, conducta, persona, protocolo de emergencia, captura | #643 + previos | — |
| F6a/F6b | panel de conducta, preguntas de captura, respuestas del flujo, duraciones | #653, #654 | `50cea2c2` |
| T19 | contrato de los cinco invariantes (S19) | #655 | `5b006739` |
| doc | catálogo de mensajes alineado a S9 | #656 | `fd4c2ac9` |

**T19 encontró dos off switches reales** en `main` (no los introdujo F6):

- `POST /settings/limits` aceptaba `0` y `costs._percent` devolvía `0.0` con `limit <= 0` → corte por costo apagado para siempre.
- `POST /settings/keywords` aceptaba `{"keywords": []}` y `compile_keywords([])` compila un patrón que no matchea → gate de emergencia apagado.

Cerrados en write y read (`_number(positive=True)`, `_keywords()`, `_limit` con fallback al default, `_percent` fail-closed, `get_emergency_keywords` con fallback, `isValidPositive` en el panel). Contrato: `tests/functional/test_invariant_contract.py` (18 tests), probado con mutaciones. Decisión del owner **L7**: lo invariante es el mecanismo, no el número.

### Lado del otro agente (visible en el repo)

- **PR #657** `fix(chat): fall back to the classified service when the KB query misses` — merge `0d3ba131`, `main` en `fd2e4341`. Toca `app/chat/nodes/respond.py`, `app/chat/subgraphs/research_triage.py`, `tests/integration/test_kb_query_fallback.py` (nuevo) y `test_realtime_writers.py`.
  - Retrieval crudo-primero y `service` del clasificador como fallback. Medido: crudo 5/12 hits, `service` 7/12, crudo→`service` 9/12.
  - E2E en el harness: `kb_retrieved chunks:4`, responde precio y queda `state=bot`.
  - Reporta suite completa **2727 passed, 3 failed pre-existing** por `media/` propiedad de root (`PermissionError: media/projects`) — **verificado**: `media/` es `drwxr-xr-x root root` en main.
  - Fuera de alcance declarado: que un pedido sin respuesta de KB ofrezca iniciar captura en vez de derivar; esa decisión vive en `chat.conduct.derivaciones`.

### Restos que hay que decidir

- Branch local **y** remota `fix/chat-retrieval-service-query` (ya mergeada, sin borrar).
- Branch remota `odd/agenda-operator-technicians` (no es del hilo chatbot; confirmar dueño).
- `main` limpio de tracked; los `??` son handoffs viejos y dos PDFs de docs.

---

## 2. Cómo trabajo yo (para comparar procesos, no para imponer)

- **ODD**: clasificar small/large → spec `S#` en `odd/tasks/<feature>.md` → TDD RED→GREEN → worktree por feature (`../lumat-agent-odd-<slug>`) → commits por unidad de trabajo → PR con `test` + `panel` verdes, sin `--admin`, sin auto-merge.
- **Verificación**: verificador independiente solo cuando el `Risk:` nombra un ítem alto (guardas, datos, contratos, concurrencia). Suites **en invocaciones separadas**: `tests/unit` (también DB-free con `DATABASE_URL` inalcanzable), `tests/integration`, `tests/functional`, `tests/injection`. **Corrección descubierta hoy:** el comando oficial es `uv run pytest tests/`, que además incluye `tests/spec` — mis corridas de T19 no lo incluían. CI corre ese comando y es la fuente de verdad.
- **Web**: `cd web && npm test && npm run build` (el `tsc -b` vive solo en el build).
- **Memoria (Engram)**: `odd/<feature>/tasks` (mirror del task doc), `odd/<feature>/conduct` (decisiones). En el hilo chatbot: `chatbot/thread-index` (#6748) es el índice canónico; `chatbot/hilo/opencode-odd` (#6747) es el estado de este lado; `chatbot/hilo` (#6749) es solo un puntero al índice.
- **Handoffs**: `odd/handoffs/<feature>.md`, untracked.

---

## 3. Unificación propuesta (decidir en el próximo chat)

1. **Un solo backlog.** Hoy la verdad está repartida entre task docs, handoffs y memoria. Propuesta: `odd/tasks/chatbot-backlog.md`, una fila por unidad con `S#`, dueño, estado, PR, y link al task doc si necesita spec propia.
2. **Un solo formato de handoff.** El mínimo común entre este y `chatbot-thread-unification.md` (el otro ya usa: estado del repo, mapa de archivos, decisiones cerradas, checklist). El próximo chat fija el formato y lo escribe una sola vez.
3. **Memoria con hilo.** Ya hay dos índices escritos en paralelo: el canónico es `chatbot/thread-index` (#6748, del otro agente) y `chatbot/hilo` (#6749) quedó como puntero. Regla: un solo índice, y cada lado guarda su estado en `chatbot/hilo/<lado>` (el mío es `chatbot/hilo/opencode-odd`). Nadie sobreescribe el topic del otro.
4. **Regla de `main`.** Nadie deja WIP sin commitear en `main`; branch + PR desde el primer cambio. Hoy el otro agente dejó WIP en `main` un rato y después lo mergeó por PR — funcionó, pero es frágil.
5. **Ownership por superficie** (evitar pisarse en `respond.py`):
   - Configuración / invariantes / panel / KB comercial: lado ODD.
   - Retrieval / clasificador / routing del chat: lado del otro agente.
   - `respond.py` es la frontera: quien lo toque, avisa en el handoff.
6. **Criterio de "terminado"**: spec con criterio de aceptación + RED observado + suites verdes + `Risk:` + PR.

---

## 4. Pendientes reales consolidados

**Decisiones de producto (bloquean trabajo):**
- Reformulación de S14: hoy repite el texto configurado.
- `redaccion: llm | plantilla` (S10) sin lector.
- Señal de "aceptó la visita" para gatear `availability` (S11).
- Cuatro `derivaciones` sin lector (`CONDUCT_DERIVACIONES_READ` documenta el subconjunto vivo). **Es la misma intersección que la U1 del otro handoff** (ruteo del miss genuino): las dos unidades tocan `chat.conduct.derivaciones` y deben secuenciarse, no ir en paralelo.

**Negocio/legal (rapso session):**
- **IVA de los cuatro precios**: el tarifario guarda 30.000 / 50.000-40.000 / 80.000-60.000 / 140.000-120.000 sin campo de impuesto. Si son netos, el bot cotiza 19% menos y hay que agregar el campo (eso sí es código).
- **Exigibilidad del 15%** de recargo por no reagendar (Ley 19.496).
- **Matriz de garantías** por servicio (hoy prosa ambigua: "1 año o hasta la próxima mantención").
- **Documentos SEC**: si Lumat emite certificado/declaración o solo trabaja con técnicos autorizados. No prometer lo que no se entrega.

**Operativo:**
- Stack `infra` (API 8000, DB 5432) vs **harness** (8001, 5433). Verificado contra las bases, no contra la pantalla:
  - **harness**: `kb_documents` = 4 filas, `project_id` NULL, `visibility=customer` (es lo que el chat exige: `audience=CUSTOMER, global_only=True`). `tarifa.precios` presente: 30.000 / 50.000-40.000 / 80.000-60.000 / 140.000-120.000. **Sin documento de precios.** Correcto.
  - **infra**: `Manual Lumat` (interna, v2) + `Lumat_KB_Gasfiteria_Chile_v1_1.pdf` (interna, proyecto `Test`), y **sin** fila `tarifa.precios` (usa el default, que coincide con los precios reales). Si `infra` va a producción: cargar los 4 documentos globales `customer` y limpiar esos dos.

**Deuda técnica registrada (no bloquea):**
- `GET /settings` expone el límite crudo si la fila no es positiva, mientras el gate usa el fallback (A1).
- La persona editable puede borrar la frase de "no inventar" / `<user_input>` del prompt; el regex determinista de inyección queda en código (A3, pre-existente).
- `costs._limit` lanza `ValueError` con una fila no numérica escrita a mano (A5, pre-existente).
- Las 4 `derivaciones` sin lector siguen guardadas pero no editables.

---

## 5. Primeros pasos del próximo chat

1. Leer **ambos handoffs** y `mem_search("chatbot hilo unificación")`.
2. **No usar los handoffs viejos como backlog.** Hay **44** archivos untracked en `odd/handoffs/`; varios ya están cumplidos (ej.: `chatbot-config-model-f3.md` y `-f5.md`; el propio handoff de T19 declara que los reemplaza). El backlog nuevo es la única verdad.
3. Preguntar al owner, de a una: (a) formato de backlog, (b) ownership de `respond.py`, (c) si `infra` u harness es el entorno de producción.
4. Crear `odd/tasks/chatbot-backlog.md` y migrar los pendientes de la sección 4.
5. Limpiar `fix/chat-retrieval-service-query` (local y remota) y decidir qué hacer con `odd/agenda-operator-technicians`.
6. Recién ahí elegir el próximo slice. Candidato natural: las decisiones de producto, porque hoy el panel ofrece/omite cosas sin lector.

**No re-litigar:** D1–D11 de la rapso session `2026-10-21-chatbot-config-brain`, L2–L7 del task doc, ni el alcance de T19.
