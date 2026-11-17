# Evaluación conversacional — `nojudge-main`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `69d9a12b7282c86f1ae835c8446cd303c7dfdf59` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `e618b6dfa573` · KB: `baa03df47194` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `sin juez (solo gates)` · inicio: 2026-11-17T14:19:31+00:00

## Resumen

- Escenarios: **42** · pasan: **35**
- Peor dimensión: `—`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 12 | 9 |
| complejo | 16 | 12 |
| supercomplejo | 14 | 14 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G6 | must_include_any | 2 |
| G1 | state | 2 |
| G10 | causes_required | 2 |
| G4 | events_forbidden | 2 |
| G2 | intent | 1 |

### Dimensiones del juez

Sin juez en esta corrida: los gates deciden solos.

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-dia-especifico` | simple | 0.00 | — |
| `complejo-dos-temas` | complejo | 0.00 | — |
| `complejo-no-quiere-email` | complejo | 0.00 | — |
| `real-precio-mantencion-ciclo` | simple | 0.00 | — |
| `real-dato-mas-pregunta` | complejo | 0.00 | — |
| `real-mantencion-caldera` | simple | 0.00 | — |
| `real-claudio-caldera-valvula` | complejo | 0.00 | — |

## Escenarios que no pasan

### `simple-dia-especifico` (simple)
- **G6 · must_include_any**: ninguna respuesta contiene: horario, visita, agend
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-dos-temas` (complejo)
- **G1 · state**: state=bot, esperado uno de: human
- **G10 · causes_required**: ninguna derivación esperada (esperaba persona); se registró: ninguna
- puntaje: 0.00 (capeado a 0 por el gate)

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

### `real-claudio-caldera-valvula` (complejo)
- **G4 · events_forbidden**: se registró lo prohibido: unknown_intent
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: real-caldera-urgencia, real-fuga-gas-bodega
