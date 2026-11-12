# corpus-real-bugs — dos defectos medidos contra conversaciones reales

Worktree: `/home/stefan/repos/lumat-agent-odd-corpus-real-bugs` · Rama: `odd/corpus-real-bugs` · Base: `4ae76ca1`.

Origen: 34 conversaciones reales del número oficial de Lumat (4.600 mensajes, nov-2025 a nov-2026). El análisis completo vive en `odd/analysis/lumatdata/` del worktree principal.

## Specs

**S1 — La cortesía chilena no es un reclamo.**
Hoy `_COMPLAINT_WORDS` incluye `molesto` y `molesta` como palabra suelta (`app/chat/nodes/handoff_gate.py`), y un match deriva la conversación a un humano **sin LLM**. En el corpus, las 3 coincidencias sobre 2.049 mensajes de cliente son cortesía, no reclamo:

- «Maxi como estas?, **te molesto** con la última pls?, el agua de duchas está impecable» (Javier Gálvez)
- «pero **te molesto** el fin de seman un minuto cuando puedas» (Mónica Dawabe)
- «**Te molesto** con una pregunta, la casa no logra calentarse a 22 grados» (Pabla Leiva)

La señal real debe conservarse: «estoy **molesto** con el servicio» tiene que seguir derivando, y ya está pinneado en `tests/integration/test_handoff.py:204`.

**S2 — Una pregunta de precio u hora, enviada junto con un dato, se contesta.**
`orchestrate._is_question` exige `"?" in text and not state.extracted`, o un término de horario/cobertura. Si el mismo mensaje trae un dato, la pregunta desaparece y el dato se guarda. En el corpus, **303 de 2.157** mensajes de cliente (14%) son «dato + pregunta».

Alcance de este unit (deliberadamente estrecho):

- **precio**: `cuanto` / `cuanta` — «Gracias Max! **Cuánto** les debo?»
- **hora**: agregar `hora` a la familia de términos de horario (el token `horas` no matchea, así que «a qué **hora** vienes» pregunta y «a las 14 **horas**» sigue siendo respuesta).

Fuera de alcance, registrado como seguimiento: preguntas de capacidad («ustedes **tienen** el personal para terminar la conversión?») y de ciclo («¿**corresponde** hacerla?»). Se resuelven después con el corpus de evaluación, no acá.

Lo que **no** puede cambiar: una respuesta de disponibilidad dicha como pregunta sigue siendo respuesta al campo — «¿puede ser el sábado?», «a las 14 puede ser», «no era calefont, es una caldera, y estoy en providencia» (`tests/unit/test_routing_table.py:268`).

## Tasks

| ID | Spec | Ruta | Commit |
|---|---|---|---|
| T1 | S1 | `handoff_gate.py` + test de reclamo | 1 |
| T2 | S2 | `orchestrate.py` + tests de ruteo | 2 |

## Log

### L1 — pedido del owner, verbatim

```text
entonces primero que todo necesito que analices los analisis que hizo el due;o de lumat con su ia.
luego necesito que hagamos nuestro propio analisis. de las conversaciones raw que tenemos.
finalmente quiero que logremos encontrar bugs, o posibles mejoras al chatbot de lumat.
y finalmente la idea es crear a partir de casos reales, el bot que va a testear al chatbot
a traves del harness localmente.
```

### L2 — decisión de alcance

Presentadas cuatro rutas, el owner eligió: **«Solo D3 y D2, sin corpus todavía»** — worktree, rama y dos arreglos chicos con sus tests; los 15 escenarios reales quedan para una segunda pasada. Eso convierte a S1 y S2 en el alcance de esta feature y difiere el corpus.

### L3 — riesgo declarado

Ambos cambios viven en nodos compartidos que corren en **cada** mensaje de **cada** conversación. Una regresión no se ve en el test nuevo: se ve en que una respuesta de disponibilidad deja de llenar el campo o una queja real deja de derivar. Por eso: diferencial de conducta contra la base además de los tests, y verificación independiente (Risk: item 3).

