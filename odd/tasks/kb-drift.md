# ODD — coherencia de la KB con la configuración (kb-drift)

Worktree: `/home/stefan/repos/lumat-agent-odd-kb-drift` · rama `odd/kb-drift` · base `a443588c`
Origen: revisión read-only del harness (convs 37–42, main worktree). La conv 42 (Leorio) pidió sábado: el turno 544 respondió con RAG sobre una fila vieja de `kb_documents` ("los sábados se coordinan con un asesor") y el turno 551 ofreció sábado igual, porque el motor determinista obedece `technician_weekly_schedule` y no lee la KB. Al re-sembrar la KB del harness apareció un segundo defecto: `kb.update_document` escribe la versión nueva con `source_meta=None`, el ruteo por tema filtra por `source_meta["source_id"]` y el bot pasó a responder "No tengo ese dato" a las preguntas de horario.

## Specs

- **S1 — Actualizar un documento conserva su ruteo.** `kb.update_document()` debe escribir los chunks de la versión nueva con el `source_meta` del documento: un parámetro explícito cuando el llamador lo provee, y el `source_meta` de la versión activa (sin `chunk_index`) cuando no. Caso que debe quedar cubierto: un documento creado con `source_meta={"source": "docs/kb", "source_id": "lumat-cobertura-horarios"}` y actualizado después sigue siendo encontrado por `kb.retrieve(..., source_ids=["lumat-cobertura-horarios"])` y por `respond.retrieve_for_queries(topic_source_ids=...)`.
- **S2 — Editar desde el panel no rompe el ruteo.** `POST /panel/kb/{doc_id}/edit` conserva el ruteo del documento editado: tras editar, `source_meta["source_id"]` sigue presente en los chunks de la versión activa y la búsqueda acotada por tema devuelve resultados.
- **S3 — La siembra mantiene y repara el ruteo.** `scripts/seed_kb_docs.py --apply --force` pasa `source_meta={"source": "docs/kb", "source_id": <slug>}` en el camino de re-versión, y repara un documento cuyo contenido ya coincide pero cuya versión activa perdió `source_id` — sin re-embeddear ni subir de versión, dejando el `audit_log` correspondiente. El reporte (sin `--apply`) nombra los documentos sin ruteo.
- **S4 — Lint de valores duplicables.** Un control estático sobre `docs/kb/*.md` detecta las clases de valor que pertenecen a la configuración y no al texto: comunas de `coverage.communes`, rangos `HH:MM` y rangos de días (`hours.schedule`), cifras con `$` (`tarifa.precios`) y duraciones en minutos u horas (`booking.service_durations`). Los hallazgos vigentes se congelan en una línea base versionada; el control **falla** cuando un documento gana un hallazgo nuevo y reporta los que la línea base todavía tolera.
- **S5 — Procedimiento de ops.** `docs/ops.md` documenta que las KB de cliente salen de `docs/kb` (sembradas) y no se editan a mano en el panel, y agrega al checklist de release la verificación `seed_kb_docs.py` en modo reporte contra producción, que debe imprimir "consistente con docs/kb".

Fuera de alcance (decidido con el owner, no es este feature): migrar horarios/cobertura/duraciones a respuestas deterministas desde la configuración (E2), y alinear el motor de oferta con la ventana comercial para que un domingo nunca se ofrezca (E3). S4 deja esas duplicaciones enumeradas como deuda visible en la línea base.

## Tasks

| # | Tarea | Specs | Ruta | Commit |
|---|---|---|---|---|
| T1 | `kb.update_document` propaga `source_meta` (explícito o heredado) + tests de ruteo tras actualizar | S1 | inline (parent) | — |
| T2 | Endpoint de edición del panel conserva el ruteo + test funcional | S2 | inline (parent) | — |
| T3 | Seed pasa `source_meta` en re-versión, repara en el lugar y reporta documentos sin ruteo | S3 | inline (parent) | — |
| T4 | `scripts/kb_doc_drift.py` + línea base `docs/kb/drift-baseline.json` + tests | S4 | inline (parent) | — |
| T5 | `docs/ops.md`: origen de las KB y check de release | S5 | inline (parent) | — |
| T6 | Verificación de cierre: `quick`, focused por unidad, `full` + `shape` | S1–S5 | inline (parent) | — |

## Log

- **L1 (pedido original, verbatim):** "hey chat. necesito que revises las conversaciones que he tenido en el mainworktree atraves del harness. hay una en particular la de leorio. donde el cliente pregunta por una visita para el sabado. revisa esa y otras conversaciones. hay un error de coherencia en esa conversacion de leorio. dice que las visita los sabados se coordinan directamente con un asesor. Pero despues ofrece correctamente horarios de visitas para el sabado."
- **L2 (decisión de producto, verbatim):** "ok de aqui nace una pregunta. por que me doy cuenta que lo mismo puede pasar con los valores y/o cpbertura. actualmente tenemos en la kb explicando los horarios de atencion. pero luego en la config es posible configurar los horarios y extender los horarios que dice la kb. lo mismo pasa para cobertura. hay una kb que explica que comunas especificamente se cubren con atencion. sin embargo despues hay una config que permite modificar los valores de cobertura. y lo mismo pasa con precios. como deberia manejar esto? modificar la kb para que siempre respeten los valores de la configuracion? y no pasar valores en la kb? o algo asi pienso?" → direccion aceptada: la configuración es dueña de los valores; la KB se queda con la política. E2/E3 quedan fuera de este feature; S4 deja la deuda enumerada.
- **L3 (alcance, verbatim):** "Solo el cinturón: E1 + lint" — re-seed del harness, KB de producción y lint de deriva; sin tocar el camino de respuesta determinista.
- **L4 (evidencia, 2026-10-28):** al re-sembrar el harness, `kb_documents` id 1 pasó a v2 ("lunes a sábado", 2 chunks) y la consulta "puede ser este sabado?" devolvió `kb_miss_offer`. Causa: chunks de v2 con `source_meta={"chunk_index": 0}` contra v1 con `{"source": "docs/kb", "source_id": "lumat-cobertura-horarios", "chunk_index": 0}`; `app/services/kb.py:246` pasa `source_meta=None` y `app/services/kb.py:428` filtra por `source_meta["source_id"]`. `POST /panel/kb` nunca pasa `source_meta`, y los tests de ruteo solo ejercitan `ingest_document`.
- **L5 (decisión, verbatim):** "Worktree + doc ODD (recomendado)" — el bug de `source_meta` entra al feature; la KB de producción no se toca antes del fix.
