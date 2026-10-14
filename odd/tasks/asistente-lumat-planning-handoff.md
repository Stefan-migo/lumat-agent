# ODD: asistente-lumat-planning-handoff — T8 (handoff de la sesión de planning al ejecutor SDB)

**Objective**: Al cerrar una sesión de planning sobre Lumat con una acción concreta, el facilitador OFRECE el handoff y, con confirmación explícita del admin, la acción se lleva a un turno de ejecución verificado (modelo por efecto), sin romper el carácter read-only de la sesión.
**Branch**: `odd/asistente-lumat-planning-handoff` · **Base**: `main` = `41cee9f4` · **Delivery**: ask-on-risk (forecast abajo)
**Test runner**: backend `uv run --no-sync pytest tests/` (suite completa, secuencial) con `eval "$(bash infra/test-db.sh env)"`; si se toca `web/`: `npm test` + `npm run build`.

## Specs

**S1 — Oferta al cerrar.** Al cerrar una sesión de planning que (a) es sobre Lumat y (b) tiene una acción concreta, el facilitador ofrece el handoff: resume la acción y pide confirmación explícita. Criterio de aceptación (handoff, verbatim): *"Al cerrar una sesión de Lumat con acción concreta, el agente **ofrece** 'cerrar con reporte + handoff'; con confirmación del admin, el handoff queda registrado (vía `sdb_requested` / el turno de ejecución), con verificación."*

**S2 — Confirmación explícita admin-only.** El handoff se registra SOLO con una acción explícita del admin; nunca inferido de texto libre (D6). Criterio (verbatim): *"Un usuario no-admin no puede disparar el handoff (403, igual que hoy)."* y *"El agente **nunca** infiere el handoff de texto libre."*

**S3 — Ejecución en el mismo hilo, con verificación.** Confirmado el handoff, se arranca un run nuevo en el mismo hilo con `sdb_requested=True`, para que el loop normal + verificación ejecute la acción. La sesión de planning sigue read-only (no ejecuta tools de negocio dentro de la sesión).

**S4 — Sin handoff = solo reporte.** Criterio (verbatim): *"Un cierre sin Lumat o sin acción concreta **no** genera handoff."*

**Nota de alcance (verificador diferido).** La verificación de efectos está a medio construir: `success_criterion` no se produce (ausente del prompt del planner), así que `run_verification` devuelve `unverifiable: no-observable-criterion`. Por eso el handoff queda registrado y ejecuta por el camino verificado, pero la verificación es **nominal** hasta reparar el eslabón del criterio (feature aparte, diferido por decisión del owner 2026-10-14). No se repara acá.

## Decisiones de diseño

- **Hilo**: mismo hilo, run nuevo tras el close. Evidencia: `sdb_requested` es un parámetro *per-run* y no se persiste (`create_run_message` lo acepta y lo descarta, `app/services/agent_chat.py:343-373`); tras `close` la sesión pasa a `closed` (`app/services/planning.py:188`) y el filtro de tools de negocio se libera; el admin ya está en ese hilo.
- **Disparador**: se reusa el flag admin-only `sdb_requested` de `send_message` (`app/panel/api/routes/chat.py:482` → 403 no-admin). No se inventa mecanismo nuevo (SDB-16).
- **Señal de "acción concreta"**: nota `next_step` capturada con confirmación explícita vía `planning.record_note` (`app/services/planning.py:108`), no texto libre.
- **Mecanismo de confirmación (elegido)**: el frontend emite el mensaje de handoff con `sdb_requested: true` desde un control explícito del admin. Alternativa considerada y descartada: reusar el flujo de aprobación (`approve_plan → execute`) — descartada porque ese camino NO pasa por `verify_effects` (gap Slice 8), o sea no da "con verificación".

## Tasks

