# Chatbot Max — Cerebro V4: contrato de reconciliación y KB oficial

Branch `odd/chatbot-kb` · Delivery `ask-on-risk` · Runner `uv run pytest tests/`
Alcance de esta slice (pasos 1–2): contrato de reconciliación V4 ↔ repo y KB comercial. Sin cambios de código.

## Specs

### S1 — Contrato de reconciliación
`odd/tasks/chatbot-cerebro-max-v4.md` clasifica **toda** sección de `refs/CEREBRO_MAX_LUMAT_V4.pdf` — A1–A9, B1–B4, C1–C3, D1–D14, E1–E3, F — como `cumple`, `falta` o `descarta`, cada una con evidencia `path:line` del repo o una razón explícita de descarte. Criterio de aceptación: ninguna sección de V4 queda sin clasificar.

### S2 — KB comercial en español de Chile, audiencia cliente
Existen cinco documentos bajo `docs/kb/`, escritos para el cliente final: sin jerga interna (`control humano`, `derivar`, `escalar`, `el bot`, `LLM`, `prompt`).

### S3 — Bloques autocontenidos
Cada párrafo de hecho mide **≤ 480 caracteres** y nombra su sujeto (servicio o tema) dentro del propio párrafo. Razón verificada: `app/services/kb.py:37-38` (`CHUNK_SIZE = 500`, `CHUNK_OVERLAP = 50`) y `:95` (`RecursiveCharacterTextSplitter`); `app/chat/nodes/respond.py:194-199` recupera `top_k=5` con `min_sim=0.50`. Un dato partido entre chunks no llega al modelo.

### S4 — Tarifario exacto
El tarifario reproduce las cifras de origen: visita técnica `$30.000`; mantención de calefont `$50.000` de marzo a octubre y `$40.000` de noviembre a febrero; mantención de caldera `$80.000` / `$60.000`; lavado de red `$140.000` / `$120.000`.

### S5 — Sin afirmación tributaria
La KB nunca afirma que un precio incluya o excluya IVA, nunca usa la palabra `total` para referirse a un precio, y deriva el detalle tributario a un asesor. Origen: V4 §A6 y §F ("IVA pendiente de definición comercial").

### S6 — Alcance por servicio
Cada uno de los cuatro servicios declara qué incluye y qué no incluye (para el lavado de red: qué resuelve y qué no incluye).

### S7 — Cobertura
La KB lista exactamente las siete comunas: Las Condes, Ñuñoa, Lo Barnechea, La Reina, Peñalolén, Colina y Huechuraba. Fuera de ellas ofrece coordinación con un asesor; nunca rechaza el trabajo.

### S8 — Horarios
Agendamiento de lunes a viernes, 09:00 a 18:00. Sábados, domingos, festivos y fuera de horario se coordinan con un asesor.

### S9 — Garantías
Mantención de calefont y de caldera: un año o hasta la próxima mantención. Lavado de red: 6 meses. Cubre mano de obra, no repuestos. No cubre intervención de terceros. La procedencia la determina una visita técnica.

### S10 — Identidad y credencial SEC
La KB atribuye la autorización SEC a los técnicos de Lumat, nunca al asistente. Ninguna línea sugiere que Max tenga credencial personal.

### S11 — Pagos y documentos
Aceptamos los medios de pago habituales; el pago anticipado es opcional y también se puede pagar al recibir el servicio. Se emiten boleta y factura.

### S12 — Sin datos inventados
Toda cifra o condición de la KB es trazable al cuestionario o a V4 §C. Ninguna decisión de negocio pendiente se resuelve por redacción.

## Reconciliación V4 ↔ repo

