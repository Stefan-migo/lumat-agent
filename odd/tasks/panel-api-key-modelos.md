# panel-api-key-modelos — API key de modelos configurable desde el panel

Estado: en curso. Rama `odd/panel-api-key-modelos`, base `origin/main 870de162`.
Worktree: `/home/stefan/repos/lumat-agent-odd-panel-api-key-modelos`.
Origen: handoff `odd/handoffs/panel-model-api-key-config.md` + memoria `architecture/panel-model-api-key-config`.

## Objetivo
Permitir configurar desde la sección **Configuración** del panel la **API key de DeepSeek**, y que esa
key alimente **los dos consumidores**: el **asistente Lumat** y el **chatbot de WhatsApp**. Editable en
caliente, cifrada en reposo, write-only y auditada.

## Requisito duro (owner, 2026-10-13)
Una sola key configurada en el panel **debe** alimentar **ambos** chats. Se blinda con un test que
prueba los **dos caminos de resolución** (chatbot y asistente), no solo el resolver.
Proveedores adicionales: fuera de alcance, se verán en el futuro.

## Por qué
Hoy la key vive **solo en env** (SH-2). El owner necesita rotarla/editarla desde el panel sin tocar
infra. Es *credential-at-rest*: cifrado en reposo, sin exposición en GET/audit/UI, admin-only.

## Estado verificado (no re-chequear)
- `app/config.py:116` — `get_settings()` con `@lru_cache`; `cache_clear()` disponible.
- `app/services/llm.py:28` — `CHAT_MODEL` capturado import-time (es el **modelo**, no la key → no bloquea).
- `app/services/llm.py:38-49` — `openai_client(provider)` llama `get_settings()` **per-call** y resuelve
  `key = deepseek_api_key if provider=="deepseek" else openrouter_api_key`. Ya es per-call.
- Consumidores: **chatbot** `openai_client()` sin arg → `chat_provider` (`chat/graph.py:115,118`,
  `chat/nodes/*`); **asistente panel** `openai_client(assistant_chat_provider)`
  (`chat/assistant/nodes.py:231-233`, `services/agent_chat.py:307-309`).
- `infra/docker-compose.yml:104,114` y `infra/.env.example:34,43` → hoy **ambos** son `deepseek`.
- `settings` KV: JSONB plano, `set_setting` audita `after={"value": value}` (`services/settings.py:218-239`)
  → meter un secreto ahí lo **filtraría** en `audit_log`.
- DB: PostgreSQL 16 (imagen pgvector). Última migración `052_memory_handoff.sql` → la nueva es **053**.
  `cryptography` **no** está en `pyproject.toml`. `pgcrypto` no se usa.
- `tests/integration/test_migrations.py:746` exige la **lista exacta** de migraciones (gotcha conocido).

## Decisiones cerradas (owner, 2026-10-13)
- **Precedencia**: la key en **DB overridea el env**. Env = fallback/bootstrap; DB = override opcional.
- **Aplicación**: **hot-apply** con **caché en proceso + TTL (~30-60s)**. Sin restart. (Leer DB por
  request = ineficiente; restart-required = downtime.) TTL porque la invalidación on-write no cruza
  workers de uvicorn.
- **Almacenamiento**: **tabla dedicada** `panel_secrets` + **cifrado de aplicación AES-256-GCM**
  (`cryptography`), **KEK desde env** (`SETTINGS_ENCRYPTION_KEY`). KEK separada de la DB → un `pg_dump`
  filtrado no expone la key. Descartados: KV en plano, `pgcrypto` (KEK en SQL), Vault/cloud SM
  (overkill), envelope DEK/KEK (overkill para 1 secreto).
- **UX**: ping `GET https://api.deepseek.com/models` con Bearer (200 válida / 401 inválida / **402
  válida-sin-saldo**); leyenda de origen (env / panel / ninguna); enmascarado solo últimos 4;
  **write-only** (el GET nunca devuelve la key); **audit redactado** (nunca el valor).

