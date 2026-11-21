# Evaluación conversacional — `captura-sliceAB9`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `cf49703cd0232075a0016d6f08086e2b0a2b9b55` · árbol sucio: **sí** · corrida: cliente scripted
- Corpus: `8adb94421f45` · KB: `34670f5b3d75` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-20T22:06:50+00:00

> **No citable como baseline**: el árbol no estaba limpio.

## Resumen

- Escenarios: **4** · pasan: **4**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| complejo | 3 | 3 |
| supercomplejo | 1 | 1 |

### Gates que fallaron

Ninguno.

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 2.75 | ±2 | 4 |
| policy | 2.25 | ±1 | 4 |
| conversational | 0.50 | ±1 | 4 |
| escalation | 2.00 | ±1 | 4 |
| tone | 3.25 | ±1 | 4 |
| closure | 1.50 | ±1 | 4 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `real-solo-sabados` | complejo | 2.50 | ±1 |
| `real-repuesto-agotado` | supercomplejo | 1.17 | ±2 |
| `real-varias-reparaciones` | complejo | 1.33 | ±1 |
| `real-reagenda-mantencion` | complejo | 3.17 | ±1 |

## Escenarios que no pasan

Ninguno.

## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: real-repuesto-agotado, real-reagenda-mantencion
- Delta por dimensión: grounding +0.25, policy +0.25, conversational +0.00, escalation +0.50, tone +0.25, closure +0.00
