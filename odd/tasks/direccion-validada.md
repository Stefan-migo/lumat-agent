# Validación de la dirección antes de guardarla

Rama `odd/direccion-validada` · worktree `../lumat-agent-odd-direccion-validada`

Hoy el bot pregunta «¿Cuál es tu dirección?» y guarda lo que llegue: `capture.py:484` acepta
cualquier texto que no repita un mensaje anterior. Una dirección inventada viaja al panel, a la
visita del técnico y a un viaje perdido. El validador la rechaza antes de escribirla, contra el
**callejero oficial de Chile**, offline y sin costo.

Riesgo: **item 1** (migración `068` + escritura de datos del cliente) e **item 3** (la ficha del
cliente cambia de forma y el panel la consume). Verificación independiente obligatoria.

## Specs

- **S1 — Nada se guarda sin validar.** La dirección que el cliente da en el chat pasa por el validador **antes** de escribirse en `customer.direccion`. Toda escritura lleva su resultado.
- **S2 — Offline y gratis.** La referencia es el **Maestro de Calles / Ejes Viales con numeración** del INE e IDE Chile (licencia CC BY 4.0), filtrado a `coverage.communes` y versionado como extracto con su archivo de atribución. **Sin API paga, sin geocoder de terceros y sin ninguna llamada de red en el camino de captura.** Un geocoder que se cae no puede bloquear a un cliente.
- **S3 — Estructura (L1).** Un validador determinista exige tipo de vía (`calle`, `avenida`, `pasaje`, `camino`, `ruta` y sus abreviaturas), nombre y número. «mi casa», «por ahí», «asdf» y cualquier texto sin esos elementos **no son una dirección**.
- **S4 — Callejero (L2).** Sobre la comuna ya capturada y validada por lista cerrada (`coverage.communes`): si la calle existe en esa comuna y el número cae dentro de un rango oficial → `validada`; si la calle existe y el número queda fuera de todos los rangos → `dudosa`; si la calle no aparece en esa comuna → `no_encontrada`. La comparación de nombres es accent-insensitive con corrección de typos acotada, y respeta la paridad del rango.
- **S5 — Nunca un rechazo duro.** `dudosa` y `no_encontrada` reformulan la pregunta una vez; a la segunda ofrecen el pin de ubicación de WhatsApp, y si el cliente insiste se guarda igual con su estado. La dirección del error manda: un falso rechazo bloquea a un cliente real que quiere pagar; una dirección inventada cuesta un viaje.
- **S6 — Resultado persistido.** La ficha del cliente guarda `direccion_estado` (`validada|dudosa|no_encontrada|cliente`), `direccion_fuente` (`callejero|pin|cliente`), `direccion_lat` y `direccion_lon` (nullable), y la API del panel los expone. La superficie visual del panel **no** entra en esta unidad.
- **S7 — El cliente no repite lo que ya dio.** La revalidación no puede romper la oferta de contacto guardado (`capture_confirm_contact`): una dirección `validada` de menos de un año se sigue ofreciendo tal cual.
- **S8 — Fuera de alcance.** Geocoders pagos (Google) y online (Nominatim/Photon) en el camino de captura; el parsing de mensajes `location` de WhatsApp (Fase 2, `MessageType.LOCATION` + su propia migración); y la ubicación predial verificada: la interpolación da la calle y el rango, **no** el domicilio exacto.

## Tasks

| ID | Qué | Specs | Ruta | Commit |
|---|---|---|---|---|
| T1 | Migración `068_customer_address_validation.sql` + campos en `Customer` (item 1, commit propio) | S6 | worker | `feat(db): store the address validation outcome on the customer` |
| T2 | `scripts/build_callejero.py`: fuente oficial → extracto filtrado a `coverage.communes` + `ATTRIBUTION.md` | S2 | worker | `data(geo): vendor the official Chilean street master extract` |
| T3 | `app/services/callejero.py`: índice, normalización, fuzzy acotado, chequeo de rango con paridad, interpolación | S4 | worker | junto a T2 |
| T4 | `app/services/address_validation.py`: validador puro, sin DB, sin red | S3, S4, S5 | worker | junto a T2 |
| T5 | Integración en `app/chat/nodes/capture.py`: validar antes de guardar, reformular una vez, ofrecer el pin a la segunda | S1, S5, S7 | worker | `feat(chat): validate the address against the street master` |
| T6 | Exportar el resultado en `app/panel/api/routes/clients.py` + textos de respuesta y su documentación | S5, S6 | worker | junto a T5 |
| T7 | Verificación independiente del corte (items 1 y 3) | todas | verifier | — |

## Log

**L1 (pedido del owner, verbatim):**

> Ademas me gustaria mejorar una logica en cuanto a la direccion. cuando el chatbot consulta por la direccion, deberia evaluar si esta direccion es correcta. es posible hacer eso? actualmente el chatbot solo acepta la direccion, esta puede ser ficticia y no llevar a ninguna direccion real. es posible que el chatbot verifique la direccion antes de guardarla?

**L2 (decisión del owner, verbatim):**

> ninguna me convence 100%. existe alguna otra opcion opensource para que el agente pueda verificar la direccion en concreto. lo del pin de whatsapp esta bueno. pero para verificar la direccion completa? alguna forma de hacerlo sin pagar?

Decisión 2026-11-16: se resuelve con el **callejero oficial de Chile** (INE/IDE Chile, CC BY 4.0) offline — valida calle + número, sin costo y sin terceros. El pin de WhatsApp queda aprobado como fallback de ambigüedad y como Fase 2 para el parsing del mensaje `location`.

**L3 (orden de trabajo, verbatim):**

> En paralelo, dos worktrees
