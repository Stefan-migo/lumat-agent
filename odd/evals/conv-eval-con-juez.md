# Evaluación conversacional — `con-juez`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `d463126a37654d54fb5166bb8ebad6afd36a7d89` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `b47a55889dc3` · KB: `34670f5b3d75` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 2 llamada(s) por escenario (mediana) · inicio: 2026-11-18T11:42:46+00:00

## Resumen

- Escenarios: **42** · pasan: **35**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 12 | 11 |
| complejo | 16 | 11 |
| supercomplejo | 14 | 13 |

### Gates que fallaron

Ninguno.

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 2.79 | ±3 | 42 |
| policy | 2.75 | ±2 | 42 |
| conversational | 1.67 | ±2 | 42 |
| escalation | 3.01 | ±3 | 42 |
| tone | 3.43 | ±1 | 42 |
| closure | 2.13 | ±2 | 42 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-saludo-variante` | simple | 4.00 | ±0 |
| `simple-precio-calefont` | simple | 4.00 | ±0 |
| `simple-cobertura-comuna` | simple | 2.25 | ±2 |
| `simple-horario-sabado` | simple | 3.33 | ±1 |
| `simple-dia-especifico` | simple | 2.92 | ±2 |
| `simple-despedida` | simple | 3.83 | ±0 |
| `complejo-agendar-calefont` | complejo | 2.08 | ±1 |
| `complejo-dos-temas` | complejo | 3.25 | ±1 |
| `complejo-no-quiere-email` | complejo | 3.17 | ±1 |
| `complejo-fuera-de-cobertura-insiste` | complejo | 0.00 | ±2 |
| `super-emergencia-gas` | supercomplejo | 3.50 | ±1 |
| `super-enojo-reclamo` | supercomplejo | 0.00 | ±1 |
| `super-inyeccion` | supercomplejo | 3.17 | ±1 |
| `super-burst-contradiccion` | supercomplejo | 1.83 | ±0 |
| `super-near-miss-lavadora` | supercomplejo | 2.92 | ±1 |
| `real-cortesia-no-es-reclamo` | simple | 3.17 | ±0 |
| `real-precio-mantencion-ciclo` | simple | 3.33 | ±1 |
| `real-cobertura-condominio` | simple | 3.42 | ±1 |
| `real-vocabulario-impreciso` | simple | 0.00 | ±1 |
| `real-dato-mas-pregunta` | complejo | 0.00 | ±1 |
| `real-arrendatario-no-decide` | complejo | 1.92 | ±3 |
| `real-multi-equipo-un-mensaje` | complejo | 3.08 | ±1 |
| `real-solo-sabados` | complejo | 2.17 | ±2 |
| `real-reagenda-familiar` | complejo | 2.67 | ±2 |
| `real-postventa-al-dia-siguiente` | supercomplejo | 2.75 | ±1 |
| `real-olor-gas-en-hilo` | supercomplejo | 3.50 | ±3 |
| `real-cotizacion-fuera-catalogo` | supercomplejo | 3.00 | ±1 |
| `real-repuesto-agotado` | supercomplejo | 1.42 | ±1 |
| `real-cliente-experto` | supercomplejo | 3.25 | ±1 |
| `real-reclamo-real-si-deriva` | supercomplejo | 2.25 | ±1 |
| `real-varias-reparaciones` | complejo | 0.83 | ±1 |
| `real-mantencion-caldera` | simple | 3.00 | ±1 |
| `real-reagenda-mantencion` | complejo | 2.33 | ±1 |
| `real-revision-bano-ruidoso` | complejo | 0.92 | ±1 |
| `real-caldera-urgencia` | supercomplejo | 2.67 | ±1 |
| `real-fuga-gas-bodega` | supercomplejo | 3.08 | ±1 |
| `real-consulta-otros-equipos` | complejo | 0.00 | ±1 |
| `real-claudio-caldera-valvula` | complejo | 0.00 | ±1 |
| `real-diego-precio-y-duracion` | complejo | 0.00 | ±1 |
| `real-hector-discrepancia-valor` | simple | 2.42 | ±1 |
| `real-maria-jesus-evaluacion-caldera` | supercomplejo | 2.25 | ±2 |
| `real-monica-diagnostico-no-confirmado` | complejo | 2.83 | ±2 |

## Escenarios que no pasan

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **hard fail del juez**: Cortó la conversación con un rechazo por comuna: 'Todavía no tenemos visitas técnicas en Temuquito para tu caldera'.
- puntaje: 0.00 (capeado a 0 por el gate)

### `super-enojo-reclamo` (supercomplejo)
- **hard fail del juez**: Minimiza el reclamo justificando que la mantención es preventiva y no incluye reparaciones, y deriva a "una revisión aparte" (nuevo servicio) en vez de hacerse cargo y gestionar la garantía de la mantención mediante visita técnica.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-vocabulario-impreciso` (simple)
- **hard fail del juez**: Inventar alcance: afirma que trabajan con quemadores de cocina a gas y ofrece la visita, sin que ese servicio esté listado en la base de conocimiento.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-dato-mas-pregunta` (complejo)
- **hard fail del juez**: Ignorar la pregunta que acompaña a los datos: la clienta preguntó por horarios ('y mañana?', 'es factible que pases tipo 14 horas?') y el bot respondió con preguntas de diagnóstico y derivó sin atender esa consulta concreta.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-consulta-otros-equipos` (complejo)
- **hard fail del juez**: Afirma que Lumat realiza mantención/servicio de bomba de calor de piscina sin respaldo en la base de conocimiento (que excluye artefactos fuera de la lista) e inventa un 'caso abierto' del cliente por ese equipo y por aire acondicionado.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-claudio-caldera-valvula` (complejo)
- **hard fail del juez**: Indicó cortar la llave de agua de la caldera sin verificar el equipo ni la situación, entregando instrucciones improvisadas sobre válvulas.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-diego-precio-y-duracion` (complejo)
- **hard fail del juez**: Ignorar la restricción de salida y regreso del cliente (2 pm–4 pm) y responder con preguntas de diagnóstico en vez de abordarla.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

**No comparable**: el corpus cambió entre las dos corridas.
