# Defectos y mejoras del chatbot de WhatsApp, medidos contra conversaciones reales

Fecha: 2026-11-12 · Estado: análisis read-only sobre `main` (`4ae76ca1`), sin cambios de código.

Base de evidencia: 34 conversaciones únicas (de 36 carpetas: dos son duplicados byte a byte), 32 clientes, **4.600 mensajes**, nov-2025 → nov-2026, 2.049 mensajes de cliente.
Código revisado: `app/chat/graph.py`, `app/chat/state.py`, `app/chat/nodes/{classify_intent,respond,orchestrate,capture,handoff_gate,cost_gate,closure_gate}.py`, `app/models.py`, `agent/personas/{orchestrator,classify}.md`, `scripts/conv_eval.py`.

---

## 0. Cómo se midió

1. Parseo determinista de los 34 exports: emisor, timestamp, tipo de mensaje, latencia de respuesta, adjuntos, fin de hilo (`local-notes/lumatdata/parse.py`, `signals.py`).
2. Extracción de las puertas deterministas **desde el código fuente**, no de memoria: los patrones de reclamo se leen de `handoff_gate.py` y se aplican con la misma semántica de palabra completa y sin tildes que usa producción.
3. Lectura cualitativa de las 34 conversaciones, con citas y número de línea.
4. Contraste contra el comportamiento real del grafo, reconstruido desde `app/chat/graph.py` y `state.py`.

Ninguna afirmación de este documento se apoya en lo que el bot "debería" hacer según un documento: todas se apoyan en código ejecutable o en mensajes citables del corpus.

---

## 1. Contexto medido (el tamaño del problema)

| Métrica | Valor |
|---|---|
| Conversaciones | 34 (32 clientes) |
| Mensajes totales / del cliente | 4.600 / 2.049 |
| Conversaciones con ≥90 mensajes | 23 de 34 |
| Conversación más larga | Sol, 710 mensajes (15% del corpus) |
| Mensajes del dueño con una promesa | **58** |
| Mensajes de cliente con un adjunto | **194 (9,5%)** |
| Notas de voz / videos | 107 / 50 |
| Mensajes de cliente que son "dato + pregunta" en el mismo turno | **303 (14%)** |
| Conversaciones que terminan con mensaje del cliente (hilo abandonado) | **22 de 34** |
| Mediana de respuesta del humano | 2-3 min |

El humano de referencia contesta en minutos, recuerda meses de historial y sostiene ocho frentes abiertos con el mismo cliente. Ninguno de los dos extremos — memoria y cierre — es lo que hoy mide el bot.

---

## 2. Defectos confirmados, con causa en el código

### D1 · El bot recuerda 6 mensajes y la conversación real tiene 700
**Severidad: alta.** SÍNTOMA · CAUSA · ALCANCE

- Causa: `app/chat/state.py:91` renderiza el transcript con `limit: int = 6`; `WINDOW_SIZE = 10` (`state.py:39`) es todo el estado que se reconstruye (D2: sin checkpointer).
- Lo único que sobrevive en base es `Conversation.captured_data` (los 7 campos), la próxima cita, la memoria de cliente y `Case.summary`.
- Alcance: **23 de 34** conversaciones reales superan los 90 mensajes. En Sol, un mensaje del turno 500 no tiene forma de saber qué equipo se intervino en el turno 12.
- Viola una regla que el propio prompt impone: `agent/personas/orchestrator.md` — «Aprovecha lo que el cliente ya dijo […] No vuelvas a preguntar lo que ya sabes».
- No requiere el motor de estados del documento del dueño: requiere **una ficha de caso acumulada** que se persista y se inyecte. `Case` y `CustomerEquipment` ya existen y no se consultan al responder.

### D2 · Una pregunta a media captura se pierde si viene con un dato adosado
**Severidad: alta.**

- Causa: `app/chat/nodes/orchestrate.py:137-156`. Se considera pregunta sólo si `"?" in text and not state.extracted`, o si nombra un término de horario/cobertura (el arreglo T4).
- Evidencia: **303 de 2.157** mensajes del cliente (14%) son "dato + pregunta" en el mismo turno. Ejemplos reales:
  - «es factible que pases tipo 14 horas?» (Carla)
  - «Consulta. No hay cómo importar el repuesto que falta…?» (Carlos Díaz)
  - «A las 14 puede ser?» (Catalina)
  - «carlos. pero dime altiro si atienden sabado» → éste lo arregló T4, y es la misma clase.
- La conjunción es el error: si el turno trae extracción, se trata como respuesta y la pregunta desaparece. La extracción **ya se aplicó** antes de decidir, así que nada se pierde por contestar la pregunta.
- Arreglo acotado: sumar forma interrogativa explícita (`¿…?`, «cuánto», «cuándo», «pueden», «se puede») a la condición, sin tocar el clasificador.

### D3 · «te molesto» se lee como reclamo y deriva a un humano sin LLM
**Severidad: media (bug real, arreglo trivial).**

