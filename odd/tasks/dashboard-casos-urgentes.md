# Dashboard — card de Casos urgentes

Frente 1 de los tres frentes de frontend pedidos por el owner (los otros dos, `conversaciones-multimedia` y
`configuracion-reorganizada`, se abren como features propias en su propio worktree, en ese orden).
El alcance es la card "Urgentes" del dashboard: cuenta y ruido hoy, y el drill-down que no lleva a ninguna parte.

## Specs

- **S1** — "muestra un monton de casos urgentes ... es solo ruido": la card "Urgentes" cuenta solo lo
  accionable, es decir casos **abiertos** cuya emergencia no fue reconocida (`acknowledged_at IS NULL`).
  Un caso reconocido deja de contarse; un caso cerrado/cancelado nunca cuenta.
- **S2** — "cuando clickeo en ellos no aparece nada no esta bien cableado lo de los casos": cada fila abre
  su destino real, no una lista genérica. Con conversación vinculada abre
  `/panel/app/conversations/<conversation_id>`; sin conversación abre la ficha del cliente en la pestaña
  de casos `/panel/app/clients/<customer_id>?tab=cases`.
- **S3** — "Cada fila abre su conversación o ficha del caso; la card muestra solo emergencias sin
  reconocer, tope 3": la lista muestra como máximo 3 filas y el número de la card sigue siendo el total
  real de urgentes pendientes.
- **S4** — comportamiento previo que se conserva: un caso cerrado no aparece en `urgent_cases`
  (`tests/functional/test_api_cases.py::test_closed_case_is_excluded_from_dashboard_urgent_cases`).

## Tasks

| ID | Spec | Route | Commit |
| --- | --- | --- | --- |
| T1 | S1, S4 | inline (backend: query + serializer) | `feat(dashboard): count only unacknowledged urgent cases` |
| T2 | S2, S3 | inline (frontend: Dashboard + AppShell wiring) | `feat(dashboard): open the real conversation or client case from urgent rows` |
| T3 | S1-S4 | inline (verificación: quick + full + frontend gate) | `docs(dashboard): record the urgent-cases evidence` |

## Log

**L1 — pedido original del owner (verbatim)**

> hey chat necesito trabajar con el frontend del proyecto. 
>
> vamos a ir con 3 frentes pricnipalmente.
>
> - dashboard algo muy sencillo. la card de casos. no cumple conlos casos.o sea muestra un monton de casos urgentes. pero cuando clickeo en ellos no aparece nada no esta bien cableado lo de los casos. necesitamos mejorarlo ya que es solo ruido
> - conversaciones (aqui tenemos que hacer implementaciones para mejorar el funcionamiento del chat), cuando lo toma un humano. el chat debe tener todas las funcionalidades de un chat de whatsapp. enviar y recibir multimedia principalmente. 
> - el ultimo frente es la seccion configuracion. hubo una implementacion de mas configuracion. sobre todo del chatbot. por ende  necesito reorganizar toda esa configuracion es mucho.

**L2 — decisiones del owner (respuestas al cuestionario, verbatim)**

- Orden: "Dashboard → Conversaciones → Configuración" — "Arrancamos por el más chico y ya diagnosticado; un worktree ODD por frente."
- Casos: "Cablear + filtrar ruido" — "Cada fila abre su conversación o ficha del caso; la card muestra solo emergencias sin reconocer, tope 3."
- Conversaciones: "Todo (imagen, doc, audio, video)" — "Incluye grabar y reproducir audio. Es el slice más grande y de más riesgo."
- Configuración: "esto es workunit especifico. creo que reorganizar es el camino. pero si hay duplicados necesitamos limpiarlo tambien"

**L3 — evidencia del diagnóstico (read-only, antes de escribir código)**

- `app/services/dashboard.py:113-122` — la query de `urgent` filtra `case_is_open_expr()` y
  `(escalated_at IS NOT NULL | emergency)`, sin mirar `acknowledged_at`: un caso ya reconocido sigue
  contando como urgente, y basta `escalated_at` para entrar aunque `emergency` sea falso. De ahí el ruido (S1).
- `app/panel/api/serializers.py:350-358` — `to_today_case_dict` no expone `conversation_id` ni
  `customer_id`, así que la fila no tiene a dónde navegar.
- `web/src/components/pages/Dashboard.tsx:191-202` — las filas de "Urgentes" hacen
  `navigate("cases")`, y `navigate` en `web/src/components/domain/AppShell.tsx:109-115` traduce `cases` a
  `conversations?tab=case`; ese tab filtra `has_case` + `exclude_closed`, un conjunto distinto del de la
  card (puede estar vacío: caso sin conversación, o conversación cerrada). De ahí "no aparece nada" (S2).
- `GET /panel/api/cases` existe (`app/panel/api/routes/cases.py:62`) pero la card no lo usa; el owner eligió
  no crear una página de casos nueva, así que la navegación por fila es la solución (S2).
