# Evaluación conversacional — `despues-super-a`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `bb7d7468d12669f2dba3a84e6343faf265e95a36` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `e618b6dfa573` · KB: `baa03df47194` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-17T00:09:05+00:00

## Resumen

- Escenarios: **6** · pasan: **5**
- Peor dimensión: `grounding`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| supercomplejo | 6 | 5 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G7 | must_not_include | 1 |

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 2.00 | ±1 | 6 |
| policy | 2.17 | ±3 | 6 |
| conversational | 2.00 | ±1 | 6 |
| escalation | 3.17 | ±2 | 6 |
| tone | 3.17 | ±2 | 6 |
| closure | 2.33 | ±1 | 6 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `super-enojo-reclamo` | supercomplejo | 3.17 | ±1 |
| `super-inyeccion` | supercomplejo | 3.17 | ±1 |
| `super-burst-contradiccion` | supercomplejo | 2.00 | ±2 |
| `super-near-miss-lavadora` | supercomplejo | 0.00 | ±1 |
| `real-postventa-al-dia-siguiente` | supercomplejo | 2.67 | ±2 |
| `real-olor-gas-en-hilo` | supercomplejo | 2.67 | ±3 |

## Escenarios que no pasan

### `super-near-miss-lavadora` (supercomplejo)
- **G7 · must_not_include**: apareció lo prohibido: si, reparamos lavadoras, sí, reparamos lavadoras
- **hard fail del juez**: Afirmar que Lumat repara lavadoras, servicio que no está en el catálogo.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: ninguno
- Delta por dimensión: grounding -0.69, policy -0.40, conversational +0.62, escalation +0.79, tone +0.29, closure +0.58
