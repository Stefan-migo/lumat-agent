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
3. **UX** = curated recipe cards + deterministic parameter form. Natural-language input is deferred;
   it must parameterize a recipe and never invent logic. The curated UI replaces the technical
   free-rule UI, while the existing free-rule backend endpoints remain for compatibility.
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
- `chain_strategy`: **stacked branch chain** (confirmado con el owner). Cada work unit es su propia
  branch encadenada sobre la anterior, mergeadas en orden: `#545 → #546 → #547 → #550 → #551`.

## Work units (stable IDs)

### Slice 1 — Runner + recetas de evento (actual)
- [ ] **A1 — Runner del worker**: cron cada 5 min que dispare `run_cycle()` (patrón `app.ops.sweep`);
  documentar en `docs/ops.md`; verificar el entrypoint `python -m app.ops.worker`. (Parte operativa
  — armar el cron en el VPS — requiere autorización remota aparte.)
- [x] **A2 — Modelo de receta**: catálogo de recetas en código (definiciones) + tabla de
  instalaciones + migración idempotente + servicio de instalación/parametrización.
  Commits `71a0b693` (modelo) y `47c1e4f4` (harness). Suite verde: 1834 passed.
  RDD **aprobado** — lineage `review-9b4846fa6e0c8eb8` (4 lentes, 0 bloqueantes).
- [x] **A3 — Recetas de evento (5)**: confirmación de reserva, aviso de cancelación, reprogramación,
  no-show, nueva solicitud al equipo. Requirió una extensión mínima del motor: `AutomationRule.recipient_target`
  + `content` (migración `046`), resolución de admin desde settings (`notify.owner_whatsapp`/`owner_email`),
  y contenido `payload → rule.content → template_event`. Commit `d4f5baaf`. Suite verde: 1840 passed.
  RDD **aprobado** — lineage `review-7cf5522c2723c822` (4 lentes, 0 hallazgos). R3-001 resuelto.
  Nota: los mensajes de las recetas son v1 (texto fijo chileno neutro); interpolar fecha/servicio queda como
  follow-up (requiere enriquecer los payloads). Targets fijos (customer/admin); configurable queda para más adelante.
- [x] **A4 — Agent tool**: `automation.create_rule` now installs a catalog recipe through typed
  `recipe_id` + `parameters`, preserving opt-in, admin-only access, and exact approval. Admin approval
  activates the installation (`enabled=True`); panel installs remain disabled by default. Commit SHA:
  reported in delivery (the SHA cannot be embedded in its own commit). Verification: focused suite
  131 passed; full suite 1843 passed, 2 warnings. Graph: `RecipeDefinition` ←contains— `recipes.py`
  —imports_from→ `automation.py` —imports→ `AutomationRule`; also consulted `install()`,
  `automation_installations.py`, `recipes.py`, `registry.py`, and `execute_tool()`.
- [x] **A5 — API + UI de tarjetas**: curated catalog and installed recipes; deterministic parameter
  form. Natural-language input is deferred. The curated UI replaces the technical free-rule UI;
  existing free-rule backend endpoints remain for compatibility.
- [x] **A5a — Backend API**: admin-only recipe catalog and installation CRUD/status endpoints,
  with transactional commit/rollback and normalized validation/conflict responses. Commit SHA:
  recorded in delivery report (the SHA cannot be embedded in its own commit).
- [x] **A5b — Frontend UI**: `AutomationRecipesPage` renders the recipe catalog as cards, a
  deterministic parameter form (channel select), and the installed list with Activar/Desactivar,
  with honest loading/error/denied/empty states and controls disabled while a request is in flight.
  It replaces the technical `AutomationRulesPage` / `AutomationRuleDetailPage`, removed together with
  their tests and stories; the free-rule backend endpoints stay. Commit SHA: reported in delivery
  (the SHA cannot be embedded in its own commit). Verification: `npm run build` (tsc -b + vite)
  passed; the full vitest suite is green serialized (102 files, 1075 tests) — the default parallel
  `npm test` shows load-induced 5s timeouts on unrelated heavy files in this loaded worktree, while
  the A5b-focused files pass in isolation (4 files, 88 tests).

