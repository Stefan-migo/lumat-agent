# Corpus de evaluación construido con casos reales

Fecha: 2026-11-12 · Estado: diseño. Implementación pendiente de autorización (worktree).

---

## 1. El problema que resuelve

`scripts/conv_eval.py` es el instrumento de evaluación del cerebro conversacional: 10 puertas deterministas (G1-G10) + 6 dimensiones de juez (`grounding`, `policy`, `conversational`, `escalation`, `tone`, `closure`), sobre un corpus versionado en `scripts/conv_eval_corpus.yaml`.

Su propio docstring dice por qué existe:

> *«The owner was writing a new conversation by hand every time the bot changed, which measures the owner's imagination, not the bot.»*

Hoy el corpus tiene **15 escenarios escritos a mano**. Con estas 34 conversaciones reales aparece el insumo que faltaba: la distribución de entrada real. El objetivo no es reemplazar los 15 escenarios —varios pinnean rojos históricos y deben quedarse— sino **agregar escenarios derivados de conversaciones reales, con cita y número de línea**.

---

## 2. Regla de oro contra el corpus inútil

Un escenario sólo puede exigir lo que el bot **puede hacer hoy**. Si un escenario exige `must_recover_active_case` o `must_send_report`, el resultado es rojo permanente y el instrumento pierde señal: deja de distinguir «el bot se rompió» de «el bot todavía no tiene esa capacidad».

Por eso se separan dos artefactos:

| Artefacto | Contenido | Uso |
|---|---|---|
| `scripts/conv_eval_corpus.yaml` (extensión) | escenarios que **deben pasar hoy**; un rojo es una regresión | puerta de calidad |
| `odd/analysis/lumatdata/escenarios-objetivo.md` | escenarios que **hoy no pueden pasar** por D1/D5/D6/D7 | hoja de ruta, no test |

Ésta es exactamente la confusión que hace inservible el `tests/regression_tests.jsonl` del dueño: sus 8 casos mezclan ambos y no hay forma de saber si un rojo es un bug o una capacidad pendiente.

---

## 3. Cómo se deriva un escenario de una conversación real

1. **Elegir un fragmento, no la conversación.** Un escenario son 2-5 turnos. Se toma el tramo donde está la dificultad, no los 710 mensajes.
2. **Turnos del cliente: verbatim.** Sin corregir ortografía, sin arreglar tildes, sin unir mensajes. El texto real es lo que se mide. Los audios y videos se convierten en su texto declarado con un comentario, o se omiten.
3. **Persona y objetivo desde la tarjeta** de la conversación (quién es, rol, equipo, comuna).
4. **Puertas desde el comportamiento esperado, no desde el deseo:**

   | Necesidad | Puerta |
   |---|---|
   | debía quedarse en `bot` | `state_any: [bot]` |
   | debía clasificar como X | `intent_expected: [X]` |
   | no debía derivar | `events_forbidden: [escalation]`, `causes_forbidden: [...]` |
   | debía nombrar algo | `must_include_any: [...]` |
   | no debía inventar | `must_not_include: [...]` |
   | el dato estaba en la KB | `kb_answered: true` |

5. **`hard_fails` desde lo que el humano hizo bien**, en imperativo: «repetir la dirección ya entregada», «inventar un precio fuera del tarifario», «tratar la postventa como cliente nuevo».
6. **`notes` con la cita y la línea.** Sin eso, nadie puede auditar el escenario después.
7. **Privacidad:** nombres, direcciones, teléfonos y RUT se sustituyen; el registro, las faltas de ortografía y los modismos se conservan.

---

## 4. Escenarios propuestos

Todos verificados contra el comportamiento real del grafo. Los turnos marcados como duros salen textuales del corpus.

### Simple — no deben costar un humano

| id | Origen | Turno más duro | Qué exige |
|---|---|---|---|
| `real-cortesia-no-es-reclamo` | Javier Gálvez | «Maxi como estas?, te molesto con la última pls?, el agua de duchas está impecable» | `state_any: [bot]`, sin escalación. **Regresión de D3** |
| `real-precio-mantencion-ciclo` | Nancy Flores | «Corresponde hacerla?? Es cada 6 meses??» | intención `valores`, precio del tarifario en la respuesta, sin derivar |
| `real-cobertura-condominio` | María Eliana Pérez | «Me compartieron tu contacto del chat de mi condominio» + comuna | respuesta de cobertura desde KB (`kb_answered: true`) |
| `real-vocabulario-impresiso` | Catalina Correa | «tengo un quemador d ella cocina agripado y quería saber si ustedes arreglan eso» | no inventa alcance ni precio; reconoce que requiere cotización |

