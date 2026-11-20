# captura-pregunta

The bot spends a turn on its own ritual (presentation, canned closure, a capture question that was
already asked) instead of reading what the customer just wrote. Measured on `main` @ `3993e4abf` by
the full-corpus re-baseline (`odd/evals/conv-eval-rebaseline-2026-11-20.md`): 36/42, zero gate
failures, and four of the six judge hard fails share this shape.

Branch `odd/captura-pregunta`. Corpus `8adb94421f45`, KB `34670f5b3d75`, judge `deepseek-v4.1-flash`
×3. Transcript transcript of record: `odd/evals/conv-eval-rebaseline-2026-11-20-conversaciones.md`.

## Specs

### S1 — A greeting turn must not replace a pending capture

When the inbound text is greeting-only and a capture batch is already pending, the turn continues the
capture (re-asks the pending batch). It must not answer with the full presentation and end there.

Measured, `real-solo-sabados` turn 1 asks for the comuna, and turn 2 answers:

> cliente: `Buen dia`
> bot: `Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar.`

Scenario expectations, verbatim from `scripts/conv_eval_corpus.yaml` (`real-solo-sabados`):

```yaml
    expect:
      state_any: [bot, human]
      events_forbidden: [escalation]
      kb_answered: true
    hard_fails:
      - "Prometer una visita sin consultar disponibilidad"
```

### S2 — An explicit change request leaves capture even when it names another noun

A turn that carries an explicit change verb about the visit's date/duration
(`cambiar la fecha`, `cambiar el día`, `cambiar la mantención`) is a change request, not a field
answer, even when a capture batch is pending and even when the same message also carries a question.
`visita|hora|dia` alone is not enough.

Measured, `real-reagenda-mantencion` turn 5, after four turns of the same diagnostic question:

> cliente: `Hola buenos dias, Favor cambiar la fecha de la manutención para el próximo martes por favor, Por temas laborales no estaré en casa hoy pm`
> bot: `Veo que esa pregunta no te acomoda. Un asesor de Lumat te contacta para terminar de coordinar los datos.`

Scenario expectations and hard fails, verbatim (`real-reagenda-mantencion`):

```yaml
    expect:
      state_any: [bot, human]
    hard_fails:
      - "Confirmar el cambio de fecha sin verificar la disponibilidad"
      - "Ignorar el motivo laboral que la clienta dio para cambiar la visita"
```

### S3 — The exhausted-field derivation never fires on a change request

`capture._reask_pending` derives `campo_sin_respuesta` only when the turn is not a change request.
The measured case: `_asked["failure"]` reached `MAX_ASKS_PER_FIELD` and the customer's reschedule was
read as a refusal to answer, ending in `handoff_campo_sin_respuesta`
(`app/services/settings.py:184`) and state `human`.

### S4 — A question about availability is not a declared availability

When the inbound text asks about availability (`_looks_like_question`), the extractor's
`availability` is not merged and the turn does not answer with `capture_availability_ack`. The
question is answered; the pending capture continues.

Measured, `real-solo-sabados` turn 3:

> cliente: `Este sábado 27 ud tiene disponibilidad?`
> bot: `Anoté que sábado 27; lo tengo en cuenta para la visita. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?`

Same shape in `real-repuesto-agotado` turn 2 and `real-reagenda-mantencion` turns 2-3. Verbatim
expectations and hard fails:

```yaml
# real-repuesto-agotado
    expect:
      state_any: [bot, human]
    hard_fails:
      - "Prometer disponibilidad o una fecha sin confirmación"
# real-reagenda-mantencion
    expect:
      state_any: [bot, human]
    hard_fails:
      - "Confirmar el cambio de fecha sin verificar la disponibilidad"
```

### S5 — `smalltalk` mid-capture does not close the conversation

With a capture batch pending, a smalltalk intent answers the social part and re-asks the pending
batch. It must not reply with `messages.smalltalk` (`Con gusto. ¿En qué más te puedo ayudar?`) and
leave the capture behind.

Measured, `real-varias-reparaciones`: the customer names two repairs, the bot asks the comuna, and

> cliente: `Eso!`
> bot: `Con gusto. ¿En qué más te puedo ayudar?`

Verbatim expectations and hard fails (`real-varias-reparaciones`):

```yaml
    expect:
      state_any: [bot, human]
      events_forbidden: [unknown_intent]
    hard_fails:
      - "Omitir una de las dos reparaciones solicitadas"
      - "Prometer un alcance o precio sin revisar los trabajos"
```

Contract note: `tests/integration/test_smalltalk.py:222` pins today's routing
(`_dispatch("smalltalk", mid_capture=True)["next_step"] == "respond"`). That assertion pins the
defect and changes with S5; the social-only path (no capture pending) keeps replying `smalltalk`.