## Restricciones
- El backend corre DESDE el worktree; un solo stack `infra` a la vez.
- **TDD estricto activo** (`openspec/config.yaml`: `testing.strict_tdd=true`). RED → GREEN → REFACTOR.
  Runner backend `uv run pytest tests/`; frontend `cd web && npm test`; build/typecheck `cd web && npm run build`.
- DB de test: `bash infra/test-db.sh up` + `eval "$(bash infra/test-db.sh env)"`.
- Commit Conventional, **sin atribución de IA**. RDD activo.
- Tests con key **falsa** (`sk-test`); nunca real.

## Alcance
- Backend: `db/migrations/053_panel_secrets.sql`, `app/models.py`, `app/config.py`,
  `app/services/crypto.py` (nuevo), `app/services/model_secrets.py` (nuevo), `app/services/llm.py`,
  `app/panel/api/routes/settings.py`, `pyproject.toml`, `infra/.env.example`, `infra/docker-compose.yml`.
- Frontend: `web/src/api.ts`, `web/src/components/pages/Settings.tsx` + tests.

## Fuera de alcance
- Multi-proveedor (OpenRouter editable desde el panel). Solo DeepSeek por ahora.
- Rotación automática / expiración / envelope encryption.
- Si el asistente se apunta a OpenRouter por env, ese consumidor queda fuera (necesita `OPENROUTER_API_KEY`).

## Tareas (IDs estables)

### Work unit 1 — Almacén cifrado del secreto (backend core)
- [x] **AK-1 — Migración.** `db/migrations/053_panel_secrets.sql`: tabla
  `panel_secrets(key text PRIMARY KEY, ciphertext bytea NOT NULL, nonce bytea NOT NULL, updated_by int
  REFERENCES users(id), updated_at timestamptz NOT NULL DEFAULT now())`. Rollback comentado. **Agregar
  `("053_panel_secrets",)` a `tests/integration/test_migrations.py`.**
- [x] **AK-2 — Modelo ORM.** `PanelSecret` en `app/models.py`.
- [x] **AK-3 — Config KEK.** `settings_encryption_key: str | None = None` en `app/config.py`; documentar en
  `infra/.env.example` (con comando de generación) y pasar en `infra/docker-compose.yml`.
- [x] **AK-4 — Cifrado.** `app/services/crypto.py`: AES-256-GCM. `encrypt(plaintext) -> (ciphertext, nonce)`,
  `decrypt(ciphertext, nonce) -> str`; KEK derivada de `settings_encryption_key`; error claro si falta.
- [x] **AK-5 — Dependencia.** `cryptography` en `pyproject.toml`.
- [x] **AK-6 — Servicio de secretos.** `app/services/model_secrets.py`: `get_model_api_key(session)`
  (DB → env), `set_model_api_key(session, key, actor)` (cifra + audit redactado `model_api_key.set`),
  `clear_model_api_key(session, actor)` (`model_api_key.clear`). El audit **nunca** guarda el valor.
- [x] **AK-7 — Tests unit.** Round-trip crypto; KEK faltante → error claro; audit redactado (el valor
  NO aparece en `audit_log`).

### Work unit 2 — Resolución hot-apply en runtime
- [x] **AK-8 — Resolver con caché.** `model_secrets.resolve_model_api_key()` con caché en proceso
  (valor + expiración, TTL ~30-60s) que lee la DB vía `session_scope()`; fallback a env.
  `invalidate_model_key_cache()` para invalidación on-write.
- [x] **AK-9 — Wiring en `llm.py`.** `openai_client(provider)`: para `deepseek` resuelve vía el resolver
  (no `settings.deepseek_api_key` directo); `openrouter` sin cambios. Mismo error claro si no hay key.
- [x] **AK-10 — Tests del requisito duro.** Probar que la key del panel alimenta **AMBOS** caminos:
  `openai_client()` (chatbot, `chat_provider=deepseek`) **y** `openai_client("deepseek")` (asistente,
  `assistant_chat_provider=deepseek`); fallback a env cuando no hay key en DB; `openrouter` sigue usando su key.

