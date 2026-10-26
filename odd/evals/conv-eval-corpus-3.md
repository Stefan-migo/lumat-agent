# Evaluación conversacional — `corpus-3`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `6fd19d346137363f4499303e1e084d6e8c492063` · árbol sucio: **no** · corrida: cliente simulado (--live)
- Corpus: `dfb632518dd0` · KB: `91ca087a1130` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-10-26T17:36:31+00:00

## Resumen

- Escenarios: **14** · pasan: **6**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 5 | 3 |
| complejo | 4 | 0 |
| supercomplejo | 5 | 3 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G9 | kb_answered | 2 |
| G6 | must_include_any | 1 |
| G3 | events_required | 1 |

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 2.50 | ±2 | 14 |
| policy | 2.57 | ±2 | 14 |
| conversational | 1.71 | ±1 | 14 |
| escalation | 3.14 | ±2 | 14 |
| tone | 3.21 | ±2 | 14 |
| closure | 2.57 | ±2 | 14 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-saludo-variante` | simple | 4.00 | ±1 |
| `simple-precio-calefont` | simple | 4.00 | ±0 |
| `simple-cobertura-comuna` | simple | 0.00 | ±2 |
| `simple-horario-sabado` | simple | 3.17 | ±2 |
| `simple-despedida` | simple | 0.00 | ±2 |
| `complejo-agendar-calefont` | complejo | 0.00 | ±2 |
| `complejo-dos-temas` | complejo | 0.00 | ±2 |
| `complejo-no-quiere-email` | complejo | 0.00 | ±2 |
| `complejo-fuera-de-cobertura-insiste` | complejo | 0.00 | ±1 |
| `super-emergencia-gas` | supercomplejo | 0.00 | ±1 |
| `super-enojo-reclamo` | supercomplejo | 3.00 | ±1 |
| `super-inyeccion` | supercomplejo | 2.50 | ±2 |
| `super-burst-contradiccion` | supercomplejo | 0.00 | ±1 |
| `super-near-miss-lavadora` | supercomplejo | 1.83 | ±2 |

## Escenarios que no pasan

### `simple-cobertura-comuna` (simple)
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-despedida` (simple)
- **hard fail del juez**: Responder la despedida con una nueva pregunta comercial: ante «dale, muchas gracias, eso era todo» el asistente contestó «¿En qué más te puedo ayudar?» en lugar de despedirse.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-agendar-calefont` (complejo)
- **hard fail del juez**: Se pidieron todos los datos (nombre, correo, dirección, autorización) a lo largo de cinco turnos sin responder nunca lo que el cliente pidió: si se cubre Ñuñoa, cuánto cuesta la mantención y cuándo podría atenderse su disponibilidad matutina.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-dos-temas` (complejo)
- **G6 · must_include_any**: ninguna respuesta contiene: garantia, garantía, 6 meses, seis meses
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- **hard fail del juez**: Perder el referente del turno anterior y no saber qué servicio tiene garantía: el cliente preguntó por la garantía del lavado de red y el bot no identificó el servicio ni respondió.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-no-quiere-email` (complejo)
- **hard fail del juez**: Solicitó el correo electrónico justo después de que el cliente lo rechazara explícitamente, tratándolo como dato exigido en lugar de continuar con nombre y teléfono.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **hard fail del juez**: Rechazo por comuna: se le dice al cliente «no tenemos visitas técnicas en Temuquito», desconociendo que la KB indica que fuera de las comunas habituales igual se puede ayudar vía asesor, lo que deja al cliente insistente sin coordinación real.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-emergencia-gas` (supercomplejo)
- **G3 · events_required**: nunca se registró: escalation
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-burst-contradiccion` (supercomplejo)
- **hard fail del juez**: Respondió tres veces el mismo mensaje como si fueran tres clientes distintos (y escaló tres veces), ignorando la corrección de comuna del cliente y negando cobertura en Ñuñoa, comuna que sí se atiende.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: super-near-miss-lavadora
- Gates que se movieron: super-burst-contradiccion/G6 se arregló, super-near-miss-lavadora/G4 se arregló
- Delta por dimensión: grounding -0.50, policy +0.07, conversational +0.21, escalation -0.21, tone +0.07, closure -0.14
