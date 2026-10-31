# pre-release-polish

Arreglos chicos de cara al próximo release: pulido del menú de proyecto del sidebar, borrado real de
artefactos (botón + tool del asistente), y borrado real de usuarios. Tres unidades independientes,
todas contra `main` (`244483d0`).

## Specs

**S1 — Menú proyecto cerrado: sólo el nombre.**
El estado cerrado del selector de proyecto no muestra el `ChevronDown` (no es un dropdown, es la
entrada a la sección), ni el badge `activo`, ni la descripción del proyecto. Queda el ícono de carpeta
y el nombre. El `ChevronRight` del encabezado de sección (que sí expande) se mantiene.

**S2 — Menú proyecto abierto: descripción + badge chico, sin leyenda "queda fijo".**
Cuando el hilo está iniciado (proyecto fijo), se elimina la leyenda "El proyecto queda fijo desde el
primer mensaje". En su lugar van la descripción (`purpose`) del proyecto y el badge de estado en una
variante más pequeña (hoy es demasiado grande).

**S3 — Botón de borrar artefacto en el panel (hard delete).**
Cada artefacto del hilo gana una acción "Eliminar" con diálogo de confirmación. Elimina **todas** las
versiones de esa raíz (filas + blobs en disco), de forma irreversible. La referencia en un mensaje que
apuntaba a ese artefacto queda como texto literal (mismo comportamiento que un archivo ya inexistente).

**S4 — Tool `artifact.delete` para el asistente.**
Herramienta `artifact.delete` con argumento `{artifact_id: int}`. Borra todas las versiones de esa
raíz, acotada a artefactos del asistente en el hilo del owner (igual que `artifact.update`). Falla
cerrada con `"no accessible chat thread for artifacts"` si el hilo no es del owner y `"artifact not
found"` si el id no pertenece al hilo. Es autónoma como `artifact.save`/`artifact.update` porque sólo
alcanza artefactos que el asistente produjo en el hilo que ya posee. Devuelve `{artifact_id, root_id,
filename, versions_deleted, deleted: true}`.

**S5 — Borrado real de usuarios: desvincular y borrar lo personal (decisión del owner 2026-10-31).**
`DELETE /users/{id}` borra el usuario de verdad. Semántica:
1. Guardas: no se puede borrar a sí mismo (403) ni al último admin activo (409).
2. Si el usuario tiene turnos en `booked` como técnico, **bloquea** con 409
   `"reassign the user's appointments before deleting"`.
3. **Desvincular** (anular las referencias que admiten nulo, para que el historial de negocio
   sobreviva): `projects.owner_id`, `project_aliases.owner_id`, `conversations.responsible_id`,
   `messages.author_id`, `cases.responsible_id`, `memories.owner_id`, `settings.updated_by`,
   `panel_secrets.updated_by`, `notification_operations.user_id`, y — tras la migración —
   `appointments.technician_id` (turnos históricos) y `project_files.owner_id`.
4. **Borrar lo personal**: `internal_chat_threads` (cascada a mensajes/adjuntos/artefactos y sus blobs),
   `technician_availability`, `technician_weekly_schedule`, `panel_notifications`,
   `push_subscriptions`.
5. Borrar la fila del usuario. Auditoría `user.delete` con `before`.

**S6 — Migración 062: dos referencias pasan a nullable.**
`appointments.technician_id` y `project_files.owner_id` dejan de ser `NOT NULL` para poder desvincular
sin perder el registro (el turno/archivo sobrevive, pierde la atribución al usuario borrado). Aditiva
y reversible; ninguna fila se borra en la migración.

## Tasks

| ID | Specs | Route | Commit |
|---|---|---|---|
| T1 | S1, S2 | inline | pulido del menú de proyecto + tests de frontend |
| T2 | S3, S4 | inline | `artifact.delete`: servicio + endpoint + tool + superficies declaradas + tests |
| T3 | S3 | inline | botón "Eliminar" en el panel con confirmación + tests |
| T4 | S5, S6 | inline | migración 062 + servicio `delete_user` + endpoint + tests |
| T5 | todas | inline | verificación de cierre: `shape` + `full`, frontend `build` + `test`, RDD |

## Log

**L1 — pedido del owner (2026-10-31, textual):** *"Menu proyecto (cerrado): ... hay un arrow down.
pero ese no es realmente un dropdown. hay que eliminar esa arrow down. tambien borrar el badge activo y
la descripcion del proyecto. Menu proyecto (abierto): ... sacar la leyenda que explica que el proyecto
queda fijo. y agregar aqui si la descripcion del proyecto. y quizas el badge activo pero mas peque;o es
muy grande actualmente. Menu Artefactos del proyeco. esta ok. pero le falta el boton para borrar
artefactos en caso de que fuera necesario. tambien una tool para que el asistenta tambien pueda
hacerlo. otra cosa ... en la seccion usuarios. cuando intento eliminar un usuario me aparece este
error ... el cual no me permite eliminar el usuario. y yo necesito que se pueda eliminar realmente el
usuario."*

**L2 — decisiones del owner (2026-10-31, tres preguntas del arranque):** borrado de usuario =
desvincular y borrar lo personal (bloquea si hay turnos `booked`); borrado de artefacto = hard delete
de todas las versiones; trabajo en worktree nuevo desde `main`.

**L3 — evidencia medida (2026-10-31):** `ContextProjectPicker`
(`web/src/components/pages/AssistantWorkspace.tsx:758`) en modo `static` (cerrado) muestra
`ChevronDown` + badge + `purpose`; en modo `locked` (abierto) muestra la leyenda "El proyecto queda
fijo desde el primer mensaje." sin badge ni descripción. El borrado de usuario choca contra 16 FKs a
`users.id` (todas sin `ondelete`): ver `app/models.py` y `db/migrations/*.sql`. `DELETE /users/{id}`
(`app/panel/api/routes/users.py:244`) captura `IntegrityError` y devuelve 409 "user is referenced by
other records; deactivate instead". `appointments.technician_id` y `project_files.owner_id` son `NOT
NULL`. Los hilos del asistente y sus hijos (`internal_chat_messages`, `assistant_attachments`,
`assistant_artifacts`) tienen `ondelete="CASCADE"` en `thread_id`. No hay endpoint ni tool de borrado
de artefactos (sólo download). `AUTONOMOUS_WRITE_ALLOWLIST` ya incluye `artifact.save`/`artifact.update`.
