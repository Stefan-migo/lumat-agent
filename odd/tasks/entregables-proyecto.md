# ODD — entregables-proyecto: PDF profesional y escritura acotada de archivos del proyecto

Worktree `../lumat-agent-odd-entregables-proyecto`, rama `odd/entregables-proyecto`, base `main` (`068f3810`).

Continúa `odd/tasks/artifact-outputs.md` (mergeada): un artifact del asistente ya se publica en `outputs/`
del proyecto. Falta lo que el owner pidió después: **reportes en PDF de calidad profesional** y la
capacidad de **escribir archivos de proyecto** (hoy todos los tools de archivos son de solo lectura:
`list_project_files`, `read_project_file`, `view_image`).

## Decisiones del owner (2026-11-06)

- Motor: **WeasyPrint**. Viabilidad medida antes de diseñar: `python:3.14-slim` + `libpango-1.0-0`,
  `libpangoft2-1.0-0`, `libharfbuzz-subset0`, `libfontconfig1`, `libgdk-pixbuf-2.0-0`, `shared-mime-info`,
  `fonts-dejavu-core` + `weasyprint` → `PDF_OK bytes=4964 head=b'%PDF-'`.
- Contenido: **spec estructurada + plantilla de la casa**, no HTML del modelo.
- Archivos de proyecto: **escritura acotada con aprobación** (`save` + `update`), sin borrar.

## Specs

**S1 — `artifact.pdf` genera un PDF real desde una spec estructurada.**
Args `extra="forbid"`: `filename` (debe terminar en `.pdf`; se sanitiza con el `safe_artifact_filename`
existente), `title` (1..200), `subtitle?` (≤300), `sections` (1..40) donde cada sección es
`heading` (1..200), `body?` (≤4.000 caracteres) y `table?` con `columns` (1..8) y `rows` (≤200, celdas
string ≤200). El modelo nunca entrega HTML, CSS ni rutas.

**S2 — El PDF es un artifact normal y se publica en `outputs/`.**
`content_type = application/pdf`, mismo hilo, misma cadena de revisiones y misma publicación que
`artifact.save`: `outputs/` es una carpeta normal del proyecto y `pdf` ya está en
`project_file_allowed_types`. Guardar bytes idénticos devuelve `changed: false` sin fila nueva.
`save_or_append` acepta `str | bytes`; un `str` se codifica en UTF-8.

**S3 — El render no sale a la red ni lee el disco. (riesgo ítem 2)**
`write_pdf(url_fetcher=...)` con un fetcher que **rechaza toda** URL (`http`, `https`, `file`, `data`,
relativa): un texto de usuario no puede convertirse en una petición saliente (SSRF) ni en la lectura de un
archivo del servidor. El HTML se arma con Jinja2 con `autoescape` obligatorio: el cuerpo es texto, nunca
markup. Estas dos condiciones son independientes: autoescape no impide que WeasyPrint busque
`<img src="http://…">` si el modelo pudiera inyectar HTML, y el fetcher no impide escapar mal un `<`.

**S4 — Los límites fallan cerrados.**
Una spec fuera de los bordes de S1 es `ToolValidationError` antes de renderizar. Un PDF mayor a
`assistant_artifact_max_bytes` usa el error de tamaño existente. Nunca se recorta texto en silencio.

**S5 — `project_file.save` crea un archivo de texto en el proyecto del hilo, con aprobación.**
Args `extra="forbid"`: `filename`, `content` (1..200.000), `folder?` (nombre de una carpeta existente en la
raíz del proyecto; ausente = raíz). Tipos permitidos: `.md`, `.txt`, `.csv` (`allowed_project_file`). El
proyecto se resuelve con la misma regla que la publicación (slug del hilo + owner). Un hilo `default` o sin
proyecto falla cerrado con un mensaje que lo explica, no con un no-op. `read_only=False`: la maquinaria de
aprobación existente lo pausa; no se agrega un gate nuevo.

**S6 — `project_file.update` reemplaza el contenido de un archivo de texto existente, con aprobación.**
`file_id` + `content`. Falla cerrado si el archivo no pertenece al proyecto del hilo, si el tipo no es de
texto, o si la fila tiene `source_artifact_root_id`: ese archivo lo publica un artifact y su fuente de
verdad es `artifact.update`; permitir dos escritores sobre el mismo contenido es cómo se desincronizan.
No crea fila nueva: misma fila, blob/size/sha256 nuevos, auditoría con el `sha256` anterior y el nuevo.

