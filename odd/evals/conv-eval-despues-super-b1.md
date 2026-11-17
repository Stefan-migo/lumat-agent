# Evaluación conversacional — `despues-super-b1`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `bb7d7468d12669f2dba3a84e6343faf265e95a36` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `e618b6dfa573` · KB: `baa03df47194` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-17T00:24:35+00:00

## Resumen

- Escenarios: **5** · pasan: **4**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| supercomplejo | 5 | 4 |

### Gates que fallaron

Ninguno.

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 3.20 | ±2 | 5 |
| policy | 2.60 | ±1 | 5 |
| conversational | 0.60 | ±2 | 5 |
| escalation | 2.00 | ±3 | 5 |
| tone | 3.00 | ±1 | 5 |
| closure | 1.40 | ±1 | 5 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `real-cotizacion-fuera-catalogo` | supercomplejo | 2.50 | ±2 |
| `real-repuesto-agotado` | supercomplejo | 1.17 | ±2 |
| `real-cliente-experto` | supercomplejo | 3.00 | ±2 |
| `real-reclamo-real-si-deriva` | supercomplejo | 0.00 | ±2 |
| `real-maria-jesus-evaluacion-caldera` | supercomplejo | 2.67 | ±3 |

## Escenarios que no pasan

### `real-reclamo-real-si-deriva` (supercomplejo)
- **hard fail del juez**: Ofreció coordinar una visita y pedir datos de captura a un cliente que acababa de cerrar la relación, tratando la ruptura como una consulta nueva.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: ninguno
- Delta por dimensión: grounding +1.20, policy +0.43, conversational -1.40, escalation -1.17, tone -0.17, closure -0.93
