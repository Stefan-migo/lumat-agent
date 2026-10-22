# HANDOFF — Frente 2, unidad 5 (UI): superficies de panel para el optimizador

Fecha: 2026-10-14. `main` = `41e517ff`. **Hilo de DISEÑO + ODD — empezar por acordar el alcance con el owner.**
Este handoff es para arrancar en un chat nuevo. El Frente 2 (asistente Lumat como optimizador del
chatbot) tiene las **unidades 1-3 mergeadas**; **esta es la unidad 5**.

## Contexto: qué ya está mergeado (no re-hacer)
- **U1 — `analytics.chatbot_metrics`** (PR #581): métricas read-only del bot. Task doc `odd/tasks/chatbot-assistant-metrics.md`.
- **U2 — `analytics.chatbot_conversations` + `conversations.transcript`** (PR #596): inspección read-only de conversaciones. Task doc `odd/tasks/chatbot-conversation-inspection.md`.
- **U3 — `settings.update`** (PR #597): write con aprobación (proponer → aprobar → `set_setting` auditado). Allowlist: `tone.style`, 6 `messages.*`, `hours.timezone`, `hours.schedule`. ADMIN-only. Task doc `odd/tasks/chatbot-assistant-settings-write.md`.
- **U4** (PRs de prompt, Nivel 4): **standby explícito del owner** — no tocar.

## Qué es la unidad 5
Del handoff de diseño (`odd/handoffs/chatbot-config-and-assistant-tools.md`): UI = **secciones nuevas
en Settings + vista de métricas/conversaciones**. "La parte de mensajes quedó resuelta por el catálogo (D7)."

**Ojo:** a diferencia de U2/U3, la U5 es diseño/frontend y **el alcance exacto NO está cerrado**. Primer
paso obligatorio: **una conversación de scope con el owner** (skills `rapso-session` / `design-agent-lead`)
antes de escribir código. Superficies candidatas a decidir:
1. **Vista de métricas del bot** (containment, tasas de derivación, `unknown_intent`, kb-hit, costo/conversación).
2. **Inspector de conversaciones** (equivalente panel de `conversations.transcript`).
3. **Settings**: ¿hay secciones nuevas, o las de tono/mensajes/horas ya alcanzan?

## Lo que YA existe (verificado en `web/`)
- **Settings por secciones**: `web/src/components/pages/Settings.tsx` (+ `Settings.css`, `Settings.test.tsx`).
- **Conversaciones**: `web/src/components/pages/ConversationsList.tsx`, `ConversationThread.tsx`.
- **Dashboards**: `web/src/components/pages/Dashboard.tsx`, `AdvancedDashboard.tsx`.
- **Chat del asistente + tarjeta de aprobación (YA FUNCIONA)**: `web/src/components/pages/AgentChat.tsx`
  renderiza el plan con **aprobar/rechazar** (`approval_pending`), y llama `approveChatPlan`
  (`web/src/api.ts:173` → `POST /panel/api/chat/threads/{id}/approval`). La U3 reusa este flujo → la UI de
  aprobación **no** hay que construirla. `AssistantApproval` en `web/src/types.ts:188`.
- **Skills de diseño disponibles** (cargar antes de tocar UI): `design-system`, `component-adapter`,
  `design-agent-lead`.

## Restricciones / gotchas (verificados)
- **Frontend type-check:** `tsc -b` vive **solo** dentro de `npm run build`; un vitest verde **no** prueba
  que tipa. Correr ambos: `npm test` y `npm run build` (en `web/`).
- **Worktree nuevo:** NO trae `node_modules` → `npm install` (o `npm ci`) dentro de `web/`. Backend tampoco
  trae `.venv`/`env`: `uv sync` + `cp ../lumat-agent/infra/.env infra/.env`; test DB `bash infra/test-db.sh up`
  + `eval "$(bash infra/test-db.sh env)"`.
- **`rapso worktree create` corta desde `origin/main`, NO del main local** → verificar el head de `origin/main`
  antes del PR; si avanzó, mergear antes de pushear (disciplina pre-merge del repo).
- **Agregar/renombrar tools** rompe CUATRO lugares pineados (por si la U5 toca backend): `test_tool_tiers.py`,
  `test_effective_config.py`, el SHA-256 del planner-catalog en `test_assistant_delegation.py`
  (actual `f4bc1a5c…`), y el set OPERADOR en `test_assistant_tool_roles.py`.
- **Merge/cleanup:** `gh pr merge --delete-branch` falla el borrado local si `main` está en el worktree
  principal; usar `rapso worktree cleanup <slug> --remote`. El cleanup NO baja el test DB ni la network
  (`docker rm -f lumat-test-<slug>-db-test-1` + `docker network rm lumat-test-<slug>_default`).
- **Worktrees vivos ajenos (NO tocar):** `odd/panel-visual-alignment`, `odd/asistente-lumat-planning-handoff`.
- **RDD nativo:** no invocarlo sin confirmar antes con el owner (regla del hilo).
- **Pre-merge (obligatorio):** integrar `origin/main` + correr `npm test`, `npm run build` y `pytest` sobre el
  árbol mezclado; mergear solo con el PR `CLEAN` y HEAD == `headRefOid`.

## Referencias
- Handoff del frente: `odd/handoffs/chatbot-assistant-optimizer.md` (unidades 1-3 mergeadas).
- Diseño original: `odd/handoffs/chatbot-config-and-assistant-tools.md`.
- Task docs: `odd/tasks/chatbot-assistant-metrics.md`, `chatbot-conversation-inspection.md`,
  `chatbot-assistant-settings-write.md`.
- Engram: `handoff/chatbot-assistant-optimizer`.

## Primer paso sugerido
1. Conversación de scope con el owner (qué pantallas, qué reusa el chat del asistente vs. vista nueva).
2. `rapso worktree create <slug>` (con consentimiento explícito del owner) + task doc ODD.
3. Implementar con Graph Check + TDD/verificación de frontend proporcional.
