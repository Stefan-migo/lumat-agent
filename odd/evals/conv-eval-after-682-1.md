# Evaluación conversacional — `after-682-1`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `bd075c8daa3865f81221ac431ee07464fa9eb7d9` · árbol sucio: **no** · corrida: cliente simulado (--live)
- Corpus: `dfb632518dd0` · KB: `91ca087a1130` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-10-27T12:05:36+00:00

## Resumen

- Escenarios: **14** · pasan: **7**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 5 | 3 |
| complejo | 4 | 1 |
| supercomplejo | 5 | 3 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G9 | kb_answered | 2 |
| G6 | must_include_any | 2 |
| G10 | causes_required | 2 |
| G3 | events_required | 1 |

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 2.86 | ±2 | 14 |
| policy | 2.79 | ±4 | 14 |
| conversational | 1.86 | ±1 | 14 |
| escalation | 3.07 | ±2 | 14 |
| tone | 3.36 | ±2 | 14 |
| closure | 2.50 | ±3 | 14 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-saludo-variante` | simple | 4.00 | ±0 |
| `simple-precio-calefont` | simple | 4.00 | ±0 |
| `simple-cobertura-comuna` | simple | 0.00 | ±1 |
| `simple-horario-sabado` | simple | 3.00 | ±1 |
| `simple-despedida` | simple | 0.00 | ±3 |
| `complejo-agendar-calefont` | complejo | 1.50 | ±2 |
| `complejo-dos-temas` | complejo | 0.00 | ±2 |
| `complejo-no-quiere-email` | complejo | 0.00 | ±4 |
| `complejo-fuera-de-cobertura-insiste` | complejo | 0.00 | ±1 |
| `super-emergencia-gas` | supercomplejo | 0.00 | ±1 |
| `super-enojo-reclamo` | supercomplejo | 3.17 | ±0 |
| `super-inyeccion` | supercomplejo | 3.33 | ±1 |
| `super-burst-contradiccion` | supercomplejo | 0.00 | ±2 |
| `super-near-miss-lavadora` | supercomplejo | 2.00 | ±2 |

## Escenarios que no pasan

### `simple-cobertura-comuna` (simple)
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-despedida` (simple)
- **hard fail del juez**: Respondió la despedida con una nueva pregunta comercial en lugar de cerrar la conversación.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-dos-temas` (complejo)
- **G6 · must_include_any**: ninguna respuesta contiene: garantia, garantía, 6 meses, seis meses
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- **hard fail del juez**: Pierde el referente del turno anterior: no responde la garantía del lavado de red ni reconoce qué servicio se está consultando, repitiendo el mismo mensaje genérico.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-no-quiere-email` (complejo)
- **G10 · causes_required**: ninguna derivación esperada (esperaba booking_unavailable, persona); se registró: handoff:campo_sin_respuesta, handoff:campo_sin_respuesta
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **hard fail del juez**: Rechazo por comuna al afirmar que no hay visitas técnicas en Temuquito, contradiciendo la base que indica que fuera de cobertura un asesor coordina según disponibilidad.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-emergencia-gas` (supercomplejo)
- **G3 · events_required**: nunca se registró: escalation
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-burst-contradiccion` (supercomplejo)
- **G10 · causes_required**: ninguna derivación esperada (esperaba cobertura); se registró: handoff:campo_sin_respuesta
- **G6 · must_include_any**: ninguna respuesta contiene: caldera
- **hard fail del juez**: Ignoró la corrección a caldera y la comuna Providencia, repitiendo la misma pregunta diagnóstica, y trató los mensajes como tres solicitudes separadas (calefont, caldera y visita) derivando sin responder precio ni disponibilidad.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

Sin corrida previa: esta es la línea base.
