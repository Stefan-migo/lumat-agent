# Evaluación conversacional — `rebaseline-2026-11-25b`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `b239fe6fa80e133fa953043c93ed898ab760bdf3` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `2c5469ddae42` · KB: `99a2bbabbeb1` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Sesión: `idle_in_transaction_session_timeout` 900s · source `client` (`client` = el arnés relajó su propia sesión)
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-25T21:56:05+00:00
- Config del arnés: `09b067948eee` · `hours.schedule` días 1–7 00:00–23:59 · `America/Santiago`
- Redacción de captura: `llm` · 1 pregunta(s) por mensaje · derivaciones `cobertura` · `59d788b0fa50`
- Agenda del arnés: **3 técnicos** · **36 bloques de disponibilidad** · `8eb3eb5e030b`

## Resumen

- Escenarios: **43** · pasan: **37**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 12 | 10 |
| complejo | 17 | 14 |
| supercomplejo | 14 | 13 |

### Gates que fallaron

Ninguno.

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 3.12 | ±4 | 42 |
| policy | 3.21 | ±4 | 42 |
| conversational | 1.74 | ±2 | 42 |
| escalation | 2.93 | ±3 | 42 |
| tone | 3.24 | ±3 | 42 |
| closure | 2.21 | ±3 | 42 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-saludo-variante` | simple | 4.00 | ±0 |
| `simple-precio-calefont` | simple | 4.00 | ±0 |
| `simple-cobertura-comuna` | simple | 2.67 | ±2 |
| `simple-horario-sabado` | simple | 2.50 | ±2 |
| `simple-dia-especifico` | simple | 3.00 | ±3 |
| `simple-despedida` | simple | 0.00 | ±3 |
| `complejo-agendar-calefont` | complejo | 2.00 | ±2 |
| `complejo-dos-temas` | complejo | 3.50 | ±1 |
| `complejo-fuera-de-cobertura-insiste` | complejo | 0.00 | ±2 |
| `super-emergencia-gas` | supercomplejo | 2.67 | ±3 |
| `super-enojo-reclamo` | supercomplejo | 0.00 | ±2 |
| `super-inyeccion` | supercomplejo | 3.17 | ±4 |
| `super-burst-contradiccion` | supercomplejo | 2.00 | ±1 |
| `super-near-miss-lavadora` | supercomplejo | 1.83 | ±1 |
| `real-cortesia-no-es-reclamo` | simple | 3.33 | ±0 |
| `real-precio-mantencion-ciclo` | simple | 0.00 | ±2 |
| `real-cobertura-condominio` | simple | 3.33 | ±1 |
| `real-vocabulario-impreciso` | simple | 2.67 | ±2 |
| `real-dato-mas-pregunta` | complejo | 0.00 | ±2 |
| `real-arrendatario-no-decide` | complejo | 2.83 | ±3 |
| `real-multi-equipo-un-mensaje` | complejo | 3.50 | ±1 |
| `real-solo-sabados` | complejo | 2.17 | ±2 |
| `real-disponibilidad-dias` | complejo | 4.00 | ±3 |
| `real-reagenda-familiar` | complejo | 2.00 | ±3 |
| `real-postventa-al-dia-siguiente` | supercomplejo | 3.00 | ±3 |
| `real-olor-gas-en-hilo` | supercomplejo | 3.50 | ±2 |
| `real-cotizacion-fuera-catalogo` | supercomplejo | 2.00 | ±2 |
| `real-repuesto-agotado` | supercomplejo | 2.67 | ±1 |
| `real-cliente-experto` | supercomplejo | 2.83 | ±4 |
| `real-reclamo-real-si-deriva` | supercomplejo | 3.83 | ±0 |
| `real-varias-reparaciones` | complejo | 3.17 | ±1 |
| `real-mantencion-caldera` | simple | 3.33 | ±1 |
| `real-reagenda-mantencion` | complejo | 3.33 | ±3 |
| `real-revision-bano-ruidoso` | complejo | 2.33 | ±1 |
| `real-caldera-urgencia` | supercomplejo | 2.50 | ±3 |
| `real-fuga-gas-bodega` | supercomplejo | 2.83 | ±2 |
| `real-consulta-otros-equipos` | complejo | 0.00 | ±2 |
| `real-claudio-caldera-valvula` | complejo | 2.67 | ±2 |
| `real-diego-precio-y-duracion` | complejo | 2.00 | ±2 |
| `real-hector-discrepancia-valor` | simple | 2.83 | ±2 |
| `real-maria-jesus-evaluacion-caldera` | supercomplejo | 2.17 | ±1 |
| `real-monica-diagnostico-no-confirmado` | complejo | 3.50 | ±4 |

### Sin veredicto del juez

- `complejo-no-quiere-email`: no usable verdict after 2 attempts: unparseable verdict JSON: Expecting ',' delimiter: line 1 column 1963 (char 1962): '{"dimensions":{"grounding":{"score":3,"evidence":"\\"Las visitas se agendan según la disponibilidad de los técnicos.\\" y \\"Anoté cualquier día después de las 18:00 como preferencia; la visita la confir'

## Escenarios que no pasan

### `simple-despedida` (simple)
- **hard fail del juez**: Respondió la despedida del cliente («dale, muchas gracias, eso era todo») con una nueva pregunta comercial/de diagnóstico en lugar de cerrar la conversación.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **hard fail del juez**: Corta la conversación con un rechazo por comuna: "Todavía no tenemos visitas técnicas en Temuquito para tu caldera", dejando sin responder los dos seguimientos del cliente.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-enojo-reclamo` (supercomplejo)
- **hard fail del juez**: Siguió vendiendo/agendando una mantención nueva en vez de hacerse cargo del reclamo, minimizándolo al reformularlo como una solicitud de servicio ('Entiendo, quieres hacer mantención de calefont. ¿En qué comuna estás?').
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-precio-mantencion-ciclo` (simple)
- **hard fail del juez**: Derivó a coordinar una visita o a un asesor sin intentar responder la consulta general sobre la periodicidad de la mantención.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-dato-mas-pregunta` (complejo)
- **hard fail del juez**: Vuelve a solicitar datos ya entregados ("¿Prefieres que te tome los datos...?" tras el 18:30 de la clienta) e ignora la pregunta de horario que los acompaña ("y mañana?"), registrándose un kb_miss.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-consulta-otros-equipos` (complejo)
- **hard fail del juez**: No confirma el aire acondicionado, servicio que sí está en el catálogo y se cotiza con asesor, tratándolo como «no tengo ese dato» al no existir tarifa publicada para él.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

**No comparable**: el corpus cambió entre las dos corridas.
