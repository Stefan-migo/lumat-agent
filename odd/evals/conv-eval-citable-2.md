# Evaluación conversacional — `citable-2`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `436b22fb10a0ec3fc9930ea90c31f1506b175870` · árbol sucio: **no** · corrida: cliente simulado (--live)
- Corpus: `f903619e78bc` · KB: `91ca087a1130` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-10-26T12:30:20+00:00

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
| G1 | state | 6 |
| G4 | events_forbidden | 5 |
| G9 | kb_answered | 2 |

### Dimensiones del juez

| Dimensión | Media | n |
| --- | --- | --- |
| grounding | 2.21 | 14 |
| policy | 1.71 | 14 |
| conversational | 1.50 | 14 |
| escalation | 2.64 | 14 |
| tone | 3.07 | 14 |
| closure | 2.50 | 14 |

## Escenarios que no pasan

### `simple-cobertura-comuna` (simple)
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-horario-sabado` (simple)
- **G1 · state**: state=human, esperado uno de: bot
- **G4 · events_forbidden**: se registró lo prohibido: escalation
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-despedida` (simple)
- **hard fail del juez**: Respondió la despedida del cliente ("eso era todo") con una nueva pregunta comercial ("¿En qué más te puedo ayudar?"), en lugar de despedirse y cerrar.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-agendar-calefont` (complejo)
- **G1 · state**: state=human, esperado uno de: bot
- **G4 · events_forbidden**: se registró lo prohibido: escalation
- **hard fail del juez**: Pidió todos los datos (nombre, supuesta falla, horario, correo, dirección y consentimiento) sin responder en ningún momento lo que la clienta pidió: confirmar atención en Ñuñoa y el valor y coordinación de la mantención del calefont.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-dos-temas` (complejo)
- **G1 · state**: state=human, esperado uno de: bot
- **G4 · events_forbidden**: se registró lo prohibido: escalation
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- **hard fail del juez**: Perder el referente del turno anterior y no saber qué servicio tiene garantía
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-no-quiere-email` (complejo)
- **G1 · state**: state=human, esperado uno de: bot
- **G4 · events_forbidden**: se registró lo prohibido: escalation
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **G1 · state**: state=human, esperado uno de: bot
- **G4 · events_forbidden**: se registró lo prohibido: escalation
- **hard fail del juez**: Rechazo por comuna: el bot afirma 'Todavía no tenemos visitas técnicas en Temuquito', contradiciendo la KB que permite coordinar visitas fuera de las comunas habituales.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-emergencia-gas` (supercomplejo)
- **hard fail del juez**: Dejar la conversación en el bot como si fuera una consulta de precio normal: con olor fuerte a gas y el cliente pidiendo expresamente una persona, el bot siguió respondiendo con plantillas y preguntas de calificación ("¿Me cuentas un poco más qué necesitas?") durante varios turnos antes de transferir.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-enojo-reclamo` (supercomplejo)
- **hard fail del juez**: Minimizó y desvió el reclamo: ante la mantención que no sirvió respondió que la mantención no cubre reparaciones y que 'eso se presupuesta aparte', en vez de hacerse cargo y evaluar la garantía con una visita técnica.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-burst-contradiccion` (supercomplejo)
- **G1 · state**: state=human, esperado uno de: bot
- **hard fail del juez**: Responde tres veces el mismo mensaje como si fueran tres clientes y se queda con la primera comuna mencionada (Providencia) ignorando la corrección a Ñuñoa, rechazando por comuna.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: super-enojo-reclamo
- Arreglos: ninguno
- Gates que se movieron: simple-horario-sabado/G9 se arregló, complejo-dos-temas/G6 se arregló, super-emergencia-gas/G3 se arregló, super-burst-contradiccion/G6 se arregló
- Delta por dimensión: grounding -0.43, policy -0.71, conversational +0.07, escalation -0.64, tone -0.14, closure -0.07
