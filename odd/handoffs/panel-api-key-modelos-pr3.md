# HANDOFF — API key de modelos desde el panel (PR3 = full-stack, COMPLETADO)

Fecha: 2026-10-14. Estado: **PR1, PR2 y PR3 implementados y verificados; falta integrar `origin/main`
y abrir el PR3.**
Origen: work unit `panel-api-key-modelos` (task doc en `odd/tasks/panel-api-key-modelos.md`, en `main`).

## Objetivo
Configurar la **API key de DeepSeek** desde la sección **Configuración** del panel, alimentando **ambos**
consumidores (chatbot WhatsApp + asistente Lumat). PR3 = **WU4**, que terminó siendo **full-stack**.

## Lo que YA está mergeado en `main`
- **Backend (PR1 + PR2):** tabla `panel_secrets` cifrada AES-256-GCM (`app/services/crypto.py`), KEK en
  `SETTINGS_ENCRYPTION_KEY`; resolución hot-apply (`app/services/model_secrets.py`,
  `resolve_model_api_key()` con caché TTL 45s); `openai_client()` resuelve DeepSeek por el resolver →
  ambos consumidores comparten la key del panel; API admin-only
  `GET/POST/DELETE /panel/api/settings/model_api_key`.
- Tests backend: `uv run pytest tests/` → **1991 passed**.

## Lo que hizo PR3 (esta sesión)
Worktree `/home/stefan/repos/lumat-agent-odd-panel-api-key-modelos-pr3`,
rama `odd/panel-api-key-modelos-pr3`, base `origin/main c253c125`.

Commits:
- `7cbc00e2` — `feat(panel): configure model API key from settings` (10 archivos, 141+/8-)
- `a9938c8e` — `docs(odd): record PR3 completion and the backend scope extension`

- **AK-14** — `web/src/api.ts`: `ModelApiKeyStatus`, `ModelApiKeyResponse`, `SaveModelApiKeyResponse` +
  `getModelApiKeyStatus()`, `saveModelApiKey()`, `deleteModelApiKey()`. Reusa `apiFetch`/`postJson`.
- **AK-15** — `web/src/components/pages/Settings.tsx`: sección "API key de modelos" en `SECTIONS` con input
  password, Guardar (POST), Borrar (DELETE, habilitado solo si `source === "panel"`), leyenda de origen,
  enmascarado y feedback del ping. Estilos en `Settings.css` (sin inline styles).
- **AK-16** — tests: `web/src/api.test.ts` + `web/src/components/pages/Settings.test.tsx` (+6 tests).
- **Fix de backend (alcance extendido por el dueño)** — `app/panel/api/routes/settings.py`: el POST
  descartaba el retorno de `validate_deepseek_key()`, así que "válida" y "válida sin saldo" devolvían el
  mismo `200 {"ok": true}` y el frontend no podía distinguirlos. Ahora responde
  `{"ok": true, "validation": "valid"|"no_balance", "model_api_key": {...}}`. La key se sigue guardando
  en ambos casos (una key sin saldo sigue siendo válida).

## Verificación observada
- `uv run pytest tests/` → **1991 passed**, exit 0.
- `npm --prefix web test` → **105 files / 1180 tests passed** (baseline 1174).
- `npm --prefix web run build` → verde, incluye `tsc -b`.
- RDD assess (`--base-ref c253c125 --committed-only`): `risk medium`, `review_due false` (`under_budget`)
  → sin review nativa para este slice.

## PR MERGEADO
- **PR #592** — https://github.com/Stefan-migo/lumat-agent/pull/592
  Título: `feat(panel): API key de modelos configurable desde Configuración (slice 3/3)`.
  Label `type:feature`, base `main`, rama `odd/panel-api-key-modelos-pr3` (pusheada).
- Checks: **GitGuardian pass**, **panel pass (2m43s)**, **test pass (3m42s)**.
  `mergeStateStatus: CLEAN`, `mergeable: MERGEABLE`.
- **MERGEADO** el 2026-10-14T10:02:05Z (merge commit `6d7988b2`). Feature en `main`.
  Worktree, rama local y rama remota limpiados.

## Integración pre-merge (hecha)
`origin/main` se movió dos veces después de crear el worktree: PR #590 (`3139dfac`) y PR #591
(`ac86159e`). **PR #591 solapaba 7 de nuestros 10 archivos** (`settings.py`, `Settings.tsx`,
`Settings.css`, `Settings.test.tsx`, `types.ts`, `mockData/settings.ts`, `mockData/settings.test.ts`).
Se mergeó `origin/main` en la rama (`d187df51`, textualmente limpio) y se re-corrió la integración sobre
el árbol mergeado:
- `uv run pytest tests/` → **2028 passed**, exit 0
- `npm --prefix web test` → **105 files / 1184 tests passed**
- `npm --prefix web run build` → verde

El merge quedó semánticamente coherente: `templates` (#591) y `model_api_key` conviven en la respuesta
del `GET /settings` sin claves duplicadas, y la interfaz `Settings` lleva ambos campos.

## Nota de honestidad (TDD)
`openspec/config.yaml` declara `strict_tdd: true`, pero el flujo activo del proyecto es ODD y las slices
previas (PR2) también escribieron tests junto con la implementación. En PR3 los tests se verificaron
**GREEN**, no se demostró **RED-first**. Si el dueño quiere strict TDD, hay que explicitarlo.

## Gotchas / convenciones vigentes
- **PRs del repo lumat-agent**: rama `odd/<slug>`, label **`type:feature`**, body libre con `## Summary`.
- **GitGuardian** marca como "Generic Password" un default tipo `password: str = "adm-pass"` en tests
  nuevos. Usar una constante con nombre inocuo (`_ADMIN_CREDENTIAL`). Un fix posterior NO limpia el check:
  hay que reescribir el historial.
- El repo **no imprime la línea de resumen** de pytest (`addopts = "-q"`); verificar con el exit code y
  contando los dots, no buscando "N passed".
- **NO tocar** `infra/.env` ni `.env.example`. Worktree nuevo: copiar `infra/.env` a mano + `uv sync`.
- DB de test: `bash infra/test-db.sh up` + `eval "$(bash infra/test-db.sh env)"` (puerto 6290).
- Frontend: `npm --prefix web ci` en worktree nuevo.

## Follow-ups NO bloqueantes (en el task doc)
- **AK-17** — Test que ejercite los consumidores REALES (`chat/graph.py`, `agent_chat.py`), no solo
  `openai_client()`.
- **AK-18 (R3-001)** — `set/clear_model_api_key` invalidan la caché ANTES del commit; un read entre
  invalidación y commit puede re-cachear el valor viejo hasta 45s. Bounded por el TTL.

## Referencias
- Task doc: `odd/tasks/panel-api-key-modelos.md` (en `main`, actualizado en la rama PR3).
- Memoria Engram: topic `odd/panel-api-key-modelos/tasks` (#6511), decisión de alcance PR3
  `odd/panel-api-key-modelos/pr3` (#6540), `architecture/panel-model-api-key-config` (#6509).
- PRs mergeados: #588 (slice 1/3), #589 (slice 2/3). Main movió con #590.
