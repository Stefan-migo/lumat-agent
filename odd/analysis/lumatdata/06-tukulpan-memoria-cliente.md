# Tukulpan: memoria de cliente, medida en producción

Fecha: 2026-11-12 · Estado: análisis read-only (sin cambios de código). Autorizado por el owner para entrar al VPS.

Insumo directo de la Fase 2 del roadmap: `app/services/tukulpan.py` es el cimiento de D1, D5, D6 y D10, y hoy no es confiable.

---

## 1. Qué es Tukulpan

No es un chat log. Es una tabla de memoria **tipada** con búsqueda híbrida.

| Pieza | Detalle |
|---|---|
| Servicio | `app/services/tukulpan.py` (941 líneas). Alias de compatibilidad: `app/services/memory.py` |
| Tabla | `memories` (migración `099_memory.sql`, MEM-1) |
| Clave | `(owner_id, proyecto, scope, entity_id, topic_key)` con `nulls_not_distinct` |
| Scopes | `customer`, `panel`, `agent`, `user` |
| Tipos | `decision`, `discovery`, `pattern`, `preference`, `customer_memo`, `summary`, `session`, `prompt` |
| Vector | embedding local de 384d (`kb.embed_texts`, mismo modelo multilingüe que `kb_chunks`, costo $0) |
| Recall | `hybrid_search`: coseno ≥ 0.50 **o** match léxico español, fusión `vector + 0.3·fts`, top 5, sin fallback fuera de scope |
| Dedup | `normalized_hash` (sha256 de contenido normalizado) + `duplicate_count` |
| Curaduría | `pin`, `status` (`active` / `needs_review` / `archived`), `handoff`, `review_after` (decaimiento por tipo) |
| Relaciones | `memory_relations` (juzgadas) y `memory_observations` (4 tipos: recurrencia, sin_respuesta, riesgo, oportunidad) |

## 2. Está cableado al bot de clientes

No es infraestructura ociosa. Tres puntos de contacto:

| Momento | Archivo | Función |
|---|---|---|
| Cada turno escribe | `app/chat/graph.py:389` | `persist_memory_session` |
| Cada turno **lee** | `app/chat/state.py:332` → `respond.py:413` | `load_customer_context` → bloque `<memory>` del prompt |
| Al cerrar la conversación | `app/chat/state.py:181` | `close_conversation` (memo + observaciones tipadas) |

## 3. Medición en producción

Producción: `v2026.11.7`, `schema_migrations` max = `063_artifact_outputs`.
`main` local ya tiene `064_conversation_turn_count.sql` sin desplegar.

Datos base: **4 clientes, 33 conversaciones (todas cerradas), 527 mensajes, 27 casos, 17 visitas**.

```
 memorias | entidades | pinned | no_activas
     22   |     11    |    0   |      0
```

Desglose por scope y tipo:

| scope | tipo | filas | largo máx | largo promedio |
|---|---|---|---|---|
| customer | customer_memo | 4 | 511 | 219 |
| customer | session | 3 | **4.376** | 1.761 |
| panel | decision | 4 | 452 | 296 |
| panel | discovery | 3 | 277 | 257 |
| panel | summary | 3 | 38 | 38 |
| agent | preference | 2 | 195 | 169 |
| agent | discovery | 2 | 817 | 494 |
| agent | summary | 1 | 229 | 229 |

Observaciones: **45** — `recurrencia` 29, `sin_respuesta` 9, `oportunidad` 6, `riesgo` 1.

Estado de la curaduría: **0 pineadas, 0 en `needs_review`, 0 archivadas**. Nadie las tocó nunca; el `pin` está construido y sin uso.

## 4. Los cuatro defectos, con causa en código

### T1 · La memo del cliente es un slot único que se pisa, y un cierre vacío la borra

- **Causa**: `close_conversation` escribe `contenido=acta_text or ""` (`tukulpan.py:799-806`) y `_upsert_resolved` hace `row.contenido = contenido` en la rama de revisión (`tukulpan.py:315`).
- **Evidencia**: `memo_len` es **exactamente** el `summary_len` de la última conversación cerrada, en los 4 clientes:

| Cliente | última conv cerrada | resumen de esa conv | memo del cliente |
|---|---|---|---|
| 1 | 1 | 0 | **0** |
| 2 | 31 | 0 | **0** |
| 3 | 33 | 366 | 366 |
| 4 | 21 | 511 | 511 |

- Y **10 de 33** conversaciones cerradas no tienen resumen. Por eso dos clientes quedaron en cero.
- **Consecuencia**: cerrar una conversación sin acta no agrega información — **borra la anterior**. La memoria de mayor valor del sistema se destruye sola.

### T2 · `session` es un append sin tope

- **Causa**: `persist_memory_session` concatena `f"{previous.contenido}\n{text}"` con cada mensaje inbound, para siempre (`tukulpan.py:746-760`). Sin cap, sin compactación, sin reescritura.
- **Evidencia**: 4.376 caracteres en el cliente 2 y subiendo; contenido con datos de prueba adentro («Hola mundo», «Providence test 1123»).
- **Consecuencia doble**: (a) el embedding es **uno solo del blob completo**, así que el vector representa el promedio de toda la historia y no lo que importa; (b) el texto se re-embebe entero en cada turno, con costo y latencia crecientes.

### T3 · La lectura no tiene presupuesto ni selección

