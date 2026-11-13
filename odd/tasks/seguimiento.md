# Seguimiento — D10

Defecto D10 de `odd/analysis/lumatdata/03-defectos-y-mejoras.md`. Va después de D6 (#809) porque
`Commitment` es una de sus dos entradas.

## Specs

**S1 · D10 — nadie persigue un hilo muerto.**
«Evidencia: **22 de 34** conversaciones terminan con un mensaje del cliente. Sol: 8 meses, cierra con
un saludo sin respuesta. María Jesús Ríos: 68 días esperando repuestos, con la calefacción apagada.
Hugo Ochoa: pregunta «Quería saber que pasó con el calefon» tras 14 días de silencio». «`closure_gate`
cierra por despedida del cliente; no hay nada que detecte un hilo que se apaga. Es el mismo problema
que D6 (compromiso sin dueño) visto desde el otro lado».

**S2 · El detector siempre, el envío detrás de una bandera.** Decisión del owner: el detector corre y
registra, y el mensaje saliente queda detrás de una bandera apagada por defecto, porque escribirle
primero a un cliente fuera de la ventana de 24 h exige plantilla aprobada por Meta y se cobra por
mensaje. Ese es un costo y una política que decide el owner, no el código.

**S3 · Detectar no puede molestar.** Con la bandera apagada, este corte no le escribe a nadie: sólo
registra. Nada del camino existente cambia de comportamiento.

## Decisiones de diseño

- **D1 · Dos entradas, un mismo barrido.** Un hilo está pendiente cuando pasaron más de
  `followup.idle_hours` sin respuesta nuestra, o cuando un `Commitment` sigue `pendiente` con su
  `due_at` vencido. Es la misma pregunta desde dos fechas, como dice el análisis.
- **D2 · El registro vive en `conversation_events`, no en una tabla nueva.** Un evento
  `idle_thread` / `commitment_overdue` es el hecho, y su existencia es la deduplicación: el barrido no
  vuelve a registrar lo mismo para la misma conversación. Sin migración.
- **D3 · La reutilización antes de la copia.** `app/services/tukulpan.py` ya tiene el predicado de
  «último mensaje entrante y ningún saliente después, 24 h» para la observación `sin_respuesta`, pero
  sólo corre al cerrar. Si es una función limpia, se reutiliza en vez de escribir el mismo predicado
  dos veces; si no lo es, se documenta por qué se escribe aparte.
- **D4 · Un solo mensaje, nunca dos.** Si el envío está habilitado, se registra el evento que lo marca
  y un hilo seguido no se vuelve a seguir.
- **D5 · La plantilla es del owner.** El nombre de la plantilla es un ajuste, vacío por defecto: sin
  plantilla configurada no se envía aunque la bandera esté encendida. El envío usa el mecanismo que ya
  existe (`notify.send_template` con su validación de `approved`), no uno nuevo.

## Tasks

| ID | Specs | Route | Commit |
|---|---|---|---|
| T1 | S1, S2, D1, D2 | `app/services/followup.py`: detector de hilo apagado y de compromiso vencido, con deduplicación por evento | `feat(followup):` |
| T2 | S2, S3, D4, D5 | Barrido `app/ops/followup.py`, ajustes (`followup.idle_enabled` false, `followup.idle_hours` 24, `followup.idle_template_name` vacío) y envío detrás de bandera | `feat(followup):` |
| T3 | S3 | Línea de cron en `docs/ops.md`, en la misma sección y estilo que `sweep` y `worker` | `docs(ops):` |

## Log

**L1 — pedido del owner (verbatim).**

```
2. d10. no entiuendo de que hablas
```
y, tras la explicación:

```
ok estoy de acuerdo con todo.
```