Graph Check: A5a consulted `automation_installations.py`, `installation_snapshot()`, `recipes.py`,
`api/serializers.py`, `AutomationRule`, and the automation panel API area (hubs `api/serializers.py`,
`models.py`). A5b consulted `AppShell()`, `api.ts`, `types.ts`, `useAsyncData()`, `panelRoutes`,
`Button`, and `StateMessage` (hubs `AppShell.tsx`, `api.ts`).

### Slice 2 — Dimensión tiempo (offsets) — branch `odd/automatizaciones-recetas-tiempo`

**Design (closed 2026-10-10):** the worker tick manufactures synthetic `DomainEvent`s. For each
enabled time-recipe installation the tick detects entities whose offset is due and calls
`publish_event(dedupe_key=...)`; the existing pipeline (`evaluate_event` → `AutomationExecution` →
`NotificationOperation`) does the rest. This reuses both existing dedupe layers
(`DomainEvent.dedupe_key` unique + `AutomationExecution.execution_key` unique), so B1 needs
**no migration and no new table**. The synthetic trigger events are added to `ALLOWED_EVENTS`
so `evaluate_event` (L140) does not skip them.

**Scope (convivir — owner decision):** the visit reminder is NOT implemented in the engine because
it already exists live (`scheduling._maintain_reminder`, hardcoded 24h, pre-scheduled, delivered by
the sweep). It migrates to the engine only when A1 (worker cron) lands in prod. B1 implements only
the two recipes that do not exist today. No `visit_reminder` catalog entry is added (honest UI).

**Anchors:** review request → `appointment.ends_at + Xd` with `status=completed` (there is no
`completed_at` column); maintenance → the customer's last completed `ends_at` + N months.
Anti-backfill floor: an occurrence only fires when its **due time** (`anchor + offset`) is
`>= installation.created_at`. A due time already in the past when the recipe is installed is
suppressed; a due time still in the future fires normally. (Floored on the due time, NOT on the
anchor: flooring on the anchor would wrongly skip entities whose anchor predates the install but
whose due time is in the future.)

- [x] **WU1 — Time recipe model**: `trigger_kind="offset"` in `RecipeDefinition`;
  `compile_rule_fields` accepts `{"event","offset"}`; `type="number"` parameter validation;
  `_offset_recipe` helper; two new recipes (`appointment_review_request`, `customer_maintenance`);
  synthetic trigger events in `ALLOWED_EVENTS`. Commit `48037e8`. Full backend suite **1879 passed**.
  Note: `validate_parameters` now applies a parameter's default when it is required but has one
  (no prior required param had a default). Adding recipes recomputed the pinned assistant planner
  catalog hash in `tests/unit/test_assistant_delegation.py` (snapshot fixture). RDD assess: medium,
  `review_due: false` (`under_budget`) — slice boundary stays open.
- [x] **WU2 — Tick evaluation**: `app/services/time_triggers.py` computing due occurrences per
  recipe + idempotent `publish_event`; hook into `worker.run_cycle` (same tick). Commit `8692404`.
  Focused `test_time_triggers.py` **5 passed**; full backend suite **1884 passed**. `dateutil` was
  unavailable → stdlib `_add_months` (clamped). Idempotency verified (double call → 1 `DomainEvent`).
  Note: installs must backdate `installation.created_at` in tests, since the floor is the due time.
- [x] **WU3 — Surface + verification**: catalog/API exposes the time recipes with numeric params
  (no backend change needed — the serializer passes `type`/`default` through); UI verified (the
  `type="number"` form branch already exists). Commit `cafafdc0` adds a frontend test covering an
  offset recipe's numeric parameter: `npm test` focused **6 passed**, `npm run build` (tsc -b + vite)
  green. A full serialized `npm test` run flaked on the unrelated `AgentChat` suite under load (the
  frontend source is byte-identical to base; `AgentChat.test.tsx` passes 58/58 in isolation and on
  `main`).

### Slice 3 — Resúmenes (branch `odd/automatizaciones-recetas-resumenes`, base `576b07ef`)

