# HANDOFF — retomar en Fase 3: la ficha del caso

**Fecha**: 2026-11-12. **Para**: el próximo chat que retome el hilo del chatbot de Lumat.
**Regla de entrada**: no re-litigar lo que este documento marca como decidido ni lo que ya está en `main`. Antes de escribir código, leer `odd/analysis/lumatdata/03-defectos-y-mejoras.md` (D1, D5, D7) y `06-tukulpan-memoria-cliente.md`.

---

## Estado verificado

| Cosa | Valor |
|---|---|
| `main` (local y remoto) | `ffdedbc3` — PRs #801, #802, #803 y #805 mergeados |
| Árbol | limpio; sólo dos untracked previos: `docs/integracion-2workers/`, `odd/handoffs/chatbot-agenda-config-fuente.md` |
| Worktrees | sólo el principal |
| Ramas | `main` + `backup/pre-evals-cleanup` (del owner) |
| PRs abiertos | ninguno |
| Suite completa sobre el árbol combinado | **exit 0**, 10m52s, cero fallos |
| CI de GitHub sobre `ffdedbc3` | `test` y `panel` en success |
| Producción | `v2026.11.7`, `schema_migrations` max = `063_artifact_outputs` |
| Migración pendiente de deploy | `064_conversation_turn_count` ya está en `main` |

**Nota de entorno**: el `.venv` del worktree principal se regeneró con `uv sync --frozen` (le faltaba `weasyprint==70.0`, por eso `scripts/test.sh full` no corría desde `lumat-agent/`). Verificado con `quick` al 100%.

---

## Lo entregado en las fases 0 a 2

1. **Análisis** (`odd/analysis/lumatdata/`, 6 documentos + `escenarios-objetivo.md`): crítica del paquete del dueño, ocho patrones del corpus, D1-D10 con causa en código, diseño de escenarios, mapa de las 34 conversaciones, y el estado de Tukulpan medido en producción.
2. **D3** (`handoff_gate.py`): la cortesía chilena dejó de derivar como reclamo. Patrón final por exclusión del clítico: `\b(?<!\bte )(?<!\ble )(?<!\bles )molest[oa]s?n?\b`.
3. **Corpus de evaluación** (`scripts/conv_eval_corpus.yaml`): 15 → **30** escenarios. Los 15 nuevos salen de conversaciones reales, 44 turnos de cliente **verbatim**, cerrando con `--validate-only` → `simple 10 · complejo 9 · supercomplejo 11`.
4. **Memoria de cliente** (`app/services/tukulpan.py`, sin migración): memo fechada que acumula y **no se borra** con un cierre sin acta; `session` 2.000 y contexto 1.500 caracteres; observaciones con dedup (`detalle.occurrences`).

---

## Fase 3 — el alcance, ya decidido

Una sola unidad: **el caso existe**. Tres piezas que son la misma pregunta desde tres lados; separarlas produce tres cosas que no se hablan.

| Pieza | Defecto | Qué significa |
|---|---|---|
| **Ficha de propiedad/equipo** | D1, capa 2 | Bloque estructurado y acotado (≈1.500 caracteres), **determinista**, reconstruido de la base e inyectado antes del transcript: qué equipos, qué propiedad, qué se intervino y cuándo, qué quedó pendiente, qué garantía corre |
| **Linaje de casos** | D5 | `Case` con `origin_case_id`: un caso nuevo **declara** de dónde viene. No reabre el anterior |
| **`decide_spending`** | D7 | Campo de tres valores con **default `si`**; se baja sólo si la conversación lo demuestra |

### Decisiones tomadas, no re-abrir

