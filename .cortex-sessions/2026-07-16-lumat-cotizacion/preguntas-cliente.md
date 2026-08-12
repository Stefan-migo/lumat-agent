# Preguntas para Lumat

> Documento vivo para la cotización. Se va ampliando a medida que surgen nuevas preguntas durante el proceso de definición, desarrollo e implementación.
>
> **Objetivo**: Estrujar el LumatRequest.md al máximo para no dejar dudas sobre los requerimientos, dolores y expectativas del cliente antes de finalizar la cotización.

---

## 🧠 Contexto general y dolor del cliente

- [ ] **¿Por qué están buscando esto AHORA?** ¿Qué problema específico los llevó a pedir la cotización? (ej: están perdiendo clientes, colapsados de llamadas, quieren profesionalizarse, la competencia tiene bot)
- [ ] **¿Cómo atienden HOY?** ¿WhatsApp personal del dueño/técnico, llamadas, presencial? ¿Todo mezclado en un mismo número?
- [ ] **¿Cuántas consultas reciben por día? ¿Cuántas se pierden?** (estimar si pueden)
- [ ] **¿Cuántos clientes activos tienen aproximadamente?**
- [ ] **¿Cuántas personas trabajan en Lumat?** (dueño, técnicos, admin — esto define cuántos usuarios del sistema)
- [ ] **¿Cuál es el mayor miedo o riesgo que ven con este proyecto?** (bot falle, clientes no lo usen, costos escondidos, pérdida de control)
- [ ] **¿El dueño de Lumat es técnico en calefacción/calefont o más administrativo?** (define nivel de complejidad del CMS y qué puede editar él mismo)
- [ ] **¿Tienen claro que WhatsApp Business NO permite enviar mensajes no solicitados?** El bot puede responder, pero no iniciar conversaciones sin un template aprobado por Meta.

---

## Base de datos existente

- [ ] **¿Tienen actualmente una base de datos con clientes?** Si existe en format excel, bien ordenado.
- [ ] **Si existe:** utilizar esa base de datos
- [ ] **Si existe:** estan limpios. no tengo claro cuantos existen.

- [ ] **¿Manejan históricos de visitas, servicios realizados o garantías?** ¿Dónde están registrados hoy?
- [ ] **¿Tienen fichas o registros de equipos por cliente?** (marca, modelo, n° serie de calefont/caldera, etc.)

## RAG — Base de conocimiento del bot

*(La información que el bot usará para responder)*

### Formato y origen

- [ ] **¿En qué formato tienen hoy la información técnica?** (PDFs, Google Docs, Notion, páginas web, chats, hojas de cálculo, texto suelto, solo en la cabeza de los técnicos)
- [ ] **¿Existen documentados los procedimientos de diagnóstico?** (códigos de error por marca/modelo, pasos de troubleshooting, soluciones comunes)
- [ ] **¿Tienen un tarifario o lista de valores referenciales?** ¿Con qué frecuencia cambia?
- [ ] **¿Tienen escritas las preguntas frecuentes de venta y postventa?** En algún lado o hay que crearlas desde cero?

### Mantenimiento del contenido

- [ ] **¿Quién va a mantener actualizada la base de conocimiento?** ¿Una persona técnica que entienda los contenidos, o el dueño sin conocimientos técnicos?
- [ ] **¿Qué tan seguido cambian los contenidos?** (precios, servicios, cobertura, procedimientos)
- [ ] **¿Prefieren un panel simple para editar ellos mismos, o que el programador haga las actualizaciones?**

## Emergencias y derivación

- [ ] **¿Tienen definidos los criterios exactos de emergencia?** El doc menciona "olor a gas, fuga, humo, incendio, monóxido" — ¿hay más casos que quieran agregar o acotar?
- [ ] **¿Cómo se maneja la derivación hoy?** ¿WhatsApp grupal, un encargado por turno, un número específico?
- [ ] **¿Quién recibe las notificaciones de emergencia?** ¿Hay turnos? ¿Técnico de guardia?

## WhatsApp

