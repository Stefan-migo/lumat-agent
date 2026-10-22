# HANDOFF — ODD `kb-panel-scope` (leak de privacidad en el panel de KB)

**Fecha**: 2026-10-15. **Estado**: **no iniciado**. ODD nuevo e independiente.
**Origen**: hallazgo durante `asistente-lumat-config-layer` (T9). El owner lo difirió a su propio ODD.

## Locator (leer PRIMERO)

- **Base**: `main` @ `9eaaceba` (merge de #626). El ODD `asistente-lumat-config-layer` está **cerrado** (T0–T9 mergeados).
- **No hay worktree todavía**. Con consentimiento explícito del owner:
  `rapso worktree create kb-panel-scope --yes`
  → `/home/stefan/repos/lumat-agent-odd-kb-panel-scope`, branch `odd/kb-panel-scope`.
- **Memoria (Engram)**: obs `6643` (el hallazgo con evidencia), obs `6647` (session summary). No hay feature doc todavía — se crea al arrancar (`odd/tasks/kb-panel-scope.md`).

## El problema (verificado sobre `main @ 9eaaceba`)

Un documento de KB con `project_id != null` (privado de un proyecto) **aparece en la sección GLOBAL "Base de conocimiento"**, etiquetado solo por su audiencia (ej. "Interno (solo Lumat)") y sin indicar a qué proyecto pertenece. Eso rompe la privacidad por usuario/proyecto.

Evidencia:

- `app/panel/api/routes/kb.py:71-77` — `kb_list` (`GET /panel/api/kb`): `select(KbDocument).order_by(KbDocument.id.desc())`, **sin ningún filtro**. Devuelve TODO, incluidos los `project_id != null`.
- `web/src/components/pages/KbList.tsx` — **no tiene columna ni filtro de proyecto**; solo muestra "Audiencia". Por eso un doc de proyecto se ve como "Interno (solo Lumat)" en la lista global.
- `to_doc_dict` (`app/panel/api/serializers.py:577`) **sí expone `project_id`** — el backend ya manda el dato; el front lo ignora.
- `web/src/components/pages/ProjectResources.tsx:478` reusa el mismo `GET /kb` y **filtra en el cliente** (`doc.project_id === projectId`), gateado por `isAdmin` (líneas 79/85).
- La ruta es **admin-only** (`require_admin_json`).
- `kb_search` (`GET /panel/api/kb/search`, `kb.py:81`) corre el probe admin con `audience=None` (`kb.py:94`) → también puede exponer contenido de proyecto.

**Lo que NO está roto**: la retrieval del agente ya está bien scopeada. `app/services/kb.py` `retrieve` filtra `project_id IS NULL` (global) cuando no hay proyecto, o `global ∪ project:<id>` cuando lo hay (~líneas 425-428). **El leak es solo de la superficie del panel** (lista + probe), no de la retrieval del asistente.

## Por qué NO agregar un valor a `KbVisibility` (evidencia)

Hay **dos ejes ortogonales**:

| Eje | Campo | Significa |
| --- | --- | --- |
| Audiencia | `visibility` (`customer` \| `internal`) | *quién puede fundamentar su respuesta* en el doc |
| Scope | `project_id` (`null` \| `id`) | *de quién es* el doc |

El problema es del eje **scope**, no del eje audiencia. Agregar `"proyecto privado"` a `KbVisibility` colapsa los dos ejes en un enum y produce una matriz incoherente (¿un doc de proyecto puede ser `customer`? ¿`internal`?).

## El fix correcto (scope-based, sin migración)

**Regla**: el listado global de la KB muestra **solo documentos globales**.

1. `kb_list`: filtrar `KbDocument.project_id.is_(None)`.
2. `kb_search` (probe admin): scoped a global, **o** marcado explícitamente como "incluye proyectos" si el owner prefiere verlos. Decidir con el owner (yo propongo global-only, consistente con la sección).
3. Front: la sección global "Base de conocimiento" deja de listar docs de proyecto; esos viven en la página del proyecto (`ProjectResources`), que ya los muestra a admins.

**NO** tocar el modelo ni `KbVisibility`. `project_id` ya existe. Cero migración.

## Alcance propuesto (a confirmar al arrancar)

- **T1**: `kb_list` scoped a `project_id IS NULL` + tests (un doc de proyecto NO aparece; uno global SÍ).
- **T2**: decidir y aplicar el scope de `kb_search` (global-only vs marcado).
- **T3 (opcional, decisión del owner)**: mostrar en la sección global una columna "Proyecto" para los docs de proyecto **en vez de** ocultarlos. Default propuesto: **ocultar** (lo que pidió el owner).

### Criterio de aceptación observable
- `GET /panel/api/kb` **no** devuelve documentos con `project_id != null`.
- La sección "Base de conocimiento" (`KbList`) no lista docs de proyecto.
- Los docs de proyecto siguen visibles en la página del proyecto (`ProjectResources`, admin).
- La retrieval del agente **no cambia** (ya estaba correcta).

## Tests a tocar

- Backend panel API: `tests/functional/test_api_kb_settings.py` (cubre `GET /panel/api/kb`; el listado está en ~líneas 215-220).
- Backend servicio KB: `tests/integration/test_kb.py`, `tests/integration/test_kb_triage_scope.py`.
- Frontend: `web/src/components/pages/KbList.test.tsx`, `KbDocumentDetail.test.tsx`.

## Env, comandos y gotchas

- Worktree: `rapso worktree create kb-panel-scope --yes`; `.venv` con `uv sync`; `mkdir -p media`; copiar `infra/.env` del worktree primario; DB de test `bash infra/test-db.sh up` (**el puerto deriva del slug**; el `env` te lo dice).
- **Antes de pytest SIEMPRE**: `eval "$(bash infra/test-db.sh env)"`.
- Backend: `uv run --no-sync pytest tests/` — el `pyproject` ya agrega `-q`; **NO agregues otro `-q`** o desaparece la línea de resumen.
- Frontend: `cd web && npx vitest run --maxWorkers=2`; build `cd web && npm run build` (tsc -b + vite).
- RDD: `gentle-ai review mode status` (on global). Assess por commit: `gentle-ai review assess --cwd <worktree> --agent opencode --base-ref <sha> --committed-only --json`.
- Reglas: chat en Rioplatense; **artefactos/código/commits/docs en inglés**; sin `Co-Authored-By`; ODD TDD RED→GREEN; un work unit = un commit (≤5 archivos); actualizar feature doc + mirror Engram por task.
- `main` tiene branch protection `strict:true` (sincronizar `origin/main` en la rama antes del merge); el owner mergea con `gh pr merge <n> --merge --admin`.
- `graphify` es gate: `graphify /home/stefan/repos/lumat-agent --update` al cerrar la sesión; después `graphify cluster-only /home/stefan/repos/lumat-agent` para regenerar `GRAPH_REPORT.md`.
