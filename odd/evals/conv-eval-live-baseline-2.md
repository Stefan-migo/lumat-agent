# Evaluación conversacional — `live-baseline-2`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `fb5220fe741503adf5246b4df8576407d6dd36e6` · árbol sucio: **sí** · corrida: cliente simulado (--live)
- Corpus: `f903619e78bc` · KB: `91ca087a1130` (4 documentos)
- Juez: `deepseek-v4.1-flash` · inicio: 2026-10-23T16:37:26+00:00

> **No citable como baseline**: la corrida no selló un árbol limpio.

## Resumen

- Escenarios: **14** · pasan: **8**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 5 | 3 |
| complejo | 4 | 2 |
| supercomplejo | 5 | 3 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G6 | must_include_any | 3 |
| G4 | events_forbidden | 1 |
| G3 | events_required | 1 |
| G1 | state | 1 |

### Dimensiones del juez

| Dimensión | Media | n |
| --- | --- | --- |
| grounding | 2.71 | 14 |
| policy | 3.07 | 14 |
| conversational | 1.50 | 14 |
| escalation | 2.29 | 14 |
| tone | 2.71 | 14 |
| closure | 2.07 | 14 |

## Escenarios que no pasan

### `simple-horario-sabado` (simple)
- **G6 · must_include_any**: ninguna respuesta contiene: sabado, sábado, asesor, coordina
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-despedida` (simple)
- **G4 · events_forbidden**: se registró lo prohibido: unknown_intent
- **hard fail del juez**: La asistente no reconoce la despedida del cliente ('eso era todo') y responde con una nueva pregunta comercial, incumpliendo los dos hard fails definidos para este caso.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-dos-temas` (complejo)
- **G6 · must_include_any**: ninguna respuesta contiene: garantia, garantía, 6 meses, seis meses
- **hard fail del juez**: El bot pierde el referente del servicio consultado: tras «y eso cuanto de garantia tiene?» no identifica que se habla del lavado de red ni responde su garantía de 6 meses, dejando al cliente sin saber qué servicio tiene garantía y negando datos que sí existen en la base de conocimiento y la tarifa.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-no-quiere-email` (complejo)
- **hard fail del juez**: Se bloqueó el agendamiento insistiendo en el correo que el cliente rechazó explícitamente ('no te voy a dar mi correo, con el telefono basta' → '¿Cuál es tu correo electrónico?'), sin pedir nunca el teléfono ofrecido ni dar curso a la visita.
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
