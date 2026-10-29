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
`resetKey` por `threadId`) — verificar antes de reescribirlo.

S4 — Artefacto en el chat: el agente dice "descargable" pero no se puede descargar desde el chat, y
muestra la ruta completa. Debe ser un link corto y descargable.

S5 — Sidebar derecha completa (rediseño): sacar el borde de hover del toggle, separarlo del
subtítulo; reordenar secciones dejando "Capacidades del asistente" antes de "Fuentes del hilo" (que
se elimina, así que queda al final); "Recursos del proyecto" como versión reducida del árbol de
archivos + KB de la configuración, con upload por botón y por drag&drop, crear y eliminar carpetas;
"Archivos del hilo" y "Artefactos del hilo" con ícono más grande y apertura por click en la fila
(cursor mano + tooltip); arrastrar archivos del proyecto y del hilo al chat para incorporarlos al
contexto del turno (los de KB son solo lectura, no manipulables); skills solo lectura mostrando las
globales; "Capacidades del agente" con mejor UI.

## Tasks

T1 — DONE (`2f66b9e3`). Remove the "Fuentes del hilo" section and its dead assertions. S1. `web/src/components/pages/AssistantWorkspace.tsx`, `web/src/components/pages/AssistantWorkspace.test.tsx`.
T2 — DONE (`2f66b9e3`). Fix the thread project once the thread has messages. S2. `web/src/components/pages/AgentChat.tsx`, `web/src/components/pages/AssistantWorkspace.tsx`, both `*.test.tsx`.
T3 — Redesign and reposition "Ver todos" and check the stick-to-bottom baseline. S3.
T4 — Render a short, downloadable artifact link in the chat. S4.
T5 — Redesign the right sidebar. S5.

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
