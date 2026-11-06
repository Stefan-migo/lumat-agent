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
| T1 | S1, S2 | inline — header layout + mobile menu wiring | `1e5cbc95` |
| T2 | S3 | inline — new message audio player + tests | `ce9ec6c6` (player), `4e8e48d8` (thread wiring + story) |

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

**L2 (evidence, T1 + T2 done)**

- Browser measurement on the isolated stack (`localhost:5173` → api `:8002`), conversation #1:
  desktop visible controls in DOM order `Volver · Tomar conversación · Detalles del cliente · Cliente ·
  Acciones de la conversación` (dots last); mobile `Volver · Cliente · Más acciones de la
  conversación` with menu items `Información del chat · Tomar conversación · Devolver al agente ·
  Cerrar conversación`.
- The 1280 px header wraps to two rows with this conversation's data, but the same measurement on the
  pre-change code with the same rows gives 100 px against 92 px now: the wrap is pre-existing (long
  `Atención humana` badge plus the phone), not a regression of this change.
- Voice-note player measured in both tones with a real 7 s file: inbound grey track with a green
  thumb, outbound mint track inside the dark bubble, total reads `0:07` from `loadedmetadata`.
- Gate: `npm run build` (tsc -b + vite build) OK; `npx vitest run` 1405 tests / 121 files green.
- Slice boundary: 460 authored lines across the three commits, past the ~400-line slice. Everything
  below belongs to the next batch of owner items and needs its own review slice.
