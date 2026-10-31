# pre-release-frontend

Tres unidades antes del release `2026.10.14`: el envío de audio de la ventana de conversación,
la generalización de los toasts de acción y el rediseño de la ventana de conversación.
Rama `odd/pre-release-frontend`, worktree `../lumat-agent-odd-pre-release-frontend`, base `main` `a54dc9f5`.

## Specs

**S1 — El audio se puede enviar desde la ventana de conversación.**
Hoy el operador no puede enviar un audio desde `/conversations/#`. Recibir audio, recibir imagen,
enviar imagen y enviar documentos ya funcionan y deben seguir funcionando (regresión prohibida).
Criterio observable: con un navegador que graba `audio/webm;codecs=opus` (Chromium en Linux), el
botón "Grabar audio" está habilitado, la grabación se envía, y el mensaje sale con
`delivery_status: sent`.

**S2 — El audio sale en un formato que Meta acepta.**
Meta acepta `audio/aac`, `audio/amr`, `audio/mpeg`, `audio/mp4` y `audio/ogg` (sólo codec Opus);
no acepta `audio/webm`. Decisión del owner: el navegador graba lo que sepa grabar y el api
normaliza a `audio/ogg;codecs=opus` con `ffmpeg -c:a copy` (remux, sin re-encode, sin pérdida).
`ffmpeg` pasa a ser dependencia de la imagen del api. Firefox (`audio/ogg;codecs=opus`) y Safari
(`audio/mp4`) siguen funcionando sin cambio de comportamiento.

**S3 — Todo feedback de acción del usuario es un toast en la esquina inferior derecha.**
El primitivo existe (`ToastProvider`/`useToast` en `web/src/components/primitives/Toast.tsx`,
anclado abajo a la derecha) y hoy sólo lo usan `AppShell`, `ProjectThreads` y `ProjectResources`.
Toda confirmación o error de una acción del usuario —guardar, eliminar, enviar, validar una clave—
debe usar ese toast, en Configuración y en el resto del sistema. No debe quedar ningún mensaje de
acción en banner, en `StateMessage` de página ni en un `<p role="status">` inline.

**S4 — Alcance del barrido: sólo acciones del usuario.**
Decisión del owner: quedan como están los estados de la página (cargando, sin permiso, falló la
carga inicial), que son persistentes y no deben desaparecer solos a los 5s; la validación de un
campo o de sintaxis, que queda al lado del campo; y la confirmación destructiva, que sigue siendo
`Dialog`. `ConversationThread`, `AgentChat` y `AssistantWorkspace` quedan fuera de este barrido:
los toca el rediseño de S5 y barrerlos antes obliga a reescribir las mismas líneas.
Dos precisiones que salen de esta misma regla (L4): el error de una acción se queda **inline dentro
del `Dialog` que la origina** —un toast se renderiza detrás del modal y el operador está
corrigiendo ese formulario— y el micro-feedback pegado a un control ("Copiado", "Guardando…",
bottón deshabilitado) tampoco es un toast: es el estado del control, no el resultado de la acción.

**S5 — La conversación tiene más protagonismo y usa el formato del chat del asistente.**
La ventana de conversación con el cliente debe dar más ancho y foco al hilo; el control para cargar
la conversación completa (`CollapsibleMessages`, "N mensajes anteriores · Ver todos") debe quedar
fijo arriba, fuera del área con scroll, porque hoy arranca pegado al último mensaje y queda fuera de
la vista. El formato de burbujas debe ser el mismo que usan los chats del asistente Lumat
(`ai-agent-grammar__*` en `AgentChat.tsx`: avatar en ambos lados, `bubble-stack`, `message-meta`).
Referencia visual: captura o maqueta del owner (pendiente, ver L2).

**S6 — Entrega.**
Un worktree (`odd/pre-release-frontend`), un PR contra `main`, tres slices como commits-unidad con
sus pruebas y docs. El release queda después y fuera de este cambio.
El PR supera las 400 líneas autoradas: es la consecuencia de juntar tres unidades en un mismo
release, que es lo que el owner eligió (L2.4). Los commits quedan separados por unidad para que el
review se pueda leer por partes; si el review se vuelve inmanejable, se corta en PRs encadenados
por slice sin reescribir el trabajo.

## Tasks

