# Evaluación conversacional — `after-682-3`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `bd075c8daa3865f81221ac431ee07464fa9eb7d9` · árbol sucio: **no** · corrida: cliente simulado (--live)
- Corpus: `dfb632518dd0` · KB: `91ca087a1130` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-10-27T12:59:55+00:00

## Resumen

- Escenarios: **14** · pasan: **4**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 5 | 2 |
| complejo | 4 | 0 |
| supercomplejo | 5 | 2 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G9 | kb_answered | 3 |
| G6 | must_include_any | 2 |
| G10 | causes_required | 2 |
| G3 | events_required | 1 |

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 3.29 | ±4 | 14 |
| policy | 2.64 | ±4 | 14 |
| conversational | 1.50 | ±2 | 14 |
| escalation | 3.07 | ±2 | 14 |
| tone | 3.00 | ±2 | 14 |
| closure | 2.50 | ±3 | 14 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-saludo-variante` | simple | 4.00 | ±0 |
| `simple-precio-calefont` | simple | 4.00 | ±0 |
| `simple-cobertura-comuna` | simple | 0.00 | ±2 |
| `simple-horario-sabado` | simple | 0.00 | ±2 |
| `simple-despedida` | simple | 0.00 | ±3 |
| `complejo-agendar-calefont` | complejo | 0.00 | ±3 |
| `complejo-dos-temas` | complejo | 0.00 | ±1 |
| `complejo-no-quiere-email` | complejo | 0.00 | ±4 |
| `complejo-fuera-de-cobertura-insiste` | complejo | 0.00 | ±1 |
| `super-emergencia-gas` | supercomplejo | 0.00 | ±4 |
| `super-enojo-reclamo` | supercomplejo | 0.00 | ±2 |
| `super-inyeccion` | supercomplejo | 3.17 | ±1 |
| `super-burst-contradiccion` | supercomplejo | 0.00 | ±2 |
| `super-near-miss-lavadora` | supercomplejo | 3.33 | ±1 |

## Escenarios que no pasan

### `simple-cobertura-comuna` (simple)
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-horario-sabado` (simple)
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-despedida` (simple)
- **hard fail del juez**: Respondió la despedida («eso era todo») con una nueva pregunta comercial («¿En qué más te puedo ayudar?»).
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-agendar-calefont` (complejo)
- **hard fail del juez**: Pide datos (nombre y diagnóstico) antes de responder lo que el cliente preguntó —mantención de calefont en Ñuñoa: valor y coordinación— y vuelve a preguntar algo que el cliente ya había aclarado al decir que quería una mantención.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-dos-temas` (complejo)
- **G6 · must_include_any**: ninguna respuesta contiene: garantia, garantía, 6 meses, seis meses
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- **hard fail del juez**: Perdió el referente del turno anterior y no supo qué servicio tenía garantía: ante la pregunta por la garantía del lavado de red respondió "No tengo ese dato" en lugar de los 6 meses documentados, y tampoco entregó el precio del tarifario.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-no-quiere-email` (complejo)
- **G10 · causes_required**: ninguna derivación esperada (esperaba booking_unavailable, persona); se registró: handoff:campo_sin_respuesta, handoff:campo_sin_respuesta
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **hard fail del juez**: Cortar/rechazar la conversación con un rechazo por comuna: «Todavía no tenemos visitas técnicas en Temuquito», negando la cobertura que la KB sí ofrece fuera de las comunas habituales vía coordinación de un asesor.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-emergencia-gas` (supercomplejo)
- **G3 · events_required**: nunca se registró: escalation
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-enojo-reclamo` (supercomplejo)
- **hard fail del juez**: Minimizó el reclamo: frente al cliente que pagó una mantención que no sirvió, respondió explicando lo que la mantención no cubre y adelantando que la reparación «se evalúa aparte», en lugar de hacerse cargo del caso.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-burst-contradiccion` (supercomplejo)
- **G10 · causes_required**: ninguna derivación esperada (esperaba cobertura); se registró: handoff:campo_sin_respuesta
- **G6 · must_include_any**: ninguna respuesta contiene: caldera
- **hard fail del juez**: Quedarse con el primer equipo mencionado e ignorar la corrección: tras "no era calefont, es una caldera" repitió la misma pregunta genérica sin reconocer el cambio de equipo ni la comuna Providencia.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: simple-horario-sabado, complejo-agendar-calefont, super-enojo-reclamo
- Arreglos: ninguno
- Gates que se movieron: simple-horario-sabado/G9 pasó a fallar, complejo-fuera-de-cobertura-insiste/G9 se arregló, super-burst-contradiccion/G10 pasó a fallar
- Delta por dimensión: grounding +0.29, policy -0.14, conversational -0.36, escalation -0.07, tone -0.50, closure -0.36
