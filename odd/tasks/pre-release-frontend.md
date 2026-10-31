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
la vista. El formato de burbujas debe ser el mismo que usan los chats del asistente Lumat: la gramática
`ai-agent-grammar__*` (`bubble-row`, `bubble-stack`, `bubble`, `message-meta`) de `AgentChat.tsx`.
La maqueta del owner (L11) precisa ese formato y **descarta** el avatar por mensaje de las dos
puntas: el hablante va como texto sólo arriba de las burbujas salientes, la hora pasa adentro de la
burbuja con un tilde de entregado, y cada día arranca con un separador centrado.
El panel de cliente deja de ser una columna: flota sobre el hilo (overlay) y se abre y cierra desde
un botón, que es lo que devuelve el ancho a la conversación.

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
| T2 | S3, S4 | inline + worker | `3a11def4`, `edb3501b`, `5e535ccb`, `b12c2307`, `14f1feaf`, `4fe96b32`, `43d8c6b3` | hecho |
| T3 | S5 | inline | ver L11 | hecho (ver delta en L11) |
| T4 | S1–S6 | inline | ver L9 | gate verde; PR pendiente de decisión del owner |

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

**L6 — barrido del resto del panel (2026-10-31).**
El worker convirtió 11 páginas (22 archivos, +172/−140): `AppointmentDetail`, `ClientFicha`,
`ClientesList`, `KbList`, `KbDocumentDetail`, `AutomationRecipesPage`, `ProjectSkills`,
`ProjectsPage`, `SelfProfile`, `UserFicha`, `UserManagement`. `ProjectAgents` no tenía feedback de
acción que convertir y así se reportó, sin inventar un cambio.
Quedaron fuera del barrido, a propósito y con razón: `ConversationThread` (lo toca S5),
`AgentChat`/`AssistantWorkspace` (su feedback es estado de stream y micro-feedback pegado al
control — "Subiendo archivo…", "Copiado", "Cancelado" —, no resultado de acción), y los errores
dentro de `Dialog`, que S4 mantiene inline.

