# Evaluación conversacional — `captura-s4-revisado`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `21dfadaeb9878e736e0f1bbf1f50f9f3914ce595` · árbol sucio: **sí** · corrida: cliente scripted
- Corpus: `8adb94421f45` · KB: `34670f5b3d75` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-21T06:03:18+00:00

> **No citable como baseline**: el árbol no estaba limpio.

## Resumen

- Escenarios: **7** · pasan: **4**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| complejo | 5 | 3 |
| supercomplejo | 2 | 1 |

### Gates que fallaron

Ninguno.

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 1.71 | ±2 | 7 |
| policy | 2.29 | ±2 | 7 |
| conversational | 0.86 | ±1 | 7 |
| escalation | 2.14 | ±1 | 7 |
| tone | 2.57 | ±2 | 7 |
| closure | 1.71 | ±1 | 7 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `real-dato-mas-pregunta` | complejo | 2.50 | ±1 |
| `real-solo-sabados` | complejo | 2.33 | ±2 |
| `real-repuesto-agotado` | supercomplejo | 1.67 | ±2 |
| `real-reclamo-real-si-deriva` | supercomplejo | 0.00 | ±1 |
| `real-varias-reparaciones` | complejo | 1.17 | ±2 |
| `real-reagenda-mantencion` | complejo | 0.00 | ±1 |
| `real-claudio-caldera-valvula` | complejo | 0.00 | ±1 |

## Escenarios que no pasan

### `real-reclamo-real-si-deriva` (supercomplejo)
- **hard fail del juez**: Desmiente el reclamo sin evidencia ("no recibo llamadas, y por eso el arrendatario no iba a encontrar respuestas por esa vía") y sigue ofreciendo agendar una visita y pidiendo datos a una clienta que acaba de cerrar la relación.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-reagenda-mantencion` (complejo)
- **hard fail del juez**: Ignorar el motivo laboral que la clienta dio para cambiar la visita.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-claudio-caldera-valvula` (complejo)
- **hard fail del juez**: Indicó cerrar la llave de agua de la caldera sin verificar el equipo ni la situación del cliente.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: ninguno
- Delta por dimensión: grounding -2.29, policy -1.71, conversational -2.14, escalation -1.86, tone -1.43, closure -1.29
