# automatizaciones-recetas

## Objective

Convertir la sección **Automatizaciones** del panel Lumat de un motor de reglas libres
(evento → notificación, sin dimensión tiempo, sin runner periódico en producción) a un
**catálogo curado de 11 recetas de negocio** (Nivel 1), con dimensión tiempo, en **3 slices**.

El builder de condiciones/acciones componibles (Nivel 2) queda **diferido a un próximo
presupuesto** y NO se implementa acá.

## Problem

El motor actual (`AutomationRule`) reacciona a 8 eventos de dominio y su único efecto es
encolar una notificación. No existe dimensión tiempo (offset ni schedule), no existe un
runner periódico en producción (`run_cycle()` solo lo llama su `main()`), la UI es un CRUD
técnico (eventos crudos, JSON editable, cooldown en segundos) y la tool del agente
(`automation.create_rule`) es un espejo de la regla libre, insuficiente para recetas.

## Why

El owner aprobó el catálogo de 11 recetas y las decisiones técnicas quedaron cerradas en la
sesión `2026-10-09-automatizaciones-recetas` (`.rapsodia-code/sessions/ready-for-odd/`).
Se eligió ODD (no SDD) para implementar slice por slice, con commits por work unit y review RDD.

## Decisions (closed — do not re-litigate)

1. **Alcance** = catálogo curado de 11 recetas (Nivel 1). Nivel 2/3 fuera de este presupuesto.
2. **Efecto** de las recetas = notificación (WhatsApp/Email) o resumen al admin. Sin acciones
   sobre datos del negocio en este alcance.
3. **UX** = patrón ChatGPT "Scheduled": tarjetas de recetas + input en lenguaje natural que
   **parametriza una receta** (nunca inventa lógica).
4. **Modelo de receta** (D-T1) = **catálogo en código** (definiciones versionadas) + tabla de
   **instalaciones en DB** (receta activa + parámetros). NO se entierra la lógica en DB.
5. **Programación del worker** (D-T2) = **cron externo cada 5 min** (patrón `app.ops.sweep`).
   Servicio worker en compose queda diferido; loop en la API descartado.
6. **Dimensión tiempo** (D-T3) = **offsets contra entidades evaluados en cada tick** (recordatorios,
   postventa, mantención) + **disparos de calendario** para resúmenes, ambos sobre el mismo tick.

## Scope

**In:** modelo de receta + migración, catálogo de recetas en código, instalaciones, tick del
worker (eventos + tiempo), cron, recetas de evento y de tiempo, UI de tarjetas, ajustes a la
tool del agente, y tests.

**Out:** builder Nivel 2/3, acciones sobre datos del negocio, design-system palette/tokens,
otras secciones del panel, otras ramas en vuelo. No revivir capacidades ya entregadas.

## Constraints

- Chat en Rioplatense Spanish; artefactos, código, comentarios y commits en English; copy de UI
  en Chilean neutral Spanish. Conventional Commits, sin atribución de IA.
- Reusar `AutomationRule`, `DomainEvent`, `evaluate_event`, `create_operation`, el sweep de entrega,
  audit y el CRUD admin antes de crear piezas nuevas.
- Graph Check obligatorio antes de tocar cada módulo (`graphify query` / `graphify path`); registrar
  los nodos consultados en el apply-progress.
- UI honesta: donde falte contrato, estado vacío/deshabilitado real — nunca fabricar recetas, envíos
  ni conteos.
- Migraciones idempotentes vía `db/migrate.sh`.

## Reuse inventory (verified HEAD 07ddfb05)

- `app/services/automation.py` — `validate_rule_input` (L26), `rule_snapshot` (L56), `create_rule`
  (L72), `update_rule` (L89), `set_rule_enabled` (L99), `_matches` (L108), `evaluate_event` (L112);
  `ALLOWED_CHANNELS`/`ALLOWED_EVENTS` (L14-15).
- `app/services/events.py` — `publish_event()` (transaccional, dedupe_key).
- `app/ops/worker.py` — `run_cycle()` (L48, lease 60s, retry 1/2min, MAX_ATTEMPTS 3), `main()` (L87).
- `app/services/notifications.py` — `create_operation`, `sweep_due_operations`, `create_due_reminder`
  (prototipo, hoy sin callers).
- `app/models.py` — `AutomationRule` (L776), `DomainEvent` (L750), `AutomationExecution`,
  `NotificationOperation` (`next_attempt_at`).
- `app/panel/api/routes/automation_rules.py` — GET/POST/GET/PATCH + `/enable` + `/disable` (admin).
- `app/chat/assistant/tools/registry.py` — `RuleArgs` (L197), tool `automation.create_rule` (L670),
  admin-only (L703).
- Frontend: `web/src/components/pages/AutomationRulesPage.tsx`, `AutomationRuleDetailPage.tsx`,
  `web/src/components/domain/panelRoutes.ts`, `AppShell.tsx`, `web/src/api.ts`, `web/src/types.ts`.
