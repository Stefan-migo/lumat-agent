# HANDOFF — asistente-lumat-config-layer → T5 (chat nuevo)

**Fecha**: 2026-10-15. **Estado**: T0–T4 hechos y **mergeados a `main`**. T5–T9 pendientes.

## Locator (leer PRIMERO)

- **Feature doc (fuente de verdad)**: `odd/tasks/asistente-lumat-config-layer.md` — ya en `main`.
  Leer hasta `## Log`. Ahí están Specs S1–S9, Tasks T0–T9 y el Log L1–L22 con toda la evidencia.
- **Base**: `main` @ `f4b5489a` (merge de #618). No hay worktree activo: el anterior se limpió.
- **Mirror Engram**: topic `odd/asistente-lumat-config-layer/tasks` (obs 6612).
- **Nuevo worktree**: con consentimiento explícito del owner, `rapso worktree create asistente-lumat-config-layer-t5 --yes`
  → `/home/stefan/repos/lumat-agent-odd-asistente-lumat-config-layer-t5` (o un slug nuevo para T5).

## Estado

T0–T4 **done y mergeados** vía 3 PRs encadenados: #616 (T0–T2), #617 (T3), #618 (T4).
T5–T9 pending (ver la tabla de Tasks del feature doc).

## T5 — multimodal tool results (S5)

Owner, verbatim: *"no hay forma de que el agente pueda seleccionar una imagen del proyecto y
verla solo a traves de tools es lo unico que me queda pendiente. eso tambien solucionaria que una
imagen del hilo no se inyecte constantemente en cada mensaje."*

Diseño: **una tool devuelve un handle de imagen; el harness agrega la imagen como parte
`image_url` a la llamada del modelo.** El agente debe poder ver **una imagen del proyecto Y una
del hilo** on demand.

Hoy (a verificar en el código):
- Los tool results son **texto JSON**: `_render_tool_evidence` (`app/chat/assistant/nodes.py`, ~788)
  y el `_plain` de `app/chat/assistant/tools/registry.py`.
- `build_multimodal_content` (`app/chat/assistant/attachments.py:70`) **sólo lee adjuntos**.
- La visión **funciona** cuando la imagen va como `image_url` base64 al responder
  (`nodes.py`, ~1108); el mecanismo nunca estaba roto, sólo no se ejercía por tools.
- `read_project_file` devuelve texto; para un PNG devuelve texto vacío → falta una tool que
  devuelva la imagen (proyecto o hilo).

Piezas probables a tocar: una tool nueva tipo `view_image`/`read_image` (handle por `file_id` o
`attachment_id`), el transporte del handle en el tool result, y la extensión de
`build_multimodal_content` (o del armado del mensaje) para inyectar la imagen del tool result en
el próximo turno del planner/responder. Cerrar el diseño con el owner antes de codear (TDD).

## Env del worktree nuevo

- `.venv` sincronizado (`uv sync`) y `media/` creado.
- DB de test aislada: `bash infra/test-db.sh up` (puerto derivado = **6376**).
  `infra/.env` copiado desde el worktree primario.
- `web/node_modules` instalado (`npm install`).
- **Antes de pytest**: `eval "$(bash infra/test-db.sh env)"` (si no, el admin URL cae al usuario
  `app` y falla auth).

## Comandos

- Backend: `uv run --no-sync pytest tests/ -q` (suite completa).
- Frontend: `cd web && npx vitest run --maxWorkers=2` (la suite completa puede crashear por memoria;
  el default sin `--maxWorkers` es más pesado).
- Build: `cd web && npm run build` (tsc -b + vite).
- RDD: `gentle-ai review mode status` (on global). Assess por commit:
  `gentle-ai review assess --cwd <worktree> --agent opencode --base-ref <main-sha> --committed-only --json`.

## Reglas y gotchas

- Chat en Rioplatense; **artefactos/código/commits/docs en inglés**; sin `Co-Authored-By`.
- ODD: TDD (RED→GREEN) cuando hay test determinista; un work unit = un commit (≤5 archivos);
  actualizar el feature doc + mirror después de cada task. Slice nuevo = rama/worktree nuevo y su PR.
- **`main` tiene branch protection**: `strict: true` (la rama debe contener el head de `main` antes de
  mergear → sincronizar `origin/main`), checks requeridos **`test` + `panel`**, y **review requerido**.
  El owner mergea sus PRs sin review usando `gh pr merge <n> --merge --admin` (bypass del review).
  GitGuardian **no** es requerido: marca falsos positivos por fixtures `password="..."` en tests.
- **CI** (`.github/workflows/tests.yml`): corre `pytest` + `npm ci`/`build`/`test` en cada PR. Si no
  dispara tras un push, re-pushear o `gh workflow run tests.yml --ref <branch>`.
- La suite de frontend es sensible a memoria: usar `--maxWorkers=2`.
