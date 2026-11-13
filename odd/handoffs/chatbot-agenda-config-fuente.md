# HANDOFF — hilo del chatbot: retomar después del testeo en producción

**Fecha**: 2026-10-29. **Para**: el próximo chat que retome el hilo del chatbot de Lumat.
**Regla de entrada**: el owner está testeando en producción **ahora**. Antes de proponer nada, pedile los hallazgos de ese testeo (conversaciones concretas, no impresiones) o leé las conversaciones nuevas en la base. No re-abrir lo que este documento marca como cerrado.

---

## Estado del repo y de producción (verificado, no supuesto)

| Cosa | Valor |
|---|---|
| `main` | `23d1d29f` (merge de #732), árbol limpio, sin PRs abiertos |
| Producción | `v2026.10.11` = `046a1254`, `/health` lo confirma |
| Schema | 058 (sin migraciones nuevas en los dos últimos releases) |
| Worktrees | solo el principal. Los del slice B, ya removidos |

### PRs de esta sesión (todos mergeados con CI verde)

- **#725** — respuestas de cobertura, horario y duración desde configuración (`app/chat/nodes/configured_answers.py`), evaluadas en `respond()` **antes** de `retrieve_chunks`.
- **#726** — la KB de cliente deja de enunciar esos valores; `docs/kb/drift-baseline.json` = `[]` (tolerancia cero).
- **#728** — una ventana 24/7 ya no se anuncia como horario de atención (S9).
- **#729 / #731** — releases `v2026.10.10` y `v2026.10.11`.
- **#730** — nombres de duración con espacios de más: matching tolerante + validador que colapsa al guardar.
- **#732** — registro en `docs/ops.md` §2.9/§3 y la advertencia nueva de §2.5.

### Configuración de producción hoy

| Clave | Valor | Comentario |
|---|---|---|
| `coverage.communes` | 7 comunas | correcto |
| `hours.schedule` | todos los días `00:00–23:59` | **no es un placeholder**: es "sin restricción"; la agenda de los técnicos es la que acota. El bot responde 24/7 |
| `hours.closure_enabled` | `false` | el cierre fuera de horario es opt-in |
| `booking.service_durations` | 4 servicios × 60 min | el owner lo cargó; corregido y verificado 4/4 |

### KB de producción

4 documentos de cliente (ids `48`, `49`, `50`, `52`), títulos alineados a los H1 de `docs/kb`, **280 chunks**, fingerprint `baa03df47194`, ruteo por tema reparado (`--apply --force` → `reparados 4`, sin re-embed).

**Ojo con el historial**: los documentos viejos (44–47) se borraron y se re-subieron a mano el 2026-10-29. Ese camino **no** es válido (pierde `source_meta.source_id` y las versiones). Está documentado en `docs/ops.md` §2.5. Lección para no repetirlo: la KB se actualiza editando `docs/kb/*.md` y corriendo `seed_kb_docs.py --apply --force` dentro del contenedor.

## Qué mirar en el testeo del owner

Las respuestas deterministas nuevas, en este orden de sospecha:

1. **Cobertura**: "¿atienden en X?" con X cubierta → lista las comunas configuradas. Con X fuera de la lista → **no** contesta el bot determinístico; cae a la política de la KB (asesor). Si contesta una lista cuando la comuna no está cubierta, es un bug del detector.
2. **Horario**: cualquier pregunta de días/horas → "Las visitas se agendan según la disponibilidad de los técnicos." Si aparece un horario enumerado, la ventana de producción cambió.
3. **Duración**: "¿cuánto dura la mantención de calefont?" → "Mantención de calefont dura 1 hora." El nombre configurado se busca **como frase** dentro del mensaje: si el cliente dice "calefón" y la clave dice "calefont", no matchea (limitación conocida, sin stemming).
4. **Precedencia**: manda duración → cobertura → horario, la primera que reconoce el turno. Y una pregunta de precio que nombre servicio o comuna se va por el camino del tarifario, no por estos.

Si algo falla, la sonda que sirve para aislar sin gastar modelo, dentro del contenedor:

```bash
docker exec -i -w /app lumat-api-1 .venv/bin/python - <<'PY'
from app.chat.nodes.configured_answers import configuration_reply
from app.chat.state import ConversationState
from app.db import session_scope
def s(t): return ConversationState(customer_id=1, conversation_id=1, phone="+56900000000", turn=2, intent="consulta", window=[{"id":1,"text":t}])
with session_scope() as session:
    for q in ("que comunas cubren?", "cual es el horario?", "cuanto dura la mantencion de calefont?"):
        print(q, "->", configuration_reply(session, s(q)))
PY
```

## Deudas y pendientes reales (no inventar otras)

1. **Doc ODD con una fila desactualizada**: `odd/tasks/agenda-config-fuente.md` tiene B5 marcado `pendiente` aunque se entregó en `f5e718ff` (#728), y le faltan las entradas de log de los dos releases. Es un PR de docs de dos líneas; hacerlo al retomar.
2. **`test_assistant_settings_write::test_settings_update_applies_through_the_approval_loop`** hace una llamada **real** al modelo sin mock (viene de #723) y puede colgar el `full` según la red. Ajeno a este hilo, pero rompe la confiabilidad del gate.
3. **`topic_document_ids` no hace stemming**: "los sábados quién los coordina" no matchea el término `sabado` y cae a la búsqueda global. Pre-existente, no regresión.
4. **Dos familias de `Timeout` en el `full`**: locks (`idle in transaction` sosteniendo el `TRUNCATE` → reiniciar el contenedor de test DB y repetir) y la llamada real al modelo del punto 2.
5. **Checks del panel nunca corridos desde acá**: `/panel/api/kpis` autenticado y el render headless. Se puede hacer cuando haya credenciales en sesión.

## Trampas de entorno que cuestan tiempo

- `cmd | tail` devuelve el exit de `tail`, y `grep -c` devuelve 1 cuando cuenta cero. En jobs de fondo: `cmd > log 2>&1; echo "exit=$?"`.
- Un worktree nuevo necesita `cp ../lumat-agent/infra/.env infra/.env`, `uv sync`, `infra/test-db.sh up` y `DATABASE_URL=$TEST_ADMIN_DB_URL bash db/migrate.sh`. El contenedor tarda en aceptar conexiones: esperar readiness antes de migrar.
- Producción: contenedor con rootfs **read-only**. Para probes, `docker exec -i -w /app lumat-api-1 .venv/bin/python -` con el script por stdin; `docker cp` y `uv run` fallan.
- `gh pr merge --delete-branch` falla con `fatal: 'main' is already used by worktree` cuando el worktree principal tiene `main`; el merge remoto igual ocurre.
- Body de PR con backticks en un string de shell: los ejecuta. Escribir el body a un archivo y usar `--body-file`.
- El release es CalVer: subir `pyproject.toml`, PR, CI verde, merge, tag sobre el commit mergeado, deploy del tag. Nunca taggear un commit que no pasó `full`.

## Las tres respuestas, en una línea cada una

- Cobertura: `coverage_reply` (S4) — lista configurada; fuera de la lista, la política queda en la KB.
- Horario: `hours_reply` (S5, S9) — días y rango configurados; ventana total = disponibilidad de técnicos.
- Duración: `duration_reply` (S6) — la clave configurada como frase; sin duración configurada, camino de KB.

Specs completas y log con evidencia: `odd/tasks/agenda-config-fuente.md` (S1–S9, B1–B5, L1–L16).
Memoria: topic `odd/agenda-config-fuente/tasks` y `odd/agenda-config-fuente/deploy-record`; el incidente de KB, en `ops/kb-routing-repair-after-manual-upload`.
