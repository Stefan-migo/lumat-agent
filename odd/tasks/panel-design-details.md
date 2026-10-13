# panel-design-details — frontend polish slice

Estado: en curso (arrancando). Rama `odd/panel-design-details`, base `origin/main 2554aff2`.
Worktree: `/home/stefan/repos/lumat-agent-odd-panel-design-details`.
Dev: vite http://127.0.0.1:5174/panel/app/ reusando el stack `infra` (:8000, código de main).

## Objetivo
Aplicar el lote de detalles visuales/funcionales del panel que reportó el owner,
un work unit atómico por cambio, con verificación (`npx vitest run` + `npm run build`)
y commit Conventional sin atribución.

## Por qué
El owner trajo 8 referencias visuales (dashboard, conversaciones, clientes, agenda, KB,
usuarios). Seis son frontend y entran acá; dos son CRUD de backend con borrado real y se
difieren a un worktree aparte (ver Fuera de alcance).

## Alcance (este worktree — solo frontend)
Touchpoints: `web/src/**`.

## Fuera de alcance (diferido a un worktree propio)
- **KB**: hard delete real de documentos (hoy solo enable/disable). Backend `app/panel/api/routes/kb.py`
  + `app/services/kb.py` + UI `web/src/components/pages/KbList.tsx`.
- **Usuarios**: delete real (hoy solo toggle-active). Backend `app/panel/api/routes/users.py` + UI
  `web/src/components/pages/UserManagement.tsx`. Ojo: FK restrictivas (`cases.responsible_id`,
  `conversations`, `appointments`, `notifications`, `projects.owner_id`) → delete con guardia de
  conflicto, nunca cascada silenciosa.
- **Clientes → archivar/remover casos cerrados**: no existe endpoint; `cases` está referenciado por
  conversaciones/citas → soft-archive, no hard delete.

Motivo del corte: mezclar pulido cosmético con CRUD destructivo degrada la review y sube el riesgo
de pérdida de datos en producción.

## Grafo (Graphify)
Refresh hecho al inicio de sesión (9429 nodos). Nodos consultados: `Dashboard.tsx`,
`ClientFicha.tsx`, `AppointmentDetail.tsx`, `realtime.ts`, `ConversationsList.tsx`,
`ConversationThread.tsx`, `api.ts`, `api/serializers.py`, `models.py`.

## Tareas (IDs estables)
- [x] **F1 — Dashboard "Agenda de hoy": hora formateada.** Hoy `Dashboard.tsx:176` renderiza
  `row.local_start` crudo (ISO con microsegundos, ej. `2026-10-13T16:22:05.811220`). Fix: formatear
  con el util compartido `web/src/components/shared/agendaTime.ts` (`formatAgendaSlot`, tz-aware, 24h).
  Frontend-only.
- [x] **F2 — Conversaciones + ConversationThread: banner de conexión.** Causa raíz:
  `realtime.ts:78` `subscribeStatus()` no emite el estado actual; las páginas arrancan en
  `"disconnected"` y, al navegar con el socket ya abierto (`connect()` hace early-return en
  `realtime.ts:80`), nunca reciben `connected` → banner permanente falso. Arreglo mínimo: trackear el
  status actual y emitirlo al suscribir (corrige también el indicador de `AgentChat.tsx`).
  **Decisión pendiente del owner**: ¿arreglar y dejar el banner, o arreglar y sacarlo?
- [x] **F3 — Clientes → card del caso activo: quitar el título externo redundante.** `ClientFicha.tsx`.
  Iteración con el owner: primero se renombró a "Caso activo" y luego se eliminó el título externo
  (redundante con el eyebrow "CASO ACTIVO #N"); queda solo el sub-card. Frontend-only.
- [x] **F4 — Clientes → "Casos anteriores": paginación máx 5/página.** Reusar
  `web/src/components/primitives/Pagination.tsx` en tabla desktop y cards mobile; clamp de página al
  cambiar cliente/conteo. Frontend-only. (Archivar casos → diferido.)
- [x] **F5 — Presentación del resumen (blob de texto libre).** `ClientFicha.tsx` (caso activo, ~:485)
  y `AppointmentDetail.tsx:199` (visita técnica). El resumen lo genera el LLM como texto libre
  (`personas/summary.md`); no se parsea a mano. Fix: mejorar tipografía/espaciado/estructura de lectura.
  Una mejora con label/value requeriría contrato backend → follow-up, fuera de este slice.

## Decisión abierta (F2)
El banner es un **bug de estado desactualizado**, no una caída real. Opciones:
1. Arreglar el bug y **dejar** el banner (aparece solo ante una caída real). Recomendado.
2. Arreglar el bug y **sacar** el banner de Conversaciones y del hilo.

## Criterios de aceptación
- Cada cambio = un work unit atómico con su commit (Conventional, sin atribución).
- `npx vitest run <archivos>` verde y `npm run build` (incluye `tsc -b`) verde por task.
- Sin cambios de comportamiento autorizado fuera del alcance.

## Verificación
- Frontend: `npx vitest run` (archivos tocados) + `npm run build`.
- Backend: no aplica en este slice.

## Progreso
- [x] F1 — `22940bdb`
- [x] F2 — `48e0bd04` (decisión owner: arreglar y **dejar** el banner; el fix lo vuelve preciso)
- [x] F3 — `5c528417`
- [x] F4 — `d9b414de`
- [x] F5 — `1d24885d` + `4965c623` (guard: un resumen que no arranca con un marcador conocido cae al texto completo, nunca se recorta)

- Iteración visual (owner): `b678629b` fila de "Agenda de hoy" (nombre + hora en la línea de título,
  motivo abajo); `b945d66d` quitar el título redundante del card de caso activo; `03305c73` devolver
  el fondo `--surface` al card de caso activo.

Verificación: `npm run build` ✅. Suites Dashboard / realtime / ClientFicha / ConversationsList
/ ConversationThread / AppointmentDetail / AgentChat ✅ (214 tests). `AgentChat` flakea por timeout
bajo carga paralela; aislado pasa 68/68 (flake conocido, no regresión).

## Próximo paso
Owner revisa en http://127.0.0.1:5174/panel/app/. Después: integrar `origin/main`, chequeo
pre-merge y PR. El CRUD de backend (KB, usuarios, archivar casos) va a un worktree aparte.