- [ ] **¿Tienen ya un número de WhatsApp Business aprobado?** (el proceso de aprobación de Meta puede tomar días o semanas)
- [ ] **Si no:** ¿están al tanto de los requisitos de Meta? (número no registrado en WhatsApp, cuenta de negocio verificada, política de uso aceptable)
- [ ] **¿Usan hoy WhatsApp para atención al cliente?** Si es así, ¿cómo lo manejan? ¿cuántos mensajes por semana aproximadamente?

## Administración y panel

- [ ] **¿Quiénes serán los usuarios del panel?** ¿Solo el dueño, o también operadores/técnicos?
- [ ] **¿Necesitan roles diferenciados?** (admin que puede editar todo vs operador que solo ve casos y cambia estados)
- [ ] **¿Qué indicadores les gustaría ver en el panel?** (contactos recibidos, motivos, casos derivados, visitas agendadas — el doc ya lista algunos, pero siempre hay más)

## Milestone 3 — Agenda, pagos y integraciones

- [ ] **¿Usan actualmente Google Calendar u otro calendario para agendar visitas?**
- [ ] **¿Cómo asignan técnicos hoy?** (por zona, por especialidad, por disponibilidad)
- [ ] **¿Cuántos técnicos tienen actualmente? ¿Cuántos proyectan tener en 1 año?**
- [ ] **¿Tienen ya un medio de pago electrónico?** (transbank, mercadopago, flow, etc.)
- [ ] **¿Necesitan facturación electrónica o solo registro de pagos?**
- [ ] **¿La postventa/manejo de garantías lo hace el mismo equipo de técnicos o hay alguien específico?**

---

## Milestone 1 — Bot IA: Flujo conversacional

- [ ] **¿El flujo de atención (pasos 1→10) es estrictamente lineal o el cliente puede saltar entre pasos?** (ej: alguien dice "emergencia" en el paso 3, ¿salta al paso 8?)
- [ ] **¿Hay consultas que el bot puede resolver COMPLETAMENTE sin derivar a un humano?** (ej: horarios, valores referenciales, preguntas frecuentes) ¿O toda consulta eventualmente deriva?
- [ ] **"Continuidad automática"** (paso 7): ¿qué significa exactamente? ¿El bot agenda una visita automática sin humano de por medio?
- [ ] **¿La conversación tiene timeout?** (ej: si el cliente no responde en 30 min, ¿se cierra la sesión? ¿se guarda lo capturado?)
- [ ] **¿El cliente puede retomar una conversación después?** (ej: "hola, ayer estaba consultando por mi calefont...") ¿El bot reconoce el contexto anterior?
- [ ] **¿Cuánto tiempo se mantiene activa una sesión?** ¿Horas, días, hasta que se cierra explícitamente?

### Menú inicial

- [ ] **¿"Emergencia" debe ser una opción visible del menú, o el bot la detecta automáticamente por palabras clave y actúa aunque el cliente elija otra opción?**
- [ ] **¿Cada opción del menú tiene subcategorías?** Ej: Calefont → ¿diagnóstico, mantención, reparación, instalación? ¿O es todo en un mismo flujo?
- [ ] **"Consultar por un servicio o valor"**: ¿el bot puede dar precios EXACTOS o solo valores referenciales ("desde $XX")?
- [ ] **¿"Hablar con una persona" está disponible SIEMPRE en el menú, o solo después de cierto punto del flujo?**

### Captura de datos del cliente

- [ ] **¿Todos los datos de la tabla en 1.5 son obligatorios?** ¿Qué pasa si el cliente no quiere dar correo electrónico o dirección exacta?
- [ ] **¿Los datos se piden todos de una vez o progresivamente según el contexto?** (ej: primero identificación, después de saber el motivo se piden datos del equipo)
- [ ] **¿El consentimiento (aceptación para almacenar datos) es un "sí" textual del cliente o un mensaje que el bot muestra y asume aceptación si continúa?**
- [ ] **¿Hay límite de fotos/archivos por conversación?** ¿Tamaño máximo? ¿Formatos aceptados solo imágenes o también video?
- [ ] **¿Hay política de retención de datos?** (ej: guardar conversaciones por 6 meses, borrar después)

