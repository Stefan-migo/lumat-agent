# Lumat WhatsApp — evaluación y handoff al agente local

Fecha: 22 de octubre de 2026. Revisión del repositorio público [Stefan-migo/lumat-agent](https://github.com/Stefan-migo/lumat-agent).

**Snapshot evaluado:** `main`, commit `fd2e4341291b10cb184b26980f599ba8d1024a42`, publicado a las 14:13:03 de Argentina. [Commit](https://github.com/Stefan-migo/lumat-agent/commit/fd2e4341291b10cb184b26980f599ba8d1024a42).

## 1. Encargo y límites

Evaluar cómo mejorar las respuestas del chatbot de WhatsApp, fundamentándolo en código público, y entregar un plan contrastable contra el repositorio local. Graphify se omitió por instrucción expresa del usuario. No se modificó el repositorio ni se publicaron cambios.

Se revisaron el ingreso de WhatsApp, grafo de conversación, estado, clasificación, recuperación, redacción, captura, agenda, derivaciones, envío y herramientas de evaluación. No se hizo una auditoría exhaustiva del panel ni del asistente interno: son superficies distintas.

**Evidencia obtenida:** lectura estática fijada al SHA y reproducción local de cinco entradas contra las expresiones regulares extraídas del código. No se ejecutaron PostgreSQL, el modelo de embeddings, llamadas al proveedor LLM ni WhatsApp. No se midieron tasas de error, calidad, costos o latencia de producción. Los ejemplos siguientes son casos de prueba propuestos salvo donde se indica reproducción.

La configuración efectiva de producción no está en este análisis. El prompt de persona, mensajes, plantillas, tarifas y conducta pueden provenir de la base de datos; el modelo/proveedor pueden cambiar por entorno. El agente local debe registrar esos valores efectivos sin revelar claves ni datos personales.

## 2. Conclusión

La prioridad es corregir decisiones y conservación de contexto antes de invertir en un modelo más caro. El texto final es solo una parte: las reglas pueden impedir llegar al redactor, la búsqueda puede recuperar un tema sin responder el aspecto consultado y los flujos de captura/agenda pueden ignorar preguntas válidas.

Orden recomendado:

1. Corregir la medición para observar las fuentes realmente consumidas.
2. Reducir derivaciones falsas y diferenciar fallos técnicos de falta de comprensión.
3. Conservar tema + aspecto de la pregunta y reutilizar la recuperación del turno.
4. Hacer que captura y agenda admitan correcciones y preguntas intermedias.
5. Calibrar recuperación con conversaciones y datos representativos.
6. Comparar prompts/modelos con ese contexto y esas métricas ya estabilizados.

No propongo otro framework, más agentes ni una reescritura. El grafo existente permite introducir estas mejoras de forma acotada.

## 3. Qué existe y debe preservarse

- El webhook persiste antes de procesar y deduplica por `wamid`.
- Hay gates de emergencia, costos y derivación antes de la clasificación normal.
- El clasificador y el redactor reciben historial: `conversation_transcript()` entrega hasta seis mensajes anteriores. No es correcto afirmar que el chatbot carece completamente de contexto.
- La búsqueda pública exige `audience=CUSTOMER`, `global_only=True`, documentos activos y su versión activa. Estos límites deben permanecer en todos los fallbacks y cachés.
- Los precios vigentes se construyen desde configuración y fecha; la disponibilidad se consulta a servicios de agenda.
- Las plantillas solo aceptan IDs ofrecidos al clasificador y no se envían con slots vacíos.
- Existen `kb_calibration.py`, `kb_fidelity.py`, `chat_harness.py` y pruebas de integración. Ampliarlos es preferible a crear un segundo sistema de evaluación.

**Cambio reciente que invalida parte de diagnósticos anteriores:** el commit revisado incorpora `retrieval_queries()` y `retrieve_chunks()`. Primero busca el texto actual; si no obtiene resultados, busca `case.service` para una intención conocida. El fallback al servicio ya está implementado. No debe proponerse como si faltara. Tampoco resuelve por sí solo toda la continuidad conversacional.

## 4. Hallazgos y cambios concretos

Prioridades: P1 = impacto directo en respuestas o validez de la evaluación; P2 = mejora relevante que requiere calibración o validación operativa. “Confirmado” describe comportamiento del código, no frecuencia en usuarios reales.

### H01 — P1. El medidor de fidelidad ya no reconstruye la búsqueda real

**Confirmado.** `scripts/kb_fidelity.py::_retrieved_chunks()` vuelve a ejecutar `kb.retrieve(text)` sin el fallback a servicio y sin `global_only=True`. `run_query()` toma esos chunks como evidencia de la respuesta. Producción usa `respond.retrieve_chunks()` con ambos comportamientos adicionales.

Puede evaluar una respuesta rescatada por el servicio contra una lista vacía, o incluir documentos asociados a proyectos que WhatsApp no pudo consultar. Además, la comprobación numérica usa solo chunks aunque el redactor también recibe `<tarifario>`, fecha y agenda. Una tarifa legítima puede quedar señalada como no sustentada. El propio script aclara que la señal numérica no es un veredicto, pero el desajuste de evidencia debe corregirse igualmente.

**Cambio:** capturar la recuperación durante la ejecución real, inicialmente mediante instrumentación del harness que envuelva el servicio y conserve la llamada original. Registrar qué evidencia llegó a `_answer_from_kb`, no solo todas las búsquedas intermedias. Incluir procedencia de tarifas y datos de agenda; diferenciar generación, plantilla y respuesta determinista. Evitar volver a buscar después como sustituto de la evidencia original.

**Aceptación:** caso raw-miss/service-hit reporta los mismos IDs/versiones/chunks consumidos; documento de proyecto no aparece; tarifa vigente válida no cuenta automáticamente como alucinación; un precio inventado sí se señala. Registrar llamadas LLM reales: la previsión actual de una llamada por consulta no contempla clasificación + redacción y posibles resúmenes.

### H02 — P1. Palabras benignas provocan derivaciones irreversibles para ese ciclo

**Confirmado y reproducido a nivel de regex.** `handoff_gate._PERSONA_PATTERN` acepta la palabra `persona` en cualquier contexto. `classify_intent._INJECTION_PATTERNS` incluye `admin(istrador)?`, `otros clientes` y `contraseña` sin exigir una petición maliciosa. El primer gate corre antes del filtro más preciso `is_explicit_human_request()`, por lo que ese filtro no corrige sus falsos positivos.

| Entrada reproducida | Regla activada |
|---|---|
| Soy el administrador del edificio y necesito mantención | injection |
| ¿Cuánto cuesta por persona? | persona |
| No quiero hablar con una persona, solo saber el precio | persona |
| ¿Atienden a otros clientes en Ñuñoa? | injection |
| Necesito cambiar la contraseña del termostato | injection |

Después del handoff, `process_message()` no vuelve a ejecutar el bot mientras la conversación esté en estado humano. Por eso un falso positivo afecta más que un turno.

**Cambio:** unificar la detección de solicitud humana, distinguiendo una selección aislada de menú de una oración. Detectar intención explícita y negación, no solo sustantivos. Para inyección, conservar bloqueos de solicitudes reales de revelar secretos o desobedecer instrucciones y separar vocabulario benigno. No retirar controles de acceso ni confiar en un clasificador como única barrera.

**Aceptación:** las cinco entradas benignas no derivan por esas razones; “quiero hablar con un asesor” deriva; solicitudes reales de revelar datos de otro cliente siguen bloqueadas. Medir precisión/recall por familia y validar también quejas informativas frente a reclamos reales.

### H03 — P1. El fallback a servicio pierde el aspecto de la pregunta

**Confirmado en la construcción de consultas; impacto semántico a medir.** Las consultas son `[texto_actual, servicio]`. No se construye “garantía de mantención de caldera” desde “¿y la garantía?”. Si el texto crudo recupera cualquier chunk sobre otro tema, el fallback ni siquiera se intenta. Si el fallback encuentra descripción general, eso no garantiza evidencia sobre garantía, exclusiones o plazo.

El clasificador sí recibe historial y puede producir un buen `service`, por lo que no se afirma que todos los seguimientos fallen. El límite es que el contrato no separa entidad/servicio y aspecto consultado.

**Cambio mínimo:** añadir al resultado validado de clasificación un `retrieval_query` autocontenido que conserve tema y aspecto, junto con señal de ambigüedad/cambio de tema. Aprovechar la misma llamada antes de añadir otro LLM. Guardar tema activo con origen y actualización; no heredar el servicio cuando el usuario cambió de equipo. Cuando haya dos referentes plausibles, pedir aclaración.

Comparar consultas cruda, contextual y servicio en el harness antes de decidir el orden productivo. No concatenar todo el historial indiscriminadamente. No bajar el umbral global para ocultar este problema.

**Aceptación:** precio → “¿qué incluye?” → “¿y la garantía?” recupera el aspecto correcto; cambiar de caldera a calefont no arrastra contexto; un hit irrelevante del texto crudo no se considera respuesta suficiente.

### H04 — P1. Se repiten búsquedas idénticas dentro del turno

**Confirmado.** `research_triage._kb_check()` recupera y, ante hit, `respond()` vuelve a recuperar sin reutilizar chunks. Ante miss, el subgrafo repite el mismo intento con el mismo estado y parámetros una vez.

Conteos derivados del flujo, no mediciones de tiempo:

| Ruta sin errores ni plantilla | Llamadas a `kb.retrieve` |
|---|---:|
| Hit en texto crudo, triage + respond | 2 |
| Miss crudo, hit servicio, triage + respond | 4 |
| Miss crudo y servicio, reintento de triage | 4 |
| Miss sin servicio, reintento de triage | 2 |

**Cambio:** añadir un resultado de recuperación por turno al estado: `not_run | hit | miss | error`, consultas intentadas y chunks. `respond` consume el resultado; recupera solo si aún no se ejecutó. Distinguir “no ejecutado” de `[]`. Guardar también versión, ámbito y message ID; no compartir el resultado entre clientes ni reutilizarlo en turnos futuros sin invalidación.

Un reintento semántico debe cambiar la consulta. Un reintento técnico debe responder a un error transitorio. Repetir el mismo miss no aporta contexto.

**Aceptación:** hit crudo una recuperación; fallback dos recuperaciones como máximo; miss no repite consultas idénticas; mismo texto final con evidencia equivalente; p50/p95 medidos antes/después.

### H05 — P1. Una pregunta de precio depende innecesariamente de un hit de KB

**Confirmado para la ruta sin plantilla.** El tarifario se carga dentro de `_answer_from_kb()`, pero `respond()` y triage derivan si no hay chunks. Puede existir un precio configurado y vigente y aun así no consultarse porque no apareció un documento semánticamente similar.

**Cambio:** planificar evidencia por tipo: precio → servicio canónico + tarifa vigente; cobertura/horario → fuente estructurada autorizada; alcance/garantía → KB; agenda → servicio de scheduling. Permitir responder el precio respaldado sin exigir un chunk ajeno. Si falta alcance, aclarar el límite, sin inventarlo. Documentar precedencia entre tarifa vigente, KB y plantillas para resolver contradicciones.

**Aceptación:** precio con tarifa válida y KB vacía se responde correctamente; servicio ambiguo pide precisión; servicio sin tarifa no inventa precio; no convierte un valor en total final o condición tributaria no autorizada.

### H06 — P1. Errores técnicos y JSON defectuoso se confunden con incomprensión

**Confirmado.** `_llm_classify()` solicita JSON por texto y aplica `json.loads`; no usa un esquema estricto ni valida exhaustivamente tipos/enums. `bool(parsed.get('injection'))` convierte una cadena no vacía como `"false"` en verdadero. El catch de `classify_intent()` transforma excepciones en `unknown` y las contabiliza como incomprensión. Algunos errores de estructura posteriores, como `fields` no-dict en `_extracted()`, quedan fuera de ese catch.

`_record_unknown_intent()` cuenta todos los eventos de la conversación, no una racha consecutiva. Dos fallos separados por turnos exitosos bastan para derivar.

Además, el catch de recuperación de `respond()` no protege `_kb_check()`, y la llamada de generación de `_answer_from_kb()` no está protegida por ese catch. Una excepción puede subir a `sweep_received()` y marcar el inbound como `failed`, sin respuesta útil.

**Cambio:** contrato validado para intent, injection booleano real, fields y plantilla; salida estructurada cuando el proveedor efectivo la soporte, más validación local siempre. Separar `model_unavailable`, `invalid_model_output`, `retrieval_unavailable` y `semantic_unknown`. Definir presupuesto de reintentos y tiempo total por turno. No contar fallos del proveedor como culpa del cliente.

Confirmar con producto si “dos fallos” significa consecutivos o acumulados. Recomiendo racha consecutiva reiniciada tras comprensión válida, manteniendo eventos históricos para diagnóstico.

**Aceptación:** timeout, JSON malformado, fields-list e injection-string producen una salida controlada; no corrompen caso; no consumen la racha semántica. unknown → éxito → unknown no deriva si se adopta la racha consecutiva. La indisponibilidad de KB se trata igual desde triage y respond.

### H07 — P1. Captura conserva datos obsoletos e interpreta texto libre como campo

**Confirmado.** `_merge_extracted()` solo rellena valores vacíos; no permite reemplazar `comuna`, `address`, `failure` o `equipment` ante una corrección explícita. Cambiar `equipment_type` no limpia automáticamente la falla/equipo anterior. Si hay un campo pendiente y no se extrajo nada, el mensaje se guarda como respuesta del primer campo. En `_dispatch()`, cancelación/reagendamiento durante captura se tratan expresamente como respuestas de campos.

**Cambio:** distinguir extracción nueva, corrección explícita, pregunta y cancelación de flujo. Conservar origen y turno de valores sensibles; permitir reemplazo inequívoco y pedir confirmación si hay ambigüedad. Al cambiar equipo, revisar qué datos siguen siendo pertinentes. Atender “cancela la solicitud” como control de conversación, sin almacenarlo como dirección/falla. No inferir consentimiento.

**Aceptación:** “me equivoqué, es Providencia” reemplaza Ñuñoa; “ahora es otro calefont” no conserva automáticamente la falla de la caldera; cancelar no llena un campo; una pregunta sin signos no se almacena como dato por defecto.

### H08 — P1. Una oferta de agenda bloquea las preguntas intermedias

**Confirmado.** `_after_handoff_gate()` manda directamente a `booking` si existe `_booking_offer`, antes de clasificar. `_resolve()` acepta un número o formatos de fecha/hora concretos. “Antes de elegir, ¿cuánto cuesta?” se trata como selección inválida. Dos entradas inválidas pueden llevar a `booking_unclear`. La preferencia capturada de disponibilidad no se pasa a `open_slots_for_assignment()` desde `_new_offer()`.

**Cambio:** mantener el estado de oferta pero distinguir elegir, preguntar, corregir preferencia, cancelar y rechazar opciones. Responder la consulta y volver a la misma oferta válida sin aumentar intentos fallidos. Incorporar preferencias temporales normalizadas al filtrado de slots o explicar que no hay coincidencias. Seguir confirmando disponibilidad en la operación de reserva.

**Aceptación:** preguntar precio o duración no consume intentos; “el segundo” se resuelve solo si inequívoco; “ninguno, después de las seis” busca alternativas o explica el límite; una oferta caducada/conflictiva nunca confirma reserva.

### H09 — P2. Similaridad no equivale a evidencia suficiente

**Confirmado en diseño; magnitud pendiente.** KB usa cosine top-5, mínimo 0.50, chunks de 500 caracteres con overlap 50. El texto indexado es contenido, sin añadir automáticamente título/jerarquía a cada chunk. La respuesta recibe textos numerados pero pierde IDs/versiones/metadatos. No hay una comprobación explícita de cobertura de las partes preguntadas.

**Cambio escalonado:** etiquetar consultas con documento y fragmento suficiente; medir Recall@5, ranking y suficiencia. Comparar chunking por sección que conserve títulos, condiciones, tablas y unidades. Evaluar expansión limitada de vecinos cuando una condición quede cortada. Probar búsqueda léxica/híbrida para marcas, modelos y códigos solo si hay un fallo medido; añadir reranking únicamente si mejora precisión con latencia aceptable.

Mantener referencias internas por afirmación o por respuesta para auditar. No es obligatorio mostrar citas técnicas al cliente. Incluir instrucciones expresas de que KB/memoria son datos y no órdenes; los delimitadores por sí solos no constituyen una barrera de seguridad.

**Aceptación:** responder garantía exige evidencia sobre garantía, no solo coincidencia con “caldera”; exclusiones y vigencia sobreviven al chunking; preguntas sin respuesta y documentos internos/de proyecto no se convierten en respuestas positivas. Elegir umbral en conjunto de ajuste y validar en un conjunto separado.

### H10 — P2. La ventana corta y el contexto estructurado no están alineados

**Confirmado.** El estado carga diez mensajes; clasificador y redactor usan seis previos. `from_db()` no rellena `summary` ni `case` a partir de registros existentes. El clasificador recibe transcript y plantillas, pero no `captured` ni `memory_context`; el redactor recibe memoria y agenda, pero no un bloque explícito con todos los campos capturados.

**Cambio:** contexto compacto compartido con tema activo, datos confirmados, pregunta pendiente, preferencias y acciones reales. Añadir resumen solo si la evaluación de conversaciones largas lo exige; no ampliar la ventana sin presupuesto. Diferenciar hechos aportados por cliente de afirmaciones previas del bot: el historial no debe convertirse en autoridad comercial.

**Aceptación:** después de más de seis mensajes sigue entendiendo el servicio y no pide la comuna ya confirmada; una corrección prevalece; otro cliente no hereda contexto; la memoria vieja no sobreescribe lo dicho ahora.

### H11 — P2. Mensajes fragmentados pueden perder el orden conversacional

**Riesgo fundamentado, no incidente demostrado.** Cada POST programa un `sweep_received`. Se reclaman mensajes con SKIP LOCKED, pero no se observa exclusión por conversación durante todo el turno. Dos tareas pueden procesar distintos mensajes del mismo cliente. Incluso en un lote secuencial, `from_db(through_message_id=...)` filtra por ID: si dos inbound ya llegaron, la respuesta al primero tendrá un ID posterior al segundo y no entrará en la ventana de ese segundo turno. `turn` además cuenta inbound sin aplicar ese corte.

**Cambio:** reproducir primero con dos sweeps y ráfagas. Serializar por conversación y definir el orden lógico de historial/procesamiento. Evaluar agrupación breve de mensajes consecutivos (“hola” / “mi caldera” / “no prende”) solo después; no demorar emergencias. No reemplazar idempotencia por debounce.

**Aceptación:** en ráfaga el segundo turno ve la respuesta anterior cuando corresponde; no hay dos respuestas incompatibles ni doble reserva; otras conversaciones siguen en paralelo.

### H12 — P2. El camino de envío del bot tiene recuperación distinta al del operador

**Riesgo por frontera transaccional, a reproducir.** `process_message()` genera y llama `deliver_outbound()` en su sesión. Este último hace POST a Meta antes de confirmar durablemente el `wamid`. Si Meta acepta y luego falla la transacción, la entrega externa no se puede deshacer. Con varias respuestas, puede enviarse una y fallar la siguiente. El envío de operador ya distingue SENDING/SENT/UNKNOWN; el camino del bot no reutiliza esa lógica.

**Cambio:** persistir las respuestas antes de entregarlas; separar generación de entrega y registrar intentos/resultados de cada outbound. Un resultado ambiguo de transporte no debe regenerar ni reenviar a ciegas. Añadir vínculo al turno y orden explícito de envío. Diseñar recuperación sin prometer exactamente-una-vez sobre una API externa sin soporte de idempotencia verificado.

**Aceptación:** timeout después de aceptación simulada, error de commit y fallo del segundo mensaje no provocan regeneración silenciosa ni duplicados al reintentar. Medir entrega además de calidad del texto.

## 5. Plan de evaluación local

### Paso A — Contrastar el snapshot

Leer instrucciones locales aplicables respetando la excepción de Graphify indicada por el usuario. No resetear ni sobrescribir cambios locales. Registrar:

```bash
git status --short
git rev-parse HEAD
git remote -v
git log -8 --oneline
git diff fd2e4341291b10cb184b26980f599ba8d1024a42 -- app/chat app/services/kb.py app/services/llm.py app/webhook scripts/kb_fidelity.py
```

Si el SHA no existe localmente, informar la limitación y obtenerlo del remoto correcto según permisos del entorno. Clasificar cada H01–H12 como confirmado, corregido localmente, refutado, pendiente de medición o fuera de alcance. No asumir que el desplegado coincide con `main` o con HEAD local.

Registrar proveedor/modelo efectivo, build de embeddings, hashes de prompts efectivos, ajustes de conducta, plantillas, corpus y fecha de tarifas. No imprimir secretos. Comparar también las personalizaciones de DB: revisar el archivo de persona por sí solo no prueba qué prompt usa producción.

### Paso B — Pruebas sin llamadas reales

Reutilizar los fixtures existentes. Priorizar contratos de JSON, conteo de búsquedas, corpus benigno/malicioso de gates, correcciones de captura, interrupciones de agenda, ámbitos de KB y fallos técnicos. Añadir casos multi-turno, no solo funciones aisladas. Los tests de `test_chatbot_cerebro_qa.py` simulan clasificación/redacción: son útiles para control de flujo, pero no prueban comprensión del modelo real. `test_kb_query_fallback.py` también simula `retrieve`.

### Paso C — Instrumentar antes de medir

Cada turno debe producir un registro con:

```text
run_id, scenario_id, turn_id, commit_sha, config_hash
input_message_ids, route, intent, active_topic, clarification_reason
queries_attempted, retrieval_status, retrieval_calls
evidence: document_id/version/chunk_index/similarity/scope
structured_evidence: tariff_version/date, booking_result
reply_source: generated/template/deterministic
handoff_reason, terminal_state, errors
latency_ms: classify/retrieve/generate/total
llm_calls, input_tokens, output_tokens, estimated_cost
delivery_status (solo pruebas de transporte)
```

No guardar conversaciones identificables en reportes compartidos. El harness del cerebro no ejecuta los guards de `process_message` ni Meta; comprobar continuidad después de handoff y transporte en una prueba separada con envío simulado.

### Paso D — Medición con embeddings/LLM reales

Los scripts escriben y eliminan documentos de prueba. Usar únicamente la DB aislada que exige el propio repositorio, no una base dev o producción con información útil. Los comandos siguientes son los mecanismos existentes revisados; confirmar dependencias y migraciones en el checkout local antes de ejecutarlos.

```bash
bash infra/test-db.sh up
eval "$(bash infra/test-db.sh env)"
uv run python scripts/kb_calibration.py --audience customer --json /tmp/lumat-retrieval-baseline.json
uv run python scripts/kb_fidelity.py --limit 6 --json /tmp/lumat-fidelity-smoke.json
```

**No interpretar fidelidad como confiable hasta corregir H01.** Extender después a escenarios multi-turno y corpus representativo de la KB autorizada, con datos anonimizados. No exportar secretos del entorno. Los scripts con LLM real generan gasto: registrar llamadas reales y acordar un presupuesto de corrida, no confiar en la previsión simplificada del script.

Comparaciones incrementales:

| Variante | Cambio aislado | Pregunta que responde |
|---|---|---|
| A | Estado actual, trazado correcto | ¿Dónde falla hoy? |
| B | Gates benignos + errores técnicos | ¿Cuántas derivaciones evitables se eliminan? |
| C | Consulta contextual | ¿Mejora continuidad sin contaminar temas? |
| D | Recuperación única por turno | ¿Mantiene calidad y reduce trabajo/latencia? |
| E | Correcciones y desvíos en captura/agenda | ¿Resuelve objetivos con menos fricción? |
| F | Chunking/umbral, ajustados aparte | ¿Mejora evidencia suficiente? |
| G | Prompt/modelo alternativo | ¿Qué mejora adicional aporta la generación? |

Repetir al menos tres veces los escenarios generativos con el mismo snapshot/corpus/configuración; temperatura 0 no debe tratarse como garantía de repetibilidad. Reportar denominadores, resultados por familia y ejemplos fallidos. Separar conjunto de ajuste y validación por conversación/tema para no evaluar sobre los mismos ejemplos que guiaron el cambio.

## 6. Matriz mínima de escenarios

Los resultados esperados dependen de fixtures comerciales explícitos; no inventar precios ni políticas para “aprobar” pruebas.

| ID | Escenario | Invariante esperada |
|---|---|---|
| S01 | Saludo solamente | Saludo breve, sin captura administrativa |
| S02 | Mantención de caldera con frase de cortesía | Recupera servicio si existe evidencia |
| S03 | Precio → qué incluye → garantía | Conserva tema y responde cada aspecto |
| S04 | Caldera → “y para un calefont?” | Cambia entidad correctamente |
| S05 | Dos servicios → “¿y ese?” | Aclara referente ambiguo |
| S06 | Soy administrador del edificio | No lo trata como ataque |
| S07 | No quiero una persona, quiero precio | No deriva por sustantivo |
| S08 | Quiero hablar con un asesor | Deriva una vez y detiene bot |
| S09 | Solicitud real de secretos/otro cliente | Bloquea sin revelar datos |
| S10 | Tarifa válida, KB sin coincidencias | Usa tarifa autorizada o aclara servicio |
| S11 | Garantía no documentada, chunk de descripción | No inventa condiciones |
| S12 | Documento interno/proyecto con respuesta exacta | Nunca lo usa en WhatsApp |
| S13 | Corrige comuna/dirección ya capturada | Actualiza sin exigir repetir todo |
| S14 | Pregunta durante captura, con/sin signos | Responde y retoma sin guardar pregunta como campo |
| S15 | Cancelar durante captura | No almacena cancelación como dato |
| S16 | Pregunta precio durante oferta de agenda | Conserva oferta, no cuenta selección inválida |
| S17 | Preferencia fuera de opciones ofrecidas | Propone alternativas reales o explica límite |
| S18 | Oferta vencida / slot tomado | Revalida; no confirma disponibilidad inventada |
| S19 | unknown → éxito → unknown | Aplica política de racha acordada |
| S20 | Timeout/JSON inválido/KB caída | Respuesta controlada y causa técnica separada |
| S21 | Más de seis mensajes previos | Conserva tema y datos confirmados |
| S22 | Audio o imagen con caption | Reconoce límites; no afirma haber interpretado evidencia inexistente |
| S23 | Tres inbound en ráfaga + dos sweeps | Orden consistente, sin acciones duplicadas |
| S24 | Emergencia durante captura/oferta/budget bloqueado | Interrumpe flujo normal y conserva protocolo existente |
| S25 | Meta acepta, respuesta HTTP/commit falla | Estado de entrega explícito, sin reenvío ciego |

S22 es exploratorio: `normalize_message()` extrae body solo de mensajes text; para media conserva payload pero no promueve caption a `text`. Esta revisión no valida capacidad de transcripción/visión. Medir demanda real antes de agregar modelos multimodales; no confundir recibir un archivo con comprenderlo.

## 7. Métricas y criterios de decisión

| Métrica | Definición |
|---|---|
| Éxito de tarea | Escenarios con objetivo resuelto / escenarios evaluados |
| Continuidad | Seguimientos con tema, referente y datos correctos / seguimientos |
| Derivación evitable | Handoffs en casos respondibles/autogestionables / esos casos |
| Precisión de handoff | Handoffs justificados / handoffs realizados |
| Recall de handoff obligatorio | Casos obligatorios derivados / casos obligatorios |
| Recall@5 | Consultas respondibles con evidencia relevante en top-5 / respondibles |
| Suficiencia | Consultas con evidencia para todas las partes solicitadas / respondibles |
| Fidelidad factual | Afirmaciones verificables respaldadas / afirmaciones verificables |
| Corrección comercial | Precios, condiciones y disponibilidad correctos / afirmaciones de ese tipo |
| Fricción | Preguntas repetidas, turnos hasta resolución y aclaraciones innecesarias |
| Rendimiento | p50/p95 por etapa y total; búsquedas y llamadas LLM por turno |
| Entrega | Respuestas persistidas/enviadas/fallidas/ambiguas; duplicados observados |

No fijar un porcentaje de mejora sin baseline. Criterios mínimos propuestos para una candidata: cero filtraciones de ámbitos prohibidos en la batería; cero reservas/precios inventados en casos críticos; sin regresión en emergencia y handoff explícito; reproducción H02 resuelta; fidelidad medida con evidencia real; reducción demostrada de búsquedas duplicadas. Estos ceros son resultados exigidos a la batería finita, no garantías universales.

Evaluación humana ciega de una muestra de respuestas: exactitud, respuesta directa, completitud, claridad y siguiente paso útil. Un juez LLM es apoyo, no fuente de verdad; separar su evaluación del chequeo numérico y de invariantes deterministas.

## 8. Entrega solicitada al agente local

1. Matriz H01–H12 con estado, evidencia local y diferencias frente al SHA revisado.
2. Baseline reproducible con configuración sanitizada, corpus/fixtures y resultados crudos.
3. Diagnóstico por capa: gates, clasificación, recuperación, evidencia, generación, flujo y transporte.
4. Propuesta de cambios mínimos ordenados por impacto, esfuerzo y regresiones posibles.
5. Comparación antes/después de cada candidata que se implemente con autorización; no mezclar todos los cambios y atribuir mejora a uno solo.
6. Lista de incertidumbres que requieran decisión de producto, por ejemplo racha de desconocidos o política de derivación comercial.

**Este handoff encarga contrastar y medir; no ordena aplicar automáticamente todas las propuestas ni desplegar.** No sustituye la revisión local ni las reglas de entrega del repositorio.

## 9. Fuentes verificables

Todas las referencias siguientes corresponden al SHA revisado, no a una rama móvil. Los símbolos permiten encontrarlas aunque cambien las líneas localmente.


| Archivo / símbolo | Enlace permanente |
|---|---|
| `app/chat/nodes/respond.py::retrieval_queries` | [L105](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/nodes/respond.py#L105) |
| `app/chat/nodes/respond.py::retrieve_chunks` | [L134](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/nodes/respond.py#L134) |
| `app/chat/nodes/respond.py::_answer_from_kb` | [L204](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/nodes/respond.py#L204) |
| `app/chat/nodes/respond.py::respond` | [L269](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/nodes/respond.py#L269) |
| `app/chat/subgraphs/research_triage.py::_kb_check` | [L52](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/subgraphs/research_triage.py#L52) |
| `app/chat/nodes/classify_intent.py::_llm_classify` | [L106](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/nodes/classify_intent.py#L106) |
| `app/chat/nodes/classify_intent.py::_extracted` | [L158](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/nodes/classify_intent.py#L158) |
| `app/chat/nodes/classify_intent.py::_record_unknown_intent` | [L183](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/nodes/classify_intent.py#L183) |
| `app/chat/nodes/classify_intent.py::classify_intent` | [L203](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/nodes/classify_intent.py#L203) |
| `app/chat/nodes/handoff_gate.py::evaluate_handoff` | [L98](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/nodes/handoff_gate.py#L98) |
| `app/chat/nodes/orchestrate.py::_dispatch` | [L47](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/nodes/orchestrate.py#L47) |
| `app/chat/nodes/orchestrate.py::_is_question` | [L124](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/nodes/orchestrate.py#L124) |
| `app/chat/state.py::conversation_transcript` | [L46](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/state.py#L46) |
| `app/chat/state.py::ConversationState` | [L139](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/state.py#L139) |
| `app/chat/graph.py::_after_handoff_gate` | [L156](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/graph.py#L156) |
| `app/chat/graph.py::run_conversation` | [L332](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/graph.py#L332) |
| `app/chat/nodes/capture.py::_merge_extracted` | [L239](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/nodes/capture.py#L239) |
| `app/chat/nodes/capture.py::capture` | [L246](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/nodes/capture.py#L246) |
| `app/chat/nodes/capture.py::_ask_next` | [L339](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/nodes/capture.py#L339) |
| `app/chat/nodes/booking.py::_new_offer` | [L55](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/nodes/booking.py#L55) |
| `app/chat/nodes/booking.py::_resolve` | [L82](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/nodes/booking.py#L82) |
| `app/chat/nodes/booking.py::booking` | [L98](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/chat/nodes/booking.py#L98) |
| `app/services/kb.py::chunk_text` | [L95](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/services/kb.py#L95) |
| `app/services/kb.py::_store_chunks` | [L159](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/services/kb.py#L159) |
| `app/services/kb.py::retrieve` | [L391](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/services/kb.py#L391) |
| `app/services/llm.py::openai_client` | [L32](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/services/llm.py#L32) |
| `app/webhook/ingest.py::normalize_message` | [L114](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/webhook/ingest.py#L114) |
| `app/webhook/ingest.py::process_message` | [L347](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/webhook/ingest.py#L347) |
| `app/webhook/ingest.py::sweep_received` | [L403](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/webhook/ingest.py#L403) |
| `app/services/send.py::deliver_message` | [L62](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/services/send.py#L62) |
| `app/services/send.py::deliver_outbound` | [L163](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/services/send.py#L163) |
| `scripts/kb_fidelity.py::_retrieved_chunks` | [L316](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/scripts/kb_fidelity.py#L316) |
| `scripts/kb_fidelity.py::run_query` | [L372](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/scripts/kb_fidelity.py#L372) |
| `scripts/kb_fidelity.py::run` | [L451](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/scripts/kb_fidelity.py#L451) |
| `scripts/kb_calibration.py::_ensure_environment` | [L494](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/scripts/kb_calibration.py#L494) |
| `scripts/kb_calibration.py::main` | [L801](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/scripts/kb_calibration.py#L801) |
| `agent/personas/orchestrator.md` | [Fuente](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/agent/personas/orchestrator.md) |
| `agent/personas/classify.md` | [Fuente](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/agent/personas/classify.md) |
| `app/config.py` | [Fuente](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/config.py) |
| `app/services/settings.py` | [Fuente](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/services/settings.py) |
| `app/webhook/router.py` | [Fuente](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/app/webhook/router.py) |
| `scripts/chat_harness.py` | [Fuente](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/scripts/chat_harness.py) |
| `scripts/kb_calibration_corpus.yaml` | [Fuente](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/scripts/kb_calibration_corpus.yaml) |
| `tests/integration/test_chatbot_cerebro_qa.py` | [Fuente](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/tests/integration/test_chatbot_cerebro_qa.py) |
| `tests/integration/test_kb_query_fallback.py` | [Fuente](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/tests/integration/test_kb_query_fallback.py) |
| `infra/test-db.sh` | [Fuente](https://github.com/Stefan-migo/lumat-agent/blob/fd2e4341291b10cb184b26980f599ba8d1024a42/infra/test-db.sh) |

### Verificación realizada en esta evaluación

Se analizaron con `ast.parse` copias de los módulos públicos para localizar símbolos y generar enlaces. Se ejecutaron exclusivamente las constantes/regex y `is_injection` extraídas mediante AST, con `re` de la biblioteca estándar, para los cinco casos de H02. No se importó la aplicación ni se ejecutó su suite. El resto de hallazgos son lectura estática y propuestas de medición, explícitamente diferenciadas.