### S7 (from L5) — The canned social line is not a reply to a non-courtesy label

When the capture re-ask happens because the classifier labelled the turn `smalltalk`, the canned
`messages.smalltalk` text («Con gusto. ¿En qué más te puedo ayudar?») is emitted only when the inbound
text is courtesy-like. «Eso!» is not; it gets the re-ask alone. Measured in `real-varias-reparaciones`
after Slice A: `Con gusto. ¿En qué más te puedo ayudar?` followed by `¿En qué comuna te encuentras?`.

### S8 (from L5) — A capture field is not exhausted by a turn that captured something

`_asked[field]` advances only when the turn produced no captured data. A customer answering the
schedule thread («Martes pm», «Entre las 14:30 y 17:30») is not refusing to answer; charging those
turns brought `_asked["failure"]` to `MAX_ASKS_PER_FIELD` and ended `real-reagenda-mantencion` in
`handoff_campo_sin_respuesta` with state `human`.

### S6 — A bare franja is a franja, not only a day

`viernes tarde`, `sábado en la mañana`, `lunes de madrugada` resolve to day + franja. Measured,
`real-solo-sabados` turn 4:

> cliente: `No me encuentro en stgo llegamos viernes tarde al dpto`
> bot: `Sobre tu horario: el viernes 20/11. Queda anotada y la confirmamos al coordinar la visita.`

Negation semantics are **out of scope**: `resolve_window` detects mentions, not preferences, and the
exclusion vocabulary lives in `capture._excludes_the_window`. S6 only stops dropping the franja.

## Tasks

| ID | Spec | Route | Commit |
| --- | --- | --- | --- |
| T1 | S1 | inline | RED+GREEN greeting guard in `receive`/`graph` |
| T2 | S2, S3 | inline | change-request vocabulary + `_reask_pending` guard |
| T3 | S5 | inline | smalltalk mid-capture continues the capture; pin updated |
| T4 | — | inline | measure the 4 scenarios (`--only`, 3 reps) — **1/4**: see L5 |
| T5 | S4 | inline | question-gated availability merge + ack |
| T6 | S6 | inline | bare franja in `resolve_window` |
| T7 | S1-S6 | inline | differential check + `test.sh full` + full-corpus measure |
| T8 | — | inline | CHANGELOG, doc verdicts, PR |

## Log

**L1 (owner, verbatim)** — `hey chat cotninuamos desde aca: Handoff guardado en Engram como 7210 (handoff/chatbot-programa-pendientes).. Dame un overview antes de continuar`

**L2 (owner decision)** — Re-baseline first: `Re-baseline del corpus completo` (option
`rebaseline`). Result: 36/42, zero gate failures, judge hard fails on 6 scenarios.

**L3 (owner decision)** — Next cut: `Captura que ignora la pregunta + reinicio de saludo` (option
`captura-pregunta`): attack the cross-cutting pattern behind `real-solo-sabados`,
`real-reagenda-mantencion`, `real-repuesto-agotado` and `real-varias-reparaciones`.

**L4 (owner decision)** — `Worktree nuevo, las dos slices` (option `worktree-ab`): work in
`../lumat-agent-odd-captura-pregunta` on `odd/captura-pregunta`, Slice A first (routing), then Slice B
(parsers), measuring between them.

**L5 (measurement, Slice A)** — `conv_eval --run-tag captura-sliceA --judge-repetitions 3 --only` the
four scenarios: **1/4 pass, zero gate failures**, and that one pass is a judge timeout, not a verdict.
Transcripts (`odd/evals/conv-eval-captura-sliceA-conversaciones.md`), read turn by turn:

- `real-varias-reparaciones` — **S5 works**: the turn now replies and re-asks instead of closing. But it
  still leads with the `messages.smalltalk` line («Con gusto. ¿En qué más te puedo ayudar?»), which is
  nonsense for «Eso!», and the two repairs are never restated.
- `real-reagenda-mantencion` — S3's guard did not fire: turn 3 («Entre las 14:30 y 17:30 por favor») is
  not a change request, so `_asked["failure"]` reached the cap and the turn still answered
  `handoff_campo_sin_respuesta`. State ended `human`. **Not fixed.**
- `real-solo-sabados` / `real-repuesto-agotado` — both hard fails are now exactly S4 and S6: the bot
  still acknowledges a mentioned date as if it were a declared availability («Anoté que sábado 27»,
  «Anoté que lunes») and still renders a mentioned day as a promise.

Conclusion: Slice A changed the failure mode (no canned closure, no dead end at the first change
request) but closed none of the four scenarios. The remaining gap is the one Slice B was written for,
plus two specs the measurement added (S7, S8, sketched above).
