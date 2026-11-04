# ODD — cierre de conversación, push, agenda y enforcement del design system

Worktree `../lumat-agent-odd-cierre-agenda-push`, rama `odd/cierre-agenda-push`, base `a80a1525` (`main`, `v2026.11.1`).
Cuatro defectos medidos en producción el 2026-11-04, con la conversación #25 y el panel real como evidencia.

## Specs

### S1 — una despedida con calificador temporal cierra la conversación

> «en produccion sigue con problemas para cerrar la conversacion»

Conversación #25 de producción (`+5492972542298`, mensajes 372-373): el cliente escribió
**«No, eso sería todo por ahora»** y el bot respondió «¿Te puedo ayudar en algo más?». La frase
`eso seria todo` matchea en `_CLOSING_PHRASES`, pero los tokens sobrantes `por` y `ahora` no están en
`_COURTESY_TOKENS` (`app/chat/nodes/closure_gate.py:42-54`), así que `is_farewell` devuelve `False` y el
turno cae a `smalltalk`. Un calificador temporal no es contenido nuevo: la frase de cierre tiene que
seguir cerrando con `por ahora`, `por el momento`, `por ahorita` y equivalentes sin tilde.

La regla no puede aflojar lo que ya protegía el diseño: `eso era todo lo que necesitaba saber del precio`
sigue **abierto** (contenido real después de la frase), y `gracias` sola sigue **sin** cerrar.

### S2 — dos negativas consecutivas cierran la conversación

> «me dice que el navegador no las acepta» / «No gracias» · «No» · «Noooooooooo»

Los mensajes 372, 374, 376 y 378 de la conversación #25 son negativas del cliente a la pregunta de cierre
del bot, y el bot repitió la misma pregunta cuatro veces hasta que el cliente escribió «Chao». `no` vive a
propósito en `_COURTESY_TOKENS` y no en `CLOSING_TOKENS`, así que una negativa nunca cierra nada.

Decisión del owner (2026-11-04): **contar, no interpretar**. Dos negativas consecutivas del cliente,
separadas por una pregunta del bot, cierran la conversación. Una negativa sola **no** cierra: sigue
siendo un «no» que responde otra cosa. El cierre usa el mismo camino que la despedida
(`set_conversation_state(..., ConvState.CLOSED, cause="farewell", actor="bot")`) para no inventar una
segunda causa en el campo `cause`.

Dos precisiones que la implementación dejó fijas (L4):

- **Negativa es el mensaje entero.** `No tengo agua caliente` abre con «no» pero responde algo; cuenta
  sólo cuando lo que sigue al «no» son cortesías o calificadores. `Noooooooooo` cuenta igual, porque la
  letra repetida se colapsa.
- **La pregunta del bot se reconoce por su forma, no por su texto.** Exigir el copy exacto de
  `messages.smalltalk_decline` ataba la regla a un texto que el operador puede editar desde el panel —
  editarlo habría apagado el cierre en silencio, y el doble de tests no lo reproduce. La condición es
  «el mensaje del bot entre las dos negativas termina en `?`».

### S3 — el panel dice la verdad sobre por qué push no se puede activar

> «al activar las notificaciones push me dice que el navegador no las acepta. pero estoy usando
> navegadores modernos que deberia aceptarlo»

`web/src/components/pages/PushSettings.tsx:19` mapea `config.public_key === null` a
`setPermission("unsupported")`, y el texto renderizado es **«Este navegador no admite push.»** Es falso: la
causa medida en producción es que `/opt/lumat/infra/.env` no tiene **ninguna** variable `VAPID_*`
(`app/config.py:69-71`), por lo que `GET /panel/api/push/config` devuelve `{"public_key": null}`
(`app/panel/api/routes/notifications.py:22-23`).

Tres causas distintas necesitan tres mensajes distintos, y el operador tiene que poder distinguirlas sin
abrir la consola: (a) el navegador no soporta push, (b) el servidor no tiene push configurado, (c) el
operador denegó el permiso. `«Este navegador no admite push»` queda reservado al caso (a).

### S4 — producción entrega un `public_key` real y guarda la suscripción

> «Autorizás generar claves VAPID en producción» → «Sí: generar claves y recrear api»

Hoy `push_subscriptions` tiene **0 filas** y `GET /panel/api/push/config` devuelve `null`. Producción
necesita el par VAPID en `/opt/lumat/infra/.env` (`VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`,
`VAPID_SUBJECT`), el contenedor `api` recreado y el endpoint devolviendo la clave pública. La clave privada
nunca se imprime ni se guarda en el repo, en memoria ni en el chat.

