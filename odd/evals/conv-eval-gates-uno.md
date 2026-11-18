# Evaluación conversacional — `gates-uno`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `d17974f4fdf22922e0b28de5f195de11aa563459` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `e0eb9c8a0a09` · KB: `baa03df47194` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `sin juez (solo gates)` · inicio: 2026-11-17T17:47:32+00:00

## Resumen

- Escenarios: **7** · pasan: **3**
- Peor dimensión: `—`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 3 | 1 |
| complejo | 4 | 2 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G1 | state | 1 |
| G10 | causes_required | 1 |
| G2 | intent | 1 |
| G4 | events_forbidden | 1 |
| G6 | must_include_any | 1 |

### Dimensiones del juez

Sin juez en esta corrida: los gates deciden solos.

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `complejo-no-quiere-email` | complejo | 0.00 | — |
| `real-precio-mantencion-ciclo` | simple | 0.00 | — |
| `real-dato-mas-pregunta` | complejo | 0.00 | — |
| `real-mantencion-caldera` | simple | 0.00 | — |

## Escenarios que no pasan

### `complejo-no-quiere-email` (complejo)
- **G1 · state**: state=bot, esperado uno de: human
- **G10 · causes_required**: ninguna derivación esperada (esperaba booking_unavailable, persona); se registró: ninguna
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-precio-mantencion-ciclo` (simple)
- **G2 · intent**: intents vistos ['consulta'], esperaba alguno de: valores
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-dato-mas-pregunta` (complejo)
- **G4 · events_forbidden**: se registró lo prohibido: unknown_intent
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-mantencion-caldera` (simple)
- **G6 · must_include_any**: ninguna respuesta contiene: mantenci, caldera
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

Sin corrida previa: esta es la línea base.