### L4 — S2 (D2) se cae por medición, antes de tocar código

Antes de implementar se midió el corpus real. Resultado:

- Mensajes de cliente con `cuanto`/`cuanta`: **27**. De ellos, **17 ya traen `?`** y por lo tanto ya se enrutan como pregunta. **Ninguno** combina la pregunta de precio con un dato en el mismo mensaje.
- La extensión natural de la familia de horarios (`agregar "hora" a _SCHEDULE_TERMS`) es un **retroceso medido**: de 12 mensajes reales que contienen «hora», la gran mayoría son *respuestas de disponibilidad* («se puede después de las 19 horas?», «18 horas», «15 horas esta bien», «12 - 13 hrs perfecto llega mi marido»). Enrutarlas como pregunta rompería el agente que llena el campo de disponibilidad.

Conclusión: S2 no tiene demanda medida y su forma obvia colisiona con el flujo de agenda. **No se implementa un cambio de código sin volumen que lo respalde.** El instrumento correcto es el corpus de evaluación (diferido por decisión del owner en L2): un escenario «dato + pregunta» mediría si alguna vez importa, y sólo entonces corresponde una señal en el clasificador. Se revierte S2 a seguimiento y queda registrado en `03-defectos-y-mejoras.md` (D2).

### L5 — S1 RED observado

Se agregaron los tres mensajes reales de cortesía a `_BENIGN_MESSAGES_THAT_MUST_NOT_TRIGGER` (`tests/integration/test_handoff.py`), con la conversación de origen anotada.

`bash scripts/test.sh db tests/integration/test_handoff.py -k benign` → **3 failed**. Fallan exactamente los tres casos nuevos; los seis benignos preexistentes siguen pasando. El fallo es el esperado: `{'handoff_reason': 'complaint'} != {'handoff_reason': None}`.

### L6 — S1 GREEN y diferencial de conducta compartida

Implementación (`app/chat/nodes/handoff_gate.py`): `molesto`/`molesta` salen de `_COMPLAINT_WORDS` y vuelven como patrón anclado — `\b(?:estoy|estaba|estuve|qued[eé])\s+(?:muy\s+|s[uú]per\s+)?molest[oa]\b` o `\bme\s+molest[ao]\b` — evaluado en `evaluate_handoff`. El adjetivo con su sujeto sigue derivando; el verbo con que un cliente educado abre una pregunta, no.

Verificación observada:

- `bash scripts/test.sh db tests/integration/test_handoff.py`: **49 passed**, 100%. Incluye el recall pinneado «estoy molesto con el servicio» (`:204`), «estoy muy molesto con el servicio» y «estoy molesto, quiero reclamar» (`:487`).
- **Diferencial** contra `4ae76ca1` (árbol base extraído con `git archive`, patrón usado en la sesión previa): mismo probe `evaluate_handoff` sobre 32 mensajes (los 6 benignos, los 12 de recall, el trigger `persona`, tráfico neutro y las formas nuevas), corrido en dos procesos con `PYTHONPATH` distinto. Baseline exit 0, candidato exit 0, stderr vacío en ambos.
- `diff` de las dos salidas: **sólo 3 líneas**, exactamente las tres de cortesía (`complaint` → `null`). Ningún verdadero positivo perdido, ningún neutro alterado. Las formas «me molesta que…», «quedé molesto», «estaba molesta» dan `complaint` en ambos lados, porque la base ya las atrapaba por la palabra suelta.
- `bash scripts/test.sh quick`: exit 0, 100%.
- `bash scripts/test.sh shape 4ae76ca1`: exit 0, «no shape surface touched».
- `git diff --check`: exit 0.

### L7 — auditoría del propio patrón: dos falsos negativos, corregidos antes de cerrar

