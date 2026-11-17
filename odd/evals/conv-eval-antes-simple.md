# Evaluación conversacional — `antes-simple`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `422703245590c037eb9b1e7891e2ebd5d4f4f5c9` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `e618b6dfa573` · KB: `baa03df47194` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-16T21:02:19+00:00

## Resumen

- Escenarios: **12** · pasan: **8**
- Peor dimensión: `closure`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 12 | 8 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G1 | state | 1 |
| G4 | events_forbidden | 1 |
| G2 | intent | 1 |
| G6 | must_include_any | 1 |

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 3.42 | ±2 | 12 |
| policy | 3.08 | ±3 | 12 |
| conversational | 2.67 | ±2 | 12 |
| escalation | 3.25 | ±2 | 12 |
| tone | 3.67 | ±2 | 12 |
| closure | 2.50 | ±2 | 12 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-saludo-variante` | simple | 4.00 | ±0 |
| `simple-precio-calefont` | simple | 4.00 | ±0 |
| `simple-cobertura-comuna` | simple | 3.00 | ±3 |
| `simple-horario-sabado` | simple | 0.00 | ±2 |
| `simple-dia-especifico` | simple | 2.83 | ±1 |
| `simple-despedida` | simple | 4.00 | ±1 |
| `real-cortesia-no-es-reclamo` | simple | 0.00 | ±3 |
| `real-precio-mantencion-ciclo` | simple | 0.00 | ±1 |
| `real-cobertura-condominio` | simple | 3.50 | ±1 |
| `real-vocabulario-impreciso` | simple | 3.50 | ±1 |
| `real-mantencion-caldera` | simple | 0.00 | ±2 |
| `real-hector-discrepancia-valor` | simple | 2.67 | ±3 |

## Escenarios que no pasan

### `simple-horario-sabado` (simple)
- **hard fail del juez**: Prometió atención el sábado sin consultar la agenda real de técnicos.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-cortesia-no-es-reclamo` (simple)
- **G1 · state**: state=human, esperado uno de: bot
- **G4 · events_forbidden**: se registró lo prohibido: escalation
- **hard fail del juez**: Derivó una consulta cortés como si fuera un reclamo (`handoff:complaint`) sin responder ni preguntar qué necesitaba el cliente.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-precio-mantencion-ciclo` (simple)
- **G2 · intent**: intents vistos ['consulta'], esperaba alguno de: valores
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-mantencion-caldera` (simple)
- **G6 · must_include_any**: ninguna respuesta contiene: mantenci, caldera
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

Sin corrida previa: esta es la línea base.