`docs/ops.md` tiene que documentar cómo se generan, dónde viven y cómo se verifica el endpoint, porque es la
diferencia entre «el navegador no soporta push» y «falta configuración de despliegue».

### S5 — el panel de visitas vencidas sigue el design system

> «toda la parte nueva para ver las agendas vencidas solo se solto sobre el panel no tiene ningun diseno»

`web/src/components/shared/OverdueVisitsPanel.tsx` usa `<section>`, `<h2>`, `<ul>`, `<li>`, `<label>` y
`<time>` **sin una sola clase propia**; los únicos `className` del archivo pertenecen a los diálogos internos
(`appointment-detail__*`). En CSS no existe ninguna regla `overdue-*`. El resultado es HTML por defecto
encima de una página que sí tiene gramática visual (`primitives.css:3192`, `agenda-page__*`).

El panel se integra a la página de Agenda con el vocabulario existente: `Card`, `Badge`, `Button`,
`StateMessage`, tokens semánticos de `web/src/tokens/tokens.css` y clases en `primitives.css`. Tiene que
declarar el modelo de estados completo que exige `web/DESIGN_SYSTEM.md:656-687`: vacío (no renderiza nada,
comportamiento actual), selección activa, acción masiva en curso, resultado por fila (éxito y error, con
`role="status"`/`role="alert"` como hoy) y error de cierre individual. Nada de colores crudos fuera de
`tokens.css` (`DESIGN_SYSTEM.md:643-654`, regla 6).

### S6 — el link «Configurar horarios de técnicos» sale de Agenda

> «tambien hay que sacar el link que dice configogurar horsrios de tecnicos, eso se traslado todo a configuracia»

`web/src/components/pages/AgendaPage.tsx:316` renderiza `<a href="/panel/app/settings#schedule">Configurar
horarios de técnicos</a>` dentro de `<section aria-label="Registro de agenda">`. La configuración de horarios
ya vive en Configuración, así que el link se retira de la Agenda. Las tres citas que lo afirman
(`AgendaPage.test.tsx:108,122` y `AgendaPage.stories.test.tsx:187`) se actualizan a la ausencia del link; no
se borran sin reemplazo, porque hoy son la única aserción de que ese acceso no vuelve.

Los tests de `aria-label="Registro de agenda"` y de los tabs no cambian.

### S7 — el agente tiene que encontrar el design system, y una página sin diseño tiene que fallar

> «el agente cuando tiene que implementar logicas nuevas no sigue el dieño ya establecido en el systema.
> podrias averiguar por que pasa eso?»

Cuatro causas medidas, las cuatro corregibles:

1. `.agents/skills/design-system/SKILL.md` manda leer `DESIGN.md`, que **no existe** en el repo, y usar
   **Tailwind**, que el proyecto no usa. La skill enseña otro stack.
2. `web/DESIGN_SYSTEM.md` es la autoridad real (697 líneas, `## Implementation rules for coding agents` en
   L643 y `## Acceptance checklist` en L656) y **no está nombrada en `AGENTS.md` ni en ninguna skill
   obligatoria**.
3. `DESIGN_SYSTEM.md:367` avisa que `Agenda` no tiene sección de page architecture y que «their absence is not
   permission to improvise»; nadie lo hizo cumplir.
4. Nada lo verifica: un componente sin clases pasa CI, `panel` y review.

El arreglo tiene que ser de las cuatro: `AGENTS.md` nombra `web/DESIGN_SYSTEM.md` como lectura obligatoria
para trabajo de UI; la skill `design-system` apunta al archivo real y al stack real (`tokens.css`,
`primitives.css`, primitives, Storybook); `DESIGN_SYSTEM.md` gana la sección de page architecture de Agenda con
el contrato de visitas vencidas; y un test estructural falla cuando un componente de página de `web/src`
declara markup propio sin ninguna clase.

## Tasks

