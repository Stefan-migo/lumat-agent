# HANDOFF — panel-visual-alignment → feature COMPLETO (todas las tabs)

Fecha: 2026-10-14. Estado: **T1, T1b, T2, T2c, T3, T4, T5, T6, T7, T8, T9, T10, T11, T12, T13, T14 listos y
verificados. No queda ninguna tarea del feature.**
Worktree: `/home/stefan/repos/lumat-agent-odd-panel-visual-alignment` — branch `odd/panel-visual-alignment`
(HEAD `a66f59b2`). Task doc: `odd/tasks/panel-visual-alignment.md` (leer hasta `## Log`; L25 es el último).
Base original de la branch: main `6d7988b2`. **OJO: main ya avanzó a `1719cc43`.** Ningún otro worktree
toca `web/`.

## Hecho esta sesión — T5 (tab Hilos), ref 9

Reemplaza el placeholder desactualizado de `ProjectsPage.tsx`. Decisiones confirmadas por el owner:
1. El empty state se adapta a **proyecto realmente vacío**: título `Aún no hay hilos en este proyecto` +
   copy/CTA/nota de la ref (`Abrir historial`). La copy de `No disponible` de la ref queda **solo** para
   el estado denied/error.
2. El subtítulo por fila necesitaba un backend acotado: `preview` = snippet de una línea del último
   mensaje.

Commits: `849aa8e2` (backend) + `807c8a45` (frontend) + `2ba5bd15` (docs).

- **Backend**: `to_internal_chat_thread_summary_dict` emite `preview` (colapsa whitespace, saca
  `**`/backticks, cap 140 + `…`). Tests: 2 nuevos en `tests/integration/test_assistant_chat.py`.
- **Frontend**: `ProjectThreads.tsx` (nuevo) — tabla poblada (búsqueda + sort `Más recientes`, paginado,
  `Nuevo hilo` con `createChatThread`, `Abrir hilo` + menú `...` renombrar/eliminar) + empty/unavailable.
  `InternalChatThreadSummary` ganó `preview`; `formatThreadActivity` en `threadDateGroups.ts`;
  `ProjectsPage` ganó `onOpenThread`/`onOpenHistory`, cableados en `AppShell`, `TechnicianShell` y el
  `AssistantWorkspace` embebido.
- **Layout**: la card usa una **container query** (`container-type: inline-size` + `@container
  (max-width: 38rem)`) para que la columna angosta del asistente embebido apile la fila en vez de
  romperla. Verificado en vivo.

Verificación T5: frontend focalizado 20/20; backend preview tests verdes; `npm run build` verde; suite
completa 1211 passed (los 2 flaky por carga pasan aislados 110/110); capturas standalone (1280) y
embebida (1280, columna ~456px) coinciden con la ref 9 imagen 1, sin overflow horizontal, y el
`.tabs__panel` embebido sigue `overflow-y: auto`. RDD assess: medium, `under_budget`, no review due.

## Hecho después de T5 — T14 (fixes mobile), L25

El owner reportó dos bugs mobile: (1) en el tab Contexto la barra de tabs se rompía (el contenido la tapaba),
y (2) las filas de Skills colapsaban (título/descripción en una columna de 25px).
- **Causa de (1)**: `.tabs` es un flex column; en mobile el `[role="tablist"]` recibe `overflow-y: hidden`
  → su min-size automático cae a 0 → se encoge (20px) bajo el panel alto de Contexto. En las otras tabs el
  panel es más corto y no hay presión, por eso "solo en Contexto". Fix en `primitives.css`
  (`flex-shrink: 0` en `.tabs [role="tablist"]`) — **cambio de primitivo compartido (risk item 3)**.
- **Fix (2)**: media query `max-width: 39.99rem` que manda los chips (`__meta`) a su propia línea (el copy
  pasó de 25px a 262px) + `.project-skills__project-card` para apilar la acción `Agregar habilidad`.
- Commits `62faed16` (fix) + `adb77b9c` (probes Playwright + alineación de breakpoint) + `a66f59b2` (docs).
- **Verificado por un verificador independiente** (copias scratch, actual vs baseline `2ba5bd15`): ambos
  fixes confirmados, sin regresión en 11 rutas con tabs, sin blockers. Un advisory pre-existente: el
  `min-height` mobile de tabs del primitivo corta en `39.99rem`, así que a ≥640px la barra mide 34px.
- **Probes de regresión durables**: `web/playwright/panel-mobile-layout.spec.ts` (3/3 verde con el fix,
  2/3 rojo en el baseline). Se corren con `npm run test:e2e` (usa el vite de 5173).
- Recordado: el empty state real de Hilos **no** lleva botón `Nuevo hilo` (decisión del owner).

## Entregado — cadena de 8 PRs stacked (2026-10-14)

