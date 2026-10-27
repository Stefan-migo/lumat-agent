# Rediseño visual de la sección Configuración (Chatbot)

Estado: entregado en 5 slices encadenados, pendiente de merge. Worktree `../lumat-agent-odd-configuracion-diseno`.
PRs apilados: #691 (S1–S4 + Agente), #692 (Persona), #693 (tabla de datos), #694 (derivaciones),
#696 (Mensajes).
Referencias: `refs/Diseño Lumat/Configuracion/redesign-2026-10-27/01-agente.png`, `02-persona.png`,
`03-conducta.png`, `04-mensajes.png`, `05-operacion-horarios.png` (ignoradas por git).
Análisis previo (2026-10-08, referencia anterior): `odd/analysis/configuracion/findings.md`, `visual.md`.

## Specs

### S1 — Chrome de la sección

1. La página mantiene `PageFrame` con título `Configuración` y meta `Preferencias globales del asistente`.
2. El título lleva la barra de acento lima (`--lime-700`) a la izquierda, como en las cinco referencias.
3. La barra superior conserva el breadcrumb existente y agrega a la derecha un botón `Historial`
   (icono reloj) que abre el historial de versiones de la sección activa:
   `persona` en la sección Persona, `emergency` en la sección Agente. En las demás secciones el botón
   no se renderiza, porque el backend solo expone esos dos scopes. El historial deja de mostrarse
   dentro de las tarjetas.
4. Las cuatro super-secciones (`Chatbot`, `Operación`, `Integraciones`, `Costos`) siguen siendo tabs
   horizontales subrayadas; la sección activa de la lista vertical se marca con una barra de acento
   lima a la izquierda, además del fondo `--surface-subtle` que ya existe.
5. Los selectores de super-sección y de sección para tablet/mobile se mantienen (`.settings-tabs__select`).

### S2 — Barra sticky de guardado (modelo híbrido)

1. Al pie de la página hay una barra sticky visible en todas las secciones, con dos estados de texto:
   - con cambios pendientes: `Cambios sin guardar` (punto ámbar);
   - sin cambios pendientes: `Sin cambios pendientes` (check verde).
2. Pendiente = alguna clave de borrador de la sección activa difiere de la última versión guardada
   (`baseline`). El cálculo usa la comparación profunda existente (`sameValue`).
3. `Guardar cambios` ejecuta, en orden, **los endpoints por tarjeta que ya existen** para cada clave
   pendiente de la sección activa. No hay endpoint nuevo ni guardado por super-sección.
4. Si algún valor pendiente es inválido, no se envía ninguna petición y se mantiene el mensaje de
   validación actual (`Sintaxis no válida` y su detalle).
5. `Descartar` restaura las claves de la sección activa desde `baseline` y no llama al backend.
6. `Guardar cambios` se deshabilita cuando no hay pendientes o cuando hay un guardado en curso.
   `Descartar` se habilita solo con pendientes.
7. Los botones `Guardar …` por tarjeta desaparecen; el guardado por tarjeta sigue disponible para
   las claves que no son de borrador (API key de modelos, correo), que mantienen su propia tarjeta.

### S3 — Patrón de tarjeta

1. `Card` mantiene icono, título y descripción; el icono se renderiza como chip cuadrado con fondo
   suave (`.card__icon` cuadrado, no círculo).
2. La ayuda contextual deja de ser una columna lateral `HelpPanel`: cada tarjeta que hoy la tiene
   muestra un botón `?` a la derecha del header, que abre la misma copia en un `Popover`
   (`HelpPanel` dentro del popover, sin columna en el layout).
3. Los badges de estado (`Original` / `Personalizado` / `Personalizada`) se mantienen y quedan a la
   izquierda del `?`.
4. La tarjeta del Agente muestra una fila `Configuración avanzada` (patrón disclosure) que contiene la
   sintaxis avanzada de las reglas de alcance.
5. No se agregan props obligatorias a `Card`: el `?` se compone con `headerAction`. Los estilos nuevos
   viven en `Settings.css` bajo clases `settings-*`; `primitives.css` solo recibe el ajuste del chip
   de icono.

### S4 — Agente (`01-agente.png`)