| ID | Spec | Qué | Verificación |
|---|---|---|---|
| T1 | S1, S2 | `closure_gate`: calificadores temporales en `_COURTESY_TOKENS` y cierre por dos negativas consecutivas leídas de `state.window` (sin persistir contadores) | **Delivered** · `8aff0a65`: RED sin la implementación, GREEN con ella (integración 20, `focused` y `quick` en 0) |
| T2 | S3 | Mensajes honestos y separados para (a) navegador sin soporte, (b) servidor sin push configurado, (c) permiso denegado | **Delivered** · `152c21b8`: 6 casos de `PushSettings`, `npm run build` exit 0 |
| T3 | S4 | **Parent-owned** · claves VAPID en prod, `.env` con backup, `api` recreado, endpoint devolviendo clave pública, procedimiento en `docs/ops.md` | **Keys in place, endpoint pending the deploy** · `9c168a5a`: par VAPID en `/opt/lumat/infra/.env` (backup `infra/.env.bak-20261104T162254Z`, 600, par verificado firmando un header); el `api` no puede verlas hasta que el release reenvíe las variables |
| T4 | S5, S6 | Panel de vencidas con el vocabulario del design system y sus estados; link de horarios retirado | **Delivered** · `c477edf6`: 63 casos enfocados + 12 de stories, `npm run build` exit 0 |
| T5 | S7 | `AGENTS.md`, skill `design-system`, sección de Agenda en `DESIGN_SYSTEM.md` y test estructural de markup sin clases | **Delivered** · `6eb9a141`: el chequeo falla con 14 contenedores sin clase y pasa con el baseline; las 3 entradas del panel de vencidas se retiraron en `c477edf6` |

Los commits van por unidad (T1, T2, T3, T4, T5), con sus tests y docs al lado del comportamiento.

## Log

### L1 — pedido original, verbatim

> hey chat necesito que entres al vps solo lectura y revises la ultima conversacion con stefan, revisa cual es
> eñ bug encontrado. en produccion sigue con problemas para cerrar la conversacion.
>
> otra cosa que me he dado cuenta es el problema de las notificaciones al activar las notificaciones push me
> dice que el navegador no las acepta. pero estoy usando navegadores modernos que deberia aceptarlo.
>
> lo otro es mejorar el diseño de agenda hay varias cosas que no deberian verse como estan actualmente.
> principalmente la seccion agenda. toda la parte nueva para ver las agendas vencidas solo se solto sobre el
> panel no tiene ningun diseño. tambien hay que sacar el link que dice confogurar horsrios de tecnicos, eso se
> traslado todo a configuracia
>
> cpn esto me dpy cuenta que el agente cuando tiene que implementar logicas nuevas no sigue el dieño ya
> establecido en el systema. podrias averiguar por que pasa eso?

### L2 — evidencia de producción (solo lectura, 2026-11-04)

VPS `179.199.148.175`, `deploy@`, `/opt/lumat`, compose project `lumat`. `/health` →
`{"status":"ok","version":"2026.11.1","commit":"846481e9"}`. Contenedores `api`, `nginx`, `db` healthy.

Conversación **#25** (`wa_phone +5492972542298`, `customer Stefan`), 15:48:25 → 15:54:05 UTC, `state=closed`,
`closed_at=15:54:05`. Mensajes 349-381 leídos enteros. Eventos 217-229: el único `state_change` es
`bot->closed: farewell` a las 15:54:05, disparado por «Chao». Los turnos 372, 374, 376 y 378 quedaron
clasificados como `smalltalk` (eventos 225-228) y recibieron la misma respuesta.

Push: `/opt/lumat/infra/.env` tiene 58 líneas y **ninguna** variable `VAPID_*`; `settings` sin filas de push;
`push_subscriptions` con **0 filas**; `printenv` del contenedor `api` sin VAPID.

Agenda: `OverdueVisitsPanel.tsx` sin clases propias; `primitives.css` sin reglas `overdue-*`; el link de
horarios citado en `AgendaPage.tsx:316`, `AgendaPage.test.tsx:108,122` y `AgendaPage.stories.test.tsx:187`.

Design system: `find . -name DESIGN.md` no devuelve nada; `.agents/skills/design-system/SKILL.md:22` manda
leerlo y L45 manda Tailwind; `grep DESIGN_SYSTEM AGENTS.md` no devuelve nada.

### L3 — las cuatro decisiones del owner

- **Cierre**: «Frases + cerrar tras 2 negativas seguidas» — contar, no interpretar.
- **Entrega**: «Un worktree y una rama para los 4 cambios» → `odd/cierre-agenda-push`.
- **VAPID en producción**: «Sí: generar claves y recrear api».
- **Agenda**: «Implementar directo con DESIGN_SYSTEM», sin maqueta previa.

### L4 — T1 verificado; dos correcciones sobre lo que devolvió el worker

`app/chat/nodes/closure_gate.py` + `tests/unit/test_closure_gate.py` +
`tests/integration/test_out_of_hours_and_farewell.py`:

