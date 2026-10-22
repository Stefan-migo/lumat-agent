# HANDOFF — WU-E: mergeado y limpiado; el próximo hilo hace el RELEASE

Fecha: 2026-10-17. Estado: **WU-E mergeado y limpiado. No queda código pendiente del feature.**

Lo que falta **ya no es de WU-E**: es **cortar un release** que incluya el trabajo en curso (T7) y,
recién después, configurar el panel y correr S9.

> Reemplaza a `odd/handoffs/automation-wu-d-wu-e.md` **solo en lo que respecta a WU-E**. Ese archivo
> sigue siendo válido para **WU-D** (multi-admin), que no se tocó.

## Hecho (2026-10-17, verificado)

- **PR #638 MERGEADA.** Merge commit **`fa2bdf71`** (`gh pr merge 638 --merge`, sin `--admin`, sin
  `--delete-branch`). Mergeada 2026-10-17T11:59:46Z. `test` ✅ y `panel` ✅; `GitGuardian` ❌ (falso
  positivo aceptado, no requerido — ver §6).
- **Limpieza completa y verificada:**
  - contenedor `lumat-test-lumat-agent-odd-wu-e-smtp-email-db-test-1` bajado + red removida;
  - `rapso worktree cleanup wu-e-smtp-email --remote` → `{"cleaned":true}`;
  - worktree `lumat-agent-odd-wu-e-smtp-email` borrado; rama `odd/wu-e-smtp-email` borrada **local y
    remota**; `docker ps | grep wu-e` → vacío.
- **Verificación sobre el árbol mergeado** (antes del merge): backend `uv run pytest tests/ -q` → exit 0;
  frontend `npm test` → 1246/1246; `npm run build` (`tsc -b` incluido) → verde.

## ⚠️ CORRECCIÓN DE ORDEN — leer antes de tocar el panel

**La pestaña "Correo" NO existe en producción.** Nació en `0de9d42c` (WU-E, T4+T5) y **ningún tag la
contiene**. Por lo tanto **no se puede configurar el SMTP del panel hasta después de deployar**.

Estado real (2026-10-17):

