# panel-proyectos-crud

Gestión real de proyectos en el panel: borrado definitivo, mover archivos y carpetas entre proyectos,
archivados fuera del worktree y la página Administrar proyectos reconstruida sobre el design system.
Riesgo alto: item 1 (borra hilos, archivos y blobs del disco sin vuelta atrás) e item 3 (agrega
contratos nuevos de API que el panel consume; ninguno existente se rompe).

## Specs

**S1 — Los proyectos archivados no aparecen como activos en el worktree.**
Texto del owner, verbatim: «Cuando se crea un nuevo proyecto, este no es posible de eliminarse. se puede
archivar pero sigue mostrandose en el worktree de proyectos. [Image#2]».
El panel de proyectos del asistente (`AssistantWorkspace`) lista solo proyectos con `status = "active"`;
un proyecto archivado desaparece de ese listado, del selector de proyecto y de la lista de hilos del
worktree. No queda como opción para iniciar chat ni para elegir proyecto. Decisión del owner: se ven
solo en Administrar proyectos mediante un filtro (S5).

**S2 — Cada proyecto tiene un menú de acciones junto al botón de chat.**
Texto del owner, verbatim: «aqui hay que agregar un boton mas que este al lado del boton nuevo chat de
cada proyecto. en este boton mas se abrira un dropdown button con distintas alternativas. primero
moveremos el contexto y archivos. ademas del eliminar button. para eliminar definitivamente el
proyecto, si es necesario. [Image#3]».
En la fila de cada proyecto del worktree, inmediatamente a la derecha del botón «Iniciar chat en
<proyecto>», aparece un botón de menú con `aria-label="Acciones de <proyecto>"` que abre un dropdown con
exactamente dos acciones: `Mover contexto y archivos` y `Eliminar proyecto`. El botón reutiliza el
primitivo `Menu` ya existente y respeta teclado y foco. El proyecto `default` («General») no ofrece
`Eliminar proyecto`.

**S3 — «Mover contexto y archivos» mueve archivos y carpetas al proyecto destino.**
Decisión del owner: mover mueve solo `project_files` y `project_folders`; los hilos **no** se mueven.
El diálogo pide el proyecto destino entre los proyectos activos del mismo owner (nunca el origen),
mueve todas las filas del proyecto origen conservando la jerarquía de carpetas y el documento de KB
asociado a cada archivo, y deja el origen sin archivos ni carpetas. Si el destino ya tiene una carpeta
con el mismo nombre en el mismo nivel, el archivo o carpeta se mueve dentro de esa carpeta en lugar de
duplicarla. La operación es atómica y deja auditoría `project.move_files` con el origen, el destino y
los conteos.

**S4 — «Eliminar proyecto» borra definitivamente y no se puede deshacer.**
Decisión del owner: «Borrado total, irreversible». El diálogo nombra el proyecto, enumera lo que se
pierde (hilos, archivos, carpetas, memorias, documentos de KB) con sus conteos, y exige escribir el
nombre exacto del proyecto para habilitar el botón destructivo. Al confirmar, `DELETE
/panel/api/projects/{slug}` borra en una sola transacción: hilos del proyecto con sus mensajes,
artefactos y adjuntos; archivos y carpetas; documentos de KB del proyecto; memorias del namespace;
alias y auditoría del proyecto; y la fila del proyecto. Los blobs de los archivos, artefactos y
adjuntos borrados se eliminan del disco después del commit. El proyecto `default` no se puede eliminar
(`400`), un slug inexistente devuelve `404`, y un proyecto ausente para otro owner devuelve `404`.

**S5 — Administrar proyectos es una tabla con CRUD y un modal de creación.**
Texto del owner, verbatim: «el administrar proyectos "/panel/app/projects" no tiene dise;o alguno esta
completamente roto. tiene el formulario para un nuevo proyecto en la misma pagina, no es un modal que se
abre al clickear un boton. los proyectos se muestran en la tabla. pero no tienen el CRUD en la tabla».
La página muestra un encabezado con la acción primaria `Nuevo proyecto`, que abre un `Dialog` con el
formulario (slug, nombre, propósito) y sus estados de validación; el formulario ya no vive en la página.
La tabla lista los proyectos con `Proyecto`, `Propósito`, `Estado` y una columna final de acciones con
menú por fila: `Abrir`, `Renombrar`, `Archivar`/`Reactivar`, `Mover contexto y archivos`, `Eliminar`.
Sobre la tabla hay un filtro `Activos / Archivados / Todos` (por defecto `Activos`) y búsqueda por
nombre. Cubre estados de carga, vacío, filtrado vacío, error y sin permiso. Todo consume tokens y
primitivos existentes según `web/DESIGN_SYSTEM.md`, y ese documento se enmienda en la misma entrega:
la entrada `### Proyectos (product-change contract)` pasa a describir el modal, el filtro y las
acciones por fila.

**S6 — Reactivar un proyecto archivado lo devuelve al worktree.**
`POST /panel/api/projects/{slug}/reactivate` deja `status = "active"`, audita `project.reactivate` y el
proyecto vuelve a listarse en el worktree (S1). Archivar (`POST /panel/api/projects/{slug}/archive`)
hace lo inverso y rechaza `default` con `400`. Ambas comparten la validación de owner del resto de los
endpoints de proyecto.

**S7 — Renombrar desde la tabla conserva el slug.**
`PATCH /panel/api/projects/{slug}` con `{"name": ...}` reutiliza `projects.rename` (alias incluido),
rechaza nombre vacío con `422`/`400` según la validación existente y un alias ya tomado, y la tabla
refresca la fila sin recargar la página.

## Tasks

| ID | Spec | Route | Commit |
| --- | --- | --- | --- |
| T1 | S4 | backend · `projects.delete` + blobs después del commit + auditoría + tests | `9aa876340` |
| T2 | S3, S6, S7 | backend · `projects.move_files`, `reactivate`, `PATCH /projects/{slug}` + tests | `9aa876340` |
| T3 | S2, S1 | web · `Menu` por proyecto + filtro de archivados + tipos y cliente API + tests | `e429e83c4` |
| T4 | S5 | web · `ProjectsPage` reconstruida (modal + tabla + filtro + acciones) + tests | `e429e83c4` |
| T5 | S5 | docs · enmienda `web/DESIGN_SYSTEM.md` (`### Proyectos`) | `e429e83c4` |

## Log

**L1 — pedido original del owner (2026-11-23), verbatim:**

> hey chat necesito que entres al vps. y revises las conversaciones con el asistente lumat. desde el usuario Stefan. ahi hay un proyecto llamado test del agente. necesito que revises lo que hemos testeado y los errores encontrados para seguir mejorando.
>
> por otra parte me di cuenta de un par de cosas:
>
> - cuando el asistente crea un nuevo documento, crea tambien una copia .bak que esat visible desde el archivos del proyecto. cuando el asistente crea un nuevo archivo esta bien que se pueda visualizar desde archivos del proyecto (/outputs), pero no es necesario que sean visibles los .bak ya que se empieza a duplicar muchas veces. [Image#1].
> - Cuando se crea un nuevo proyecto, este no es posible de eliminarse. se puede archivar pero sigue mostrandose en el worktree de proyectos. [Image#2],
> - [Image#3], aqui hay que agregar un boton mas que este al lado del boton nuevo chat de cada proyecto. en este boton mas se abrira un dropdown button con distintas alternativas. primero moveremos el contexto y archivos. ademas del eliminar button. para eliminar definitivamente el proyecto, si es necesario.
> - Cuando se crea un archivo pdf: 1. no se puede visualizar en el visualizador del panel. actualmente los archivos pdf creados por el asistente, al descargarlos estan corruptos no puedo abrirlos.
> - el administrar proyectos "/panel/app/projects" no tiene dise;o alguno esta completamente roto. tiene el formulario para un nuevo proyecto en la misma pagina, no es un modal que se abre al clickear un boton. los proyectos se muestran en la tabla. pero no tienen el CRUD en la tabla.
>
> ----
>
> Revisa el artifact que esta trabajando el asistente con todas la tools que ha testeado. necesitamos corregir las tools que estan fallando.

**L2 — decisiones del owner (2026-11-23), verbatim del cuestionario:**
- Mover: «Solo archivos y carpetas» — «Mueve: project_files + project_folders. Los hilos no se mueven.»
- Eliminar: «Borrado total, irreversible» — «DELETE definitivo. Confirmación escribiendo el slug/nombre. Aviso explícito: archivos e hilos se pierden.»
- Archivados: «Ocultos, con filtro en Administrar» — «Worktree: solo activos. Administrar proyectos: filtro Activos / Archivados / Todos.»
- Entrega: «Dos PRs: tools y después panel».

**L3 — estado de producción que motiva el corte (2026-11-23, solo lectura):** 4 proyectos, uno
archivado (`e2e-temporal-verif`, 0 hilos, 0 archivos) que hoy se lista igual que los activos en el
worktree; el panel no expone archivar, reactivar, mover ni eliminar (`web/src/api.ts` solo tiene
`listProjects`, `createProject`, `updateProjectConfig`); `POST /projects` crea y `PATCH
/projects/{slug}/config` edita configuración, pero no hay `DELETE` ni renombre. `project_aliases` y
`project_audit` referencian `projects.id` sin `ON DELETE CASCADE`, así que el borrado debe eliminarlos
explícitamente antes de la fila del proyecto.

**L4 — frontera de revisión (2026-11-23):** 452 líneas agregadas y 30 borradas en 10 archivos, en dos
commits: backend (`9aa876340`, camino de borrado + mover/reactivar/renombrar) y web + docs
(`e429e83c4`). El riesgo del corte está concentrado en `delete_project` y `deletion_impact`; el resto
es superficie de panel. La suite `full` corre en el cierre del corte.

**L5 — verificación independiente y tests añadidos (2026-11-23):** un `gentle-ai-verify` separado
sondeó el borrado contra una base aislada: completitud (13 dependientes en 0, sin huérfanos), owner
scope con dos proyectos del mismo slug, paridad byte a byte entre `deletion-impact` y lo borrado, orden
chunks→documentos, blobs solo tras commit y merge de carpetas homónimas. Veredicto: las seis reglas
pasan, los tests estaban incompletos. Se agregaron cuatro tests de esa lista (`ca8c51000`) y se actualizó
`tests/functional/test_api_projects.py`, que todavía esperaba 405 en `PATCH`/`DELETE` de un proyecto.

**Advisories aceptadas, no bloqueantes:** memorias con `owner_id NULL` bajo el mismo slug sobreviven y
no se cuentan (solo alcanzables por datos legados: `MEM-2` restringe la escritura a `default`); las
filas derivadas `memory_observations`/`memory_relations` se borran pero no se enumeran en el preview;
un `unlink` fallido después del commit reporta 500 sobre un borrado ya confirmado (semántica
preexistente de `remove_files_after_commit`); `move_files` no dedupe nombres de archivo homónimos en la
raíz del destino.

