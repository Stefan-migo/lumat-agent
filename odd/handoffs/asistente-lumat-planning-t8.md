# HANDOFF — Asistente Lumat: T8 (handoff planning → SDB)

**Fecha**: 2026-10-14. **Estado**: el núcleo guiado de las Sesiones de planificación está **mergeado** (`main` = `82210e1a`, PR #595). Lo único pendiente del feature es **T8 (S9)**: el handoff de la sesión de planning al ejecutor SDB. Nada de T8 está implementado.

## Estado git
- `main` = `origin/main` = `82210e1a` (merge del PR #595). Contiene el feature de planning guiado.
- Branch `odd/asistente-lumat-planning-guiado` **borrado** (local + remoto); worktree `../lumat-agent-odd-asistente-lumat-planning-guiado` **removido**.
- Worktrees vivos (NO tocar): `../lumat-agent-odd-chatbot-conversation-inspection`, `../lumat-agent-odd-panel-visual-alignment`.
- Doc del feature (en main): `odd/tasks/asistente-lumat-planning-guiado.md` — Specs S1–S10, tareas T1–T8, log, verificación.

## Qué se entregó (para contexto)
Sesión de planning = **brainstorming guiado** por un agente-facilitador, en **hilo propio**, con captura explícita y reporte sustantivo:
- `planning.open`/`planning.close`/`planning.record_decision`/`planning.record_note` (`app/services/planning.py` + `app/chat/assistant/tools/registry.py`).
- Hilo propio (`planning.open_in_new_thread`) + evento SSE `planning` + switch de UI al asentar el run.
- Overlay facilitador (`agent/prompts/planning_facilitator.md`, inyectado solo con sesión activa).
- Reporte markdown sustantivo (objetivo/decisiones/riesgos/próximos pasos/notas/gaps) en Tukulpan scope `agent`.
- Contrato de cierre: mínimo = objetivo + ≥1 decisión; los faltantes son **gaps**; **el cierre nunca se bloquea**.

## Qué es T8 (S9) — y su dependencia de "Slice 5"
T8 = **handoff de la sesión de planning al ejecutor SDB**: al cerrar, si el tema es de Lumat y hay una **acción concreta**, el agente **ofrece** el handoff y **el usuario lo confirma**; nunca se infiere de texto libre (D6). Si no es de Lumat o no hay acción, queda **solo el reporte**. La sesión es read-only para el negocio (D16): la ejecución no ocurre dentro de la sesión.

**La dependencia "Slice 5" ya está resuelta.** El "Slice 5" al que el diseño de planning difirió = el refactor **SDB = loop + verify** (D14/D15), que es un **feature ODD aparte** (`odd/tasks/asistente-sdb.md`), no parte del feature de planning. Estado real de ese refactor en `main`:
- **Slices 1–7 mergeados** (PRs #489, #490, #491, #506, + slice 7). SDB ya **no** es un subgrafo de 7 fases: es el loop normal + un paso `verify`.
- `app/chat/assistant/verification.py` **existe**: `EFFECT_TOOLS` (~línea 11), `verification_required(dispatched_tools, explicit, handoff)` (~24), `run_verification` (~74). Verificador read-only de contexto fresco.
- **`sdb_requested` existe y es admin-only** (`app/panel/api/routes/chat.py` → 403 para no-admin). El doc de SDB dice explícito: *"The optional Cortex→SDB handoff reuses the existing admin-only `sdb_requested` flag"*.
- **Pendiente del refactor SDB: solo Slice 8** = cablear el verificador al camino de servicio aprobado (`approve_plan → execute`) para que D15 cubra `project.*`/`automation.create_rule`. (No bloquea a T8; sí conviene saberlo.)

**Implicancia para T8**: "handoff a SDB" ya NO significa "crear una tarea SDB" (esa maquinaria se borró en el Slice 6 del refactor SDB). Significa: **llevar la acción confirmada de la sesión a un turno de ejecución con verificación**, reusando `sdb_requested` (admin-only) como el disparador de handoff del `verification_required`.

## Alcance propuesto de T8 (a confirmar al arrancar)
1. **Oferta en el cierre**: cuando `planning.close` detecta que el tema es de Lumat **y** hay una acción concreta (p. ej. próximos pasos / decisión con efecto), el agente **ofrece** el handoff — nunca automático.
2. **Confirmación explícita**: el handoff se dispara solo si el usuario (admin) confirma; el agente no lo infiere.
3. **Reuso de `sdb_requested`**: el handoff setea esa flag (admin-only) en el turno de ejecución correspondiente; no se inventa un mecanismo nuevo.
4. **Condicional**: si no es de Lumat o no hay acción concreta → sin handoff, solo el reporte.
5. **Read-only intacto (D16)**: la sesión no ejecuta tools de negocio; la ejecución va al loop+verify.

### Criterio de aceptación observable
- Al cerrar una sesión de Lumat con acción concreta, el agente **ofrece** "cerrar con reporte + handoff"; con confirmación del admin, el handoff queda registrado (vía `sdb_requested` / el turno de ejecución), con verificación.
- Un usuario no-admin no puede disparar el handoff (403, igual que hoy).
- Un cierre sin Lumat o sin acción concreta **no** genera handoff.
- El agente **nunca** infiere el handoff de texto libre.

## Archivos a explorar/tocar
- `app/services/planning.py` — `close_session` / `build_report` / `report_gaps` (dónde engancha la oferta de handoff).
- `app/chat/assistant/tools/registry.py` — `_planning_close` (result shape; hoy devuelve `gaps`/`minimum_met`).
- `app/chat/assistant/verification.py` — `verification_required` / `EFFECT_TOOLS` / `run_verification`.
- `app/chat/assistant/nodes.py` — call site de `verification_required(...)` (~:850) y el nodo `verify_effects`.
- `app/services/agent_chat.py` — plumbing de `sdb_requested` en `run_agent_turn`/`_run_agent_turn_session`.
- `app/panel/api/routes/chat.py` — gate admin de `sdb_requested` (403).
- `app/chat/assistant/state.py` — campo `sdb_requested`.
- `agent/prompts/planning_facilitator.md` — overlay (agregar la regla de oferta/confirmación).
- `odd/tasks/asistente-sdb.md` — contexto y contrato de SDB (SDB-16: `sdb_requested` admin-only).

## Decisiones cerradas (no re-litigar)
- D6: handoff **opcional**, **admin-only**, **nunca** inferido de texto libre.
- D16: la sesión de planning es **read-only** para el negocio.
- D2/D18: **un** artefacto = el reporte; el handoff es adicional y condicional.
- El refactor SDB (loop + verify) reusa `sdb_requested`; no crear maquinaria SDB nueva.
- Núcleo guiado (S1–S8): cerrado y mergeado — no re-abrir.

## Reglas del repo
- ODD worktree por feature con consentimiento: `../lumat-agent-odd-<slug>` en `odd/<slug>`; doc en `odd/tasks/<slug>.md`. Provision: `rapso` NO hace `uv sync` ni `.env` → a mano (`uv sync --frozen`, `cp ../lumat-agent/infra/.env infra/.env`, `cd web && npm ci`, `bash infra/test-db.sh up`).
- Strict TDD ON. Runner: `uv run --no-sync pytest tests/` (**suite completa**, secuencial) con `eval "$(bash infra/test-db.sh env)"`.
- Si se toca `web/`: `npm test` + `npm run build`.
- Graph Check (`graphify query`) antes de editar; refresh del grafo al cerrar sesión.
- Commits conventional, sin `Co-Authored-By`. PR base `main`, un label `type:*` (y `size:exception` si >400 líneas), **sin `Closes`**.
- Pre-merge (obligatorio): el branch debe contener `origin/main`; correr backend + frontend + build sobre el árbol mergeado.
- RDD on por defecto: `gentle-ai review assess --cwd <wt> --base-ref <boundary> --committed-only --json`; `under_budget` → `review_due:false` (el boundary se acumula).

## Open questions
- ¿El "handoff" dispara un **turno de ejecución verificado** en el mismo hilo de planning, o en un hilo nuevo del ejecutor? (Elegir con evidencia del flujo actual de `sdb_requested`.)
- ¿Cómo se determina "acción concreta" sin inferir de texto libre? (¿Una tool explícita de confirmación de handoff?)
- ¿Coordinar con **Slice 8** de SDB (verificador en el camino de servicio aprobado)?

## Referencias
- Doc del feature: `odd/tasks/asistente-lumat-planning-guiado.md`.
- Doc de SDB: `odd/tasks/asistente-sdb.md`.
- Engram: `odd/asistente-lumat-planning-guiado/tasks`; sesión `cortex-session/2026-10-13-asistente-lumat-planning/*`; `handoff/asistente-lumat-planning-t8`.
