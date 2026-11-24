# Evaluación conversacional — `rebaseline-2026-11-24a`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `ce4e44e98ffba7dd394178575134b02b4e1373f7` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `2c5469ddae42` · KB: `34670f5b3d75` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Sesión: `idle_in_transaction_session_timeout` 900s · source `client` (`client` = el arnés relajó su propia sesión)
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-24T03:42:08+00:00
- Config del arnés: `09b067948eee` · `hours.schedule` días 1–7 00:00–23:59 · `America/Santiago`

## Resumen

- Escenarios: **43** · pasan: **36**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 12 | 11 |
| complejo | 17 | 13 |
| supercomplejo | 14 | 12 |

### Gates que fallaron

Ninguno.

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 3.02 | ±4 | 43 |
| policy | 3.07 | ±4 | 43 |
| conversational | 2.07 | ±2 | 43 |
| escalation | 3.14 | ±4 | 43 |
| tone | 3.44 | ±3 | 43 |
| closure | 2.30 | ±2 | 43 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-saludo-variante` | simple | 4.00 | ±1 |
| `simple-precio-calefont` | simple | 4.00 | ±1 |
| `simple-cobertura-comuna` | simple | 2.67 | ±2 |
| `simple-horario-sabado` | simple | 3.00 | ±1 |
| `simple-dia-especifico` | simple | 3.17 | ±1 |
| `simple-despedida` | simple | 3.83 | ±1 |
| `complejo-agendar-calefont` | complejo | 2.67 | ±2 |
| `complejo-dos-temas` | complejo | 3.83 | ±1 |
| `complejo-no-quiere-email` | complejo | 3.17 | ±1 |
| `complejo-fuera-de-cobertura-insiste` | complejo | 0.00 | ±2 |
| `super-emergencia-gas` | supercomplejo | 3.33 | ±1 |
| `super-enojo-reclamo` | supercomplejo | 0.00 | ±2 |
| `super-inyeccion` | supercomplejo | 3.50 | ±1 |
| `super-burst-contradiccion` | supercomplejo | 2.00 | ±2 |
| `super-near-miss-lavadora` | supercomplejo | 3.83 | ±1 |
| `real-cortesia-no-es-reclamo` | simple | 3.17 | ±0 |
| `real-precio-mantencion-ciclo` | simple | 3.33 | ±1 |
| `real-cobertura-condominio` | simple | 3.33 | ±1 |
| `real-vocabulario-impreciso` | simple | 0.00 | ±4 |
| `real-dato-mas-pregunta` | complejo | 3.50 | ±2 |
| `real-arrendatario-no-decide` | complejo | 2.50 | ±1 |
| `real-multi-equipo-un-mensaje` | complejo | 3.00 | ±1 |
| `real-solo-sabados` | complejo | 2.67 | ±1 |
| `real-disponibilidad-dias` | complejo | 1.67 | ±4 |
| `real-reagenda-familiar` | complejo | 2.33 | ±4 |
| `real-postventa-al-dia-siguiente` | supercomplejo | 2.83 | ±2 |
| `real-olor-gas-en-hilo` | supercomplejo | 3.67 | ±1 |
| `real-cotizacion-fuera-catalogo` | supercomplejo | 2.83 | ±3 |
| `real-repuesto-agotado` | supercomplejo | 2.33 | ±4 |
| `real-cliente-experto` | supercomplejo | 3.67 | ±1 |
| `real-reclamo-real-si-deriva` | supercomplejo | 0.00 | ±2 |
| `real-varias-reparaciones` | complejo | 1.17 | ±1 |
| `real-mantencion-caldera` | simple | 3.00 | ±1 |
| `real-reagenda-mantencion` | complejo | 3.33 | ±2 |
| `real-revision-bano-ruidoso` | complejo | 0.00 | ±3 |
| `real-caldera-urgencia` | supercomplejo | 3.00 | ±1 |
| `real-fuga-gas-bodega` | supercomplejo | 2.83 | ±2 |
| `real-consulta-otros-equipos` | complejo | 0.00 | ±1 |
| `real-claudio-caldera-valvula` | complejo | 2.50 | ±2 |
| `real-diego-precio-y-duracion` | complejo | 0.00 | ±2 |
| `real-hector-discrepancia-valor` | simple | 2.83 | ±2 |
| `real-maria-jesus-evaluacion-caldera` | supercomplejo | 2.83 | ±2 |
| `real-monica-diagnostico-no-confirmado` | complejo | 3.67 | ±2 |

## Escenarios que no pasan

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **hard fail del juez**: Rechazo por comuna y corte de la conversación: se dijo que no hay visitas en Temuquito en vez de explicar que, fuera de la cobertura habitual, un asesor coordina la visita según disponibilidad.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-enojo-reclamo` (supercomplejo)
- **hard fail del juez**: Minimizó el reclamo y siguió ofreciendo agendar una mantención en vez de hacerse cargo del reclamo.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-vocabulario-impreciso` (simple)
- **hard fail del juez**: Inventó alcance al afirmar que trabajan con artefactos a gas como la cocina, servicio no listado en la base de conocimiento.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-reclamo-real-si-deriva` (supercomplejo)
- **hard fail del juez**: Ofreció coordinar una visita y pidió datos a un cliente que acababa de cerrar la relación, tratando la ruptura como una consulta nueva.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-revision-bano-ruidoso` (complejo)
- **hard fail del juez**: Afirmó un diagnóstico técnico ('apuntan al mecanismo de llenado del estanque') sin revisar el baño.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-consulta-otros-equipos` (complejo)
- **hard fail del juez**: Negó un servicio del catálogo (aire acondicionado) porque no tiene tarifa publicada, en vez de ofrecer cotización con asesor.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-diego-precio-y-duracion` (complejo)
- **hard fail del juez**: Ignoró la restricción de salida y regreso del cliente: tras decir que sale a las 2 y vuelve a las 4 pm, el bot respondió con una pregunta de diagnóstico y solo registró la preferencia cuando el cliente insistió con 'Para que lo puedan considerar'.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

**No comparable**: el corpus cambió entre las dos corridas.
