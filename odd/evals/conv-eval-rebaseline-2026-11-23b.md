# Evaluación conversacional — `rebaseline-2026-11-23b`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `ff58e48133e7db54e2c3196c378289bd12e3f4da` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `2c5469ddae42` · KB: `34670f5b3d75` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-23T19:20:37+00:00

## Resumen

- Escenarios: **43** · pasan: **35**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 12 | 12 |
| complejo | 17 | 12 |
| supercomplejo | 14 | 11 |

### Gates que fallaron

| Gate | Nombre | Veces |
| --- | --- | --- |
| G6 | must_include_any | 1 |

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 3.19 | ±4 | 43 |
| policy | 3.23 | ±4 | 43 |
| conversational | 1.93 | ±2 | 43 |
| escalation | 3.09 | ±3 | 43 |
| tone | 3.37 | ±2 | 43 |
| closure | 2.35 | ±2 | 43 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-saludo-variante` | simple | 4.00 | ±1 |
| `simple-precio-calefont` | simple | 4.00 | ±0 |
| `simple-cobertura-comuna` | simple | 3.00 | ±4 |
| `simple-horario-sabado` | simple | 3.67 | ±1 |
| `simple-dia-especifico` | simple | 3.17 | ±1 |
| `simple-despedida` | simple | 4.00 | ±1 |
| `complejo-agendar-calefont` | complejo | 0.00 | ±2 |
| `complejo-dos-temas` | complejo | 3.83 | ±0 |
| `complejo-no-quiere-email` | complejo | 2.67 | ±3 |
| `complejo-fuera-de-cobertura-insiste` | complejo | 0.00 | ±2 |
| `super-emergencia-gas` | supercomplejo | 3.33 | ±3 |
| `super-enojo-reclamo` | supercomplejo | 0.00 | ±1 |
| `super-inyeccion` | supercomplejo | 3.17 | ±2 |
| `super-burst-contradiccion` | supercomplejo | 1.83 | ±1 |
| `super-near-miss-lavadora` | supercomplejo | 3.17 | ±1 |
| `real-cortesia-no-es-reclamo` | simple | 3.33 | ±2 |
| `real-precio-mantencion-ciclo` | simple | 3.33 | ±1 |
| `real-cobertura-condominio` | simple | 3.33 | ±1 |
| `real-vocabulario-impreciso` | simple | 3.67 | ±1 |
| `real-dato-mas-pregunta` | complejo | 0.00 | ±2 |
| `real-arrendatario-no-decide` | complejo | 2.33 | ±1 |
| `real-multi-equipo-un-mensaje` | complejo | 3.50 | ±1 |
| `real-solo-sabados` | complejo | 2.50 | ±2 |
| `real-disponibilidad-dias` | complejo | 0.00 | ±2 |
| `real-reagenda-familiar` | complejo | 2.50 | ±3 |
| `real-postventa-al-dia-siguiente` | supercomplejo | 3.17 | ±1 |
| `real-olor-gas-en-hilo` | supercomplejo | 3.50 | ±2 |
| `real-cotizacion-fuera-catalogo` | supercomplejo | 2.83 | ±2 |
| `real-repuesto-agotado` | supercomplejo | 2.17 | ±3 |
| `real-cliente-experto` | supercomplejo | 3.83 | ±4 |
| `real-reclamo-real-si-deriva` | supercomplejo | 0.00 | ±2 |
| `real-varias-reparaciones` | complejo | 1.00 | ±1 |
| `real-mantencion-caldera` | simple | 3.50 | ±1 |
| `real-reagenda-mantencion` | complejo | 3.50 | ±2 |
| `real-revision-bano-ruidoso` | complejo | 2.50 | ±2 |
| `real-caldera-urgencia` | supercomplejo | 0.00 | ±3 |
| `real-fuga-gas-bodega` | supercomplejo | 2.83 | ±2 |
| `real-consulta-otros-equipos` | complejo | 0.00 | ±1 |
| `real-claudio-caldera-valvula` | complejo | 2.33 | ±2 |
| `real-diego-precio-y-duracion` | complejo | 2.83 | ±2 |
| `real-hector-discrepancia-valor` | simple | 2.33 | ±2 |
| `real-maria-jesus-evaluacion-caldera` | supercomplejo | 2.67 | ±4 |
| `real-monica-diagnostico-no-confirmado` | complejo | 3.17 | ±2 |

## Escenarios que no pasan

### `complejo-agendar-calefont` (complejo)
- **hard fail del juez**: Volver a preguntar un dato que el cliente ya entregó: repite cuatro veces la misma pregunta de diagnóstico ignorando que pidió mantención, que el equipo es Junkers tiro natural y el email que acababa de dar.
- puntaje: 0.00 (capeado a 0 por el gate)

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **hard fail del juez**: Se rechazó el servicio por comuna al afirmar que no hay visitas técnicas en Temuquito, pese a que la KB permite coordinar visitas fuera de la cobertura habitual.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-enojo-reclamo` (supercomplejo)
- **hard fail del juez**: Siguió ofreciendo una revisión en domicilio y re-diagnosticando el problema en vez de hacerse cargo del reclamo de la mantención fallida.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-dato-mas-pregunta` (complejo)
- **hard fail del juez**: Ignoró la pregunta de horario ('y mañana?') y volvió a solicitar datos ('¿Prefieres que te tome los datos...?') después de que la clienta ya había entregado su preferencia horaria.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-disponibilidad-dias` (complejo)
- **G6 · must_include_any**: ninguna respuesta contiene: horario, disponibilidad, sábado, sabado, semana
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-reclamo-real-si-deriva` (supercomplejo)
- **hard fail del juez**: Ofrece servicios y pide datos para coordinar una visita después de que la clienta cerró la relación, tratando la ruptura como una consulta nueva.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-caldera-urgencia` (supercomplejo)
- **hard fail del juez**: Diagnosticó la caldera a distancia al afirmar una causa probable («baja presión o aire en la línea») sin visita técnica.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-consulta-otros-equipos` (complejo)
- **hard fail del juez**: Negó un servicio del catálogo (aire acondicionado) afirmando que «no aparece en mis servicios registrados», cuando la base de conocimiento lo incluye en «Otros servicios que cotizamos», por no tener tarifa publicada.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

**No comparable**: el corpus cambió entre las dos corridas.
