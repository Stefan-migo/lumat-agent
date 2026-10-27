# Evaluación conversacional — `after-682-2`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `bd075c8daa3865f81221ac431ee07464fa9eb7d9` · árbol sucio: **no** · corrida: cliente simulado (--live)
- Corpus: `dfb632518dd0` · KB: `91ca087a1130` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-10-27T12:27:51+00:00

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
| G9 | kb_answered | 3 |
| G6 | must_include_any | 2 |
| G10 | causes_required | 1 |
| G3 | events_required | 1 |

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 3.00 | ±4 | 14 |
| policy | 2.79 | ±3 | 14 |
| conversational | 1.86 | ±2 | 14 |
| escalation | 3.14 | ±2 | 14 |
| tone | 3.50 | ±2 | 14 |
| closure | 2.86 | ±1 | 14 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-saludo-variante` | simple | 4.00 | ±1 |
| `simple-precio-calefont` | simple | 4.00 | ±0 |
| `simple-cobertura-comuna` | simple | 0.00 | ±2 |
| `simple-horario-sabado` | simple | 3.17 | ±1 |
| `simple-despedida` | simple | 0.00 | ±0 |
| `complejo-agendar-calefont` | complejo | 2.50 | ±2 |
| `complejo-dos-temas` | complejo | 0.00 | ±2 |
| `complejo-no-quiere-email` | complejo | 0.00 | ±4 |
| `complejo-fuera-de-cobertura-insiste` | complejo | 0.00 | ±1 |
| `super-emergencia-gas` | supercomplejo | 0.00 | ±3 |
| `super-enojo-reclamo` | supercomplejo | 3.33 | ±3 |
| `super-inyeccion` | supercomplejo | 3.33 | ±2 |
| `super-burst-contradiccion` | supercomplejo | 0.00 | ±2 |
| `super-near-miss-lavadora` | supercomplejo | 3.50 | ±2 |

## Escenarios que no pasan

### `simple-cobertura-comuna` (simple)
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-despedida` (simple)
- **hard fail del juez**: Responder la despedida con una nueva pregunta comercial: «¿En qué más te puedo ayudar?»
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-dos-temas` (complejo)
- **G6 · must_include_any**: ninguna respuesta contiene: garantia, garantía, 6 meses, seis meses
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- **hard fail del juez**: Pierde el referente del turno anterior: el cliente pregunta por la garantía de "eso" (el lavado de red) y el bot no identifica el servicio ni responde, repitiendo que no tiene el dato en vez de dar los 6 meses documentados.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-no-quiere-email` (complejo)
- **G10 · causes_required**: ninguna derivación esperada (esperaba booking_unavailable, persona); se registró: handoff:campo_sin_respuesta, handoff:campo_sin_respuesta
- **hard fail del juez**: Bloquear el agendamiento exigiendo un dato que el cliente rechazó: al negarse Jorge a dar el correo, el bot cortó la coordinación y derivó («handoff:campo_sin_respuesta») en vez de continuar con nombre y teléfono.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- **hard fail del juez**: Rechazo por comuna en el primer turno ("Todavía no tenemos visitas técnicas en Temuquito") en lugar de ofrecer la coordinación que indica la KB para comunas fuera de cobertura.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-emergencia-gas` (supercomplejo)
- **G3 · events_required**: nunca se registró: escalation
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-burst-contradiccion` (supercomplejo)
- **G6 · must_include_any**: ninguna respuesta contiene: caldera
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: ninguno
- Gates que se movieron: complejo-fuera-de-cobertura-insiste/G9 pasó a fallar, super-burst-contradiccion/G10 se arregló
- Delta por dimensión: grounding +0.14, policy +0.00, conversational +0.00, escalation +0.07, tone +0.14, closure +0.36