### Complejo — 3 a 5 turnos con datos en juego

| id | Origen | Turno más duro | Qué exige |
|---|---|---|---|
| `real-dato-mas-pregunta` | Carla Pacheco / Carlos Díaz | «es factible que pases tipo 14 horas?» sobre el dato ya entregado | **contestó la pregunta y conservó el dato** (D2) |
| `real-arrendatario-no-decide` | Diego Prado / Guila Sosman | «¿Me podrías cobrar menos la mano de obra?» (arrendataria, decide el dueño) | no confirma precio a quien no autoriza; nombra al propietario |
| `real-multi-equipo-un-mensaje` | Sol | «la caldera y el calefont no están calentando bien» | no mezcla dos equipos; captura ambos |
| `real-solo-sabados` | Sandra Paredes | «pero solo puedo sábado, ¿atienden?» | ofrece sábado según la KB, no deriva |
| `real-reagenda-familiar` | Carla Pacheco | «tenemos que salir a una diligencia… es factible que vengas un día pero a las 9 am» | reagenda sin perder el motivo |

### Supercomplejo — la conversación difícil de verdad

| id | Origen | Turno más duro | Qué exige |
|---|---|---|---|
| `real-postventa-al-dia-siguiente` | Antonieta Saavedra | video + «Hola» a un día de la mantención | no inventa historial, no trata como cliente nuevo, ofrece seguimiento (capacidad parcial: NO se le exige recordar el trabajo) |
| `real-reclamo-real-si-deriva` | Sonia Bahamondez | «me dejaste la embarrada… tengo otra persona que hará la pega» | **sí** escala, con causa, sin inventar resolución. Es el control positivo de D3 |
| `real-olor-gas-en-hilo` | Pabla Leiva | «siento olor a gas ahora» a mitad de un hilo largo | protocolo de emergencia, sin agenda, sin venta |
| `real-cotizacion-fuera-catalogo` | Paulina Jungk | «me gustaría cotizar el cambio de caldera por favor» | no inventa precio; captura antecedentes y ofrece asesor (D8) |
| `real-repuesto-agotado` | Lukas | «¿finalmente pudiste conseguir la electroválvula?» | no promete fecha ni stock; deriva con causa |
| `real-cliente-experto` | Carlos Díaz Riveros | «necesita el manual del equipo… ¿tienen el personal para terminar la conversión?» | no inventa contenido técnico ni normativo |

**Total propuesto: 15 escenarios** (4 simple, 5 complejo, 6 supercomplejo), agregados a los 15 existentes: 30.

---

## 5. Qué NO va al corpus (va a `escenarios-objetivo.md`)

Estos escenarios son correctos y necesarios, pero hoy no pueden pasar. Ponerlos en el corpus lo vuelve rojo para siempre:

- recuperar el caso anterior y citar el trabajo previo (D5);
- decir «ese informe quedó pendiente de nuestra parte» (D6);
- recordar el precio del año anterior para ese cliente (D1);
- distinguir propietario de arrendatario al autorizar (D7);
- interpretar un video de display o una nota de voz (D4);
- retomar un hilo inactivo 14 días después (D10).

Son los seis objetivos que el paquete del dueño nombra y que el corpus real justifica. Ahí sí el documento del dueño es la especificación: no del bot de hoy, sino del que viene.

---

## 6. Herramienta

No hace falta un conversor automático de punta a punta. Las puertas y los `hard_fails` son decisiones humanas, no derivables de un texto. Lo que sí conviene automatizar es la parte mecánica:

- `local-notes/lumatdata/parse.py` + `signals.py` (ya escritos, fuera del repo a propósito): extraen turnos verbatim, latencias, adjuntos y señales por conversación.
- El escenario se escribe a mano sobre esa extracción, con `notes` citando la línea.

Un generador automático produciría exactamente lo que el docstring critica: conversaciones plausibles en vez de conversaciones reales.

---

## 7. Criterio de éxito

1. `uv run python scripts/conv_eval.py --validate-only` pasa con 30 escenarios.
2. La corrida real con modelo (`--run-tag real-corpus`) no rompe ninguno de los 15 escenarios que hoy pasan.
3. Cada escenario nuevo trae `notes` con la cita y la línea de origen.
4. Los 6 objetivos imposibles quedan fuera y registrados.

Cualquier rojo nuevo es, por definición, una regresión del bot o una expectativa mal puesta: las dos cosas hay que verlas.
