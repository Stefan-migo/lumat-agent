# LumatAgent — Checklist de activación de la WhatsApp Business API (Cloud API de Meta)

> Documento orientado al cliente, con partes técnicas para Stefan (HandCodeStudio)
> Fecha: 7 de agosto de 2026
> **Estatus: guía operativa; plazos y costos referenciales sujetos a las condiciones vigentes de Meta.**

---

## Introducción

La WhatsApp Business **Cloud API** de Meta es la vía oficial para que un sistema automatizado atienda y escriba mensajes por WhatsApp en nombre de Lumat. No es la app de WhatsApp Business del celular: es una API en la nube que se conecta al servidor donde corre LumatAgent.

**Qué se necesita:**
- Una cuenta de negocio en Meta (Business Suite / Facebook Business).
- Verificación de la empresa ante Meta.
- Un número de teléfono real y propio, con verificación por SMS o llamada.
- Una app de desarrollador de Meta configurada con la Cloud API (parte técnica, la hace Stefan).

**Cuánto puede tardar:** el proceso es burocrático y depende de la revisión de Meta. La cuenta y el número se crean en minutos, pero la **verificación de la empresa puede demorar semanas**. Por eso conviene iniciarlo apenas se firme el contrato y avanzar con un número prepago de pruebas mientras tanto.

---

## Sección A — Pasos que hace el cliente (Maximiliano)

> A cargo de Lumat. Stefan acompaña y guía, pero la cuenta y la documentación son del cliente.

1. **Preparar antes de empezar**:
   - Documentos de la empresa (nombre legal, RUT, dirección, rubro).
   - Un correo y un teléfono de contacto reales y accesibles.
   - Acceso al dominio `lumat.cl` (se usa para verificar la empresa) o documentación legal de la empresa si se verifica por documentos.
2. **Crear la cuenta de negocio en Meta Business Suite** (Facebook Business): `business.facebook.com`. Usar un perfil administrativo único de la empresa, no una cuenta personal de un empleado.
3. **Verificar la empresa**: Meta pide confirmar que Lumat es un negocio real. Dos vías: verificar el **dominio** (`lumat.cl`) o subir **documentación** de la empresa. La verificación desbloquea el nombre comercial visible y límites mayores.
4. **Registrar el número de teléfono**: el número real y propio donde Meta enviará un **SMS o llamada con un código de verificación**. Tener el teléfono a mano; la llamada viene de Meta y solo entrega el código (no es una llamada comercial). Si no se contesta, se puede usar el SMS.
5. **Configurar el nombre del negocio** tal como se mostrará a los clientes.
6. **Aceptar los términos** de la plataforma de WhatsApp Business.

**Errores comunes:**
- Usar una cuenta personal de WhatsApp ya activa en el número que se quiere registrar (ver Sección C).
- Número de teléfono con formato incompleto o que no recibe SMS/llamadas.
- No tener el teléfono disponible en el momento de la verificación.
- Confundir la cuenta personal con la cuenta de negocio en la configuración.

**Nota práctica:** el número debe ser **real, propio y con capacidad de recibir SMS o llamadas**. No se admiten códigos cortos.

---

## Sección B — Pasos que hace Stefan (parte técnica)

> A cargo de HandCodeStudio. Requiere que Lumat haya creado la cuenta de negocio (Sección A).

1. **Crear una app en Meta for Developers** (`developers.facebook.com`) asociada a la cuenta de negocio de Lumat.
2. **Configurar WhatsApp Cloud API**: vincular la Business Account (WABA), obtener el **Phone Number ID** y el **token** de acceso permanente.
3. **Configurar el webhook**: la URL del servidor (`https://agente.lumat.cl/webhook/whatsapp`) + un *verify token*. Cuando un cliente escribe, Meta hace push del mensaje a esa URL.
4. **Suscribirse a los eventos de mensajes** necesarios (`messages`).
5. **Configurar la verificación en dos pasos (PIN de 6 dígitos)** del número, apenas se registre (medida de seguridad de Meta).
6. **Preparar plantillas** (para mensajes fuera de la ventana de 24 h): recordatorios de visita, alertas de emergencia, resúmenes. Las de utilidad se aprueban rápido, a veces automáticamente.
7. **Persistir mensajes apenas llegan**: responder `200` al webhook de inmediato y guardar en la base de datos sin demoras; deduplicar por ID del mensaje (wamid) para tolerar reintentos de Meta.

**Número de prueba (test number) de Meta** vs **número de producción**:

| Aspecto | Test number (Meta) | Número real de producción |
|---------|--------------------|---------------------------|
| Origen | Lo asigna Meta con el WABA de prueba | Número telefónico propio de Lumat |
| ¿Puede ser un número ya usado? | No, es de Meta | Sí, si es de Lumat (borrando antes la cuenta de WhatsApp de ese número) |
| Mensajes | Gratuitos, solo a **5 números destinatarios** verificados | Reales, facturados por conversación |
| Plantillas | Pre-aprobadas de ejemplo | Requieren aprobación y verificación de negocio para escalar |
| Uso | Desarrollo y pruebas técnicas | Operación con clientes |

