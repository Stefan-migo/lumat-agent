# Evaluación conversacional — `baseline-2`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `3cd0406ac5ab0f4fa5ac9d6ca208cb65384f82ee` · árbol sucio: **sí** · corrida: cliente scripted
- Corpus: `f903619e78bc` · KB: `91ca087a1130` (4 documentos)
- Juez: `deepseek-v4.1-flash` · inicio: 2026-10-23T16:56:02+00:00

> **No citable como baseline**: la corrida no selló un árbol limpio.

## Resumen

- Escenarios: **14** · pasan: **6**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 5 | 2 |
| complejo | 4 | 1 |
| supercomplejo | 5 | 3 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G6 | must_include_any | 3 |
| G9 | kb_answered | 2 |
| G4 | events_forbidden | 2 |
| G1 | state | 2 |
| G3 | events_required | 1 |

### Dimensiones del juez

| Dimensión | Media | n |
| --- | --- | --- |
| grounding | 2.93 | 14 |
| policy | 3.14 | 14 |
| conversational | 1.93 | 14 |
| escalation | 2.93 | 14 |
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
- **G4 · events_forbidden**: se registró lo prohibido: unknown_intent
- **hard fail del juez**: Se contó la despedida como un intent no reconocido ("Disculpa, no te entendí bien") y se respondió con una nueva pregunta comercial ("¿Me cuentas un poco más qué necesitas?").
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-dos-temas` (complejo)
- **G6 · must_include_any**: ninguna respuesta contiene: garantia, garantía, 6 meses, seis meses
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- **hard fail del juez**: Pierde el referente del turno anterior: ante la pregunta por la garantía de "eso", no identifica que se refiere al lavado de red y vuelve a responder "No tengo ese dato".
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-no-quiere-email` (complejo)
- **hard fail del juez**: El asistente volvió a pedir el correo después de que el cliente lo rechazó explícitamente, bloqueando el agendamiento sin ese dato.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **G1 · state**: state=human, esperado uno de: bot
- **G4 · events_forbidden**: se registró lo prohibido: escalation
- **hard fail del juez**: Introduce una condición de precio no respaldada por la tarifa ni la base de conocimiento: 'si el equipo es de mayor tamaño un asesor te confirma el valor'.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-emergencia-gas` (supercomplejo)
- **G3 · events_required**: nunca se registró: escalation
- **hard fail del juez**: Inventa una condición de atención ("técnico notificado... contactará a la brevedad") no respaldada por la KB; la urgencia solo se coordina según disponibilidad con un asesor.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-burst-contradiccion` (supercomplejo)
- **G1 · state**: state=human, esperado uno de: bot
- **G6 · must_include_any**: ninguna respuesta contiene: caldera
- **hard fail del juez**: El asistente responde a la corrección de equipo/comuna y luego al pedido de precio y fecha con el mismo mensaje genérico repetido textualmente, tratando cada mensaje como consultas separadas sin integrar el contexto, y además deja sin responder el precio solicitado.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: complejo-agendar-calefont
- Gates que se movieron: complejo-agendar-calefont/G1 se arregló, complejo-agendar-calefont/G4 se arregló, complejo-no-quiere-email/G1 se arregló, complejo-no-quiere-email/G4 se arregló
- Delta por dimensión: grounding -0.07, policy -0.29, conversational +0.14, escalation +0.50, tone +0.50, closure +0.21
