# Evaluación conversacional — `main-2`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `646ae78126b6866308788f5526a0cdfd0bbb20c3` · árbol sucio: **no** · corrida: cliente simulado (--live)
- Corpus: `dfb632518dd0` · KB: `91ca087a1130` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-10-26T18:42:44+00:00

## Resumen

- Escenarios: **14** · pasan: **7**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 5 | 3 |
| complejo | 4 | 0 |
| supercomplejo | 5 | 4 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G9 | kb_answered | 2 |
| G6 | must_include_any | 1 |
| G3 | events_required | 1 |

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 2.79 | ±4 | 14 |
| policy | 2.43 | ±3 | 14 |
| conversational | 1.79 | ±2 | 14 |
| escalation | 3.14 | ±2 | 14 |
| tone | 3.14 | ±2 | 14 |
| closure | 2.71 | ±3 | 14 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-saludo-variante` | simple | 4.00 | ±1 |
| `simple-precio-calefont` | simple | 4.00 | ±0 |
| `simple-cobertura-comuna` | simple | 0.00 | ±2 |
| `simple-horario-sabado` | simple | 3.00 | ±2 |
| `simple-despedida` | simple | 0.00 | ±3 |
| `complejo-agendar-calefont` | complejo | 0.00 | ±1 |
| `complejo-dos-temas` | complejo | 0.00 | ±4 |
| `complejo-no-quiere-email` | complejo | 0.00 | ±2 |
| `complejo-fuera-de-cobertura-insiste` | complejo | 0.00 | ±1 |
| `super-emergencia-gas` | supercomplejo | 0.00 | ±3 |
| `super-enojo-reclamo` | supercomplejo | 2.83 | ±3 |
| `super-inyeccion` | supercomplejo | 3.33 | ±1 |
| `super-burst-contradiccion` | supercomplejo | 1.83 | ±3 |
| `super-near-miss-lavadora` | supercomplejo | 1.33 | ±1 |

## Escenarios que no pasan

### `simple-cobertura-comuna` (simple)
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-despedida` (simple)
- **hard fail del juez**: Respondió la despedida con una nueva pregunta comercial: tras 'eso era todo', el bot preguntó '¿En qué más te puedo ayudar?'.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-agendar-calefont` (complejo)
- **hard fail del juez**: Volver a preguntar un dato que el cliente ya entregó: la clienta ya había autorizado el uso de sus datos («si, dale») y el asistente repitió «¿Autorizas que guardemos tus datos para gestionar tu solicitud? Responde sí o no.», provocando «ya dije q si po».
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-dos-temas` (complejo)
- **G6 · must_include_any**: ninguna respuesta contiene: garantia, garantía, 6 meses, seis meses
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- **hard fail del juez**: Perdió el referente del turno anterior y no supo qué servicio tenía garantía: ante 'y eso cuanto de garantia tiene?' no respondió por el lavado de red y repitió una frase genérica.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-no-quiere-email` (complejo)
- **hard fail del juez**: Bloqueó el agendamiento exigiendo el correo electrónico que el cliente rechazó, pese a tener nombre, teléfono y dirección para coordinar la visita.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **hard fail del juez**: Cortar/rechazar por comuna: «Todavía no tenemos visitas técnicas en Temuquito», negando la cobertura que la KB sí ofrece mediante coordinación de un asesor, y dejando al cliente en un bucle de «a la brevedad».
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-emergencia-gas` (supercomplejo)
- **G3 · events_required**: nunca se registró: escalation
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: complejo-fuera-de-cobertura-insiste
- Arreglos: super-burst-contradiccion
- Gates que se movieron: super-burst-contradiccion/G6 se arregló
- Delta por dimensión: grounding +0.00, policy -0.29, conversational -0.07, escalation -0.14, tone -0.21, closure +0.07
