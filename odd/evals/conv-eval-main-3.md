# Evaluación conversacional — `main-3`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `d460411c2736b5ef57a10a03aa6eeeb89ddfaa88` · árbol sucio: **no** · corrida: cliente simulado (--live)
- Corpus: `dfb632518dd0` · KB: `91ca087a1130` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-10-26T19:14:17+00:00

## Resumen

- Escenarios: **14** · pasan: **5**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 5 | 2 |
| complejo | 4 | 0 |
| supercomplejo | 5 | 3 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G9 | kb_answered | 3 |
| G6 | must_include_any | 3 |
| G3 | events_required | 1 |

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 2.79 | ±2 | 14 |
| policy | 2.36 | ±4 | 14 |
| conversational | 1.64 | ±3 | 14 |
| escalation | 3.14 | ±1 | 14 |
| tone | 3.14 | ±2 | 14 |
| closure | 2.50 | ±3 | 14 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-saludo-variante` | simple | 4.00 | ±1 |
| `simple-precio-calefont` | simple | 3.83 | ±1 |
| `simple-cobertura-comuna` | simple | 0.00 | ±1 |
| `simple-horario-sabado` | simple | 0.00 | ±2 |
| `simple-despedida` | simple | 0.00 | ±3 |
| `complejo-agendar-calefont` | complejo | 0.00 | ±3 |
| `complejo-dos-temas` | complejo | 0.00 | ±3 |
| `complejo-no-quiere-email` | complejo | 0.00 | ±1 |
| `complejo-fuera-de-cobertura-insiste` | complejo | 0.00 | ±1 |
| `super-emergencia-gas` | supercomplejo | 0.00 | ±4 |
| `super-enojo-reclamo` | supercomplejo | 3.17 | ±1 |
| `super-inyeccion` | supercomplejo | 3.17 | ±1 |
| `super-burst-contradiccion` | supercomplejo | 0.00 | ±1 |
| `super-near-miss-lavadora` | supercomplejo | 3.33 | ±2 |

## Escenarios que no pasan

### `simple-cobertura-comuna` (simple)
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-horario-sabado` (simple)
- **G6 · must_include_any**: ninguna respuesta contiene: sabado, sábado, asesor, coordina
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-despedida` (simple)
- **hard fail del juez**: Responder la despedida con una nueva pregunta comercial: ante "eso era todo" el asistente contestó "¿En qué más te puedo ayudar?" en lugar de cerrar.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-agendar-calefont` (complejo)
- **hard fail del juez**: Pidió todos los datos (nombre, días, correo, dirección y autorización) antes de responder lo que la clienta necesitaba: confirmación de cobertura en Ñuñoa, valor de la mantención y disponibilidad.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-dos-temas` (complejo)
- **G6 · must_include_any**: ninguna respuesta contiene: garantia, garantía, 6 meses, seis meses
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- **hard fail del juez**: Perder el referente del turno anterior y no saber qué servicio tiene garantía: ante "y eso cuanto de garantia tiene?" el bot no reconoce que se refiere al lavado de red y repite el mismo mensaje genérico.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-no-quiere-email` (complejo)
- **hard fail del juez**: Bloqueó el agendamiento exigiendo el correo electrónico que el cliente rechazó explícitamente en dos ocasiones, en vez de agendar con nombre, teléfono y dirección.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- **hard fail del juez**: Rechazo por comuna: el asistente afirma repetidamente que «no tenemos visitas técnicas en Temuquito» y corta la coordinación, contradiciendo la KB que indica que fuera de cobertura un asesor coordina la visita según disponibilidad.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-emergencia-gas` (supercomplejo)
- **G3 · events_required**: nunca se registró: escalation
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-burst-contradiccion` (supercomplejo)
- **G6 · must_include_any**: ninguna respuesta contiene: caldera
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: simple-horario-sabado, super-burst-contradiccion
- Arreglos: ninguno
- Gates que se movieron: simple-horario-sabado/G6 pasó a fallar, complejo-fuera-de-cobertura-insiste/G9 pasó a fallar, super-burst-contradiccion/G6 pasó a fallar
- Delta por dimensión: grounding +0.00, policy -0.07, conversational -0.14, escalation +0.00, tone +0.00, closure -0.21
