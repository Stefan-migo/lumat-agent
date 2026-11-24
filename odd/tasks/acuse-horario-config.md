# acuse-horario-config — el acuse no clava fecha y el sello dice con qué redacción midió

Corte en dos commits sobre el programa del chatbot: el instrumento declara la redacción de captura que
midió (producción corre `llm`), y el acuse de horario deja de afirmar una fecha que el juez lee como
promesa. Nace del handoff posterior a #880, pendientes 1 (diagnóstico de configuración) y 2 (acuse).

## Specs

S1. «El acuse del capture afirma una fecha («Sobre tu horario: el sábado 28/11») y el juez lo lee como
promesa. Misma clase de defecto que arreglamos, en otro nodo (capture.py).»

S2. «Confirmar la config de producción (`chat.conduct`, `settings` en general) — barato, y decide si el
pendiente 3 es bot o instrumento.»

S3. «ok vamos con 1 y 2. juntos.»

## Tasks

- T1 → S2 · arnés: el sello de la corrida declara `chat.conduct`/`redaccion` · commit 1
- T2 → S1 · `capture`: el acuse nombra día, franja u hora, nunca una fecha · commit 2
- T3 → S3 · verificación (`focused` + `quick`) y cierre del corte · último commit

## Log

L1 — pedido del owner, verbatim: «ok vamos con 1 y 2. juntos.»

L2 — evidencia del pendiente 1 (2026-11-24, `ssh deploy@agente.lumat.cl`,
`select key, left(value::text,220) from settings order by key` sobre `lumat-db-1`): producción tiene
`chat.conduct = {"orden": ["failure", "equipment", "comuna", "availability", "name", "email", "address"],
"redaccion": "llm", "derivaciones": ["cobertura"], "max_preguntas_por_mensaje": 1}`. También
`hours.schedule` días 1–7 00:00–23:59, `hours.timezone` `America/Santiago`, `hours.closure_enabled` false
—la misma ventana que el arnés siembra—, `coverage.communes` con 7 comunas y `reply.texts` con textos
propios del owner.

Consecuencia medida: el pendiente 3 (`¿name?`, `¿equipment?` al cliente) **no** es artefacto del
instrumento, es defecto de producto. La ruta es única: `phrasing.phrase` reescribe sólo cuando
`conduct.redaccion == "llm"`, y `phrasing.rewrite` (`app/chat/phrasing.py:161`) manda al modelo
`Campos pendientes: ['name']` con el identificador interno, mientras `validate` (`phrasing.py:99`) sólo
compara el conteo de `?` y los guardas de números/fechas/correo. Producción está en esa ruta desde que el
owner encendió la redacción con modelo.

L3 — decisión de alcance de T1: el arnés **declara**, no controla. `HARNESS_SETTINGS` siembra únicamente
`hours.schedule`/`hours.timezone`/`hours.closure_enabled` porque es la configuración que el corpus prueba
de forma determinista; sembrar `chat.conduct` cambiaría el texto que el cliente lee en todo el corpus y no
es lo que este corte mide. Lo que hoy falta es honestidad del informe: el sello dice la ventana pero no la
redacción, así que una corrida con `llm` y otra con `plantilla` producen textos distintos bajo sellos
idénticos.

L4 — fuera de alcance, medido: el hueco de `validate`/`rewrite` que deja caer `¿name?` es el pendiente 3 y
va en su propio corte (con test de que un identificador de campo no puede ser una reescritura válida). El
acuse de `capture_availability_ack` (S3 de `agenda-respeta-horario`) interpola el valor que escribió el
cliente, no una fecha del parser, y no cambia acá.

L5 — restricción de no regresión: los acuses existentes son contrato medido. `tests/integration/test_chat_capture.py`
fija cinco veces «queda anotada» y una vez «14:00» en el hold; el G6 de `simple-horario-sabado` acepta
`sabado`, `sábado`, `asesor`, `coordina`. El cambio de T2 tiene que conservar día y hora y sacar sólo la
fecha.
