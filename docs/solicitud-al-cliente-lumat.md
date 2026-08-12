# Solicitud de requerimientos y accesos — LumatAgent

> **Para:** Lumat (Maximiliano) · **De:** Desarrollo LumatAgent · **Fecha:** 12 de agosto de 2026
> **Contexto:** Contrato firmado y Pago 1 recibido. Kickoff oficial: lunes 17 de agosto de 2026.

---

## 1. Propósito de este documento

Para construir el asistente de WhatsApp de Lumat necesitamos que la empresa prepare
y nos entregue ciertos accesos, datos y contenidos. Cuanto antes lleguen, antes
terminamos: **el trámite de Meta es el único paso que depende de ustedes y que puede
tardar semanas**.

Este documento lista exactamente qué necesitamos, para qué, y para cuándo.

---

## 2. Lo que necesitamos de Lumat

### 2.1. Meta (WhatsApp Business API) — URGENTE

Este es el bloque crítico. Sin esto, el bot no puede conectarse a WhatsApp.

| # | Requerimiento | ¿Para qué? | ¿Cómo lo hacemos? |
|---|---|---|---|
| 1 | **Cuenta de negocio en Meta** (Facebook Business Manager) creada o verificada | Es el contenedor de todo lo demás | Ustedes crean la cuenta o nos dan acceso como desarrollador a la existente |
| 2 | **Número de teléfono dedicado** para el bot | Es el número desde el que responderá LumatAgent en WhatsApp | Idealmente un número nuevo que no use otra persona |
| 3 | **Suscripción a WhatsApp Business API** (WhatsApp Business Platform) | Habilita el envío/recepción de mensajes programáticos | Se vincula a la cuenta de negocio; el costo de uso es por mensaje según tarifas de Meta |
| 4 | **Verificación de negocio** de Meta | Requisito para usar la API de forma estable y mensajes de plantilla | Documentación de la empresa; los guiamos paso a paso |
| 5 | **Token de acceso permanente** y PIN de 2 pasos | Credenciales que usa el servidor para hablar con WhatsApp | Ustedes lo generan, nosotros lo instalamos de forma segura en el servidor |
| 6 | **Número de prueba** (test number) | Verificar el flujo completo antes de mover el número real | Se configura desde el panel de desarrollador de Meta |
| 7 | **Dominio o subdominio** para el webhook (ej. `agente.lumat.cl`) | Meta necesita una URL HTTPS pública donde entregar los mensajes | Nosotros coordinamos el DNS; ustedes confirman el dominio |
| 8 | **Aprobación de plantilla** `emergency_alert` | Enviar alertas de emergencia (gas, incendio, etc.) aunque el cliente no haya escrito primero | Nosotros la redactamos y la enviamos; Meta la aprueba |

> ⚠️ **Por qué es urgente:** la revisión de la verificación de negocio y la aprobación
> de plantillas puede tomar días o semanas en Meta. Nuestro primer hito intermedio
> (servidor + webhook vivo) está fijado para el **24 de agosto** y depende de este bloque.

### 2.2. Base de conocimiento del negocio

Para que el bot responda con información real y confiable (no inventada), necesitamos
los documentos con el conocimiento de Lumat:

| # | Contenido | Formato preferido |
|---|---|---|
| 1 | **Catálogo de servicios**: qué servicios ofrecen y descripción de cada uno | PDF, Word o texto |
| 2 | **Tarifas y precios** vigentes (si no son públicos, nos indican qué responder y qué derivar) | PDF, Excel o texto |
| 3 | **Cobertura geográfica**: comunas/zonas donde trabajan | texto |
| 4 | **Garantías y condiciones** de los trabajos | PDF o texto |
| 5 | **Procedimientos típicos**: cómo se toma un trabajo, plazos, qué se necesita del cliente | PDF o texto |
| 6 | **Preguntas frecuentes** (si tienen o quieren que las redactemos juntos) | texto |
| 7 | **Protocolos de emergencia**: qué hacer ante gas, incendio, fugas, etc. | texto (si tienen) |

> Si no tienen estos documentos formalizados, no es problema: hacemos una sesión
> de captura de conocimiento (una entrevista guiada) y nosotros redactamos la base.
> Solo necesitamos que alguien con el conocimiento del negocio nos dedique 1–2 horas.

### 2.3. Datos operativos

| Dato | Uso |
|---|---|
| Horarios de atención | El bot responde "estamos fuera de horario" o deriva correctamente |
| Contactos de emergencia (teléfonos) | Alerta de emergencia si el cliente no responde |
| Nombre/identidad con la que responde el bot | Tono y presentación |
| Persona encargada de revisar las derivaciones a humano | Quién recibe los avisos del panel |

### 2.4. Decisiones de marca y tono

- Nombre visible y presentación del asistente (ej. "Asistente Lumat").
- Tono: formal / cercano / técnico.
- Mensajes estándar que quieran que el bot use (saludo, despedida, fuera de horario).
- (Opcional) Logo para el panel de administración.

---

## 3. Qué NO necesitamos de ustedes

- **No necesitan escribir código ni configurar servidores** — lo hacemos nosotros.
- **No necesitan comprar licencias de software** adicionales.
- **No necesitan conocimientos técnicos** — solo entregar accesos y datos.
- Los costos de Meta (mensajes, verificación) se facturan según lo acordado en el contrato.

---

## 4. Formato y plazos de entrega

| Bloque | Fecha deseada | Notas |
|---|---|---|
| 2.1 Meta (al menos ítems 1, 2, 6) | **Lo antes posible** — idealmente antes del 17 de agosto | Puede ser en paralelo con todo lo demás |
| 2.2 Base de conocimiento | Antes del **24 de agosto** | Si falta, coordinamos la sesión de captura |
| 2.3 Datos operativos | Antes del **31 de agosto** | |
| 2.4 Decisiones de marca | Antes del **31 de agosto** | Se puede ajustar después sin problema |

---

## 5. Próximo paso

Agendar 30 minutos en la semana del **17 de agosto** para:

1. Guiarlos en la configuración de Meta (cuenta, verificación, token).
2. Resolver dudas sobre los puntos de este documento.
3. Agendar la sesión de captura de conocimiento si no hay documentos.

Cualquier duda, respondemos por este mismo canal.

---

*Documento entregado como parte del hito 1 del proyecto LumatAgent. Los accesos y datos
solicitados se manejan de forma confidencial y se usan exclusivamente para el sistema.*
