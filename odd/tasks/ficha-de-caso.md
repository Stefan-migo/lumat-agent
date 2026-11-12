# Ficha de caso — Fase 3 del chatbot de WhatsApp

Feature de la Fase 3 del roadmap del chatbot, alcance fijado en
`odd/handoffs/chatbot-fase-3-ficha-de-caso.md`. Una sola unidad: **el caso existe**.
Riesgo alto declarado en el handoff: item 1 (migración) e item 3 (`respond` corre en cada mensaje).

## Specs

**S1 · La ficha del caso existe y es determinista.**
«Bloque estructurado y acotado (≈1.500 caracteres), **determinista**, reconstruido de la base e
inyectado antes del transcript: qué equipos, qué propiedad, qué se intervino y cuándo, qué quedó
pendiente, qué garantía corre». Sin llamada a modelo para construirla; cota dura de 1.500 caracteres
con recorte determinista.

**S2 · Se inyecta antes del transcript, en `respond`.**
«la ficha se inyecta en el prompt de `respond`, que corre en cada mensaje». La ventana de turno no se
toca: «la ventana de turno se queda como está, es correcta para el tono» (`conversation_transcript`,
`limit=6` sin cambios).

**S3 · La ficha cuelga de la propiedad, no del cliente.**
«Ocho de 34 propiedades reales son de otro. Por eso la ficha cuelga de la **propiedad**, no del
cliente». Cada trabajo anterior se muestra con la dirección donde se hizo; cuando esa dirección no es
la del cliente actual, la ficha la nombra explícitamente para que el bot no la confunda con «mi casa».
No se inventa un modelo de propiedad: el ancla es la dirección registrada en el caso.

**S4 · Linaje de casos.**
«`Case` con `origin_case_id`: un caso nuevo **declara** de dónde viene. No reabre el anterior». Un caso
nuevo de un cliente con casos previos guarda el id del caso previo más reciente; la fila previa no se
modifica (estado, `summary`, `closed_at`, `conversation_id` intactos).

**S5 · `decide_spending`: tres valores, default `si`.**
«Campo de tres valores con **default `si`**; se baja sólo si la conversación lo demuestra». Valores:
`si`, `duda`, `no`. `si` es el default y el valor ante cualquier ausencia de evidencia.

**S6 · La bajada es un extractor determinista de 5-6 frases.**
«La regla de bajada es un extractor de 5-6 frases («soy arrendatario/a», «consulto con el dueño», «el
dueño es X», «te escribo de parte de», «administro», «no es mi casa»)». Determinista, sin modelo,
insensible a tildes y mayúsculas, con límite de palabra. La ausencia de evidencia nunca cambia el valor.

**S7 · No confirmar precio ni autorizar trabajo a quien no decide.**
«La capacidad mínima no es «conocer el rol»: es **no confirmar precio ni autorizar trabajo a quien no
decide**». El hecho viaja en la ficha y en la persona.

**S8 · Una sola pregunta, sólo cuando hay plata en juego.**
«Una sola pregunta, sólo cuando hay plata en juego». Con `decide_spending = duda` y un turno que toca
dinero, `respond` hace una única pregunta determinista y registra el evento; nunca la repite en la
misma conversación.

**S9 · Fuera de alcance.**
«promesas (Fase 4), rescate de hilos (Fase 5), cotización (Fase 6), media/visión (Fase 7), clasificador
(Fase 8)». Tampoco entra la UI del panel: el handoff dice que la sección de casos «es consecuencia, no
trabajo aparte», y la consecuencia empieza cuando la base tiene linaje.

### Decisiones de diseño (no fijadas al detalle en el handoff)

- **D1 · Tokens de `decide_spending`**: `si` | `duda` | `no`. `duda` es el estado «hay indicio, no
  prueba» (nombrar a un dueño distinto del que escribe): es el que dispara S8.
- **D2 · La subida existe, pero sólo por autodeclaración explícita** («soy el dueño», «yo decido»,
  «yo pago»). Sin ella, un falso positivo del extractor bloquearía precios a un propietario para
  siempre. Es una decisión, no una lectura del handoff: queda sujeta a veto del owner.
- **D3 · La garantía que corre** sale de una tabla en código con las tres garantías publicadas en
  `docs/kb/lumat-garantias-pagos.md` (mantención de calefont y de caldera: 1 año o hasta la próxima
  mantención; lavado de red: 6 meses). La ficha dice el vencimiento; nunca lo inventa para un servicio
  sin garantía publicada.

## Tasks

| ID | Specs | Route | Commit |
|---|---|---|---|
| T1 | S4, S5 | Migración `065_case_ficha.sql` + modelos (`cases.origin_case_id`, `customers.decide_spending`) | `feat(db):` propio (item 1) |
| T2 | S1, S3, D3 | `app/services/case_ficha.py` + tests: constructor determinista, cota, propiedad, garantía | `feat(chat):` |
| T3 | S2 | Inyección `<ficha>` antes de `<conversation>` en `respond` + persona | `feat(chat):` |
| T4 | S4 | Linaje en `app/services/cases.py` (`get_or_create_case`, `create_manual_case`) + tests | `feat(cases):` |
| T5 | S5, S6, S7, S8 | `decide_spending`: extractor, persistencia por turno, pregunta única, hecho en ficha y persona | `feat(chat):` |

## Log

**L1 — pedido del owner (verbatim).**

```
Retomamos el hilo del chatbot de Lumat en Fase 3. Leé odd/handoffs/chatbot-fase-3-ficha-de-caso.md y
odd/analysis/lumatdata/03-defectos-y-mejoras.md (D1, D5, D7). Arrancá con la ficha del caso.
```

**L2 — cortes de revisión (slice boundaries).** La unidad se entrega en cortes de ~400 líneas
autoradas: corte 1 = T1 (migración + modelos) + T2 (constructor de la ficha) + T3 (inyección en
`respond`), cerrado en `dd0dcd99` con 847 líneas sobre `origin/main`. Corte 2 = T4 (linaje) y T5
(`decide_spending`), que van en commits propios. Si el corte 2 supera el tamaño razonable, se abre
como PR encadenado sobre el corte 1 en vez de engordar el mismo PR.
