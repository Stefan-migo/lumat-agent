# Evaluación conversacional — `brain-boundary`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `7e26ed64007a0d38c43fb3a288489c3c1396c9d1` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `e618b6dfa573` · KB: `baa03df47194` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 1 llamada(s) por escenario (mediana) · inicio: 2026-11-17T11:46:15+00:00

## Resumen

- Escenarios: **2** · pasan: **2**
- Peor dimensión: `grounding`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| supercomplejo | 2 | 2 |

### Gates que fallaron

Ninguno.

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 1.50 | ±0 | 2 |
| policy | 3.00 | ±0 | 2 |
| conversational | 2.50 | ±0 | 2 |
| escalation | 3.50 | ±0 | 2 |
| tone | 3.50 | ±0 | 2 |
| closure | 2.50 | ±0 | 2 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `real-caldera-urgencia` | supercomplejo | 2.33 | ±0 |
| `real-fuga-gas-bodega` | supercomplejo | 3.17 | ±0 |

## Escenarios que no pasan

Ninguno.

## Contra la corrida anterior

Sin corrida previa: esta es la línea base.
