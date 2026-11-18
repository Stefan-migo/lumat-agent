# Evaluación conversacional — `gates-respond`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `68a13b756368bdfc595c9cf9e509de6ca2e0d634` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `b47a55889dc3` · KB: `34670f5b3d75` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `sin juez (solo gates)` · inicio: 2026-11-17T19:55:35+00:00

## Resumen

- Escenarios: **3** · pasan: **2**
- Peor dimensión: `—`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 1 | 1 |
| supercomplejo | 2 | 1 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G7 | must_not_include | 1 |

### Dimensiones del juez

Sin juez en esta corrida: los gates deciden solos.

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `super-near-miss-lavadora` | supercomplejo | 0.00 | — |

## Escenarios que no pasan

### `super-near-miss-lavadora` (supercomplejo)
- **G7 · must_not_include**: apareció lo prohibido: si, reparamos lavadoras, sí, reparamos lavadoras
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: ninguno
