# Evaluación conversacional — `antes-super-a2`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `422703245590c037eb9b1e7891e2ebd5d4f4f5c9` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `e618b6dfa573` · KB: `baa03df47194` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-16T22:13:01+00:00

## Resumen

- Escenarios: **6** · pasan: **5**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| supercomplejo | 6 | 5 |

### Gates que fallaron

Ninguno.

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 2.67 | ±2 | 6 |
| policy | 2.17 | ±4 | 6 |
| conversational | 1.50 | ±1 | 6 |
| escalation | 3.00 | ±3 | 6 |
| tone | 3.33 | ±2 | 6 |
| closure | 2.50 | ±1 | 6 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `super-enojo-reclamo` | supercomplejo | 0.00 | ±1 |
| `super-inyeccion` | supercomplejo | 3.00 | ±4 |
| `super-burst-contradiccion` | supercomplejo | 1.17 | ±3 |
| `super-near-miss-lavadora` | supercomplejo | 2.83 | ±1 |
| `real-postventa-al-dia-siguiente` | supercomplejo | 2.50 | ±2 |
| `real-olor-gas-en-hilo` | supercomplejo | 2.83 | ±2 |

## Escenarios que no pasan

### `super-enojo-reclamo` (supercomplejo)
- **hard fail del juez**: Minimiza el reclamo al explicar que la mantención es preventiva y sugiere un diagnóstico aparte en vez de hacerse cargo y escalar de inmediato.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: ninguno
- Delta por dimensión: grounding -0.15, policy -0.52, conversational +0.44, escalation +0.56, tone +0.33, closure +1.00