### Base de conocimiento

- [ ] **¿Los valores referenciales son precios fijos o rangos?** ¿Varían por comuna, por técnico, por tipo de servicio?
- [ ] **¿Tienen ya una base de códigos de error por marca/modelo, o la irán construyendo con el tiempo?**
- [ ] **¿Las preguntas frecuentes de venta y postventa existen escritas en algún lado (DOC, PDF, WhatsApp), o hay que crearlas desde cero?**
- [ ] **¿El contenido de la base de conocimiento es principalmente texto, o incluye tablas, diagramas, imágenes que el bot debe poder mostrar?**
- [ ] **¿Quién y con qué frecuencia va a actualizar la base de conocimiento?** (esto define si el método de actualización puede ser técnico o necesita ser ultra simple)

### Orientación técnica y responsabilidad

- [ ] **¿Tienen una lista de "verificaciones simples y seguras" ya definidas y aprobadas por ellos?** ¿O hay que ayudarlos a definirla?
- [ ] **¿Quién aprueba qué recomendaciones puede dar el bot?** ¿Hay un riesgo legal si el bot sugiere algo y el cliente se confía?
- [ ] **¿Tienen seguro o alguna protección ante eventuales problemas derivados de recomendaciones del bot?**

### Emergencias

- [ ] **¿"Notificar inmediatamente al equipo" significa WhatsApp, SMS, llamada telefónica, o todo a la vez?**
- [ ] **¿A quién se notifica?** ¿Dueño, técnico de guardia, grupo de WhatsApp? ¿Hay turnos?
- [ ] **¿Hay escalamiento si la primera persona no responde?** (ej: si no responde en 5 min, notificar al siguiente)
- [ ] **¿La detección es solo por palabras clave o también por contexto/semántica?** (ej: "huele raro" no tiene keywords exactas pero es potencial emergencia)
- [ ] **¿Hay distintos niveles de emergencia?** (ej: fuga de gas = crítica, ruido extraño = moderada)

### Derivación a humano

- [ ] **¿Hay horarios definidos de atención humana?** El bot funciona 24/7, ¿pero si derivan a las 2 AM, quién recibe?
- [ ] **¿Si derivan y nadie responde, qué pasa?** ¿Se agenda automático para el siguiente día hábil? ¿Se encola?
- [ ] **"Cliente molesto"** (criterio de derivación): ¿cómo detecta el bot eso? ¿Palabras clave, repeticiones, tono?
- [ ] **¿La transferencia es al mismo número de WhatsApp (cambia a humano) o a un número/grupo diferente?**

### Registro y fichas de cliente

- [ ] **Los 8 estados (nuevo, contactado, pendiente, agendado, en evaluación, finalizado, cancelado, postventa):** ¿el bot puede cambiar algunos automáticamente? ¿Cuáles son solo manuales?
- [ ] **¿"Postventa" como estado aplica desde M1 o es un placeholder para M3?**
- [ ] **¿Las notas internas las ve solo el equipo de Lumat o también el cliente?**

### Panel administrativo

- [ ] **¿Solo admin y operador como roles, o necesitan también "técnico" (que ve solo sus casos asignados)?**
- [ ] **"Edición de respuestas, reglas y contenidos autorizados":** ¿pueden editar el comportamiento del bot (reglas/flujo) o solo el contenido estático (textos, FAQ)?
- [ ] **¿Las notificaciones del panel son por email, por WhatsApp, o ambas?**
- [ ] **¿Los indicadores básicos quieren verlos como gráficos, como números, o tabla?**

### Requisitos de IA

- [ ] **"Registrar respuestas no resueltas":** ¿dónde se registran? ¿Un log interno, un panel visible, un email al admin?
- [ ] **Límites de consumo:** ¿quién define el tope mensual de gasto en OpenAI? ¿Qué pasa cuando se alcanza? (¿el bot deja de responder, o solo alerta?)

