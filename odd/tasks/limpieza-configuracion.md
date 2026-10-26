# Limpieza de Configuración — clave muerta, defaults duplicados, opciones divergentes y push duplicado

Cierre de la deuda que quedó anotada (y deliberadamente no tocada) al cerrar el frente 3. El owner la
autorizó después de mergear los tres frentes: "merge y limpieza".

## Specs

- **S1** — "`chat.conduct.redaccion` se valida, se guarda y nadie la lee": la clave se elimina del contrato
  de settings (validación, defaults, borrador del panel y tipo del SPA). Un valor ya guardado en una base
  existente no puede romper la lectura ni impedir guardar el resto de `chat.conduct`.
- **S2** — "la copia de `MESSAGE_DEFAULTS` dentro de `SETTINGS_DEFAULTS` ya drifteó (omite
  `messages.smalltalk`)": los mensajes fijos tienen una sola fuente de verdad, y `messages.smalltalk`
  aparece con su default real en esa fuente.
- **S3** — "opciones duplicadas UI↔backend (tono, tarifa, días) que ya divergen entre sí": cada lista de
  opciones tiene una sola fuente. Tono y tarifa se resuelven contra la lista canónica del backend; los
  nombres de días de la semana dejan de estar copiados tres veces en el frontend.
- **S4** — "`PushSettings` montado dos veces (en la pestaña de horarios y como vista propia)": un solo
  montaje, y la vista `push` sigue siendo alcanzable desde donde hoy lo es.
- **S5** — comportamiento que se conserva: ningún texto fijo cambia de valor, ninguna opción válida
  desaparece, el guardado de cada tarjeta sigue igual y las vistas que hoy funcionan siguen funcionando.

## Fuera de alcance

Los 7 hallazgos `WARNING` no bloqueantes de la revisión nativa del frente 2 (`R1-001`, `R3-001..003`,
`R4-001..003`): la revisión sólo publicó ids, lente y `path:line`, no el texto de cada hallazgo, así que
actuar sobre ellos sería adivinar. Necesitan el texto de la revisión.

## Tasks

| ID | Spec | Route | Commit |
| --- | --- | --- | --- |
| T1 | S1 | worker (contrato + panel, tolerando datos legacy) | `102209bd`, `48226d06` |
| T2 | S2, S3 | worker (defaults de una fuente + opciones canónicas) | `8a2a1088`, `b86d6b2b`, `db09f3a4` |
| T3 | S4 | worker (un solo montaje de PushSettings) | `7a10b6da` |
| T4 | S1-S5 | inline (drift de fixtures + endurecido del panel) | `05d0f255`, `52b58c96` |
| T5 | S1-S5 | inline (evidencia) | este commit |

## Log

**L1 — pedido del owner (verbatim)**

> merge y limpieza

**L2 — deuda que este pedido cierra (verbatim del doc del frente 3, S5)**

> `chat.conduct.redaccion` (clave validada, guardada y nunca leída), la copia de `MESSAGE_DEFAULTS` dentro
> de `SETTINGS_DEFAULTS` que ya drifteó (omite `messages.smalltalk`), opciones duplicadas UI↔backend
> (tono, tarifa, días) que ya divergen, y el doble montaje de `PushSettings` (pestaña de horarios y vista
> propia).

**L3 — evidencia verificada (`path:line`), del inventario del frente 3**

- `app/services/settings.py:1057-1060` y `:1079` — `redaccion` se valida y se persiste.
  `grep redaccion app/` sólo devuelve `services/settings.py`; `agent/` no tiene ninguna coincidencia.
  `web/src/components/pages/Settings.tsx:144,170` lo mantienen en el borrador y `web/src/types.ts:552` lo
  tipa. `validate_conduct` lo exige en el payload (`:1050-1082`): quitarlo del SPA sin tocar el validador
  rompería el guardado.
- `app/services/settings.py:201-268` (`MESSAGE_DEFAULTS`) y `:437-446` (`SETTINGS_DEFAULTS`) — dos copias;
  el comentario en `:387-389` dice que la fuente son los nodos del chat, pero la copia omite
  `messages.smalltalk`, que sólo sobrevive por el fallback de `get_message` (`:831-834`).
- `app/services/settings.py:592` (`TONE_STYLES`) vs `Settings.tsx:710` (menú de tono hardcodeado);
  `app/services/settings.py:361-366` (`TARIFA_LABELS`) vs `Settings.tsx:37-42`; nombres de días en
  `Settings.tsx:31`, `web/src/components/primitives/DayToggle.tsx:3` y
  `web/src/components/shared/TechnicianScheduleEditor.tsx:9`.
- `web/src/components/pages/Settings.tsx:783` monta `<PushSettings embedded />` y
  `web/src/components/domain/AppShell.tsx:143` monta la vista `push` completa
  (`web/src/components/pages/PushSettings.tsx:17`).
- `web/src/components/pages/Settings.test.tsx:51` pinnea el array de secciones y `:512-515` el grupo de
  derivación de una sola opción: cualquier limpieza que toque esas tarjetas actualiza el contrato a
  propósito.

**L4 — verificación**

- **T1.** RED: 12 fallos en `tests/unit/test_chat_conduct.py` (default, validación y proyección con
  `redaccion`) y 3 en `tests/functional/test_api_conduct_settings.py` (el GET exponía la clave y el POST
  rechazaba un payload sin ella). GREEN: unit + funcional (11) + panel (38) + `tsc -b` + `quick`.
  Cubierto explícitamente: guardar sin `redaccion`, leer una base que todavía la tiene guardada, y que los
  otros campos de `chat.conduct` no cambian.
- **T2.** RED: `SETTINGS_DEFAULTS` sin `messages.smalltalk`, `KeyError: 'options'` en el funcional, 4 fallos
  de frontend. GREEN: unit (2) + funcional + 50 tests de frontend + `tsc -b` + `quick`.
- **T3.** RED: la sección de horarios no tenía link a la página de push. GREEN: 86 tests + `tsc -b`.
- **Rama actualizada con `main`** (que ya traía el reagrupado de Configuración) en `049a69e6`: merge
  textualmente limpio, re-verificado sobre el árbol mezclado (`quick`, funcional de conduct, `tsc -b`,
  44 tests de panel) — el caso de merge semántico que compila en cada rama y rompe combinado.
- **El `full` encontró cuatro cosas que los tests enfocados no podían ver:**
  1. **Un crash real:** el panel hacía `settingsOptions(data).tones` sin fallback, y `options` es un campo
     nuevo; como el SPA se despliega aparte de la API, un panel nuevo contra un backend viejo dejaba la
     página de Configuración **en blanco**. Corregido en `05d0f255`: el tipo lo declara opcional y el panel
     degrada al tono actual y a las claves crudas.
  2. Dos fixtures de stories con la forma vieja del payload (`mockData/settings.ts`, su lista de claves).
  3. Dos tests de `tests/functional/test_api_kb_settings.py`: el set exacto de claves del GET y un
     `_CONDUCT` que todavía mandaba `redaccion`; más un docstring de ruta que la seguía documentando.
  4. Dos stories de push que asertaban el montaje embebido eliminado en T3.
- **Cierre:** `scripts/test.sh shape origin/main` → exit 0 (sin shape surfaces) · `scripts/test.sh full`
  **verde (8m10s)** · `npm run build` (`tsc -b`) verde · `npm test` → **112 archivos, 1296 tests** verdes.
