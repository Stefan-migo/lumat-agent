# Evaluación conversacional — `pregunta-gana-sched`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `c2e7f8e45af3e92cb7d1abb52cda2114f727d8be` · árbol sucio: **sí** · corrida: cliente scripted
- Corpus: `2c5469ddae42` · KB: `34670f5b3d75` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-21T19:28:03+00:00

> **No citable como baseline**: el árbol no estaba limpio.

## Resumen

- Escenarios: **7** · pasan: **7**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 3 | 3 |
| complejo | 4 | 4 |

### Gates que fallaron

Ninguno.

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 2.71 | ±2 | 7 |
| policy | 3.43 | ±3 | 7 |
| conversational | 1.86 | ±3 | 7 |
| escalation | 3.00 | ±3 | 7 |
| tone | 3.43 | ±1 | 7 |
| closure | 1.86 | ±1 | 7 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-cobertura-comuna` | simple | 2.33 | ±3 |
| `simple-horario-sabado` | simple | 2.33 | ±2 |
| `real-cobertura-condominio` | simple | 3.17 | ±2 |
| `real-dato-mas-pregunta` | complejo | 3.33 | ±3 |
| `real-solo-sabados` | complejo | 2.50 | ±1 |
| `real-disponibilidad-dias` | complejo | 2.17 | ±3 |
| `real-reagenda-mantencion` | complejo | 3.17 | ±2 |

## Escenarios que no pasan

Ninguno.

## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: real-disponibilidad-dias
- Gates que se movieron: real-disponibilidad-dias/G6 se arregló
- Delta por dimensión: grounding +0.00, policy +0.29, conversational -0.29, escalation +0.14, tone -0.29, closure -0.14
