# Evaluación conversacional — `gates-42-final2`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `113dc11b39791e2ac3b9fb473aaf4f3df603ce87` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `b47a55889dc3` · KB: `34670f5b3d75` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `sin juez (solo gates)` · inicio: 2026-11-18T01:06:26+00:00

## Resumen

- Escenarios: **42** · pasan: **41**
- Peor dimensión: `—`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 12 | 12 |
| complejo | 16 | 16 |
| supercomplejo | 14 | 13 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G6 | must_include_any | 1 |

### Dimensiones del juez

Sin juez en esta corrida: los gates deciden solos.

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `real-maria-jesus-evaluacion-caldera` | supercomplejo | 0.00 | — |

## Escenarios que no pasan

### `real-maria-jesus-evaluacion-caldera` (supercomplejo)
- **G6 · must_include_any**: ninguna respuesta contiene: evaluación, evaluacion, revis
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: ninguno
