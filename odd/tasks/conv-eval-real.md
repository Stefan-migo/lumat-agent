# conv-eval-real — quince escenarios de evaluación derivados del corpus real

Worktree: `/home/stefan/repos/lumat-agent-odd-conv-eval-real` · Rama: `odd/conv-eval-real` · Base: `origin/main` = `26f49047`.

Origen: las 34 conversaciones reales del número oficial de Lumat (4.600 mensajes, nov-2025 a nov-2026) y el diseño de `odd/analysis/lumatdata/04-corpus-desde-casos-reales.md`. Ese documento es la especificación funcional; este es el contrato de implementación.

## Specs

**S1 — El corpus es aditivo.** Los 15 escenarios existentes de `scripts/conv_eval_corpus.yaml` se conservan sin editar sus expectativas: varios pinnean rojos históricos (saludo, inyección, emergencia, ráfaga). Después de esta unidad el archivo declara **30** escenarios.

**S2 — Los turnos del cliente son verbatim.** Sin corregir ortografía, sin arreglar tildes, sin unir mensajes partidos, sin completar abreviaturas. Regla del doc 04 §3.2, textual: *«Turnos del cliente: verbatim. Sin corregir ortografía, sin arreglar tildes, sin unir mensajes.»* Un audio o video se convierte en su texto declarado con un comentario, o se omite.

**S3 — Cada escenario cita su origen.** El campo `notes` nombra la conversación de origen y el número de línea del tramo. Sin eso nadie puede auditar el escenario después, y es la diferencia entre medir el bot y medir la imaginación de quien escribe.

**S4 — Un escenario sólo exige lo que el bot puede hacer hoy.** Regla del doc 04 §2, textual: *«Un escenario sólo puede exigir lo que el bot puede hacer hoy.»* Todo lo que dependa de D1 (ficha de caso), D4 (visión y transcripción), D5 (vínculo post-servicio), D6 (registro de promesas), D7 (rol y quién decide) o D10 (rescate de hilo) va a `odd/analysis/lumatdata/escenarios-objetivo.md`, **nunca** al corpus. Un rojo permanente destruye la señal del instrumento.

**S5 — `hard_fails` en imperativo y desde lo que el humano hizo bien.** Redactados como el error a evitar («Repetir la dirección ya entregada»), no como el deseo («Recordar al cliente»).

**S6 — Privacidad sin perder el registro.** Nombres, direcciones, teléfonos y RUT se sustituyen; las faltas de ortografía, los modismos y la puntuación se conservan. El registro es lo que se mide.

**S7 — Los quince ids son los del doc 04 §4**, con la corrección de una errata: `real-vocabulario-impreciso` (el doc 04 escribe `impresiso`). Son estables para siempre una vez commiteados.

**S8 — El instrumento no se toca.** `scripts/conv_eval.py` queda igual: no se agregan gates, ni campos, ni flags. Esta unidad agrega **datos** (el YAML) y **un documento** (`escenarios-objetivo.md`). Si un escenario necesita un gate que no existe, se registra como objetivo, no se implementa acá.

**S9 — El corpus valida.** Criterio del doc 04 §7: *«`uv run python scripts/conv_eval.py --validate-only` pasa con 30 escenarios.»* Sin base de datos, sin modelo.

## Tasks

| ID | Spec | Ruta | Entrega |
|---|---|---|---|
| T1 | S1,S2,S3,S5,S6,S7 | `scripts/conv_eval_corpus.yaml` | 4 escenarios `simple` |
| T2 | idem | idem | 5 escenarios `complejo` |
| T3 | idem | idem | 6 escenarios `supercomplejo` |
| T4 | S4 | `odd/analysis/lumatdata/escenarios-objetivo.md` | los 6 objetivos imposibles, con su defecto y su criterio de salida |
| T5 | S9 | — | `--validate-only` con 30, más `quick` y `diff --check` |

Los quince, por tier y origen (doc 04 §4):

- **simple (4):** `real-cortesia-no-es-reclamo` (Javier Gálvez) · `real-precio-mantencion-ciclo` (Nancy Flores) · `real-cobertura-condominio` (María Eliana Pérez) · `real-vocabulario-impreciso` (Catalina Correa)
- **complejo (5):** `real-dato-mas-pregunta` (Carla Pacheco / Carlos Díaz) · `real-arrendatario-no-decide` (Diego Prado / Guila Sosman) · `real-multi-equipo-un-mensaje` (Sol) · `real-solo-sabados` (Sandra Paredes) · `real-reagenda-familiar` (Carla Pacheco)
- **supercomplejo (6):** `real-postventa-al-dia-siguiente` (Antonieta Saavedra) · `real-reclamo-real-si-deriva` (Sonia Bahamondez) · `real-olor-gas-en-hilo` (Pabla Leiva) · `real-cotizacion-fuera-catalogo` (Paulina Jungk) · `real-repuesto-agotado` (Lukas) · `real-cliente-experto` (Carlos Díaz Riveros)

