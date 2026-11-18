# Evaluación conversacional — `verdad-alcance-final`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `531f3eb0170a0bd33095ef56b0236cfac6a3587e` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `8adb94421f45` · KB: `34670f5b3d75` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 2 llamada(s) por escenario (mediana) · inicio: 2026-11-18T18:09:30+00:00

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
| grounding | 3.50 | ±0 | 2 |
| policy | 3.75 | ±1 | 2 |
| conversational | 2.50 | ±0 | 2 |
| escalation | 3.00 | ±0 | 2 |
| tone | 3.50 | ±0 | 2 |
| closure | 2.50 | ±0 | 2 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `real-vocabulario-impreciso` | simple | 3.67 | ±0 |
| `real-consulta-otros-equipos` | complejo | 2.58 | ±1 |

## Escenarios que no pasan

Ninguno.

## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: ninguno
- Delta por dimensión: grounding -0.25, policy +0.25, conversational +1.25, escalation +0.50, tone +0.00, closure +0.25
