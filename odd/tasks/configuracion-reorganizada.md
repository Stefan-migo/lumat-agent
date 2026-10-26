# Configuración — reorganizada en super-secciones y dueño único de `reply.texts`

Frente 3 de los tres frentes de frontend pedidos por el owner. Alcance: la sección Configuración del
panel (`/panel/app/settings`), que creció a 11 pestañas planas al sumar la configuración del chatbot.
Se reagrupa en super-secciones y se elimina el dueño duplicado de `reply.texts`.

## Specs

- **S1** — "el ultimo frente es la seccion configuracion. hubo una implementacion de mas configuracion.
  sobre todo del chatbot. por ende necesito reorganizar toda esa configuracion es mucho": las 11
  pestañas se agrupan en cuatro super-secciones — **Chatbot** (Agente, Persona, Conducta, Mensajes),
  **Operación** (Horarios y avisos, Cobertura, Tarifas), **Integraciones** (Capacidades, API key de
  modelos, Correo) y **Costos** (Costos) — con sub-pestañas verticales dentro de cada grupo.
- **S2** — "reorganizar es el camino. pero si hay duplicados necesitamos limpiarlo tambien": los ids de
  pestaña y sus etiquetas **no cambian** (el deep link `#schedule` que usa Agenda sigue funcionando), así
  que la reorganización es de estructura, no de nombres.
- **S3** — "Un solo dueño para reply.texts": las 25 claves de `reply.texts` se editan en **un solo lugar**,
  la pestaña Conducta ("todo en Conducta"), y la pestaña Mensajes deja de tener el bloque duplicado de
  "Respuestas del flujo". Un único botón de guardado, con guarda sobre todas las claves, para que nunca se
  pueda enviar un mapa a medias ni pisar ediciones sin guardar de otra pestaña.
- **S4** — comportamiento que se conserva: cada tarjeta mantiene su propio guardado y su nota, el
  historial de versiones (`persona`, `emergency`) sigue igual, la carga diferida de horarios de técnicos
  sigue disparándose al abrir su grupo, y las secciones siguen siendo alcanzables desde el menú móvil.
- **S5** — fuera de alcance (deuda anotada, no se toca): `chat.conduct.redaccion` (clave que se valida,
  se guarda y nadie lee), la copia de `MESSAGE_DEFAULTS` dentro de `SETTINGS_DEFAULTS` que ya drifteó,
  las opciones duplicadas UI↔backend (tono, tarifa, días) y el doble montaje de `PushSettings`.

## Tasks

| ID | Spec | Route | Commit |
| --- | --- | --- | --- |
| T1 | S1, S2, S4 | worker (Settings.tsx: super-secciones + sub-tabs verticales, ids intactos) | `f9c20cd2` |
| T2 | S3 | worker (dueño único de `reply.texts`) | `882bff2f` |
| T3 | S1-S4 | inline (gate frontend + evidencia) | este commit |

## Log

**L1 — pedido original del owner (verbatim)**

> - el ultimo frente es la seccion configuracion. hubo una implementacion de mas configuracion. sobre todo del chatbot. por ende  necesito reorganizar toda esa configuracion es mucho.

**L2 — decisiones del owner (verbatim)**

- Agrupación: "4 super-secciones con sub-tabs" — "Sub-tabs verticales dentro de cada grupo: Chatbot /
  Operación / Integraciones / Costos, manteniendo las 11 pestañas y sus ids."
- Duplicados: "Un solo dueño para reply.texts" — "Un único lugar para editar reply.texts (todo en
  Conducta), y la pestaña Mensajes deja de tener el bloque duplicado."

**L3 — diagnóstico verificado (`path:line`)**

- `web/src/components/pages/Settings.tsx:50-55` — `SECTIONS`: **11** pestañas, no 12.
- `Settings.tsx:616` — `Tabs` horizontal para secciones; `:717` — `Tabs` vertical para plantillas de
  mensaje: el patrón de sub-tabs verticales ya existe en el archivo.
- `Settings.tsx:615` + `Settings.test.tsx:130-137` — en móvil la lista de secciones es un `Menu`: hay dos
  superficies que mantener en paso.
- `Settings.tsx:420` + `AgendaPage.tsx:300` + `AgendaPage.test.tsx:85,99` — el único deep link es
  `#schedule`.
- `Settings.tsx:443` — la carga de técnicos depende de `activeSection !== "schedule"`: mover esa tarjeta
  sin tocar la guarda deja la tarjeta vacía sin request.
- `app/services/settings.py:900-927` — `validate_reply_texts` exige las **25** claves de
  `REPLY_TEXT_DEFAULTS` y rechaza claves desconocidas: por eso un guardado parcial necesita cambio de
  backend, y por eso el dueño único (que envía el mapa completo) no lo necesita.
- `Settings.tsx:706` (guarda sobre las 5 de derivación) vs `:773` (guarda sobre todo el borrador) —
  ambas pestañas postean `/settings/reply-texts` con el mapa completo: un botón podía pisar ediciones sin
  guardar de la otra pestaña. Es el defecto que S3 elimina.
- `web/src/components/pages/Settings.test.tsx:51` — array ordenado exacto de etiquetas; más ~35 clics por
  nombre y 26 `selectSection(...)` en `web/src/stories/pages/Settings.stories.test.tsx`: el contrato de
  estructura que T1 tiene que actualizar a propósito.
- `SettingsVersionHistory` acotado a `persona` | `emergency` (`app/panel/api/routes/settings.py:255-258`).

**L4 — verificación del frente 3**

- **T1.** RED: los dos asserts de estructura nuevos fallaban (la lista plana no coincidía con el
  esquema grupo/miembro y las 11 pestañas aparecían juntas). GREEN: `Settings.test.tsx` +
  `SettingsEmail.test.tsx` + `Settings.stories.test.tsx` → **75 tests**. `tsc -b` verde.
- **T2.** RED: 6 tests fallaban (el editor de flujo no estaba en Conducta, Mensajes todavía renderizaba
  "Respuestas del flujo", y las aserciones del save movido no encontraban la acción). GREEN: **76 tests** en
  los dos archivos de settings. `tsc -b` verde. La guarda nueva es una sola expresión sobre las 25 claves
  (`REPLY_TEXT_KEYS.every(...)`) y alimenta tanto el `disabled` del botón como el early-return del save.
- **Gate completo del frente:** `npm run build` (`tsc -b` + vite) verde; `npm test` → **111 archivos,
  1277 tests**, todos verdes. No hay cambios de backend en este frente, así que no aplica `scripts/test.sh`.
- **Diferencia de conteo con el frente 2** (1285 vs 1277): el frente 2 corría sobre una branch que ya
  incluía los tests del compositor multimedia; este worktree nace de `origin/main`. No se perdió cobertura.
- **Deuda anotada y no tocada (S5):** `chat.conduct.redaccion` (clave validada, guardada y nunca leída), la
  copia de `MESSAGE_DEFAULTS` dentro de `SETTINGS_DEFAULTS` que ya drifteó (omite `messages.smalltalk`),
  opciones duplicadas UI↔backend (tono, tarifa, días) que ya divergen, y el doble montaje de `PushSettings`
  (pestaña de horarios y vista propia).
