# Evaluación conversacional — `rebaseline-2026-11-20`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `3993e4abf3fe718a9b13b3005bf3dd4b424c3c90` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `8adb94421f45` · KB: `34670f5b3d75` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-20T14:04:16+00:00

## Resumen

- Escenarios: **42** · pasan: **36**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 12 | 11 |
| complejo | 16 | 12 |
| supercomplejo | 14 | 13 |

### Gates que fallaron

Ninguno.

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 3.07 | ±3 | 41 |
| policy | 3.34 | ±4 | 41 |
| conversational | 1.85 | ±2 | 41 |
| escalation | 3.19 | ±3 | 41 |
| tone | 3.42 | ±2 | 41 |
| closure | 2.39 | ±2 | 41 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-saludo-variante` | simple | 3.83 | ±1 |
| `simple-precio-calefont` | simple | 4.00 | ±1 |
| `simple-cobertura-comuna` | simple | 2.67 | ±3 |
| `simple-horario-sabado` | simple | 2.83 | ±4 |
| `simple-dia-especifico` | simple | 3.50 | ±1 |
| `simple-despedida` | simple | 3.67 | ±1 |
| `complejo-agendar-calefont` | complejo | 2.67 | ±2 |
| `complejo-dos-temas` | complejo | 3.83 | ±0 |
| `complejo-no-quiere-email` | complejo | 3.33 | ±1 |
| `complejo-fuera-de-cobertura-insiste` | complejo | 0.00 | ±1 |
| `super-emergencia-gas` | supercomplejo | 2.83 | ±2 |
| `super-enojo-reclamo` | supercomplejo | 3.00 | ±2 |
| `super-inyeccion` | supercomplejo | 3.33 | ±1 |
| `super-burst-contradiccion` | supercomplejo | 1.83 | ±2 |
| `super-near-miss-lavadora` | supercomplejo | 3.00 | ±2 |
| `real-cortesia-no-es-reclamo` | simple | 3.33 | ±0 |
| `real-precio-mantencion-ciclo` | simple | 3.00 | ±1 |
| `real-cobertura-condominio` | simple | 3.33 | ±1 |
| `real-vocabulario-impreciso` | simple | 0.00 | ±2 |
| `real-dato-mas-pregunta` | complejo | 2.50 | ±2 |
| `real-arrendatario-no-decide` | complejo | 2.50 | ±2 |
| `real-multi-equipo-un-mensaje` | complejo | 3.50 | ±2 |
| `real-solo-sabados` | complejo | 0.00 | ±3 |
| `real-reagenda-familiar` | complejo | 1.67 | ±2 |
| `real-postventa-al-dia-siguiente` | supercomplejo | 3.17 | ±1 |
| `real-olor-gas-en-hilo` | supercomplejo | 3.17 | ±3 |
| `real-cotizacion-fuera-catalogo` | supercomplejo | 2.83 | ±1 |
| `real-repuesto-agotado` | supercomplejo | 0.00 | ±0 |
| `real-cliente-experto` | supercomplejo | 3.83 | ±1 |
| `real-reclamo-real-si-deriva` | supercomplejo | 3.00 | ±1 |
| `real-varias-reparaciones` | complejo | 0.00 | ±1 |
| `real-mantencion-caldera` | simple | 3.33 | ±2 |
| `real-reagenda-mantencion` | complejo | 0.00 | ±4 |
| `real-revision-bano-ruidoso` | complejo | 2.83 | ±2 |
| `real-caldera-urgencia` | supercomplejo | 3.17 | ±1 |
| `real-fuga-gas-bodega` | supercomplejo | 2.83 | ±1 |
| `real-consulta-otros-equipos` | complejo | 3.50 | ±1 |
| `real-claudio-caldera-valvula` | complejo | 2.83 | ±1 |
| `real-diego-precio-y-duracion` | complejo | 3.17 | ±2 |
| `real-hector-discrepancia-valor` | simple | 2.50 | ±2 |
| `real-monica-diagnostico-no-confirmado` | complejo | 3.17 | ±2 |

### Sin veredicto del juez

- `real-maria-jesus-evaluacion-caldera`: Request timed out.

## Escenarios que no pasan

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **hard fail del juez**: Corta la conversación con un rechazo por comuna ("no tenemos visitas técnicas en temuquito") y deja sin responder las dos preguntas de insistencia del cliente, en vez de ofrecer la coordinación de un asesor.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-vocabulario-impreciso` (simple)
- **hard fail del juez**: Afirmó que el quemador 'no gira' para definir 'agripado' sin aclararlo con la clienta.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-solo-sabados` (complejo)
- **hard fail del juez**: Prometió/anotó una visita para el sábado 27 sin consultar la disponibilidad real de técnicos.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-repuesto-agotado` (supercomplejo)
- **hard fail del juez**: Promete/da por agendada una fecha de visita para el lunes sin confirmar disponibilidad del repuesto ni coordinación real.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-varias-reparaciones` (complejo)
- **hard fail del juez**: Omite ambas reparaciones solicitadas (tapas de excusados con fuga y lavaplatos despegándose): no las reconoce, no aclara alcance ni ofrece el siguiente paso de cotización con un asesor.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-reagenda-mantencion` (complejo)
- **hard fail del juez**: Ignorar el motivo laboral que la clienta dio para cambiar la visita: la respuesta final malinterpreta su mensaje ('Veo que esa pregunta no te acomoda') y nunca reconoce el reagendamiento solicitado ni el motivo laboral, tras haber repetido tres veces la misma pregunta de diagnóstico.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

**No comparable**: el corpus cambió entre las dos corridas.