- RED sin la implementación (stash del archivo): `bash scripts/test.sh db
tests/integration/test_out_of_hours_and_farewell.py` → exit 1, fallan
`test_production_sequence_closes_after_temporal_qualifier` y `test_two_refusals_close_but_one_refusal_does_not`.
- GREEN con la implementación: mismo comando → exit 0, 20 casos; `focused` de la unit → exit 0; `quick` → exit 0;
`shape` → exit 0 (ninguna superficie de shape).

Lo que corregí del lote del worker, y por qué:

1. **Su test comparaba el copy configurado.** El doble de clasificador responde `unknown` a un «No» suelto, así
   que el bot contestaba la aclaración y no la pregunta de cierre: el test medía el doble, no la regla. La regla
   pasó a exigir «una pregunta del bot» (`endswith("?")`), y los tests afirman la forma, no el texto.
2. **`_is_refusal` aceptaba cualquier mensaje que empiece con «no».** «No tengo agua caliente» es una queja y
   habría contado como negativa; ahora sólo cuenta la negativa sin contenido (cortesías/calificadores detrás) y
   se colapsan letras repetidas para que «Noooooooooo» también cuente.
3. **`event.cause` no es `farewell`**: el evento guarda `bot->closed: farewell` (`app/chat/state.py:146`). Los
   tests afirman la cadena real.

Entorno del worktree (costó dos intentos): no hay `.venv` local y `db/migrate.sh` sólo respeta `PYTHON` cuando
falta el `.venv`; se resolvió con un symlink `.venv` → el del worktree principal y `web/node_modules` → el del
principal. La base de test del worktree escucha en 5701.

### L5 — corte de entrega: dos PRs, no uno

La rama llegó a **650 líneas autoradas en 3 commits** (doc ODD 203, T1 151, T5 296) y el trabajo que falta (T2,
T3, T4) ronda otras 550. Un solo PR sería una revisión de ~1200 líneas, que es exactamente lo que la disciplina
de work units prohíbe. Corte declarado:

- **PR 1 (listo para revisar)**: `docs(odd)` + T1 (cierre de conversación) + T5 (design system: skill, AGENTS,
  contrato de Agenda, chequeo estructural y baseline). Historia: el bot cierra y el próximo cambio de panel no
  puede volver a inventar diseño.
- **PR 2 (después del 1)**: T2 (mensajes de push) + T3 (VAPID en producción y `docs/ops.md` §2.8.3) + T4 (panel
  de visitas vencidas + retiro del link de horarios).

Los PRs y el deploy los decide el owner; la rama no se pushea sin ese pedido.

### L6 — T4 entregado y corregido; cierre en curso

El band de vencidas quedó con clases BEM y CSS por tokens (`overdue-visits__*`), sin un solo hex crudo, y el link
de horarios se retiró con sus tres aserciones invertidas a ausencia deliberada. Dos correcciones propias sobre
lo que devolvió el worker:

1. **`aria-label` que no contenía el texto visible.** El botón masivo decía «Cerrar 3 visitas seleccionadas» y
exponía «Cerrar visitas seleccionadas»: viola label-in-name (WCAG 2.5.3). Se quitó el `aria-label`; los tres
tests consultan ahora por el texto visible con una expresión regular.
2. **Dos modificadores sin reglas.** `overdue-visits__result--success/--error` se aplicaban sin CSS; se les dio
borde y fondo con `--success-*` y `--danger-*`, sin que el color sea el único canal (el texto ya lo dice).

Verificado: `npx vitest run` de los 3 archivos enfocados → 63 casos; stories de Agenda → 12; `npm run build`
exit 0; el chequeo estructural queda verde con el baseline en 11 entradas.

### L7 — cierre: las dos suites completas

- **Backend `full`**: exit 0, 6m 14s, hasta 100%. Advertencias preexistentes (pooling del modelo FastEmbed, ninguna
  falla).
- **Panel `npm test`**: la primera corrida dio **1 falla de 1392** en
  `AppShell > keeps the push deep link landing on the single standalone push settings page`. Causa real y
  legítima: la página de push ahora exige las tres capacidades (`PushManager`, `Notification`,
  `serviceWorker`) porque sin ellas el botón no puede funcionar, y el test de AppShell sólo simulaba
  `PushManager`. Se completó el test, no se aflojó el componente: **segunda corrida exit 0, 120 archivos / 1392
  casos**. La suite completa atrapó exactamente la clase de regresión que un archivo enfocado no ve.
- `shape` → exit 0 (ninguna superficie de shape tocada: el compose y los docs no están en la lista).

Cierre del worktree: `.venv` y `web/node_modules` son symlinks locales (gitignoreados) y la base de test en 5701
queda levantada hasta el cleanup del worktree.
