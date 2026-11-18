# Evaluación conversacional — `verdad-alcance-s1s2`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `98489e6f5eb88517c88256a74429f4c62e4f481b` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `8adb94421f45` · KB: `34670f5b3d75` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 2 llamada(s) por escenario (mediana) · inicio: 2026-11-18T17:22:44+00:00

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
| grounding | 2.50 | ±3 | 2 |
| policy | 2.50 | ±2 | 2 |
| conversational | 2.00 | ±0 | 2 |
| escalation | 2.50 | ±1 | 2 |
| tone | 3.00 | ±0 | 2 |
| closure | 2.00 | ±0 | 2 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `real-vocabulario-impreciso` | simple | 2.83 | ±2 |
| `real-consulta-otros-equipos` | complejo | 2.00 | ±3 |

## Escenarios que no pasan

Ninguno.

## Contra la corrida anterior

Sin corrida previa: esta es la línea base.