**Design (closed 2026-10-10):** calendar triggers ride the same worker tick as the Slice 2 offsets.
Two new `trigger_kind="schedule"` recipes (`admin_daily_summary`, `admin_weekly_summary`) publish
synthetic `DomainEvent`s (`admin.daily_summary_due`, `admin.weekly_summary_due`) once per business day /
ISO week; the existing pipeline delivers the digest to the admin (`recipient_target="admin"`). No
migration: dedupe rides `DomainEvent.dedupe_key` (same as Slice 2). The digest text is built from real
KPIs at trigger time and carried in the event payload (`content`), which `evaluate_event` already prefers
over `rule.content`.

**Scope:** daily + weekly summary to the admin (notification only, no data actions). Digest KPIs: open
cases (`cases.list_open_cases`), unresolved questions (`respond.list_unresolved_questions`), spend
(`costs.daily_spend`). Honest empty state when there is no data. The `backup status` mentioned in
`docs/ops.md` §2.8 is omitted — no in-app source, must not be fabricated.

**Business timezone:** `hours.timezone` (default `America/Santiago`) via `ZoneInfo`. A tick fires when
local `now >= due_time` (today at HH:MM; the configured weekday at HH:MM for weekly). Dedupe keys:
`schedule:{recipe_id}:{YYYY-MM-DD}` (daily) and `schedule:{recipe_id}:W{iso_week}` (weekly).

**Work units:**
- [x] **WU1 — Schedule recipe model**: `trigger_kind="schedule"`; param types `time` (HH:MM) and
  `weekday` (1-7); `_schedule_recipe`; the two summary recipes; synthetic events in `ALLOWED_EVENTS`;
  updated catalog expectations. Commit `85899bda`. Full backend suite **1894 passed**.
- [x] **WU2 — Digest builder**: `app/ops/daily_summary.py` `build_digest(session, *, period, now)` from
  real KPIs (open cases, unresolved questions, spend), honest empty state, plus a stdout `main()`.
  Commit `b8306b8d`. Full backend suite **1898 passed**.
- [x] **WU3 — Calendar evaluation**: `_summary_due` in `app/services/time_triggers.py` on the same tick,
  business timezone (`hours.timezone`), day/week dedupe, digest in the event payload, anti-backfill
  floor. Commit `4a81fc61`. Separate `fix:` commit `d5a048cf` isolates per-installation failures
  (resolves R3-003). Full backend suite **1903 passed**.
- [x] **WU4 — Surface + verification**: `AutomationRecipesPage.tsx` renders `time` (native time input)
  and `weekday` (Lunes–Domingo select, integer value) params. Commit `8ffd0c64`. `npm run build`
  (tsc -b + vite) green; full serialized `npm test` **104 files, 1108 tests** green.

### Transversal
- [ ] **D1 — Evento de pago** — **FUERA DE ALCANCE (por ahora)**. Confirmado por el owner (2026-10-12):
  no hay pagos en el sistema y quedan fuera de este alcance. La **Integración de pagos** es un entregable
  con **presupuesto aparte** dentro del Milestone 3 (`LumatRequest.md` §3.8 / línea 322); los avisos de
  pago del requisito (`:310`) dependen de eso. El backend no tiene ningún concepto de pago (cero matches
  de Payment/Quote/Invoice/Stripe/Transbank/MercadoPago/Webpay/Flow/Khipu) y `Case.amount`
  (`app/models.py:361-378`) es el monto del servicio, no un estado de pago. **D1 no se retoma hasta que
  exista la integración de pagos.** Recon: Engram `odd/automatizaciones-recetas/d1-d2-recon`.
- [x] **D2 — Destinatario en eventos de caso** — cerrado en Slice 4 (acotado): el destinatario del
  cliente (`phone_e164`) viaja en los payloads `case.*` donde se conoce. Sin receta nueva.
- [x] **D3 — Redefinir `template_event`** — cerrado en Slice 4: removido de raíz (migración `049`). El
  texto de la notificación se resuelve solo desde `payload.content` / `payload.text` / `rule.content`.

### Slice 4 — Transversal acotado (D2 + D3)

Worktree `../lumat-agent-odd-automatizaciones-recetas-transversal`, branch
`odd/automatizaciones-recetas-transversal`, base `00e09e3c`. Strict TDD ON
(`openspec/config.yaml`, runner `uv run pytest tests/`). Migración **049**.

