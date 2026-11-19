# Evaluación conversacional — `agenda-house-8`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `c49417d007589a985d4f3e6dfc4552aae832d933` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `8adb94421f45` · KB: `34670f5b3d75` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-19T15:26:34+00:00

## Resumen

- Escenarios: **3** · pasan: **3**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| complejo | 3 | 3 |

### Gates que fallaron

Ninguno.

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 3.00 | ±2 | 3 |
| policy | 3.00 | ±3 | 3 |
| conversational | 1.00 | ±1 | 3 |
| escalation | 3.00 | ±2 | 3 |
| tone | 3.67 | ±2 | 3 |
| closure | 1.33 | ±2 | 3 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `real-dato-mas-pregunta` | complejo | 2.67 | ±2 |
| `real-reagenda-familiar` | complejo | 2.00 | ±3 |
| `real-diego-precio-y-duracion` | complejo | 2.83 | ±2 |

## Escenarios que no pasan

Ninguno.

## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: real-reagenda-familiar
- Delta por dimensión: grounding -0.33, policy +0.33, conversational +0.00, escalation +1.00, tone +0.33, closure +0.00
