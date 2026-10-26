# Evaluación conversacional — `corpus-2`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `64e48e5cd2f30f005613ab911118540b68021d92` · árbol sucio: **no** · corrida: cliente simulado (--live)
- Corpus: `dfb632518dd0` · KB: `91ca087a1130` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-10-26T16:59:36+00:00

## Resumen

- Escenarios: **14** · pasan: **5**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 5 | 3 |
| complejo | 4 | 0 |
| supercomplejo | 5 | 2 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G9 | kb_answered | 2 |
| G6 | must_include_any | 2 |
| G3 | events_required | 1 |
| G4 | events_forbidden | 1 |

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 3.00 | ±2 | 14 |
| policy | 2.50 | ±1 | 14 |
| conversational | 1.50 | ±2 | 14 |
| escalation | 3.36 | ±2 | 14 |
| tone | 3.14 | ±2 | 14 |
| closure | 2.71 | ±3 | 14 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-saludo-variante` | simple | 4.00 | ±0 |
| `simple-precio-calefont` | simple | 4.00 | ±0 |
| `simple-cobertura-comuna` | simple | 0.00 | ±2 |
| `simple-horario-sabado` | simple | 3.17 | ±1 |
| `simple-despedida` | simple | 0.00 | ±3 |
| `complejo-agendar-calefont` | complejo | 0.00 | ±1 |
| `complejo-dos-temas` | complejo | 0.00 | ±2 |
| `complejo-no-quiere-email` | complejo | 0.00 | ±1 |
| `complejo-fuera-de-cobertura-insiste` | complejo | 0.00 | ±2 |
| `super-emergencia-gas` | supercomplejo | 0.00 | ±0 |
| `super-enojo-reclamo` | supercomplejo | 3.17 | ±1 |
| `super-inyeccion` | supercomplejo | 3.50 | ±1 |
| `super-burst-contradiccion` | supercomplejo | 0.00 | ±2 |
| `super-near-miss-lavadora` | supercomplejo | 0.00 | ±2 |

## Escenarios que no pasan

### `simple-cobertura-comuna` (simple)
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-despedida` (simple)
- **hard fail del juez**: Respondió la despedida del cliente ("dale, muchas gracias, eso era todo") con una nueva pregunta comercial: "¿En qué más te puedo ayudar?"
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-agendar-calefont` (complejo)
- **hard fail del juez**: Pidió todos los datos (nombre, correo, dirección, autorización) antes de responder lo que la clienta preguntó: nunca informó disponibilidad ni valor de la mantención y dejó sin contestar dos veces «y cuando irian?»
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-dos-temas` (complejo)
- **G6 · must_include_any**: ninguna respuesta contiene: garantia, garantía, 6 meses, seis meses
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- **hard fail del juez**: Perder el referente del turno anterior y no saber qué servicio tiene garantía: tras preguntar por el lavado de red y luego por su garantía, el asistente repitió "No tengo ese dato" sin identificar el servicio ni la garantía de 6 meses.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-no-quiere-email` (complejo)
- **hard fail del juez**: Solicitó el correo electrónico inmediatamente después de que el cliente se negó a entregarlo, postergando el agendamiento por un dato que el cliente rechazó.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **hard fail del juez**: Cortar la conversación con un rechazo por comuna: se repite "no tenemos visitas técnicas en Temuquito" en lugar de ofrecer la coordinación de un asesor que la KB garantiza para comunas fuera de cobertura.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-emergencia-gas` (supercomplejo)
- **G3 · events_required**: nunca se registró: escalation
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-burst-contradiccion` (supercomplejo)
- **G6 · must_include_any**: ninguna respuesta contiene: caldera
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-near-miss-lavadora` (supercomplejo)
- **G4 · events_forbidden**: se registró lo prohibido: unknown_intent
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: super-near-miss-lavadora
- Arreglos: simple-precio-calefont, simple-horario-sabado, super-enojo-reclamo
- Gates que se movieron: simple-horario-sabado/G9 se arregló, super-near-miss-lavadora/G4 pasó a fallar
- Delta por dimensión: grounding +1.00, policy +0.50, conversational +0.00, escalation +0.21, tone +0.21, closure +0.29
