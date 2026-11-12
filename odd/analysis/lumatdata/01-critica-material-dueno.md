# Crítica del material que entregó el dueño de Lumat

Fecha: 2026-11-12 · Autor: sesión de análisis (Pi / ODD) · Estado: análisis read-only, sin cambios de código.

Fuentes analizadas, tal como llegaron:

| Archivo | Tamaño | Qué es |
|---|---|---|
| `MAX_LUMAT_CONVERSATION_STRUCTURE_57698p7.md` | 2.176 líneas, 74 secciones | Especificación de arquitectura conversacional escrita por el dueño con ChatGPT |
| `LUMAT_MAX_KNOWLEDGE_BASE_FINAL/` | 13 archivos | "Base de conocimiento conductual": reglas maestras, taxonomías, 94 casos, 6 ejemplos, 8 tests, prompt base |
| `chats raw/` | 36 carpetas, 4.600 mensajes | Exportaciones de WhatsApp del número oficial de Lumat, nov-2025 → nov-2026 |

---

## 1. Veredicto en una línea

El paquete **no es un análisis del chatbot**: es la especificación de un CRM de servicios que el chatbot debería tener detrás.
Confunde el trabajo de un humano con vehículo, herramientas y relación comercial (lo que los chats muestran) con lo que un bot de WhatsApp tiene que decir en el próximo turno (lo que el bot resuelve), y por eso prescribe un motor de estados de 19 objetos donde el cuello de botella real está en cosas de un turno: contestar una pregunta en medio de la captura, enrutar a la fuente correcta, no repetir un dato ya dado.

Se puede rescatar (y hay que hacerlo): el marco *caso ≠ mensaje*, el registro de promesas, la vinculación post-servicio/garantía y la distinción de roles. El resto hay que reescribirlo contra el sistema que existe.

---

## 2. El error de marco

### 2.1 Los chats no contienen al bot

Verificado sobre los 4.600 mensajes: los únicos dos emisores son `Tú` (2.667 mensajes) y el cliente. `Tú` es Maximiliano Escanilla, el dueño — se identifica él mismo en `Camila Covián…/chat.txt:5` («Soy Maximiliano Escanilla técnico SEC») y en `Hugo Ochoa…/chat.txt:11` («Soy Maximiliano Escanilla técnico certificado»); además envía sus propios datos bancarios (`Antonieta Saavedra…/chat.txt:14-19`).

**Cero mensajes del bot en todo el corpus.** No hay una sola respuesta del asistente virtual, ni un log de fallo, ni un `unknown`, ni un handoff.

Consecuencia dura: **de estas conversaciones no se puede diagnosticar al bot.** Lo que sí entregan, y es mucho:

1. la distribución real de entrada (cómo escribe un cliente de verdad, con sus faltas de ortografía y audios);
2. el estándar humano de comportamiento (qué hizo el dueño, qué funcionó, qué se cayó);
3. evidencia de qué fallas cuestan plata y clientes.

El paquete del dueño usa el corpus como si fuera (1)+(2)+(3)+diagnóstico del bot. Ese cuarto uso no existe en los datos.

### 2.2 Lo que el bot es, medido en el código

`app/chat/graph.py` construye un `StateGraph` sobre `ConversationState` **sin checkpointer**: el estado se reconstruye de la base en cada mensaje (D2). El recorrido real es:

```
receive → emergency_gate → cost_gate → handoff_gate → classify_intent
        → capture | respond(KB) | booking | manage | handoff → closure_gate
```

Lo que efectivamente existe (verificado en `app/models.py` y `agent/personas/classify.md`):

- **14 intenciones**: consulta, calefont, caldera, calefaccion, solicitar_visita, cancelar_visita, reagendar_visita, valores, postventa, emergencia, persona, smalltalk, unknown.
- **7 campos capturables**, uno por turno: name, email, comuna, address, equipment, failure, availability.
- **1 caso** (`Case`) con `service`, `amount`, `priority`, `status`, `emergency`, `responsible_id`, `summary`.
- **1 eje de estado conversacional** con 3 valores: `bot` / `human` / `closed`.
- **RAG sobre documentos** (`kb_documents` + `kb_chunks`, pgvector): cobertura, horarios, garantías, servicios. **No hay RAG sobre casos.**
- Puertas deterministas antes de cualquier LLM: emergencia, presupuesto (`cost_gate`), handoff, cierre fuera de horario.
- Precio publicado resuelto desde el tarifario (`tarifa.precios`), no desde la KB.