- **Causa**: `load_customer_context` usa `list_for_entity` (todas las filas del cliente, sin límite) y las inyecta enteras en el prompt (`tukulpan.py:696-728`).
- `hybrid_search` existe y es bueno, pero lo usa el asistente del panel (`memory.search`), no el bot de clientes.
- **Consecuencia**: hoy son ~4,4k caracteres y no duele; con una conversación de 710 mensajes es un problema de costo y de atención del modelo. Es el volcado completo o nada.

### T4 · Las observaciones no tienen dedup

- **Causa**: `_fires_recurrencia` dispara en **cada** cierre una vez alcanzado el umbral (`prior_closes + 1 >= settings.obs_recur_count`, `tukulpan.py:869-886`).
- **Evidencia**: el cliente 2 acumuló **21** filas `recurrencia` idénticas; el cliente 3, ocho.
- **Consecuencia**: el registro dice 21 veces lo mismo. Eso no es memoria, es ruido — y contamina cualquier lectura agregada.

## 5. Veredicto

**El motor: suficiente, y sobra.** Scope por entidad, embedding local sin costo, búsqueda híbrida en español, dedup por hash, decaimiento por tipo, relaciones juzgadas, observaciones tipadas. **No hay que construirlo ni reemplazarlo.**

**El modelo de memoria de cliente encima: hoy no alcanza**, y por semántica, no por capacidad:

| Hoy | Debería ser |
|---|---|
| `customer_memo` = resumen de la última conversación | ficha del cliente que se **fusiona** y nunca se pisa |
| `session` = append infinito de lo que dijo el cliente | **recap acotado** con compactación |
| Lectura = volcado completo | **selección con presupuesto** (pin + recencia + relevancia) |
| `recurrencia` × 21 | una observación con `last_seen` y contador |

## 6. Lo que hay que cambiar (input de la Fase 2)

En este orden, porque cada uno es verificable solo:

1. **Merge en vez de overwrite.** Una memo nueva se fusiona con la anterior; un cierre sin acta **no escribe** (no borra). Criterio de aceptación: cerrar una conversación sin resumen deja la memo anterior intacta, con un test que lo pruebe.
2. **Tope y compactación de `session`.** Cap duro de caracteres; al superarlo (o al cerrar), se reescribe como recap estructurado. Criterio: el largo nunca crece sin límite y el embedding se calcula sobre el recap.
3. **Lectura con presupuesto.** `load_customer_context` con tope de caracteres, pin primero, después recencia, y `hybrid_search` cuando la pregunta lo justifique. Criterio: el bloque `<memory>` jamás supera el presupuesto, y un cliente sin memorias produce una cadena vacía (no bloquea).
4. **Dedup de observaciones.** Misma `(scope, entity_id, tipo)` en ventana → actualizar `last_seen` e incrementar contador, no insertar. Criterio: dos cierres seguidos que cumplen recurrencia producen **una** fila.

## 7. Lo que ya funciona y no hay que tocar

- `hybrid_search`: dos canales admitidos por separado porque fallan en direcciones opuestas (una consulta telegráfica diluye el coseno; una consulta natural no relacionada llega a 0.42 y necesita el umbral alto). Está bien razonado y medido.
- El contrato estilo KB: el servicio **stagea**, nunca commitea; el caller es dueño de la transacción.
- `visibility_target`: thread / global / user derivan el eje persistido; la memoria global no puede alcanzarse desde otro proyecto.
- `_guard_writable_project`: la escritura fuera de `default` exige la capacidad del servicio de proyectos.
- El `review_after` por tipo: el decaimiento está construido y es correcto.
- Las 9 observaciones `sin_respuesta` de producción: **ya detectan D10** (hilo muerto). El detector funciona; lo que falta es un lector.

## 8. Nota de infraestructura

Dos hechos operativos que costaron tiempo y conviene registrar:

1. **`~/.ssh/config` está desactualizado.** Apunta a `138.128.243.241`, que da *connection timed out*. El VPS real es `agente.lumat.cl` = `179.199.148.175`, usuario `deploy`. Comando de lectura: `ssh deploy@agente.lumat.cl`, DB con `docker exec -i lumat-db-1 psql -U lumat -d lumat`.
2. **Producción está detrás de `main`.** `v2026.11.7` con schema `063`; `main` tiene `064_conversation_turn_count.sql`. Cualquier cambio de memoria en la Fase 2 se suma a una migración que todavía no llegó a producción.

## 9. El dato que cambia la Fase 7

Medido con una sonda real contra la API de DeepSeek desde el contenedor de producción, con un PNG 32×32:

```
deepseek-chat:  OK -> 'Rojo'   | served=deepseek-flash
deepseek-flash: OK -> ''       | served=deepseek-flash
```

**El modelo que el bot ya usa ve imágenes.** `CHAT_MODEL=deepseek-chat` y el alias se sirve con `deepseek-flash`, multimodal. Dos cautelas medidas: una imagen de 1×1 es rechazada por la API («unsupported image»), y el nombre `deepseek-flash` explícito se comportó distinto del alias con el mismo `max_tokens`. El nombre del modelo no se cambia sin medir.

Con eso, D4 deja de ser un techo de capacidad: el gate (`MEDIA_EVIDENCE_TYPES`) es lo único que impide que el bot mire. Lo que falta para audio es transcripción — DeepSeek no tiene API de audio —, y es una decisión de costo, no de arquitectura.
