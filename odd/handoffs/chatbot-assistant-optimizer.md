# HANDOFF — Frente 2: Asistente Lumat como optimizador del chatbot (unidades 4-5)

Fecha: 2026-10-14. `main` = `41e517ff`. **Este hilo continúa el Frente 2.** Las **unidades 1, 2 y 3
están mergeadas** (métricas + inspección + write con aprobación). El **Frente 1 (arreglar el bot)
está cerrado**. Próximo paso: **unidad 4 (PRs de prompt — standby del owner)** o **unidad 5 (UI)**.

## De qué trata
Darle al **asistente Lumat del panel** herramientas para **leer → analizar → proponer → (con
aprobación) aplicar** mejoras al chatbot de WhatsApp. Tres capas:

1. **Leer** — el asistente ve cómo le va al bot (métricas + conversaciones reales). Read-only.
2. **Analizar/proponer** — interpreta las métricas y arma una propuesta concreta.
3. **Aprobar/aplicar** — el humano aprueba; el asistente aplica settings en vivo (N1-2) o genera un
   PR de prompt (N4).

## Estado de las unidades
- **Unidad 1 — MERGEADA** (PR #581): tool read-only `analytics.chatbot_metrics` +
  `app/services/analytics.py`. Task doc: `odd/tasks/chatbot-assistant-metrics.md`.
- **Unidad 2 — Inspección de conversaciones — MERGEADA** (PR #596): dos tools read-only
  `analytics.chatbot_conversations` (encuentra conversaciones por señal: escalation /
  unknown_intent / kb_miss / any) + `conversations.transcript` (metadata + últimos mensajes +
  eventos). Task doc: `odd/tasks/chatbot-conversation-inspection.md`.
- **Unidad 3 — Loop de aprobación — MERGEADA** (PR #597): tool write `settings.update` con
  aprobación (sugerir → aprobar → `set_setting` auditado). Allowlist server-side: `tone.style`,
  6 `messages.*`, `hours.timezone`, `hours.schedule`. ADMIN-only, no autónoma, nunca en subagentes.
  Task doc: `odd/tasks/chatbot-assistant-settings-write.md`.
- **Unidad 4 — PRs de prompt** (Nivel 4): **standby explícito del owner** — no tocar sin conversarlo.
- **Unidad 5 — UI** ← **arrancar acá en chat nuevo**: secciones nuevas en Settings + vista de
  métricas/conversaciones. La parte de mensajes quedó resuelta por el catálogo (D7).
  **Handoff dedicado: `odd/handoffs/chatbot-assistant-optimizer-unit5-ui.md`.**

## Frente 1 (cerrado — no volver salvo regresión)
- `chatbot-conversation-fixes` (PR #578), `chatbot-message-catalog` (PR #591),
  `chatbot-first-turn-greeting` (PR #593, `main` = `36c57d29`).

## Contrato de tools del asistente (verificado)
- **`app/chat/assistant/tools/registry.py`** — `@dataclass(frozen=True) ToolDefinition`, modelos
  Pydantic de args (ya existen `KpiArgs`, `OperationalHistoryArgs`), `tool_schemas()`,
  `execute_tool()`.
- **Fuente de verdad:** `app/agent_registry.py:31` `KNOWN_TOOLS = tuple(TOOL_REGISTRY)`. Una tool
  nueva debe estar en `TOOL_REGISTRY` **y** whitelisteada en `agent/registry.yaml`
  (`assistant.tools_whitelist`), o el grafo no construye.
- **Materia prima ya existente:** `app/services/dashboard.py` (`compute_kpis(window_days)`),
  `app/services/costs.py`, `app/services/conversations.py`, `app/services/analytics.py` (unidad 1).
- **Settings:** `app/services/settings.py` (KV `settings`, `get_setting`/`set_setting` auditado),
  `app/panel/api/routes/settings.py`, `web/src/components/pages/Settings.tsx` (por secciones).

## Gotchas (verificados)
- `agent/*.md` están **byte-acoplados** a `FALLBACKS` (`app/services/prompts.py`), con guard en
  `tests/unit/test_prompts.py::test_fallbacks_equal_agent_files`: tocar un prompt obliga a
  actualizar el fallback byte-idéntico.
- La suite del clasificador es un **mock keyword-based** (`tests/integration/conftest.py`): prueba el
  wiring, no la calidad real.
- **No confundir los "asistentes":** el **chatbot** de WhatsApp = `deepseek-chat` + nodos LangGraph;
  el **Agente Lumat** del panel = `gemini-2.5-flash` + `ToolDefinition`/registry.
- `prompts.render` hace sustitución **estricta** de `{{slots}}` (KeyError si falta o sobra una).

## Ambiente y restricciones
- **Strict TDD ON** (`openspec/config.yaml`). Runner: `uv run pytest tests/`. La suite backend tarda
  ~7-8 min (**2044 tests** al 2026-10-14).
- **Worktree por feature:** `rapso worktree create <slug>` → `../lumat-agent-odd-<slug>`, branch
  `odd/<slug>`. Task doc en `odd/tasks/<slug>.md` (viaja a `main` por el PR).
- **GOTCHA de worktree nuevo:** NO trae `.venv` ni `infra/.env` → correr `uv sync` y
  `cp ../lumat-agent/infra/.env infra/.env`. Test DB:
  `bash infra/test-db.sh up` + `eval "$(bash infra/test-db.sh env)"`.
- **GOTCHA de cleanup:** `rapso worktree cleanup` NO baja el test DB del worktree (queda el
  contenedor corriendo) → `docker rm -f lumat-test-<slug>-db-test-1` +
  `docker network rm lumat-test-<slug>_default`.
- **GOTCHA de merge:** `gh pr merge --delete-branch` puede fallar al borrar el branch remoto si el
  checkout local de `main` choca con el worktree principal (el merge sí se aplica) → borrar el remote
  a mano (`git push origin --delete <branch>`).
- **Pre-merge (obligatorio):** traer `origin/main` a la branch + correr la integración local
  (backend `pytest` + `npm test` + `npm run build`) sobre el árbol mezclado; auto-merge NO; mergear
  solo con el PR `CLEAN` y el HEAD local == el `headRefOid` que GitHub testeó. El repo tiene ruleset
  con los checks `test` y `panel`.
- **Frontend:** `tsc -b` vive solo dentro de `npm run build`; un vitest verde NO prueba que tipa.
- **RDD:** on global; `under_budget` no dispara review. **Confirmar con el owner antes** de invocar el
  review nativo.
- **Otros worktrees vivos (ajenos — no tocar, tienen sus propios agentes):**
  `odd/asistente-lumat-planning-guiado`, `odd/panel-api-key-followups`, `odd/panel-visual-alignment`.

## Referencias
- Handoff previo del frente: Engram **#6440** (`handoff/chatbot-assistant-optimizer`).
- Sesión de diseño del sistema de mensajes: Engram **#6505** (`session-summary/lumat-agent`) +
  `.rapsodia-code/sessions/.../2026-10-13-chatbot-message-system/`.
- Task docs: `odd/tasks/chatbot-assistant-metrics.md` (unidad 1),
  `odd/tasks/chatbot-conversation-fixes.md` (Frente 1).
- Cierre del Frente 1: `odd/tasks/chatbot-message-catalog.md`,
  `odd/tasks/chatbot-first-turn-greeting.md`.
