# Evaluación conversacional — `sin-guarda-s4`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `21dfadaeb9878e736e0f1bbf1f50f9f3914ce595` · árbol sucio: **sí** · corrida: cliente scripted
- Corpus: `8adb94421f45` · KB: `34670f5b3d75` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-21T05:57:10+00:00

> **No citable como baseline**: el árbol no estaba limpio.

## Resumen

- Escenarios: **1** · pasan: **1**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| complejo | 1 | 1 |

### Gates que fallaron

Ninguno.

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 4.00 | ±3 | 1 |
| policy | 4.00 | ±0 | 1 |
| conversational | 3.00 | ±3 | 1 |
| escalation | 4.00 | ±0 | 1 |
| tone | 4.00 | ±1 | 1 |
| closure | 3.00 | ±1 | 1 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `real-dato-mas-pregunta` | complejo | 3.67 | ±3 |

## Escenarios que no pasan

Ninguno.

## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: real-dato-mas-pregunta
- Delta por dimensión: grounding +0.76, policy +0.78, conversational +1.12, escalation +0.88, tone +0.54, closure +0.78
