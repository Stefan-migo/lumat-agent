# Evaluación conversacional — `s6-refusal-fix`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `e7c4cca170b6fa8dcb00e0a9bfcf398dd704b5b8` · árbol sucio: **sí** · corrida: cliente scripted
- Corpus: `dfb632518dd0` · KB: `91ca087a1130` (4 documentos)
- Bot: `deepseek` / `deepseek-chat`
- Juez: `sin juez (solo gates)` · inicio: 2026-10-27T20:47:19+00:00

> **No citable como baseline**: el árbol no estaba limpio.

## Resumen

- Escenarios: **1** · pasan: **0**
- Peor dimensión: `—`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| complejo | 1 | 0 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G1 | state | 1 |
| G10 | causes_required | 1 |

### Dimensiones del juez

Sin juez en esta corrida: los gates deciden solos.

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `complejo-no-quiere-email` | complejo | 0.00 | — |

## Escenarios que no pasan

### `complejo-no-quiere-email` (complejo)
- **G1 · state**: state=bot, esperado uno de: human
- **G10 · causes_required**: ninguna derivación esperada (esperaba booking_unavailable, persona); se registró: ninguna
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: ninguno