| V4 | Veredicto | Evidencia / razón |
|---|---|---|
| A1 Identidad, misión, presentación | **falta** | `agent/personas/orchestrator.md:1` no tiene nombre ni identidad; dice "gasfitería" y omite calefacción y climatización |
| A2 Prioridades innegociables | **parcial** | Seguridad ✅ `app/chat/graph.py:141-147`; no inventar ✅ `orchestrator.md:1`; herramientas verificables ✅ `booking.py:149` |
| A3 Regla anti-interrogatorio | **falta — bug real** | `app/chat/nodes/capture.py:39-46` ordena `name` → `email` → `comuna` → `address`; `MAX_ASKS = 3` en `:59` |
| A4 Rutina por mensaje | **parcial** | El grafo es determinista (`graph.py:243-308`), pero ningún prompt ve la fecha |
| A5 Etapas GREETING→BOOKED | **descarta** | Duplica `next_step` + `intent` + `booking`: una segunda máquina de estados en paralelo |
| A6 Precios / cobertura / garantías | **falta** | No existe tarifario en KB ni en código; `grep -r "temporada\|invierno\|verano" app/` → 0 |
| A6 Temporada por fecha del servicio | **falta** | Ningún prompt inyecta fecha; `app/services/prompts.py:98-116` solo conversation/booking/kb/user_input |
| A7 Agenda y datos | **parcial** | Agenda real ✅ `booking.py:121-141` + `scheduling.open_slots_for_assignment`; sin validación geográfica |
| A8 Postventa / pagos / humano | **parcial** | Derivación con bundle ✅ `cases.py:146-162`; sin link de pago; sin notificación interna al derivar |
| A9 Seguridad técnica | **parcial** | Protocolo determinista antes del LLM ✅ `emergency.py:61-121`, aviso a dueño y admins ✅; redacción a mejorar en la persona |
| B1 Orden de ejecución | **cumple** | `graph.py:259-308`: emergency → cost → handoff → closure → receive → classify → orchestrate |
| B2 Estado persistente | **descarta** | `next_best_action` ≡ `next_step`; `known_data` ≡ `captured`; `missing_data` se calcula, no se persiste |
| B3 Herramientas con esos nombres | **descarta** | Equivalentes reales: `scheduling.book/cancel/open_slots_for_assignment`, `technician_schedule`, `cases.create_handoff_case`. No se renombra código por un documento |
| B3 `check_coverage`, `get_service_quote`, `get_payment_link` | **difiere** | No existen. Son features nuevas, no arreglos de respuesta |
| B4 Logging y control de generación | **parcial** | Auditoría y actividad ✅ `handoff.py:82-96`; `prompt_version` / `response_origin` no verificados |
| C1 Tarifario automático | **falta** | Se resuelve en esta slice (`docs/kb/lumat-precios.md`) |
| C2 Alcance comercial por servicio | **falta** | Se resuelve en esta slice (`docs/kb/lumat-servicios.md`) |
| C3 Cobertura, horarios, garantías | **falta** | Se resuelve en esta slice (`lumat-cobertura-horarios.md`, `lumat-garantias-pagos.md`) |
| D1–D14 Guiones | **parcial** | Se usan como intuición de test, no como texto a copiar: V4 los declara reconstrucciones anonimizadas, no transcripciones |
| E T01–T24 | **falta** | Ninguno existe como test. T01 (saludo sin formulario) ya cumple vía `receive.py:28-38` |
| E Condición de salida T01–T12 | **falta** | Se implementa en el paso 4 |
| F Decisiones pendientes | **no aplica al código** | Se escala a Lumat; el prompt ya ordena no inventar |

### Lo que el repo ya tiene y V4 no reconoce

- Guardarraíles de costo: `app/chat/nodes/cost_gate.py` + `app/services/costs.py:14-17` (80% conservador, 100% bloqueo, $1.50/conversación, $5/día).
- Emergencias con notificación real: `app/services/notify.py:196-210`, `app/services/notifications.py:205-228`.
- Agenda real con horizonte de técnicos: `app/services/technician_schedule.py`, `app/services/scheduling.py`.
- Derivación con bundle de historial y resumen: `app/services/cases.py:146-162`.
- Idempotencia por WAMID y tolerancia a reintentos: `app/webhook/`.

## Pendientes de decisión de Lumat