1. `Alcance del agente`: cuando no hay reglas, se muestra el estado vacío con el texto
   `No hay reglas personalizadas` y `Agrega categorías o revisa la configuración avanzada.`, más el
   botón `+ Agregar regla`. Ese botón abre la fila `Configuración avanzada`, que es donde hoy se
   editan las reglas (`categoria=modo`); no se inventa un catálogo de categorías que el backend no
   expone. Con reglas cargadas se listan como filas `categoría` + badge de modo
   (`bot_resolve` / `always_escalate`) en vez del estado vacío.
2. `Detección de emergencias`: las palabras se editan como chips removibles (`×`), con el input
   `Escribe una frase y presiona Enter` y el botón `Agregar`. Se agrega al presionar Enter o el
   botón y se quita con `×`. El ayudante es
   `Usa expresiones claras para evitar activaciones innecesarias.` y la banda informativa
   `La detección se evalúa antes de generar la respuesta.`
3. El payload de `keywords` no cambia: sigue siendo la lista de strings que ya consume
   `/panel/api/settings/keywords`.
4. `Protocolo de emergencia`: `Instrucciones de seguridad` y `Contactos de emergencia` en dos columnas,
   `Mensaje al notificar` a ancho completo, con el ayudante `Se envía cuando se notifica al equipo.`
   El badge `Original` / `Personalizado` se mantiene.

### S5 — Persona (`02-persona.png`)

1. `Persona del asistente` muestra un control segmentado `Vista previa` / `Editar Markdown` y un botón
   `Ampliar`.
2. `Vista previa` renderiza el Markdown del borrador con `react-markdown` + `remark-gfm` (ya son
   dependencias), en modo solo lectura y con scroll interno.
3. `Editar Markdown` muestra el textarea existente con la misma validación.
4. `Ampliar` abre un `Dialog` a pantalla completa con el mismo Markdown renderizado.
5. Se mantiene la banda informativa: `Los datos del cliente se agregan automáticamente. No incluyas
   variables como {{nombre}}.`
6. `Instrucción de brevedad` queda como tarjeta propia, con el texto descriptivo actual.

### S6 — Conducta (`03-conducta.png`)

1. `Datos y preguntas` reemplaza las tarjetas `Conducta de la conversación` y `Preguntas de captura`
   por una sola tabla: `#`, `Campo`, `Pregunta al cliente`, con acciones por fila de subir, bajar y
   quitar (menú kebab `⋯`).
2. La tabla lee el orden de captura (`conduct.orden`) y el texto de cada pregunta
   (`capture_questions.questions`), y escribe en ambos borradores: reordenar marca `conduct`
   pendiente, editar un texto marca `captureQuestions` pendiente.
3. La banda informativa repite las dos reglas vigentes: los datos de contacto se solicitan después de
   la disponibilidad y un dato quitado deja de preguntarse.
4. El pie `Preguntas por mensaje` usa un stepper `−` / valor / `+` sobre `max_preguntas_por_mensaje`,
   con el ayudante `Los textos se envían tal como están escritos.`
5. `Derivaciones y respuestas` reemplaza las tarjetas `Derivaciones` y los acordeones de textos por un
   editor de dos columnas: buscador `Buscar situación`, lista con los cinco casos de derivación y los
   grupos `Agendar`, `Gestionar una visita`, `Derivar a una persona`, `Captura` con su conteo, y panel
   de detalle con:
   - `Cuándo se envía` (el texto `when` o el título del grupo);
   - el toggle `Derivar al equipo` para los cinco casos, enlazado a `conduct.derivaciones`;
   - `Mensaje al cliente` con el textarea del scope `replyTexts`;
   - `Insertar dato` con los slots disponibles de esa clave, que insertan `{{slot}}`;
   - `Vista previa` con `Datos de ejemplo`, que reemplaza los slots por valores de ejemplo.
6. Los textos de los cinco casos siguen siendo las primeras entradas de la lista; el resto queda
   agrupado por acordeón como hoy.

### S7 — Mensajes (`04-mensajes.png`)

1. `Tono del asistente` queda como fila: descripción + selector de tono a la derecha.
2. `Mensajes del asistente` muestra el badge con la cantidad (`11 mensajes`), un buscador
   `Buscar mensaje`, la lista de plantillas, el editor con `Cuándo se envía`, `Texto del mensaje` y la
   `Vista previa en WhatsApp` (badge `Ilustrativa`) dentro del panel del editor.
