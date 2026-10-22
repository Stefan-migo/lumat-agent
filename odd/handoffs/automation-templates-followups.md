# HANDOFF — Automatizaciones: feature automation-templates mergeado + WU de seguimiento

Fecha: 2026-10-15. Estado: **WU-B + WU-C entregados y mergeados a `main`**. Queda 1 work unit nuevo de
seguimiento (template-izar las recetas que siguen free-form), más los ya anotados WU-D y WU-E.

## Qué se entregó (todo en `main`)

Feature doc: `odd/tasks/automation-templates.md` (specs S1–S7, tasks, log, verificación).
Doc de templates: `docs/meta-templates.md` (mapeado template → receta → renderer).

- **PR #634** `odd/automation-templates` → `main`, merge commit **`1ef128b0`**. Filtro `origin`: las
  recetas pueden declarar `conditions` exact-match; `appointment_confirmation` filtra `{"origin":"panel"}`
  y `book()` publica `origin` (`assistant` si reservó el chat, si no `panel`). Así la reserva por chat no
  se confirma dos veces.
- **PR #636** `odd/automation-templates-engine` → `main`, merge commit **`6422b179`**. (Reemplaza a #635,
  que GitHub autocerró al borrarse su rama base.) El motor entrega templates Meta: una receta declara
  `template_event`, y al enviar se resuelve la receta por
  `AutomationExecution.operation_id → AutomationRule.installation_id → recipe_id` y se manda con
  `notify.send_template` + `validate_channel_policy(business_initiated=True)`. El recordatorio 24h pasó a
  ser la receta `appointment_reminder` (scan `time_triggers._reminder_due` que publica
  `appointment.reminder_due`); el seguimiento al dueño pasó a dos recetas (`appointment_followup`,
  `appointment_followup_no_show`) con `delay_seconds=86400` que el motor respeta vía `next_attempt_at`.
  Se borraron `scheduling._maintain_reminder`, `scheduling._schedule_followup` y los branches hardcodeados
  `:reminder:24h` / `followup:*` de `notifications.process_operation`.

`main` = **`6422b179`**. Verificación: suite backend completa `EXIT=0`; verifier independiente S1–S7 MET,
0 blockers. Sin migración: no hace falta, la receta se resuelve en runtime.

## Estado del repo

- Worktree `../lumat-agent-odd-automation-templates` **removido**; ramas local y remota borradas.
- Test DB del worktree: apagada (`infra/test-db.sh down -v`).
- Otro worktree vivo, ajeno a esto: `../lumat-agent-odd-assistant-write-chaining` (detached HEAD
  `2514d9dc`; su contenido ya está mergeado por PR #633). No tocar.
- **Ojo**: el checkout principal `/home/stefan/repos/lumat-agent` quedó en `9f6da17e`, **detrás** de
  `origin/main`. Hay que `git pull` antes de arrancar el próximo worktree.

## WU-NUEVO — Templates Meta para las 9 recetas que siguen free-form

**Problema**: el motor ya sabe mandar templates, pero **9 recetas no declaran `template_event`** y siguen
saliendo por `send_text` free-form → fuera de la ventana de 24h de Meta, el mensaje no entrega. Es el gap
central #6633. El owner nombró `appointment_review_request` (pedido de evaluación post-visita) como el caso
concreto.

Recetas sin `template_event`: `appointment_confirmation`, `appointment_cancellation`,
`appointment_rescheduled`, `appointment_no_show`, `case_new_request`, `appointment_review_request`,
`customer_maintenance`, `admin_daily_summary`, `admin_weekly_summary`.

**Trabajo por receta (código, chico)**: declarar `template_event` en la receta (`app/services/recipes.py`),
registrar un renderer en `notifications._TEMPLATE_RENDERERS`, y definir su setting del nombre Meta + el
armado de `params` posicionales.

**BLOQUEO EXTERNO (hacer primero)**: cada mensaje necesita un template **aprobado en Meta** (categoría
Utility, idioma `es`, params posicionales que matcheen). Recién después se publica la fila
`NotificationTemplateVersion` con `approved: true` (vía `POST /panel/api/templates`).

**ORDEN — es trampa**: NO poner `template_event` antes de que la fila esté aprobada. Un `template_event`
sin fila aprobada hace que la operación falle **permanentemente** (`TemplatePolicyError`), en vez de
intentar free-form como hoy. Orden correcto: (1) Meta aprueba → (2) `template_event` + renderer +
setting → (3) publicar la fila `approved: true`.

Prioridad sugerida por el owner: `appointment_review_request` primero.

## Advisories aceptadas del feature (no arregladas, a decidir)

1. Desinstalar una receta antes del sweep diferido del follow-up hace que esa operación pendiente caiga al
   camino free-form genérico.
2. `_reminder_due` no aplica el piso de `installation.created_at` que sí aplican sus evaluadores hermanos:
   al instalar, recuerda de una toda visita ya agendada dentro de las próximas 24h (parece intencional).
3. Una visita reservada con >24h de anticipación y reprogramada a <24h **igual** recibe recordatorio (el
   `created_at` es inmutable).
4. Operaciones pendientes pre-deploy con clave `appointment:{id}:reminder:24h` caerían a free-form una vez.

## Pendientes previos (siguen abiertos)

- **WU-D — Multi-admin / doble destinatario** (destinatario como parámetro, UNIQUE `(recipe_id,
  recipient_target)`, migración, UI). Topic Engram: `odd/automation-multi-recipient/workunit`.
- **WU-E — Email real (SMTP)**: settings de puerto/usuario/TLS + password cifrada (`PanelSecret`), unificar
  las dos `send_email`, UI. Topic Engram: `odd/email-smtp/workunit`.

## Setup de un worktree nuevo (recordatorio)

`git pull` en el checkout principal → `rapso worktree create <slug>` (con consentimiento explícito del
owner) → `uv sync` → `cp ../lumat-agent/infra/.env infra/.env` → `infra/test-db.sh up` → `npm ci` en
`web/`. Tests: `eval "$(infra/test-db.sh env)" && uv run pytest tests/ -q`.

## Lecciones cargadas (para no repetir errores)

- `recipes.RECIPES` se serializa en la descripción de la tool `automation.create_rule` del asistente: agregar
  recetas rompe el tripwire SHA en `tests/unit/test_assistant_delegation.py`. Actualizarlo a conciencia.
- `tests/functional/test_api_automation_recipes.py` afirma el orden exacto del catálogo.
- `recipes.py` importa `automation.py`: cualquier `automation → recipes` debe ser import diferido.
- Mergear una PR con `--delete-branch` cuando otra PR la tiene de base **autocierra** la PR apilada y no se
  puede reabrir (hay que crear una PR nueva). Para cadenas, mergear a `main` sin borrar la base, o reapuntar
  antes.
