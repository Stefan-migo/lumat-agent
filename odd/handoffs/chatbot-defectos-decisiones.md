# Handoff — defectos del bot: las tres decisiones de producto

Escrito el 2026-10-27 al cerrar la sesión que abrió y avanzó la feature `chatbot-defectos`.
La fuente de verdad es **`odd/tasks/chatbot-defectos.md`** (S1–S6, T1–T6, L1–L10): leelo hasta `## Log` antes de tocar
nada. Este archivo es el mapa para arrancar en una sesión nueva, y su razón de existir son las **tres decisiones**
que quedaron abiertas.

## Dónde estamos

| | |
|---|---|
| Worktree | `/home/stefan/repos/lumat-agent-odd-chatbot-defectos` |
| Rama | `odd/chatbot-defectos` |
| Base | `main` = `d121e647` (PR #695 ya mergeado) |
| Abierto | **PR #697** (T5a + T5b), verde y `CLEAN` |
| Base de test | derivada, puerto **5907** |
| Instrumento | `scripts/conv_eval.py` + `scripts/conv_eval_corpus.yaml` (14 escenarios) |

**Cerrado y en `main`:** `super-emergencia-gas` (registra el evento `escalation`) y `simple-despedida` (la
despedida cierra aunque venga envuelta en cortesía).

**Cerrado en código, esperando merge:** T5a (la cobertura se evalúa antes de derivar) y T5b (un solo renderizado
de la pregunta para los dos caminos de captura).

**Bloqueado por estas decisiones:** T2b (retrieval, 4 escenarios), T6 (`no-quiere-email`) y el remate de
`super-burst-contradiccion` (G6).

## Antes de correr el evaluador, cuatro trampas que cuestan mediciones falsas

1. **Una suite por worktree.** `pytest` y el evaluador comparten base y se bloquean en el `TRUNCATE`.
2. **`pytest` vacía `kb_documents`.** Re-sembrar con `scripts/seed_kb_docs.py --apply` antes de cada corrida.
3. **`pytest` deja filas en `settings`.** `--reset` vacía 24 tablas de conversación y **`settings` no está entre
   ellas**, así que el bot de la próxima corrida queda configurado por el último test. Borrar `settings` antes de
   medir. Costó una verificación inválida entera (L7).
4. **Los tests van por `bash scripts/test.sh db …`**, nunca `uv run pytest` directo: el script exporta
   `TEST_POSTGRES_PASSWORD` y sin eso la migración falla con "permission denied to alter role".

Una corrida de un escenario: `--only <id> --judge-repetitions 3` tarda segundos o minutos, no 80. El trío
completo (tres corridas de 14) se reserva para el cierre de feature.

---

# Las tres decisiones

Cada una tiene: **de qué se trata en una frase**, **qué ve el cliente hoy**, **qué se midió** y **las opciones con
su costo**. Ninguna se puede elegir desde el código.

---

## Decisión 1 — Cómo busca el bot en su base de conocimiento

**En una frase:** cuando el cliente pregunta algo que la base **sí** responde, el bot a veces contesta "no tengo
ese dato, te contacta un asesor". Pasa en 4 de los 14 escenarios.

**Qué ve el cliente hoy**

```
cliente:  hola, ustedes trabajan en maipú?
bot:      No tengo ese dato. ¿Prefieres que te tome los datos para coordinar una visita,
          o que te atienda una persona?
```

La respuesta está en la base — el documento "Cobertura y horarios de Lumat" dice exactamente qué comunas se
cubren. El bot la tiene y no la encuentra.

**Por qué pasa.** El bot busca por **parecido semántico** entre el mensaje y los documentos, y corta en un umbral
de 0.50. Los mensajes del cliente son cortos y los pedazos de documento son largos, así que los puntajes salen
bajos: 0.40, 0.45.

**Lo que se midió, y por qué el atajo obvio está descartado**

| Consulta | Puntaje | ¿Debería encontrar? |
|---|---|---|
| `y eso cuanto de garantia tiene?` | 0.4498 | **sí** |
| `hola, ustedes trabajan en maipu?` | 0.4033 | **sí** |
| `hola, arreglan lavadoras? se me inundo el lavadero` | **0.4026** | **NO** |
| `hola, necesito mantencion de caldera, estoy en temuquito` | 0.3491 | **sí** |

La consulta que **no** debe encontrar nada puntúa **más alto** que tres de las cuatro que sí deberían. Bajar el
umbral haría que el bot conteste sobre lavadoras — que es justo el escenario que prueba que no se inventa
servicios (`super-near-miss-lavadora`, hoy pasa 3 de 3).

**Opciones**

- **(a) Buscar por intención, en el documento que corresponde.** El bot **ya** clasifica la intención de cada
  mensaje ("esto es una consulta de cobertura", "esto es un precio"), y los 4 documentos ya están separados por
  tema: cobertura y horarios, garantías y pagos, quiénes somos, servicios. Con eso, "trabajan en maipú" busca sólo
  en el documento de cobertura y lo encuentra sin depender del puntaje. Es la más precisa. **Costo**: toca el
  camino que alimenta **todos** los turnos del cliente, no sólo estos cuatro; hay que cuidar que "arreglan
  lavadoras" siga sin encontrar nada.
- **(b) Armar una mejor consulta.** En vez de buscar con la pregunta cruda, buscar con intención + tema
  ("cobertura comunas donde trabajamos"). Más barato de hacer, menos preciso que (a), mismo riesgo de alcance.
- **(c) Dejarlo así.** El bot deriva a un asesor: es seguro y no inventa nada, pero el cliente paga un turno extra
  y vos tenés conocimiento que no estás usando.

---

## Decisión 2 — Qué contesta el bot cuando la comuna está fuera de cobertura

**En una frase:** el bot deriva de inmediato y **nunca menciona el equipo** que el cliente acaba de corregir; y al
turno siguiente repite la misma frase textual.

**Qué ve el cliente hoy**

```
cliente:  no era calefont, es una caldera, y estoy en providencia
bot:      Todavía no tenemos visitas técnicas en Providencia, un asesor de Lumat se contactará
          contigo para ayudarte a la brevedad.
cliente:  cuanto sale y cuando pueden venir
bot:      Todavía no tenemos visitas técnicas en Providencia, un asesor de Lumat se contactará
          contigo para ayudarte a la brevedad.
```

Dos cosas a la vez: la corrección del equipo queda **sin acusar recibo**, y la segunda respuesta es **idéntica** a
la primera. El resto del escenario ya está arreglado: la derivación ahora registra la causa correcta
(`cobertura`), que era el otro defecto.

**Opciones**

- **(a) Acusar recibo en la derivación**: "Una mantención de caldera en Providencia: un asesor coordina la visita
  según disponibilidad". El cliente siente que lo escucharon, y la derivación sigue siendo la misma.
- **(b) No repetir**: si ya derivó, el turno siguiente no repite la frase — o responde lo que sí se puede (precio)
  y aclara que la visita la coordina el asesor.
- **(c) Dejarlo y aceptar que el corpus está mal.** El escenario espera que alguna respuesta diga "caldera". Si la
  política es "fuera de cobertura deriva de inmediato", esa expectativa puede ser la equivocada — pero entonces se
  cambia el **corpus**, y eso es una decisión explícita, no un ajuste para que dé verde.

**Ojo con lo que está en juego:** el corpus se alineó a la política real del producto en la feature anterior. Si se
toca, hay que tocar la especificación, no el número.

---

## Decisión 3 — Qué significa "el cliente se negó a dar un dato"

**En una frase:** hoy **no existe** una causa que signifique "el cliente se negó". Un rechazo explícito se registra
como "campo sin respuesta", que es un problema comercial distinto.

**Qué pasa hoy**

```
bot:      ¿Me dejas tu correo para agendar?
cliente:  no te voy a dar mi correo
bot:      ¿Me confirmas tu correo?               ← insiste
cliente:  no
bot:      [deriva] causa registrada: campo_sin_respuesta
```

`campo_sin_respuesta` significa literalmente "pregunté dos veces y no obtuve una respuesta aceptable". En el panel y
en las métricas se lee **"no contestó"**, cuando lo que pasó es **"dijo que no"**. Son dos problemas distintos: al
que no contesta se lo puede empujar; al que dijo que no hay que abrirle otro camino.

Detalle técnico que importa: existe `consent_declined`, pero **sólo** para el paso de consentimiento, no para los
campos de datos. Y el texto "no te voy a dar" no está entre las palabras de rechazo (`_SKIP_WORDS`).

**Opciones**

- **(a) Causa propia `campo_rechazado`** y que el agendamiento siga sin ese dato. Es lo que refleja la realidad y
  lo que hace medible el rechazo.
- **(b) Tratar el rechazo como "saltar el campo"** y hacer el correo opcional en el flujo de agendamiento. Más
  simple; cambia la regla comercial de qué datos son obligatorios.
- **(c) El bot está bien y el corpus está mal.** Posible, pero hoy el registro dice algo que no pasó, y eso ya es
  un defecto de datos aparte de lo que espere el corpus.

---

## Orden recomendado para la sesión nueva

1. **Decisión 1 (retrieval)** — desbloquea **cuatro** escenarios de una vez. Es la de mayor retorno y la de mayor
   alcance: todo turno del cliente pasa por ahí.
2. **Decisión 2 (cobertura)** — desbloquea cerrar `super-burst-contradiccion`, que ya tiene todo lo demás hecho.
3. **Decisión 3 (`no-quiere-email`)** — un escenario, pero es el único donde puede que el que esté mal sea el
   corpus.

Las tres se pueden tomar en la misma sesión `rapso-session` y salir con tres specs reescritas y tres tareas
desbloqueadas.

## Lo que NO hay que rehacer

- **El precio de la mantención no es un defecto.** Cuatro observaciones dieron `$50.000`; el cálculo es
  determinista y la elección de fila la hace el modelo. Está medido y descartado (L2).
- **La extracción de la comuna funciona** y **`equipment_type` se corrige**. Lo que quedaba obsoleto era el campo
  libre `equipment`, y eso ya se resolvió (L9, L10).
- **Los tres primeros intentos de T5 fallaron porque sus tests pasaban antes de implementar.** No repetir la vía de
  sembrar `_pending` en la base ni de mockear el clasificador: hay que medir el estado real y llamar la función
  directa (L9).
- **`conv_eval` debería validar `settings` antes de medir**: es un follow-up del **evaluador**, no del bot, y está
  registrado en L7.
