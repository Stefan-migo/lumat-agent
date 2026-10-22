# HANDOFF — Automatizaciones: WU-D (multi-admin) y WU-E (Email SMTP real)

Fecha: 2026-10-15. Estado: **WU-B + WU-C mergeados a `main`; no queda nada pendiente de merge ni de limpieza.**
Este handoff es para arrancar en un chat nuevo con los dos work units que quedan abiertos.

> `odd/handoffs/automation-workunits.md` quedó **desactualizado** (lista B y C como pendientes; ya están en
> `main`). Usar este archivo. El WU de plantillas Meta para las 9 recetas free-form vive aparte, en
> `odd/handoffs/automation-templates-followups.md`.

## Punto de partida (verificado hoy, no de memoria)

- **No hay PRs abiertos** (`gh pr list --state open` → vacío). **No hay nada que mergear**: #634, #636, #633,
  #632, #631 están todos MERGED.
- `origin/main` = **`6422b179`** (merge de #636).
- El checkout principal `/home/stefan/repos/lumat-agent` está en **`9f6da17e`, 16 commits detrás** de
  `origin/main`. **Hacer `git pull` antes de arrancar.** Confirmado con `git grep`: `template_event` no
  existe en el working tree local, solo en `origin/main` — o sea, tu árbol todavía no tiene el motor.
- **Limpieza hecha en esta sesión**: el worktree `../lumat-agent-odd-automation-templates` ya estaba removido
  y las ramas remotas borradas; quedaba un ref stale `refs/remotes/origin/odd/automation-templates` que ya se
  podó (`git fetch --prune`). Refs de automation: limpios.
- Worktree ajeno vivo: `../lumat-agent-odd-assistant-write-chaining` (detached `2514d9dc`, contenido ya
  mergeado por #633). No tocar.

## Lo que cambió en el motor (contexto que afecta a D y E)

`automation-templates` (PRs #634/#636) dejó el motor así:

- Una receta puede declarar **`template_event`**; al enviar se resuelve por
  `AutomationExecution.operation_id → AutomationRule.installation_id → recipe_id` y sale con
  `notify.send_template` + `validate_channel_policy(business_initiated=True)`. Hoy lo declaran 3 recetas
  (`appointment_reminder`, `appointment_followup`, `appointment_followup_no_show`).
- El recordatorio 24h y el follow-up al dueño son **recetas**; se borró el scheduler hardcodeado
  (`scheduling._maintain_reminder`, `scheduling._schedule_followup`) y los branches `:reminder:24h` /
  `followup:*` de `notifications.process_operation`.
- **Sin migración**: la receta se resuelve en runtime; `AutomationRule.template_event` sigue dropeada.
- Mapeo template → receta → renderer en `docs/meta-templates.md`.

---

## WU-D — Multi-admin / doble destinatario

**Problema**: hoy una receta tiene **un solo destinatario fijo** y se puede instalar **una sola vez**. El
objetivo del owner: que una mantención avise al cliente **y** a los admins configurados.

**Bloqueos verificados contra `origin/main`**:

1. `db/migrations/045_automation_installations.sql:3` → `recipe_id VARCHAR(100) NOT NULL UNIQUE` — una receta
   = una instalación.
2. El destinatario es **atributo fijo** de la definición: `RecipeDefinition.recipient_target`
   (`app/services/recipes.py`), no es parámetro.
3. `evaluate_event` crea **una** `NotificationOperation` por regla (un solo recipient).

**Alcance**:

1. Volver el destinatario un **parámetro** de receta (`customer` / `admin`), en vez de atributo fijo.
2. Cambiar el UNIQUE de `recipe_id` a **`(recipe_id, recipient_target)`** → **migración** (esquema, no datos).
3. Multi-admin: lista de destinatarios admin configurables; `_resolve_recipient` devuelve **varios** →
   `evaluate_event` crea **una operación por destinatario**, cada una con su propia `idempotency_key`.
4. UI del panel para elegir destinatario(s).

**Decisión ya cerrada con el owner**: modelarlo como *"instalar la misma receta una segunda vez con segundo
destinatario"*, **no** como un modo `both` global.

**Dónde**: `app/services/recipes.py`, `app/services/automation.py` (`_resolve_recipient` / `evaluate_event`),
`app/services/automation_installations.py`, `app/models.py`, `db/migrations/`,
`app/panel/api/routes/automation_recipes.py`, `web/src/components/pages/AutomationRecipesPage.tsx`.

**Dependencia**: dependía de WU-B para la parte WhatsApp (límite 24h). **WU-B ya está mergeado → WU-D está
desbloqueado.**

---

## WU-E — Email real (SMTP)

**Problema**: el email del sistema **no es configurable y no funciona en producción**.

**Bloqueos verificados contra `origin/main`**:

1. `app/services/settings.py:181-182` → solo existen `notify.smtp_host` y `notify.smtp_from`. **No hay
   puerto, usuario, password ni TLS.**
2. `app/services/notifications.py:148` → `smtplib.SMTP("localhost")` **hardcodeado**, From fijo
   `notificaciones@lumat.cl`, sin auth, **ignora los settings**.
3. `app/services/notify.py:112` → `smtplib.SMTP(host)` sí lee el setting, pero sin puerto ni auth. **Dos
   implementaciones divergentes.**
4. Defaults: `DEFAULT_SMTP_HOST="localhost"`, `DEFAULT_SMTP_FROM="notificaciones@lumat.cl"`,
   `DEFAULT_OWNER_EMAIL="emergencias@lumat.cl"`, `DEFAULT_OWNER_WHATSAPP="+56912345678"` (placeholder —
   verificar en la DB de prod).
5. **Verificado en producción** (memoria `ops/prod-kb-and-smtp-state`): el SMTP **nunca tuvo valores reales**.

**Criticidad**: sin esto, **todo** fallback a email (emergencia, recordatorio de visita, follow-up, y el canal
email de las automatizaciones) falla en prod.

**Mecanismo de secretos ya existente y reutilizable**: tabla `PanelSecret` (`app/models.py`) +
`app/services/crypto` + `app/services/model_secrets.py` (el patrón que ya usa la API key de DeepSeek). La
password SMTP va **ahí**, no en un setting plano.

**Alcance**:

1. Settings nuevos: `notify.smtp_port`, `notify.smtp_user`, `notify.smtp_tls` (+ password cifrada en
   `PanelSecret`).
2. Arreglar `notifications.send_email` para usar host/puerto/auth/TLS en vez de `localhost`.
3. **Unificar** `notifications.send_email` y `notify.send_email` en una sola ruta configurable.
4. UI de configuración de correo en el panel (Configuración).
5. Verificación end-to-end: mandar un email real y observar el audit de la `NotificationOperation`.

**Dónde**: `app/services/notifications.py`, `app/services/notify.py`, `app/services/settings.py`,
`app/models.py` (`PanelSecret`), `app/services/crypto.py`, `app/services/model_secrets.py`,
`web/src/components/pages/Settings.tsx`.

**cPanel (Bluehosting)**: host típico `mail.<dominio>`, puerto **587 (STARTTLS)** o **465 (SSL)**, usuario =
email completo, password de la cuenta. Verificar salida del VPS por ese puerto.

---

## Orden y dependencias

- **WU-D y WU-E son independientes entre sí.** No hay dependencia de uno con el otro.
- Superficie compartida mínima: ambos podrían tocar `app/models.py` (D por el UNIQUE, E por `PanelSecret`).
  No van en paralelo en el mismo árbol: son dos features ODD secuenciales.
- Criterio para elegir el primero: **WU-E cierra un agujero en producción** (el email no entrega hoy);
  **WU-D habilita una capacidad nueva** (multi-admin). El owner decide.

## Setup de un worktree nuevo (recordatorio)

`git pull` en el checkout principal → `rapso worktree create <slug>` (con consentimiento explícito del owner)
→ `uv sync` → `cp ../lumat-agent/infra/.env infra/.env` → `infra/test-db.sh up` → `npm ci` en `web/`.
Tests: `eval "$(infra/test-db.sh env)" && uv run pytest tests/ -q`.

## Lecciones cargadas (para no repetir errores)

- `recipes.RECIPES` se serializa en la descripción de la tool `automation.create_rule` del asistente: agregar
  o cambiar recetas rompe el tripwire SHA en `tests/unit/test_assistant_delegation.py`. Actualizarlo a
  conciencia.
- `tests/functional/test_api_automation_recipes.py` afirma el orden exacto del catálogo.
- `recipes.py` importa `automation.py`: cualquier `automation → recipes` debe ser **import diferido**.
- Mergear una PR con `--delete-branch` cuando otra PR la tiene de base **autocierra** la PR apilada y no se
  puede reabrir (hay que crear una PR nueva). Para cadenas, mergear a `main` sin borrar la base, o reapuntar
  antes.
- **El borrado de rama deja refs remotos stale locales**: después de un `--delete-branch`, correr
  `git fetch --prune` o tu `git branch -a` sigue mostrando la rama borrada.
- **`main` tiene branch protection** (corregido en AGENTS.md por #632): checks requeridos `test` y `panel`
  (`.github/workflows/tests.yml`), `strict: true` (la rama debe estar al día con `main`). `tsc -b` vive solo
  dentro de `npm run build`, así que la suite frontend verde **no** prueba que tipa. `enforce_admins: false`
  permite `--admin`: no usarlo.
