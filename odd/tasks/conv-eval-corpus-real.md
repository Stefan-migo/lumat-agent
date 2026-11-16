# Corpus de evaluación derivado de las conversaciones reales

Rama `odd/corpus-real` · worktree `../lumat-agent-odd-corpus-real` · diseño de origen: `odd/analysis/lumatdata/04-corpus-desde-casos-reales.md`

Implementa el doc 04: el instrumento de evaluación (`scripts/conv_eval.py`) deja de medir
la imaginación del dueño y empieza a medir la distribución de entrada real, derivando
escenarios de las 34 conversaciones de WhatsApp que Lumat entregó.

Riesgo: item 6 sólo si se borra un escenario existente. El corpus es interno, no hay datos
del cliente en el repo, no hay migración.

## Specs

- **S1 — Fuente.** Los insumos son las 36 carpetas de `/home/stefan/repos/LumatData/Chat bot IA-20261112T160227Z-1-001/Chat bot IA/chats raw`, de las cuales **34 son conversaciones únicas** (`Hugo Ochoa …(1)` y `Jorge orihuela …(1)` son duplicados byte a byte). Se leen en modo read-only. **Los chats crudos nunca entran al repositorio**; lo único que se versiona es el escenario derivado y su cita.
- **S2 — Cita obligatoria.** Cada escenario derivado lleva en `notes` el nombre de la conversación y el rango de líneas de donde salieron sus turnos, y sus `turns` son el texto **verbatim** del cliente, con sus faltas de ortografía y su español chileno. Traducir o corregir el turno borra justo lo que se mide.
- **S3 — Aditivo, no sustitutivo.** Los escenarios que ya están en `scripts/conv_eval_corpus.yaml` **se quedan**: varios pinnean rojos históricos. Los derivados se agregan.
- **S4 — Regla de oro.** Un escenario derivado sólo puede exigir lo que el bot **puede hacer hoy**. Una capacidad que el bot todavía no tiene va a `odd/analysis/lumatdata/escenarios-objetivo.md`, nunca al corpus: un rojo permanente destruye la señal del instrumento.
- **S5 — Cobertura de los tres tiers.** Se agregan escenarios en `simple`, `complejo` y `supercomplejo`, siguiendo las listas propuestas del doc 04 §4, y toda conversación con desenlace medible queda representada al menos una vez.
- **S6 — Autocontenido.** El corpus carga y evalúa sin acceso a los chats crudos: `scripts/conv_eval.py` en modo scripted corre offline. El derivador acepta la ruta de origen como argumento (`--source`), nunca hardcodeada.
- **S7 — Sin inventos.** Ningún escenario sin cita; ningún turno parafraseado; ninguna expectativa (`expect`, `hard_fails`) que el doc 04 no justifique. Cuando el corpus real no alcanza para una expectativa determinista, se deja fuera de `expect` y se documenta en `notes`.

## Tasks

| ID | Qué | Specs | Ruta | Commit |
|---|---|---|---|---|
| T1 | Derivador `scripts/derive_conv_corpus.py`: parsea las carpetas con `--source`, deduplica, emite un extracto legible por máquina (emisor, timestamp, tipo, línea de origen) | S1, S6 | inline | `feat(evals): derive the scenario extract from the real chats` |
| T2 | Selección de escenarios por tier con cita y rango de líneas, según doc 04 §4 | S2, S5 | worker | junto a T3 |
| T3 | Escritura de los escenarios en `scripts/conv_eval_corpus.yaml` + validación del esquema | S2, S3, S7 | worker | `feat(evals): add scenarios derived from real conversations` |
| T4 | Corrida scripted completa y baseline registrado en `odd/evals/` | S4, S6 | inline | `docs(evals): record the corpus-derived baseline` |
| T5 | Actualizar el estado del doc 04 y el encabezado del corpus | S3, S5 | inline | junto a T4 |

## Estado de las tareas

| ID | Estado | Commit |
|---|---|---|
| T1 | hecho | `f9c540cd` |
| T2 | parcial — 22 de 34 conversaciones con escenario | `adf4aa02` |
| T3 | parcial — 7 escenarios nuevos, 4 citas corregidas | `adf4aa02` |
| T4 | pendiente — corte 2 | — |
| T5 | pendiente — corte 2 | — |

