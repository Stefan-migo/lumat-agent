# HANDOFF — agenda + conversaciones (continuar en chat nuevo)

Date: 2026-10-12. Estado: `main` = `8063a050`. Todo lo de este hilo está **mergeado y limpio**.

## Qué cubrió este hilo

1. Cerrar el editor de horarios por técnico (T5 de `agenda-booking-slice2`).
2. Rediseñar esa config como un tab de verdad en Agenda.
3. S1 de Conversaciones: cerrada = archivada + paginación real.

## Hecho (mergeado y limpiado)

- **`agenda-booking` slice 2 — backend** (PR #558) y **frontend T5** (PR #560): editor de horario
  semanal por técnico, materialización de `technician_availability`, API `GET/PUT
  /panel/api/technicians/{id}/schedule`.
- **PR #569 — `odd/agenda-technician-schedule-tab`**: reemplaza el `<details>` + modal de #560 por un
  **tab "Técnicos"** en el registro de Agenda (al lado de Activas / No activas), con lista en filas
  Lumat (icono de identidad + nombre + resumen semanal) y **editor inline** (DayToggle + Inicio/Fin).
  Resuelve de paso el advisory R3-001 del review de #560 (un solo editor inline a la vez). Commit merge
  `f8ab54e0`.
- **PR #571 — `odd/conversations-closed-pagination` (Conversaciones S1)**: los tabs vivos
  (Todas / Atención humana / Emergencias / Con caso) **excluyen cerradas**; "Cerradas" es el archivo.
  Paginación **server-side de 10** con la primitiva `Pagination` y rango real en el footer. Backend:
  `exclude_closed` / `emergency` / `has_case` en `GET /panel/api/conversations` + counts alineados a la
  fila de cada tab. Commit merge `8063a050`.

## Pendiente (para el próximo chat)

- ~~**Conversaciones S2 — visor de histórico por cliente.**~~ **CERRADA COMO "NO CHANGE" (2026-10-12).**
  El tab de `ClientFicha.tsx` ya es reference-faithful: se cerró en `clientes-panel-redesign` **CL-7**
  (owner review 2026-10-06). El tope de 10 mensajes + `Abrir conversación` fue **decisión del owner**, y la
  referencia (`refs/Diseño Lumat/Clientes/ClientFichaTabConversaciones.png` + `mobileTablet/Clientes/LUMAT
  client conversations on mobile and tablet-5.png`) muestra **un solo hilo, sin vista agregada**. El planteo
  original de este handoff ("histórico completo + agregado") revertía esas decisiones; el owner eligió
  dejarlo como está — no se escribió código. Residual opcional NO pedido: la columna `Conversación` de la
  card de mensajes es vestigial (la card muestra un hilo; la referencia no la tiene).
- ~~**Conversaciones S3 — sesión nueva vacía.**~~ **VERIFICADA (2026-10-12), sin cambio de código.**
  Confirmado por código y por tests verdes en el test DB aislado:
  `get_or_create_conversation` filtra `state != CLOSED` y crea una nueva (`app/chat/state.py:47-66`); la
  memoria es por cliente (`load_customer_context`, `app/services/tukulpan.py:704`, lee `scope="customer"`
  por `entity_id`). Tests verdes: `test_chat_state.py::test_cr5_closed_conversation_opens_new`,
  `test_handoff.py::test_cr5_closed_opens_new_conversation_through_ingest`,
  `test_chat_state.py::test_s2_from_db_carries_memory_context`,
  `test_customers.py::test_cr5_history_lists_conversations_cases_messages`.
- **Duración de la visita en el chatbot.** Hoy está **fija en 60 min** (`app/chat/nodes/booking.py:21`
  `DURATION_MINUTES = 60`, usado en búsqueda de cupos y en `book()`). No hay setting ni se le pregunta al
  cliente. El panel sí permite duración variable (crear/reprogramar). Probable próximo: **durar por
  servicio**. No empezado.
- Fuera de este hilo (unidades separadas): contenido de la KB de VALORES, rediseño de copy/flujo del
  chatbot (H2/H3), y comodidad de comuna en los cupos.

## Gotchas verificados

- **La suite web completa NO es señal local**: timeouts de 5 s por carga. Correr archivos focales;
  **CI sí corre la suite web completa** (job `panel`) y es el gate real. El `panel` de #571 falló por un
  test de stories que quedó sin actualizar (URL vieja); se arregló con `6729ae1e`. No confiar solo en
  corridas focales.
- **Disciplina pre-merge**: mergear `origin/main` a la branch antes de mergear el PR (fuerza CI sobre el
  árbol real). Ambos PRs la cumplieron.
- **`rapso worktree cleanup <slug> --remote`** borra worktree + branch local/remota pero **deja el test
  DB**: `docker rm -f lumat-test-lumat-agent-odd-<slug>-db-test-1` y
  `docker network rm lumat-test-lumat-agent-odd-<slug>_default`.
- Branch sin PR por si hace falta: `odd/agenda-technician-schedule-tab` ya mergeada/borrada; las demás
  branches no mergeadas son de otros agentes (no tocar).

## Entorno dev (main)

- Stack: `infra-api-1` (:8000, `--reload`, repo main bind-mounted) + `infra-db-1`; Vite de main :5173.
- **Migración `048_technician_weekly_schedule` se aplicó a mano** al dev DB (estaba atrasado).
- Hay un horario cargado para **jperez** (id 2): Lun–Vie 09:00–18:00, Sáb 09:00–14:00.
- Cola de conversaciones en dev: ~13 no cerradas, 2 cerradas (cambia con el uso).

## Referencias Engram

- `odd/agenda-booking-slice2/tasks` — task doc + entregas backend/frontend + review.
- `odd/agenda-technician-schedule-tab/tasks` — task doc del tab de técnicos.
- `odd/conversations-closed-pagination/tasks` — task doc de S1.
- Handoff previo: `odd/handoffs/agenda-booking-slice2-frontend.md`.
