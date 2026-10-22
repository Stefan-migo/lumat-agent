# HANDOFF — ODD `chatbot-config-model`, slice F2 (capa 2: copy)

**Estado:** F1 mergeado (PR #644, merge `28a07508`). No hay worktree abierto ni branch. F2 arranca desde `main`.

## Fuente de verdad

- `odd/tasks/chatbot-config-model.md` — ya está en `main`: specs S1–S19, tareas T1–T19, y el `## Log` con T1–T5 cerrados (commits, decisiones y evidencia). **No lo re-crees: extendelo.**
- Rapso session archivada: `.rapsodia-code/sessions/archived/2026-10-21-chatbot-config-brain/` (`session.md` D1–D11, `report.md`). Gitignored.
- Engram: `odd/chatbot-config-model/tasks` (mirror del doc) y `handoff/chatbot-config-model-f2`.
- **No re-litigar** D1–D11 ni el diseño de `odd/tasks/chatbot-message-catalog.md` (PR #581).

## Arranque

```bash
rapso worktree create chatbot-config-model-f2
cp ../lumat-agent/infra/.env infra/.env
bash infra/test-db.sh up
cd web && npm ci
```

El slug es libre; lo que importa es nacer desde `main` (que ya trae el task doc y F1).

## Alcance F2 (S6–S9): toda la capa de copy

| ID | Task | Spec |
|---|---|---|
| T6 | `greeting_short` en `MessagesBody` y en la UI | S6 |
| T7 | `capture.questions` como fallback | S7 |
| T8 | Textos de agenda / cancelación / derivación | S8 |
| T9 | Contrato del catálogo de plantillas (sin rediseño) | S9 |

### T6 — el campo que ya se lee pero no se escribe

Hallazgo verificado, importante: **la lectura ya funciona**. `GET /settings` arma `messages` iterando `MESSAGE_DEFAULTS`, y ese dict ya incluye `greeting_short`. Lo que falta es la **escritura**:

- `MessagesBody` (`app/panel/api/routes/settings.py:74`) tiene cinco campos: `greeting`, `cannot_answer`, `clarification`, `farewell`, `out_of_hours`.
- `POST /settings/messages` hace `body.model_dump()` y guarda `messages.<key>`.
- `app/chat/nodes/receive.py:67` usa `greeting_short` cuando el cliente ya dijo qué necesita.
- Panel: `web/src/types.ts` → `Settings.messages` **no** declara `greeting_short`; `MESSAGE_TEMPLATES` en `Settings.tsx` tiene cinco entradas; el mock y los fixtures tampoco.

Al volver obligatorio el campo en el body, `test_settings_update_messages_audited` postea cinco claves y pasa a 422: actualizalo a propósito (es contrato, no ruido).

### T7 — preguntas de captura como fallback

- `app/chat/nodes/capture.py`: `CAPTURE_FIELDS` (orden + texto juntos, ~línea 47), `_FIELD_QUESTIONS = dict(CAPTURE_FIELDS)`, `_FIELD_ORDER`, `MAX_ASKS = 3`, `EVIDENCE_QUESTION`, `CONSENT_QUESTION`, `COMPLETION_REPLY`.
- Objetivo: mover **los textos** a `capture.questions` con defaults idénticos. El **orden** sigue en código: se configura en `chat.conduct` (T10, capa 3).
- El texto configurado es fallback cuando el LLM no redacta. La redacción por LLM es F3/F4 (T14/T16), no esta slice.

### T8 — textos deterministas

Anclas verificadas:

- `booking.py:44` slots disponibles; `:119` "No pude identificar un único horario…"; `:149` "Tu visita técnica quedó confirmada para…".
- `manage.py:101` slots de reagendamiento; `:166` "No puedo reagendar esta visita…"; `:179` visita reagendada; `:201` visita cancelada.
- `handoff.py:40` `HANDOFF_REPLY`.
- `capture.py` `COMPLETION_REPLY`, `EVIDENCE_QUESTION`, `CONSENT_QUESTION`.

Misma superficie que los mensajes: una clave de settings por texto, default igual al actual, sin tocar el flujo.

### T9 — plantillas

Solo **extender** `messages.templates`: sigue disparándose únicamente en intenciones informativas, reemplaza la respuesta del modelo y sus slots se validan. No rediseñes la selección por `classify`.

## Restricciones verificadas (actualizadas)

- Strict TDD ON (`openspec/config.yaml:28,38`); runner `uv run pytest tests/`.
- `agent/*.md` byte-acoplado a `prompts.FALLBACKS` (`tests/unit/test_prompts.py:162`). Si tocás la persona o un template, editá ambos.
- **`tests/unit` es realmente DB-free** desde `1731ef28`: los tests que abren DB viven en `tests/integration`. Probarlo: `DATABASE_URL="postgresql+psycopg://app:app@127.0.0.1:1/nope" uv run pytest tests/unit -q` debe pasar.
- Si recreás la DB de test, el suite **no migra**: corré `db/migrate.sh` con `DATABASE_URL` admin (`tests._testdb.admin_database_url()`). Sin eso, todo falla por auth del rol `app`.
- Correr `tests/unit`, `tests/integration` y `tests/functional` en invocaciones separadas.
- Pre-merge: `origin/main` al día, checks `test` + `panel` verdes, sin `--admin`, no auto-merge.
- `gh pr merge --delete-branch` falla localmente si `main` está en otro worktree (`fatal: 'main' is already used by worktree`): mergeá sin ese flag y limpiá branch/worktree a mano. `git worktree remove` rechaza directorios con archivos ignorados: usá `--force`, o `rm -rf` si el registro ya se borró.
- Docker de test por worktree: borrá contenedor y red (`lumat-test-<proyecto>-db-test-1`, `lumat-test-<proyecto>_default`) al eliminar el worktree.

## Contrato del panel (rompe el gate `panel` si lo olvidás)

- `web/src/stories/pages/_shared/mockData/settings.test.ts` compara las claves exactas del mock con `SETTINGS_KEYS`. Al agregar una clave al GET hay que tocar: `types.ts`, el mock, esa lista, y los fixtures de `Settings.test.tsx` y `SettingsEmail.test.tsx`. Si no, `tsc -b` falla (y `tsc` solo corre dentro de `npm run build`).
- `Settings.test.tsx` fija la lista de secciones del panel (hoy nueve, con Tarifas y Cobertura).
- Los mensajes del panel son copy en español de Chile: nada de voseo.

## Harness (conducta real)

```bash
docker compose -p lumat-harness -f infra/docker-compose.yml -f infra/docker-compose.harness.yml up -d
docker compose -p lumat-harness -f infra/docker-compose.yml -f infra/docker-compose.harness.yml exec -T api bash db/seed.sh
cd web && VITE_API_TARGET=http://localhost:8001 npm run dev
```

Panel `:5173/panel/app/`, API `:8001`, DB `:5433`. Subir los `docs/kb/*.md` con visibilidad **cliente** (el default es `internal`). Harness de chat: `exec api uv run python scripts/chat_harness.py --phone +56900000001`; cada teléfono es un cliente distinto.

**Acción de producción pendiente de F1:** los precios ahora viven en settings. En el harness y en producción hay que cargar `tarifa.precios` desde el panel (sección Tarifas) y **retirar de la KB el documento de precios** si ya estaba ingerido; borrar el archivo del repo no borra la fila ingerida.

## Pendientes (no bloquean F2)

- Redacción default exacta de cada pregunta de captura (decisión de copy, T7).
- Si el saludo se personaliza con el nombre del cliente.
- Derivaciones activas por defecto (T10, capa 3).
- De Lumat: IVA de los cuatro precios, exigibilidad del 15%, matriz de garantías, documentos SEC.

## Próximo paso inmediato

T6: agregar `greeting_short` a `MessagesBody`, al tipo `Settings.messages`, al mock y a `MESSAGE_TEMPLATES`; guardar y ver que `receive.py` cambia el saludo sin deploy.