**Frontera de corte (2026-11-16):** el corte 1 cierra en 466 líneas autoradas en 3 commits. Quedan **12 conversaciones sin escenario** (listadas en L5) y el baseline scripted (T4) para el corte 2, sobre rama nueva desde `main` con este corte mergeado.

## Log

**L1 (pedido del owner, verbatim):**

> ok si me gustaria continuar con dos cosas. primero mejorar el evaluator con todos los archivos de conversaciones reales. la idea aqui es seguir utilizando las conversaciones reales que nos paso la gente de Lumat, para mejorar el bot. en este caso seria mejorar el evaluator. la idea aqui seria mejorar el evaluator con casos reales de los chats de whatsapp real que lumat extrajo y nos entrego.

**L2 (acceso a los datos, verbatim):**

> Sí, leé los chats desde ahí

Autorizado el 2026-11-16: lectura read-only de `/home/stefan/repos/LumatData/Chat bot IA-20261112T160227Z-1-001/Chat bot IA/chats raw`. Los crudos no se copian ni se commitean.

**L3 (hallazgo del 2026-11-16, al implementar T1).** Dos hechos que cambian el alcance de T2/T3:

1. **El corpus ya traía 15 escenarios `real-*` con cita** (`real-cortesia-no-es-reclamo` … `real-reclamo-real-si-deriva`), además de los 15 históricos: 30 en total. La derivación no arranca de cero; lo que falta es cobertura.
2. **Cuatro citas preexistentes no verifican**: la auditoría automática no encontró ningún turno dentro del rango citado en `real-dato-mas-pregunta`, `real-solo-sabados`, `real-reagenda-familiar` y `real-cliente-experto`. Se dejan intactas hasta revisarlas contra el chat de origen: una cita que no verifica destruye la trazabilidad que S2 exige.

Alcance corregido de T2/T3: **19 de las 34 conversaciones no tienen escenario**, y las 4 citas dudosas se revisan antes de agregar cualquier otra.

**L4 (entrega de T1, 2026-11-16).** `scripts/derive_conv_corpus.py` lee 36 carpetas, descarta 2 duplicados byte a byte y emite 4.600 mensajes con emisor, timestamp, tipo y línea de origen (2.551 del dueño, 2.049 del cliente). Sin `--source` no hace nada; la ruta nunca se versiona.

**L5 (T2/T3, 2026-11-16).** Cubre S2, S4, S5 y S7. Se corrigieron las cuatro citas: `real-dato-mas-pregunta` a Carla Pacheco `chat.txt:31-39`; `real-solo-sabados` a Sandra Paredes `chat.txt:2-15` (el turno ahora conserva el mensaje completo); `real-reagenda-familiar` a Carla Pacheco `chat.txt:53-56`; `real-cliente-experto` a Carlos Díaz Riveros `chat.txt:45-52`. Las cuatro sí proceden de esas conversaciones; sus rangos previos omitían líneas de turnos.

Se agregaron siete escenarios en conversaciones que no estaban cubiertas: `real-varias-reparaciones` (Gonzalo Bettancourt, 69-71), `real-mantencion-caldera` (Nerys de la Rosa, 25-30), `real-reagenda-mantencion` (Paula Brintrup, 7-18), `real-revision-bano-ruidoso` (Marta Larrain, 5-13), `real-caldera-urgencia` (Marisol Loyola, 5-13), `real-fuga-gas-bodega` (Paolo Ganderini, 3-5) y `real-consulta-otros-equipos` (Francisco Rodríguez, 50-53). Total: 37 (11 simple, 13 complejo, 13 supercomplejo); los 15 históricos no se tocaron.

Siguiente slice: 13 conversaciones todavía sin escenario: Camila Covián, Claudio Meneses Liendo, Diego Prado, Héctor Reyes, Hugo Ochoa, Jorge Orihuela, Juan Pereira, Karen Portal los Maitenes, Kathy, Marcelo Aceituno, María Jesús Ríos, Mónica Dawabe y Sofía.
