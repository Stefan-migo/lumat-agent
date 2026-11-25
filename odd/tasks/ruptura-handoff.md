# ruptura-handoff — una ruptura de relación escala a una persona, con su propio texto

Pendiente 6 del handoff post-`v2026.11.19` (familia 4, `real-reclamo-real-si-deriva`). El bot
ofreció captura a un cliente que acababa de terminar la relación de trabajo. Decisión del owner:
vocabulario determinista **más** texto propio para la derivación.

## Specs

Aprobadas por el owner el 2026-11-25, verbatim:

- **S1** — «Una ruptura de relación explícita escala a una persona antes de cualquier respuesta del
  modelo.»
- **S2** — «Una ruptura es un mensaje en que el cliente declara que la relación de trabajo termina,
  no un mensaje enojado que pide algo.»
- **S3** — «La lista de disparadores es determinista, sin modelo, y se mide con dos instrumentos:
  frases reales que deben disparar y mensajes benignos que no.»
- **S4** — «La derivación por ruptura tiene texto propio, revisado por el dueño, y no reutiliza el
  genérico.»
- **S5** — «El texto reconoce el reclamo, no discute, no promete compensación y no ofrece servicios
  ni agenda.»
- **S6** — «Se edita desde el panel como las otras derivaciones.»

**Texto predeterminado enviado en el cambio (S4), pendiente de aprobación del owner:**

> «Lamento mucho cómo terminó esto. No voy a discutirlo contigo ni ofrecerte nada más: lo dejo en
> manos de una persona de Lumat, que va a revisar lo que pasó y te va a contactar.»

## Tasks

- T1 → S2, S3 · RED: recall sobre las frases medidas y precisión sobre el set benigno · `-`
- T2 → S1, S2 · GREEN: el disparador de ruptura en `handoff_gate` y su razón propia · `-`
- T3 → S4, S5, S6 · el texto propio: slot de `reply.texts`, derivación y superficie del panel · `-`
- T4 → S1-S6 · verificación (focused, quick, shape, gate del panel) y cierre · `-`

## Log

L1 — pedido del owner, verbatim:

> 6. Familia 4 (real-reclamo-real-si-deriva): pide decisión de producto, como la pidió el saludo. El bot
> tiene una sola herramienta (buscar datos) y una ruptura de relación no tiene dato que buscar.

> A+B · Vocabulario más texto propio

L2 — evidencia medida (24b, `odd/evals/conv-eval-rebaseline-2026-11-24b-conversaciones.md:535-550`):
el cliente dice «me dejaste la embarrada… el arrendatario contrató otro gasfiter y dice que te llamó
muchísimas veces y no contestas… lleguemos hasta aquí con el tema de trabajo» y «Muy irresponsable tu
forma de trabajar». El bot contesta con el saludo y con «¿Prefieres que te tome los datos para
coordinar una visita, o que te atienda una persona?». Estado final `bot`, juez 0.00, hard fail; los
gates declarados (G7, G8) están verdes: el rojo es del juez y nombra justo esas dos frases.

L3 — por qué no dispara hoy: `handoff_gate.evaluate_handoff` corre antes de `receive` (así el saludo
no precede a una derivación), pero la lista de reclamos no tiene «no contestas» (sí «nadie responde»),
ni «irresponsable», ni «me dejaste la embarrada», ni «lleguemos hasta aquí». El segundo turno cae en
`kb_miss_offer`, que es el texto que pide datos.

L4 — alcance: A+B, no C. Una instrucción de prompt no arregla la causa —23b muestra el turno 1 bien y
el turno 2 fallando igual— y `agent/prompts/*` es superficie de forma, así que costaría la suite
completa sin garantía.

L5 — verificación observada. Backend: `focused tests/integration/test_handoff.py` 81 tests en verde,
`quick` exit 0, `shape` exit 0 sin superficie de forma. Panel: `npm ci` exit 0 (con 15 avisos de
auditoría preexistentes), `npm run build` exit 0 con `tsc -b`, `npm test` exit 0 — 122 archivos, 1452
tests. RED real, no de proveedor: el worker confirmó que los dos tests fallaban por el disparador y el
texto ausentes, no por un error de autenticación, después de mockear el clasificador como el resto del
archivo.

L6 — corrección de calibración antes de commitear (2026-11-25): el primer disparador coincidía con las
dos frases del corpus como literales, que es enseñarle la prueba en vez de implementar S2. Se reemplazó
por una clase de frases —terminar la relación, reemplazar a Lumat, y las dos medidas— con una prueba
de recall de cinco redacciones plausibles que **no** son las del corpus y una de precisión con tres
mensajes enojados que piden algo. Una declaración de ruptura gana sobre una petición en el mismo
mensaje: es la decisión, y quedó comentada en el código.
