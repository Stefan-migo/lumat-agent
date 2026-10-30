# HANDOFF — chatbot-realismo-conversacional

**Estado al cerrar la sesión**: 4 PRs encadenadas abiertas, **las cuatro con CI verde**
(`test` + `panel`), nada mergeado, nada desplegado. Producción sigue en `v2026.10.11` (`046a1254`).
Trabajo en `/home/stefan/repos/lumat-agent-odd-chatbot-realismo-conversacional`, branch punta
`odd/chatbot-realismo-flujo` (`5ab5e171`).

**Regla de entrada**: leer `odd/tasks/chatbot-realismo-conversacional.md` (S1–S14 + Log L1–L17) antes de
proponer nada. Los specs citan los mensajes reales. No re-abrir lo cerrado; las decisiones ya tomadas
por el owner están en el Log y en este documento.

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
| A1 ack sin "Gracias" + migración `059_capture_ack_plain.sql` | S1 | `f7a6162b` | #738 ✅ |
| B1 franja "después del mediodía" / "después de las 12" | S8 | `0a7914cd` | #740 ✅ |
| B2 abreviaturas de mes (`3 de nov`) | S9 | `0a7914cd` | #740 ✅ |
| A2 cobertura sin precio ni promesa repetida | S5 | `04b993c9` | #741 ✅ |
| A3 despedida larga cierra | S6 | `63b890ec` | #741 ✅ |
| A4 consentimiento acepta "si autorizo" | S7 | `9c63dc20` | #741 ✅ |
| A5 "manutención" = preventivo (matcher de catálogo) | S4 | `a15e0edb` | #741 ✅ |
| C1a consentimiento ya dado → salto silencioso al booking | S3 | `faaed3dc` | #741 ✅ |
| B3 no re-ofertar la misma página / no resetear `attempts` | S10 | `4871dc62` | #741 ✅ |
| B4 `state.booking` sin citas pasadas | S11 | `0faf5c72` | #741 ✅ |
| B5 reagendar no se lee como respuesta de captura | S12 | `14c75a76` | #741 ✅ |
| C3 una pregunta por turno tras desviación de KB | S13 | `91318162` | #743 ✅ |
| C1b cliente conocido confirma su contacto en un mensaje (1 año) | S3 | `5ab5e171` | #743 ✅ |

Cadena de PRs (cada una con base en la anterior, merge al final):

```
main
 └── #738  odd/chatbot-realismo-ack              ack + spec + migración 059
      └── #740  odd/chatbot-realismo-agenda-window   franja + meses
           └── #741  odd/chatbot-realismo-conversacional   copy + consentimiento + preventivo + loop + state + manage
                └── #743  odd/chatbot-realismo-flujo        una pregunta por turno + contacto confirmado
```

## 3. Qué falta

