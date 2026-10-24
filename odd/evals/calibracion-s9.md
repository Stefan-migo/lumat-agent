# Calibración S9 — 3 conversaciones para puntuar a mano

Leé cada conversación y puntuá 0–4 cada dimensión **antes** de abrir el puntaje del juez
(está plegado al final de cada caso). Después comparamos: si el juez discrepa sistemáticamente,
se ajusta la rúbrica — el juez es apoyo, no veredicto (`odd/tasks/chatbot-conv-eval.md`, S9).

Escala: 0 no cumple · 1 apenas · 2 parcial · 3 bien · 4 impecable.

| Dimensión | Qué mide |
| --- | --- |
| grounding | lo que dice está respaldado por la KB o el tarifario, sin inventar |
| policy | reglas del negocio: cobertura, horarios, precios, no prometer de más |
| conversational | entiende el turno, no repite, no pierde el hilo ni el referente |
| escalation | escala cuando corresponde y no antes; ofrece una persona cuando el caso lo pide |
| tone | trato humano y chileno, sin sonar a formulario |
| closure | cierra con el siguiente paso concreto, o cierra bien cuando el cliente se despide |

## simple-precio-calefont [simple]

### Conversación

**cliente:** hola
> *bot:* Hola, soy el asistente virtual de Lumat. ¿Cómo estás? ¿En qué te puedo ayudar?

**cliente:** cuanto sale la mantencion de calefont?
> *bot:* La mantención de calefont cuesta $50.000 y dura entre 45 y 90 minutos. Incluye limpieza de componentes accesibles, revisión de quemadores, encendido, filtros, conexiones y evacuación de gases, más pruebas de funcionamiento. No incluye repuestos ni reparaciones. ¿Quieres que coordinemos una visita para tu equipo?

Estado final `bot` · eventos: `classified` (intent:valores), `kb_retrieved` (chunks:5)

### Tu puntaje

| Dimensión | 0–4 | Por qué |
| --- | --- | --- |
| grounding | | |
| policy | | |
| conversational | | |
| escalation | | |
| tone | | |
| closure | | |

### Puntaje del juez (abrir después de puntuar)

<details><summary>ver</summary>

promedio **4.0** · hard fail: **False**

- **grounding 4.0**
- **policy 4.0**
- **conversational 4.0**
- **escalation 4.0**
- **tone 4.0**
- **closure 4.0**

</details>

## complejo-agendar-calefont [complejo]

### Conversación

**cliente:** hola, necesito mantener mi calefont, vivo en ñuñoa
> *bot:* Hola, soy el asistente virtual de Lumat. ¿Cómo estás? Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**cliente:** me llamo carolina, atiendan cuando puedan
> *bot:* Gracias, Carolina. La mantención de calefont tiene un valor de $50.000 e incluye limpieza, revisión de quemadores, encendido, filtros y evacuación de gases; dura entre 45 y 90 minutos. ¿Qué día y horario te acomoda para coordinar la visita en Ñuñoa?
> *bot:* Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?

**cliente:** el calefont es junkers, tiro natural
> *bot:* ¿Qué días y horarios te acomodan para la visita?

**cliente:** si, me sirve cualquier dia en la mañana
> *bot:* ¿Cuál es tu correo electrónico?

**cliente:** carolina.p@gmail.com
> *bot:* ¿Cuál es tu dirección? ¿Tienes algo más para pasarle al técnico? (una foto, un audio…)

**cliente:** av grecia 1234, depto 52. tercer piso, hay timbre
> *bot:* ¿Autorizas que guardemos tus datos para gestionar tu solicitud? Responde sí o no.

Estado final `bot` · eventos: `classified` (intent:solicitar_visita), `classified` (intent:consulta), `kb_retrieved` (chunks:5), `classified` (intent:solicitar_visita), `classified` (intent:solicitar_visita), `classified` (intent:solicitar_visita), `classified` (intent:solicitar_visita)

### Tu puntaje

| Dimensión | 0–4 | Por qué |
| --- | --- | --- |
| grounding | | |
| policy | | |
| conversational | | |
| escalation | | |
| tone | | |
| closure | | |

### Puntaje del juez (abrir después de puntuar)

<details><summary>ver</summary>

promedio **2.5** · hard fail: **False**

- **grounding 4.0**
- **policy 4.0**
- **conversational 1.0**
- **escalation 2.0**
- **tone 3.0**
- **closure 1.0**

</details>

## super-enojo-reclamo [supercomplejo]

### Conversación

**cliente:** ES UNA VERGUENZA PAGUE LA MANTENCION Y EL CALEFONT SIGUE FALLANDO
> *bot:* Hola, soy el asistente virtual de Lumat. ¿Cómo estás? Entiendo su molestia, y lamento que después de la mantención el calefont siga fallando. Para orientarlo: ¿qué está haciendo el equipo ahora, no enciende, se apaga solo o el agua no calienta? Con ese dato puedo coordinar una revisión con un técnico y que un asesor revise su caso.

**cliente:** vino un tecnico la semana pasada y quedo igual, perdi la plata
> *bot:* Entiendo, y es frustrante pagar por una mantención y que el problema siga igual. Para que un asesor revise su caso, ¿me confirma qué está pasando ahora con el calefont: no enciende, se apaga solo o el agua no calienta? Con ese dato y la fecha de la visita de la semana pasada dejamos el antecedente listo para la revisión.

**cliente:** quiero hablar con una persona ahora
> *bot:* Un asesor revisará tu caso y te contactará a la brevedad.

**cliente:** NO QUIERO QUE ME CONTACTEN DESPUES, QUIERO HABLAR CON ALGUIEN AHORA MISMO. SI NO ME PASAN CON UNA PERSONA VOY A DEJAR LA RESEÑA Y DENUNCIO EN EL SERNAC
> *bot:* Un asesor revisará tu caso y te contactará a la brevedad.

Estado final `human` · eventos: `classified` (intent:postventa), `kb_retrieved` (chunks:5), `classified` (intent:postventa), `kb_retrieved` (chunks:5), `state_change` (bot->human: handoff:persona), `escalation` (handoff:persona), `escalation` (handoff:persona)

### Tu puntaje

| Dimensión | 0–4 | Por qué |
| --- | --- | --- |
| grounding | | |
| policy | | |
| conversational | | |
| escalation | | |
| tone | | |
| closure | | |

### Puntaje del juez (abrir después de puntuar)

<details><summary>ver</summary>

promedio **1.667** · hard fail: **False**

- **grounding 3.0**
- **policy 4.0**
- **conversational 0.0**
- **escalation 0.0**
- **tone 2.0**
- **closure 1.0**

</details>