- Causa: `_COMPLAINT_WORDS` incluye `molesto` y `molesta` con patrón de palabra completa (`handoff_gate.py:92-94`). Un match dispara handoff determinista, sin modelo.
- Evidencia: de **2.049** mensajes del cliente, 3 disparan la puerta y **los 3 son cortesía chilena**, no reclamo:
  - «te molesto con la última pls?» (Javier Gálvez)
  - «pero te molesto el fin de seman un minuto cuando puedas» (Mónica Dawabe)
  - «Te molesto con una pregunta, la casa no logra calentarse a 22 grados» (Pabla Leiva)
- Tasa de falso positivo medida: **100%**. El cliente más educado del país recibe «te atiende una persona» por saludar.
- Arreglo: quitar `molesto`/`molesta` de la lista, o exigir la forma «estoy molesto» / «me molesta que».

### D4 · Un adjunto derivación: no hay visión ni transcripción en el bot de clientes
**Severidad: alta (techo de valor).**

- Causa: `MEDIA_EVIDENCE_TYPES` (image, video, audio, document, sticker) dispara handoff (`handoff_gate.py:42-44`). No hay transcripción de audio en ninguna parte de `app/`; la visión (`view_image`) existe **sólo** en el asistente interno del panel (`app/chat/assistant/`), no en el cerebro de clientes.
- Evidencia: **194 de 2.049** mensajes del cliente (9,5%) son adjuntos; 107 notas de voz, 50 videos, 18 stickers. **27 de 34** conversaciones reales tocan una puerta que saca al bot de la conversación.
- Costo concreto: el humano diagnostica desde el video («Esos son errores de que sigue tapada la caldera», Antonieta L29; Claudio manda video del E25/E26 y se resuelve por chat). El bot no puede y deriva.
- Es una decisión consciente y defendible, pero es el límite superior de lo que el bot puede resolver: conviene medirlo y decidirlo, no heredarlo.

### D5 · El post-servicio no se vincula al trabajo anterior
**Severidad: alta (es la falla más cara).**

- Causa: `Case` no referencia casos ni visitas previos; `CustomerEquipment` cuelga del cliente, no de la propiedad, y no se consulta en `respond`. `Case.summary` se escribe recién en el handoff.
- Evidencia: Antonieta reporta al día siguiente de la mantención; Marcelo Aceituno a los dos días con garantía de un año declarada; Pabla Leiva reincide tres veces; Sol escribe «la mantencion a la caldera la hicieron Uds mismos hace pocos meses» (L691).
- El bot clasifica `postventa`, pero no puede decir lo único que el cliente necesita oír: que hay un trabajo previo y una garantía que revisar. La respuesta de oro EX-003/EX-004 del propio dueño es hoy inemitible.

### D6 · Las promesas no se registran
**Severidad: alta.**

- Causa: no existe objeto tarea/compromiso. `Case.summary` y `ConversationEvent` no modelan «queda pendiente de nuestra parte».
- Evidencia: **58** mensajes del dueño con promesa explícita: «le envío el detalle», «mañana voy», «le confirmo en un rato», «estoy cotizando los repuestos». En el corpus hay promesas cumplidas tarde (cotización a 29 días en Gonzalo; 6 días en Nerys), incumplidas (Paolo: cotización eléctrica pedida 5 meses después) y nunca cerradas (Guila: «Le preparo un informe» → sin documento).
- Nota: el documento del dueño identifica esto correctamente (§19-20). Es el hallazgo más valioso de su paquete.

### D7 · No existe rol ni pagador
**Severidad: alta (riesgo de dinero).**

- Causa: `Customer` no tiene rol; no hay vínculo propietario↔arrendatario.
- Evidencia: 48 menciones de rol. Guila Sosman es **arrendataria** con un calefont que ella misma describe con riesgo de explosión, y el dueño no paga la mitad de un termostato; Diego Prado es arrendatario de Mónica Dawabe y traslada al dueño la decisión de un radiador de 200.000; Sonia Bahamondez es corredora; Sandra Paredes es arrendataria; Marcelo Aceituno pide un recibo «para enviar de respaldo al dueño de la casa».
- Riesgo: autorizar un trabajo, prometer un precio o cobrar a quien no decide.

### D8 · Precio de tarifario ≠ cotización, y falta el paso intermedio
**Severidad: media.**

- Causa: `respond.tariff_service()` reconoce sólo 4 frases explícitas (mantención calefont, mantención caldera, lavado de red, visita técnica). Fuera de eso, KB miss → «no tengo ese dato» u oferta de asesor.
- Evidencia: la demanda real está dominada por trabajos **fuera** de tarifario: encimera nueva (Sol), quemador de cocina agripado (Catalina), cambio de caldera (Paulina), bypass y diseño (Juan Pereira), conversión GLP→GN (Carlos), filtración (Sol), filtro de 120.000 (Nancy), mano de obra de termostato (Guila).
- No es un bug del tarifario: es la ausencia del paso «esto requiere cotización» con captura de antecedentes, que es lo que el humano hacía en un turno.