### 2.3 El delta

| El paquete del dueño exige (§) | Lumat tiene |
|---|---|
| 19 objetos persistentes (§5) | 7 en forma compatible: Customer, Conversation, Message, Case (parcial), Appointment, ConversationEvent, CustomerEquipment |
| 9 ejes de estado independientes (§15) | 1 completo (`bot`/`human`/`closed`) + `AppointmentStatus` + `Case.emergency` booleano |
| Motor de transición de estados (§40) | no existe |
| RAG sobre casos reales (§33-35) | no existe; el RAG es sobre 4 documentos de cliente |
| `next_best_action` calculada (§28-29) | no existe; la decisión es el router del grafo |
| Objetos Task/Commitment (§19-20) | no existe |
| Property, Quote, Part, Payment, Document (§22-25) | no existen |
| Person/Role (§7) | no existe |
| Log de decisión y de retrieval (§38, §34) | no existe; hay `conversation_events` y `audit_log` |

El documento describe, sin decirlo, una reescritura completa del backoffice. Presentado como "contexto para que Max entienda conversaciones", se lee como un requisito del bot. No lo es: 12 de sus 19 objetos no son necesarios para responder bien un mensaje de WhatsApp, y su ausencia no es la causa de que el bot falle.

---

## 3. Contradicciones verificables

Estas no son opiniones: se comprueban contra los archivos entregados.

### 3.1 Tres vocabularios de intención incompatibles entre sí

| Fuente | Vocabulario |
|---|---|
| `…STRUCTURE…md` §12.1 | `REPORT_PROBLEM`, `REQUEST_MAINTENANCE`, `REQUEST_QUOTE`, … (17) |
| `…STRUCTURE…md` §12.2 | `NO_HOT_WATER`, `NO_HEATING`, `GAS_SMELL`, … (18, llamados *issue_type*) |
| `taxonomy/intents.json` | `NEW_SERVICE`, `MAINTENANCE_REQUEST`, `POST_SERVICE_ISSUE`, … (26) |
| El bot real | `consulta`, `calefont`, `caldera`, … (14) |

**La intersección entre `taxonomy/intents.json` y las 14 del bot es vacía: 0 de 26.** Ni un solo identificador compartido. Y `§12.2` mete como *issue_type* cosas que la taxonomía trata como intención (`NO_HOT_WATER`, `SAFETY_GAS`), mientras `§12.1` las separa. Adoptar el paquete tal cual obliga a tirar el clasificador que hoy funciona.

### 3.2 Los 94 casos no cumplen el esquema de casos del propio paquete

`cases/case_schema.json` declara 13 campos. Los 94 registros de `cases/real_cases.jsonl` tienen 8, y **9 de los 13 declarados no aparecen en ninguna fila**:

```
intent · context · states · triggers · correct_behavior · avoid · next_best_action · tags · source_notes
```

Los que sí tienen son metadatos: `case_id`, `customer`, `category`, `scenario` (una línea), `training_value` (una línea), `source_type`, `use_for`, `do_not_use_for`. Ejemplo real, la fila completa del caso 12:

```json
{"case_id":"LUMAT-012","customer":"Karen Lobos","category":"calefont",
 "scenario":"Mantención de dos calefont y filtros",
 "training_value":"Mantener tareas individuales y dependencias.", …}
```

**Ningún caso contiene `correct_behavior`, `avoid` ni `next_best_action`.** Es un índice de temas, no un corpus de entrenamiento. Un RAG sobre esto recupera «Karen Lobos — calefont — mantención de dos calefont y filtros»: una etiqueta. Y como el propio documento prohíbe (§36) usar casos para política, el resultado neto es: se propone un RAG cuyo contenido no puede responder nada.