- **D1 no se arregla subiendo el límite de 6 mensajes.** Tres capas: (1) la ventana de turno se queda como está, es correcta para el tono; (2) la ficha del caso es la capa que sobrevive; (3) la memoria curada de Tukulpan, ahora confiable.
- **D7 no es un sistema de roles.** Es un hecho guardado con default `si`. La capacidad mínima no es «conocer el rol»: es **no confirmar precio ni autorizar trabajo a quien no decide**. La regla de bajada es un extractor de 5-6 frases («soy arrendatario/a», «consulto con el dueño», «el dueño es X», «te escribo de parte de», «administro», «no es mi casa»). Una sola pregunta, sólo cuando hay plata en juego. El rol fino (arrendatario, corredor, administrador) es para el panel y el tono.
- **Ocho de 34 propiedades reales son de otro.** Por eso la ficha cuelga de la **propiedad**, no del cliente.
- **La sección de casos del panel es consecuencia, no trabajo aparte**: hoy el panel lista casos sin hilo porque la base no tiene linaje.
- **Fuera de alcance**: promesas (Fase 4), rescate de hilos (Fase 5), cotización (Fase 6), media/visión (Fase 7), clasificador (Fase 8).

### Riesgo declarado: alto

- **Item 1** (datos guardados): esta fase **sí necesita migración**, a diferencia de la Fase 2.
- **Item 3** (contratos y código compartido): la ficha se inyecta en el prompt de `respond`, que corre en cada mensaje.
- Por eso: worktree propio, documento ODD, RED observado por spec, `full` al cerrar, y **verificación independiente obligatoria** antes del PR. La migración en su propio commit.

---

## Evidencia que sostiene la Fase 3

- **23 de 34** conversaciones reales superan los 90 mensajes; la mayor tiene 710. En el turno 500 el bot no sabe qué equipo se intervino en el turno 12.
- **58 mensajes del dueño contienen una promesa**; el patrón dominante no es «no supe qué hacer» sino «lo dejé pendiente».
- Antonieta reporta al día siguiente de la mantención; Marcelo Aceituno a los dos días con garantía de un año; Pabla Leiva reincide tres veces.
- **8 de 34** propiedades son de otro (arrendatario, corredor, derivación). Guila Sosman es arrendataria con un calefont que ella describe como riesgoso; Diego Prado traslada al dueño la decisión de un radiador de 200.000.
- Lo que decide el desenlace del corpus **no es el diagnóstico técnico**: es la firmeza de la hora y la existencia del precio escrito.

---

## Antes de empezar

1. `git pull` y confirmar `main` = `ffdedbc3` o posterior.
2. `bash scripts/test.sh quick` en el principal para confirmar el entorno.
3. Crear el worktree con los **cuatro pasos de bootstrap** (memoria `lumat/entorno/bootstrap-worktree-odd`): `uv sync --frozen`, `cp infra/.env`, `bash infra/test-db.sh up`, y `graphify-out` por symlink a otro worktree del mismo commit — **no** copiar los 648 MB.
4. Escribir `odd/tasks/<feature>.md` con specs, tasks y log, con el pedido del owner **verbatim** en L1.

## Trampas aprendidas en las fases 1 y 2

- **`gh pr checks --watch` devuelve verde obsoleto** justo después de un push. Guardar el SHA y esperar con `gh run list --commit <sha>` / `gh run watch`.
- **Una suite por worktree y por servidor de test**, también entre el padre y un subagente verificador. El síntoma es un timeout en **setup** esperando psycopg, no una aserción.
- **Un test que trae el implementador puede ser vacuo**: en Fase 2 creaba la segunda conversación con otro teléfono (= otro cliente) y leía una memo que el cierre nunca escribió. Probar que los tests nuevos **fallan en la base** antes de aceptar un verde.
- **El stall de `tests/functional/test_seed_dev.py` es preexistente** (`odd/tasks/suite-truncate-stall.md`). Para tener señal de suite completa: `bash scripts/test.sh full --deselect tests/functional/test_seed_dev.py::test_dev_seed_populates_dashboard_and_composer`.

## Pendientes que no son del roadmap, y son decisión del owner

1. **Desplegar**: producción en schema `063`; `064` ya está en `main`.
2. **Medir los seis detectores deterministas contra el corpus.** Salió de D3: el detector de reclamo tiene **cero verdaderos positivos** sobre 2.049 mensajes reales — su único match son tres «te molesto» de cortesía. Es lectura pura, sin código.
3. **Correr el corpus de evaluación con modelo** (`--run-tag real-corpus`) contra los 30 escenarios: nunca se ejecutó con juez desde que se agregaron los 15 nuevos.