### D9 · Tres `unknown` derivan, con turnos multi-tema
**Severidad: media.**

- Causa: el clasificador debe elegir **1 de 14** intenciones (`agent/personas/classify.md`); a los 3 `unknown` seguidos la conversación pasa a humano.
- Evidencia: los turnos reales traen 2-3 temas con su lectura técnica: «No calienta la casa, los radiadores están "calientes" pero el termostato llega a 14 con la calefacción prendida» (Paulina). Sol acumula 150 mensajes con signo de pregunta y 91 con dinero: el multi-tema es la norma, no la excepción.
- Riesgo: derivar por incomprensión a un cliente que sí se explicó.

### D10 · Nadie persigue un hilo muerto
**Severidad: alta (costo comercial).**

- Evidencia: **22 de 34** conversaciones terminan con un mensaje del cliente. Sol: 8 meses, cierra con un saludo sin respuesta. María Jesús Ríos: 68 días esperando repuestos, con la calefacción apagada. Hugo Ochoa: pregunta «Quería saber que pasó con el calefon» tras 14 días de silencio.
- `closure_gate` cierra por despedida del cliente; no hay nada que detecte un hilo que se apaga. Es el mismo problema que D6 (compromiso sin dueño) visto desde el otro lado.

---

## 3. Priorización

Criterio: valor medido en el corpus ÷ riesgo de intervención.

| # | Cambio | Valor | Riesgo | Esfuerzo |
|---|---|---|---|---|
| 1 | **D3** sacar `molesto/molesta` del detector de reclamos | Quita un 100% de falsos positivos | muy bajo | 1 línea + test |
| 2 | **D2** preguntar también con forma interrogativa y extracción | Recupera hasta 14% de turnos | bajo | 1 función + tests |
| 3 | **D1** ficha de caso acumulada e inyección de historial | Habilita todo lo demás | medio | varias iteraciones |
| 4 | **D6** objeto de compromiso/tarea | Cierra la brecha más valiosa del paquete del dueño | medio | modelo + nodo |
| 5 | **D5** vínculo post-servicio ↔ trabajo previo | Convierte `postventa` en algo útil | medio | consulta + prompt |
| 6 | **D7** rol del cliente (propietario / arrendatario / corredor) | Evita autorizar gasto ajeno | medio | campo + regla |
| 7 | **D8** paso "requiere cotización" con captura | Convierte un «no tengo el dato» en un avance | bajo | ampliar `tariff_service` |
| 8 | **D4** transcripción de audio (y luego lectura de display) | Recupera 107 notas de voz | alto (costo) | proveedor nuevo |
| 9 | **D9** clasificación multi-tema | Menos derivaciones | medio | clasificador |
| 10 | **D10** detección de hilo inactivo | Recupera clientes perdidos | bajo | job + plantilla |

D1, D5, D6 y D7 son un solo trabajo de fondo («el caso existe»); D2, D3 y D8 son arreglos de turno y se pueden hacer sin esa base.

---

## 4. Lo que hay que NO tocar

Todo esto está verificado en `main` y funcionando; el paquete del dueño podría degradarlo:

1. **Protocolo de emergencia.** `emergency_gate` corre antes que cualquier LLM y antes que el control de presupuesto; el prompt indica alejarse, no accionar artefactos ni luces y llamar a la distribuidora o a Bomberos al **132** (`agent/personas/orchestrator.md:28`). El `safety_protocols.json` del dueño es menos específico.
2. **Detección de inyección (SH-4).** Determinista, antes del modelo, con el texto del cliente siempre dentro de `<user_input>`.
3. **Cortocircuito de saludo (S1).** 11 de 18 `unknown` históricos eran saludos; hoy no lo son.
4. **Precio publicado desde el tarifario en un KB miss (L2).** Evita «no tengo ese dato» cuando la cifra está configurada.
5. **Orden de las puertas:** emergencia > presupuesto > handoff > LLM.
6. **El instrumento de evaluación** (`scripts/conv_eval.py`): 10 puertas deterministas + 6 dimensiones de juez, con tiers. No reemplazarlo por el tablero de métricas del §67 del documento del dueño.

---

## 5. Nota sobre el instrumento de evaluación

El corpus de `scripts/conv_eval_corpus.yaml` tiene hoy **15 escenarios escritos a mano**. El docstring del propio módulo dice el problema: *«The owner was writing a new conversation by hand every time the bot changed, which measures the owner's imagination, not the bot.»*

Estas 34 conversaciones reales son exactamente el insumo que falta: la distribución de entrada real, con sus faltas de ortografía, sus cambios de tema, sus audios y sus silencios. El diseño de esa carga está en `04-corpus-desde-casos-reales.md`.
