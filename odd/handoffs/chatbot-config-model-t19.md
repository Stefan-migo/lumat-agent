# HANDOFF — ODD `chatbot-config-model`, T19 (contrato de los cinco invariantes)

**Estado:** F1–F6 mergeadas (T1–T18 ✅). `main` en `50cea2c2` (merge de #654), sin worktree ni branch abiertos. Grafo `graphify-out/` actualizado por última vez desde `48ef8499`: corré `graphify <root> --update` antes de empezar.

## Queda una sola tarea

| ID | Task | Spec | Estado |
|---|---|---|---|
| **T19** | Test de contrato de los cinco invariantes | S19 | **siguiente** |
| — | F6 | S18 | ✅ (PRs #653/#654) |

T19 no es un slice: no toca UI ni produce comportamiento nuevo. Es una **red de seguridad**: un test que falla si alguna de las cinco garantías se vuelve desactivable, más la constancia de que las pruebas de esas cinco conductas siguen verdes.

## Fuente de verdad

- `odd/tasks/chatbot-config-model.md` — en `main`: specs S1–S19, tareas, `## Log` con T1–T18 cerrados y L0–L6. **No lo re-crees: extendelo.**
- Este handoff reemplaza a `odd/handoffs/chatbot-config-model-f5.md` (histórico, ya cumplido).
- Rapso session archivada: `.rapsodia-code/sessions/archived/2026-10-21-chatbot-config-brain/` (D1–D11). Gitignored.
- Engram: `odd/chatbot-config-model/tasks` (mirror del doc, al día tras F6), `odd/chatbot-config-model/conduct` (decisiones F3/F4/F6).
- **No re-litigar** D1–D11 ni L2–L6.

## Lectura de S19 (textual)

> Ninguna capa expone ni permite desactivar: 1. Gate de emergencia antes del LLM. 2. Límites de costo (`cost.conversation_limit`, `cost.daily_limit`). 3. Consentimiento antes de reservar. 4. No inventar y `<user_input>` tratado como dato (anti-inyección). 5. Takeover humano: con control humano activo, el bot calla.
> Criterio de aceptación: un test de contrato falla si alguna de estas claves aparece como escribible desde el panel, y las pruebas existentes de emergencia, costo, consentimiento y takeover siguen verdes.

## Decisión abierta #1 — qué significa "escribible desde el panel"

**El criterio literal no se cumple hoy, y no lo rompió F6:** `cost.conversation_limit` y `cost.daily_limit` **son** editables desde la sección Costos (`POST /settings/limits` → `_KNOWN_SECTIONS` en `app/panel/api/routes/settings.py:827`), y `emergency.keywords` es editable desde Agente (`POST /settings/keywords`). Los dos llevan ahí desde antes del baseline de F6.

Dos lecturas:

1. **"No se pueden desactivar" (recomendada).** Lo invariante es el *mecanismo*, no el número: el tope de costo existe siempre, y la emergencia se detecta siempre antes del LLM; el owner ajusta umbrales y palabras, no apaga la protección. El test de contrato entonces verifica que **no hay ninguna clave ni ruta que desactive** el gate, el corte por costo, el consentimiento o el takeover, y que esas claves no están en `ASSISTANT_WRITABLE_SETTINGS`.
2. **"Ninguna clave de las cinco es escribible".** Habría que sacar los límites y las palabras clave del panel y fijarlos en código. Un tope de costo fijo corta al bot siempre en el mismo umbral, y las palabras de emergencia dejarían de ajustarse al vocabulario real de los clientes: es peor producto.

Con (1), T19 queda como test de contrato + un guard de superficies; con (2), T19 arrastra además cambiar el panel y la spec. **Definí esto antes de escribir el test.**

## Anclas verificadas hoy (main `50cea2c2`)

| Invariante | Dónde vive | Cómo lo prueba la suite |
|---|---|---|
| 1. Gate antes del LLM | `app/chat/graph.py:260-263` (`START → emergency_gate` y sus tres aristas), `app/chat/nodes/emergency_gate.py`, `app/chat/nodes/emergency.py` | `tests/integration/test_emergency_notify.py`, flujos de `test_chat_capture.py` |
| 2. Límites de costo | `app/chat/nodes/cost_gate.py`, `app/services/costs.py`, claves en `SETTINGS_DEFAULTS` | `tests/unit`/`tests/functional` de costos; `GET /settings` expone `snapshot` |
| 3. Consentimiento | `app/chat/nodes/capture.py:19-21,142,178` (`capture_consent`, `record_consent`), textos en `reply.texts` | `tests/integration/test_chat_capture.py` |
| 4. No inventar + `<user_input>` | `agent/prompts/respond.md` + `prompts.render` (escapes), persona | `tests/injection/test_injection_suite.py` |
| 5. Takeover humano | `app/webhook/ingest.py:375-379` (con `HUMAN`/`CLOSED` el mensaje se persiste y **no** se responde), estados puestos en `handoff.py:81` y `emergency.py:69` | `test_chat_capture.py`, `test_assistant_harness_production.py` |

Superficies escribibles hoy, para el contrato:

- `POST /settings/{section}` catch-all con `_KNOWN_SECTIONS = {scope, keywords, tone, messages, hours, limits, meta, email}`.
- Rutas específicas: `tarifa`, `coverage`, `durations`, `capture-questions`, `reply-texts`, `conduct`, `persona`, `emergency`, `message-templates`, `email*`, `model_api_key`.
- `ASSISTANT_WRITABLE_SETTINGS` (`app/services/settings.py:985`): **excluye** todo lo protegido. Ya hay un test unitario de esa lista.

## Patrón de guard que ya existe en el repo

En F6 quedó un test que sirve de molde para T19: `tests/functional/test_api_conduct_settings.py::test_every_derivation_the_panel_renders_has_a_reader` escanea `app/*.py` y falla si el panel expone una opción que ningún código lee. El equivalente para S19 es escanear las superficies escribibles (rutas del panel + `ASSISTANT_WRITABLE_SETTINGS`) y fallar si aparece una clave que desactive un invariante. Cuidado con el catch-all: prueba lo que el endpoint hace con una sección inventada, no solo qué lista existe.

## Arranque

```bash
rapso worktree create chatbot-config-model-t19 --yes   # consentimiento del owner por feature
cp ../lumat-agent/infra/.env infra/.env
uv sync
bash infra/test-db.sh up        # puerto 6313 o el que asigne; esperá ~8s antes de correr tests
# Si tocás web/ recién ahí: cd web && npm ci
```

Correr siempre en invocaciones separadas: `tests/unit`, `tests/integration`, `tests/functional`, `tests/injection`. Y probar `tests/unit` con `DATABASE_URL="postgresql+psycopg://app:app@127.0.0.1:1/nope"`: tiene que pasar (unit es DB-free). Si recreás la DB de test, el suite **no migra solo**: corré `db/migrate.sh` con la `DATABASE_URL` admin.

## Restricciones verificadas

- Strict TDD ON (`openspec/config.yaml:28,38`); runner `uv run pytest tests/`.
- `agent/*.md` byte-acoplado a `prompts.FALLBACKS` (`tests/unit/test_prompts.py:162`). Si tocás un template, editá ambos.
- Pre-merge: `origin/main` al día, checks `test` + `panel` verdes, sin `--admin`, no auto-merge. `strict: true` obliga a mergear `origin/main` en la branch y esperar el re-run.
- `gh pr merge --delete-branch` falla localmente si `main` está en otro worktree: mergeá sin ese flag y limpiá a mano.
- `git worktree remove` rechaza directorios con archivos ignorados (`infra/.env`): usá `--force`. Y `bash infra/test-db.sh down` **antes** de borrar el worktree.
- Delivery: `ask-on-risk`; con más de ~400 líneas se corta en PRs encadenados `stacked-to-main`. Si el PR apilado no borra su rama base, GitHub **no** retargetea: `gh pr edit <n> --base main` a mano.
- GitGuardian marca `password = "adm-pass"` de los helpers de test como secreto en los PRs de backend (falso positivo, ya está en `main` en siete archivos). No es check requerido; se reporta y sigue.

## Deuda y pendientes (no bloquean T19)

- **`odd/tasks/chatbot-message-catalog.md` está desactualizado:** documenta que un slot desconocido se renderiza como `""`, y S9 lo prohíbe. Corrección es decisión del owner.
- **Decisiones de producto abiertas:** redacción de la reformulación de S14 (hoy repite el texto configurado), `redaccion: llm | plantilla` de S10 sin lector (F6 no lo expone, L6), señal de "aceptó la visita" para gatear `availability` (S11), y los cuatro `derivaciones` sin lector (`CONDUCT_DERIVACIONES_READ` documenta el subconjunto vivo).
- **Acción de producción pendiente de F1:** cargar `tarifa.precios` desde el panel (sección Tarifas) y **retirar de la KB el documento de precios** si ya estaba ingerido; borrar el archivo del repo no borra la fila ingerida.
- De Lumat: IVA de los cuatro precios, exigibilidad del 15%, matriz de garantías, documentos SEC.

## Próximo paso inmediato

Resolver la decisión #1 (lectura 1 o 2). Con eso, T19 en RED primero: el test de contrato debe fallar contra el árbol actual por la razón correcta y no por una lista mal escrita. Si se elige (1), el test no toca código de producción; si se elige (2), el trabajo incluye sacar `limits` y `keywords` del panel antes de que el contrato pueda pasar.
