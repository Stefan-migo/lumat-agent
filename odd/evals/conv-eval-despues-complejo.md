# Evaluación conversacional — `despues-complejo`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `bb7d7468d12669f2dba3a84e6343faf265e95a36` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `e618b6dfa573` · KB: `baa03df47194` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-16T23:22:10+00:00

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
| grounding | 2.69 | ±2 | 16 |
| policy | 2.56 | ±3 | 16 |
| conversational | 1.38 | ±1 | 16 |
| escalation | 2.38 | ±3 | 16 |
| tone | 2.88 | ±2 | 16 |
| closure | 1.75 | ±1 | 16 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `complejo-agendar-calefont` | complejo | 0.00 | ±2 |
| `complejo-dos-temas` | complejo | 0.00 | ±1 |
| `complejo-no-quiere-email` | complejo | 0.00 | ±1 |
| `complejo-fuera-de-cobertura-insiste` | complejo | 2.83 | ±3 |
| `real-dato-mas-pregunta` | complejo | 0.00 | ±1 |
| `real-arrendatario-no-decide` | complejo | 2.00 | ±1 |
| `real-multi-equipo-un-mensaje` | complejo | 3.50 | ±1 |
| `real-solo-sabados` | complejo | 1.83 | ±1 |
| `real-reagenda-familiar` | complejo | 0.00 | ±1 |
| `real-varias-reparaciones` | complejo | 3.83 | ±1 |
| `real-reagenda-mantencion` | complejo | 0.00 | ±2 |
| `real-revision-bano-ruidoso` | complejo | 0.83 | ±1 |
| `real-consulta-otros-equipos` | complejo | 0.00 | ±3 |
| `real-claudio-caldera-valvula` | complejo | 0.00 | ±2 |
| `real-diego-precio-y-duracion` | complejo | 0.00 | ±3 |
| `real-monica-diagnostico-no-confirmado` | complejo | 3.67 | ±1 |

## Escenarios que no pasan

### `complejo-agendar-calefont` (complejo)
- **hard fail del juez**: Pedir todos los datos antes de responder lo que el cliente preguntó: ante «necesito mantener mi calefont, vivo en ñuñoa» el bot pidió el nombre y luego el diagnóstico del equipo sin confirmar cobertura ni informar el valor de la mantención, y repitió la misma pregunta tras recibir los datos.
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
- **hard fail del juez**: Ignorar la pregunta que acompaña a los datos: la clienta preguntó "es factible que pases tipo 14 horas?" y "y mañana?" y el bot nunca respondió sobre el horario, cerrando con "No tienes visitas próximas para reagendar."
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-reagenda-familiar` (complejo)
- **hard fail del juez**: Ignorar la hora alternativa solicitada: la clienta propone las 9 am y el bot nunca la recoge ni la coordina, derivando a preguntas de diagnóstico del equipo.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-reagenda-mantencion` (complejo)
- **hard fail del juez**: Ignoró el motivo laboral que la clienta dio para cambiar la visita y cerró con 'No tienes visitas próximas para reagendar', sin reconocer el reagendamiento solicitado ni verificar disponibilidad u ofrecer alternativa.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-consulta-otros-equipos` (complejo)
- **hard fail del juez**: Afirmar que Lumat ofrece un servicio sin confirmarlo (bomba de calor de piscina) e inventar condiciones (caso registrado/abierto).
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-claudio-caldera-valvula` (complejo)
- **G4 · events_forbidden**: se registró lo prohibido: unknown_intent
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-diego-precio-y-duracion` (complejo)
- **hard fail del juez**: Ignoró la restricción de salida y regreso del cliente ("Tengo que salir a las 2, volviendo a las 4pm"): no la reconoció, no la comentó y repitió una pregunta sobre la falla del equipo.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: ninguno
- Delta por dimensión: grounding -0.48, policy -1.10, conversational -0.96, escalation -1.38, tone -0.96, closure -0.58
