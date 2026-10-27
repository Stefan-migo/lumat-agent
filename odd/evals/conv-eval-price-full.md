# Evaluación conversacional — `price-full`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `6b8669f05e14f629a9817e10ab3ce737366ec3db` · árbol sucio: **sí** · corrida: cliente scripted
- Corpus: `dfb632518dd0` · KB: `91ca087a1130` (4 documentos)
- Bot: `deepseek` / `deepseek-chat`
- Juez: `sin juez (solo gates)` · inicio: 2026-10-27T21:50:28+00:00

> **No citable como baseline**: el árbol no estaba limpio.

## Resumen

- Escenarios: **14** · pasan: **12**
- Peor dimensión: `—`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 5 | 5 |
| complejo | 4 | 2 |
| supercomplejo | 5 | 5 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G1 | state | 2 |
| G10 | causes_required | 2 |

### Dimensiones del juez

Sin juez en esta corrida: los gates deciden solos.

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `complejo-dos-temas` | complejo | 0.00 | — |
| `complejo-no-quiere-email` | complejo | 0.00 | — |

## Escenarios que no pasan

### `complejo-dos-temas` (complejo)
- **G1 · state**: state=bot, esperado uno de: human
- **G10 · causes_required**: ninguna derivación esperada (esperaba persona); se registró: ninguna
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-no-quiere-email` (complejo)
- **G1 · state**: state=bot, esperado uno de: human
- **G10 · causes_required**: ninguna derivación esperada (esperaba booking_unavailable, persona); se registró: ninguna
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: ninguno