### Work unit 3 — API del panel (write-only + ping)
- [ ] **AK-11 — Validación por ping.** Ping `GET https://api.deepseek.com/models` (httpx, Bearer candidata):
  200 → válida; **402 → válida sin saldo (aceptar)**; 401 → rechazar; timeout/error → 502 con mensaje.
- [ ] **AK-12 — Rutas.** `app/panel/api/routes/settings.py`: `POST /panel/api/settings/model_api_key`
  (admin-only; body `{api_key}`; valida, cifra, invalida caché); `DELETE .../model_api_key` (clear).
  El GET suma un bloque `model_api_key: {configured, source: "env"|"panel"|"none", masked}` — **nunca** el valor.
- [ ] **AK-13 — Tests functional.** POST válido/inválido (mockeando el ping), DELETE, el GET nunca expone
  la key, admin-only (operador → 403).

### Work unit 4 — Frontend
- [ ] **AK-14 — Cliente API.** `web/src/api.ts`: tipos + get status / post key / delete key.
- [ ] **AK-15 — Sección en Settings.** `web/src/components/pages/Settings.tsx`: sección "API key de modelos"
  en `SECTIONS`: input password + Guardar (POST) + Borrar (DELETE) + leyenda de origen
  ("Configurada en el servidor (variable de entorno)" / "Configurada desde el panel" / "No configurada") +
  enmascarado + feedback del ping (válida / sin saldo / inválida).
- [ ] **AK-16 — Tests frontend.**

## Verificación
- Backend: `uv run pytest tests/` (verde). Incluye migraciones, crypto, resolver, rutas.
- Frontend: `cd web && npm test` (verde) + `cd web && npm run build` (incluye `tsc -b`).
- Prueba manual: setear key desde el panel → confirmar que el asistente y el chatbot responden sin restart.

## Entrega (delivery)
- Forecast ~550-700 líneas autoradas (incluye tests) → **supera ~400** → estrategia `ask-on-risk`.
- Slices naturales (chained PRs): **PR1** = WU1+WU2 (almacén + runtime, core security); **PR2** = WU3 (API);
  **PR3** = WU4 (frontend). Cada PR ≤400 líneas.
- Base `origin/main`; integrar `origin/main` antes del PR; CI verde (`test` + `panel`).

## Riesgos / notas
- **Credential-at-rest**: nunca filtrar la key en logs, audit, tests, ni UI. Tests con `sk-test`.
- La KEK (`SETTINGS_ENCRYPTION_KEY`) viene de settings → cambiarla requiere **restart** (la key del modelo no).
- Al tocar `llm.py` revisar que los conftest fuerzan `DEEPSEEK_API_KEY=sk-test` y mockean `POST /chat/completions`.
- Grafo consultado (Graph Check): comunidades `session_scope`, `get_settings`, `routes/settings.py`,
  `agent_chat.py`, `chat/graph.py`, `Settings.tsx`, `api.ts`. Sin path directed `llm.py → routes/settings.py`
  (el cableado es nuevo).

## Evidencia (PR1 — WU1+WU2)
- `uv run pytest tests/` → **1974 passed**, exit 0 (12 tests nuevos sobre los 1962 de `main`).
- Tests nuevos: `tests/unit/test_model_secrets.py` (5), `tests/integration/test_model_secrets.py` (1, requisito duro).
- **Gotcha encontrado y corregido**: la migración `053` creaba `panel_secrets` sin `GRANT` al rol `app`
  (least privilege) → el resolver chocaba con `permission denied` en cada llamada al LLM, tumbando ~40
  tests de chat. Fix: `GRANT SELECT, INSERT, UPDATE, DELETE ON panel_secrets TO app;`.
- **Gotcha encontrado y corregido**: `panel_secrets` faltaba en `EXPECTED_TABLES` (`test_migrations.py`).
- La DB de test se reseteó (`test-db.sh down`+`up`) para reaplicar la migración con el GRANT.
