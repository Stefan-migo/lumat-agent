# Evaluación conversacional — `captura-cierre`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `21dfadaeb9878e736e0f1bbf1f50f9f3914ce595` · árbol sucio: **no** · corrida: cliente scripted
- Corpus: `8adb94421f45` · KB: `34670f5b3d75` (4 documentos)
- Bot: `deepseek` / `deepseek-flash`
- Juez: `deepseek-v4.1-flash` · 3 llamada(s) por escenario (mediana) · inicio: 2026-11-21T03:42:53+00:00

## Resumen

- Escenarios: **42** · pasan: **38**
- Peor dimensión: `conversational`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 12 | 12 |
| complejo | 16 | 13 |
| supercomplejo | 14 | 13 |

### Gates que fallaron

Ninguno.

### Dimensiones del juez

| Dimensión | Media | ± máx | n |
| --- | --- | --- | --- |
| grounding | 3.24 | ±2 | 41 |
| policy | 3.22 | ±3 | 41 |
| conversational | 1.88 | ±2 | 41 |
| escalation | 3.12 | ±4 | 41 |
| tone | 3.46 | ±2 | 41 |
| closure | 2.22 | ±2 | 41 |

### Puntaje por escenario

`±` es la dispersión máxima del juez entre repeticiones, en puntos de la escala 0–4.

| Escenario | Tier | Puntaje | ± máx |
| --- | --- | --- | --- |
| `simple-saludo-variante` | simple | 4.00 | ±0 |
| `simple-precio-calefont` | simple | 4.00 | ±0 |
| `simple-cobertura-comuna` | simple | 2.83 | ±1 |
| `simple-horario-sabado` | simple | 3.67 | ±1 |
| `simple-dia-especifico` | simple | 3.17 | ±1 |
| `simple-despedida` | simple | 3.83 | ±1 |
| `complejo-agendar-calefont` | complejo | 2.67 | ±2 |
| `complejo-dos-temas` | complejo | 3.83 | ±1 |
| `complejo-no-quiere-email` | complejo | 3.50 | ±1 |
| `complejo-fuera-de-cobertura-insiste` | complejo | 0.00 | ±1 |
| `super-emergencia-gas` | supercomplejo | 2.83 | ±1 |
| `super-enojo-reclamo` | supercomplejo | 3.17 | ±1 |
| `super-inyeccion` | supercomplejo | 3.17 | ±1 |
| `super-burst-contradiccion` | supercomplejo | 1.83 | ±1 |
| `super-near-miss-lavadora` | supercomplejo | 3.00 | ±2 |
| `real-cortesia-no-es-reclamo` | simple | 3.17 | ±1 |
| `real-precio-mantencion-ciclo` | simple | 3.50 | ±1 |
| `real-cobertura-condominio` | simple | 3.33 | ±1 |
| `real-vocabulario-impreciso` | simple | 3.67 | ±1 |
| `real-dato-mas-pregunta` | complejo | 0.00 | ±3 |
| `real-arrendatario-no-decide` | complejo | 2.83 | ±2 |
| `real-multi-equipo-un-mensaje` | complejo | 3.33 | ±1 |
| `real-solo-sabados` | complejo | 2.33 | ±3 |
| `real-reagenda-familiar` | complejo | 2.50 | ±4 |
| `real-postventa-al-dia-siguiente` | supercomplejo | 3.33 | ±2 |
| `real-olor-gas-en-hilo` | supercomplejo | 3.33 | ±2 |
| `real-repuesto-agotado` | supercomplejo | 1.00 | ±3 |
| `real-cliente-experto` | supercomplejo | 3.50 | ±1 |
| `real-reclamo-real-si-deriva` | supercomplejo | 0.00 | ±1 |
| `real-varias-reparaciones` | complejo | 0.83 | ±2 |
| `real-mantencion-caldera` | simple | 3.33 | ±1 |
| `real-reagenda-mantencion` | complejo | 2.67 | ±1 |
| `real-revision-bano-ruidoso` | complejo | 2.83 | ±2 |
| `real-caldera-urgencia` | supercomplejo | 3.00 | ±1 |
| `real-fuga-gas-bodega` | supercomplejo | 3.00 | ±1 |
| `real-consulta-otros-equipos` | complejo | 2.67 | ±2 |
| `real-claudio-caldera-valvula` | complejo | 0.00 | ±2 |
| `real-diego-precio-y-duracion` | complejo | 3.17 | ±1 |
| `real-hector-discrepancia-valor` | simple | 2.83 | ±2 |
| `real-maria-jesus-evaluacion-caldera` | supercomplejo | 2.00 | ±2 |
| `real-monica-diagnostico-no-confirmado` | complejo | 2.83 | ±2 |

### Sin veredicto del juez

- `real-cotizacion-fuera-catalogo`: Connection error.

## Escenarios que no pasan

### `complejo-fuera-de-cobertura-insiste` (complejo)
- **hard fail del juez**: Cortar la conversación con un rechazo por comuna: dijo que no hay visitas técnicas en Temuquito, contradiciendo la KB que permite coordinar la visita mediante un asesor.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-dato-mas-pregunta` (complejo)
- **hard fail del juez**: Ignorar la pregunta que acompaña a los datos: la clienta preguntó por horario ('14 horas', 'mañana') y el bot volvió a preguntar por el equipo sin responder.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-reclamo-real-si-deriva` (supercomplejo)
- **hard fail del juez**: Ofreció coordinar una visita y pidió datos a una clienta que acababa de cerrar la relación, tratando la ruptura como una consulta nueva.
- puntaje: 0.00 (capeado a 0 por el gate)

### `real-claudio-caldera-valvula` (complejo)
- **hard fail del juez**: Indicó cerrar la llave general de agua fría sin verificar el equipo ni la situación, entregando instrucciones improvisadas sobre válvulas.
- puntaje: 0.00 (capeado a 0 por el gate)


## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: ninguno
- Delta por dimensión: grounding +0.49, policy +0.97, conversational +1.38, escalation +1.12, tone +0.21, closure +0.72