Antes de aceptar el patrón se comparó, sobre una batería de formas reales, la semántica vieja (palabra suelta), la implementada y una variante endurecida. Resultado:

| forma | palabra suelta (base) | implementada (L6) | endurecida |
|---|---|---|---|
| «estoy/estaba/estuve/quedé molesto» | sí | sí | sí |
| «**quedo** molesto con el trabajo» (sin tilde) | **sí** | **no** | sí |
| «**ando** molesto con el servicio» | **sí** | **no** | sí |
| «**estamos** molestos con el trabajo» | no | no | sí |
| «**me molestan** los cobros» | no | no | sí |
| «te molesto con una pregunta» / «te molesto con el cuento» | sí (falso positivo) | no | no |

O sea: la implementación de L6 **introducía dos falsos negativos** frente a la base — una queja real escrita sin tilde o con «ando» dejaba de llegar a un humano. Eso es peor que el bug original, porque el cliente enojado es el que no puede esperar. La variante endurecida agrega plurales (`estamos/están/quedamos` + `molestos/molestas`) y `me molestan`, y cubre las dos formas perdidas, sin reabrir el falso positivo (`molesto con el…` sin sujeto NO se acepta, precisamente porque «te molesto con el tema» es cortesía).

Se aplica la variante endurecida con sus casos en el set de recall y el caso trampa en el de precisión.

### L8 — verificación independiente: bloqueante encontrado, y el arreglo correcto era otro

Resultado del verificador: **VERDICT: FINDINGS**. El hallazgo es correcto y grave. El patrón anclado del L6 blanqueaba la forma del enojo (verbo + lista de adverbios) y por eso **perdía 19 formas de queja real que la base sí atrapaba**:

```
estoy bastante / algo / sumamente / realmente / re / medio molesto con el servicio
estoy muy pero muy molesto · muy molesto con el servicio · bastante molesta con la atencion
me siento molesto · me tiene molesto · me dejo molesto · sigo molesto · ando molesto
molesto con el servicio, todavia no vienen
```

Y el diagnóstico del verificador sobre por qué los tests no lo vieron también es correcto: **el instrumento era de un solo lado** donde este cambio actúa. El set de precisión cubría la cortesía y el de recall sólo pinneaba las formas que la lista blanca ya contemplaba, así que 49 tests en verde convivieron con 15 falsos negativos.

Corrección aplicada (propuesta por el verificador y medida antes de aceptarla): en vez de enumerar la forma del enojo, **se conserva la palabra y se excluye el clítico de cortesía**:

```python
re.compile(r"\b(?<!\bte )(?<!\ble )(?<!\bles )molest[oa]s?n?\b", re.IGNORECASE)
```

El `\b` dentro de cada lookbehind es funcional, no decorativo: un `(?<!te )` plano también bloquearía «bastante molesto», que termina en «te ». El `n?` agregado reacha el plural «me molestan», que ninguna versión anterior alcanzaba.

Medición previa a aceptar (46 casos):

| patrón | recall fallado | precisión fallada |
|---|---|---|
| base (palabra suelta) | 3 | 9 |
| L6 (anclado) | **15** | 0 |
| final (clítico excluido) | **0** | **0** |

Diferencial final contra `4ae76ca1` sobre **60 mensajes**: sólo 12 líneas cambian — 9 de cortesía (`complaint` → `null`) y 3 de queja plural (`null` → `complaint`). **Ninguna línea de recall cambia**: toda forma de enojo que la base derivaba, sigue derivándola.

Instrumento completado en ambas mitades: 13 casos de recall y 9 de cortesía agregados a `tests/integration/test_handoff.py`; `bash scripts/test.sh db tests/integration/test_handoff.py` → **74 passed**. Nits del verificador corregidos: las tres líneas del corpus se citan con sus erratas reales (`fin de seman`, sin truncar) y se eliminó el scratch que el verificador dejó en `/tmp`.

### L9 — correcciones de honestidad sobre el proceso