- [x] **T1 — D3: remover `template_event` de raíz** (migración `049_drop_automation_rule_template_event.sql`).
  El campo hoy duplica `event_type` (las recetas lo setean igual, `recipes.py:78`) y su único rol extra
  es ser fallback final de texto (`automation.py:158`) + gate redundante de política (`:140`). No está
  enganchado al registry de plantillas de notificaciones (verificado: `NotificationTemplateVersion` se
  elige por settings, no por `AutomationRule.template_event`). Removerlo de: `app/models.py` (columna),
  `app/services/automation.py` (`validate_rule_input`, gate de evaluación, fallback de contenido,
  serializer), `app/services/recipes.py` (`compile_rule_fields`),
  `app/panel/api/routes/automation_rules.py`, `app/panel/api/serializers.py`, `web/src/types.ts`;
  migración nueva; tests actualizados + versión en `tests/integration/test_migrations.py`. El texto pasa
  a resolverse solo desde `payload.content` / `payload.text` / `rule.content`.
- [x] **T2 — D2 acotado: destinatario en payloads de caso**. Agregar el destinatario del cliente
  (`phone_e164`) a los eventos `case.*` donde el cliente se conoce, en `app/services/cases.py` (4 sitios
  `publish_event`: `case.created` ×2, `case.updated` ×2). Sin receta nueva; el único consumidor
  (`case_new_request`) es admin-targeted y resuelve desde settings, así que no cambia comportamiento.
- [x] **T3 — Cerrar slice**: task doc actualizado; verificación backend/frontend verde; review nativo RDD
  aprobado (lineage `review-5ca037e6e4ca9962`, 4 lentes, 0 hallazgos, authority burned); PR **#563**
  mergeado a `main` (`1d98576e`) con CI verde (`test` + `panel`).

Route (ODD): T1 y T2 delegados a un writer (2+ archivos no triviales); verificación observada por el
writer; review nativo RDD por candidato (base `00e09e3c`).

## Review follow-ups (non-blocking — from A2 RDD `review-9b4846fa6e0c8eb8`)

These were reported as informational on the approved A2 candidate. They do NOT reopen the review;
they are separate later work.

- [x] **R3-001** (`app/services/recipes.py:59`) — **resuelto en A3**: `compile_rule_fields` ahora valida la
  presencia de `channel` y lanza un `ValueError` claro (`recipe has no channel parameter`), más un assert de
  integridad del catálogo.
- [ ] **R3-002** (`app/services/automation_installations.py:11`) — `installation_snapshot` returns the
  stored `parameters` dict by reference (mutable), and optional string params accept `null`. Return a
  detached copy and decide the null policy.
- [ ] **R4-001** (`app/services/automation_installations.py:36-41`) — the service establishes no
  transaction boundary; commit/rollback belongs to the caller. Ensure callers roll back on later errors.
- [ ] **R4-002** (`app/services/automation_installations.py:49-58`) — the duplicate-install precheck can
  race with concurrent requests; the DB unique constraint rejects the loser, but the `IntegrityError` is
  not translated into the documented `ValueError`. Normalize the conflict response when wiring the API.
- [x] **R3-003 — Slice 2 review** — **resuelto en Slice 3 WU3** (commit `d5a048cf`): the per-installation
  evaluation is wrapped in `try/except` + logger + `continue`, so one broken installation no longer
  aborts the tick. Original report (`app/services/time_triggers.py:109-116`) — an enabled offset
  installation whose persisted parameters no longer validate raises inside `evaluate_time_triggers`
  and aborts the worker cycle before it claims any domain events, stalling unrelated queued events on
  every tick. Isolate per-installation failures (skip + continue). Advisory WARNING from the Slice 2
  RDD review `review-41c0036acfbe328e` (the review assigned it id `R3-001`; renamed here to avoid
  colliding with the resolved A2 `R3-001`); non-blocking, does not reopen that review.

## Verification

- Backend: `uv run pytest tests/` (TDD estricto).
- Frontend: `cd web && npm test` y `cd web && npm run build`.
- Por work unit: Graph Check registrado; commit convencional; verificación observada antes de tildar.

## Progress log

- 2026-10-09 — Task doc creado desde la sesión `2026-10-09-automatizaciones-recetas`. Worktree
  `../lumat-agent-odd-automatizaciones-recetas`, branch `odd/automatizaciones-recetas`, base `07ddfb05`.