No bloquean la construcción: la persona ordena no inventar y derivar.

1. **IVA en los cuatro precios base.** Hasta que se defina, ningún precio se presenta como total con impuesto.
2. **Alcance exacto del descuento de la visita.** Aplica si se contrata mantención o reparación; falta precisar plazo y si es la misma orden.
3. **Exigibilidad del recargo del 15% por cancelación tardía.** Está redactado como condición publicada; requiere validación.
4. **Matriz de garantías más allá de mantenciones y lavado de red.**
5. **Documentos emitibles y distinción informe de servicio / certificación SEC.**

## Tasks

| ID | Task | Specs | Ruta | Estado |
|---|---|---|---|---|
| T1 | Contrato de reconciliación V4 ↔ repo | S1 | inline | ✅ |
| T2 | KB identidad | S2, S3, S10 | inline | ✅ |
| T3 | KB servicios | S2, S3, S6 | inline | ✅ |
| T4 | KB precios | S2, S3, S4, S5 | inline | ✅ |
| T5 | KB cobertura y horarios | S2, S3, S7, S8 | inline | ✅ |
| T6 | KB garantías y pagos | S2, S3, S9, S11 | inline | ✅ |
| T7 | Verificación estructural S2–S12 | S2–S12 | inline | pendiente |

## Log

**L1 (2026-10-20, solicitud original):**
> hey chat necesito que volvamos a trabajar con el chatbot. para mejorar respuestas principalmente. Finalmente obtuve el archivo de informacion de lumat. el oficial. [PDF 1] este es el archivo. probablemente hay que mejorarlo un poco. pero la informacion esta.

**L2 (2026-10-20):**
> no la regla de negar que es IA. no va. ya lo converse ayer con ellos. y lo entendieron

**L3 (2026-10-20):**
> si Max a secas

**L4 (2026-10-20):**
> ok interesante entiendo. pero necesito que trabajemos con esta version 2 del archivo puede incluso existir una version 3

Archivo recibido: `CEREBRO_MAX_LUMAT_V4.pdf`, 16 páginas, fechado 20 de octubre de 2026. Es la versión vigente; una v3 sería anterior.

**L5 (2026-10-20):**
> esta en revision realmente. que tan lejos esta este V4 de lo que veniamos trabajando y que tan lejos estamos de lo que ya tenemos construido. necesito este analisis. la gente de lumat no tienen tanto conocimiento tecnico y a veces preguntan a chat de IA para asesorarse. necesito yo mantener el control del chatbot y filtrar solo lo que nos sirve para la construccion

**L6 (2026-10-20):**
> ok perfecto vamos a comenzar con pasos 1 y 2

### Análisis

- V4 no es una revisión del cuestionario: es un documento derivado de él más cuatro conversaciones reconstruidas. Su parte comercial (§C) es utilizable; su parte técnica (§B) describe un sistema que no es este.
- Tres correcciones de V4 son mejores que el cuestionario y se adoptan: no negar ser IA, no atribuirse credencial SEC personal, y no prometer totales con IVA.
- El único bug que V4 diagnostica con precisión en este repo es el orden de captura de `capture.py` (A3). T01, que V4 declara fallido, ya funciona.
- Se descarta §A5 (etapas), §B2 (estado) y §B3 (nombres de herramientas) por duplicación o renombre sin valor.
- Se difiere `check_coverage`, `get_payment_link` y link de pago: features nuevas, no arreglos.
- La KB se escribe en bloques ≤ 480 caracteres porque el chunker corta a 500 y solo se entregan 5 chunks al modelo.

### Decisiones

- Identidad del asistente: **Max**, asistente virtual de Lumat. Si le preguntan si es un bot, lo dice y continúa.
- Precios en KB con temporada explícita; sin motor de precios ni código nuevo.
- Sin duplicar el tarifario dentro de los servicios: precios viven solo en `lumat-precios.md`.
- La ingestión de los cinco documentos en la KB queda como paso manual vía panel (`visibility=customer`), no como script.
