# panel-visual-alignment

Objective: redesign the project-detail tabs (Contexto, Agentes, Skills, Hilos) to match the owner's
reference images. Frontend only. Branch `odd/panel-visual-alignment`.
Delivery: ask-on-risk. Runner: `npm test` (vitest) + `npm run build` (tsc -b + vite build).

Scope lock: agents stay fixed system roles; no backend/contract changes. Hilos is wired to the
existing endpoint. No palette/token changes.

## Specs

S1 — Shared page chrome (refs 6-9).
The project-detail header adopts the reference shape: a leading folder icon tile, the project name as
the page title, the status badge beside the title, the purpose as subtitle, and `Abrir asistente` as
the primary action. No page-level breadcrumb: the shell top bar owns it. Reuse `PageFrame`/`PageHeader`;
any new slot is additive and must not change existing pages. Tab bar keeps its underline-active style.

S2 — Contexto tab (ref 6). Two-column layout.
Left card `Instrucciones del proyecto`: icon + title + subtitle `Define el contexto compartido por el
asistente.`; read-only `Nombre del proyecto` and `Propósito`; editable `Instrucciones del proyecto`
with placeholder `Describe cómo debe trabajar el asistente en este proyecto…`; helper `Estas
instrucciones forman parte del contexto del proyecto.`; footer action `Guardar cambios`.
Right column: `Archivos del proyecto` card — icon + title + count badge + `Subir archivo`; empty state
`Aún no hay archivos` / `Sube el primer documento de este proyecto.`; `Conocimiento del proyecto` card
— icon + title + count + `Subir archivo a la KB`; empty state `Sin documentos indexados` / `Los
archivos compatibles se indexan automáticamente.`; footer note `Los archivos del proyecto se comparten
como contexto; los adjuntos de un hilo permanecen en ese hilo.`
Behavior is already wired and must not change.

S3 — Agentes tab (ref 8).
Card `Agentes del proyecto` with subtitle `Roles disponibles para trabajar con el contexto del
proyecto.` Three role cards, each with a dark circular icon tile, name, role chip, and description:
- `Orquestador` · chip `Asistente del proyecto` · `Responde consultas y utiliza las herramientas
  disponibles según la solicitud.`
- `Verificador` · chip `Solo lectura` · `Contrasta criterios con evidencia y consulta herramientas de
  solo lectura.`
- `Explorador` · chip `Investigación` · `Investiga con las herramientas habilitadas para la
  delegación.`
Then `Última ejecución` card: subtitle `Estado registrado de la ejecución más reciente.`, status pill
(e.g. `Completada`) and timestamp. Read-only; agents remain fixed system roles.

S4 — Skills tab (ref 7).
Search field `Buscar habilidad por nombre o descripción…`. `Catálogo global` card with count badge +
`Habilidades globales de solo lectura.` and rows: icon tile, name, description, chips `Global` /
`Solo lectura`. `Habilidades del proyecto` card with count + `Agregar habilidad` action, dashed empty
state `Aún no hay habilidades en este proyecto` / `Agrega una habilidad para definir instrucciones
específicas.`, and a collapsible `Agregar habilidad` disclosure. Footer note `Las habilidades globales
se consultan; las del proyecto se gestionan aquí.` Existing add/edit/delete behavior preserved
(whole-array PATCH via `updateProjectConfig`).

S5 — Hilos tab, wired (ref 9).
Replace the hardcoded placeholder. List the project's chat threads via `GET
/panel/api/chat/threads?proyecto=<slug>`. When empty, show the reference empty-state visual (icon,
title, supporting copy, `Abrir historial` CTA, footer note). Assumption to confirm with the owner: the
empty-state copy reflects a real empty project (not "unavailable"), e.g. `Aún no hay hilos en este
proyecto`.

## Tasks

| ID | Spec | Route | Status | Evidence |
| --- | --- | --- | --- | --- |
| T1 shared chrome | S1 | inline | done | f194eef9 |
| T2 Contexto | S2 | inline | pending | — |
| T3 Agentes | S3 | inline | pending | — |
| T4 Skills | S4 | inline | pending | — |
| T5 Hilos wire | S5 | inline | pending | — |

## Log

L1 (owner, verbatim): "ok quiero trabajar en estos tres paneles. ... Estas tabs no han sido disea;adas
y algunas no estan conectadas. hay que redise;ar completamente estas secciones estas son las
referencias para el dise;o ... necesito que adaptemos lo que tenemos. entiendo que la seccion agentes
deberia dar la posibilidad de crear un agente? o modificarlo? no estoy seguro. lo mismo con skills.
deberia haber una forma de agregar skills?"
L2 (owner): "vamos solo frontend." → agents stay fixed roles; no backend.
L3 (owner): "si hilos si entra hay que cablearlo." → Hilos is in scope and wired.
L4: T1 done (f194eef9). Added an additive `titleIcon` slot to shared `PageFrame`/`PageHeader`
(optional, no existing page changed); project detail now renders the folder tile + status badge beside
the title, purpose as subtitle. `npm run build` green; full vitest suite green (1182 passed; the two
`ProjectsPage` header assertions were updated to the new structure).
