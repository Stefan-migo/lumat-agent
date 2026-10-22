# HANDOFF — Configurabilidad del chatbot + asistente Lumat como optimizador

Date: 2026-10-13. Estado: `main` = `c8865f10`. **Este hilo es de DISEÑO — no se escribió código para la parte de "asistente optimizador".**

## De qué trata
Panorama y dirección sobre: (a) cuán configurable es el chatbot de WhatsApp, (b) una UI completa de configuración, y (c) darle al **asistente Lumat del panel** herramientas para **analizar → sugerir → (con aprobación) aplicar** mejoras al chatbot.

## Precedente ya mergeado en la sesión
- **PR #572** `odd/chatbot-visit-duration` → **duración de visita por servicio** vía mapa `booking.service_durations` (default vacío → 60). Merge `c8865f10`. La tool del chatbot ya resuelve por `case.service` (cupos + commit).
- **Conversaciones S2** (cerrada como no-change) y **S3** (verificada). Ver `odd/handoffs/lumat-thread-agenda-conversations.md`.

## Hallazgos clave (verificados)

### Configurabilidad del chatbot, por niveles
- **A — dato + UI (Settings del panel):** mensajes estándar (saludo, despedida, aclaración, "no puede responder", fuera de horario), tono, horarios + zona horaria, keywords de emergencia, reglas de derivación por categoría (`bot_resolve`/`always_escalate`), límites de gasto, costo Meta, capacidades del asistente.
- **B — dato, SIN UI (seed/DB):** `booking.service_durations`, `cost.llm_rates`, `kpi.window_days`.
- **C — código/prompt (NO dato):** taxonomía de intenciones + contrato JSON, campos de captura, umbrales de derivación, TTL/ventana/N de cupos.
- **D — contenido:** documentos de la KB (subida por panel).
- Todo A/B vive en **una tabla KV** (`settings`), lectura `get_setting`, escritura `set_setting` **auditada**.

### Dónde viven los prompts
- `agent/personas/*.md` (orchestrator, **classify**, assistant, research_triage, retrieval, customer_records, escalation, human_handoff, summary), `agent/prompts/*.md` (respond, classify, assistant_plan, assistant_respond, summary), `agent/skills/*.md` (capture, emergency, handoff), `agent/registry.yaml`.
- Loader: `app/services/prompts.py` (`load` = verbatim, `render` = sustituye `{{}}`).
- **Prompts = CÓDIGO:** `app/services/prompts.py:34-36` tiene `FALLBACKS` **byte-idénticos** a cada `.md`, y un test lo verifica (`FALLBACKS[key] == agent/file`). Cambiar un prompt = editar `.md` + fallback + tests + commit + deploy. **No es hot-swap.**

### `registry.yaml` = 3 roles bajo el MISMO esquema
- `agent:` = **chatbot** WhatsApp (persona orchestrator + skills emergency/handoff/capture, `tools_whitelist: []`).
- `sub_agents:` = sub-agentes del chatbot (research_triage, retrieval, customer_records, human_handoff, escalation; `memoria_scope: customer`).
- `assistant:` = **asistente Lumat del panel** (persona `assistant.md`, skill `memoria-tukulpan`, prompts `assistant_plan/respond.md`, la lista grande de tools, `memoria_scope: panel`).
- Loader: `app/agent_registry.py` (valida y cachea el registry en la construcción del grafo). **Settings → Capacidades** ya lista las tools por rol con niveles (`todos / solo lectura / puede escribir / limitado`).

## Diseño acordado (dirección)
- Flujo: **`analizar (read-only) → proponer → aprobar → aplicar`**.
- **Nivel 1-2** (settings) → `set_setting` en vivo, auditado, reversible, sin deploy.
- **Nivel 4** (prompts) → **PR generado por el asistente**, revisado/mergeado/deployado por el humano. Nunca mutación en vivo.
- **Libertad:** mucha en leer/proponer; escribir = **aprobar-y-aplicar** (el contrato de tools ya tiene `requires_approval`).
- **Delegación:** un **subagente solo para análisis/draft** (comprime contexto); la **aprobación + el apply** se quedan en el asistente principal. Un subagente NO muta settings solo.

## Próximo (unidades propuestas, en orden)
1. **`analytics.chatbot_metrics`** — tool **read-only** para el asistente: contención/deflexión, tasa de derivación, intenciones `unknown`, turnos hasta resolver, hit de KB, costo por conversación. ← **arrancar acá.**
2. **Loop de aprobación** para writes Nivel 1-2 (sugerir → aprobar → `set_setting`).
3. **Nivel 4:** cambios de prompt como **PRs generados por el asistente**.
4. **(Opcional)** exponer Nivel B en Settings (duración por servicio, tarifas LLM).

## Gotchas
- Prompts **byte-acoplados** a `FALLBACKS` (test) → editar prompt obliga a tocar `app/services/prompts.py`.
- `booking.service_durations` vacío → **60** (el chatbot sigue en 1 hora hasta cargar valores).
- Test DB por worktree: copiar `infra/.env` de main (gitignored) + `infra/test-db.sh up`.
- Disciplina pre-merge: mergear `origin/main` a la branch antes de mergear el PR (fuerza CI sobre el árbol real).
- La pestaña Settings es **por secciones** (no KV libre): exponer claves nuevas = agregar sección.

## Entorno / referencias
- `main` = `c8865f10`.
- Archivos: `app/services/settings.py`, `app/services/prompts.py`, `app/agent_registry.py`, `agent/registry.yaml`, `agent/personas/*.md`, `agent/prompts/*.md`, `app/chat/nodes/capture.py`, `app/panel/api/routes/settings.py`, `web/src/components/pages/Settings.tsx`.
- Engram: `odd/chatbot-visit-duration/{landscape,decision,tasks,pr,close}`, este handoff.