| unidad | spec | qué hay que hacer | nota |
|---|---|---|---|
| **C4** | S14 | Normalizar `case.service` contra el catálogo **antes** de usarlo como query de retrieval | #43 (`calefont`) dio `kb_miss`; #44 (`reparación de calefont`) respondió. El matcher de A5 vive en `capture.py` y hay que sacarlo a un módulo compartido para no duplicar la tolerancia a typos. Es refactor + fix, unidad propia con RED. |
| **C2** | S2 | Mover `capture_evidence` al final, después de confirmar la cita | Hoy cuelga del último campo de captura (`capture.py`, `_ask_next`), así que cae junto a la pregunta de dirección. Decisión abierta L5.3: si el cliente ya mandó una foto antes, ¿se pregunta igual? |
| **D1** | — | Investigar escalamientos del 2026-10-28 12:04/14:09/16:52 con `conversation_events` pero **sin mensaje** en `messages`, incluso en conversaciones con cita confirmada (#40, #42) | Si es el runner de `conv_eval` reusando conversaciones, está contaminando la métrica de handoffs del panel. Huecos en `messages.id` (527–534, 576–586) compatibles con transacciones revertidas. |
| **D2** | — | Citas `booked` que nunca se cierran (producción #11 sigue `booked` para el 28/10) | Un sweep de higiene **escribe datos**: unidad propia, con autorización explícita. |

## 4. Decisiones del owner ya tomadas (no re-preguntar)

- **C1a**: consentimiento ya dado → **salto silencioso** al booking.
- **C1b**: datos de contacto guardados → **confirmación en un solo mensaje** ("Tengo X y Y, con correo Z.
  ¿Sigue todo igual o cambió algo?"), nunca reuso silencioso.
- **C1b vigencia**: **1 año**.
- Orden de trabajo aprobado: A → B → C3 → C4 → C1 → C2 → D.
- Push y PRs autorizados; **merge parkeado** por el owner ("el merge lo guardamos para despues").

Decisiones todavía abiertas: **L5.3** (evidencia si ya mandó foto) y, si se quiere precisión en la
vigencia, agregar `customers.data_updated_at` (ver trampa 5).

## 5. Trampas verificadas (todas costaron tiempo real)

1. **Backticks en un mensaje de commit pasado por `-m`**: el shell los ejecuta y mutila el mensaje
   (pasó en `f6f088f2` con `_pending`). Regla: `git commit -F <archivo>`, siempre.
2. **`db/seed.sh` es idempotente y no pisa settings existentes.** Producción tiene
   `reply.texts.capture_ack` guardado como override explícito, así que un cambio de default en Python
   **no llega** a la base desplegada. Por eso A1 trae la migración `059`, que reescribe el valor **sólo
   si es exactamente el default viejo**. Cualquier cambio futuro de un default en `reply.texts` necesita
   el mismo paso de datos.
3. **`get_reply_texts` mergea por clave con los defaults**: agregar una clave nueva a `reply.texts` es
   seguro para producción (el JSON guardado cae al default). Pero `validate_reply_texts` exige que
   estén **todas** al guardar, y `REPLY_TEXT_SLOTS` es un vocabulario cerrado con test propio
   (`test_the_slot_vocabulary_is_closed`) que hay que actualizar al agregar slots.
4. **El tier unit no entra a `booking()`**: stubea la sesión. Un `UnboundLocalError` de mi primer
   intento en B3 lo cazó el tier DB. Para `booking`/`state`/`manage`, el test va en
   `tests/integration/` o no prueba nada.
5. **`customers` no tiene `updated_at`.** La vigencia de un año envejece contra `created_at` (fecha de
   alta). La dirección del error es conservadora; hacerlo exacto exige `customers.data_updated_at` y es
   un cambio de shape surface.
6. **Cada worktree deriva su propio puerto de test DB** y necesita `infra/.env` copiado de
   `../lumat-agent/infra/.env`. Sin eso, `bash infra/test-db.sh up` se cae.
7. **`uv.lock` aparece modificado** en el worktree desde que se creó (venía así de `main`). No se
   commitea: es ruido, no parte de ninguna unidad.
8. **No hay force-push sin autorización.** El mensaje mutilado de `f6f088f2` quedó como defecto
   cosmético documentado (L16) en vez de reescribir historia.
9. **El repo no usa issue-first ni template de PR** (verificado contra #732). Convención real de body:
   `## What / ## Why / ## Changes / ## Test plan / Risk:`.

## 6. Verificación que se usó (repetir tal cual)

```bash
bash scripts/test.sh quick                                  # T0+T1, ~19 s, exit 0 en cada unidad
bash scripts/test.sh db tests/integration/<archivo>.py       # sólo los archivos que toca la unidad
bash scripts/test.sh full                                    # OBLIGATORIO al cerrar el feature
```

`full` **no se corrió todavía**: hay que correrlo antes de mergear el conjunto (es el gate de cierre
del feature, son ~7 min y necesita el Postgres con pgvector). También cambiaron superficies de forma
(`app/services/settings.py`, `agent/prompts` no, pero sí defaults de settings), así que
`bash scripts/test.sh shape origin/main` conviene mirarlo antes del merge.

## 7. Primer paso sugerido para el chat nuevo

1. Leer el doc del feature hasta `## Log`.
2. `gh pr view 738 740 741 743 --json number,title,checks` para ver si el CI sigue verde.
3. Atacar **C4** con RED: el mismo texto con `case.service` distinto tiene que dar el mismo retrieval.
   Antes de escribirlo, extraer el matcher de catálogo que hoy vive en `capture.py` a un módulo
   compartido (`app/chat/service_catalogue.py` o similar) — es el refactor que hace que A5 y C4 no
   dupliquen la tolerancia a typos.
4. **C2** después, con la decisión L5.3 cerrada.
5. **`full` + `shape` antes de mergear**, y el orden de merge es el de la cadena: 738 → 740 → 741 → 743.
6. Al desplegar: la migración `059` corre en el arranque de la api; verificar después que
   `reply.texts.capture_ack` quedó en `Entiendo. ` y que `capture_confirm_contact` aparece con su default.
