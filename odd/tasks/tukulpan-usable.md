# tukulpan-usable — la memoria de cliente deja de borrarse a sí misma

Worktree: `/home/stefan/repos/lumat-agent-odd-tukulpan-usable` · Rama: `odd/tukulpan-usable` · Base: `origin/main` = `26f49047`.

Origen: la medición en producción documentada en `odd/analysis/lumatdata/06-tukulpan-memoria-cliente.md` (llega con el PR #801). Este documento es autocontenido: repite la evidencia que cada spec necesita y no depende de que #801 esté mergeado.

**Riesgo declarado: item 1 (datos guardados) e item 3 (código compartido que corre en cada mensaje de cada conversación).** Verificación independiente obligatoria al cerrar, más diferencial de conducta contra la base. Sin migración: los cuatro arreglos caben en el servicio.

---

## La evidencia que motiva esto

Producción (`v2026.11.7`, schema `063`): 4 clientes, 33 conversaciones cerradas, 527 mensajes, **22 memorias en total**, 0 pineadas, 0 en `needs_review`, 45 observaciones.

| Hallazgo | Medición |
|---|---|
| La memo del cliente se pisa | `memo_len` es **exactamente** el `summary_len` de la última conversación cerrada, en los 4 clientes. Dos quedaron en 0 porque su último cierre no tenía resumen. **10 de 33** cierres no tienen resumen |
| `session` crece sin tope | 4.376 caracteres en un cliente, con texto de prueba adentro, y sube en cada mensaje inbound |
| La lectura no tiene presupuesto | `list_for_entity` devuelve **todas** las filas del cliente y se inyectan enteras en el prompt |
| Las observaciones se repiten | un cliente acumuló **21** filas `recurrencia` idénticas; `_fires_recurrencia` dispara en cada cierre una vez pasado el umbral |

## Specs

**S1 — Un cierre sin acta no borra la memo.** `close_conversation` con `acta_text` vacío **no escribe** la memo: deja intacta la anterior. Hoy escribe `""` y la destruye.

**S2 — Un cierre con acta se acumula, no se reemplaza.** La memo pasa a ser una secuencia de entradas fechadas (`AAAA-MM-DD: <acta>`), una por cierre, la más reciente al final. Contrato del consumidor: `load_customer_context` la sigue leyendo como un bloque de texto, y el contenido previo **nunca** desaparece salvo por el tope de S3.

**S3 — La memo tiene tope y descarta lo más viejo.** Largo máximo `CUSTOMER_MEMO_MAX_CHARS` (3.000). Al superarlo se descartan **entradas completas** desde el principio, nunca se corta una entrada a la mitad. La entrada más reciente siempre sobrevive.

**S4 — La `session` tiene tope y compacta lo más viejo.** Largo máximo `SESSION_MAX_CHARS` (2.000). Al superarlo se descartan **turnos completos** desde el principio. Compactación determinista: no hay llamada al modelo, no hay costo por turno. El turno recién llegado siempre queda.

**S5 — La lectura del contexto tiene presupuesto.** `load_customer_context` nunca devuelve más de `MEMORY_CONTEXT_MAX_CHARS` (1.500) caracteres. Orden de inclusión: `pin` primero, después el resto por `last_seen_at` descendente; se agregan mientras quepan. Cliente sin memorias → cadena vacía, sin excepción, sin bloquear la respuesta.

**S6 — Una observación no se duplica.** Para el mismo `(scope, entity_id, tipo)` dentro de `obs_recur_window_days`, la segunda ocurrencia **actualiza** la fila existente en vez de insertar: `detalle.occurrences` incrementa y `detalle.last_seen` se actualiza. Sin cambio de esquema: el contador vive en el JSONB `detalle`. La clave es `occurrences` y no `count` a propósito: las filas viejas traen un `count` que guardaba el **umbral** configurado (`obs_recur_count`), no la cantidad de ocurrencias, y leerlo como contador las hacía saltar a 3 en la primera actualización. El `count` viejo se conserva intacto y no se lee.

**S7 — Sin migración.** Los cuatro cambios son de servicio. Si un arreglo parece exigir una columna nueva, la implementación se detiene y se reporta en vez de agregar una migración.

**S8 — El contrato KB se respeta.** `tukulpan` sigue **stageando** y nunca commiteando: el caller es dueño de la transacción. Ninguna función nueva ni modificada llama a `commit()`.

**S9 — Ningún comportamiento existente cambia fuera de estos cuatro puntos.** `hybrid_search`, `upsert`, `_fold_duplicate`, `visibility_target`, `_guard_writable_project`, `review_after` y el camino del asistente (`memory.read`/`search`/`write` del panel) quedan igual. La suite completa lo prueba.

## Tasks

| ID | Spec | Ruta | Qué entrega |
|---|---|---|---|
| T1 | S1,S2,S3 | `app/services/tukulpan.py` (`close_conversation`) | memo que acumula y no se borra |
| T2 | S4 | `app/services/tukulpan.py` (`persist_memory_session`) | session acotada por turnos completos |
| T3 | S5 | `app/services/tukulpan.py` (`load_customer_context`) | lectura con presupuesto y prioridad |
| T4 | S6 | `app/services/tukulpan.py` (`_write_observation`) | observación con dedup en ventana |

Cada task llega con su test, escrito antes (RED observado) y con el caso que hoy falla.

## Criterios de aceptación, verificables

1. Cerrar una conversación **sin** resumen deja el contenido de la memo **idéntico** al anterior. Test con la memo previa no vacía.
2. Dos cierres con resumen producen **dos entradas fechadas** en la memo, en orden.
3. Con 5.000 caracteres de actas acumuladas, la memo queda en **≤ 3.000** y la entrada más reciente está presente.
4. Tras 40 turnos inbound, `session` queda en **≤ 2.000** y el turno 40 está presente; el turno 1 ya no.
5. Con 20 memorias de 500 caracteres, `load_customer_context` devuelve **≤ 1.500** caracteres, la pineada está incluida y las demás en orden de `last_seen_at`.
6. Dos cierres consecutivos que cumplen `recurrencia` dejan **una** fila con `detalle.occurrences == 2`.
7. Cliente sin memorias → `""`.
8. `bash scripts/test.sh full` en verde y `bash scripts/test.sh shape` sin superficies nuevas tocadas.

## Log

### L1 — pedido del owner, verbatim

```text
si arranca con fase 1
```

(Contexto previo aprobado, roadmap: *«vamos en ese orden»* sobre las fases 0 a 8. Fase 1 cerrada en el PR #803.)

### L2 — por qué esta fase existe

Las cuatro fases siguientes (D1, D5, D6, D10) leen de Tukulpan. Construir la ficha del caso sobre una memoria que se borra a sí misma es construir sobre arena. Esta fase no agrega capacidad: **hace confiable la que ya existe**.

### L3 — lo que se decidió no hacer

- **No** se agrega un objeto `Property`/`Equipment` acá: es Fase 3.
- **No** se llama al modelo para compactar: sería un costo por turno en el camino más caliente. Compactación determinista por turnos completos; el recap con modelo queda como seguimiento.
- **No** hay migración: el contador de observaciones vive en el JSONB existente.
- **No** se toca el camino del asistente del panel, aunque comparte el servicio (S9).

### L4 — verificación independiente: un bloqueante y cinco avisos

`VERDICT: FINDINGS`. La verificación independiente encontró lo que mi corrida no alcanzó:

- **Bloqueante (real, causado por S2):** `tests/functional/test_api_memories.py:620` afirmaba `memo == "acta del cierre final"`; con entradas fechadas la memo es `"2026-11-12: acta del cierre final"`. La suite quedaba roja. Corregido el assert para verificar la **fecha y el acta por separado**, sin fijar un día concreto.
- **Aviso 2 (corregido):** un acta o un turno **solo** más largo que el tope lo desbordaba (`while len(entries) > 1` conserva el elemento más grande aunque él solo rompa el presupuesto). Ahora el contenido final se trunca con `…`: se conserva el criterio «lo más reciente sobrevive» sin romper el tope.
- **Aviso 3 (corregido):** una memo escrita por el escritor viejo guardaba el acta entera **con sus saltos de línea**; el lector nuevo la partía en varias entradas y el tope tiraba la mitad. Ahora `_memo_entries` reconoce el prefijo `AAAA-MM-DD: ` como inicio de entrada y **todo lo demás pertenece a la entrada anterior**, así una memo legacy se conserva entera.
- **Aviso 4 (corregido):** ver S6 — clave `occurrences` en vez de `count`.
- **Aviso 5 (documentado, sin arreglo):** `_write_observation` hace check-then-insert; dos sesiones concurrentes pueden insertar dos filas. Es la forma previa, la spec no lo pide, y el índice único que lo resolvería está prohibido por S7 (sin migración). Queda como limitación conocida.
- **Aviso 6 (corregido):** `acta_text="   "` es verdadero y escribía una entrada vacía. La guarda ahora exige `strip()`.

El verificador confirmó además, con sondas propias: que S1 deja intactos `contenido`, `last_seen_at`, `updated_at`, `titulo`, `pin`, `origin_thread_id` y las relaciones; que S5 ordena pin primero y respeta el presupuesto; que S6 deduplica por `last_seen` y no por `created_at`; que 40 turnos dan 1.949 caracteres byte-idénticos entre dos corridas; y que **los tests nuevos discriminan**: el código base con los tests nuevos falla 11 de 20.

### L5 — un error de proceso propio: dos suites en un worktree

Mi primera corrida de `full` se detuvo con un timeout en `tests/functional/test_seed_dev.py:42` (familia preexistente, `odd/tasks/suite-truncate-stall.md`), sin ningún `FAILED`. La segunda, deseleccionando ese test, murió en **setup** esperando la base — porque el verificador independiente estaba usando el mismo servidor. La regla «una suite a la vez por worktree» también aplica entre el padre y un subagente verificador: está escrito en `AGENTS.md` y la contradije en la misma instrucción en que la cité. La corrida que vale es la que se hace con la base libre.