**Conclusión práctica:** el test number de Meta **no sirve para probar con clientes reales**. Para la fase de pruebas de Lumat se usa un **número prepago dedicado** (Sección C).

---

## Sección C — Uso del número de prueba (prepago dedicado)

**Recomendación acordada en la reunión:** validar primero el agente con un **número prepago dedicado** y migrar al número real de WhatsApp solo tras validar el funcionamiento.

**Hallazgos técnicos de la investigación (7 de agosto de 2026):**

- **El chip/SIM conserva sus funciones normales**: al registrar el número en la Cloud API, el número **sigue recibiendo y haciendo llamadas y SMS** por la red celular. Es útil como respaldo y para la verificación inicial.
- **La app de WhatsApp se apaga en ese número**: un número registrado en la Cloud API **no puede estar a la vez activo en la app de WhatsApp (normal o Business)**. Si el número principal de Max tiene WhatsApp personal/empresa, al migrarlo a la API **ese WhatsApp se apaga**.
- **Por eso se recomienda un número DEDICADO**: un SIM prepago nuevo, de bajo costo, usado solo por el agente. Evita interrumpir el WhatsApp personal de Max y permite que el chip siga tomando llamadas/SMS normales.
- El número de prueba de Meta (test number) **no puede ser un número que Lumat ya use**; es un número de Meta asignado para pruebas técnicas.

**Impacto en el plan:**

| Punto | Respuesta | Acción |
|-------|-----------|--------|
| El SIM sigue con llamadas/SMS normales | Sí, documentado | Mantener la SIM accesible durante el alta |
| La app de WhatsApp no puede usar el mismo número que la API | Correcto; hay que borrar la cuenta de WhatsApp de ese número primero | Usar SIM prepago dedicado para el agente |
| Verificación del número | SMS o llamada de Meta con código de un solo uso | Coordinar el momento del alta y configurar el PIN de 2 pasos |
| Test number vs. producción | El test number no sirve para clientes reales | Probar con el número prepago propio; migrar tras validar |

**Sobre el historial de conversaciones (mensajes borrados):**

- El agente **recibe y guarda cada mensaje en el momento en que llega**. Si un cliente borra un mensaje "para todos" después, ese borrado **no elimina la copia ya guardada** en el servidor de Lumat.
- La Cloud API **no tiene un evento de webhook de borrado**: llega un evento genérico (`unsupported`, error `131051`) que se dispara por múltiples causas, por lo que **no se puede detectar borrados de forma confiable**. Si se quiere marcar borrados, se registra como heurística, no como garantía.
- La retención del historial es **política de Lumat** (los datos viven en su servidor). Corresponde definir por cuánto tiempo se conservan las conversaciones y verificar la normativa chilena aplicable (p. ej. Ley 19.628) antes de comprometer almacenamiento indefinido.

---

## Sección D — Checklist de verificación final

| Ítem | Estado | Responsable | Fecha |
|------|--------|-------------|-------|
| Cuenta de negocio creada en Meta Business Suite | Pendiente | Lumat | |
| Empresa verificada (dominio o documentación) | Pendiente | Lumat | |
| Número de teléfono registrado y verificado (SMS/llamada) | Pendiente | Lumat + Stefan | |
| PIN de verificación en dos pasos configurado | Pendiente | Stefan | |
| App de desarrollador creada y asociada a la cuenta | Pendiente | Stefan | |
| Cloud API configurada (Business Account ID, Phone Number ID, token) | Pendiente | Stefan | |
| Webhook configurado y respondiendo `200` | Pendiente | Stefan | |
| Suscripción a eventos de mensajes activa | Pendiente | Stefan | |
| Plantillas de utilidad preparadas y aprobadas | Pendiente | Stefan + Lumat | |
| Número prepago dedicado comprado y disponible | Pendiente | Lumat | |
| Pruebas con número prepago validadas | Pendiente | Lumat + Stefan | |
| Migración al número real de WhatsApp | Pendiente | Stefan + Lumat | |

---

## Sección E — Costos referenciales de la API

> **Referencial y sujeto a las tarifas vigentes de Meta.** Se confirma al momento de activar la cuenta.

| Concepto | Costo referencial |
|----------|-------------------|
| Conversaciones iniciadas por el cliente (dentro de la ventana de 24 h) | Gratuitas |
| Mensajes de plantilla aprobados (fuera de la ventana de 24 h) | ~$0.04-0.08 USD por mensaje |
| Verificación de negocio (para desbloquear nombre visible y límites mayores) | Según tarifa vigente de Meta |
| Número prepago dedicado de pruebas (SIM) | Bajo; costo del plan prepago local |

**Nota:** la estructura de precios de Meta cambia por mercado y región (Chile). El valor real se obtiene en el panel de WhatsApp Manager al activar la cuenta. Con el volumen esperado de Lumat (decenas de conversaciones diarias, la mayoría dentro de la ventana de 24 h), el costo mensual de mensajería es bajo; el costo recurrente principal es el del VPS (~€5-15/mes, ver `02-requerimientos-servidor.md`).
