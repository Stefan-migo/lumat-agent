# Qué estamos midiendo en el chatbot, y qué encontramos

Documento para el equipo de Lumat. Explica, sin tecnicismos, cómo se evalúa hoy el chatbot
de WhatsApp y qué salió de la primera medición completa antes/después.

Fecha: 16 de noviembre de 2026.

---

## 1. La pregunta que queríamos contestar

Durante las últimas semanas se hicieron diez mejoras grandes al chatbot: memoria de la
conversación, transcripción de audios, registro de promesas, ficha del caso, cotizaciones,
clasificación de temas, seguimiento de conversaciones abandonadas.

La pregunta era simple y hasta ahora no tenía respuesta:

> **¿El chatbot mejoró de verdad, o sólo cambió?**

Porque una cosa es que el código compile y las pruebas pasen, y otra muy distinta es que las
conversaciones con clientes reales salgan mejor.

---

## 2. Cómo se mide: un cliente de prueba automático

Imaginá un examen de conducir. Siempre el mismo recorrido, siempre el mismo examinador, para
que dos conductores se puedan comparar de verdad.

Hicimos eso con el chatbot:

- **42 conversaciones de prueba**, escritas a partir de **34 conversaciones reales de WhatsApp**
  que ustedes nos entregaron. Mismos errores de ortografía, mismo español chileno, mismos
  cambios de tema, mismas urgencias.
- Un programa hace de **cliente** y le escribe al chatbot, turno por turno.
- Después se evalúa de dos maneras:
  1. **Reglas fijas**: ¿registró el compromiso? ¿derivó a un humano cuando correspondía?
     ¿contestó el precio que está en el tarifario? Esto no lo juzga nadie, lo verifica un programa.
  2. **Un juez**: otra inteligencia artificial lee la conversación completa y puntúa seis cosas
     de 0 a 4 — qué tan apegado estuvo a la información real, si respetó las reglas, si sonó
     conversacional, si escaló bien, el tono y si cerró.

Cada conversación se evalúa **tres veces** y se toma la mediana, para no depender de la suerte
de una sola respuesta.

---

## 3. La comparación: antes y después

Corrimos exactamente **las mismas 42 conversaciones** contra dos versiones del chatbot:

| | Qué versión | Cuándo |
|---|---|---|
| **Antes** | la anterior a las diez mejoras | commit `4ae76ca1` |
| **Después** | la actual | commit `08560bb1` |

Todo lo demás quedó igual: las mismas conversaciones, la misma base de conocimiento, el mismo
juez. La única diferencia entre las dos corridas es el chatbot.

---

## 4. El resultado general

| | Antes | Después |
|---|---|---|
| Conversaciones aprobadas | 26 de 41 | **25 de 41** |

**El número casi no se movió.** Y esa es justamente la razón para no mirar sólo el número:
adentro pasaron cosas muy distintas y algunas son graves.

---

## 5. Lo que mejoró

El chatbot mejoró mucho en **cómo reacciona a la emoción del cliente**. Tres casos que antes
sacaban cero hoy sacan más de 2.5 sobre 4.

### Ejemplo real: la cortesía chilena

> **Cliente:** «[nombre] como estás?, **te molesto** con la última pls?, el agua de duchas está impecable»
>
> **Antes:** el chatbot leía «te molesto» como reclamo y **derivaba a un humano** sin responder.
> **Puntaje: 0 de 4.**
>
> **Ahora:** «Con gusto. ¿En qué más te puedo ayudar?»
> **Puntaje: 3.33 de 4.**

Esa expresión —«te molesto»— es cortesía, no queja. La versión anterior la confundía siempre.

### Lo mismo con el enojo

El caso del cliente enojado pasó de **0 a 3.17**. Y el chatbot dejó de prometer atención en
sábado sin revisar la agenda real de técnicos (de **0 a 2.5**).

---

## 6. Lo que empeoró, y es lo más importante de este informe