3. Cada mensaje de `messages` se marca con el badge `Mensaje fijo`, porque se envía tal cual.
4. `Respuestas prediseñadas` mantiene su tarjeta con el botón `+ Agregar respuesta`, el estado vacío
   `Aún no hay respuestas prediseñadas` / `Crea una plantilla para una consulta frecuente.` y la banda
   `Si falta un dato necesario, el bot responde normalmente.`
5. La sección Operación (`05-operacion-horarios.png`) queda fuera de esta entrega por decisión del
   owner; se trabaja después sobre el mismo sistema visual.

### S8 — Owner visual follow-up (2026-10-27)

1. Persona: “todo el "header" del card persona del asistente debe mejorar el layout, el original tiene el elayout roto, el boton ampliar no esta en el contenedor de los botones vista previa y editar. el estilo de los Botones Vista previa y Editar MD, no estan correctos mejorar. color del banner con el texto "Los datos del cliente se agregan automáticamente. No incluyas variables como
{{nombre}}."”
2. Conducta: “podriamos meter los casos de derivacion en un dropdown menu tambien. para que sigan todos la misma logica?” Presentation only: preserve specific cases and generic response as separate groups, use the existing accordion, initially expanded.
3. Mensajes: “el actual muestra mucha informacion es un card de 3 o 4 lineas por mensaje del asistente. en la referencia es solo una linea. todo se explica en el panel derecho.” “el panel derecho esta bien. pero se podria mejorar la version de la vista previa. para crear algo mas estilo whtasapp como lo hace la ref.”

## Tasks

| ID | Specs | Ruta | Commit |
| --- | --- | --- | --- |
| T1 | S1 S2 S3 S4 | writer | `feat(settings): sistema visual y Agente con barra de guardado sticky` |
| T2 | S5 | writer | `feat(settings): persona con vista previa markdown y ampliar` |
| T3 | S6.1–S6.4 | writer | `feat(settings): conducta con tabla de datos y preguntas` |
| T4 | S6.5–S6.6 | writer | `feat(settings): conducta con editor de derivaciones y vista previa` |
| T5 | S7 | writer | `feat(settings): mensajes con buscador y vista previa en el editor` |
| T6 | S1–S7 | inline | verificación final: `npm run build` + `npm test` |

| T7 | S8.1 | inline, done | `96b08129`; Persona follow-up; PR #692 slice |
| T8 | S8.2 | inline, done | `e594b824`; Derivations follow-up; PR #694 slice |
| T9 | S8.3 | inline, done | `bac3ca37`; Messages follow-up; PR #696 slice |
| T10 | S8 | inline, done | L16–L17: build, 93 focused tests, 1310 full-suite tests, browser and pushes |

## Log

- L1 (owner, verbatim): «'/home/stefan/Downloads/Agente setting with robot icon.png' '/home/stefan/Downloads/LUMAT Persona Settings with Markdown Preview.png' '/home/stefan/Downloads/LUMAT chatbot behavior settings.png' '/home/stefan/Downloads/LUMAT assistant messages editor.png' '/home/stefan/Downloads/LUMAT schedules, hours, and alerts.png' \n\nok estos son los dise;os que seguiremos para mejorar el estilo de la seccion de configuracion»
- L2 (owner, decisiones): alcance = Chatbot completo (4 pantallas), Operación después; guardado =
  barra sticky que reenvía los endpoints por tarjeta (híbrido); flujo = worktree + doc ODD + PR por
  slice.
- L3 (orquestador, exploración): la estructura de super-secciones, tabs y endpoints ya existe; el
  cambio es visual, de composición y de estado de guardado. El análisis previo
  `odd/analysis/configuracion/findings.md` sigue siendo válido como inventario, pero varias filas
  (`configuracion-016` HelpPanel, `018` MessagePreview, `021` header action) ya están resueltas.
- L4 (desvío registrado en S4.1): el botón `+ Agregar regla` de la referencia abre `Configuración
  avanzada` en vez de crear una fila con selector de categoría, porque el backend no expone un
  catálogo de categorías de alcance.
- L5 (orquestador, re-secuenciación): S4 se implementa junto a S1–S3 en T1, porque el sistema
  visual (barra sticky y tarjetas con `?`) solo se puede probar de punta a punta sobre una sección
  migrada. Los slices restantes quedan como S5, S6 y S7, uno por pantalla.