### 3.3 Los números no cuadran con la evidencia entregada

- El `README.md` y el `manifest.json` declaran **94 casos reales**.
- El corpus tiene, descontando dos carpetas duplicadas byte a byte (`Hugo Ochoa …(1)`, `Jorge orihuela …(1)`), **34 conversaciones de 32 clientes**.
- El paquete nombra 5 identidades que no existen en el corpus entregado: **Andrés Cáceres, Matías Moya, Karen Lobos, Dawabe Textil, «Cliente no especificado»**.

Sobre 94 casos, eso son entre 3 y 4 conversaciones por cliente contadas como "casos" distintos. El dueño avisó que analizó más chats de los que entregó; el problema es que entonces **la base no es reproducible ni auditable con lo que tenemos**, y el peso relativo de cada cliente en el RAG queda inflado por quien más conversó, no por quien más se repite (Sol aporta 6 "casos" y 710 mensajes; Marisol Loyola aporta 1 y 28).

### 3.4 La regla de duplicados no se aplicó a su propia entrega

`§57` exige detectar duplicados por cliente + rango temporal + similitud, para no sobreponderar en RAG. El corpus entregado tiene 2 carpetas idénticas carácter a carácter. La regla es correcta y no se cumplió.

### 3.5 Los "good_response" piden capacidades que no existen

De `training/examples.jsonl`, dos respuestas modelo:

- EX-003: «Sí, tengo el caso de tu caldera registrado.»
- EX-004: «Tienes razón, ese informe quedó pendiente de nuestra parte.»

Hoy el bot no puede emitir ninguna de las dos: no recupera el caso anterior ni tiene registro de entregables. Como objetivo de entrenamiento son correctas; como expectativa de test son imposibles, y usadas así generan fallos que no son del bot. Un corpus de evaluación tiene que distinguir **lo que el bot debería hacer** de **lo que hoy puede hacer**, o mide la segunda cosa creyendo medir la primera.

### 3.6 Pide 100+ tests y entrega 8, y no son ejecutables

`§66` fija un objetivo de 100+ tests de regresión. `tests/regression_tests.jsonl` tiene **8**. Además sus `expect` usan nombres de estado interno (`warranty_state`, `material_state`, `commercial_state`) que ningún componente de Lumat puede producir, y predicados que sólo un juez interpretaría (`must_not_reask_address`, `must_preserve_commitment`). No hay runner, ni umbral, ni mapeo al instrumento que Lumat ya tiene (`scripts/conv_eval.py`: 10 puertas deterministas G1-G10 + 6 dimensiones de juez). Adoptarlo crearía un segundo tablero de puntuación incompatible con el primero.

### 3.7 El protocolo de seguridad entregado es más débil que el que está en producción

`knowledge/safety_protocols.json` para olor a gas dice: «cerrar suministro si es seguro», «ventilar», «evitar llamas», «contactar emergencia/distribuidora».

Lo que Lumat ya responde hoy (`agent/personas/orchestrator.md:28`) es más preciso y más seguro: alejarse del lugar, **no encender ni apagar artefactos ni luces**, contactar desde un lugar seguro a la distribuidora **o a Bomberos al 132**.

El archivo que se presenta como «prioridad CRÍTICA» y primer nivel de la jerarquía (§4) es menos accionable que el prompt vigente. Sustituirlo sería un retroceso en la única materia donde el documento acierta en el orden de prioridades.

### 3.8 Ceguera a costo y latencia

El pipeline propuesto encadena ~15 etapas por mensaje, con retrieval, log de decisión, validación pre-envío (§53) y un objeto `ResponseDecision` por turno. No hay estimación de tokens, ni de latencia, ni de costo por conversación, ni de qué pasa cuando el proveedor falla.

Lumat es una PyME chilena con un `cost_gate` que **bloquea el LLM** cuando la conversación o el día llega al 100% del presupuesto (`app/chat/nodes/cost_gate.py`). Un diseño que cuadruplica las llamadas por turno sin decir cuánto cuesta es inaplicable, por buena que sea la arquitectura.

