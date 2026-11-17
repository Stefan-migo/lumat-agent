# Evaluación conversacional — `despues-simple`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `bb7d7468d12669f2dba3a84e6343faf265e95a36` · árbol sucio: **sí** · corrida: cliente scripted
- Corpus: `e618b6dfa573` · KB: `baa03df47194` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-16T22:53:22+00:00

> **No citable como baseline**: el árbol no estaba limpio.

## Resumen

- Escenarios: **12** · pasan: **9**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 12 | 9 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G6 | must_include_any | 2 |
| G2 | intent | 1 |

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 3.17 | ±2 | 12 |
| policy | 3.67 | ±2 | 12 |
| conversational | 2.33 | ±1 | 12 |
| escalation | 3.75 | ±4 | 12 |
| tone | 3.83 | ±1 | 12 |
| closure | 2.33 | ±2 | 12 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-saludo-variante` | simple | 4.00 | ±1 |
| `simple-precio-calefont` | simple | 4.00 | ±0 |
| `simple-cobertura-comuna` | simple | 2.83 | ±2 |
| `simple-horario-sabado` | simple | 2.50 | ±4 |
| `simple-dia-especifico` | simple | 0.00 | ±4 |
| `simple-despedida` | simple | 3.83 | ±0 |
| `real-cortesia-no-es-reclamo` | simple | 3.33 | ±1 |
| `real-precio-mantencion-ciclo` | simple | 0.00 | ±2 |
| `real-cobertura-condominio` | simple | 3.33 | ±1 |
| `real-vocabulario-impreciso` | simple | 3.50 | ±1 |
| `real-mantencion-caldera` | simple | 0.00 | ±2 |
| `real-hector-discrepancia-valor` | simple | 3.33 | ±2 |

## Escenarios que no pasan

### `simple-dia-especifico` (simple)
- **G6 · must_include_any**: ninguna respuesta contiene: horario, visita, agend
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-precio-mantencion-ciclo` (simple)
- **G2 · intent**: intents vistos ['consulta'], esperaba alguno de: valores
- **hard fail del juez**: Inventa una periodicidad no documentada (una vez al año y cada 6 meses en uso intensivo) y además afirma que la mantención quedó registrada como pendiente de hoy.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-mantencion-caldera` (simple)
- **G6 · must_include_any**: ninguna respuesta contiene: mantenci, caldera
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

**No comparable**: el corpus cambió entre las dos corridas.
