# Evaluación conversacional — `pregunta-gana`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `c2e7f8e45af3e92cb7d1abb52cda2114f727d8be` · árbol sucio: **sí** · corrida: cliente scripted
- Corpus: `2c5469ddae42` · KB: `34670f5b3d75` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-21T19:11:24+00:00

> **No citable como baseline**: el árbol no estaba limpio.

## Resumen

- Escenarios: **7** · pasan: **5**
- Peor dimensión: `closure`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 2 | 2 |
| complejo | 5 | 3 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G6 | must_include_any | 1 |

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 2.71 | ±2 | 7 |
| policy | 3.14 | ±1 | 7 |
| conversational | 2.14 | ±2 | 7 |
| escalation | 2.86 | ±2 | 7 |
| tone | 3.71 | ±1 | 7 |
| closure | 2.00 | ±1 | 7 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-cobertura-comuna` | simple | 2.67 | ±2 |
| `real-cobertura-condominio` | simple | 3.33 | ±1 |
| `real-dato-mas-pregunta` | complejo | 2.83 | ±2 |
| `real-solo-sabados` | complejo | 2.67 | ±2 |
| `real-disponibilidad-dias` | complejo | 0.00 | ±2 |
| `real-reagenda-mantencion` | complejo | 3.50 | ±1 |
| `real-claudio-caldera-valvula` | complejo | 0.00 | ±2 |

## Escenarios que no pasan

### `real-disponibilidad-dias` (complejo)
- **G6 · must_include_any**: ninguna respuesta contiene: horario, disponibilidad, sábado, sabado, semana
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-claudio-caldera-valvula` (complejo)
- **hard fail del juez**: Indicó cortar la llave de agua de la caldera sin verificar el equipo ni la situación, con una instrucción improvisada sobre válvulas.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

Sin corrida previa: esta es la línea base.