- La suite completa del L6 dio verde (exit 0, 100%, sólo las dos advertencias preexistentes), pero quedó **invalidada** por la corrección del L8: el verde que cuenta es el del código final.
- El stall del primer intento (`tests/functional/test_seed_dev.py:42`, timeout de 120 s en el subproceso `seed_dev`) es la familia preexistente documentada en `odd/tasks/suite-truncate-stall.md`; el test pasa aislado y no toca el detector modificado. Se reporta como fallo y no como verde, y el segundo intento se corrió de forma deliberada y registrada, no automática.
- D2 quedó fuera por medición (L4), no por falta de tiempo: su forma obvia habría roto el flujo de disponibilidad.

### L10 — segunda verificación independiente: APPROVE, con una concesión documentada

`VERDICT: APPROVE`, must-fix: ninguno. Evidencia de la ronda: barrido de 266 casos (38 prefijos × 7 formas) sin una sola pérdida de recall y 114 ganadas (los plurales); 28 formas de enojo todas escalando; familia de cortesía completa fuera, incluida con mayúscula y con «Hola, te molesto un segundo»; `gate` 0, `shape` 0, `diff --check` 0; árbol sin mutar. Confirmó por sonda directa la afirmación del `\b` dentro del lookbehind: «bastante/sumamente/realmente molesto», «deporte/soporte molesto», «quite/garantice molesto» escalan; «te/le/les molesto» no.

También verificó por simulación del assert que el instrumento es ahora de dos lados: 10 casos benignos y 2 de recall fallan en `4ae76ca1`; y que **16 de los casos de recall habrían fallado con el patrón rechazado del L6** — el instrumento ya detecta el bloqueante que la ronda anterior no vio.

**A1 — concesión aceptada y documentada.** La exclusión del clítico alcanza también al `le`/`les` de tercera persona, así que estas quejas reales dejan de derivar de forma determinista:

```
a mi señora le molesta que no avisen
lo que mas le molesta a mi señora es que no avisaron
a los vecinos les molesta el ruido del equipo
```

La base las derivaba. **El corpus tiene cero ocurrencias de `le`/`les`**, en ningún sentido: no hay evidencia medida ni a favor ni en contra. Se acepta como concesión explícita por una razón concreta: el candidato está aprobado, el verde de la suite completa corresponde a este código, y reabrir el patrón por un caso sin evidencia invalida esa corrida y exige otra ronda de verificación. La corrección está identificada y es barata — distinguir persona en vez de enumerar adverbios:

```python
# en vez de excluir (te|le|les) por igual:
_COURTESY_CLITIC = re.compile(
    r"\b(?:te|le|les)\s+molesto\b"                      # 1.ª persona: cortesía
    r"|\b(?:te|le|les)\s+molesta(?=\s+(?:si|cuando)\b)", # «¿te molesta si…?»
    re.IGNORECASE,
)
# y el patrón de queja vuelve a la palabra suelta: r"\bmolest[oa]s?n?\b"
```

Con esa forma «le molesta que no avisen» vuelve a derivar y «te molesto con una pregunta» sigue fuera. Queda como seguimiento con evidencia pendiente, no como deuda invisible.

**A2 y A3 — preexistentes, no causadas por este cambio.** A2: la prueba del clítico es un espacio literal, así que la cortesía partida por salto de línea o tabulador sigue dando falso positivo (`te\nmolesto`), igual que en la base. A3: ceguera a la negación («no me molesta, pero el equipo no funciona» deriva), igual que en la base. Ambas quedan registradas.

**A4 — el instrumento sigue siendo de integración.** El verificador propone un `tests/unit/test_handoff_upset_pattern.py` sin base de datos para que las dos mitades corran en T1. No se agrega en esta unidad a propósito: la suite completa que da el verde corresponde al árbol actual, y sumar un archivo nuevo después de lanzarla dejaría el verde sin cubrirlo. Se registra como seguimiento inmediato de bajo costo.

