# Evaluación conversacional — `agenda-pref-2`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `b83af012f149fb33e0e41c56a9404edc35c13fb4` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `1eab60be927d` · KB: `6fbd06e66d2a` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-10-28T01:10:38+00:00

## Resumen

- Escenarios: **4** · pasan: **2**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 2 | 1 |
| complejo | 2 | 1 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G6 | must_include_any | 1 |
| G1 | state | 1 |
| G10 | causes_required | 1 |

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 3.50 | ±1 | 4 |
| policy | 2.75 | ±3 | 4 |
| conversational | 1.00 | ±0 | 4 |
| escalation | 1.75 | ±4 | 4 |
| tone | 3.00 | ±1 | 4 |
| closure | 1.75 | ±1 | 4 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-horario-sabado` | simple | 3.50 | ±1 |
| `simple-dia-especifico` | simple | 0.00 | ±3 |
| `complejo-agendar-calefont` | complejo | 1.50 | ±1 |
| `complejo-no-quiere-email` | complejo | 0.00 | ±4 |

## Escenarios que no pasan

### `simple-dia-especifico` (simple)
- **G6 · must_include_any**: ninguna respuesta contiene: horario, visita, agend
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-no-quiere-email` (complejo)
- **G1 · state**: state=bot, esperado uno de: human
- **G10 · causes_required**: ninguna derivación esperada (esperaba booking_unavailable, persona); se registró: ninguna
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: complejo-agendar-calefont
- Gates que se movieron: simple-dia-especifico/G6 pasó a fallar
- Delta por dimensión: grounding +1.00, policy +0.75, conversational +1.00, escalation +1.75, tone +1.50, closure +1.75
