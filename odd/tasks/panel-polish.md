# panel-polish — frontend order and message-audio design

Feature branch `odd/panel-polish` (worktree `../lumat-agent-odd-panel-polish`). Scope: conversation
thread header layout (desktop + mobile) and the audio message design inside the bubble.
Authority: `web/DESIGN_SYSTEM.md` (Conversaciones, Button, Accessibility), `web/src/tokens/tokens.css`.

## Specs

**S1 — Desktop header order.** The conversation header must place the three-dot menu (`...`) last:
`Tomar conversación`, `Detalles del cliente` (the info control), `Cliente`, then `...`.
Source: "en la version desktop, necesitamos cambiar el orden dejando los 3 puntos (boton ...) al final".

**S2 — Mobile header order and chat information.** On mobile the buttons are reordered as well and the
standalone info control is not offered, because it does nothing there (the details panel is hidden
below the mobile breakpoint). The chat information must be reachable only through the `...` menu, as
the item `Información del chat`, which opens the existing sheet dialog.
Source: "en la version mobile. tambien hay que reordenar los botones. en este caso el boton informacion
no esta funcional. en mobiles hay que abrir el boton mas (...) y recien ahi esta la informacion del chat."

**S3 — Audio message design.** An audio message inside the thread bubble must render a designed player
instead of the browser's native `<audio controls>` widget: play/pause control, seekable progress,
elapsed and total time, readable on both bubble tones (inbound light, outbound dark), keyboard
operable, with Spanish accessible names. The native player currently shows a white pill reading
`0:00 / 0:00` over the bubble and a redundant `Audio adjunto` label.
Source: "hay que mejorar la burbuja del chat, para mostrar el audio. actualmente se ve asi. hay que
mejorar el dise;o."

## Tasks

| ID | Spec | Route | Commit |
|---|---|---|---|
| T1 | S1, S2 | inline — header layout + mobile menu wiring | `feat(panel): reorder conversation header actions and move chat info into the mobile menu` |
| T2 | S3 | inline — new message audio player + tests | `feat(panel): render audio messages with a designed player` |

## Log

**L1 (owner, original request, verbatim)**

> ok primero que todo quiero mejorar el orden de esto: [Image#1], tanto en la version desktop como en la versio mobile.
>
> en la version desktop, necesitamos cambiar el orden dejando los 3 puntos (boton ...) al final
> [Image#2] en la version mobile. tambien hay que reordenar los botones. en este caso el boton informacion no esta funcional. en mobiles hay que abrir el boton mas (...) y recien ahi esta la informacion del chat.
>
> ---
>
> hay que mejorar la burbuja del chat, para mostrar el audio. [Image#3] actualmente se ve asi. hay que mejorar el dise;o.
>
> ---
>
> eso por ahora

Image evidence read from the three attached screenshots (desktop header `Tomar conversación · ... · i ·
Cliente`; mobile header `Cerrada · ... · i · Cliente`; audio bubble `Audio adjunto` + native white
player `0:00 / 0:00` with `02:51` under it).