- Producción corre **`v2026.10.4`** = commit `c6142845` (deploy 2026-10-14). El tag es ancestro de `main`.
- `main` (local y `origin`) = **`3d442dd0`** (PR #641, merge de **T6** de assistant-write-chaining),
  **293 commits** adelante del tag de producción.
- **Migraciones nuevas sin aplicar: 054–057** (prod está en schema 053):
  `054_project_files_kb_document`, `055_project_folders`, `056_appointment_technician_state`,
  `057_grant_automation_installation_delete`. → **el próximo deploy aplica migraciones** (data-touching,
  dump pre-deploy obligatorio).

Orden correcto:

```
T7 aterriza → release v2026.10.5 → deploy → configurar panel ("Correo") → S9 → §2.9
```

## 1. Estado de worktrees (verificado 2026-10-17)

- `/home/stefan/repos/lumat-agent` — `main` @ `3d442dd0`
- `../lumat-agent-odd-assistant-write-chaining` — rama `odd/assistant-write-chaining-t7`,
  **sin commits propios todavía** (== HEAD de main).
  → ⚠️ **ACTIVO: otra sesión trabaja ahí. NO TOCAR.** Se espera a que aterrice para incluirlo en el release.
- `origin/odd/agenda-operator-technicians` — ajeno y preexistente. **NO TOCAR.**
- `../lumat-agent-odd-wu-e-smtp-email` — **borrado**.

## 2. Release (NO cortar hasta que T7 esté mergeado)

> El owner decidió **esperar** al worktree activo y meterlo en el mismo release, en vez de dos releases
> seguidos (los templates de WABA y el trabajo de T7 entran juntos).

1. Bump `pyproject.toml` `[project] version` = `2026.10.5` → commit `release: 2026.10.5` → tag anotado
   `v2026.10.5` → push de ambos (ver `docs/ops.md` §2.1). La versión es CalVer `YYYY.MM.N`.
2. **Deploy** por SSH como `deploy` (`docs/ops.md` §2.1):
   - **dump pre-deploy obligatorio** (hay migraciones 054–057);
   - `GIT_SHA=$(git rev-parse --short HEAD)`; build con `--project-name lumat`;
   - `nginx -t` **dentro de la red compose** (standalone SIEMPRE falla: no resuelve `api`).
3. Smoke §2.1.2 en `panel.lumat.cl` — y ahora **confirmar además que aparece la pestaña "Correo"**.
4. Registrar la fila en `docs/ops.md` §2.9 (release record).
5. **No usar `--admin`.** El repo lo prohíbe explícitamente.

## 3. Configurar el panel (recién DESPUÉS del deploy)

`https://panel.lumat.cl/panel/app/settings` → pestaña **"Correo"**.

Valores relevados del cPanel de Bluehosting (dominio `lumat.cl`, cPanel 134.0.63):

| Campo | Valor |
|---|---|
| Servidor SMTP | `mail.lumat.cl` |
| Puerto | `465` |
| Remitente | `notificaciones@lumat.cl` |
| Usuario | `notificaciones@lumat.cl` (dirección **completa**) |
| Seguridad | `SSL (465)` |
| Contraseña SMTP | la de la casilla |

**Dos writes separados**: **"Guardar correo"** (los 5 campos) y después **"Guardar contraseña"**.
Confirmación esperada: "Contraseña guardada en el panel" + clave enmascarada.

Notas:
- La casilla `notificaciones@lumat.cl` es **nueva y dedicada** a esto (no la usa nada más) → sin riesgo
  al usar su contraseña.
- El transporte **no verifica el certificado TLS** (`ssl._create_stdlib_context()` → `CERT_NONE`,
  `app/services/notify.py:125-127`), así que el cert de cPanel **no puede** romper el envío. No perder
  tiempo ahí.
- Salida del VPS: confirmar que alcanza `mail.lumat.cl:465` (en el VPS, no local):
  `uv run python -c "import socket; socket.create_connection(('mail.lumat.cl',465),timeout=8)"`.
- El puerto **25** está bloqueado por muchos ISPs en Chile. Por eso 465/587, nunca 25.

## 4. S9 — verificación end-to-end con SMTP real

> ⚠️ Corre contra la base y el SMTP **de producción** y **manda un email real**. Requiere autorización
> explícita del owner.

**Paso A — disparar un envío determinista** (probe directo del transporte nuevo, sin depender de que
WhatsApp falle):

```bash
cd /home/stefan/repos/lumat-agent
uv run python - <<'PY'
from app.db import session_scope
from app.services import notifications

with session_scope() as session:
    op = notifications.create_operation(
        session,
        recipient="tu-correo@ejemplo.cl",   # a dónde querés recibir la prueba
        channel="email",
        content="Prueba S9 de WU-E: transporte SMTP real.",
        source_entity="case",
        source_id="s9-probe",
        idempotency_key="wu-e-s9-probe",
    )
    session.flush()
    delivered = notifications.process_operation(session, op.id)
    print("delivered:", delivered, "| status:", op.status, "| error:", op.error)
PY
```

**Paso B — confirmar la evidencia:**

- El email **llegó** al destinatario (revisar spam: envío nuevo desde una IP nueva).
- La fila de audit existe:

```bash
uv run python - <<'PY'
from sqlalchemy import select
from app.db import session_scope
from app.models import AuditLog

with session_scope() as session:
    rows = session.scalars(
        select(AuditLog).where(AuditLog.action == "notification.operation_sent").order_by(AuditLog.id.desc()).limit(3)
    )
    for row in rows:
        print(row.action, "|", row.entity_id, "|", row.after)
PY
```

Esperado: una fila `notification.operation_sent` con `channel: "email"` y el destinatario usado.

**Si falla**, el error queda en `op.error` y en el audit `notification.attempt_failed` /
`notification.exhausted`. Errores probables: salida al puerto bloqueada por el VPS, usuario sin el
dominio completo, o contraseña mal cargada. Registrar el resultado en `odd/tasks/wu-e-smtp-email.md` (S9)
y, si hace falta una corrección, en el feature doc del branch.

## 5. Templates de WhatsApp — CRUCE RESUELTO ✅

El owner creó y aprobó los templates en WABA el 2026-10-16 (12 activos). **Se cruzaron contra lo que
espera la app y coinciden todos.** No hay desajuste que corregir.

Los 5 que la app envía como **template** (`app/services/settings.py:179-185`):

| Setting | Nombre | WABA |
|---|---|---|
| `notify.reminder_template_name` | `appointment_reminder_24h` | ✅ |
| `notify.followup_template_name` | `appointment_followup` | ✅ |
| `notify.followup_no_show_template_name` | `appointment_followup_no_show` | ✅ |
| `notify.en_route_template_name` | `en_route` | ✅ |
| `notify.arrived_template_name` | `arrived` | ✅ |

**Dato de alcance:** de los 12 aprobados, la app manda como template **solo esos 5**
(`_TEMPLATE_RENDERERS` tiene 3 events en `app/services/notifications.py:114-118` + las 2 quick actions de
técnico en `app/services/visit_actions.py`). Los otros 7 (`appointment_confirmation`, `_cancellation`,
`_rescheduled`, `_no_show`, `_review_request`, `customer_maintenance`) caen en `send_whatsapp(recipient,
content)` → **free-text**, válido solo dentro de la ventana de 24h. Probablemente **intencional** (se
disparan por sesión/origen panel), pero es una **decisión del owner**, no un bug asumido. `hello_world`
es el sample de Meta: ignorar.

Nota de infra: `app/services/notifications.py:344-348` lanza
`TemplatePolicyError("no renderer registered for template event ...")` si un recipe tiene
`template_event` sin renderer — cualquier recipe nuevo debe registrarse en `_TEMPLATE_RENDERERS`.

## 6. GitGuardian: por qué el check queda rojo

- Reporta 4 hits, **todos fixtures de test** que existen justamente para probar lo contrario:
  `tests/functional/test_api_settings_email.py`, `tests/functional/test_verifier_wue_api.py` y
  `web/src/components/pages/SettingsEmail.test.tsx`. **No hay credencial real ni nada que rotar.**
- Es **irreducible desde el código**: el escaneo es **por commit** y matchea la **forma**. Se intentaron
  dos commits de fix-forward: no limpiaron el check y volvieron los tests menos naturales → **se
  revirtieron**; los tests entregados son byte a byte los que aprobó el review.
- `a433e762` agrega `.gitguardian.yaml` con exclusión acotada (cubre ggshield y pre-commit). **El GitHub
  App no lee ese archivo**: para poner el check verde hay que cargar las mismas exclusiones de path en el
  dashboard (workspace → secrets detection → filepath exclusions).
- Antecedente: ya pasó en el repo (PR #430). El check **no bloquea merges**.

## Trampas y lecciones (para no repetir errores)

- **`test`/`panel` son los únicos requeridos.** `UNSTABLE` en `mergeStateStatus` = mergeable con un check
  no requerido en rojo; **no** es `BLOCKED`.
- **`strict: true`**: si `main` avanza, la rama queda `BEHIND` y hay que mergear `origin/main` dentro antes.
- **No correr las suites backend y frontend en paralelo**, ni con la máquina cargada: con swap agotado los
  tests de frontend dan timeouts falsos (el mismo test tardó 75 s bajo carga y 667 ms en reposo). Series.
- **`gh pr merge` puede no imprimir nada y haber mergeado igual** — verificar con
  `gh pr view <n> --json state,mergeCommit`.
- **El review nativo exige copiar `provider_task.prompt` EXACTO** (sin envoltorio). Un slot rechazado
  (`inspection.status=unavailable`) **no consume** el slot: re-consultar STATUS de la misma lineage y
  relanzar sólo ese slot.
- **`tests/_testdb.py` deriva el puerto de test del nombre del directorio del repo**: una copia scratch
  debe conservar el nombre del worktree.
- **Force-push**: autorizado por el owner solo para la rama de WU-E (ya borrada). Ante una reescritura,
  verificar la invariante del árbol (`git diff <tip-previo> HEAD`) antes de empujar.
- El worktree de `assistant-write-chaining` **parece** stale pero está **ACTIVO**. Verificar
  `git worktree list` + `git branch` antes de proponer limpieza ajena.

## Pendientes que NO son de WU-E

- **WU-D (multi-admin / doble destinatario)**: sin empezar. Ver
  `odd/handoffs/automation-wu-d-wu-e.md` para bloqueos y alcance verificados.
- `origin/odd/agenda-operator-technicians`: ref remoto ajeno y preexistente.
- Un handoff viejo (`handoff/agenda-cierre-meta-templates`, en Engram) declaraba los templates Meta como
  **BLOQUEADOS**; quedó **desactualizado** con lo que se hizo el 2026-10-16.
