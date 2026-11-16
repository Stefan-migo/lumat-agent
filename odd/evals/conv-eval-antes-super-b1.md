# Evaluación conversacional — `antes-super-b1`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `422703245590c037eb9b1e7891e2ebd5d4f4f5c9` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `e618b6dfa573` · KB: `baa03df47194` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-16T22:31:21+00:00

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
| grounding | 3.40 | ±2 | 5 |
| policy | 2.00 | ±4 | 5 |
| conversational | 1.00 | ±1 | 5 |
| escalation | 1.60 | ±1 | 5 |
| tone | 2.60 | ±2 | 5 |
| closure | 1.60 | ±1 | 5 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `real-cotizacion-fuera-catalogo` | supercomplejo | 3.00 | ±1 |
| `real-repuesto-agotado` | supercomplejo | 1.17 | ±4 |
| `real-cliente-experto` | supercomplejo | 3.33 | ±1 |
| `real-reclamo-real-si-deriva` | supercomplejo | 0.00 | ±1 |
| `real-maria-jesus-evaluacion-caldera` | supercomplejo | 1.33 | ±1 |

## Escenarios que no pasan

### `real-reclamo-real-si-deriva` (supercomplejo)
- **hard fail del juez**: Reabre la venta tras el cierre: ofrece agendar una visita y pide datos de captura a una clienta que acaba de terminar la relación, tratando la ruptura como consulta nueva.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: ninguno
- Delta por dimensión: grounding +0.73, policy -0.17, conversational -0.50, escalation -1.40, tone -0.73, closure -0.90
