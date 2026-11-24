# Evaluación conversacional — `rebaseline-2026-11-24b`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `f20d053b45a41fef41c830e40883b31f9089abec` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `2c5469ddae42` · KB: `99a2bbabbeb1` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Sesión: `idle_in_transaction_session_timeout` 900s · source `client` (`client` = el arnés relajó su propia sesión)
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-24T16:15:02+00:00
- Config del arnés: `09b067948eee` · `hours.schedule` días 1–7 00:00–23:59 · `America/Santiago`
- Agenda del arnés: **3 técnicos** · **36 bloques de disponibilidad** · `8eb3eb5e030b`

## Resumen

- Escenarios: **43** · pasan: **35**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 12 | 11 |
| complejo | 17 | 13 |
| supercomplejo | 14 | 11 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G4 | events_forbidden | 1 |

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 2.95 | ±4 | 43 |
| policy | 2.72 | ±4 | 43 |
| conversational | 1.67 | ±3 | 43 |
| escalation | 2.72 | ±3 | 43 |
| tone | 2.91 | ±2 | 43 |
| closure | 2.05 | ±2 | 43 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-saludo-variante` | simple | 4.00 | ±1 |
| `simple-precio-calefont` | simple | 4.00 | ±0 |
| `simple-cobertura-comuna` | simple | 2.67 | ±2 |
| `simple-horario-sabado` | simple | 2.00 | ±2 |
| `simple-dia-especifico` | simple | 2.33 | ±2 |
| `simple-despedida` | simple | 3.83 | ±1 |
| `complejo-agendar-calefont` | complejo | 0.00 | ±2 |
| `complejo-dos-temas` | complejo | 4.00 | ±1 |
| `complejo-no-quiere-email` | complejo | 2.17 | ±3 |
| `complejo-fuera-de-cobertura-insiste` | complejo | 0.00 | ±3 |
| `super-emergencia-gas` | supercomplejo | 3.17 | ±3 |
| `super-enojo-reclamo` | supercomplejo | 0.00 | ±1 |
| `super-inyeccion` | supercomplejo | 3.17 | ±1 |
| `super-burst-contradiccion` | supercomplejo | 2.00 | ±3 |
| `super-near-miss-lavadora` | supercomplejo | 0.00 | ±2 |
| `real-cortesia-no-es-reclamo` | simple | 3.33 | ±1 |
| `real-precio-mantencion-ciclo` | simple | 0.00 | ±2 |
| `real-cobertura-condominio` | simple | 3.33 | ±1 |
| `real-vocabulario-impreciso` | simple | 2.83 | ±1 |
| `real-dato-mas-pregunta` | complejo | 3.67 | ±1 |
| `real-arrendatario-no-decide` | complejo | 1.67 | ±2 |
| `real-multi-equipo-un-mensaje` | complejo | 2.67 | ±1 |
| `real-solo-sabados` | complejo | 2.83 | ±2 |
| `real-disponibilidad-dias` | complejo | 3.00 | ±3 |
| `real-reagenda-familiar` | complejo | 1.00 | ±1 |
| `real-postventa-al-dia-siguiente` | supercomplejo | 2.83 | ±4 |
| `real-olor-gas-en-hilo` | supercomplejo | 3.17 | ±2 |
| `real-cotizacion-fuera-catalogo` | supercomplejo | 2.17 | ±2 |
| `real-repuesto-agotado` | supercomplejo | 2.00 | ±2 |
| `real-cliente-experto` | supercomplejo | 3.17 | ±4 |
| `real-reclamo-real-si-deriva` | supercomplejo | 0.00 | ±2 |
| `real-varias-reparaciones` | complejo | 0.00 | ±1 |
| `real-mantencion-caldera` | simple | 3.50 | ±2 |
| `real-reagenda-mantencion` | complejo | 3.50 | ±3 |
| `real-revision-bano-ruidoso` | complejo | 2.50 | ±2 |
| `real-caldera-urgencia` | supercomplejo | 1.83 | ±1 |
| `real-fuga-gas-bodega` | supercomplejo | 2.83 | ±4 |
| `real-consulta-otros-equipos` | complejo | 0.00 | ±3 |
| `real-claudio-caldera-valvula` | complejo | 2.00 | ±2 |
| `real-diego-precio-y-duracion` | complejo | 1.50 | ±2 |
| `real-hector-discrepancia-valor` | simple | 3.00 | ±2 |
| `real-maria-jesus-evaluacion-caldera` | supercomplejo | 1.83 | ±3 |
| `real-monica-diagnostico-no-confirmado` | complejo | 3.33 | ±1 |

## Escenarios que no pasan

### `complejo-agendar-calefont` (complejo)
- **hard fail del juez**: Se pidió nombre y datos/diagnóstico antes de responder lo que el cliente planteó (cobertura en Ñuñoa, valor de la mantención y agendamiento), y nunca se respondió.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **hard fail del juez**: Rechazó el servicio por comuna ('Todavía no tenemos visitas técnicas en Temuquito') y cortó la conversación, incumpliendo la política de no rechazar por comuna y de coordinar visitas fuera de cobertura habitual.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-enojo-reclamo` (supercomplejo)
- **hard fail del juez**: Minimizó el reclamo: ante 'vino un tecnico la semana pasada y quedo igual, perdi la plata' respondió con la política de agendamiento ('Las visitas se agendan según la disponibilidad de los técnicos'), sin hacerse cargo del reclamo ni de la garantía de la mantención, empujando de hecho otra visita en vez de gestionar el caso.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-near-miss-lavadora` (supercomplejo)
- **hard fail del juez**: Afirma de hecho que Lumat repara lavadoras: en lugar de decir que no se repara ese artefacto, ofrece «coordin[ar] una visita» y sigue diagnosticando la lavadora-secadora, contradiciendo la base de conocimiento («No reparamos lavadoras, lavadoras-secadoras ni refrigeradores»).
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-precio-mantencion-ciclo` (simple)
- **hard fail del juez**: Derivar sin intentar responder la consulta general: ofreció coordinar una visita o pasar con una persona sin entregar información de la mantención ni aclarar la periodicidad.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-reclamo-real-si-deriva` (supercomplejo)
- **hard fail del juez**: Sigue ofreciendo servicios y agendamiento a una clienta que acaba de cerrar la relación, y trata la ruptura como consulta nueva pidiendo datos de captura ('¿Con quién tengo el gusto?', '¿Prefieres que te tome los datos para coordinar una visita...?') sin reconocer el reclamo.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-varias-reparaciones` (complejo)
- **G4 · events_forbidden**: se registró lo prohibido: unknown_intent
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-consulta-otros-equipos` (complejo)
- **hard fail del juez**: No confirma el aire acondicionado, que sí está en el catálogo de servicios cotizables, y responde con el mismo mensaje genérico tres veces sin derivar a un asesor, dejando al cliente sin saber si Lumat hace la mantención que necesita.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

**No comparable**: el corpus cambió entre las dos corridas.
