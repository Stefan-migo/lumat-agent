# HANDOFF — ODD `chatbot-config-model`, slice F5 (capa 4: persona y seguridad)

**Estado:** F1–F4 mergeadas. `main` en `48ef8499` (merge de #650), sin worktree ni branch abiertos. Grafo `graphify-out/` actualizado desde `48ef8499`. F5 arranca desde `main`.

## Roadmap: quedan F5, F6 y T19

| Slice | Capa | Specs | Tasks | Estado |
|---|---|---|---|---|
| F1 | Datos | S1–S5 | T1–T5 | ✅ |
| F2 | Copy | S6–S9 | T6–T9 | ✅ (PRs #645/#646) |
| F3 | Conducta (config) | S10–S11 | T10–T11 | ✅ (PRs #647/#648) |
| F4 | Conducta (comportamiento) | S14–S17 | T14–T17 | ✅ (PRs #649/#650) |
| **F5** | **Persona y seguridad** | **S12–S13** | **T12–T13** | **siguiente** |
| F6 | Panel | S18 | T18 | pendiente (último por S18) |
| — | Invariantes | S19 | T19 | sin slice; necesita las superficies estables |

## Fuente de verdad

- `odd/tasks/chatbot-config-model.md` — en `main`: specs S1–S19, tareas T1–T19, `## Log` con T1–T17 cerrados y L0–L4. **No lo re-crees: extendelo.**
- Este handoff reemplaza a `odd/handoffs/chatbot-config-model-f3.md` (histórico, ya cumplido).
- Rapso session archivada: `.rapsodia-code/sessions/archived/2026-10-21-chatbot-config-brain/` (D1–D11). Gitignored.
- Engram: `odd/chatbot-config-model/tasks` (mirror del doc, quedó en estado T9 — el doc en la branch es la fuente), `odd/chatbot-config-model/conduct` (decisiones F3/F4).
- **No re-litigar** D1–D11.

## Arranque

```bash
rapso worktree create chatbot-config-model-f5 --yes   # consentimiento del owner por feature
cp ../lumat-agent/infra/.env infra/.env
uv sync                                               # test-db.sh necesita .venv
bash infra/test-db.sh up
# Si tocás web/ recién ahí: cd web && npm ci
```

Si recreás la DB de test, el suite **no migra solo**: corré `db/migrate.sh` con la `DATABASE_URL` admin (`tests._testdb.admin_database_url()`).

Correr siempre en invocaciones separadas: `tests/unit`, `tests/integration`, `tests/functional`, `tests/injection`. Y probar `tests/unit` con `DATABASE_URL="postgresql+psycopg://app:app@127.0.0.1:1/nope"`: tiene que pasar (unit es DB-free).

## Alcance F5 (S12–S13)

| ID | Task | Spec |
|---|---|---|
| T12 | Persona editable con versión, diff y restaurar | S12 |
| T13 | Protocolo de emergencia editable, misma superficie | S13 |

### T12 — la persona

S12: la persona de Max es editable desde el panel sobre `agent/personas/orchestrator.md`, con historial de versiones, diff entre versiones y "restaurar default". Guardar una persona que rompe el contrato **no se persiste**.

Anclas verificadas hoy (main `48ef8499`):

- `agent/personas/orchestrator.md` y `agent/personas/orchestrator_brief.md` son los archivos; `respond.py:171-172` los consume con `prompts.load(...)`.
- `app/services/prompts.py:37` `FALLBACKS` (literales congelados) y `load()` en `:159-165`: devuelve `agent/{key}` **verbatim** y cae al literal con warning. `load` está decorado con `@lru_cache(maxsize=32)` (`:159`): si el contenido puede cambiar en runtime, hay que invalidar la caché.
- `tests/unit/test_prompts.py:162-164` (AC-3) exige `prompts.FALLBACKS[key] == agent/{key}` byte por byte. **Consecuencia de diseño:** si la persona editable se guarda en el archivo, ese test deja de poder pasar en cuanto alguien edite; si se guarda en settings con el archivo como default, el test sigue siendo válido y no hay que tocarlo.
- Precedentes de versionado en el repo, para reusar el patrón: `KbDocument.version` / `active_version` (`app/models.py:495-496`) con `POST /kb/{id}/restore` (pointer flip, audita), y `NotificationTemplateVersion` (`app/models.py:775`) con `UniqueConstraint(event, channel, locale, version)`.

### T13 — protocolo de emergencia

Las tres claves **ya existen** como settings con default y ya se leen: `emergency.safety_instructions`, `emergency.contacts`, `emergency.notify_message` en `app/services/settings.py:341-345`, consumidas por `app/chat/nodes/emergency.py:51-63`. Lo que falta es la superficie de edición, versión, diff y restaurar.

- Hoy solo `emergency.keywords` tiene ruta de panel (`app/panel/api/routes/settings.py:386`).
- El gate determinista de emergencia corre **antes** del LLM (`app/chat/nodes/emergency.py`, `emergency_gate.py`) y no debe depender de estas filas para disparar. Eso es S13 y también el invariante 1 de S19.
- `emergency.*` **no** está en `ASSISTANT_WRITABLE_SETTINGS` (`app/services/settings.py:845`): el asistente del panel no puede escribirlas. No lo cambies sin decisión explícita.

### Preguntas que F5 tiene que resolver antes de escribir código

1. **Dónde vive la persona editable.** Escribir `agent/personas/orchestrator.md` en runtime choca con el contenedor (FS efímero), con `lru_cache` y con el test byte-acoplado. La alternativa natural es una clave de settings (p. ej. `persona.orchestrator`) que `prompts.load` prefiera sobre el archivo, dejando el archivo como default y "restaurar default" = borrar la fila. Si se elige eso, `respond.py` y `emergency.py` **no** cambian: cambia `prompts.load`.
2. **Dónde viven las versiones.** Tabla nueva compartida por persona y emergencia, o reuso del patrón KB (`version` + `active_version` + restore). Si es tabla nueva, ¿una sola con un `scope`/`key`, o una por tipo?
3. **Qué se versiona.** S12 habla solo de `orchestrator.md`. ¿También `orchestrator_brief.md`? El brief se concatena en `respond.py:171-172`, así que una persona editada sin su brief puede quedar incoherente.
4. **Qué significa "rompe el contrato".** Con la persona en settings, el contrato verificable es: los placeholders que el prompt declara existen, el texto no queda vacío, y `tests/unit/test_prompts.py` sigue pasando sobre el default. Definilo antes de implementar; S12 no lo detalla.
5. **UI en F5 o en F6.** S12 dice "editable desde el panel" y S18 dice que el rediseño va último. Precedente: F1 metió el editor de Tarifas en su propia slice sin esperar a F6. Si entra UI en F5, se toca el contrato del panel (ver abajo); si no, F5 entrega rutas y F6 la UI — pero entonces "editable desde el panel" queda a medias y hay que registrarlo.
6. **Cómo se edita el diff.** Diff entre versiones: ¿lo calcula el backend (y devuelve un diff textual) o el panel compara dos versiones que ya puede leer?

## Restricciones verificadas

- Strict TDD ON (`openspec/config.yaml:28,38`); runner `uv run pytest tests/`.
- `agent/*.md` byte-acoplado a `prompts.FALLBACKS` (`tests/unit/test_prompts.py:162`). Si tocás la persona o un template, editá ambos.
- `tests/unit` es DB-free: probalo con una `DATABASE_URL` inalcanzable.
- Pre-merge: `origin/main` al día, checks `test` + `panel` verdes, sin `--admin`, no auto-merge.
- `gh pr merge --delete-branch` falla localmente si `main` está en otro worktree: mergeá sin ese flag y limpiá branch/worktree a mano.
- `git worktree remove` rechaza directorios con archivos ignorados (`infra/.env`): usá `--force`.
- Docker de test por worktree: `bash infra/test-db.sh down` **antes** de borrar el worktree.
- Delivery: la feature usa `ask-on-risk`; F2, F3 y F4 se entregaron como dos PRs encadenados porque cada una superaba ~400 líneas. Estimá primero y proponé el corte antes de abrir nada.
- **Tests de captura:** usá una comuna cubierta (**Ñuñoa**). F4 migró los flujos de Providencia a Ñuñoa porque S15 deriva las comunas fuera de las siete.

## Contrato del panel (solo si agregás una clave al GET o tocás web/)

`web/src/stories/pages/_shared/mockData/settings.test.ts:7` compara las claves exactas del mock con `SETTINGS_KEYS`. Al agregar una clave al GET hay que tocar: `types.ts`, el mock, esa lista, y los fixtures de `Settings.test.tsx` y `SettingsEmail.test.tsx`. Si no, `tsc -b` falla (y `tsc` solo corre dentro de `npm run build`). `Settings.test.tsx` fija además la lista de secciones del panel.

Los mensajes del panel son copy en español de Chile: nada de voseo. `Settings.tsx` vive en `web/src/components/pages/`, no en `web/src/pages/`.

## Deuda y pendientes (no bloquean F5)

- **`odd/tasks/chatbot-message-catalog.md` está desactualizado:** documenta que un slot desconocido se renderiza como `""`, y S9 lo prohíbe (el preset se salta). Es el doc de otra feature; la corrección es decisión del owner.
- **Dos textos de captura siguen hardcodeados** a propósito: `_SOCIAL_REPLY` y el prefijo `"Entiendo, es un problema con tu {equipo}."` de `_ask_next`.
- **`COMPLETION_REPLY`** no lo emite ningún flujo; solo `scripts/kb_fidelity.py` lo usa como fixture. Marcado con `ponytail:`.
- **Decisiones de producto abiertas** (todas en Pendientes del task doc): redacción de la reformulación de S14 (hoy repite el texto configurado), `redaccion: llm | plantilla` de S10 sin lector (redactar con el modelo es una llamada extra por turno), y la señal de "aceptó la visita" para gatear `availability` (S11).
- **Acción de producción pendiente de F1:** cargar `tarifa.precios` desde el panel (sección Tarifas) y **retirar de la KB el documento de precios** si ya estaba ingerido; borrar el archivo del repo no borra la fila ingerida.
- De Lumat: IVA de los cuatro precios, exigibilidad del 15%, matriz de garantías, documentos SEC.

## Próximo paso inmediato

Resolver las seis preguntas de arriba **antes** de escribir código, en particular (1) y (5): dónde vive la persona editable y si F5 incluye UI. Con eso, T12 en RED primero: el test byte-acoplado de `prompts` y el de "una persona que rompe el contrato no se persiste" son los dos que hay que escribir antes de tocar `prompts.load`.
