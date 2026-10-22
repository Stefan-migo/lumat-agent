# HANDOFF — Automatizaciones: work units pendientes

> **DESACTUALIZADO (2026-10-15, posterior).** WU-B y WU-C ya están mergeados a `main`. Para lo que queda
> (WU-D y WU-E) usar `odd/handoffs/automation-wu-d-wu-e.md`.

Fecha: 2026-10-15. Estado: análisis de la sección Automatizaciones completo; **desinstalador entregado y mergeado** (PR #629, `58e7652f`). Quedan 4 work units pendientes, en orden de dependencia.

## Contexto mínimo (para retomar sin releer todo)

Sección = **catálogo curado de recetas** (`app/services/recipes.py`, 9 recetas) que, ante un evento/tiempo, **envía una notificación** (WhatsApp/email) al cliente o al admin. Pipeline: `publish_event()` → `domain_events` → `run_cycle()` (`app/ops/worker.py`, cron `*/5` en prod) → `evaluate_event()` (`app/services/automation.py`) → `NotificationOperation` → sweep → envío.

Dos hechos que condicionan todo:
- **El motor manda WhatsApp free-form** (`send_text`), sin plantilla y sin chequear la ventana de 24h de Meta. Es el gap central (#6633).
- **El destinatario admin es UN solo número/email** (`notify.owner_whatsapp` / `notify.owner_email`). Ojo: `notify.owner_whatsapp` default es `+56912345678` (placeholder) — verificar en la DB de prod.

## Orden recomendado

### WU-B — Motor con TEMPLATES + filtro `origin`  (primero; habilita el resto)
- **Problema**: `automation.py` no usa plantillas; fuera de la ventana de 24h Meta rechaza el texto libre.
- **Alcance**:
  - Que `RecipeDefinition` pueda declarar un **template** (nombre + armado de `params` posicionales), reutilizando el patrón de `notifications._send_appointment_reminder` (`appointment_reminder_24h`) y `validate_channel_policy(approved=True, business_initiated=True)`.
  - **Filtro `origin`**: `scheduling.book()` ya recibe `actor`; agregar `origin` (`assistant`/`panel`) al payload de `appointment.booked`. La receta de confirmación filtra con conditions exact-match `{"origin":"panel"}` → dispara **solo** para reservas de panel (el chatbot confirma en el chat). Decisión ya cerrada con el owner.
- **Archivos**: `app/services/{automation,recipes}.py`, `app/services/scheduling.py` (payload), `app/services/notifications.py` (envío), `app/models.py` si hace falta.
- **Plantillas que espera el código** (nombre exacto, idioma `es`, categoría Utility, params posicionales): `appointment_reminder_24h` (2 params), `appointment_followup` / `appointment_followup_no_show` (3 params), `emergency_alert`. Doc: `docs/meta-templates.md`.
- **Publicar la fila de registro** recién DESPUÉS de que Meta apruebe: `POST /panel/api/templates` con `approved: true` (evento/channel/locale + content con `{vars}` + required_variables).

### WU-C — Migrar recordatorio 24h + seguimiento al dueño a RECETA  (depende de B)
- `scheduling._maintain_reminder` → 24h **ANTES** de la visita → cliente → template `appointment_reminder_24h`.
- `scheduling._schedule_followup` → 24h **DESPUÉS** del cierre → **al owner** → templates `appointment_followup` / `_no_show`. Es un aviso interno ("andá a hacer seguimiento al cliente", completada / no-show).
- **Alcance**: convertirlos en recetas del catálogo (opt-in; hoy son automáticos e ineludibles) y **borrar el camino hardcodeado en el MISMO cambio** (si conviven, se manda doble).
- **Recomendado hacerlo junto con WU-B** para dejar una sola fuente de verdad para las notificaciones de cita.

### WU-D — Multi-admin / doble destinatario  (depende de B para WhatsApp)
- Hoy: `recipe_id` es UNIQUE en `automation_installations` y `recipient_target` es fijo por receta → no se puede instalar la misma receta dos veces ni mandar a varios admins.
- **Alcance**: (1) destinatario como **parámetro**; (2) UNIQUE `(recipe_id, recipient_target)` (migración); (3) lista de destinatarios admin configurables; `_resolve_recipient` devuelve varios → `evaluate_event` crea **una operación por destinatario** con idempotency_key propia; (4) UI en el panel.
- **Decisión del owner**: preferir "instalar la misma receta una segunda vez con segundo destinatario" antes que un modo `both` global.

### WU-E — Email real (SMTP)  (para después del panel del técnico)
- Hoy no configurable: `SETTINGS_DEFAULTS` solo tiene `notify.smtp_host`/`notify.smtp_from` (sin puerto/usuario/password/TLS); `notifications.send_email` hardcodea `smtplib.SMTP("localhost")`; `notify.send_email` es otra implementación. Password debe ir al store cifrado (`PanelSecret` + `app/services/crypto`).
- **Alcance**: settings de puerto/usuario/TLS + password cifrada; unificar las dos `send_email`; UI de configuración; verificación end-to-end.
- **cPanel Bluehosting**: `mail.<dominio>` :587 (STARTTLS) o :465 (SSL), usuario = email completo. Verificar salida del VPS.

## Estado del repo
- `main` = `58e7652f` (merge PR #629). Worktree `../lumat-agent-odd-automation-uninstall` removido; branch local/remoto borrados.
- Otros worktrees vivos ajenos a esto: `odd/assistant-write-chaining`, `odd/panel-tecnico-wu8`. No tocar.
- Test DB del worktree: apagada (`infra/test-db.sh down -v`).

## Setup de un worktree nuevo (recordatorio)
`rapso worktree create <slug>` (con consentimiento explícito del owner) → `uv sync` (crea `.venv`) → `cp ../lumat-agent/infra/.env infra/.env` → `infra/test-db.sh up` → `npm ci` en `web/`. Correr tests: `eval "$(infra/test-db.sh env)" && uv run pytest tests/ -q`.
