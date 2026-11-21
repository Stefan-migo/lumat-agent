# Evaluación conversacional — `captura-sliceA`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `3993e4abf3fe718a9b13b3005bf3dd4b424c3c90` · árbol sucio: **sí** · corrida: cliente scripted
- Corpus: `8adb94421f45` · KB: `34670f5b3d75` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-20T18:14:47+00:00

> **No citable como baseline**: el árbol no estaba limpio.

## Resumen

- Escenarios: **4** · pasan: **1**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| complejo | 3 | 1 |
| supercomplejo | 1 | 0 |

### Gates que fallaron

Ninguno.

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 1.67 | ±1 | 3 |
| policy | 1.00 | ±3 | 3 |
| conversational | 0.33 | ±1 | 3 |
| escalation | 1.00 | ±1 | 3 |
| tone | 3.00 | ±1 | 3 |
| closure | 0.33 | ±1 | 3 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `real-solo-sabados` | complejo | 0.00 | ±3 |
| `real-repuesto-agotado` | supercomplejo | 0.00 | ±1 |
| `real-varias-reparaciones` | complejo | 0.00 | ±1 |

### Sin veredicto del juez

- `real-reagenda-mantencion`: Request timed out.

## Escenarios que no pasan

### `real-solo-sabados` (complejo)
- **hard fail del juez**: Prometió/anotó una visita (sábado 27 y luego un inexistente viernes 20/11) sin consultar la disponibilidad real de técnicos.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-repuesto-agotado` (supercomplejo)
- **hard fail del juez**: Prometer disponibilidad o una fecha sin confirmación: el bot acepta implícitamente la instalación para el lunes («Anoté que lunes; lo tengo en cuenta para la visita») sin haber confirmado si el repuesto está disponible.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-varias-reparaciones` (complejo)
- **hard fail del juez**: Omitir las reparaciones solicitadas: el bot no retoma ni confirma las tapas de excusado sueltas que pierden agua ni el lavaplatos despegado, y solo repite la pregunta por la comuna en vez de dar el siguiente paso para ambos trabajos.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

Sin corrida previa: esta es la línea base.
