# HANDOFF — Configuración de la API key de modelos (panel)

Fecha: 2026-10-13. Estado: **sin empezar**. Origen: pedido del owner durante el cierre del
work unit `panel-backend-crud` (KB/usuarios/casos, ya mergeado a `main` en `870de162`).

## Objetivo
Agregar en la sección **Configuración** del panel un sistema para configurar la **API key de los
modelos** (por ahora **DeepSeek**), que debe usarse tanto por el **asistente Lumat** como por el
**chatbot de WhatsApp**.

## Estado actual verificado (no asumir, ya está chequeado)
- **La key vive SOLO en env** (decisión de diseño SH-2): `app/config.py` — docstring *"all secrets
  live in server environment variables"*; el campo es `deepseek_api_key: str | None = None`.
- `app/services/llm.py` — `openai_client(provider)`: lee `get_settings()` (env-only, `@lru_cache`)
  y elige `settings.deepseek_api_key` (deepseek) o `settings.openrouter_api_key` (openrouter).
  **`CHAT_MODEL = get_settings().chat_model` se captura en import-time** (`llm.py:28`).
- Callers de `openai_client()` (cambio cross-cutting): `app/chat/nodes/{summary,classify_intent,
  respond}.py`, `app/chat/assistant/nodes.py`, `app/services/agent_chat.py`, `app/chat/graph.py`,
  `app/services/relations.py`.
- **Ambos ya comparten la key** vía env: `infra/.env.example` trae `CHAT_PROVIDER=deepseek`,
  `ASSISTANT_CHAT_PROVIDER=deepseek`, `ASSISTANT_CHAT_MODEL=deepseek-flash`. Lo nuevo es *editarla
  desde el panel*, NO unificar el provider.
- La tabla KV `settings` **hoy no guarda ningún secreto** (verificado: 0 matches de api_key/secret/token).
- `GET /panel/api/settings` (`app/panel/api/routes/settings.py`) devuelve **todas** las secciones →
  la key **nunca** puede volver en claro.
- Sección Configuración (frontend): `web/src/components/pages/Settings.tsx` — tabs (`SECTIONS`),
  drafts, y `save(<key>, "/panel/api/settings/<section>", body)` → `POST` por sección.
  Rutas backend: `app/panel/api/routes/settings.py` (GET + POST por sección + catch-all de sección
  desconocida, `_KNOWN_SECTIONS`).
- Infra: `infra/docker-compose.yml` (`DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:-}`), `infra/.env.example`.
- Constantes de modelo relacionadas: `CHAT_MODEL`, `chat_provider`, `assistant_chat_provider`,
  `assistant_chat_model` en `app/config.py`.

## Por qué se difirió (memoria `handoff/panel-model-api-key-config`)
1. Perfil de riesgo distinto: **credential-at-rest** + wiring de runtime vs borrado destructivo de DB.
2. **Choca con SH-2** (env-only) — invertir esa decisión merece su propia review.
3. **Cross-cutting**: cambiar la resolución de la key toca todos los callers + el `CHAT_MODEL`
   capturado en import-time.
4. **Superficie de exposición**: `GET /panel/api/settings` devuelve todo → hace falta write-only +
   enmascarado + admin-only + audit.

## Decisiones de diseño PENDIENTES (bloquean el arranque)
- **Precedencia**: ¿la key en DB *overridea* el env, o el env es la fuente de verdad y la DB es un
  override opcional? ¿Qué pasa si existen ambas?
- **Aplicación**: ¿aplica **en caliente** (resolver lee la DB en cada llamada) o requiere
  reload/restart? (ojo con `@lru_cache` y `CHAT_MODEL` en import-time).
- **Almacenamiento**: ¿reutiliza el KV `settings` (contradice SH-2) o un almacén de secretos
  separado? ¿Cifrado en reposo?
- **UX**: ¿qué se muestra si la key ya está seteada por env? ¿Solo se puede *setear/reemplazar*
  (nunca leer)? ¿Validación con un ping a DeepSeek?

## Alcance sugerido
- Backend: `app/config.py` o un resolver nuevo; `app/services/llm.py` (resolución de la key);
  `app/services/settings.py`; `app/panel/api/routes/settings.py` (sección nueva, write-only).
- Frontend: `web/src/components/pages/Settings.tsx` (sección "API key de modelos" en `SECTIONS`),
  `web/src/api.ts`.
- Tests: functional (settings/rutas), unit (resolución de la key), frontend (Settings).

## Setup de trabajo
- Worktree nuevo: `rapso worktree create <slug> --yes --root /home/stefan/repos/lumat-agent`, base
  `origin/main`. Slugs libres (no usar `panel-backend-crud`, ya mergeado).
- **Backend desde el worktree**; un solo stack `infra` a la vez.
- **TDD estricto activo** (`openspec/config.yaml testing.strict_tdd=true`): RED → GREEN → REFACTOR.
  Backend `uv run pytest tests/`; frontend `cd web && npm test` + `npm run build` (incluye `tsc -b`).
  DB de test: `bash infra/test-db.sh up` (puerto derivado 6026) + `eval "$(bash infra/test-db.sh env)"`.
- Commit Conventional **sin atribución de IA**. RDD activo (review al superar ~400 líneas o riesgo alto).

## Riesgos / notas
- Es **credential-at-rest**: cuidado con filtrar la key en tests, logs, audit `before/after`, o la UI.
- Tests con key **falsa** (`sk-test`), nunca real.
- Al tocar `llm.py` hay que revisar que el test suite mockea el chat (los conftest fuerzan
  `DEEPSEEK_API_KEY=sk-test`).

## Referencias
- Engram: topic `handoff/panel-model-api-key-config`.
- Código listado arriba; work unit previo `odd/tasks/panel-backend-crud.md` (cerrado, mergeado).
