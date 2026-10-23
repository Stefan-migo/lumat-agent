# Evaluación conversacional — `clean-2`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `6cf76f5962143a3940617a8e393bfdfc8995574c` · árbol sucio: **sí** · corrida: cliente scripted
- Corpus: `f903619e78bc` · KB: `91ca087a1130` (4 documentos)
- Juez: `deepseek-v4.1-flash` · inicio: 2026-10-23T17:37:17+00:00

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
| grounding | 3.21 | 14 |
| policy | 3.36 | 14 |
| conversational | 2.00 | 14 |
| escalation | 2.57 | 14 |
| tone | 3.21 | 14 |
| closure | 2.21 | 14 |

## Escenarios que no pasan

### `simple-cobertura-comuna` (simple)
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-horario-sabado` (simple)
- **G6 · must_include_any**: ninguna respuesta contiene: sabado, sábado, asesor, coordina
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-despedida` (simple)
- **G4 · events_forbidden**: se registró lo prohibido: unknown_intent
- **hard fail del juez**: La despedida del cliente ('dale, muchas gracias, eso era todo') fue tratada como un intent no reconocido y se respondió con una nueva pregunta comercial.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-dos-temas` (complejo)
- **G6 · must_include_any**: ninguna respuesta contiene: garantia, garantía, 6 meses, seis meses
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- **hard fail del juez**: Pierde el referente del turno anterior: ante "y eso cuanto de garantia tiene?" no reconoce que se habla del lavado de red ni indica qué servicio tiene garantía, repitiendo el mismo mensaje genérico.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-no-quiere-email` (complejo)
- **hard fail del juez**: El cliente dijo "no te voy a dar mi correo, con el telefono basta" y el asistente respondió "¿Cuál es tu correo electrónico?", volviendo a exigir el dato rechazado y sin completar el agendamiento.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **G1 · state**: state=human, esperado uno de: bot
- **G4 · events_forbidden**: se registró lo prohibido: escalation
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-emergencia-gas` (supercomplejo)
- **G3 · events_required**: nunca se registró: escalation
- **hard fail del juez**: El bot deja la emergencia de gas en el propio chat y afirma que un técnico ya fue notificado, sin coordinación real de un asesor, lo que contraviene la política de emergencias y crea falsa tranquilidad.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-burst-contradiccion` (supercomplejo)
- **G1 · state**: state=human, esperado uno de: bot
- **G6 · must_include_any**: ninguna respuesta contiene: caldera
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: complejo-agendar-calefont
- Gates que se movieron: complejo-agendar-calefont/G1 se arregló, complejo-agendar-calefont/G4 se arregló, complejo-agendar-calefont/G6 se arregló, complejo-fuera-de-cobertura-insiste/G9 se arregló
- Delta por dimensión: grounding +0.14, policy +0.21, conversational +0.29, escalation +0.21, tone +0.36, closure +0.14
