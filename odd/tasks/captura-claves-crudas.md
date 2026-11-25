# captura-claves-crudas — el cliente no puede leer el nombre interno del campo

Corte del programa del chatbot: pendiente 3 del handoff posterior a #880, confirmado como defecto de
producción en el corte `acuse-horario-config` (no artefacto del instrumento). Con `redaccion: llm` —el
valor que tiene producción— el modelo reescribe la pregunta de captura y puede devolver «¿name?».

## Specs

S1. «Claves crudas al cliente: ¿name?, ¿equipment?. Al cliente le llega el nombre interno del campo.»

## Tasks

- T1 → S1 · `phrasing.validate` rechaza un identificador de campo como reescritura · commit 1
- T2 → S1 · `phrasing.rewrite` deja de mandar identificadores al modelo · commit 2
- T3 → S1 · verificación (`focused` + `quick`) y cierre · último commit

## Log

L1 — pedido del owner, verbatim: «ok merge limpieza y continuamos con el pendiente 3».

L2 — el mecanismo, medido en el corte anterior: la ruta es única y sólo existe con `redaccion: llm`
(producción, `select key, value from settings` sobre `lumat-db-1`, 2026-11-24). `phrasing.phrase`
(`app/chat/phrasing.py`) llama a `rewrite` sólo para `PHRASEABLE_KEYS`; `rewrite` manda al modelo
`Campos pendientes: ['name']` —el identificador interno— y le pide «conserva exactamente su intención y
los campos preguntados»; `validate` sólo compara el conteo de `?` y los guardas de marcas, números,
moneda, fecha y correo, así que «¿name?» pasa como reescritura válida. Evidencia del cliente:
`odd/evals/conv-eval-rebaseline-2026-11-24b-conversaciones.md` líneas 53, 70, 144, 147, 423, 764, 769.

L3 — decisión de alcance: dos capas, en dos commits. **Primero el gate determinista** (T1), porque es la
autoridad: una regla de prompt se puede desobedecer y no deja rastro, y este proyecto ya decidió que lo
que protege al cliente es la regla que se puede probar. **Después la entrada** (T2): si el modelo no
recibe el identificador, tampoco lo repite. El gate queda aunque el prompt mejore, porque el proveedor
puede cambiar sin avisar.

L4 — precisión del gate: `comuna` y `email` son palabras españolas y **no** entran en la lista de
identificadores, o se rechazaría la reescritura correcta («¿En qué comuna estás?», «¿Cuál es tu email?»).
La lista es sólo de tokens que no existen en español: `failure`, `equipment`, `equipment_type`,
`availability`, `name`, `address`. El resto de las garantías (correo y dirección no se adelantan) ya las
da `_FORWARD_GUARDED`.

L5 — restricción de no regresión: `tests/unit/test_capture_phrasing.py` fija que un draft válido que
menciona hechos capturados se acepta y que el modo `plantilla` es byte-idéntico; `test_chat_capture.py` y
`test_capture_validation.py` fijan la pregunta que llega al cliente. Ningún arreglo de este corte puede
cambiar la pregunta cuando el rewrite falla: la caída sigue siendo el template.
