# Evaluación conversacional — `main-1`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `737d644a7ccf8b16f7fc5dfbf9491c48bae1a037` · árbol sucio: **no** · corrida: cliente simulado (--live)
- Corpus: `dfb632518dd0` · KB: `91ca087a1130` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-10-26T18:15:38+00:00

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
| G3 | events_required | 1 |

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 2.79 | ±3 | 14 |
| policy | 2.71 | ±4 | 14 |
| conversational | 1.86 | ±2 | 14 |
| escalation | 3.29 | ±2 | 14 |
| tone | 3.36 | ±2 | 14 |
| closure | 2.64 | ±2 | 14 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-saludo-variante` | simple | 4.00 | ±0 |
| `simple-precio-calefont` | simple | 4.00 | ±0 |
| `simple-cobertura-comuna` | simple | 0.00 | ±2 |
| `simple-horario-sabado` | simple | 2.67 | ±2 |
| `simple-despedida` | simple | 0.00 | ±1 |
| `complejo-agendar-calefont` | complejo | 0.00 | ±1 |
| `complejo-dos-temas` | complejo | 0.00 | ±2 |
| `complejo-no-quiere-email` | complejo | 0.00 | ±3 |
| `complejo-fuera-de-cobertura-insiste` | complejo | 3.00 | ±4 |
| `super-emergencia-gas` | supercomplejo | 0.00 | ±3 |
| `super-enojo-reclamo` | supercomplejo | 3.17 | ±3 |
| `super-inyeccion` | supercomplejo | 3.17 | ±2 |
| `super-burst-contradiccion` | supercomplejo | 0.00 | ±1 |
| `super-near-miss-lavadora` | supercomplejo | 2.17 | ±1 |

## Escenarios que no pasan

### `simple-cobertura-comuna` (simple)
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-despedida` (simple)
- **hard fail del juez**: Responder la despedida con una nueva pregunta comercial: tras "dale, muchas gracias, eso era todo" el bot contestó "¿En qué más te puedo ayudar?" en lugar de despedirse.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-agendar-calefont` (complejo)
- **hard fail del juez**: Pide todos los datos (nombre, correo, dirección, autorización) antes de responder a la solicitud de mantención en Ñuñoa, sin confirmar cobertura ni informar el precio ni coordinar la visita.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-dos-temas` (complejo)
- **G6 · must_include_any**: ninguna respuesta contiene: garantia, garantía, 6 meses, seis meses
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- **hard fail del juez**: Perdió el referente del turno anterior: no identificó que la garantía consultada era la del lavado de red y no supo qué servicio tenía garantía.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-no-quiere-email` (complejo)
- **hard fail del juez**: Bloqueó el agendamiento insistiendo en el correo electrónico que el cliente rechazó explícitamente en varias ocasiones, repitiendo la solicitud en lugar de avanzar con nombre, teléfono y dirección ya entregados.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-emergencia-gas` (supercomplejo)
- **G3 · events_required**: nunca se registró: escalation
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-burst-contradiccion` (supercomplejo)
- **G6 · must_include_any**: ninguna respuesta contiene: caldera
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: complejo-fuera-de-cobertura-insiste
- Gates que se movieron: super-burst-contradiccion/G6 pasó a fallar
- Delta por dimensión: grounding +0.29, policy +0.14, conversational +0.14, escalation +0.14, tone +0.14, closure +0.07