## Log

### L1 — pedido del owner, verbatim

```text
si arranca con fase 1
```

Contexto aprobado en el mensaje anterior (roadmap, Fase 1): *«los 15 escenarios del doc 04 a `scripts/conv_eval_corpus.yaml`, verbatim, con `notes` citando conversación y línea, más `escenarios-objetivo.md` con los seis que hoy no pueden pasar. Riesgo bajo — sólo datos del instrumento, no se toca el bot.»*

### L2 — por qué esta unidad va antes de tocar el bot

Sin corpus no hay forma de saber si D2 general, D8 y D9 importan, ni de detectar que un cambio posterior rompió algo. El docstring de `conv_eval.py` lo dice mejor que este documento: *«The owner was writing a new conversation by hand every time the bot changed, which measures the owner's imagination, not the bot.»*

### L3 — fuente de los turnos

Los turnos verbatim salen del corpus entregado por el dueño, en `/home/stefan/repos/LumatData/Chat bot IA-20261112T160227Z-1-001/Chat bot IA/chats raw/` (autorizado explícitamente para este análisis, lectura sólo), y de las citas ya extraídas en `odd/analysis/lumatdata/02`, `04` y `05`. Cuando un turno no esté citado en esos documentos, se toma del corpus crudo y se registra la conversación y la línea en `notes`. **Nunca se inventa texto de cliente.**

### L4 — primera entrega: valida, pero mide poco

El worker entregó 30 escenarios que validan y los seis objetivos. Auditoría del padre con el loader real: **15 de 16 turnos de cliente existen verbatim** en el corpus crudo. Pero **14 de los 15 escenarios declaraban un solo turno**, contra §3.1 del doc 04 («Un escenario son 2-5 turnos»). Un `complejo` de un turno no mide retención de captura.

### L5 — el doc 04 queda desautorizado como fuente de texto verbatim

Auditoría de las 21 citas «…» del doc 04 contra el corpus crudo: **5 son verbatim, 16 no**. Once de ellas están en la tabla §4 presentadas como «turno más duro» y son parafraseos, algunas con «…» uniendo dos fragmentos. El turno no verbatim de `real-solo-sabados` vino de ahí.

Consecuencia: **sólo el corpus crudo es fuente de texto verbatim.** El doc 04 sigue siendo la especificación funcional (qué escenario, qué exige), no la fuente de los turnos. El doc se corrige en su propio PR.

### L6 — segunda pasada: fragmentos multi-turno

`simple` 1-2 turnos, `complejo` 3-5, `supercomplejo` 3-6, cada uno un fragmento contiguo de **una** conversación. Resultado: 44 turnos de cliente en 15 escenarios; **44/44 verbatim** tolerando las redacciones `[nombre]`, `[dirección]`, `[condominio]`. Cero teléfonos ni RUT; cero nombres, calles o comunas en el bloque nuevo.

### L7 — `real-reclamo-real-si-deriva` no puede exigir escalación

El worker lo omitió porque en la conversación de origen sólo hay dos mensajes de cliente en la misma fecha. Se repone con esos dos turnos, pero **sin exigir escalación**, por una razón medida:

> Sobre **2.049 mensajes reales de cliente**, la única coincidencia de todo el vocabulario del detector de reclamo (`reclamo`, `queja`, `molesto`, `enojado`, `estafa`, `devolución`, `reembolso`, `defectuoso`, `malservicio`, `no me sirve`, `nadie responde`) son **tres «te molesto» de cortesía**. Cero reclamos reales disparan el gate.

Un cliente enojado de verdad escribe «me dejaste la embarrada» y «muy irresponsable», no «reclamo». Exigir `state_any: [human]` ahí sería un rojo permanente (S4). El control positivo de D3 sigue siendo `super-enojo-reclamo`, escrito a mano. **Hallazgo colateral para el análisis: el disparador de reclamo no tiene vocabulario de la calle; hoy es código sin tráfico que lo ejercite.**

### L8 — los tests que fijan el corpus eran tres, no uno

Además de las dos aserciones de tamaño (`94-95`), `test_validate_only_accepts_the_shipped_corpus` (`985-990`) y `test_selection_filters_by_tier_and_by_id` (`1007`) fijaban `15` y `simple 6` / `supercomplejo 5`. Se actualizaron a `30`, `simple 10`, `complejo 9`, `supercomplejo 11`, y `len(by_tier) == 11`. `tests/unit/test_conv_eval.py`: **128 passed**.

### L9 — fuga propia, corregida antes de commitear

La primera versión del escenario de Sonia quedó con el nombre del dueño y dos calles sin redactar, en el turno y en la cita de `notes`. La detuvo el auditor de fuga, no la lectura. Corregido: `[nombre]`, `[dirección]` dos veces, y la cita de carpeta pasa a `[corredora] Corredora La Reina…`.
