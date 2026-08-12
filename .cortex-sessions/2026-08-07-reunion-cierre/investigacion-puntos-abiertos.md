# Investigación — Puntos abiertos WhatsApp Business API

**Fecha:** 7 de agosto de 2026
**Propósito:** Resolver los dos puntos técnicos abiertos tras la reunión de cierre con el cliente Lumat (gasfitería, Chile): (1) qué sucede con las llamadas telefónicas y la app de WhatsApp al migrar un número a la WhatsApp Business Platform (Cloud API), y (2) qué pasa con el contenido de mensajes que el usuario borra después de enviarlos. El objetivo es entregar a Stefan información verificable para definir el plan de activación del número del agente IA y qué puede prometer al cliente sobre el historial de conversaciones.

**Nota metodológica:** developers.facebook.com bloquea el acceso automatizado (HTTP 400). Todo el contenido oficial se leyó a través de capturas de Wayback Machine de las páginas oficiales de Meta (URLs originales indicadas en cada fuente). Lo marcado como "experiencia de terceros" no está documentado oficialmente.

---

## 1. Llamadas telefónicas al migrar el número

### Respuesta clara (resumen ejecutivo)

- **El chip/SIM conserva todas las funciones telefónicas normales.** Registrar el número en la Cloud API no afecta la red celular: el número sigue recibiendo y haciendo llamadas y SMS. Está documentado: *"Registered numbers can still be used for everyday purposes, such as calling and text messages."*
- **La app de WhatsApp (normal o Business) deja de poder usar ese número.** Los números ya activos en WhatsApp Messenger o WhatsApp Business **no pueden registrarse** en la plataforma salvo que se borre antes la cuenta de WhatsApp de ese número; y una vez migrado, el número ya no se puede usar en la app.
- La verificación de propiedad la hace Meta con un **SMS o llamada de voz con un código de un solo uso**; es una verificación automática de la plataforma, no se mezcla con llamadas del negocio.
- El **número de prueba (test number)** lo asigna Meta y es de Meta: **no puede ser un número que el cliente ya use**. Para mensajes reales se necesita un número de producción propio y dedicado.
- Conclusión: se necesita un número **dedicado al agente**; no es obligatorio un SIM nuevo, pero si el número está en una cuenta de WhatsApp personal, esa cuenta debe borrarse o el número debe cambiarse de SIM.

### Detalle técnico

**Verificación y registro del número** (documentado en *Business Phone Numbers*):

- Requisitos para registrar: (a) que el número te pertenezca, (b) que tenga código de país y área (no se admiten códigos cortos), (c) que pueda **recibir llamadas de voz o SMS** porque Meta envía un mensaje para verificar la propiedad.
- Proceso: durante el alta (App Dashboard → WhatsApp → API Setup → Add a phone number), Meta envía un **SMS o un mensaje de voz con el código de verificación**. Ese código se ingresa para confirmar que el número es del negocio.
- Después del alta conviene (y la plataforma lo exige como medida de seguridad) configurar la **verificación en dos pasos (PIN de 6 dígitos)** para el número, vía WhatsApp Manager o por API (`/PHONE_NUMBER_ID/two_step`).
- La llamada de verificación proviene de WhatsApp/Meta y solo entrega el código; no es una llamada comercial ni se puede confundir con una llamada del negocio. Si el cliente no está atento, puede no responderla: siempre existe la opción SMS como alternativa.

**App de WhatsApp vs. Cloud API** (documentado):

- *"Numbers already in use with the WhatsApp Messenger app or WhatsApp Business app cannot be registered unless they are deleted first."* → El mismo número **no puede estar a la vez** en la app y en la Cloud API. Para registrar el número hay que borrar antes la cuenta de WhatsApp asociada (FAQ oficial: "How to delete your account").
- *"Webhooks set up will not affect the phone number on your WhatsApp Business App. Only after you migrate your number over to the WhatsApp Business Platform can you no longer use that number on your WhatsApp Business App."* → La configuración de webhooks por sí sola no toca la app; el conflicto aparece **al migrar/registrar** el número en la plataforma.
- *"Business phone numbers can only be registered for use with one API at a time: Cloud API or On-Premises API."* → Un número registrado queda vinculado a una sola API.

**Número dedicado y límites** (documentado):

