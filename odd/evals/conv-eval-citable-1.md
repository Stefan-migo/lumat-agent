# Evaluación conversacional — `citable-1`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `7dfffaa4aee46f90ecee5547720078886706e256` · árbol sucio: **no** · corrida: cliente simulado (--live)
- Corpus: `f903619e78bc` · KB: `91ca087a1130` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-10-26T12:02:35+00:00

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
| G1 | state | 6 |
| G4 | events_forbidden | 5 |
| G9 | kb_answered | 3 |
| G6 | must_include_any | 2 |
| G3 | events_required | 1 |

### Dimensiones del juez

| Dimensión | Media | n |
| --- | --- | --- |
| grounding | 2.64 | 14 |
| policy | 2.43 | 14 |
| conversational | 1.43 | 14 |
| escalation | 3.29 | 14 |
| tone | 3.21 | 14 |
| closure | 2.57 | 14 |

## Escenarios que no pasan

### `simple-cobertura-comuna` (simple)
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-horario-sabado` (simple)
- **G1 · state**: state=human, esperado uno de: bot
- **G4 · events_forbidden**: se registró lo prohibido: escalation
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-despedida` (simple)
- **hard fail del juez**: Responder la despedida con una nueva pregunta comercial: tras «eso era todo», el bot preguntó «¿En qué más te puedo ayudar?».
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-agendar-calefont` (complejo)
- **G1 · state**: state=human, esperado uno de: bot
- **G4 · events_forbidden**: se registró lo prohibido: escalation
- **hard fail del juez**: Pedir todos los datos antes de responder lo que el cliente preguntó: el bot encadenó nombre, email, dirección y consentimiento de datos sin entregar información de la mantención ni atender la disponibilidad que la clienta había señalado.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-dos-temas` (complejo)
- **G1 · state**: state=human, esperado uno de: bot
- **G4 · events_forbidden**: se registró lo prohibido: escalation
- **G6 · must_include_any**: ninguna respuesta contiene: garantia, garantía, 6 meses, seis meses
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- **hard fail del juez**: Pierde el referente del turno anterior y no sabe qué servicio tiene garantía: tras preguntar por el lavado de red, el cliente pregunta por "eso" y el bot no identifica el servicio ni su garantía documentada.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-no-quiere-email` (complejo)
- **G1 · state**: state=human, esperado uno de: bot
- **G4 · events_forbidden**: se registró lo prohibido: escalation
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **G1 · state**: state=human, esperado uno de: bot
- **G4 · events_forbidden**: se registró lo prohibido: escalation
- **hard fail del juez**: Rechazo por comuna: «Todavía no tenemos visitas técnicas en Temuquito», repetido textualmente, en lugar de ofrecer la coordinación de asesor que exige la política para comunas fuera de cobertura.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-emergencia-gas` (supercomplejo)
- **G3 · events_required**: nunca se registró: escalation
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-burst-contradiccion` (supercomplejo)
- **G1 · state**: state=human, esperado uno de: bot
- **G6 · must_include_any**: ninguna respuesta contiene: caldera
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

Sin corrida previa: esta es la línea base.
