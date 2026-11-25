# eval-conduct-paridad — el arnés mide el bot que atiende: siembra `chat.conduct`

Pendiente 1 del handoff post-`v2026.11.19`. El arnés sembraba la ventana y la agenda, pero
**declaraba** la redacción de captura en vez de controlarla, así que una corrida en la base de
evaluación medía `plantilla` mientras producción corre `llm`.

## Specs

- **S1** — El arnés siembra la redacción de producción: «sembrar `{"redaccion": "llm"}` para
  paridad». La corrida mide el bot que atiende clientes, no el default del código.
- **S2** — El sello sigue declarando con qué midió: «Es la primera corrida en la que el informe dice
  con qué redacción midió». La línea de conducta no se quita; ahora declara un valor garantizado.
- **S3** — Paridad es la fila de producción, verbatim, no una aproximación: «producción tiene
  `chat.conduct = {"orden": ["failure", "equipment", "comuna", "availability", "name", "email",
  "address"], "redaccion": "llm", "derivaciones": ["cobertura"], "max_preguntas_por_mensaje": 1}`»
  (lectura por SSH del 2026-11-24, `odd/tasks/acuse-horario-config.md` L2). Esa fila es
  `CHAT_CONDUCT_DEFAULTS` con `redaccion: llm`: la brecha es una clave, y el test la fija.
- **S4** — El seed conserva el contrato del arnés que ya existe: idempotente (una segunda corrida no
  escribe una segunda fila de auditoría) y autoritativo (un valor distinto se sobrescribe, porque una
  base compartida no decide qué midió una corrida). Base: docstring y test de `seed_harness_settings`.

## Tasks

- T1 → S1-S4 · RED: los tests que fijan la conducta sembrada, su paridad y su idempotencia · `78b756254`
- T2 → S1, S3, S4 · GREEN: `HARNESS_CONDUCT` + `seed_harness_conduct()` y su llamada en `main()` · `78b756254`
- T3 → S2 · las docstrings que decían «declarada, no sembrada» y `L25` del doc del arnés · `78b756254`
- T4 → S1-S4 · verificación (`focused` + `db` + `quick` + `shape`) y cierre del corte · `-`

## Log

L1 — pedido del owner, verbatim (pendiente 1 del handoff, más la decisión):

> 1. Re-baseline del corpus — decidir antes de correr. El arnés no siembra chat.conduct: la base de
> evaluación está vacía, así que mediría plantilla mientras producción corre llm. Elegí: sembrar
> {"redaccion": "llm"} para paridad, o medir plantilla sabiendo que el sello lo va a declarar. Es la
> primera corrida en la que el informe dice con qué redacción midió.

> vamos con el orden sugerido

L2 — decisión de alcance: se siembra `llm` (paridad). El camino alternativo —medir `plantilla` a
sabiendas— queda descartado para el corpus de 43 escenarios: el corpus existe para juzgar al bot que
atiende, y un número citable que describe otro bot no sirve para decidir.

L3 — evidencia de la fila de producción (S3): `acuse-horario-config.md` L2 la transcribe de
`select key, left(value::text,220) from settings order by key` por SSH del 2026-11-24. No se vuelve a
leer producción en este corte: la lectura está registrada y fechada, y el test fija la relación con
`CHAT_CONDUCT_DEFAULTS` para que un cambio de default reabra la decisión en vez de pasar inadvertido.

L4 — corrida y cierre (2026-11-25). `rebaseline-2026-11-25` sobre sello `78b756254`: **37/43, ningún
gate fallido**, y por primera vez el informe declara `Redacción de captura: llm · … · 59d788b0fa50`
(S2, ver `odd/tasks/chatbot-conv-eval.md` L26). La corrida **no es citable**: este doc quedó editado y
sin commitear cuando arrancó, así que el árbol estaba sucio — error de proceso, no del instrumento.

**Frontera de entrega declarada.** El corte tiene tres unidades de commit y la tercera es la más grande
porque incluye los dos informes generados (`.md` y `-conversaciones.md`), que este repositorio versiona
igual que los de 24b:

- `045fda387` — la spec del corte.
- `78b756254` — la semilla y sus tests (código, tests y `L25` de la doc del arnés).
- `afb1e2b9f` — la evidencia de la corrida, `L26` y este registro.

El baseline **citable** se corre después de mergear los cortes del día, sobre árbol limpio: esta corrida
midió el código base, sin ninguno de los arreglos de hoy, así que describe un bot que ya está siendo
reemplazado.