- El WABA (WhatsApp Business Account) requiere un *valid, dedicated business phone number*.
- El portfolio de negocio inicia con hasta **2 números registrados** (se puede ampliar hasta 20 tras verificación de negocio).
- Número en uso para mensajes pagos: no se puede eliminar hasta 30 días después del último mensaje pago.

**Test number vs. número de producción** (documentado en *Get Started*):

| Aspecto | Test number | Número real de producción |
|---|---|---|
| Origen | Lo crea y asigna Meta automáticamente con el WABA de prueba | Número telefónico propio del negocio |
| ¿Puede ser un número que el cliente ya usa? | **No**: es un número de Meta, no el del cliente | Sí, si el cliente lo posee (borrando antes la cuenta de WhatsApp de ese número) |
| Mensajes | Gratuitos, a hasta **5 números destinatarios** verificados | Reales, facturados por conversación |
| Plantillas | Pre-aprobadas (p. ej. `hello_world`) | Requieren aprobación y verificación de negocio para escalar |
| Uso | Desarrollo y pruebas | Operación con clientes |

### Recomendación práctica para el caso Lumat

1. **Coincide con lo acordado en la reunión**: validar primero con un número prepago de pruebas y migrar al número principal solo tras validar el agente. El "test number" de Meta es insuficiente para probar con clientes reales; usar en su lugar un **número prepago dedicado** del cliente para la fase de prueba con la Cloud API.
2. **Comunicar al cliente el impacto sobre su WhatsApp actual**: si el número principal está en una cuenta de WhatsApp personal/empresa del dueño, al registrarlo en la Cloud API **se apaga el WhatsApp en ese número**. Recomendar un **número dedicado nuevo (SIM prepago)** para el agente, evitando interrumpir el WhatsApp personal de Max y permitiendo que el chip siga tomando llamadas/SMS normales (útil como respaldo y para la verificación inicial).
3. **Durante el alta**: avisar al cliente que le llegará un SMS o llamada de Meta con el código de verificación; tener la SIM en un teléfono accesible. Configurar el **PIN de verificación en dos pasos** inmediatamente.
4. Considerar el costo de la **verificación de negocio** de Meta para desbloquear el nombre comercial visible y escalar límites, aunque no es requisito para arrancar en modo individual.

### Fuentes

- Cloud API — Business Phone Numbers: <https://developers.facebook.com/docs/whatsapp/cloud-api/phone-numbers> (captura 2024-12-13)
- Cloud API — Get Started: <https://developers.facebook.com/docs/whatsapp/cloud-api/get-started> (captura 2025-01-05)
- Cloud API — Webhooks Setup: <https://developers.facebook.com/docs/whatsapp/cloud-api/guides/set-up-webhooks> (captura 2024-12-26)
- WhatsApp Business Platform — About the Platform: <https://developers.facebook.com/docs/whatsapp/overview> (captura 2025-01-16)
- Cloud API — Two-Step Verification: <https://developers.facebook.com/docs/whatsapp/cloud-api/reference/two-step-verification>
- WhatsApp FAQ — How to delete your account: <https://faq.whatsapp.com/2138577903196467/>

---

## 2. Mensajes borrados

### Respuesta clara (resumen ejecutivo)

- **Sí, el negocio ya tiene el contenido antes de que el usuario lo borre.** El webhook entrega el contenido completo del mensaje en tiempo real cuando llega. El borrado "para todos" posterior es un evento de cliente que **no elimina la copia ya entregada y almacenada** por el negocio.
- **La Cloud API no tiene un evento de webhook de borrado** (no existe `message_delete` ni `revoke`). Está documentado: *"the Cloud API does not support webhook status updates for deleted messages"*. Al borrar un mensaje, el negocio recibe un webhook con tipo `unsupported` y error `131051`, **ambiguo** (otros comportamientos generan el mismo error).
- La documentación no obliga al negocio a purgar mensajes ya recibidos; la retención documentada por Meta aplica a la **media** (30 días). El historial propio es responsabilidad del negocio, sujeto a los términos de datos de la plataforma y a la ley aplicable.
- Existe un caso límite no documentado oficialmente (experiencia de terceros): si el usuario borra "para todos" **antes** de que Meta complete el envío al webhook, el contenido puede no llegar o llegar vacío.
- El borrado "solo para mí" (delete for me) no afecta la entrega: el destinatario (el negocio) recibe el mensaje completo con normalidad.

### Detalle técnico

**Entrega en tiempo real** (documentado en *Webhook Notification Payload Examples*):

