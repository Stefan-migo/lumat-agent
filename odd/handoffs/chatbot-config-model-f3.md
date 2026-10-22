# HANDOFF — ODD `chatbot-config-model`, slice F3 (capa 3: conducta)

> **Superado.** F3 y F4 están mergeadas. Para continuar, usá `odd/handoffs/chatbot-config-model-f5.md`.

**Estado:** F1 mergeado (PR #644, `28a07508`). F2 mergeado en dos PRs encadenados: #645 (`b6f90e59`, T6–T7) y #646 (`a066f1a9`, T8–T9). `main` está en `a066f1a9`, sin worktree ni branch abiertos. F3 arranca desde `main`.

**F3 mergeada** (2026-10-21): #647 (T10) y #648 (T11), `main` pasó a `a34f55f7`.

**F4 mergeada** (2026-10-21, chat siguiente): **#649** (F4a, T14–T15, 354 líneas) y **#650** (F4b, T16–T17, 134 líneas), `main` en **`48ef8499`**. Sin worktree ni branches abiertos. Detalle y decisiones en `odd/tasks/chatbot-config-model.md` → Log T10–T17 y `L4`.

Hallazgo de F4 que conviene tener presente: la suite entera reservaba visitas en **Providencia**, que no está entre las siete comunas; con S15 eso deriva, así que los flujos de chat se migraron a **Ñuñoa**. Si escribís un test nuevo de captura, usá una comuna cubierta.

## Roadmap: F3 no es la última

| Slice | Capa | Specs | Tasks | Estado |
|---|---|---|---|---|
| F1 | Datos | S1–S5 | T1–T5 | ✅ |
| F2 | Copy | S6–S9 | T6–T9 | ✅ |
| **F3** | **Conducta (config)** | **S10–S11** | **T10–T11** | **✅ (PRs #647/#648, verdes)** |
| F4 | Conducta (comportamiento) | S14–S17 | T14–T17 | pendiente |
| F5 | Persona y seguridad | S12–S13 | T12–T13 | pendiente |
| F6 | Panel | S18 | T18 | pendiente |
| — | Invariantes | S19 | T19 | sin slice asignada |

El documento lista "Capa 4 — Persona y seguridad (F5)" **antes** de "Conducta (F4)", pero ese es el orden del texto, no el de dependencia. Orden recomendado: **F3 → F4 → F5 → F6**, y T19 al final (o dentro de F6), porque el test de contrato de los cinco invariantes necesita las superficies ya estables. F4 depende de `chat.conduct` (F3); F5 es independiente; S18 dice explícitamente que el rediseño del panel va último.

## Fuente de verdad

- `odd/tasks/chatbot-config-model.md` — en `main`: specs S1–S19, tareas T1–T19, `## Log` con T1–T9 cerrados y L0–L3. **No lo re-crees: extendelo.**
- Rapso session archivada: `.rapsodia-code/sessions/archived/2026-10-21-chatbot-config-brain/` (`session.md` D1–D11, `report.md`). Gitignored.
- Engram: `odd/chatbot-config-model/tasks` (mirror del doc), `odd/chatbot-config-model/delivery` (PRs de F2), `handoff/chatbot-config-model-f3` (este handoff).
- **No re-litigar** D1–D11 ni el diseño de `odd/tasks/chatbot-message-catalog.md`. Ojo: ese doc quedó desactualizado en un punto (ver Deuda).

## Arranque

```bash
rapso worktree create chatbot-config-model-f3 --yes   # consentimiento del owner ya dado por feature
cp ../lumat-agent/infra/.env infra/.env
uv sync                                               # test-db.sh necesita .venv; sin esto falla
bash infra/test-db.sh up
# Si tocás web/ recién ahí: cd web && npm ci
```

El slug es libre; lo que importa es nacer desde `main` (`a066f1a9`), que ya trae el task doc con F1 y F2.

Si recreás la DB de test, el suite **no migra**: corré `db/migrate.sh` con la `DATABASE_URL` admin (`tests._testdb.admin_database_url()`). Sin eso, todo falla por auth del rol `app`.

## Alcance F3 (S10–S11): configuración, no comportamiento

F3 mueve dos cosas a settings: el objeto de conducta y el orden de captura. **No** implementa "una pregunta por mensaje", ni reformulación, ni derivaciones efectivas: eso es F4 (T14–T17) y T15. F3 valida y expone; el flujo actual sigue funcionando igual hasta que F4 lo lea.

| ID | Task | Spec |
|---|---|---|
| T10 | Objeto `chat.conduct` + validación | S10 |
| T11 | Orden de captura efectivo desde configuración | S11 |

### T10 — `chat.conduct`

Una sola clave de settings, `chat.conduct`, con cuatro campos:

- `orden`: lista de campos, default `failure → equipment → comuna → availability → name → email → address`;
- `redaccion`: `llm` | `plantilla`, default `llm`;
- `max_preguntas_por_mensaje`: `1` | `2`, default `1`;
- `derivaciones`: reglas activas de la lista cerrada (cobertura, pedido explícito, garantía, servicio sin tarifa, presupuesto especial).

**Validación al guardar:** todo campo de `orden` existe en el modelo de captura, sin repetidos y con `name/email/address` después de `availability`; valores fuera del enum se rechazan; al menos una derivación queda alcanzable. Config inválida no se persiste.

Anclas verificadas hoy:

- El modelo de captura vive en `app/chat/nodes/capture.py:53` (`CAPTURE_FIELDS`, siete tuplas campo→texto) y su orden en `CAPTURE_FIELD_ORDER` (`:68`).
- **No existe** ninguna clave `chat.conduct` en el código: las únicas menciones son dos comentarios que apuntan a T10 (`capture.py:66`, `app/services/settings.py:57`).
- **Las cinco derivaciones no existen como concepto.** Los motivos de derivación actuales son otros: `persona`, `complaint`, `emergencia`, `injection_detected`, `unknown_intent_twice`, `scope_always_escalate` (`app/chat/nodes/handoff_gate.py:118`, `orchestrate.py:73-86`, `classify_intent.py:284-305`), más `kb_miss`, `kb_unavailable`, `booking_*`, `manage_*`. O sea: "pedido explícito" se parece a `persona`, y las otras cuatro son nuevas. Mapearlas es decisión de diseño de T10, no un renombre.
- `scope_rules` (`bot_resolve` | `always_escalate`) **no** es esto: es la política por categoría del clasificador. `derivaciones` es otra lista y no la reemplaza.
- Los cinco invariantes de S19 **no** entran acá: emergencia, límites de costo, consentimiento, no-inventar y takeover no se vuelven configurables. En particular, `chat.conduct` **no** debe entrar en `ASSISTANT_WRITABLE_SETTINGS` (`app/services/settings.py:661`) sin decisión explícita: hoy esa allowlist es el límite del asistente del panel.

Preguntas que T10 tiene que resolver antes de escribir código:

1. ¿`derivaciones` se guarda como lista de slugs activos o como mapa slug→bool? Precedente en el repo: `coverage.communes` es lista, `scope_rules` es mapa. La validación de "al menos una alcanzable" sugiere lista no vacía.
2. ¿`GET /settings` expone `chat.conduct` en F3? T6 y T7 no expusieron sus claves al GET porque la UI es F6; mantener esa línea deja F6 con el contrato completo. Si se expone ahora, hay que tocar los cinco lugares del contrato del panel (ver abajo).
3. ¿`chat.conduct.orden` valida contra `CAPTURE_FIELDS` **del código** o contra la lista de campos que el modelo de captura declara? Es el mismo conjunto hoy; conviene una sola fuente y que el validador la reciba como parámetro, igual que `validate_capture_questions(value, fields)` (T7), para no crear un ciclo `settings → capture`.

### T11 — el orden efectivo

El orden deja de estar solo en código: `chat.conduct.orden` pasa a ser la fuente, con el orden actual como default. El código sigue decidiendo **qué campo falta** (`_missing_fields`, `capture.py:197`) y sigue armando el lote; solo cambia de dónde sale la secuencia.

Anclas verificadas:

- `CAPTURE_FIELD_ORDER` (`capture.py:68`) → `_missing_fields` (`:197`) → `_ask_next` (`:275`).
- `MAX_ASKS = 3` (`:64`) y `_DIAGNOSIS_FIELDS = {"failure", "equipment"}` (`:131`): los diagnósticos se preguntan de a uno; el lote de 2–3 queda para datos de reserva. **Ese empaquetado sigue en código** (S11 no lo hace configurable).
- `capture.questions` (T7) guarda `{campo: texto}` y **su validador recibe el orden como parámetro**: `validate_capture_questions(value, fields)` en `app/services/settings.py`. Lo llama `POST /settings/capture-questions` con `CAPTURE_FIELD_ORDER` (`app/panel/api/routes/settings.py:42,504`). **Con el orden configurable, esa ruta tiene que pasar el orden efectivo**, o cambiar el orden deja `capture.questions` inválido (o guardable con las claves equivocadas). Es el acoplamiento menos obvio de la slice.

**Pregunta abierta que no hay que inventar:** S11 dice "`availability` se pregunta solo después de que el cliente aceptó la visita". Hoy no existe esa señal antes de `availability`: el consentimiento es un paso **posterior** a todos los campos (`capture.py`, `_pending == "consent"`), y la reserva ocurre después. O sea, "aceptó la visita" no puede ser el consentimiento. Antes de implementar el gating hay que decidir qué significa: ¿el intent declarado ("quiero una visita") alcanza como aceptación? Sin esa respuesta, T11 entrega orden configurable y deja el gating explícitamente fuera.

## Restricciones verificadas

- Strict TDD ON (`openspec/config.yaml:28,38`); runner `uv run pytest tests/`.
- `agent/*.md` byte-acoplado a `prompts.FALLBACKS` (`tests/unit/test_prompts.py:162`). Si tocás la persona o un template, editá ambos.
- `tests/unit` es DB-free desde `1731ef28`. Probarlo: `DATABASE_URL="postgresql+psycopg://app:app@127.0.0.1:1/nope" uv run pytest tests/unit -q` debe pasar.
- Correr `tests/unit`, `tests/integration`, `tests/functional` y `tests/injection` en invocaciones separadas.
- Pre-merge: `origin/main` al día, checks `test` + `panel` verdes, sin `--admin`, no auto-merge.
- `gh pr merge --delete-branch` falla localmente si `main` está en otro worktree (`fatal: 'main' is already used by worktree`): mergeá sin ese flag y limpiá branch/worktree a mano.
- `git worktree remove` rechaza directorios con archivos ignorados (`infra/.env`): usá `--force`.
- Docker de test por worktree: `bash infra/test-db.sh down` antes de borrar el worktree; si quedó huérfano, borrá `lumat-test-<proyecto>-db-test-1` y la red `lumat-test-<proyecto>_default`.
- Delivery: la feature usa `ask-on-risk`. F2 se entregó como dos PRs stacked-to-main porque el total superaba 2× el presupuesto de 400 líneas. Para F3, estimá primero: si entra en ~400, un PR; si no, proponé el corte antes de abrir nada.

## Contrato del panel (solo si agregás una clave al GET)

`web/src/stories/pages/_shared/mockData/settings.test.ts` compara las claves exactas del mock con `SETTINGS_KEYS`. Al agregar una clave al GET hay que tocar: `types.ts`, el mock, esa lista, y los fixtures de `Settings.test.tsx` y `SettingsEmail.test.tsx`. Si no, `tsc -b` falla (y `tsc` solo corre dentro de `npm run build`). `Settings.test.tsx` fija además la lista de secciones del panel.

Los mensajes del panel son copy en español de Chile: nada de voseo. `Settings.tsx` vive en `web/src/components/pages/`, no en `web/src/pages/`.

## Deuda y pendientes (no bloquean F3)

- **`odd/tasks/chatbot-message-catalog.md` está desactualizado:** documenta que un slot desconocido se renderiza como `""`, y S9 (T9, ya mergeado) lo prohíbe: ahora el preset se salta. Es el doc de otra feature; la corrección es decisión del owner.
- **Dos textos de captura siguen hardcodeados** a propósito: `_SOCIAL_REPLY` y el prefijo `"Entiendo, es un problema con tu {equipo}."`. Son copy de captura, no de las cinco áreas de T8; candidatos a absorber en F4 o a una slice de cierre.
- **`COMPLETION_REPLY`** no lo emite ningún flujo; solo `scripts/kb_fidelity.py` lo usa como fixture. Marcado con `ponytail:` en `capture.py`.
- **Acción de producción pendiente de F1:** los precios ya viven en settings. En el harness y en producción hay que cargar `tarifa.precios` desde el panel (sección Tarifas) y **retirar de la KB el documento de precios** si ya estaba ingerido; borrar el archivo del repo no borra la fila ingerida.
- Redacción default exacta de cada pregunta de captura, si el saludo se personaliza con el nombre, y derivaciones activas por defecto: decisiones de copy/producto, no de F3 salvo la última.
- De Lumat: IVA de los cuatro precios, exigibilidad del 15%, matriz de garantías, documentos SEC.

## Próximo paso inmediato

**F5** (T12–T13, persona y seguridad): persona editable con versión/diff/restaurar sobre `agent/personas/orchestrator.md` — acordate de `tests/unit/test_prompts.py:162`, el contrato espejado con `prompts.FALLBACKS` — y el protocolo de emergencia editable. Es independiente de F4. Después **F6** (T18, rediseño del panel, último) y **T19** (test de contrato de los cinco invariantes), que necesita las superficies estables.

Decisiones de producto abiertas, todas anotadas en Pendientes del task doc: gating de `availability` (S11, falta la señal de "aceptó la visita"), redacción de la reformulación (S14, hoy repite el texto configurado), y `redaccion: llm | plantilla` (S10) sin lector — redactar con el modelo es una llamada extra por turno.
