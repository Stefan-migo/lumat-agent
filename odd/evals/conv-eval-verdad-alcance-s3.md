# Evaluación conversacional — `verdad-alcance-s3`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `248f160cdd81a18d914d5253e058f9e96ef4464d` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `8adb94421f45` · KB: `34670f5b3d75` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 2 llamada(s) por escenario (mediana) · inicio: 2026-11-18T17:39:10+00:00

## Resumen

- Escenarios: **2** · pasan: **2**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 1 | 1 |
| complejo | 1 | 1 |

### Gates que fallaron

Ninguno.

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 3.75 | ±1 | 2 |
| policy | 3.50 | ±1 | 2 |
| conversational | 1.25 | ±2 | 2 |
| escalation | 2.50 | ±0 | 2 |
| tone | 3.50 | ±1 | 2 |
| closure | 2.25 | ±1 | 2 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `real-vocabulario-impreciso` | simple | 3.00 | ±2 |
| `real-consulta-otros-equipos` | complejo | 2.58 | ±1 |

## Escenarios que no pasan

Ninguno.

## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: ninguno
- Delta por dimensión: grounding +1.25, policy +1.00, conversational -0.75, escalation +0.00, tone +0.50, closure +0.25
