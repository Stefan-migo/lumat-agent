# Multi-tema — D9

Defecto D9 de `odd/analysis/lumatdata/03-defectos-y-mejoras.md`. Toca el contrato del clasificador,
que es una superficie compartida: por eso va en su propio corte y con verificación independiente.

## Specs

**S1 · D9 — un turno con dos o tres temas no se lee como incomprensión.**
«Causa: el clasificador debe elegir **1 de 14** intenciones (`agent/personas/classify.md`); a los 3
`unknown` seguidos la conversación pasa a humano». «Evidencia: los turnos reales traen 2-3 temas con su
lectura técnica: «No calienta la casa, los radiadores están "calientes" pero el termostato llega a 14
con la calefacción prendida» (Paulina). Sol acumula 150 mensajes con signo de pregunta y 91 con
dinero: el multi-tema es la norma, no la excepción». «Riesgo: derivar por incomprensión a un cliente
que sí se explicó».

**S2 · Lo que sigue igual.**
`unknown` sigue existiendo para la incomprensión real, y los tres `unknown` seguidos siguen derivando
a una persona: lo que cambia es que un turno que sí se explicó no cuenta como incomprensión. El orden
de las puertas no cambia. La detección de inyección no cambia.

## Decisiones de diseño

- **D1 · El contrato crece, no rompe.** El clasificador devuelve además `intents`, lista ordenada de
  los temas del turno; `intent` sigue siendo el primero y nadie que hoy lea `intent` se rompe. Un
  consumidor nuevo puede leer los temas secundarios sin que el formato viejo desaparezca.
- **D2 · La incomprensión se comprueba, no se cree.** Si el clasificador devuelve `unknown` pero el
  turno nombra vocabulario técnico o de servicio del negocio (caldera, calefont, calefacción,
  radiador, termostato, visita, instalación, mantención, filtración, …), el turno **no** es
  incomprensión: se rescata la intención con una tabla determinista. Sin modelo, sin segunda llamada.
- **D3 · El rescate no inventa intención.** Sólo mapea a las intenciones que ya existen; si el término
  no está en la tabla, `unknown` se respeta y la conversación puede derivar como hoy.

## Tasks

| ID | Specs | Route | Commit |
|---|---|---|---|
| T1 | S1, S2 | Contrato aditivo `intents` en la persona, el prompt y el parser | `feat(classify):` |
| T2 | S1, S2 | Rescate determinista de `unknown` por vocabulario, sin contar racha | `feat(classify):` |

## Log

**L1 — pedido del owner (verbatim).**

```
- ok d 9 tambien arrancarlo.
```

**L2 — D9 cerrado con dos decisiones de la implementación.** El rescate se evaluó después de la
inyección y antes de escribir el evento `classified`, así que el `cause` que lee `unknown_streak` ya
lleva la intención rescatada y el turno no cuenta como incomprensión. El vocabulario quedó acotado a lo
que tiene destino claro: «instalación», «mantención» y «filtración» se dejaron fuera porque D2 no fija a
qué intención corresponden, y mapearlos habría sido inventar una regla. `intents` vive ahora en
`ConversationState`, no sólo en el dict del nodo, así que el estado lo conserva durante el turno.