- L6 (orquestador, re-secuenciación 2): S6 se entrega en dos slices —la tabla `Datos y preguntas`
  (S6.1–S6.4) y el editor `Derivaciones y respuestas` (S6.5–S6.6)— porque juntos pasaban de 400
  líneas en un solo commit y mezclaban dos concerns revisables por separado.
- L7 (orquestador, cierre): las cuatro pantallas del Chatbot quedaron migradas y verificadas
  (`npm run build` + `npm test` → 1308 pruebas en 112 archivos). Queda pendiente de decisión del
  owner el merge de la pila y, después, Operación/Horarios con el mismo sistema visual.
- L8 (owner, revisión del resultado real en el 5175): «los tab del side bar menu son muy anchos,
  quitan espacio para la informacion principal. hay que reducir el widht de todo el side bar menu con
  los tabs "agente, persona, conducta, mensajes"». El menú vertical pasa de `minmax(12rem, 0.8fr)` a
  `minmax(10rem, 13rem)` con `gap: var(--space-5)`, y el ayudante del protocolo deja de montarse sobre
  el textarea (el margen negativo heredado de la versión de una columna). El arreglo vive en la rama
  base (#691) y se propaga a las ramas apiladas con merges ascendentes, sin reescribir historia.
- L9 (owner, segunda ronda visual): cuatro defectos concretos sobre el resultado real del 5175.
  1. **Doble línea verde en el título.** No era una regla global duplicada: dos páginas dibujaban su
     propio acento encima del `::before` global de `.page-header__copy` (`Settings.css` en T1 y
     `AutomationRecipesPage.css`, el caso que el owner ya había visto en Automatizaciones). Se
     eliminaron ambas; el acento queda con una sola fuente.
  2. **Historial.** Se mantiene (la referencia lo muestra y el historial de versiones es real) pero se
     rediseña como acción fantasma: sin borde, verde de marca, `--text-sm`, superficie al hacer hover.
  3. **Faltaban los iconos del menú de secciones.** Cada sección declara su icono en `GROUPS` y el
     primitive `Tabs` ya lo renderizaba; los iconos quedan en `--corp-fg-muted` y toman `--corp-text`
     en el ítem activo.
  4. **El popover de ayuda rompía el diseño.** Duplicaba el título (`Popover` + `HelpPanel`) y se
     anclaba a la izquierda, saliéndose del viewport. Ahora el popover muestra un solo título y las
     dos frases, y se ancla al borde derecho (`.popover__panel { inset: auto 0 auto auto }`).
  Además, en las tarjetas de Agente: chip de icono de 44px con `--success-bg`, padding `--space-5`,
  título semibold, estado vacío centrado con icono, fila `Configuración avanzada` con `</>` y chevron
  que rota, fila de palabras clave en un único control bordeado con el botón `Agregar` dentro, y la
  etiqueta `Palabras y frases de activación` sobre los chips. El ayudante del protocolo ya no se
  monta sobre el textarea porque las columnas ahora son grid con `gap`.
- L10 (owner, tercera ronda visual): la tarjeta `Detección de emergencias` todavía se leía "más
  cruda" que la referencia. Los chips pasan a ser pastillas rellenas en `--bg`, sin borde, con la `×`
  como botón silencioso (sin cromo, gris y con hover) dentro de **un solo campo bordeado** que también
  contiene la fila de alta; el alta usa `placeholder` + `aria-label` en vez de una etiqueta visible
  (como en la referencia y como ya hace `SearchInput`); y la banda informativa deja el `--info-tint`
  azul por el tono sage de la página con texto e icono en `--corp-fg-muted`.

- L11 (owner, verbatim):

```text
ok bastante mejor:

tab persona:

- actual /tmp/gpUBFQIP/pi-clipboard-a27b7d60-f5b8-4022-9925-74ce2d602085.png, referencia, /tmp/gpUBFQIP/pi-clipboard-30f2dfdb-e3c6-4900-adc4-6ad4e8dd3de6.png. varias cosas aun no estan alineadas:
todo el "header" del card persona del asistente debe mejorar el layout, el original tiene el elayout roto, el boton ampliar no esta en el contenedor de los botones vista previa y editar. el estilo de los Botones Vista previa y Editar MD, no estan correctos mejorar. color del banner con el texto "Los datos del cliente se agregan automáticamente. No incluyas variables como
{{nombre}}."


tab conducta:

en el card Derivaciones y respuestas /tmp/gpUBFQIP/pi-clipboard-b0811087-97f6-4b48-9f46-e29c9188e343.png actual, primero hay un apartado "Casos de derivacion" y luego abajo hay un dropdown button con "Derivar a una persona". podriamos unificar? estamos mezclando cosas si es asi? podriamos meter los casos de derivacion en un dropdown menu tambien. para que sigan todos la misma logica?

Tab Mensajes:

- actual /tmp/gpUBFQIP/pi-clipboard-f3c06adb-5265-4a3f-a0af-ae0d3207d29b.png, referencia : /tmp/gpUBFQIP/pi-clipboard-1d984066-cc1c-49a4-a8af-fc092ace245f.png.

ok aqui principalmente es la barra lateral con los mensajes reducidos. el actual muestra mucha informacion es un card de 3 o 4 lineas por mensaje del asistente. en la referencia es solo una linea. todo se explica en el panel derecho.

el panel derecho esta bien. pero se podria mejorar la version de la vista previa. para crear algo mas estilo whtasapp como lo hace la ref. /tmp/gpUBFQIP/pi-clipboard-415a5973-77a1-45fe-af25-a84b21d0e000.png
```
- L12 (execution plan): follow the existing stacked-PR boundaries (#692, #694, #696), never one accumulated main-range slice. Local CSS only; no primitive/token/API changes. Graph consulted: Settings(), Settings.tsx, previewTemplate(), Settings.test.tsx; Settings community; path queries returned ambiguous/no directed paths (not evidence of independence). Existing report lists model/fixture god nodes; none touched. Graph refresh remains session-close only.

- L13 (T7 evidence): RED missing toolbar, GREEN 4 Persona tests; browser 1440/390px, same-row controls, edited draft in preview/dialog, no mobile overflow. Pure styling validated visually (no meaningful unit RED for colors). Native assess medium, reviewDue=false. Risk: none; local-only selectors.

- L14 (T8 evidence): RED missing accordion trigger; GREEN collapse/reopen, independent generic/specific text and preserved draft. Browser Enter/Space/search/count passed. Derivation editor fits 390px; whole-page mobile overflow check failed (scrollWidth 620px), originating in unchanged capture table and its visually-hidden label. Not fixed as part of this request. Assessment unavailable because temporary browser script was untracked; script removed. Risk: none, uses existing local accordion without API changes.

- L15 (T9 evidence): RED sidebar repeated 12 fixed-message badges vs required one in detail; GREEN compact list/search/draft unit test. Browser all 11 rows 36px/nowrap, drafts preserved, multiline preview uses pre-wrap. Browser mobile RED two columns (late S7 desktop CSS overwrote earlier mobile rule); GREEN one column, detail visible at 390px, no horizontal overflow at 900/390px. WhatsApp visual checked in screenshots; test harness maps production logo URL to existing public asset for Storybook. Graph: Settings.tsx imports MessagePreview(), which imports Avatar(); shared components left unchanged. Risk: none, local selectors only.

- L16 (final functional gates): npm ci exit 0; first npm run build exit 1 (new test used unsupported Testing Library ByRoleOptions.exact), removed option; corrected npm run build exit 0 (tsc -b + Vite, chunk-size warning); focused Settings + stories 93/93, exit 0; npm test 1310/1310 across 112 files, exit 0 (117.94s). Native assessment medium, reviewDue=false; no native review started. npm ci reports 11 vulnerabilities (4 moderate, 3 high, 4 critical); dependency remediation is outside this visual scope, lockfile unchanged. Delivery pending normal pushes of #692/#693/#694/#696.

- L17 (delivery evidence): all normal pushes succeeded (job-18, exit 0): #692 `96b08129`, #693 `2c400288` (merge), #694 `e594b824`, #696 `bac3ca37`. Changes propagated upward only, no rebase/force-push/main merge. T7–T10 complete; this documentation-only commit records final hashes and checks. Remaining unrelated observations: existing capture-table mobile overflow and dependency audit warnings.