Dos casos de **emergencia con gas** pasaron de aprobados a **0 de 4**, con la peor nota posible
en «respetó las reglas».

### Ejemplo real: fuga de gas en una bodega

> **Cliente:** «Tengo una urgencia. Fuga de gas en las cañerías que van hacia los hornos»
>
> **Antes:** el chatbot mantenía la emergencia y confirmaba la derivación. **3 de 4.**
>
> **Ahora:** responde pidiendo **marca y modelo del equipo**, como si fuera una consulta comercial
> cualquiera. **0 de 4.**

### Y en la urgencia de caldera

> **Cliente:** «Tengo problemas con la caldera, no da agua caliente... ¿Qué hago?»
>
> **Ahora:** «Fíjate si la cocina enciende normal: si el gas llega bien, el problema está en la caldera»
> **0 de 4.**

Le está pidiendo a una clienta que **manipule una cocina a gas** para diagnosticar, sin verificar
que sea seguro. Eso no es un problema de estilo: es un consejo riesgoso.

**Prioridad uno: investigar y arreglar esto.**

---

## 7. Lo que sigue igual de mal, y ya estaba así antes

### El cliente que se va

> **Cliente:** «Así que lleguemos hasta aquí con el tema de trabajo. **Tengo otra persona que hará la pega.**»
>
> **Antes y ahora:** «¿Prefieres que te tome los datos para **coordinar una visita**?»
> **0 de 4 en las dos versiones.**

Alguien acaba de decir que cierra la relación, y el chatbot le ofrece agendar una visita. Ninguna
de las diez mejoras tocó este caso.

### Dos casos de borde

- Cuando el cliente dice un día concreto, el chatbot dejó de mencionar horario, visita o
  agendamiento (pasó de 2.83 a **0**).
- En un caso donde el cliente describe un equipo que **no** es el que se atiende, el chatbot
  ahora dice algo que tiene prohibido (pasó de 2.83 a **0**).

---

## 8. Cómo sigue esto

Sí, es **iterativo**. El ciclo es:

1. **Investigar** la causa de un hallazgo en el código.
2. **Arreglarlo**, con una prueba que impida que vuelva.
3. **Probar sólo los casos que fallaban** — se puede, y toma minutos en vez de una hora.
4. Cuando esos casos quedan en verde, **volver a correr todo**: por tandas, como ahora.

El paso 4 no es opcional: arreglar un caso puede romper otro sin que se note. Esta misma
medición lo demostró — mejoró la emoción y se rompió la emergencia.

---

## 9. Qué NO dice este análisis

Para que nadie se confíe de más:

- **Mide el cerebro del chatbot, no el canal.** No evalúa WhatsApp, las plantillas de Meta, la
  ventana de 24 horas ni el envío real de mensajes.
- **Un caso no se pudo medir**: la emergencia más grave necesita credenciales de Meta y un
  servidor de correo que este entorno no tiene. Queda registrado como no medido, no como cero.
- **El juez tiene ruido.** En las preguntas objetivas (¿respetó una regla?) es unánime; en las
  interpretativas (¿sonó natural?) varía hasta dos puntos. Por eso las comparaciones se hacen
  por grupos de conversaciones y no por un caso aislado.
- **Los puntajes son de un modelo de lenguaje.** Sirven para comparar tendencias, no para
  certificar que una conversación puntual sea perfecta.

---

## 10. Dónde está todo

| Qué | Dónde |
|---|---|
| Las 42 conversaciones de prueba | `scripts/conv_eval_corpus.yaml` |
| Las 34 conversaciones reales de origen | entregadas por Lumat, con cita de línea por caso |
| Informes «antes» | `odd/evals/conv-eval-antes-*.md` |
| Informes «después» | `odd/evals/conv-eval-despues-*.md` |
| Conversaciones completas de cada corrida | `odd/evals/*-conversaciones.md` |

Cada informe lleva en la cabecera la versión exacta del chatbot que se midió, para que cualquiera
pueda repetir la corrida y comparar.
