# Stickers en el hilo del panel

Pedido del owner, no un defecto del análisis: «para el frontend de conversaciones, los stickers deben
reproducirse tambien. la experiencia de la conversacion de whatsapp desde el panel. debe ser lo mas
cercano a la experiencia de whatsapp».

## Specs

**S1 · Un sticker se ve como un sticker.**
«los stickers deben reproducirse tambien»: hoy un mensaje `msg_type = "sticker"` cae en la rama por
defecto del hilo y se dibuja como un enlace de descarga. Tiene que verse como el sticker que el cliente
envió.

**S2 · La conversación del panel se parece a la de WhatsApp.**
«la experiencia de la conversacion de whatsapp desde el panel. debe ser lo mas cercano a la experiencia
de whatsapp». Un sticker de WhatsApp no lleva burbuja: va sin fondo, sin relleno y sin los metadatos de
un mensaje de texto encima. Esa es la diferencia visible entre un sticker y una imagen.

**S3 · Lo que no cambia.**
Texto, imagen, video, audio y documento siguen dibujándose como hoy. El backend no se toca: el sticker
de WhatsApp llega como `image/webp` y el endpoint de media ya lo sirve `inline`.

## Decisiones de diseño

- **D1 · Sólo frontend.** El backend ya guarda el sticker (`ingest._META_TYPE_TO_ENUM`), ya lo sirve
  inline (`image/webp` está en `_INLINE_MEDIA_TYPES`) y el serializador ya entrega `media_download_url`
  y `media_available`. No hay nada que arreglar en la API.
- **D2 · El estilo lo manda `web/DESIGN_SYSTEM.md`.** La superficie de conversación se gobierna por
  `DS-GRAMMAR-1`; el sticker es un caso de ese grammar, no un componente nuevo, así que no se agrega
  sección ni se inventan tokens.
- **D3 · Un sticker no disponible se dice, no se rompe.** `media_available === false` mantiene el aviso
  que ya existe ("Este archivo no está disponible"), en vez de una imagen rota.

## Tasks

| ID | Specs | Route | Commit |
|---|---|---|---|
| T1 | S1, S2, S3, D1-D3 | `web/src/components/pages/ConversationThread.tsx` + su CSS + tests | `feat(panel):` |

## Gate

El gate del panel no es el de siempre: `npm ci` → `npm run build` (`tsc -b`) → `npm test`. Un Vitest
verde no prueba que el árbol tipa, y `tsc -b` vive sólo dentro de `build`.

## Log

**L1 — pedido del owner (verbatim).**

```
lo otro. para el frontend de conversaciones, los stickers deben reproducirse tambien. la experiencia
de la conversacion de whatsapp desde el panel. debe ser lo mas cercano a la experiencia de whatsapp.
```
