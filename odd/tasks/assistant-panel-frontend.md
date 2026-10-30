# ODD — Assistant panel frontend (Lumat)

Feature: the Asistente Lumat frontend work the owner asked for, starting from the harness handoff
of 2026-10-29. Worktree `../lumat-agent-odd-assistant-panel-frontend`, branch
`odd/assistant-panel-frontend`.

## Specs

S1 — "Fuentes del hilo": eliminarla. Es código muerto: `AssistantWorkspace.tsx:703` tiene `count={0}`
hardcodeado y un texto fijo ("El hilo no entrega fuentes asociadas a sus respuestas"). Nunca se
pobló. Si algún día las citas son entregable, vuelve con datos reales (los chunks de KB y las URLs
de `web.search`/`web.fetch` ya viajan en `evidence`).

S2 — Selector de Proyecto de la sidebar: bloquearlo cuando el hilo ya arrancó. Hoy solo se
deshabilita mientras corre un turno (`state={isRunActive ? "disabled" : "default"}`). El owner
confirmó: sin mensajes = selector (reusar el del chatbox); con el primer mensaje = fijo.

S3 — Botón "Ver todos" del chat principal: rediseñarlo y reposicionarlo (al owner no le gusta el
diseño ni el borde de hover), y la conversación debe mantenerse siempre en el último mensaje salvo
que el usuario scrollee arriba. Ojo: `useStickToBottom` ya existe y ya tiene ese comportamiento (con
`resetKey` por `threadId`) — verificar antes de reescribirlo. Owner's choice on 2026-10-29, verbatim:
"Fila arriba del primer mensaje".

S4 — Artefacto en el chat: el agente dice "descargable" pero no se puede descargar desde el chat, y
muestra la ruta completa. Debe ser un link corto y descargable.

S5 — Sidebar derecha completa (rediseño): sacar el borde de hover del toggle, separarlo del
subtítulo; reordenar secciones dejando "Capacidades del asistente" antes de "Fuentes del hilo" (que
se elimina, así que queda al final); "Archivos del hilo" y "Artefactos del hilo" con ícono más
grande y apertura por click en la fila (cursor mano + tooltip); skills solo lectura mostrando las
globales; "Capacidades del agente" con mejor UI.

S6 — "Recursos del proyecto" en el sidebar, per the owner on 2026-10-29 (verbatim): "los archivos
del proyecto debe ser completo. crear carpetas, subir archivos, tambie poder agregar archivos
arrastrando a worktree de archivos de proyecto.  los checkboxes se eliminan. en cambio vamos a
permitir que estos archivos sean arrastables y que se puedan agregar manualmente al chat del hilo.
si el usuario quiere referenciar estos archivos. seria casi completo. lo de la kb puede quedar como
solo lectura en el sidebar menu. y que se peuda configurar solo desde configuracion". So: the full
project file tree (folders, upload, dropping files onto the tree), the thread checkboxes removed in
favour of dragging files into the chat, and the project KB read-only in the sidebar, configured only
from Configuración.