- Los mensajes entrantes llegan como `messages[].type: "text"` con `text.body` (contenido completo), `id` (wamid), `from`, `timestamp`. La plataforma hace push al webhook apenas se recibe el mensaje.
- Para media (imagen/video/documento), Meta descarga la media y notifica cuando está disponible, con `media_id` para descargarla.

**Evento de borrado en el webhook** (documentado):

- Sección "Status: Message Deleted" de la documentación oficial: *"Currently, the Cloud API does not support webhook status updates for deleted messages. If a user deletes a message, you will receive a webhook with an error code for an unsupported message type."* Payload: `messages[]` con `type: "unsupported"` y `errors: [{ "code": 131051, "details": "Message type is not currently supported" }]`. La propia documentación aclara: *"Note that there are other user behaviors that can trigger this same error message."*
- **No existe** en Cloud API un evento tipo `message_delete` / `revoke` como el de otras plataformas de mensajería. No hay forma confiable de detectar un borrado desde el webhook.

**Retención y almacenamiento**:

- Media: Meta almacena la media en la Cloud API **30 días** (salvo borrado manual) y las URLs de descarga expiran a los 5 minutos (*Media reference*).
- Mensajes de texto: Meta no documenta una política que obligue al negocio a eliminar lo ya recibido; la copia queda del lado del negocio una vez entregada. Esto es una **derivación del comportamiento documentado** (push en tiempo real + ausencia de evento de borrado) y de la experiencia de desarrolladores en la práctica; **no hay una declaración oficial explícita** tipo "el negocio puede conservar mensajes borrados". La conservación está sujeta a los términos de procesamiento de datos de la Business Platform y a la normativa local (en Chile, considerar Ley 19.628 y normativa de telecomunicaciones aplicable).

**Casos en los que el contenido puede NO llegar al webhook**:

- **Borrado "para todos" ultrarrápido** (el usuario borra antes de que Meta complete el push): no documentado oficialmente; la experiencia de terceros sugiere que el contenido puede no entregarse o llegar como `unsupported` sin `body`. Caso de carrera improbable pero posible.
- **Mensajes que desaparecen (disappearing)**: no soportados por Cloud API; el negocio recibe `type: "unknown"`/`unsupported` con error `131051` y Meta notifica al emisor (documentado).
- **Tipos de mensaje no soportados**: mismo webhook `unsupported`/`131051` (documentado).
- **Endpoint caído**: Meta reintenta hasta **7 días** con frecuencia decreciente; si el endpoint nunca responde 200, el mensaje se pierde. Los reintentos pueden generar **duplicados** (documentado en *Webhooks Setup*).
- **"Delete for me"**: borra solo en el dispositivo del emisor; el destinatario recibe el mensaje normalmente (no es una excepción de entrega).

**Implicación práctica**: el sistema del negocio recibe cada mensaje al llegar y lo persiste; el borrado posterior del usuario no lo elimina del historial propio, porque (a) el push ya ocurrió con contenido y (b) no existe un evento de borrado que pueda "deshacer" lo entregado.

### Recomendación práctica (qué puede prometer Stefan al cliente)

1. **Se puede prometer**: "el agente recibe y guarda cada mensaje en el momento en que llega; si un cliente borra un mensaje después, ese borrado no lo elimina de nuestro historial del servidor." Es correcto salvo el caso límite del borrado ultrarrápido antes de la entrega (no garantizable).
2. **Persistir apenas llega**: procesar el webhook con respuesta `200` inmediata y persistir en base de datos sin demoras, minimizando la ventana de carrera del borrado ultrarrápido y tolerando reintentos/duplicados (deduplicar por `id` wamid).
3. **No depender del webhook `unsupported`/131051** para detectar borrados: es ambiguo y se dispara por múltiples causas. Si se quiere "marcar" borrados, se puede registrar el evento, pero documentarlo al cliente como heurística, no como garantía.
4. **Avisar sobre retención**: documentar en el contrato que la retención de conversaciones es política del negocio (dato del cliente en su servidor), y verificar cumplimiento normativo local (Chile) antes de comprometer el almacenamiento indefinido.

### Fuentes