- `docs/ops.md` §2.8/§2.8.1 — patrón de cron (sweep) a imitar.
- `infra/docker-compose.prod.yml` — api/db/nginx/certbot (sin worker).

## Gaps (to build)

1. **Slice 1**: runner del worker (cron) + modelo de receta (catálogo en código + instalaciones DB)
   + recetas de evento + UI de tarjetas.
2. **Slice 2**: tick de offsets + recordatorio de visita + pedir evaluación + mantención periódica.
3. **Slice 3**: disparos de calendario + módulo `daily_summary` + resumen diario/semanal.
4. **Transversal**: evento de pago; destinatario en eventos de caso; redefinir `template_event`.

## TDD resolution

- `openspec/config.yaml`: `testing.strict_tdd: true`, runner `uv run pytest tests/` → **TDD ENABLED**
  (RED → GREEN → REFACTOR con evidencia observada) para backend.
- Frontend: `npm test` (vitest) + `npm run build` (type-check vía `tsc -b`). Checks ordinarios, no cero checks.

## Delivery strategy

- Forecast: **> ~1,000 authored changed lines** a lo largo de los 3 slices → excede el budget de ~400.
  `delivery_strategy`: `ask-on-risk`. Cada slice es un work unit revisable con su(s) commit(s) y su
  verificación. PR/merge quedan en manos del owner.
- `chain_strategy`: **pendiente de confirmar** con el owner antes del primer PR (patrón histórico del
  repo: `stacked-to-main`).

## Work units (stable IDs)

### Slice 1 — Runner + recetas de evento (actual)
- [ ] **A1 — Runner del worker**: cron cada 5 min que dispare `run_cycle()` (patrón `app.ops.sweep`);
  documentar en `docs/ops.md`; verificar el entrypoint `python -m app.ops.worker`. (Parte operativa
  — armar el cron en el VPS — requiere autorización remota aparte.)
- [x] **A2 — Modelo de receta**: catálogo de recetas en código (definiciones) + tabla de
  instalaciones + migración idempotente + servicio de instalación/parametrización.
  Commits `71a0b693` (modelo) y `47c1e4f4` (harness). Suite verde: 1834 passed.
  RDD **aprobado** — lineage `review-9b4846fa6e0c8eb8` (4 lentes, 0 bloqueantes).
- [ ] **A3 — Recetas de evento (5)**: confirmación de reserva, aviso de cancelación, reprogramación,
  no-show, nueva solicitud al equipo.
- [ ] **A4 — Tool del agente**: adaptar a recetas (`recipe_id` + parámetros tipados) manteniendo
  opt-in/admin-only/aprobación.
- [ ] **A5 — API + UI de tarjetas**: catálogo (tarjetas) + activas/parametrizadas; input NL que
  parametriza recetas.

### Slice 2 — Dimensión tiempo (offsets)
- [ ] **B1 — Tick de offsets** + receta recordatorio de visita + pedir evaluación + mantención periódica.

### Slice 3 — Resúmenes
- [ ] **C1 — Disparos de calendario** + módulo `daily_summary` + resumen diario/semanal.

### Transversal
- [ ] **D1 — Evento de pago**.
- [ ] **D2 — Destinatario en eventos de caso**.
- [ ] **D3 — Redefinir `template_event`** (contenido vs nombre de evento).

## Review follow-ups (non-blocking — from A2 RDD `review-9b4846fa6e0c8eb8`)

These were reported as informational on the approved A2 candidate. They do NOT reopen the review;
they are separate later work.

- [ ] **R3-001** (`app/services/recipes.py:59`) — `compile_rule_fields` indexes `values["channel"]`
  unconditionally, but the recipe model does not require a channel parameter; a recipe without one
  raises `KeyError`. Tighten the model or the compile path before A3 adds real recipes.
- [ ] **R3-002** (`app/services/automation_installations.py:11`) — `installation_snapshot` returns the
  stored `parameters` dict by reference (mutable), and optional string params accept `null`. Return a
  detached copy and decide the null policy.
- [ ] **R4-001** (`app/services/automation_installations.py:36-41`) — the service establishes no
  transaction boundary; commit/rollback belongs to the caller. Ensure callers roll back on later errors.
- [ ] **R4-002** (`app/services/automation_installations.py:49-58`) — the duplicate-install precheck can
  race with concurrent requests; the DB unique constraint rejects the loser, but the `IntegrityError` is
  not translated into the documented `ValueError`. Normalize the conflict response when wiring the API.

## Verification

- Backend: `uv run pytest tests/` (TDD estricto).
- Frontend: `cd web && npm test` y `cd web && npm run build`.
- Por work unit: Graph Check registrado; commit convencional; verificación observada antes de tildar.

## Progress log

- 2026-10-09 — Task doc creado desde la sesión `2026-10-09-automatizaciones-recetas`. Worktree
  `../lumat-agent-odd-automatizaciones-recetas`, branch `odd/automatizaciones-recetas`, base `07ddfb05`.
