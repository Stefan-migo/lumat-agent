# fixes-tools-testing

Corte backend del testing E2E del asistente Lumat (hilo 84, proyecto `test-del-agente`, producción
`v2026.11.14`). Corrige las cuatro tools que fallaron más la corrupción de PDF y la copia `.bak` visible.
Riesgo alto: toca la publicación de archivos de proyecto (item 3: contrato de `project_file.update`) y
la imagen de entrega (item 5: `odd/evals/*.json` en el build del api).

## Specs

**S1 — Ninguna copia `.bak` visible en Archivos del proyecto.**
Texto del owner, verbatim: «cuando el asistente crea un nuevo documento, crea tambien una copia .bak
que esat visible desde el archivos del proyecto. cuando el asistente crea un nuevo archivo esta bien
que se pueda visualizar desde archivos del proyecto (/outputs), pero no es necesario que sean visibles
los .bak ya que se empieza a duplicar muchas veces».
`project_file.update` sigue guardando los bytes anteriores en un artifact del mismo hilo (recuperable),
pero **nunca** lo publica en los archivos del proyecto: `list_project_files` / la carpeta `outputs`
no listan ningún archivo cuyo nombre termine en `.bak<ext>`. Se conserva el resto del contrato de
S-A (respaldo antes de sobrescribir, `changed: false` sin auditoría, fallo cerrado si el respaldo no se
puede guardar) y se enmienda `openspec/specs/assistant-tools/spec.md` en el mismo cambio.

**S2 — Un artifact `.pdf` no puede recibir contenido que no es un PDF.**
Texto del owner, verbatim: «Cuando se crea un archivo pdf: 1. no se puede visualizar en el visualizador
del panel. actualmente los archivos pdf creados por el asistente, al descargarlos estan corruptos no
puedo abrirlos».
`artifact.update` (y `artifact.save`) rechazan con `ToolValidationError` cualquier revisión cuyo
contenido no sea coherente con la extensión declarada por el artifact: para `.pdf` los bytes deben
empezar con `%PDF-`. El rechazo no escribe blob, no inserta revisión, no republica y deja intacta la
versión vigente. `artifact.pdf` sigue produciendo un PDF real servible por el visor.

**S3 — `view_image` resuelve adjuntos del hilo.**
Texto del owner, verbatim sobre el error observado en producción: `Tool execution failed: thread image
not found`, repetido cuatro veces con tres vías de carga distintas.
El contexto del turno expone **todos** los adjuntos del hilo —imágenes incluidas— con `id`, `filename`
y `kind`, de modo que `view_image(source="thread", id=<id>)` resuelve exactamente el adjunto del hilo.
Una imagen que además viaja inline al modelo no puede seguir siendo un `id` invisible para él.

**S4 — `conversations.search` busca en el texto de la conversación.**
Hallazgo del testing, verbatim: `conversations.search` «query "caldera" devuelve 0 filas aunque existen
conversaciones de caldera; no matchea por texto del summary».
La búsqueda matchea, sin distinguir mayúsculas: nombre del cliente, teléfono y **texto del summary** de
la conversación. La paginación, el orden y la forma de la respuesta no cambian, y una query que no
matchea nada sigue devolviendo cero filas.

**S5 — `chatbot.eval_regression` es utilizable en el entorno desplegado.**
Hallazgo del testing, verbatim: `baseline report 'baseline' is missing or unreadable: [Errno 2] No such
file or directory: '/app/odd/evals/conv-eval-baseline.json'`.
(a) El repositorio versiona **un** baseline de referencia —`odd/evals/conv-eval-baseline.json`, tag
`baseline`, derivado del run medido `rebaseline-2026-11-20` con una fila por escenario y sin los
transcripts de `evidence`/`observations`— porque `odd/evals/*.json` está en `.gitignore` y una imagen
construida desde un tag limpio nunca tendría ninguno; la imagen del api (raíz `Dockerfile` e
`infra/Dockerfile.api`) copia `odd/evals/`, así que el tag `baseline` corre en producción;
(b) cuando el tag pedido no existe, el error nombra el tag pedido y enumera los tags disponibles en el
directorio, para que el asistente corrija sin adivinar.

## Tasks

| ID | Spec | Route | Commit |
| --- | --- | --- | --- |
| T1 | S1 | backend · `_update_project_file` deja de publicar el `.bak` + openspec + tests | `a874ba2de` |
| T2 | S2 | backend · validación de formato por extensión en artifact save/update + tests | `fe97e4651` |
| T3 | S3 | backend · ids de adjuntos (incluidas imágenes) en el contexto del turno + tests | `8681482df` |
| T4 | S4 | backend · `list_conversations` matchea summary + tests | `5bc9b948e` |
| T5 | S5 | delivery · baseline `conv-eval-baseline.json` versionado, copiado en la imagen + error con tags disponibles + tests | this commit |

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

**L2 — decisiones del owner (2026-11-23):** dos PRs separados, tools primero y panel después; los
proyectos archivados se ocultan del worktree y se filtran en Administrar proyectos; mover mueve solo
archivos y carpetas; eliminar es borrado total irreversible con confirmación escribiendo el nombre;
se autoriza limpiar en producción los 3 archivos corruptos/duplicados del proyecto `test-del-agente`.

**L3 — evidencia recogida en producción (2026-11-23, solo lectura):**
- `project_files` ids 6 y 8 = `herramientas-probadas-hilo-84.bak.md` (dos filas, dos roots de artifact
  distintos, hilos 50 y 54) en la carpeta `outputs`; la copia buena es el file id 3.
- `project_files` id 11 = `reporte-cobertura-tools-hilo-84.pdf`, 3.507 B, `file type` = texto UTF-8;
  es la revisión v2 del artifact root 14 escrita por `artifact.update`, mientras la v1 (20.621 B) sí es
  un PDF 1.7 válido. El `content_type` de la fila sigue `application/pdf`.
- `assistant_attachments` 2 (hilo 54) y 4/5 (hilo 59) existen como imágenes; el modelo nunca recibió
  sus ids porque `prepare_attachment_context` hace `continue` en `kind == "image"`.
- `/app/odd` no existe en el contenedor del api: `odd/evals` nunca entra a la imagen.
- Mensajes 249-257 del hilo 54: cinco turnos repitiendo «No pude escribir en este turno: el harness me
  pidió responder solo con texto, sin emitir tools» con seis `read_project_file` paginados por turno.
  Es un defecto de planeación (gasta el presupuesto de pasos releyendo y nunca planea la escritura),
  fuera de este corte: va al informe como hallazgo abierto.

**L4 — frontera de revisión (2026-11-23):** el corte son 290 líneas agregadas y 26 borradas en 17
archivos. `odd/evals/conv-eval-baseline.json` es un dato versionado de 1.050 líneas que no pide lectura
línea a línea: 42 filas de escenario puntuadas, sin `evidence` ni `observations`, derivadas del run
medido del 2026-11-20.
**L5 — flake preexistente corregido (2026-11-23):** la suite `full` de la rama hermana falló en
`test_artifact_pdf_saves_and_publishes_idempotently` con `changed: False` esperado y `True` obtenido.
Repetido tres veces en este worktree: una falla y dos passes. Causa: WeasyPrint estampa fecha de
creación y document id en cada render, así que dos llamadas idénticas pueden diferir en bytes. El test
ahora fija el renderer en bytes estables (el contrato bajo prueba es el de la tool) y el `%PDF-` real
sigue cubierto por `tests/unit/test_assistant_pdf_reports.py`. Commit `5541fcc89`.

