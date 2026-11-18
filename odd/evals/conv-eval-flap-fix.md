# Evaluación conversacional — `flap-fix`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `dc530d8334d39da8e722a7e9b8fa13f0d9872069` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `b47a55889dc3` · KB: `baa03df47194` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `sin juez (solo gates)` · inicio: 2026-11-17T19:06:33+00:00

## Resumen

- Escenarios: **2** · pasan: **1**
- Peor dimensión: `—`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 1 | 1 |
| supercomplejo | 1 | 0 |

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
- Arreglos: simple-cobertura-comuna
- Gates que se movieron: simple-cobertura-comuna/G6 se arregló