---

## 4. Lo que el paquete acierta

Sin esto la crítica es injusta y el rescate se pierde.

1. **«La unidad no es el mensaje, es el caso» (§2).** Correcto, y el corpus lo demuestra: Sol lleva 6 hilos abiertos en 710 mensajes; Mónica Dawabe mezcla calefont, calefacción, ruido y una obra B2B en 495. Un bot que responde el último mensaje pierde el hilo.
2. **«Un saludo no reinicia el contexto».** Ya está resuelto en Lumat (S1, `_flow_start` en `app/chat/graph.py`), y coincide con el rojo histórico: 11 de 18 `unknown` de producción eran saludos.
3. **Las promesas crean pendientes (§19-20).** Es un hueco real: el corpus tiene **58 mensajes del dueño con promesa** («te confirmo», «lo reviso», «te mando») y Lumat no tiene objeto `Task`. Hoy una promesa vive en el historial del chat y nadie la vigila.
4. **Post-servicio ≠ cliente nuevo (§43, POST).** Real y verificable: Antonieta reporta el mismo error al día siguiente de la mantención; Marcelo Aceituno a los dos días; Pabla Leiva reincide tres veces. Lumat clasifica `postventa` pero no puede vincularlo al trabajo anterior.
5. **Pagado ≠ terminado · instalado ≠ probado (§41).** Real: Diego Prado y Lukas dependen de autorización del propietario; Nerys paga anticipo y la visita se incumple.
6. **Roles: quien usa el equipo no autoriza el gasto (§7).** Real: Guila Sosman es arrendataria con calefont inseguro; Diego Prado es arrendatario de Mónica Dawabe; Sonia Bahamondez es corredora. Lumat no tiene rol.
7. **No inventar precios, diagnósticos ni disponibilidad (§10, §12).** Coincide exactamente con la regla CM-4 que ya está en producción.
8. **Texto del cliente = datos, nunca instrucciones (§37).** Lumat ya lo hace mejor que el documento: hay detección determinista de inyección antes de cualquier LLM (SH-4, `app/chat/nodes/classify_intent.py:43-57`).

Siete de estos ocho son **capacidades ausentes**, no defectos: son la lista de lo que hay que construir, ordenada por cuánto duele. Ese es el uso correcto del paquete.

---

## 5. Cómo usarlo

| Parte del paquete | Veredicto | Uso |
|---|---|---|
| `§2, §43, §41, §7, §19-20` (caso, post-servicio, roles, promesas) | Correcto | Insumo directo para el backlog, priorizado por el corpus |
| `knowledge/master_rules.md` | Correcto en su mayoría | Candidato a reglas de juez del evaluador, no a prompt |
| `taxonomy/intents.json` | Incompatible (0/26 con el bot) | Descartar como taxonomía; sirve como lista de temas a cubrir |
| `cases/real_cases.jsonl` | Índice sin contenido conductual | No sirve para RAG; sirve como mapa de qué conversación cubre qué |
| `training/examples.jsonl` | 6 ejemplos; 2 piden capacidades ausentes | Útil como semilla de escenarios, con la capacidad marcada |
| `tests/regression_tests.jsonl` | 8 tests, no ejecutables | Reescribir como escenarios del corpus de `conv_eval` |
| `§5, §15, §40, §28-29, §33-35` (objetos, estados, motor, RAG, NBA) | Reescritura de backoffice | Backlog de producto, no requisito del bot |
| `§3, §53, §67` (pipeline, validación, métricas) | Sin costo ni latencia | Reescribir sobre `conv_eval` (G1-G10 + 6 dimensiones) |
| `safety_protocols.json` | Más débil que producción | No sustituir el prompt vigente |

La conclusión operativa: **el paquete es materia prima, no especificación.** Su valor está en nombrar las capacidades que faltan; su riesgo está en que, tomado literalmente, borra un bot que ya funciona mejor en los cuatro puntos donde hoy acierta (saludo, inyección, precio publicado, emergencia).