**S7 — El asistente no borra, mueve ni renombra archivos del proyecto.**
No hay `project_file.delete`, `.rename` ni `.move`. La superficie humana del panel ya los tiene
(`DELETE`/`PATCH` en `app/panel/api/routes/project_files.py`) y el agente no gana nada con poder
destructivo.

**S8 — `artifact.pdf` no reemplaza a `artifact.save`.**
`artifact.save` sigue produciendo texto; `artifact.update` sigue siendo la edición de un artifact de texto.
Un PDF no se edita: se regenera.

**S9 — Delivery: las libs de sistema están donde el código corre. (riesgo ítem 5)**
`pyproject.toml` declara `weasyprint`. Las libs de pango harfbuzz/fontconfig/gdk-pixbuf están en las tres
superficies donde el código se ejecuta, no solo en la del que probó: la etapa runtime del `Dockerfile` de
producción, el contenedor de desarrollo (`infra/Dockerfile.api` referenciado por `infra/docker-compose.yml`)
y el job `test` de `.github/workflows/tests.yml`. Un test que renderiza un PDF de verdad corre en CI: si
salta, la dependencia no está probada.

**S10 — La plantilla es una superficie de impresión, no una superficie del panel.**
El CSS vive en el template del render (A4, márgenes, numeración de página, encabezado con título y fecha,
tablas legibles, tipografía con fallback DejaVu). No reusa los tokens del panel y no entra en el contrato de
`web/DESIGN_SYSTEM.md`, que aplica a superficies web. Se declara para que nadie lo lea como deuda.

## Fuera de alcance

- Gráficos, imágenes y logos en el reporte (requiere resolver recursos, que S3 prohíbe).
- Editar o borrar archivos subidos por humanos desde el agente (S7).
- Carpetas creadas por el agente; `folder` solo referencia una existente.
- Envío del PDF por WhatsApp o email.

## Delivery

The branch exceeds the ~400 authored changed lines of a single review slice, so the boundary is declared
here as a chain. Push, PR creation and merge remain the owner's decision.

- **PR 1 — delivery and PDF** (`00f7983a`, `9e172fe4`): the dependency commit (`Risk: item 5`) opens the
chain, then the render and the tool (`Risk: item 2`). A reviewer can take the dependency alone before
reading any rendering code.
- **PR 2 — project file writes and the review repair** (`dbfc7a0c`, `dbc43e7a`): the two class-A file tools
(`Risk: item 1`, mitigated by the mandatory backup), and then what the independent review found — a dev
container that could not build, a dead CI cache, a page frame that vanished on a backslash title, and an
unbounded report spec. The repair sits at the head because it spans both surfaces.

## Tasks

- [x] **T1 — Delivery primero (riesgo ítem 5).** `pyproject.toml` + `Dockerfile` runtime +
      `infra/Dockerfile.api` + `infra/docker-compose.yml` + job `test` de CI. Commit propio: la feature no
      puede testearse sin esto y la revisión de dependencias no debe compartir commit con la lógica.
      *Check:* `uv sync` resuelve y un contenedor nuevo renderiza un PDF de prueba.
- [x] **T2 — Slice A RED.** Tests que fallan: la spec rechaza HTML y campos extra; los bordes de S1; el
      fetcher rechaza `http`, `https`, `file` y `data`; el HTML escapa `<script>` en un `body`; un render real
      produce bytes que empiezan con `%PDF-`; el tool guarda el artifact con `application/pdf` y lo publica en
      `outputs/`; un guardado idéntico devuelve `changed: false`.
- [x] **T3 — Slice A GREEN.** `app/services/reports.py` (render + fetcher + template Jinja2 con autoescape),
      `ArtifactPdfArgs`/`PdfSection`/`PdfTable` en el registry, `save_or_append` aceptando bytes,
      `artifact.pdf` en `agent/registry.yaml` y en `agent/personas/assistant.md`.
- [x] **T4 — Slice A spec + commit.** AT-17 en `openspec/specs/assistant-tools/spec.md`.
      `feat(assistant): render professional PDF reports from a structured spec`.
- [x] **T5 — Slice B RED.** Tests: `project_file.save` crea en la raíz y en una carpeta existente; rechaza
      un tipo no permitido y un hilo `default`; `project_file.update` reemplaza la misma fila con nuevo
      `sha256`; rechaza un archivo de otro proyecto, uno publicado por un artifact, y un tipo no textual;
      ambas escrituras requieren aprobación (no están en la allowlist autónoma) y dejan auditoría.
