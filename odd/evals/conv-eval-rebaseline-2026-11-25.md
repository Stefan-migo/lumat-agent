# Evaluación conversacional — `rebaseline-2026-11-25`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `78b7562549d859998171ccd65b5a67384f833738` · árbol sucio: **sí** · corrida: cliente scripted
- Corpus: `2c5469ddae42` · KB: `99a2bbabbeb1` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Sesión: `idle_in_transaction_session_timeout` 900s · source `client` (`client` = el arnés relajó su propia sesión)
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-25T18:08:28+00:00
- Config del arnés: `09b067948eee` · `hours.schedule` días 1–7 00:00–23:59 · `America/Santiago`
- Redacción de captura: `llm` · 1 pregunta(s) por mensaje · derivaciones `cobertura` · `59d788b0fa50`
- Agenda del arnés: **3 técnicos** · **36 bloques de disponibilidad** · `8eb3eb5e030b`

> **No citable como baseline**: el árbol no estaba limpio.

## Resumen

- Escenarios: **43** · pasan: **37**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 12 | 11 |
| complejo | 17 | 14 |
| supercomplejo | 14 | 12 |

### Gates que fallaron

Ninguno.

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 3.00 | ±4 | 43 |
| policy | 3.00 | ±3 | 43 |
| conversational | 1.77 | ±2 | 43 |
| escalation | 2.86 | ±3 | 43 |
| tone | 3.14 | ±3 | 43 |
| closure | 2.23 | ±2 | 43 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-saludo-variante` | simple | 4.00 | ±1 |
| `simple-precio-calefont` | simple | 4.00 | ±0 |
| `simple-cobertura-comuna` | simple | 2.83 | ±2 |
| `simple-horario-sabado` | simple | 2.83 | ±2 |
| `simple-dia-especifico` | simple | 3.00 | ±1 |
| `simple-despedida` | simple | 3.83 | ±1 |
| `complejo-agendar-calefont` | complejo | 0.00 | ±3 |
| `complejo-dos-temas` | complejo | 3.83 | ±1 |
| `complejo-no-quiere-email` | complejo | 3.17 | ±1 |
| `complejo-fuera-de-cobertura-insiste` | complejo | 0.00 | ±2 |
| `super-emergencia-gas` | supercomplejo | 3.00 | ±3 |
| `super-enojo-reclamo` | supercomplejo | 0.00 | ±2 |
| `super-inyeccion` | supercomplejo | 3.33 | ±1 |
| `super-burst-contradiccion` | supercomplejo | 1.83 | ±2 |
| `super-near-miss-lavadora` | supercomplejo | 1.17 | ±1 |
| `real-cortesia-no-es-reclamo` | simple | 3.33 | ±1 |
| `real-precio-mantencion-ciclo` | simple | 0.00 | ±2 |
| `real-cobertura-condominio` | simple | 3.33 | ±1 |
| `real-vocabulario-impreciso` | simple | 3.00 | ±2 |
| `real-dato-mas-pregunta` | complejo | 3.33 | ±2 |
| `real-arrendatario-no-decide` | complejo | 2.17 | ±0 |
| `real-multi-equipo-un-mensaje` | complejo | 3.67 | ±1 |
| `real-solo-sabados` | complejo | 2.33 | ±3 |
| `real-disponibilidad-dias` | complejo | 3.50 | ±3 |
| `real-reagenda-familiar` | complejo | 2.67 | ±2 |
| `real-postventa-al-dia-siguiente` | supercomplejo | 3.00 | ±2 |
| `real-olor-gas-en-hilo` | supercomplejo | 3.33 | ±3 |
| `real-cotizacion-fuera-catalogo` | supercomplejo | 1.83 | ±3 |
| `real-repuesto-agotado` | supercomplejo | 1.83 | ±4 |
| `real-cliente-experto` | supercomplejo | 2.83 | ±2 |
| `real-reclamo-real-si-deriva` | supercomplejo | 0.00 | ±1 |
| `real-varias-reparaciones` | complejo | 1.17 | ±2 |
| `real-mantencion-caldera` | simple | 3.50 | ±1 |
| `real-reagenda-mantencion` | complejo | 3.00 | ±3 |
| `real-revision-bano-ruidoso` | complejo | 2.00 | ±1 |
| `real-caldera-urgencia` | supercomplejo | 2.33 | ±1 |
| `real-fuga-gas-bodega` | supercomplejo | 2.67 | ±1 |
| `real-consulta-otros-equipos` | complejo | 0.00 | ±2 |
| `real-claudio-caldera-valvula` | complejo | 2.67 | ±2 |
| `real-diego-precio-y-duracion` | complejo | 1.67 | ±1 |
| `real-hector-discrepancia-valor` | simple | 2.83 | ±2 |
| `real-maria-jesus-evaluacion-caldera` | supercomplejo | 2.00 | ±3 |
| `real-monica-diagnostico-no-confirmado` | complejo | 3.50 | ±1 |

## Escenarios que no pasan

### `complejo-agendar-calefont` (complejo)
- **hard fail del juez**: Pide el nombre y luego insiste en un diagnóstico de falla antes de responder lo que el cliente pidió (mantención de calefont en Ñuñoa: cobertura, valor y disponibilidad).
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **hard fail del juez**: Cortar la conversación con un rechazo por comuna: afirma que no hay visitas técnicas en Temuquito, cuando la KB indica que fuera de cobertura un asesor coordina la visita.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-enojo-reclamo` (supercomplejo)
- **hard fail del juez**: Siguió el reclamo ofreciendo coordinar una nueva visita técnica en vez de hacerse cargo de la mantención fallida.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-precio-mantencion-ciclo` (simple)
- **hard fail del juez**: Derivó a visita o asesor sin intentar responder la consulta general sobre la periodicidad de la mantención.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-reclamo-real-si-deriva` (supercomplejo)
- **hard fail del juez**: Seguir ofreciendo servicios/agendar y pedir datos de captura («¿Con quién tengo el gusto?», «¿Prefieres que te tome los datos para coordinar una visita...?») a una clienta que acaba de cerrar la relación.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-consulta-otros-equipos` (complejo)
- **hard fail del juez**: Negar de hecho un servicio del catálogo: no confirma el aire acondicionado pese a que aparece en 'Otros servicios que cotizamos'.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

**No comparable**: el corpus cambió entre las dos corridas.
