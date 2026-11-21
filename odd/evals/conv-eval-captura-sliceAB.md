# Evaluación conversacional — `captura-sliceAB`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `cf49703cd0232075a0016d6f08086e2b0a2b9b55` · árbol sucio: **sí** · corrida: cliente scripted
- Corpus: `8adb94421f45` · KB: `34670f5b3d75` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-20T18:52:22+00:00

> **No citable como baseline**: el árbol no estaba limpio.

## Resumen

- Escenarios: **4** · pasan: **2**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| complejo | 3 | 2 |
| supercomplejo | 1 | 0 |

### Gates que fallaron

Ninguno.

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 2.50 | ±2 | 4 |
| policy | 2.00 | ±4 | 4 |
| conversational | 0.50 | ±1 | 4 |
| escalation | 1.50 | ±3 | 4 |
| tone | 3.00 | ±1 | 4 |
| closure | 1.50 | ±1 | 4 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `real-solo-sabados` | complejo | 2.50 | ±3 |
| `real-repuesto-agotado` | supercomplejo | 0.00 | ±2 |
| `real-varias-reparaciones` | complejo | 1.17 | ±1 |
| `real-reagenda-mantencion` | complejo | 0.00 | ±4 |

## Escenarios que no pasan

### `real-repuesto-agotado` (supercomplejo)
- **hard fail del juez**: Aceptó la fecha del lunes para la visita sin confirmar disponibilidad de técnicos ni el estado del repuesto, dejando al cliente con una expectativa de fecha no confirmada.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-reagenda-mantencion` (complejo)
- **hard fail del juez**: Ignoró el motivo laboral que la clienta dio para cambiar la visita: no lo reconoció ni lo mencionó al responder.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: real-reagenda-mantencion
- Arreglos: real-solo-sabados, real-varias-reparaciones
- Delta por dimensión: grounding +0.83, policy +1.00, conversational +0.17, escalation +0.50, tone +0.00, closure +1.17