- [x] **T6 — Slice B GREEN + spec + commit.** `ProjectFileSaveArgs`/`ProjectFileUpdateArgs`, handlers,
      `agent/registry.yaml`, persona, AT-18/AT-19. `feat(assistant): let the agent save and update text files
      in its project` (commit remains owner-owned).
- [ ] **T7 — Cierre.** `scripts/test.sh full` (la rama toca shapes: `agent/registry.yaml`, prompts, persona,
      `app/models.py` no, pero `agent/*` sí), `scripts/test.sh shape origin/main`, verificación independiente
      del diff completo (ítems 2 y 5), y entrega en cadena como la feature anterior.

## Log

**L1 — pedido del owner (verbatim).**

> ok pregunta si ahora los artifacts creados por el aistente se van a ver tambien en el worktree de archivos
> del proyectos. el asistente deberia tener herramientas para modificar los archivos del proyecto? al menos
> los markdown y el agente debe tener capacidad de crear tambien pdf para entregar reportes peofesionales en
> pdf

**L2 — estado medido al abrir la feature.** Los artifacts ya se ven en los archivos del proyecto: la
publicación crea una fila normal de `project_files` dentro de la carpeta `outputs`, y la superficie del panel
(`GET /panel/api/projects/{slug}/files|folders`, `GET .../files/{id}/download`) lista cualquier fila. Tools de
archivo actuales: `list_project_files`, `read_project_file`, `view_image` — **todos read-only**. `pdf` ya
está en `project_file_allowed_types`; las dependencias actuales son `pypdf`/`pdfplumber` (lectura), sin motor
de generación.

**L3 — decisiones del owner.** WeasyPrint; spec estructurada con plantilla de la casa; escritura acotada con
aprobación (`save` + `update`, sin borrar).

**L4 — viabilidad medida antes de diseñar.** `docker run python:3.14-slim` + las libs de S9 + `weasyprint` →
`PDF_OK bytes=4964 head=b'%PDF-'`. Sin esa medición la decisión del motor era una suposición.

**L5 — costo de delivery medido.** Tres superficies instalan dependencias del sistema y hoy solo el
`Dockerfile` de producción lo hace (con `ffmpeg`): el contenedor de desarrollo usa la imagen `uv` pelada con
`uv sync` adentro y el job `test` de CI instala `ffmpeg` con presupuesto de tiempo guardado. S9 las cubre por
eso y no por prolijidad.

**L6 — clasificación de escritura y dos correcciones del 2026-11-06.**

**`artifact.pdf` es autónoma, no gateada.** Queda en `AUTONOMOUS_WRITE_ALLOWLIST` junto a
`artifact.save`, `artifact.update` y `artifact.delete`. La razón es la misma de `artifact-outputs` S12: un
artifact vive en el hilo del owner, con el mismo owner y el mismo almacenamiento, y la publicación en
`outputs/` es la consecuencia declarada de esa autorización, no una escritura de clase A distinta. Gatear un
PDF mientras `artifact.save` no lo está sería incoherente y le pondría un prompt de aprobación al pedido más
común. El alcance gateado de esta feature son los **archivos de proyecto** (`project_file.save` /
`.update`, S5-S6): esa sí es una escritura nueva sobre contenido arbitrario del proyecto.

