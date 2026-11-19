# saludo-informal — el saludo que WhatsApp escribe con letras repetidas

Corte sobre `main` @ `ec584056e` (PR #845 mergeada). Rama `odd/saludo-informal`,
worktree `../lumat-agent-odd-saludo-informal`.

Origen: conversación de producción #40 con el cliente #3 (`+56934029170`), el
2026-11-18 21:42 UTC, bajo `v2026.11.10` (imagen construida 15:54 UTC). Dos
inbound (`Holaa`, `Cómo estás?`) separados por 1,7 s, un solo turno, y una
respuesta incoherente que terminó en humano.

## Specs

### S1 · Un saludo con letras repetidas sigue siendo un saludo

El vocabulario del saludo se compara por **forma reducida** (toda corrida de una
letra repetida cuenta como una): `Holaa`, `holaaa`, `buenaaas`, `Holaaa, todo
bien?` cuentan como saludo en cualquier turno, igual que `hola`. Un saludo así
**no** llega al clasificador y **no** suma `unknown_intent`.

Producción: `"Holaa"` no está en `GREETING_WORDS` (`app/chat/nodes/receive.py:33`),
así que `is_greeting_only` y `is_social_only` devolvieron `False` y el turno tomó
el camino de contenido.

### S2 · La ráfaga de primer contacto no promete ayuda que nadie pidió

Dos mensajes del cliente antes de la primera respuesta son **un turno**
(`collapse_trailing_burst`, `app/chat/state.py:48`): `"Holaa"` + `"Cómo estás?"`
se leen como `"Holaa\nCómo estás?"`. Ese turno:

- `has_content` es `False`, así que el saludo elegido es el que **pregunta**
  (`greeting_name`: `"Hola, {{nombre}}. Soy Max, el asistente virtual de Lumat.
  ¿En qué te puedo ayudar?"`), nunca el que promete (`greeting_short_name`:
  `"Hola, {{nombre}}. Soy Max, de Lumat. Ya te ayudo con eso."`);
- responde la pregunta social con `messages.social` y **no** clasifica;
- no arrastra `messages.smalltalk` (`"Con gusto. ¿Te puedo ayudar en algo más?"`).

Producción contestó exactamente lo contrario:
`"Hola, Max Escanilla. Soy Max, de Lumat. Ya te ayudo con eso.\n\nCon gusto. ¿Te
puedo ayudar en algo más?"`.

### S3 · Nada con contenido se pierde en el saludo

La reducción de letras no crea saludos de la nada: `"holaa necesito una visita"`,
`"holanda"`, `"hola, tengo un calefont que no calienta"` y `"buenas necesito una
visita"` siguen siendo contenido y siguen clasificando. Es la guarda contra el
defecto inverso —ignorar al cliente— que cuesta más que el que se arregla acá.

### S4 · El cliente que no entendió al bot recibe una reparación, no un espejo

Cuando el cliente dice que **no entendió al bot** (`"No te entendí"`, `"no
entendí"`, `"no entiendo nada"`, `"no te entiendo"`, `"no comprendo"`) y no hay
campo de captura pendiente, el bot:

- responde un mensaje determinista nuevo, `messages.confusion`, que se hace cargo
  del malentendido y ofrece las dos salidas (repetir con otras palabras o una
  persona) — sin llamada al modelo;
- **no** suma `unknown_intent`: la confusión del cliente no es un fallo de
  comprensión del cliente;
- **no** responde `"Perdón. No entendí tu mensaje."`, que es el espejo medido en
  producción;
- no toca el camino de un reclamo con contenido (`"no entiendo por qué me
  cobraron eso"` sigue su ruta normal).

Con un campo de captura pendiente la regla no dispara: ahí el turno sigue siendo
del nodo que está preguntando.

## Tasks

| ID | Specs | Ruta | Commit |
| --- | --- | --- | --- |
| T1 | S1-S3 | inline, test-first: forma reducida en `receive.py` + guardas negativas | `17b13cc8d` |
| T2 | S4 | inline, test-first: detector de confusión + respuesta determinista | `016e436af` |
| T3 | S4 | inline: `messages.confusion` en defaults, labels, validación y panel | `016e436af` |
| T4 | S1-S4 | inline: `bash scripts/test.sh quick`, `db` de las suites tocadas, `full` al cerrar | este corte |

Slice boundary: dos unidades de review (`17b13cc8d` 209 líneas autoradas,
`016e436af` 292) y una tercera solo de documentación. Cada una se lee sola; el
release es uno solo, después de las dos.

## Log

### L1 — pedido del owner (verbatim)

> Hey chat vamos a continuar desde aca:
>
> - necesito que entres al vps solo lectura y revises la ultima conversacion con max escanilla: hubo un error que ya teniamos solucionado:
>
> ```
> 18 de noviembre de 2026
> Holaa
> 21:42
> Cómo estás?
> 21:42
> Lumat
> Hola, Max Escanilla. Soy Max, de Lumat. Ya te ayudo con eso. Con gusto. ¿Te puedo ayudar en algo más?
> 21:42
> No te entendí
> 21:43
> Lumat
> Perdón. No entendí tu mensaje.
> 21:43
> Jaja
> 21:43
> Lumat
> Con gusto. ¿Te puedo ayudar en algo más?
> 21:43
> ```
>
> El cliente saluda en dos turnos. 1er turno hola, 2do turno como estas? el chatbot responde: Hola, Max Escanilla. Soy Max, de Lumat. Ya te ayudo con eso. Con gusto. ¿Te puedo ayudar en algo más?
>
> Por que respondio con "ya te ayudo con eso", si el cliente solo saludo?
>
> Necesito que investigues esto como prioridad. y lo resolvamos. solo una vez que hayamos resuleto esto. nos detenemos. vamos a hacer un releaser y solo despues de eso...

### L2 — decisiones del owner (2026-11-19)

1. Alcance: **saludo + reparación del meta-reclamo** en el mismo corte.
2. Worktree: **sí**, `rapso worktree create saludo-informal --yes`.

### L3 — evidencia de producción (solo lectura, 2026-11-19)

Deploy `v2026.11.10` (`610399db`), contenedor `lumat-api-1` construido
`2026-11-18T15:54Z`. Conversación `40`, cliente `3`:

```
644 inbound  21:42:38.251  Holaa
645 inbound  21:42:39.976  Cómo estás?
646 outbound 21:42:41.340  Hola, Max Escanilla. Soy Max, de Lumat. Ya te ayudo con eso.\n\nCon gusto. ¿Te puedo ayudar en algo más?
647 inbound  21:43:17.872  No te entendí
648 outbound 21:43:20.892  Perdón. No entendí tu mensaje.
649 inbound  21:43:36.641  Jaja
650 outbound 21:43:39.654  Con gusto. ¿Te puedo ayudar en algo más?
```

Eventos: `classified intent:smalltalk` (336), `unknown_intent "No te entendí"`
actor `rule` (337), `classified intent:unknown` (338), `classified
intent:smalltalk` (339).

Settings de producción del tramo relevante:
`messages.greeting_short_name = "Hola, {{nombre}}. Soy Max, de Lumat. Ya te ayudo
con eso."`, `messages.smalltalk = "Con gusto. ¿Te puedo ayudar en algo más?"`,
`messages.clarification = "Perdón. No entendí tu mensaje."`.

### L4 — causa raíz reproducida sin base de datos (2026-11-19)

`collapse_trailing_burst` fusiona los dos inbound (`"Holaa\nCómo estás?"`), y la
comparación por palabra exacta falla:

```
'Holaa\nCómo estás?'   greeting_only=False social_only=False has_content=True  flow_start='classify_intent'
'hola\nCómo estás?'    greeting_only=True  social_only=True  has_content=False flow_start='__end__'
'Holaaa, todo bien?'   greeting_only=False social_only=False has_content=True  flow_start='classify_intent'
```

La familia S1/S2 de `odd/tasks/chatbot-backlog.md` sigue siendo correcta: el
flujo no estaba roto, el vocabulario sí. Un carácter de más cambia el camino del
turno entero.

### L5 — S1-S3 (commit `17b13cc8d`)

RED observado antes de la corrección, en dos niveles: 16 fallos en
`tests/unit/test_chat_greeting.py` (`Holaa`, `holaaa`, `buenaaas`, la ráfaga
`"Holaa\nCómo estás?"`) y el test end-to-end de la ráfaga entrando al clasificador
—`AssertionError: a greeting burst must not reach classification`— con el fix
retirado del árbol. GREEN: 67 tests unitarios y 30 de integración en las dos
suites de conversación.

Implementación: `_reduced` colapsa cada corrida de una letra; el vocabulario se
proyecta una vez (`_GREETING_WORDS_REDUCED`, `_GREETING_FILLERS_REDUCED`,
`_SOCIAL_QUESTION_ENDINGS_REDUCED`, `_GREETING_IDIOMS_REDUCED`,
`_STATEMENT_ENDINGS_REDUCED`) y los matchers comparan tokens reducidos. El texto
del cliente nunca se reescribe.

Un caso que **no** entra y conviene registrar: `holiiss` reduce a `holis`, que no
es una palabra del vocabulario. No se agregó al spec: es una variante inventada,
no medida, y el corte se queda con lo que producción escribió.

### L6 — S4 (commit `016e436af`)

RED conductual observado retirando `receive.py` y `graph.py`: los dos tests de
comportamiento fallaban con la aclaración (`"Disculpa, no te entendí bien…"`) en
lugar de la reparación, y el tercero —el reclamo con contenido— pasaba igual,
que es la guarda. GREEN: 20 unitarios del detector y 3 de integración.

Plomería del mensaje nuevo: `MESSAGE_DEFAULTS` + `_FIXED_MESSAGE_LABELS` (de ahí
sale la validación y la etiqueta humana del panel), `MessagesBody` con default
para clientes de panel viejos, el espejo en `web/src/types.ts`, el campo en
`Settings.tsx` y los mocks. El GET del panel ya expone todo `MESSAGE_DEFAULTS`,
así que el texto nuevo aparece sin tocar el snapshot.

Efecto colateral esperado y corregido: dos tests de panel contaban 12 mensajes
fijos y ahora son 13; el POST auditado de mensajes exige el mapa completo.
