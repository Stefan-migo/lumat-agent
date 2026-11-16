# Evaluación conversacional — `antes-complejo`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `422703245590c037eb9b1e7891e2ebd5d4f4f5c9` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `e618b6dfa573` · KB: `baa03df47194` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-16T21:26:10+00:00

## Resumen

- Escenarios: **16** · pasan: **7**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| complejo | 16 | 7 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G1 | state | 2 |
| G10 | causes_required | 2 |
| G4 | events_forbidden | 2 |

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 2.81 | ±2 | 16 |
| policy | 2.69 | ±3 | 16 |
| conversational | 1.06 | ±2 | 16 |
| escalation | 2.44 | ±3 | 16 |
| tone | 3.00 | ±2 | 16 |
| closure | 1.50 | ±1 | 16 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `complejo-agendar-calefont` | complejo | 0.00 | ±1 |
| `complejo-dos-temas` | complejo | 0.00 | ±0 |
| `complejo-no-quiere-email` | complejo | 0.00 | ±2 |
| `complejo-fuera-de-cobertura-insiste` | complejo | 2.33 | ±1 |
| `real-dato-mas-pregunta` | complejo | 0.00 | ±2 |
| `real-arrendatario-no-decide` | complejo | 2.33 | ±3 |
| `real-multi-equipo-un-mensaje` | complejo | 3.33 | ±1 |
| `real-solo-sabados` | complejo | 1.83 | ±3 |
| `real-reagenda-familiar` | complejo | 0.00 | ±2 |
| `real-varias-reparaciones` | complejo | 2.83 | ±2 |
| `real-reagenda-mantencion` | complejo | 0.00 | ±2 |
| `real-revision-bano-ruidoso` | complejo | 0.83 | ±1 |
| `real-consulta-otros-equipos` | complejo | 0.00 | ±3 |
| `real-claudio-caldera-valvula` | complejo | 0.00 | ±2 |
| `real-diego-precio-y-duracion` | complejo | 0.00 | ±3 |
| `real-monica-diagnostico-no-confirmado` | complejo | 2.50 | ±2 |

## Escenarios que no pasan

### `complejo-agendar-calefont` (complejo)
- **hard fail del juez**: Se pidieron datos (nombre y diagnóstico del equipo) y se forzó la derivación antes de responder lo que la clienta pidió: confirmar cobertura en Ñuñoa y coordinar la mantención de calefont.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-dos-temas` (complejo)
- **G1 · state**: state=bot, esperado uno de: human
- **G10 · causes_required**: ninguna derivación esperada (esperaba persona); se registró: ninguna
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-no-quiere-email` (complejo)
- **G1 · state**: state=bot, esperado uno de: human
- **G10 · causes_required**: ninguna derivación esperada (esperaba booking_unavailable, persona); se registró: ninguna
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-dato-mas-pregunta` (complejo)
- **G4 · events_forbidden**: se registró lo prohibido: unknown_intent
- **hard fail del juez**: Ignorar la pregunta que acompaña a los datos: la clienta preguntó por «mañana» y por las «14 horas» y el asistente no respondió, repitiendo la pregunta sobre el equipo.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-reagenda-familiar` (complejo)
- **hard fail del juez**: Ignorar la hora alternativa solicitada: la clienta pidió las 9 am y el bot nunca la retomó ni la coordinó.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-reagenda-mantencion` (complejo)
- **hard fail del juez**: Ignorar el motivo laboral que la clienta dio para cambiar la visita: ante "Por temas laborales no estaré en casa hoy pm" responde "No tienes visitas próximas para reagendar", sin atender la razón ni ofrecer el reagendamiento al martes solicitado.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-consulta-otros-equipos` (complejo)
- **hard fail del juez**: Afirma que Lumat puede revisar/mantener una bomba de calor de piscina ("Podemos revisarlo"), servicio que no está confirmado en la base de conocimiento: cobertura inventada.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-claudio-caldera-valvula` (complejo)
- **G4 · events_forbidden**: se registró lo prohibido: unknown_intent
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-diego-precio-y-duracion` (complejo)
- **hard fail del juez**: Ignorar la restricción de salida y regreso del cliente: ante «Tengo que salir a las 2, volviendo a las 4pm» el asistente no la considera ni la retoma, y vuelve a preguntar por el diagnóstico dos veces.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: ninguno
- Delta por dimensión: grounding -0.60, policy -0.40, conversational -1.60, escalation -0.81, tone -0.67, closure -1.00