- 2026-10-09 — Slice 1 cerrado (A2, A3, A4, A5a, A5b) con PRs encadenados abiertos:
  **#545** (A2 → main), **#546** (A3 → #545), **#547** (A4 agent tool → #546),
  **#550** (A5a API → #547), **#551** (A5b UI → #550). Todos OPEN, review RDD aprobado por work unit.
  **A1 (runner/cron) queda diferido al release, en el servidor** (requiere autorización remota).
  NL input deferido dentro de A5. Slice 2 (B1 offsets) y Slice 3 (C1 resúmenes) pendientes.
- 2026-10-10 — Slice 2 abierto en worktree nuevo `../lumat-agent-odd-automatizaciones-recetas-tiempo`,
  branch `odd/automatizaciones-recetas-tiempo`, base `54fb4527` (main avanzó tras el handoff:
  release v2026.10.1 + #553). Diseño del tick cerrado (synthetic `DomainEvent`s, sin migración).
  Decisión del owner: **convivir** con `_maintain_reminder` (no duplicar el recordatorio de visita).
  B1 = WU1 (modelo de receta de tiempo) + WU2 (evaluación en el tick) + WU3 (superficie + verificación).
- 2026-10-10 — Slice 2 implementado y **RDD aprobado**. Commits `48037e8` (WU1), `8692404` (WU2),
  `cafafdc0` (WU3). Review nativo: lineage `review-41c0036acfbe328e`, 1 lente (reliability),
  riesgo medium, 421 líneas, **0 bloqueantes**, 1 advisory (R3-001). Authority **burned**. Pendiente
  humano: push + PR/merge. A1 (cron del worker) sigue diferido, así que las recetas de tiempo no
  disparan en prod todavía.
- 2026-10-10 — Slice 3 abierto en worktree nuevo `../lumat-agent-odd-automatizaciones-recetas-resumenes`,
  branch `odd/automatizaciones-recetas-resumenes`, base `576b07ef`. Diseño C1 cerrado (schedule en el
  mismo tick, sin migración, digest por payload). C1 = WU1 (modelo de recetas de calendario) + WU2
  (builder del resumen) + WU3 (evaluación en el tick + fold R3-003) + WU4 (UI + verificación). WU1
  commiteado (`85899bda`); NOTA: `infra/.env` no lo copia `rapso worktree create` — copiado a mano.
- 2026-10-10 — Slice 3 C1 backend + UI completo. Commits `85899bda` (WU1), `b8306b8d` (WU2),
  `4a81fc61` (WU3 tick), `d5a048cf` (WU3 fix R3-003), `8ffd0c64` (WU4 UI). Backend suite **1903**,
  frontend serializado **1108**, `npm run build` verde. Pendiente: review RDD del slice (base `576b07ef`)
  y push/PR del owner.
- 2026-10-11 — Slice 3 mergeado (PR #561, main `00e09e3c`). Recon read-only de los pendientes:
  el catálogo tiene 9 recetas y los 11 objetivos del diseño están cubiertos (9 recetas + 2 mecanismos
  nativos: `_maintain_reminder`, emergencia por `notify.py`). **D1 (pago) queda BLOQUEADO**: no existe
  concepto de pago en el backend; la integración de pagos es entregable aparte (Milestone 3). Owner
  decide: diferir D1 y cerrar **D2 acotado + D3** en un slice nuevo. Slice 4 abierto en worktree
  `../lumat-agent-odd-automatizaciones-recetas-transversal`, branch `odd/automatizaciones-recetas-transversal`,
  base `00e09e3c`. D3 = remover `template_event` de raíz (migración 049).
- 2026-10-12 — **Slice 4 cerrado**: D2 (acotado) + D3 mergeados (PR **#563**, main `1d98576e`). Backend
  **1925** tests verdes; `npm run build` verde; CI verde (`test` + `panel`). Review nativo RDD
  `review-5ca037e6e4ca9962` aprobado (4 lentes, 0 hallazgos, authority burned). **D1 (pago) queda fuera
  de alcance**: presupuesto aparte (Milestone 3 §3.8), no hay pagos en el sistema.
