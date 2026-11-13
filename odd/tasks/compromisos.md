# Compromisos — D6 y D10

Dos defectos de `odd/analysis/lumatdata/03-defectos-y-mejoras.md` que son la misma fila vista desde
dos fechas: D6 registra lo que prometemos, D10 detecta que se venció o que el hilo se apagó. D6 va
primero porque D10 sin compromisos no sabe *de qué* escribir.

## Specs

**S1 · D6 — las promesas se registran.**
«Causa: no existe objeto tarea/compromiso. `Case.summary` y `ConversationEvent` no modelan «queda
pendiente de nuestra parte»». «Evidencia: **58** mensajes del dueño con promesa explícita: «le envío el
detalle», «mañana voy», «le confirmo en un rato», «estoy cotizando los repuestos». En el corpus hay
promesas cumplidas tarde (cotización a 29 días en Gonzalo; 6 días en Nerys), incumplidas (Paolo:
cotización eléctrica pedida 5 meses después) y nunca cerradas (Guila: «Le preparo un informe» → sin
documento)». «Es el hallazgo más valioso de su paquete».

**S2 · El compromiso nace de la frase que lo promete, no de una interpretación.**
El registro guarda el texto del mensaje que prometió, literal, más su vencimiento cuando la frase lo
declara. Determinista: sin modelo, sin resumen.

**S3 · Fuera de este corte.** Perseguir el hilo apagado (D10, task T2), la UI del panel y el envío
saliente. La sección del panel es consecuencia del linaje, como en la Fase 3.

## Decisiones de diseño

- **D1 · El vencimiento se parsea, no se adivina.** «hoy», «mañana», «pasado mañana», «el lunes» …
  «el domingo», «en N días», «la próxima semana» dan fecha. «en un rato», «a la brevedad», «estoy
  cotizando» no dan fecha: el compromiso queda sin vencimiento y no se marca vencido. Inventar una
  fecha es peor que no tenerla.
- **D2 · Se registra lo que el humano promete; las promesas del bot quedan fuera de este corte.**
  El corpus mide los mensajes del dueño, que es donde está la mora. Las respuestas fijas del bot que
  prometen («un asesor de Lumat revisará tu consulta y te contactará») ya crean su obligación por otra
  vía: son la antesala de una derivación que abre o escala un caso. Registrarlas además llenaría la
  tabla con una fila por cada respuesta fija, que es el ruido que vuelve inservible un registro de
  compromisos. El campo `actor` existe igual, para el día que se decida incluirlas.
- **D3 · Una promesa ya registrada no se duplica.** El mismo mensaje no crea dos filas.

## Tasks

| ID | Specs | Route | Commit |
|---|---|---|---|
| T1 | S1, S2, S3 | Modelo `Commitment` + migración `066` + extractor determinista en el envío del operador | `feat(commitments):` propio (item 1) |
| T2 | — | D10: detector de hilo apagado y envío detrás de bandera (handoff posterior) | `feat(commitments):` |

## Log

**L1 — pedido del owner (verbatim).**

```
- ok d6 lo iniciamos entonces
```
