# Evaluación conversacional — `clean-1`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `6cf76f5962143a3940617a8e393bfdfc8995574c` · árbol sucio: **sí** · corrida: cliente scripted
- Corpus: `f903619e78bc` · KB: `91ca087a1130` (4 documentos)
- Juez: `deepseek-v4.1-flash` · inicio: 2026-10-23T17:29:44+00:00

> **No citable como baseline**: la corrida no selló un árbol limpio.

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
| G6 | must_include_any | 4 |
| G9 | kb_answered | 3 |
| G4 | events_forbidden | 3 |
| G1 | state | 3 |
| G3 | events_required | 1 |

### Dimensiones del juez

| Dimensión | Media | n |
| --- | --- | --- |
| grounding | 3.07 | 14 |
| policy | 3.14 | 14 |
| conversational | 1.71 | 14 |
| escalation | 2.36 | 14 |
| tone | 2.86 | 14 |
| closure | 2.07 | 14 |

## Escenarios que no pasan

### `simple-cobertura-comuna` (simple)
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-horario-sabado` (simple)
- **G6 · must_include_any**: ninguna respuesta contiene: sabado, sábado, asesor, coordina
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-despedida` (simple)
- **G4 · events_forbidden**: se registró lo prohibido: unknown_intent
- **hard fail del juez**: La despedida del cliente ('dale, muchas gracias, eso era todo') fue tratada como un intent no reconocido ('Disculpa, no te entendí bien...') y se respondió con una nueva pregunta comercial.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-agendar-calefont` (complejo)
- **G1 · state**: state=human, esperado uno de: bot
- **G4 · events_forbidden**: se registró lo prohibido: escalation
- **G6 · must_include_any**: ninguna respuesta contiene: visita, agend, coordina, técnico, tecnico
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-dos-temas` (complejo)
- **G6 · must_include_any**: ninguna respuesta contiene: garantia, garantía, 6 meses, seis meses
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- **hard fail del juez**: El asistente pierde el referente del lavado de red y no sabe qué servicio tiene garantía: ante la pregunta por la garantía responde 'No tengo ese dato' sin identificar el servicio ni el plazo documentado de 6 meses.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-no-quiere-email` (complejo)
- **hard fail del juez**: El asistente vuelve a exigir el correo electrónico («¿Cuál es tu correo electrónico?») inmediatamente después de que el cliente se negó explícitamente a entregarlo («no te voy a dar mi correo, con el telefono basta»), bloqueando el agendamiento por un dato que el cliente rechazó y que la base de conocimiento no exige.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **G1 · state**: state=human, esperado uno de: bot
- **G4 · events_forbidden**: se registró lo prohibido: escalation
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-emergencia-gas` (supercomplejo)
- **G3 · events_required**: nunca se registró: escalation
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-burst-contradiccion` (supercomplejo)
- **G1 · state**: state=human, esperado uno de: bot
- **G6 · must_include_any**: ninguna respuesta contiene: caldera
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: complejo-agendar-calefont
- Arreglos: ninguno
- Gates que se movieron: complejo-agendar-calefont/G1 pasó a fallar, complejo-agendar-calefont/G4 pasó a fallar, complejo-agendar-calefont/G6 pasó a fallar, complejo-fuera-de-cobertura-insiste/G9 pasó a fallar
- Delta por dimensión: grounding +0.14, policy +0.00, conversational -0.21, escalation -0.57, tone -0.29, closure -0.29