- [x] **T1 — Oferta al cerrar.** S1, S4. Route: inline. Extender el resultado de `_planning_close` (`app/chat/assistant/tools/registry.py:755-768`) para exponer la propuesta de handoff cuando la sesión tiene al menos una nota `next_step`, y agregar la regla de oferta/confirmación en `agent/prompts/planning_facilitator.md`. Tests: con `next_step` → ofrece; sin `next_step` → solo reporte. **Done** — commits `aa1cd537` (propuesta + tests) y `c71aea43` (overlay). RED observado (ImportError `handoff_candidate`), GREEN, suite completa **2112 passed**. `planning.handoff_candidate` (`app/services/planning.py`); `close_session` y `_planning_close` exponen `handoff`.
- [ ] **T2 — Confirmación explícita admin-gated.** S2. Route: inline. `web/src/api.ts` `sendChatMessage` gana `sdb_requested` opcional; control de confirmación en la UI del hilo cuando hay propuesta de handoff. Gate admin ya existe (`chat.py:482`); test de 403 no-admin se conserva. Tests backend + frontend.
- [ ] **T3 — Run de handoff en el mismo hilo.** S3. Route: inline. Verificar/asegurar que el mensaje con `sdb_requested=True` arranca el run normal en el mismo hilo y llega a `verify_effects` por la rama `handoff` (`app/chat/assistant/nodes.py:865`). Tests: run arranca con el flag; verificación disparada por la rama handoff.
- [ ] **T4 — Spec y docs.** S1–S4. Route: inline. Actualizar `openspec/specs/sdb-native/spec.md` (SDB-16) si aporta; nota de verificación nominal.

Forecast: ~250-350 líneas autoradas (backend chico + frontend del control + tests). Bajo el presupuesto de ~400.

## Log

- **L1 (2026-10-14)** — Request del owner al retomar (verbatim): *"hey chat continuamos desde aca. dame un overview antes de continuar 📄 odd/handoffs/asistente-lumat-planning-t8.md (repo lumat-agent)"*. Origen: handoff `odd/handoffs/asistente-lumat-planning-t8.md`; T8 = S9 del feature `asistente-lumat-planning-guiado` (mergeado, PR #595).
- **L2 (2026-10-14)** — El owner pidió entender SDB antes de decidir. Investigación: SDB hoy = loop normal + verificación condicional; el `success_criterion` nunca se produce → el verificador devuelve `unverifiable`. Owner decidió: (1) **no** construir el agente multi-paso (no hay ejecutor multi-paso; no hay casos observados); (2) dejar la decisión de cerrar/cortar el verificador para cuando aparezca un caso real; (3) proceder con T8 sobre el modelo por efecto.
- **L3 (2026-10-14)** — Nueva base: `main` avanzó a `41cee9f4` (PR #596, `chatbot-conversation-inspection`); hay trabajo concurrente en curso (`chatbot-assistant-settings-write`, `panel-visual-alignment`). Se ramifica desde `41cee9f4`, no desde el `82210e1a` del handoff.
- **L4 (2026-10-14)** — Exploración read-only del cierre de planning + plumbing `sdb_requested` (mapa en Engram `discovery/...plumbing-sdb-requested`). Hallazgos: `sdb_requested` per-run y no persistido; sin productor no-HTTP; `planning.*` no está en `EFFECT_TOOLS`; el patrón propose→confirm existente es el flujo de aprobación; no hay señal estructurada de "Lumat/acción concreta". Recomendación: mismo hilo, run nuevo, flag reusado.
- **L5 (2026-10-14)** — Worktree creado y provisionado (`rapso worktree create`, + `uv sync --frozen`, `.env`, `npm ci`, `bash infra/test-db.sh up`).
- **L6 (2026-10-14)** — T1 done. Oferta al cerrar implementada: `planning.handoff_candidate(cortex)` devuelve `{"actions": [...]}` cuando hay notas `next_step` con contenido, `None` si no; `close_session` y `_planning_close` lo exponen; overlay con la regla "Offer the handoff, never assume it". Supuesto registrado: la condición "tema de Lumat" se trata como inherente a la sesión (corre en el asistente Lumat); el gate implementado es "acción concreta = nota `next_step` capturada". Si el owner quiere un gate más estricto de "Lumat", es follow-up. RED → GREEN; suite completa 2112 passed.
