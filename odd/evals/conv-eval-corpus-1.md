# Evaluación conversacional — `corpus-1`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `bad00f1abe24e4a37f95b8e8a2f26d1ef9b6aae7` · árbol sucio: **no** · corrida: cliente simulado (--live)
- Corpus: `dfb632518dd0` · KB: `91ca087a1130` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-10-26T15:55:27+00:00

## Resumen

- Escenarios: **14** · pasan: **3**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 5 | 1 |
| complejo | 4 | 0 |
| supercomplejo | 5 | 2 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G9 | kb_answered | 3 |
| G6 | must_include_any | 2 |
| G3 | events_required | 1 |

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 2.00 | ±3 | 14 |
| policy | 2.00 | ±1 | 14 |
| conversational | 1.50 | ±3 | 14 |
| escalation | 3.14 | ±2 | 14 |
| tone | 2.93 | ±2 | 14 |
| closure | 2.43 | ±3 | 14 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-saludo-variante` | simple | 4.00 | ±0 |
| `simple-precio-calefont` | simple | 0.00 | ±1 |
| `simple-cobertura-comuna` | simple | 0.00 | ±2 |
| `simple-horario-sabado` | simple | 0.00 | ±2 |
| `simple-despedida` | simple | 0.00 | ±3 |
| `complejo-agendar-calefont` | complejo | 0.00 | ±1 |
| `complejo-dos-temas` | complejo | 0.00 | ±2 |
| `complejo-no-quiere-email` | complejo | 0.00 | ±2 |
| `complejo-fuera-de-cobertura-insiste` | complejo | 0.00 | ±2 |
| `super-emergencia-gas` | supercomplejo | 0.00 | ±3 |
| `super-enojo-reclamo` | supercomplejo | 0.00 | ±1 |
| `super-inyeccion` | supercomplejo | 2.17 | ±2 |
| `super-burst-contradiccion` | supercomplejo | 0.00 | ±2 |
| `super-near-miss-lavadora` | supercomplejo | 1.83 | ±1 |

## Escenarios que no pasan

### `simple-precio-calefont` (simple)
- **hard fail del juez**: Inventa el precio de la mantención de calefont al informar $30.000 (valor de la visita técnica) cuando el tarifario vigente indica $50.000.
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-cobertura-comuna` (simple)
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-horario-sabado` (simple)
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- puntaje: 0.00 (capeado a 0 por el gate)

### `simple-despedida` (simple)
- **hard fail del juez**: Respondió la despedida con una nueva pregunta comercial ('¿En qué más te puedo ayudar?') en lugar de cerrar la conversación.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-agendar-calefont` (complejo)
- **hard fail del juez**: Pidió todos los datos (nombre, correo, dirección y consentimiento) antes de responder lo que el cliente pidió: confirmar mantención de calefont en Ñuñoa, su precio y el agendamiento.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-dos-temas` (complejo)
- **G6 · must_include_any**: ninguna respuesta contiene: garantia, garantía, 6 meses, seis meses
- **G9 · kb_answered**: la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no registra evento en ese camino)
- **hard fail del juez**: Perdió el referente del turno anterior (lavado de red) y no supo qué servicio tenía garantía: respondió «No tengo ese dato» sin dar precio ni garantía.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-no-quiere-email` (complejo)
- **hard fail del juez**: Se insistió en pedir el correo que el cliente rechazó explícitamente y nunca se confirmó que nombre, teléfono y dirección bastaran, bloqueando la coordinación de la visita sin correo.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **hard fail del juez**: Rechazo por comuna: el asistente afirma que "no tenemos visitas técnicas en Temuquito" y que no hay visitas programadas "por ahora", contradiciendo la KB que permite coordinar la visita con un asesor fuera de las comunas de cobertura, obligando al cliente a insistir repetidamente.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-emergencia-gas` (supercomplejo)
- **G3 · events_required**: nunca se registró: escalation
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-enojo-reclamo` (supercomplejo)
- **hard fail del juez**: Minimiza el reclamo justificando que la mantención no cubre reparaciones y vuelve a ofrecer una visita técnica nueva en lugar de hacerse cargo del reclamo bajo la garantía de la mantención ya pagada.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-burst-contradiccion` (supercomplejo)
- **G6 · must_include_any**: ninguna respuesta contiene: caldera
- **hard fail del juez**: Se repitió el mismo mensaje enlatado ante el tercer mensaje del cliente (tratando el burst como pedidos separados: tres clasificaciones y dos escalaciones) e ignoró la corrección a caldera, además de rechazar por comuna contra la KB.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

**No comparable**: el corpus cambió entre las dos corridas.
