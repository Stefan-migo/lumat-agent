# Evaluación conversacional — `agenda-pref-4`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `e90c5a3d1bbac685ac332e6a68058b0faade0bad` · árbol sucio: **sí** · corrida: cliente scripted
- Corpus: `1735bb01b90e` · KB: `6fbd06e66d2a` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-10-28T01:19:31+00:00

> **No citable como baseline**: el árbol no estaba limpio.

## Resumen

- Escenarios: **2** · pasan: **2**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 2 | 2 |

### Gates que fallaron

Ninguno.

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 3.50 | ±0 | 2 |
| policy | 3.50 | ±1 | 2 |
| conversational | 2.00 | ±1 | 2 |
| escalation | 4.00 | ±1 | 2 |
| tone | 3.00 | ±1 | 2 |
| closure | 2.50 | ±2 | 2 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-horario-sabado` | simple | 3.33 | ±2 |
| `simple-dia-especifico` | simple | 2.83 | ±1 |

## Escenarios que no pasan

Ninguno.

## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: ninguno
