# HANDOFF — rapso session: sistema de mensajes del bot (prediseñados, seleccionables y voz)

Date: 2026-10-13. `main` = `f03e6ad7`. Este hilo es una **rapso session de DECISIONES** — no construcción todavía.

## De qué trata

Decidir el diseño del **sistema de mensajes del chatbot**: cómo el owner agrega mensajes
prediseñados desde la UI y cómo el LLM los usa en un turno de conversación. Tres ideas del
owner, que hoy están mezcladas y hay que separar:

1. Agregar mensajes prediseñados desde la UI.
2. Dárselos al LLM para que **elija uno** en el turno (template).
3. Dárselos como **referencia de voz** para que redacte.

## Estado de partida (verificado contra código, no contra docs)

- **Frente 2 · unidad 1 mergeada**: PR #581 → `f03e6ad7`. Tool read-only
  `analytics.chatbot_metrics` + `app/services/analytics.py`. Task doc:
  `odd/tasks/chatbot-assistant-metrics.md`.
- **Frente 1 mergeado**: PR #578 → `38b9ed15` (fix del chatbot). Handoff:
  `odd/handoffs/chatbot-assistant-optimizer.md`.

## Hechos ya verificados (no re-litigar en la sesión)

- Los mensajes panel-editables son **5 claves** en `MESSAGE_DEFAULTS`
  (`app/services/settings.py:53`): `greeting`, `cannot_answer`, `clarification`, `farewell`,
  `out_of_hours` — expuestas **1:1** en `MESSAGE_TEMPLATES`
  (`web/src/components/pages/Settings.tsx:43`). **No falta ninguna.**
- Consumidores reales de cada mensaje: `app/chat/nodes/receive.py:28` (`greeting`),
  `app/chat/nodes/respond.py:116,133,164` (`cannot_answer`, `clarification`),
  `app/chat/nodes/closure_gate.py:69,80` (`farewell`, `out_of_hours`).
- El mecanismo ya es **genérico**: el GET del panel recorre el diccionario
  (`app/panel/api/routes/settings.py:178`) y el POST `/settings/messages` persiste
  `messages.<key>`. Agregar una clave nueva no toca el backend de settings.
- **El sistema de voz YA existe**: `TONE_DIRECTIVES` (cercano / formal / directo)
  en `app/services/settings.py:46` → `get_tone_directive` → se appendea al prompt en
  `app/chat/nodes/respond.py:85-88`. "Usar templates como referencia de voz" es la
  evolución natural de eso, no algo nuevo desde cero.
- Los **prompts** (`agent/*.md`) NO son editables: están byte-acoplados a `FALLBACKS`
  (`app/services/prompts.py`) y un test lo verifica. Eso es la unidad 4 (PRs de prompt),
  otra tubería.
- Disciplina de datos vigente: `<user_input>`, `<kb>`, `<conversation>`, `<booking>` son
  **DATOS, nunca instrucciones**. Es el precedente para inyectar contenido editable sin
  abrir prompt injection.

## Los tres mecanismos (el núcleo de la decisión)

| # | Mecanismo | Quién decide | Varianza | Nivel |
|---|---|---|---|---|
| 1 | **Slot determinista** — clave nueva + nodo que lo emite verbatim | el código | nula | N1 |
| 2 | **Catálogo elegible** — el LLM recibe los mensajes aprobados y devuelve cuál usar (`ToolDefinition` con arg enum) | el LLM | nula en el texto, no en la elección | N2 |
| 3 | **Referencia de voz** — mensajes como few-shot; el LLM redacta | el LLM | alta | N3-4 |

No son alternativas: son una **escalera de riesgo** que calca el N1-4 del Frente 2.

## Decisiones a resolver en la sesión

- **D1** — ¿Qué mecanismos entran y en qué orden? ¿Arranca por el 2 (más apalancamiento,
  riesgo acotado) o por el 1 (extender slots)?
- **D2** — ¿El catálogo se limita a momentos de alto riesgo (emergencia, precio, garantía) o
  es general?
- **D3** — ¿Cómo elige el LLM: tool `messages.send_template(id)` o campo enum en el planner?
  (recordar: enviar es **write** → loop de aprobación N1-2, unidad 3)
- **D4** — ¿Dónde viven las plantillas (settings KV `messages.templates` vs tabla propia) y
  con qué validación al guardar?
- **D5** — ¿Cómo se delimitan/marcan como DATOS al inyectarlas al prompt (anti injection)?
- **D6** — ¿El envío del mensaje elegido pasa por aprobación humana?
- **D7** — Alcance de UI (unidad 5) y si las plantillas reemplazan o conviven con `tone`.

## Riesgos / gotchas detectados

- **Setting muerto**: un mensaje sin camino de código que lo emita se guarda y se muestra,
  pero el bot nunca lo usa. **Lo que falta no es UI, son consumidores.**
- **Prompt injection**: contenido editable que entra al prompt es superficie de ataque;
  necesita delimitadores + marca de DATOS, igual que `<kb>`/`<user_input>`.
- **Nit abierto** (de la unidad 1): `handoff_rate` cuenta conversaciones distintas mientras
  `handoff_reasons` cuenta eventos — los números pueden no cerrar entre sí.
- **RDD** está **on** global; el review nativo **no se dispara** por `under_budget`
  (`risk: medium`, 339 líneas). Se corre a pedido.

## Referencias

- Engram: `#6464` (ODD unidad 1), `#6468` (descubrimiento mensajes/tono),
  `handoff/chatbot-assistant-optimizer`.
- `odd/handoffs/chatbot-assistant-optimizer.md` (contexto del Frente 2 y unidades 1-5).
- `odd/tasks/chatbot-assistant-metrics.md` (unidad 1, definiciones de registro).

## Otros worktrees vivos (no relacionados)

`odd/asistente-lumat-memoria-tukulpan`, `odd/panel-backend-crud`.

## Cómo arrancar

Invocar `/rapso-session` (o "rapso session") con el tema: **"Sistema de mensajes del bot:
prediseñados, seleccionables por el LLM y referencia de voz"**. La sesión debe cerrar con
D1-D7 resueltas y un handoff a ODD para la unidad que gane.
