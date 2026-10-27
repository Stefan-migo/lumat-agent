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

## Tasks

| ID | Specs | Ruta | Commit |
| --- | --- | --- | --- |
| T1 | S1 S2 S3 S4 | writer | `feat(settings): sistema visual y Agente con barra de guardado sticky` |
| T2 | S5 | writer | `feat(settings): persona con vista previa markdown y ampliar` |
| T3 | S6.1–S6.4 | writer | `feat(settings): conducta con tabla de datos y preguntas` |
| T4 | S6.5–S6.6 | writer | `feat(settings): conducta con editor de derivaciones y vista previa` |
| T5 | S7 | writer | `feat(settings): mensajes con buscador y vista previa en el editor` |
| T6 | S1–S7 | inline | verificación final: `npm run build` + `npm test` |

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
