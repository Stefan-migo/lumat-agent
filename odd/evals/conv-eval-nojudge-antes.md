# Evaluación conversacional — `nojudge-antes`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `be5266f8b38cda791304171e3e4d207c0e8b55eb` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `e618b6dfa573` · KB: `baa03df47194` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `sin juez (solo gates)` · inicio: 2026-11-17T14:27:21+00:00

## Resumen

- Escenarios: **42** · pasan: **33**
- Peor dimensión: `—`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 12 | 8 |
| complejo | 16 | 12 |
| supercomplejo | 14 | 13 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G6 | must_include_any | 3 |
| G1 | state | 3 |
| G4 | events_forbidden | 3 |
| G10 | causes_required | 2 |
| G2 | intent | 1 |

### Dimensiones del juez

Sin juez en esta corrida: los gates deciden solos.

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-cobertura-comuna` | simple | 0.00 | — |
| `complejo-dos-temas` | complejo | 0.00 | — |
| `complejo-no-quiere-email` | complejo | 0.00 | — |
| `real-cortesia-no-es-reclamo` | simple | 0.00 | — |
| `real-precio-mantencion-ciclo` | simple | 0.00 | — |
| `real-dato-mas-pregunta` | complejo | 0.00 | — |
| `real-mantencion-caldera` | simple | 0.00 | — |
| `real-claudio-caldera-valvula` | complejo | 0.00 | — |
| `real-maria-jesus-evaluacion-caldera` | supercomplejo | 0.00 | — |

## Escenarios que no pasan

### `simple-cobertura-comuna` (simple)
- **G6 · must_include_any**: ninguna respuesta contiene: asesor, coordina, cuentame, cuéntame
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-dos-temas` (complejo)
- **G1 · state**: state=bot, esperado uno de: human
- **G10 · causes_required**: ninguna derivación esperada (esperaba persona); se registró: ninguna
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-no-quiere-email` (complejo)
- **G1 · state**: state=bot, esperado uno de: human
- **G10 · causes_required**: ninguna derivación esperada (esperaba booking_unavailable, persona); se registró: ninguna
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-cortesia-no-es-reclamo` (simple)
- **G1 · state**: state=human, esperado uno de: bot
- **G4 · events_forbidden**: se registró lo prohibido: escalation
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

### `real-maria-jesus-evaluacion-caldera` (supercomplejo)
- **G6 · must_include_any**: ninguna respuesta contiene: evaluación, evaluacion, revis
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: ninguno