- Cloud API — Webhook Notification Payload Examples (sección "Status: Message Deleted"): <https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples> (captura 2025-01-15)
- Cloud API — Webhooks Setup (reintentos y duplicados): <https://developers.facebook.com/docs/whatsapp/cloud-api/guides/set-up-webhooks> (captura 2024-12-26)
- Cloud API — Media (retención 30 días): <https://developers.facebook.com/docs/whatsapp/cloud-api/reference/media> (captura 2024-12-01)
- Graph API — Webhooks Reference: WhatsApp Business Account (campos `messages`, `security`, etc.): <https://developers.facebook.com/docs/graph-api/webhooks/reference/whatsapp-business-account/> (captura 2025-02-28)
- Cloud API — Error codes (131051): <https://developers.facebook.com/docs/whatsapp/cloud-api/support/error-codes>
- WhatsApp Business Platform — About the Platform: <https://developers.facebook.com/docs/whatsapp/overview> (captura 2025-01-16)

---

## 3. Resumen de implicaciones para el proyecto

| Punto | Respuesta | Impacto en el plan | Acción |
|---|---|---|---|
| El SIM sigue recibiendo llamadas/SMS normales | Sí, documentado | Bajo: el chip sigue siendo un número celular normal | Informar al cliente; mantener SIM accesible durante el alta |
| La app de WhatsApp no puede usar el mismo número que la Cloud API | No puede; hay que borrar la cuenta de WhatsApp del número primero | Medio: si el número principal tiene WhatsApp personal, se apaga al migrar | Recomendar número dedicado (SIM prepago) para el agente |
| Verificación del número | SMS o llamada de Meta con código de un solo uso | Bajo: proceso de 5-10 min, requiere atender el teléfono | Coordinar con el cliente el momento del alta y el PIN de 2 pasos |
| Test number vs. producción | Test number es de Meta y no sirve para clientes reales; producción exige número propio dedicado | Bajo: la fase de pruebas con clientes usa número prepago propio | Arrancar con número prepago; migrar al principal tras validación |
| El negocio ya recibió el mensaje antes del borrado | Sí: push en tiempo real con contenido completo | Bajo: el historial propio persiste pese al borrado "para todos" | Persistir en el momento; deduplicar por wamid |
| Webhook de borrado | No existe `message_delete`/`revoke`; llega `unsupported` + error 131051 (ambiguo) | Medio: no se puede detectar borrados de forma confiable | No comprometer detección de borrados; documentarlo como heurística |
| Retención de datos | Meta retiene media 30 días; el historial del negocio es responsabilidad propia | Medio: implicación legal/privacidad (Chile) | Definir política de retención y verificar Ley 19.628 |
| Endpoint caído | Reintentos hasta 7 días; posibles duplicados | Bajo (operación normal) | Asegurar disponibilidad del webhook y deduplicación |

---

## 4. Referencias completas

**Documentación oficial de Meta** (accedida vía Wayback Machine por bloqueo de acceso automatizado):

1. Cloud API — Business Phone Numbers: <https://developers.facebook.com/docs/whatsapp/cloud-api/phone-numbers>
2. Cloud API — Get Started: <https://developers.facebook.com/docs/whatsapp/cloud-api/get-started>
3. Cloud API — Webhooks Setup: <https://developers.facebook.com/docs/whatsapp/cloud-api/guides/set-up-webhooks>
4. Cloud API — Webhook Notification Payload Examples: <https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples>
5. Cloud API — Media: <https://developers.facebook.com/docs/whatsapp/cloud-api/reference/media>
6. Cloud API — Two-Step Verification: <https://developers.facebook.com/docs/whatsapp/cloud-api/reference/two-step-verification>
7. Cloud API — Error codes: <https://developers.facebook.com/docs/whatsapp/cloud-api/support/error-codes>
8. Graph API — Webhooks Reference: WhatsApp Business Account: <https://developers.facebook.com/docs/graph-api/webhooks/reference/whatsapp-business-account/>
9. WhatsApp Business Platform — About the Platform: <https://developers.facebook.com/docs/whatsapp/overview>
10. WhatsApp Business Management API: <https://developers.facebook.com/docs/whatsapp/business-management-api/>
11. WhatsApp FAQ — How to delete your account: <https://faq.whatsapp.com/2138577903196467/>

**Otras fuentes consultadas:**

- Wayback Machine (Internet Archive) — utilizada para leer las páginas oficiales anteriores: <https://web.archive.org/>
- Stack Overflow / foros de la comunidad Meta — se buscó evidencia de terceros sobre borrado ultrarrápido y detección de borrados; no se hallaron respuestas canónicas con enlaces oficiales adicionales, por lo que ese punto se marca como experiencia no documentada.