---

## Milestone 2 — Página Web

- [ ] **¿Tienen logo, colores corporativos, tipografía definida?** ¿O hay que diseñar la identidad visual desde cero?
- [ ] **¿Tienen fotografías reales de sus trabajos (instalaciones, equipos) o necesitan usar fotos de stock?**
- [ ] **¿Quién escribe los textos de cada sección de la web?** (inicio, servicios, cobertura, FAQ, etc.)
- [ ] **¿El bot IA en la web debe ser el mismo bot de WhatsApp pero en modo chat widget?** ¿O uno independiente?
- [ ] **El formulario de contacto web:** ¿debe integrarse con la misma base de datos del bot (cliente único) o son sistemas separados?
- [ ] **Si alguien llena el formulario web, ¿el bot debería poder retomar la conversación?** (ej: "Recibimos tu consulta por la web, ¿quieres continuar por WhatsApp?")
- [ ] **¿Qué tan simple necesita ser el CMS?** ¿Editar texto plano, markdown, WYSIWYG como WordPress? ¿Lo usará el dueño (posiblemente no técnico)?
- [ ] **¿Necesitan multi-idioma o solo español?**
- [ ] **¿Tienen ya dominio registrado?** ¿O hay que comprarlo?

---

## Milestone 3 — Catálogo, Agenda, Pagos

### Catálogo de servicios

- [ ] **¿Los precios se muestran públicamente en el catálogo, o son "consultar" / "desde $XX"?**
- [ ] **¿Los servicios tienen variantes?** (ej: mantención básica vs completa, con repuestos vs sin repuestos)
- [ ] **¿Cada servicio tiene un técnico especialista asignado o cualquiera puede realizarlo?**

### Agendamiento

- [ ] **¿Cuántos técnicos tienen HOY? ¿Cuántos proyectan tener en 1 año?** (define escalabilidad del motor de agenda)
- [ ] **¿Los técnicos tienen especialidades?** (gas, calefacción, electricidad, o todos hacen todo)
- [ ] **¿Cobertura geográfica: todos los técnicos cubren todas las comunas o hay zonas asignadas?**
- [ ] **¿Trabajan sábados, domingos, feriados?**
- [ ] **Google Calendar:** ¿cada técnico tiene su propio calendar o usan uno corporativo compartido?
- [ ] **Bloques de 1 hora:** ¿es estricto o hay servicios que requieren más/ menos tiempo?

### Pagos

- [ ] **¿Tienen ya cuenta con algún procesador de pagos?** (MercadoPago, Transbank, Flow, Khipu, otro)
- [ ] **¿Necesitan emitir boletas electrónicas (SII) ahora, o solo el registro de pago?**
- [ ] **¿Aceptan efectivo solo en persona o también necesitan registro de pago en efectivo en el sistema?**

### Emergencia (M3)

- [ ] **El botón de emergencia en la web: ¿es para cualquier visitante o solo para clientes con ficha?**
- [ ] **¿El botón llama automáticamente al número de emergencia o abre un modal con instrucciones + número?**

### Postventa

- [ ] **¿Quién gestiona la postventa y garantías?** ¿El mismo técnico que hizo el servicio, o alguien administrativo?
- [ ] **¿La solicitud de evaluación post-servicio es automática o manual?**

---

## Generales

- [ ] **¿Tienen dominio ya registrado?** ¿O hay que comprarlo?
- [ ] **¿Tienen las marcas/logos/colores definidos o hay que diseñar la identidad web?**
- [ ] **¿Hay alguna integración con la que ya cuenten y quieran mantener?** (contabilidad, SII, inventario, etc.)
- [ ] **¿Tienen algún contrato o acuerdo previo con algún proveedor que condicione las decisiones?** (ej: ya pagan OpenAI, ya tienen cuenta Meta Business)

---

> **Nota:** Este documento se actualiza a medida que surgen nuevas preguntas durante el proceso de cotización y desarrollo. Cada pregunta marcada como resuelta queda registrada con su respuesta en el historial del proyecto.