Corrección de proceso: la instrucción que le di al writer decía lo contrario ("must NOT appear in an
autonomous-write allowlist"). El writer **frenó en vez de obedecer** y señaló la contradicción; tenía razón.
Un writer que no convierte una instrucción equivocada del orquestador en código es el comportamiento
correcto.

**Defecto medido en el fetcher de recursos.** `HTML(string=..., url_fetcher=_reject_url)` tiene el binding
correcto (en WeasyPrint 70 `url_fetcher` es parámetro de `HTML.__init__`; pasarlo a `write_pdf` lo tragaría
`**options` y el control quedaría inerte en silencio). Pero con una función pelada, WeasyPrint busca
`_fail_on_errors` en el fetcher en su camino de error y el render **aborta** con
`AttributeError: 'function' object has no attribute '_fail_on_errors'`. Medido: un objeto con
`_fail_on_errors = False` hace que el render **termine** (`bytes=2505 head=b'%PDF-'`), descarte el recurso e
igualmente invoque el fetcher con la URL. Se cambia a esa forma: bloquear un recurso degrada el reporte, no
lo rompe.

**Evidencia de que el control existe y se usa** (sonda propia, antes de aceptar el reporte del writer):
`url_fetcher` se invoca con `http://example.com/x.png` y el render no hace ninguna petición.

**L7 — Slice B implemented in worktree, pending owner commit.** RED was observed because `project_file.save` / `project_file.update` did not exist; focused integration and quick checks passed GREEN. Both tools remain class-A and outside the autonomous allowlist. The panel only moves project files, so `project_file.update` introduced a new destructive capability. The owner chose that any text file may be updated only after its previous bytes are backed up in a same-thread artifact published under `outputs/`; if backup storage fails, the update is refused. Implemented the `.bak` artifact, fail-closed behavior, and backup ID in the result and audit.

**Command evidence:** RED — `bash scripts/test.sh db tests/integration/test_assistant_project_file_writes.py` failed on the missing backup ID and missing refusal; GREEN — the same command passed (7 tests). `bash scripts/test.sh quick` passed (100%).

**L8 — verifier corrections.** The independent verifier found the dev Compose Dockerfile path resolved outside the repository root, an outdated evidence-size fixture, a title-ending-backslash that broke the PDF page frame, a CI apt cache path that differed from the guarded script, missing-blob updates surfacing as 500s, and no aggregate PDF content bound. Fixed those delivery/test/rendering/handler defects here and added regression coverage. Known limits: update writes the replacement blob before the database row flushes, so a failed flush leaves bytes recoverable from the `.bak` artifact; a `.bak` name reuses an existing thread artifact with that name; and a project file whose backup exceeds the 5 MB artifact cap cannot be updated (fails closed).

**L9 — evidencia de cierre técnico (2026-11-09).**

- `bash scripts/test.sh full` sobre el branch → **EXIT=0**, 7m11s.
- `origin/main` mergeado al branch (`c2a8a64c`, merge limpio). Trajo 30 archivos y 1368 inserciones de
  otra feature en vuelo, incluida `db/migrations/064_conversation_turn_count.sql`; sin colisión con este
  trabajo, que no agrega migraciones.
- `bash scripts/test.sh full` sobre el árbol combinado → **EXIT=0**, 9m39s. Obligatorio por `AGENTS.md`
  (después de mergear `origin/main`) y porque el árbol que se mergearía no era el testeado.
- `bash scripts/test.sh shape origin/main` → exit 3 (`agent/personas/assistant.md`, `agent/registry.yaml`).
- Cuatro commits, worktree limpio: `00f7983a` delivery (`Risk: item 5`), `9e172fe4` render y tool
  (`Risk: item 2`), `dbfc7a0c` escritura de archivos con respaldo (`Risk: item 1`), `7c7fbb8c` la
  reparación del verificador.

**Verificación independiente: qué encontró y qué se hizo.** Bloqueante real: el contenedor de desarrollo
no podía construir (`context: ..` + `dockerfile: Dockerfile.api`, con el archivo en `infra/`), probado con
`docker compose build --print`, no leyendo. Defectos reales: el caché de debs de CI apuntaba a un
directorio que el script ya no usa; el marco de página del PDF desaparecía con un título terminado en `\`
porque el texto del usuario estaba dentro de un string CSS; el spec no tenía tope agregado (13 MB de HTML
admisibles antes de que el límite de artifact lo rechazara); un blob ausente salía como 500. Regresión de
capacidad medida por mí: el turno de 4 pasos necesita 4.675 caracteres de evidencia y el techo era 4.500,
así que el paso del dashboard se expulsaba; el techo quedó en 5.500 con la medición en el comentario.

**Límites declarados, no defectos abiertos.** `project_file.update` escribe el blob antes de que su fila
haga flush (los bytes son recuperables desde el `.bak`); un `.bak` reusa un artifact del hilo con ese
nombre si existe; un archivo cuyo respaldo supera el tope de 5 MB de artifact no se puede actualizar (falla
cerrado); el payload de `assistant.capabilities` puede consumir hasta 4.000 caracteres del presupuesto de
evidencia, así que cada tool nueva que engorde el catálogo acerca el techo al borde.

**Entrega pendiente de autorización del owner.** Este trabajo no se publicó: la autorización de la feature
anterior no se hereda.