S7 — Delivery, per the owner on 2026-10-29: four slices, and publication deferred until the whole
assistant frontend is done ("esto lo dejaremos para despues. cuando ya este listo le frontendo del
asistente"). Work stays on `odd/assistant-panel-frontend` as separate slices; push, PR and merge
happen once the frontend is complete, not slice by slice.

## Tasks

T1 — DONE (`2f66b9e3`). Remove the "Fuentes del hilo" section and its dead assertions. S1. `web/src/components/pages/AssistantWorkspace.tsx`, `web/src/components/pages/AssistantWorkspace.test.tsx`.
T2 — DONE (`2f66b9e3`). Fix the thread project once the thread has messages. S2. `web/src/components/pages/AgentChat.tsx`, `web/src/components/pages/AssistantWorkspace.tsx`, both `*.test.tsx`.
T3 — DONE (`87305e9a`). Short, downloadable artifact link inside the agent message. S4. `web/src/components/pages/AgentChat.tsx`, `web/src/components/pages/AgentChat.test.tsx`.
T4 — DONE. "Ver todos" as a quiet line above the first visible message. S3. `web/src/components/shared/CollapsibleMessages.tsx`.
T5 — DONE (`b6f204c7`). Slice 2: sidebar shell — the toggle separated from the subtitle with no hover border, section order, capabilities UI. S5.
T6 — DONE (`42daabf9`). Slice 3: thread files and artifacts open from the whole row, larger icon, pointer cursor and tooltip. S5.
T7 — DONE (`e2f3a004`, `9ee3a35f`). Slice 4: full project resources — folder tree with upload and drop, KB read-only, files draggable into the chat, skills read-only, thread checkboxes removed, and the chat accepts the dropped project file. S6.
T8 — Slice 1 PR: the chat work (T3 + T4) together. S7.

Slice boundary: 684 authored lines over 10 commits. The ~400-line review slice is past, and per L10 the
boundary is recorded here instead of opening a PR: slices land as commits and the PR opens when the
assistant frontend is complete.

## Log

L1 — Owner request that opened this thread (verbatim):
"Continuamos el hilo del asistente Lumat. Leé primero .rapsodia-code/handoffs/2026-10-29-harness-asistente-cierre.md y después mem_get_observation con id 6971 (project lumat-agent). Producción está en v2026.10.12 (24b60d77), deployada y verificada. Lo que queda: (1) habilitar web.search/web.fetch en el hilo del panel, (2) el frontend del asistente, que es lo grande, (3) el camino de alertas por mail. Antes de tocar el frontend, pedime las capturas de nuevo: las del hilo anterior murieron con /tmp."

L2 — P1 verified as already done, not pending: project `test-del-agente` carries `web.search` and
`web.fetch` in `tool_policy.opt_in_enabled`, every production thread inherits it, and a read-only
probe in production returned `web.search ok rows=1` and `web.fetch ok`.

L3 — Owner authorized starting T1 and T2 before the screenshots arrive, and authorized the worktree
(`rapso worktree create assistant-panel-frontend --yes`).

L4 — Owner on P3 (verbatim): "aqui habiamos quedado en utilizar resend pero nunca lo temrinamos de
configurar". So the email path is Resend as the relay; the missing pieces are the owner's Resend API
key and the verified sending domain.

L5 — Spec source note: S1–S5 quote the owner's decisions as the previous thread recorded them in
`.rapsodia-code/handoffs/2026-10-29-harness-asistente-cierre.md` §2 P2. Reading correction: the
project selector S2 refers to is the composer popover in `AgentChat.tsx`, not a control in the left
sidebar.

L6 — T2 reading correction, measured in the code, not assumed: the composer project popover is only
rendered while `messages.length === 0` (`activeConversation`), so it already disappears with the
first message and needed no change. The controls that still changed the project with messages were
the mobile header picker and the "Cambiar" action of the thread detail sheet. T2 therefore threads a
`threadStarted` flag from `AgentChat` into `AssistantWorkspace` and disables both from the first
message, which is what S2 asks for. The existing test that changes the project on a message-less
thread stays green, so the pre-first-message behaviour is pinned.

L7 — T4 interpretation: the disclosure line counts the messages it hides (`total - previewCount`),
not the thread total, because "26 mensajes anteriores" while ten are visible would be false. The
component is shared with the WhatsApp thread page, so its copy changed there too and both existing
tests were updated; the collapse/expand behaviour itself is unchanged.

L8 — The owner supplied the nine screenshots the previous thread lost with `/tmp`; all of them record
the current state, not a design.

L9 — Owner decisions on 2026-10-29 that rewrote S3 and S5 and added S6–S7 (verbatim): "ok en este
caso. los archivos del proyecto debe ser completo. crear carpetas, subir archivos, tambie poder
agregar archivos arrastrando a worktree de archivos de proyecto.  los checkboxes se eliminan. en
cambio vamos a permitir que estos archivos sean arrastables y que se puedan agregar manualmente al
chat del hilo. si el usuario quiere referenciar estos archivos. seria casi completo. lo de la kb
puede quedar como solo lectura en el sidebar menu. y que se peuda configurar solo desde
configuracion". Chosen options: "Fila arriba del primer mensaje" for S3 and "Slices encadenados (4
PRs)" for S7.

L10 — Owner on publication, verbatim: "esto lo dejaremos para despues. cuando ya este listo le
frontendo del asistente". So S7 no longer means one PR per slice: the slices land as
commits on `odd/assistant-panel-frontend` and the PR opens when the assistant frontend is
complete. P3 (Resend) stays parked for the same reason.

L11 — The full-suite gate for slice 2 reported 22 failures across 7 files (UserManagement, Settings, ClientesList, AppShell, AgendaPage, ClientFicha, AppointmentDetail) with 17-29 s per test, while `npm run build` stayed green. The machine was saturated at the time — load average 62/72 and a `pytest` process from another worktree plus three test containers. The four affected files I re-ran in isolation (AppShell, AgendaPage, ClientFicha, ClientesList) passed 187/187. Not a regression, but the full suite must be re-run under a quiet machine before the frontend is declared complete.

L12 — Slice 4 closed. The thread "pin" checkboxes and their component are gone because the owner replaced pinning with dragging a file into the chat (L9); the chat now accepts the `application/x-lumat-project-file` payload and attaches the project file to the thread. The test that pinned the old `PUT /resources` behaviour was removed with it, and the new panel tests assert there are no checkboxes left.