**L7 — el rojo de ProjectsPage era un defecto del test, no del producto (2026-10-31).**
El único fallo del barrido fue `saves project instructions through the config endpoint`: la
toast de éxito no aparecía porque el mensaje real era el de error ("No pudimos guardar las
instrucciones."). Causa: el test mockeaba `fetch` por **secuencia** (`mockResolvedValueOnce`), y
`ProjectResources` también fetchea al montar, así que el PATCH recibía la respuesta de otro
request. El test viejo no lo detectaba porque su única aserción de resultado era el valor del
textarea, que sale del estado local y no de la respuesta: **el guardado llevaba fallando en ese
test sin que nadie lo viera**. Se corrigió mockeando por URL y método. Regla que deja: una
aserción de resultado tiene que mirar lo que produjo la llamada, no el estado que el usuario ya
tecleó.

**L8 — el gate mintió dos veces por un huérfano, no por código (2026-10-31).**
Dos corridas de `scripts/test.sh full` salieron con exit 1 y **cero** `FAILED`/`ERROR`. No era un
test flojo: `pytest-timeout` (120 s, `timeout_method = "thread"`) mata el proceso de pytest pero
**no** los subprocesos que el test lanzó. `tests/functional/test_seed_dev.py:42` corre
`seed_dev.py` con `subprocess.run`; cuando ese test expiró, el hijo sobrevivió `idle in
transaction` y bloqueó todos los `TRUNCATE` de `tests/functional/conftest.py:88`. La segunda
corrida moría en el primer test de base, no en el del seed.
Confirmado en `pg_stat_activity` (dos `TRUNCATE` en `active/Lock` y el culpable `idle in
transaction`), limpiado con `kill -9` del huérfano y `pg_terminate_backend`, y re-corrido sobre
base limpia: **exit 0, 0 fallos, 0 timeouts**. Corolario que queda: en este repo un `full` rojo
sin ningún `FAILED` es el harness bloqueado; re-correr sobre la base sucia repite el timeout.

**L9 — gate de cierre (2026-10-31).**
- Backend `full` sobre base limpia: `BACKEND_EXIT=0`, 0 `FAILED`, 0 `ERROR`, 0 timeouts.
- Frontend `npm test` sobre el árbol final: verde, 119 archivos / 1386 tests.
- `npm run build` (`tsc -b` + vite): verde.
- Slice 1: 3 tests nuevos de formato de audio + 18 tests de media existentes en verde.

**L10 — pendiente del owner (2026-10-31).**
T3 no arranca sin la captura o maqueta de la ventana de conversación (L2.2). El push de la rama y
la apertura del PR quedan como decisión del owner, como manda la política del repo.

**L11 — maqueta recibida y rediseño aplicado (2026-10-31).**
El owner entregó `LUMAT WhatsApp support chat with details.png`. Implementado en
`ConversationThread.tsx` + `ConversationThread.css`:
- **Header compacto**: una sola banda con volver, avatar, nombre, teléfono con punto verde, `#id`,
  pill de estado y acciones a la derecha, más un botón "Cliente". Desaparecieron la fila de
  identidad con "Iniciada el …", la fila de acciones y la banda "Historial de mensajes" con su
  frescura: las tres comían alto útil.
- **Panel de cliente como overlay**: `.conversation-workspace` pasa a una columna y los detalles
  flotan sobre el hilo con `--elevation-overlay`, abiertos por defecto y cerrados desde el botón.
  Bajo el breakpoint móvil el overlay y su botón se ocultan y sigue valiendo el sheet
  "Información del chat" del menú.
- **"Ver todos" arriba y fuera del scroller**: `CollapsibleMessages` envuelve ahora al área con
  scroll en lugar de vivir adentro. Antes el hilo abría en el último mensaje y el control quedaba
  fuera de la vista justo cuando hace falta.
- **Formato de burbujas**: sin avatares por mensaje, hablante sólo en las salientes, hora adentro
  de la burbuja, tilde de entregado en las salientes enviadas, y separador de día centrado al
  cambiar de fecha (`role="separator"`).
Se eliminaron `formatRecency` y `formatInitiatedDate` al quedar sin uso.

**Delta deliberado contra la maqueta** (para que el owner decida, no para que lo descubra después):
- El **composer** sigue como estaba (Adjuntar / Grabar audio en su fila propia). La maqueta lo
  muestra como una sola fila de íconos con emoji; el emoji no existe en ningún lado del panel y
  crearlo es una feature nueva, no un rediseño. Queda para después.
- La **lupa** del header y el **chevron flotante de scroll** de la maqueta no se implementaron: la
  búsqueda dentro del hilo no existe como función y el chevron duplica "Ver todos" en el caso corto.
- La maqueta muestra un **rail de tres íconos** (persona, portapapeles, info); sólo hay datos para
  el primero, así que el panel se abre desde un único botón en vez de inventar dos secciones vacías.

Nota de disciplina: los tres tests nuevos de esta capa (control sobre el scroller, overlay
abrible/cerrable, separador de día) se escribieron **después** de la implementación, no en RED
primero; los 4 tests existentes que rompió el cambio de formato se migraron a la conducta nueva.

**L12 — segunda vuelta sobre la maqueta, con el render real a la vista (2026-10-31).**
El owner mandó dos capturas del resultado y cuatro correcciones sobre el render, no sobre la
descripción:
1. **El alto no se usaba.** `.conversation-workspace` tenía `height: clamp(480px, 100dvh - 15rem,
   736px)`, un número fijo que dejaba una franja muerta abajo. Ahora la cadena
   `.conversation-thread-page` → `.page-frame__content` → `.conversation-workspace` es flex con
   `min-height: 0` y la tarjeta toma la altura que realmente queda.
2. **El espacio libre se lo llevaba el composer, no el hilo.** Defecto de mi propio slice 3: al
   eliminar la banda "Historial de mensajes", `.ai-agent-grammar__main` quedó con
   `grid-template-rows: auto minmax(0,1fr) auto` para dos hijos, así que la fila elástica era la
   segunda — el composer. Corregido a `minmax(0,1fr) auto` en esta página.
3. **Burbujas centradas.** La gramática compartida centra una columna de 52 rem
   (`.ai-agent-grammar__thread-area`); acá se anula el `max-width` y las burbujas van a las orillas
   de la tarjeta, que es como se lee un hilo de WhatsApp.
4. **Aviso de 24 h invasivo.** Era un bloque ámbar con título y subtítulo, repetido en las dos
   ramas del composer. Ahora es una línea fina (`conversation-thread__window-note`) con
   `aria-label` propio para no perder el nombre accesible. Se eliminó además el
   "Conversación cerrada" que se imprimía al pie: decía "cerrada" cuando en realidad era la ventana
   de 24 h, y ya lo dice el aviso.
El toggle de detalles salió del círculo flotante sobre el hilo (se veía fuera de lugar en la
captura) y pasó a ser un botón del header con `aria-pressed`.

**Respuesta a la consulta de GIF/stickers** (verificado en el código, no supuesto): el backend ya
modela `MessageType.STICKER` y `app/webhook/ingest.py:117` lo ingiere, y `image/gif` está en los
sufijos y en los tipos servidos inline. Un **GIF** que llegue como `image` se ve animado hoy mismo
con el `<img>` existente; si WhatsApp lo entrega como video MP4 —el caso típico— se ve como video
con controles, no en loop. Un **sticker** llega y se guarda, pero el panel no tiene rama de render:
cae al `default` de `MessageBubble` y aparece como link de descarga. Falta una rama `sticker` con
`<img>` (webp). Enviar stickers no es posible: la Cloud API sólo acepta stickers de un pack propio.

**L13 — el panel de cliente arranca colapsado (2026-10-31).**
Pedido del owner tras ver el render: "la información del cliente debe estar colapsada cuando se
abre una conversación". `detailOpen` pasa a `false` y un `useEffect` sobre `conversationId` lo vuelve
a colapsar al cambiar de conversación, para que no herede el panel abierto del cliente anterior.
Los cinco tests que asumían un inspector siempre visible (cuatro en `ConversationThread.test.tsx`,
uno en el story test) se migraron a: el panel **no** está al abrir, se abre con el botón y se
cierra con su cabecera.

