# HANDOFF — frontend-polish (pulido general de frontend)

Fecha: 2026-10-09. Estado: T1–T11 hechos y confirmados visualmente por el owner.
Sin PR todavía. La rama tiene 9 commits sobre una base vieja → **hay que integrar
el main actual antes de PR**.

## Git / worktree

- Worktree: `/home/stefan/repos/lumat-agent-odd-frontend-polish`
  (branch `odd/frontend-polish`, HEAD `3d9943dc`). Working tree limpio.
- Base al crear el worktree: `origin/main` = `9550ffa4` (PR #540).
- AHORA `origin/main` = local `main` = `a843bd98` (PR #543, asistente-agentes-proyecto).
  Nuestra rama está **12 commits atrás** de main y **9 adelante**.
- Antes de PR: `git fetch && git merge origin/main` en la rama y correr el chequeo
  de integración pre-merge (suite frontend + `npm run build` + suite backend), ver
  `AGENTS.md` → "Pre-merge integration check".

## Stack dev (levantado en este worktree)

- Compose project `infra` corriendo **desde este worktree**, reusando el volumen
  `infra_db` (datos reales: 33 conversaciones, 34 casos, 5 usuarios). api :8000,
  db interno. Verificado healthy.
- Frontend vite en **http://127.0.0.1:5173/panel/app/** (HMR).
  Log: `/tmp/lumat-frontend-polish-web.log`.
- OJO: `infra` es identidad compartida → **un solo stack `infra` a la vez**. Antes de
  levantar otro worktree/main, bajá este:
  `docker compose -p infra -f infra/docker-compose.yml down`.
- Un worktree nuevo NO trae `infra/.env` (gitignored) ni `web/node_modules`:
  `cp <main>/infra/.env infra/.env` y `cd web && npm ci`.
- Otros worktrees activos de otros agentes (NO tocar): `odd/asistente-agentes-proyecto`,
  `odd/automatizaciones-recetas`, `odd/realistic-dev-seed`.

## Hecho — T1–T11 (commits en `odd/frontend-polish`)

| Commit | Qué |
|---|---|
| `224703ec` | Bordes de control → `--border` (claro) en todo el panel + doc en `DESIGN_SYSTEM.md`. **RDD review APROBADA** (lens review-reliability, 0 hallazgos). |
| `00a3542f` | Icono del menú de acciones `MoreHorizontal` → `EllipsisVertical` (global). |
| `78b611ed` | Fondo de los triggers de `Menu`: `--surface` claro por default, `--corp-bg` al abrir. |
| `a6c9c34f` | Fix de paginación de Conversaciones (client-side 10/página) + componente `Pagination` compartido (números + `…`) en Conversaciones, Clientes, Usuarios. |
| `fe0899e1` | `DataTable` con ancho por columna + columna identidad de Conversaciones acotada (38% + summary `max-width: 22rem`). |
| `672a3b5b` | Acciones de fila de Conversaciones: se quitó "Abrir conversación"; en filas `human` → "Devolver al agente" (→bot) + "Cerrar conversación" (→closed). |
| `a498685a` | Fix del test de stories (URL vieja). |
| `ca51448a` | Docs ODD. |
| `3d9943dc` | Fix tabs horizontales: label + número en una línea (`.tabs__tab-copy`). |

Detalle por task: `odd/tasks/frontend-polish.md`.

## Decisiones / gotchas para el próximo chat

- **Bordes de control** usan `--border` (claro) por decisión de producto; trade-off de
  contraste 1.18:1 vs 3:1 documentado en `web/DESIGN_SYSTEM.md`. `--border-strong`
  queda solo para decorativos (relleno de send deshabilitado, dot de disponibilidad).
- **Conversaciones pagina client-side sobre hasta 100 filas** (tope de la API `/panel/api/conversations`).
  El endpoint ya soporta `limit/offset/total`; si la cola supera 100, mover a server-side
  (los tabs `emergency`/`case` no tienen filtro server).
- `.tabs__tab-copy` es `inline-flex` por defecto; `grid` solo en `.tabs--vertical`.
- **Tests flaky por carga**: `AgentChat` y `ClientesList` fallan por timeout cuando otro
  agente corre su suite en paralelo; pasan aislados. No confundir con regresiones.
- **RDD**: `review mode status` → on (global). Boundary revisado = `224703ec`; los commits
  posteriores quedaron `under_budget` (sin review). Si el slice crece:
  `gentle-ai review assess --cwd <repo> --agent opencode --base-ref 224703ec --committed-only --json`.
- Gotcha RDD: un STATUS devuelto sin `--cwd` corre con el cwd del proceso → ejecutarlo con
  `cwd=worktree` o falla con `invalid_request`.

## Próximo paso

El owner sigue trayendo detalles visuales. Aplicar en este worktree, **un work unit por
cambio**, con verificación (`npx vitest run <archivos>` + `npm run build`) y commit
Conventional sin atribución. Al cerrar el hilo: `git merge origin/main`, chequeo de
integración pre-merge, push y PR.
