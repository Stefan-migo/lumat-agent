# Evaluación conversacional — `citable-3`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `6f67abb2683fff90e85334c0834196914bd07089` · árbol sucio: **no** · corrida: cliente simulado (--live)
- Corpus: `f903619e78bc` · KB: `91ca087a1130` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-10-26T13:01:29+00:00

## Resumen

- Escenarios: **14** · pasan: **5**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 5 | 2 |
| complejo | 4 | 0 |
| supercomplejo | 5 | 3 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G1 | state | 5 |
| G4 | events_forbidden | 4 |
| G6 | must_include_any | 3 |
| G9 | kb_answered | 2 |
| G3 | events_required | 1 |

### Dimensiones del juez

| Dimensión | Media | n |
| --- | --- | --- |
| grounding | 2.93 | 14 |
| policy | 2.64 | 14 |
| conversational | 1.71 | 14 |
| escalation | 3.07 | 14 |
| tone | 3.14 | 14 |
| closure | 2.36 | 14 |

## Escenarios que no pasan

### `simple-cobertura-comuna` (simple)
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-horario-sabado` (simple)
- **G6 · must_include_any**: ninguna respuesta contiene: sabado, sábado, asesor, coordina
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-despedida` (simple)
- **hard fail del juez**: Responder la despedida con una nueva pregunta comercial: después de «eso era todo», el asistente preguntó «¿En qué más te puedo ayudar?».
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-agendar-calefont` (complejo)
- **G1 · state**: state=human, esperado uno de: bot
- **G4 · events_forbidden**: se registró lo prohibido: escalation
- **hard fail del juez**: Se pidieron todos los datos (nombre, correo, dirección y autorización) antes de responder la solicitud de mantención en Ñuñoa, sin informar cobertura, precio ni horario de visitas.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-dos-temas` (complejo)
- **G1 · state**: state=human, esperado uno de: bot
- **G4 · events_forbidden**: se registró lo prohibido: escalation
- **G6 · must_include_any**: ninguna respuesta contiene: garantia, garantía, 6 meses, seis meses
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- **hard fail del juez**: Perder el referente del turno anterior y no saber qué servicio tiene garantía: no responde por el lavado de red ni entrega su garantía documentada.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-no-quiere-email` (complejo)
- **G1 · state**: state=human, esperado uno de: bot
- **G4 · events_forbidden**: se registró lo prohibido: escalation
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **G1 · state**: state=human, esperado uno de: bot
- **G4 · events_forbidden**: se registró lo prohibido: escalation
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-emergencia-gas` (supercomplejo)
- **G3 · events_required**: nunca se registró: escalation
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-burst-contradiccion` (supercomplejo)
- **G1 · state**: state=human, esperado uno de: bot
- **G6 · must_include_any**: ninguna respuesta contiene: caldera
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: super-enojo-reclamo
- Gates que se movieron: simple-horario-sabado/G1 se arregló, simple-horario-sabado/G4 se arregló, simple-horario-sabado/G6 pasó a fallar, complejo-dos-temas/G6 pasó a fallar, super-emergencia-gas/G3 pasó a fallar, super-burst-contradiccion/G6 pasó a fallar
- Delta por dimensión: grounding +0.71, policy +0.93, conversational +0.21, escalation +0.43, tone +0.07, closure -0.14
