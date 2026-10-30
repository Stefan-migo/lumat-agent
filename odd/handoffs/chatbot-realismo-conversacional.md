# HANDOFF — chatbot-realismo-conversacional

**Estado al cerrar la sesión**: **todo mergeado**. Las cuatro PRs de la cadena (`#738`, `#740`, `#741`,
`#743`) y la de las últimas dos unidades (`#750`, C4 + C2). Producción corre `v2026.10.13`, esquema
**060_capture_ack_plain**: las migraciones `059` y `060` ya se aplicaron. El worktree vigente es
`/home/stefan/repos/lumat-agent-odd-chatbot-realismo-c4`.

**Regla de entrada**: leer `odd/tasks/chatbot-realismo-conversacional.md` (S1–S14 + Log L1–L19) antes
de proponer nada. Los specs citan los mensajes reales. No re-abrir lo cerrado; las decisiones ya
tomadas por el owner están en el Log y en este documento.

---

## 1. De dónde salió esto

Auditoría read-only (2026-10-29) de las conversaciones de prueba del owner:

- **Producción** `agente.lumat.cl`: conversación **#23** (customer #2, 30 mensajes) y #22. Acceso:
  `ssh deploy@179.199.148.175` + `sudo -n docker exec lumat-db-1 psql -U lumat -d lumat` (sólo SELECT).
  Ojo: `~/.ssh/config` apunta a `138.128.243.241`, que **no responde**; el host real es
  `179.199.148.175` (`agente.lumat.cl` resuelve ahí) y root está deshabilitado.
- **Harness local**: `lumat-harness` (api :8001, db :5433), conversaciones #37–#46.

De ahí salieron 14 defectos, cada uno con su mensaje textual en el doc.

## 2. Qué está hecho

| unidad | spec | commit | PR |
|---|---|---|---|
| A1 ack sin "Gracias" + migración `060_capture_ack_plain.sql` | S1 | `f7a6162b` + renumeración `6602e4ed` | #738 ✅ |
| B1 franja "después del mediodía" / "después de las 12" | S8 | `0a7914cd` | #740 ✅ |
| B2 abreviaturas de mes (`3 de nov`) | S9 | `0a7914cd` | #740 ✅ |
| A2 cobertura sin precio ni promesa repetida | S5 | `04b993c9` | #741 ✅ |
| A3 despedida larga cierra | S6 | `63b890ec` | #741 ✅ |
| A4 consentimiento acepta "si autorizo" | S7 | `9c63dc20` | #741 ✅ |
| A5 "manutención" = preventivo (matcher de catálogo) | S4 | `a15e0edb` | #741 ✅ |
| C1a consentimiento ya dado → salto silencioso al booking | S3 | `faaed3dc` | #741 ✅ |
| B3 no re-ofertar la misma página / no resetear `attempts` | S10 | `4871dc62` | #741 ✅ |
| B4 `state.booking` sin citas pasadas | S11 | `0faf5c72` | #741 ✅ |
| B5 reagendar no se lee como respuesta de captura | S12 | `14c75a76` | #743 ✅ |
| C3 una pregunta por turno tras desviación de KB | S13 | `f6f088f2` | #743 ✅ |
| C1b cliente conocido confirma su contacto en un mensaje (1 año) | S3 | `5ab5e171` | #743 ✅ |

Cadena de PRs (cada una con base en la anterior; hoy las cuatro contienen `origin/main` = `2bb8f0fb`):

```
main 2bb8f0fb
 └── #738  odd/chatbot-realismo-ack              6602e4ed  ack + spec + migración 060
      └── #740  odd/chatbot-realismo-agenda-window  7aa71d86  franja + meses
           └── #741  odd/chatbot-realismo-conversacional  cb7d5973  copy + consentimiento + preventivo + loop + state + manage
                └── #743  odd/chatbot-realismo-flujo   7e3bf6fa  una pregunta por turno + contacto confirmado
```

## 3. Qué falta

