# Evaluación conversacional — `gates-42`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `dc530d8334d39da8e722a7e9b8fa13f0d9872069` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `b47a55889dc3` · KB: `baa03df47194` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `sin juez (solo gates)` · inicio: 2026-11-17T18:57:54+00:00

## Resumen

- Escenarios: **42** · pasan: **40**
- Peor dimensión: `—`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 12 | 11 |
| complejo | 16 | 16 |
| supercomplejo | 14 | 13 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G6 | must_include_any | 1 |
| G7 | must_not_include | 1 |

### Dimensiones del juez

Sin juez en esta corrida: los gates deciden solos.

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-cobertura-comuna` | simple | 0.00 | — |
| `super-near-miss-lavadora` | supercomplejo | 0.00 | — |

## Escenarios que no pasan

### `simple-cobertura-comuna` (simple)
- **G6 · must_include_any**: ninguna respuesta contiene: asesor, coordina, cuentame, cuéntame
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-near-miss-lavadora` (supercomplejo)
- **G7 · must_not_include**: apareció lo prohibido: si, reparamos lavadoras, sí, reparamos lavadoras
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: ninguno