| ID | Specs | Route | Commit | Estado |
|----|-------|-------|--------|--------|
| T1 | S1, S2 | inline | `3b83f31e` (api) + `3b58ef72` | hecho |
| T2 | S3, S4 | inline + worker | `3a11def4` (Configuración), `edb3501b` (Agenda), worker en curso | en curso |
| T3 | S5 | worker (tras la captura) | — | bloqueada por L2 |
| T4 | S1–S6 | inline | — | pendiente |

## Log

**L1 — pedido del owner (verbatim).**
> lo primero es hacer un analisis de todos los toasts del, sistema sobre todos los que aparecen en la pagina configuracion. para que todos los toast sean un pop up que se muestra en la esquina infrerior derecha. ya esta creado ese toast para algunos casos. pero tiene que generalizarse para todos los toasts del sistema.
>
> Lo otro es mejorar la pagina /conversations/#.
>
> donde se puede ver la conversacion. hay un bug donde no se puede enviar un audio. se puede recibir el audio, se puede recibir imagen, pero no se puede enviar el audio. la imagen y los documentos se envian correctamente.
>
> despues necesitamos mejorar el dise;o de la ventana de conversacion con el cliente. hay que darle mas protagonismo a la conversacion. el boton ver mas (para cagar la conversacion completa) debe esetar arriba y cambiar el format utilizar el mismo formato que se usa en los chats del asistente lumat.

**L2 — decisiones del owner (2026-10-31).**
1. Audio: `ffmpeg` en el api; el navegador graba webm y el backend remuxea a ogg/opus.
2. Rediseño: el owner manda captura o maqueta antes de codear. T3 no arranca sin ella.
3. Toasts: sólo acciones del usuario (S4).
4. Entrega: un worktree, un PR, tres slices (S6).

**L3 — evidencia de diagnóstico (2026-10-31).**
La lista fija `["audio/ogg;codecs=opus", "audio/mp4", "audio/aac"]` de
`ConversationThread.tsx:182-184` no interseca lo que soporta Chromium en Linux
(`audio/webm;codecs=opus`), así que `supportedRecordingMime` queda `null` y el botón nace
deshabilitado. `ConversationThread.composer.test.tsx:61` mockea `MediaRecorder.isTypeSupported`
devolviendo exactamente los mimeTypes de esa lista, por eso el test pasa y el navegador real no.
El backend ya sacaba el `caption` de los audios (`app/services/send.py:91`); el defecto es de
formato y de detección, no de entrega.

**L4 — inventario de toasts y refinamiento de S4 (2026-10-31).**
El primitivo `ToastProvider`/`useToast` existe y está montado en `app.tsx`, anclado abajo a la
derecha. Lo usaban sólo 3 archivos (`AppShell`, `ProjectThreads`, `ProjectResources`). En
Configuración había cuatro mecanismos distintos y ninguno era el toast: el banner de `PageFrame`
(`saved`/`saving`/`server-error`), `modelApiKeyFeedback`, `emailFeedback` y los `StateMessage` de
carga de sección. El resto del panel repite el mismo patrón con estados locales propios.

Refinamiento explícito de S4, para que la regla no se aplique a ciegas:
- **Queda inline** el error de una acción cuando se muestra **dentro del `Dialog`** que la origina:
  un toast se renderiza detrás del modal y el operador está corrigiendo ese formulario. Aplica a
  cancelar/reprogramar/cerrar visita en `AgendaPage`, a los diálogos de `ClientFicha` y a los de
  `shared/`.
- **Queda inline** el micro-feedback pegado a un control ("Copiado", "Guardando…", botón
  deshabilitado): no es un resultado, es el estado del control.
- **Pasa a toast** toda confirmación o error de acción que hoy ocupa una banda de la página, un
  `StateMessage` de resultado, o un badge de fila que informa el resultado de una acción.

**L5 — primer intento de barrido delegado (2026-10-31).**
Un `gentle-ai-worker` en background recibió el barrido de 13 páginas y devolvió **cero cambios**:
la máquina estaba en load 42–72 (`packagekitd` y `gnome-software` comiendo CPU) y tomó los timeouts
del baseline por rojo propio; `ClientesList` pasó sola al reintentar. También señaló que
`ProjectResourcesPanel.test.tsx` no existe en el repo (error de mi brief). Conclusión operativa: en
esta máquina hay que medir el baseline antes de delegar y nunca creer un rojo de frontend sin mirar
`uptime`. Configuración se hizo inline y quedó verde (102 tests en los tres archivos de Settings).