| unidad | spec | qué hay que hacer | nota |
|---|---|---|---|
| **C4** | S14 | Normalizar `case.service` contra el catálogo **antes** de usarlo como query de retrieval | `respond.py:225 turn_queries()` appendea `service` crudo. #43 (`calefont`) dio `kb_miss`; #44 (`reparación de calefont`) respondió. El matcher de A5 está en `capture.py:396-450` (`_edit_distance_at_most_one`, `_matches_catalogue_phrase`, `_preventive_services`) y hay que extraerlo a un módulo compartido. **Decisión abierta**: `case.service` sin palabra de servicio (`calefont`) → ¿`Visita técnica`, o no steerear el retrieval? Lo primero es coherente con L10 fix 2 (la visita técnica es el default de reparación); lo segundo arriesga repetir el `kb_miss`. |
| **C2** | S2 | Mover `capture_evidence` al final, después de confirmar la cita | Hoy cuelga del último campo de captura (`capture.py`, `_ask_next`). Decisión abierta L5.3: si el cliente ya mandó una foto antes, ¿se pregunta igual? |
| **D1** | — | **Diagnosticado (L25).** No es producción: los escalamientos sin mensaje son del **harness** (`classified` tras un `outbound`, con inserts revertidos) y los 96 `inbound/failed` son filas de seed sin `wamid`. | Cerrado: la métrica del panel no está contaminada. El riesgo real es leer números del harness como comportamiento de cliente. |
| **D2** | — | **Diagnosticado (L25).** Producción: **10 `booked` vencidas** (la más vieja 34 días), **cero `completed` y cero `no_show`**. | Necesita decisión de producto: **quién** marca una visita como hecha. Escribe datos: unidad propia con autorización explícita. |
| **D3** | — | Anclar los helpers de `test_scheduling.py` y `test_chat_booking.py` a una hora fija del día objetivo | Pre-existente en `main`, no de este feature. Ver L19: falla cuando la suite corre después de ~22:00Z. No tocado acá por estar fuera de las superficies del feature. |

## 4. Decisiones del owner ya tomadas (no re-preguntar)