El feature se entregó partido en 8 slices encadenados (el branch tenía 3774 líneas / 41 archivos, sobre la
guía de 400 y la norma del repo de ≤~800). Cada slice es un branch `odd/panel-visual-alignment-sN` basado
en el anterior, con CI verde y Chain Context. El árbol del último slice es **idéntico** al árbol verificado.

| PR | Slice | Base | Budget |
| --- | --- | --- | --- |
| #605 | S1 chrome + Contexto | `main` | 372 |
| #606 | S2 backend carpetas (mig 055) | s1 | 339 |
| #608 | S3 árbol de archivos UI | s2 | 767 |
| #609 | S4 mover + upload | s3 | 451 |
| #610 | S5 toast + Conocimiento + scroll | s4 | 486 |
| #611 | S6 Agentes + Skills | s5 | 631 |
| #612 | S7 Hilos | s6 | 788 |
| #613 | S8 fixes mobile + probes | s7 | 153 |

**Estado: TODOS MERGEADOS a `main`** (2026-10-15, `main` = `58c9880f`). Branches del feature borradas
(local y remoto). El árbol de `main` es idéntico al verificado (`git diff` vacío).

Pitfall que costó tiempo (para no repetir): en GitHub, **retargeteá cada hijo a `main` ANTES de que mergee
su padre** (o antes de borrar la branch del padre). GitHub NO retargetea solo: un hijo cuya base es una
branch mergeada se mergea *dentro de esa branch* (mi #608 terminó en la branch `s2`, no en `main`; se
recuperó con el PR #614). Y borrar la branch base de un PR lo **cierra**. Además el repo exige la branch
al día con la base: rebaseá cada hijo sobre el `main` nuevo **después** de que mergee el padre.

Notas de construcción:
- Los commits se linearizaron sobre `origin/main` con `git rebase --onto origin/main origin/main` (único
  conflicto: el commit de T5 tocaba `TechnicianShell.tsx`, borrado en main por #604 → se dropeó ese edit).
- El fix de `test_migrations.py` se repartió: S1 registra `054`, S2 registra `055` + `project_folders`.
- La DB de test **no** se resetea sola (el fixture reaplica migraciones, no dropea): para validar un prefix
  recrearla (`psql .../postgres -c "DROP DATABASE lumat WITH (FORCE);" -c "CREATE DATABASE lumat OWNER lumat;"`).

Pre-merge (AGENTS.md): al mergear, cada branch debe tener el head actual de `main` (merge de `origin/main`)
+ integración local (suite + `npm run build`). `mergeable: CLEAN` no prueba que el árbol combinado compile.

## Gotchas (para no regresar)

- **RDD ON (global)**: por work-unit commit, `gentle-ai review assess --cwd . --agent opencode --base-ref
  HEAD~N --committed-only --json`. Viene dando medium / `under_budget` / `review_due false`.
- **`main` en `1719cc43`**: merge antes de PR + integración.
- **Vite sirve módulos en `/panel/app/src/...`** (base `/panel/app/`), NO en `/panel/src/...`. Un 404 ahí
  es URL equivocada. Si un cambio no aparece: matar vite, `rm -rf web/node_modules/.vite`, reiniciar.
- **El bash tool mata procesos background no detachados** → `setsid ... & disown`. Ojo: no uses
  `pkill -f "…vite"` (matchea el propio shell); usá el truco `[v]ite`. Hoy hay **dos** vites: 5173 (viejo,
  de otra sesión) y 5174 (este worktree).
- **`<dialog>` cerrado queda en el DOM.** `getByRole` lo ignora, pero `getByText` SÍ matchea su contenido
  → scopeá con `within(screen.getByRole("dialog"))`.
- **`...` vertical sin fondo ni borde** es decisión global (`.menu__trigger--icon`): no le devuelvas fondo
  ni borde.
- **La tab embebida scrollea como un todo** (S6e/T13): `.projects-page--embedded` es flex column y
  `.tabs__panel` scrollea. Contenido nuevo de tab entra solo en ese scroll.
- **El tab de Hilos reacciona a su ancho con container query**, no a la viewport: si agregás columnas,
  mantené el layout responsive por contenedor, no por media query de viewport.
- **`.markdown`** (primitives.css) es el render de markdown compartido — reusalo.
- Proyecto demo `test` (2 hilos) y `teest2` (1 hilo). Para el estado vacío, usá un proyecto sin hilos.

## Key Learnings

1. T5 quedó completo: `ProjectThreads.tsx` reemplaza el placeholder y lista los hilos del proyecto vía `GET /panel/api/chat/threads?proyecto=<slug>`.
2. El subtítulo por fila salió de un campo `preview` nuevo en el summary de hilos (snippet de una línea del último mensaje, sin markdown de énfasis).
3. El layout del tab usa container queries (`@container`) porque el workspace embebido da una columna angosta con viewport ancha; una media query de viewport no alcanza.
4. `main` avanzó a `1719cc43`; antes de mergear hay que traer main y correr la integración local (suite + `npm run build`, que es donde vive el typecheck).