- **C1a**: consentimiento ya dado → **salto silencioso** al booking.
- **C1b**: datos de contacto guardados → **confirmación en un solo mensaje** ("Tengo X y Y, con correo Z.
  ¿Sigue todo igual o cambió algo?"), nunca reuso silencioso.
- **C1b vigencia**: **1 año**.
- Orden de trabajo aprobado: A → B → C3 → C4 → C1 → C2 → D.
- **Merge y limpieza autorizados** (L18), con el orden de la cadena: 738 → 740 → 741 → 743.

Decisiones todavía abiertas: **L5.3** (evidencia si ya mandó foto) y el mapeo de C4 de la sección 3.

## 5. Trampas verificadas (todas costaron tiempo real)

1. **Backticks en un mensaje de commit pasado por `-m`**: el shell los ejecuta y mutila el mensaje
   (pasó en `f6f088f2` con `_pending`). Regla: `git commit -F <archivo>`, siempre.
2. **`db/seed.sh` es idempotente y no pisa settings existentes.** Producción tiene
   `reply.texts.capture_ack` guardado como override explícito, así que un cambio de default en Python
   **no llega** a la base desplegada. Por eso A1 trae la migración `060`, que reescribe el valor **sólo
   si es exactamente el default viejo**. Cualquier cambio futuro de un default en `reply.texts` necesita
   el mismo paso de datos.
3. **`get_reply_texts` mergea por clave con los defaults**: agregar una clave nueva a `reply.texts` es
   seguro para producción. Pero `validate_reply_texts` exige que estén **todas** al guardar, y
   `REPLY_TEXT_SLOTS` es un vocabulario cerrado con test propio
   (`test_the_slot_vocabulary_is_closed`) que hay que actualizar al agregar slots.
4. **El tier unit no entra a `booking()`**: stubea la sesión. Para `booking`/`state`/`manage`, el test va
   en `tests/integration/` o no prueba nada.
5. **`customers` no tiene `updated_at`.** La vigencia de un año envejece contra `created_at`. Hacerlo
   exacto exige `customers.data_updated_at` y es cambio de shape surface.
6. **Cada worktree deriva su propio puerto de test DB** y necesita `infra/.env` copiado de
   `../lumat-agent/infra/.env`.
7. **`uv.lock` aparece modificado** en el worktree (lo escribe `uv sync` con la versión del paquete).
   No se commitea: es ruido. Se restaura con `git checkout -- uv.lock`.
8. **No hay force-push sin autorización.**
9. **El repo no usa issue-first ni template de PR** (verificado contra #732). Convención real de body:
   `## What / ## Why / ## Changes / ## Test plan / Risk:`.
10. **Una versión de migración pertenece a un solo archivo.** `059` ya era de
    `059_memory_user_scope.sql` cuando este feature traía `059_capture_ack_plain.sql`; dos archivos con
    la misma versión dejan uno sin aplicar para siempre (la versión se registra una vez en
    `schema_migrations`). Este feature quedó en **060**. Antes de crear una migración, mirar
    `git ls-tree origin/main db/migrations/`, no sólo el worktree.
11. **Renombrar una migración deja la test DB persistente mintiendo**: `schema_migrations` conserva el
    nombre viejo y `test_schema_migrations_records_version` falla. Se arregla reconstruyendo la base
    descartable: `bash infra/test-db.sh down && bash infra/test-db.sh up`.
12. **`full` después de ~22:00Z falla 4 tests que no son tuyos** (L19): los helpers anclan en
    `datetime.now(timezone.utc) + 2 days` y el bloque de slots cruza medianoche. Si te toca, corré el
    diferencial (revertir `app/chat/slot_window.py` a `origin/main`) antes de creer que rompiste algo.
13. **Un `full` interrumpido deja un `seed_dev.py` huérfano** que bloquea la test DB y hace colgar la
    corrida siguiente en `conftest.py:88` (`TRUNCATE`). `ps -eo pid,cmd | grep seed_dev` y matarlo.

14. **`graphify-out/` vive en el worktree, no en el repo.** Al recrear el worktree el gráfico se
    pierde, y el Graph Check que `AGENTS.md` exige es entonces un bloqueo legítimo para cualquier
    subagente. Copiarlo desde el worktree principal (`cp -a ../lumat-agent/graphify-out .`) alcanza
    mientras el commit sea el mismo; reconstruirlo con `graphify .` es el paso de cierre de sesión.
15. **No existe el evento `handoff:*`.** Ese texto es la columna **`cause`** de un evento `escalation`.
    Los nombres de evento son `classified`, `escalation`, `state_change`, `kb_retrieved`,
    `unknown_intent`, `kb_miss`. Buscar `event like 'handoff%'` devuelve vacío y hace creer que nunca
    hubo escalamientos.
16. **Filas de seed en `messages`: sin `wamid` y con microsegundos idénticos entre días** (`.839683`, a
    las 01:15 y 01:17). No son fallas de producción; no las cuentes como mensajes perdidos.
17. **Preguntá en qué base vive el hallazgo antes de perseguirlo.** D1 se documentó como problema de
    producción y estaba entero en el harness. Producción: 23 conversaciones / 309 mensajes. Harness:
    46 / 537.
18. **Dos suites DB en el mismo worktree se pisan.** Cada worktree deriva una sola test database y las
    corridas concurrentes chocan en el `TRUNCATE`; van de a una, siempre.

## 6. Verificación que se usó (repetir tal cual)

```bash
bash scripts/test.sh quick                                    # T0+T1, ~19 s, exit 0 en cada unidad
bash scripts/test.sh db tests/integration/<archivo>.py         # sólo los archivos que toca la unidad
bash scripts/test.sh shape origin/main                         # exit 3 => full obligatorio
bash scripts/test.sh full                                      # ~7-10 min, Postgres con pgvector
```

Estado medido en esta sesión: `test_migrations.py` → 39 passed; `quick` → exit 0; `shape` → exit 3
(migración nueva); `full` → 4 failed, los cuatro de L19 (pre-existentes, dependientes de la hora).
CI (`test` + `panel`) verde en las cuatro PRs sobre el árbol combinado.

## 7. Primer paso sugerido para el chat nuevo

1. Leer el doc del feature hasta `## Log`.
2. La cadena y #750 están mergeadas; no re-abrir S1–S14 salvo para verificar.
3. La próxima unidad es **D2**: el sweep de citas vencidas necesita primero una decisión de producto
   (quién marca `completed` / `no_show`) y después autorización explícita, porque escribe datos.
4. Si el catálogo de servicios crece con una entrada que no sea preventiva ni visita, revisar
   `canonical_service` (L24): hoy todo lo no preventivo colapsa a `Visita técnica`.
5. Follow-ups abiertos: **D3** (tests que dependen de la hora, trampa 12) y evaluar
   `customers.data_updated_at` para que la vigencia de un año sea exacta (trampa 5).
6. En el próximo deploy: `059` y `060` **ya están aplicadas** (producción en `060_capture_ack_plain`,
   verificado en esta sesión); no hace falta volver a mirar `capture_ack`.

