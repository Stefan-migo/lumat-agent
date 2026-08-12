**LUMAT**

**PLAN DE MILESTONES PARA COTIZACIÓN**

Bot IA · Página Web · Servicios e Integraciones

Documento de alcance funcional para que el programador pueda preparar una propuesta técnica y económica separada por etapa, con costos iniciales, costos mensuales, plazos, entregables y exclusiones.

# **1\. Objetivo del documento**

Definir con precisión los tres milestones principales del proyecto digital de Lumat, de manera que el programador pueda cotizar cada etapa por separado y proponer la arquitectura técnica más adecuada.

La prioridad inmediata es el Milestone 1: Bot IA de atención al cliente. Los Milestones 2 y 3 deberán quedar considerados desde el diseño inicial para evitar rehacer integraciones en el futuro.

# **2\. Alcance general del proyecto**

* Milestone 1: Bot IA de atención al cliente, captura de datos, orientación inicial, derivación y administración.  
* Milestone 2: Página web Lumat con presentación de servicios, contacto, formularios y conexión con el bot.  
* Milestone 3: Catálogo de servicios, agendamiento, base de clientes, pagos y automatizaciones operativas.

# **3\. Requisitos generales para la cotización**

* Valor neto y valor total de cada milestone.  
* Plazo de desarrollo y fecha estimada de entrega.  
* Costos únicos de implementación.  
* Costos mensuales de servidor, licencias, IA, WhatsApp, mantenimiento y soporte.  
* Costos variables por uso, conversación, mensaje, almacenamiento o transacción.  
* Tecnologías, plataformas y proveedores propuestos.  
* Funciones incluidas, funciones opcionales y exclusiones.  
* Condiciones de garantía, soporte y corrección de errores.  
* Propiedad del código, cuentas, datos, dominio, número de WhatsApp y accesos.  
* Condiciones de migración y continuidad si termina la relación con el proveedor.

# **MILESTONE 1 — BOT IA DE ATENCIÓN AL CLIENTE**

## **1.1 Objetivo**

Implementar un bot de inteligencia artificial para atender a clientes de Lumat, responder consultas frecuentes, recopilar antecedentes, clasificar solicitudes, detectar riesgos, registrar cada caso y derivar oportunamente a una persona.

## **1.2 Canal de operación**

La propuesta debe considerar dos etapas técnicas:

* Ambiente de prueba: bot accesible mediante enlace o canal de prueba para revisión de Lumat.  
* Canal productivo: conexión con WhatsApp Business Platform o solución equivalente aprobada por Lumat.

El programador debe indicar expresamente qué solución de WhatsApp utilizará, qué proveedor interviene, qué costos cobra Meta o el proveedor y qué requisitos de aprobación existen.

## **1.3 Flujo principal de atención**

1. Saludo e identificación como asistente virtual de Lumat.  
2. Presentación de las categorías de atención.  
3. Identificación del motivo de contacto.  
4. Solicitud progresiva de datos del cliente y antecedentes técnicos.  
5. Entrega de orientación inicial basada en la información disponible.  
6. Clasificación del caso por servicio, prioridad y estado.  
7. Propuesta de derivación, solicitud de visita o continuidad automática.  
8. Registro de la conversación y creación o actualización de la ficha del cliente.  
9. Generación de un resumen para el administrador o técnico.  
10. Cierre con confirmación de recepción y siguientes pasos.

## **1.4 Menú inicial requerido**

* Calefont.  
* Caldera.  
* Sistema de calefacción.  
* Solicitar visita técnica.  
* Consultar por un servicio o valor.  
* Postventa o garantía.  
* Emergencia.  
* Hablar con una persona.

## **1.5 Datos que debe recopilar**

| Categoría | Datos requeridos |
| :---- | :---- |
| **Identificación** | Nombre completo, teléfono/WhatsApp y correo electrónico. |
| **Ubicación** | Comuna y dirección del servicio. |
| **Equipo** | Tipo de equipo, marca, modelo y antigüedad aproximada si el cliente la conoce. |
| **Falla** | Descripción del problema, código de error, momento en que ocurre y frecuencia. |
| **Evidencia** | Fotografías, videos o audio cuando corresponda. |
| **Disponibilidad** | Días y horarios preferentes para una visita. |
| **Consentimiento** | Aceptación para almacenar los datos y utilizar la información con fines de atención. |

## **1.6 Base de conocimiento inicial**

El bot debe trabajar con una base de conocimiento administrable y ampliable. Lumat entregará la información validada y el programador deberá habilitar un método simple para actualizarla sin modificar el código.

* Información institucional y comercial de Lumat.  
* Servicios disponibles y comunas de cobertura.  
* Horarios de atención y canales de contacto.  
* Valores referenciales o reglas para indicar cuándo se requiere cotización.  
* Formas de pago, garantías y política de cancelación.  
* Preguntas frecuentes de venta y postventa.  
* Problemas frecuentes de calefont, calderas y calefacción.  
* Códigos de error por marca y modelo que Lumat vaya incorporando.  
* Procedimientos de derivación y criterios de emergencia.

## **1.7 Orientación técnica permitida**

El bot podrá realizar preguntas de diagnóstico preliminar y entregar recomendaciones básicas de bajo riesgo. No podrá confirmar diagnósticos definitivos, indicar intervenciones peligrosas ni reemplazar la revisión de un técnico.

* Preguntar si el equipo enciende, si muestra un código y si el problema afecta calefacción, agua caliente o ambos.  
* Solicitar fotografías de la pantalla, manómetro o instalación visible.  
* Recomendar verificaciones simples y seguras previamente aprobadas por Lumat.  
* Indicar cuando la información no es suficiente y se requiere visita técnica.  
* Mostrar una advertencia de seguridad cuando corresponda.

## **1.8 Detección de emergencias**

El bot debe detectar palabras o expresiones relacionadas con olor a gas, fuga, humo, incendio, chispa, explosión, monóxido, intoxicación, riesgo eléctrico o filtración severa.

Ante una emergencia, el bot debe interrumpir el flujo comercial, entregar instrucciones de seguridad previamente aprobadas por Lumat, recomendar contacto con servicios de emergencia o distribuidora de gas y notificar inmediatamente al equipo.

## **1.9 Derivación a atención humana**

* Cuando el cliente solicite hablar con una persona.  
* Cuando el bot no comprenda la consulta después de dos intentos.  
* Cuando exista una emergencia o riesgo para personas o instalaciones.  
* Cuando se trate de un reclamo, garantía o cliente molesto.  
* Cuando se necesite presupuesto personalizado.  
* Cuando la información técnica sea insuficiente o contradictoria.  
* Cuando el caso requiera revisar fotografías o videos con criterio técnico.

La transferencia debe incluir el historial y un resumen para que el cliente no tenga que repetir toda la información.

## **1.10 Registro y ficha del cliente**

* Crear una ficha automática al primer contacto.  
* Reconocer clientes existentes por número de teléfono.  
* Guardar datos personales, conversaciones, archivos y solicitudes.  
* Evitar registros duplicados.  
* Permitir agregar notas internas.  
* Registrar fecha, hora, canal y responsable.  
* Mantener estados: nuevo, contactado, pendiente, agendado, en evaluación, finalizado, cancelado y postventa.

## **1.11 Panel de administración**

* Inicio de sesión para usuarios autorizados.  
* Listado y búsqueda de clientes.  
* Visualización de conversaciones y archivos.  
* Bandeja de casos pendientes y derivados.  
* Cambio de estado y asignación de responsable.  
* Edición de respuestas, reglas y contenidos autorizados.  
* Exportación de clientes y solicitudes en Excel o CSV.  
* Indicadores básicos: contactos recibidos, motivos, casos derivados y solicitudes de visita.  
* Roles y permisos diferenciados para administrador y operador.

## **1.12 Requisitos de inteligencia artificial**

* Responder únicamente utilizando la información autorizada por Lumat.  
* Reconocer cuando no dispone de una respuesta confiable.  
* Evitar inventar precios, diagnósticos, garantías o disponibilidad.  
* Registrar las respuestas no resueltas para mejorar la base de conocimiento.  
* Permitir ajustar el tono, mensajes y reglas del bot.  
* Incluir límites de consumo y alertas de costo.  
* Indicar el modelo o proveedor de IA propuesto y sus costos.

## **1.13 Entregables del Milestone 1**

* Diseño y documentación del flujo conversacional.  
* Bot funcional en ambiente de prueba.  
* Conexión al canal productivo aprobado.  
* Base de conocimiento inicial cargada.  
* Captura estructurada de datos y archivos.  
* Detección de emergencia y derivación humana.  
* Ficha de clientes y registro de conversaciones.  
* Panel administrativo.  
* Exportación de información.  
* Pruebas funcionales y corrección de errores.  
* Manual de uso y capacitación.  
* Entrega de cuentas, accesos y documentación técnica.

## **1.14 Criterios de aceptación**

* El bot responde correctamente a los flujos acordados.  
* Los datos quedan registrados sin duplicaciones evidentes.  
* Las conversaciones pueden ser derivadas a una persona.  
* Las emergencias activan el protocolo definido.  
* El administrador puede revisar clientes, conversaciones y estados.  
* La información puede exportarse.  
* Lumat puede actualizar contenidos mediante el mecanismo acordado.  
* Los costos de operación son visibles y controlables.  
* Las cuentas y datos quedan bajo control de Lumat.

# **MILESTONE 2 — PÁGINA WEB LUMAT**

## **2.1 Objetivo**

Crear una página web simple, profesional, rápida y adaptable a celulares, orientada a explicar los servicios, generar contactos y conectar al cliente con el Bot IA, WhatsApp y la futura agenda.

## **2.2 Secciones mínimas**

* Inicio con propuesta de valor y llamados a la acción.  
* Presentación de Lumat.  
* Servicios principales: calefont, calderas y calefacción.  
* Cobertura geográfica.  
* Preguntas frecuentes.  
* Formulario de contacto.  
* Información de contacto.  
* Botón flotante de WhatsApp.  
* Botón de llamada.  
* Acceso visible al Bot IA.  
* Política de privacidad y tratamiento de datos.

## **2.3 Formulario de contacto**

* Nombre.  
* Teléfono/WhatsApp.  
* Correo.  
* Comuna.  
* Dirección.  
* Servicio requerido.  
* Descripción del problema.  
* Carga de fotografías.  
* Autorización para tratamiento de datos.

## **2.4 Requisitos técnicos**

* Diseño responsive para computador, tablet y celular.  
* Carga rápida y optimización básica.  
* Dominio y certificado SSL.  
* Integración con correo y WhatsApp.  
* Integración con el Bot IA.  
* Panel o sistema simple para editar textos, imágenes y servicios.  
* Configuración básica para buscadores.  
* Medidas de seguridad, respaldo y recuperación.  
* Analítica básica de visitas y conversiones.

## **2.5 Entregables del Milestone 2**

* Diseño aprobado por Lumat.  
* Página web publicada en el dominio definido.  
* Versión móvil y escritorio.  
* Formulario funcional.  
* Botones de WhatsApp y llamada.  
* Bot IA integrado.  
* Configuración de dominio, SSL y analítica.  
* Panel de edición o procedimiento documentado para cambios.  
* Pruebas y capacitación.

## **2.6 Criterios de aceptación**

* La web funciona correctamente en dispositivos móviles y computadores.  
* Los formularios llegan al canal acordado y registran al cliente.  
* El Bot IA y WhatsApp son accesibles desde la página.  
* Los contenidos básicos pueden actualizarse.  
* La página cuenta con SSL y respaldo.  
* Lumat recibe todos los accesos administrativos.

# **MILESTONE 3 — SERVICIOS, AGENDAMIENTO E INTEGRACIONES**

## **3.1 Objetivo**

Completar la operación digital incorporando catálogo detallado de servicios, agenda de visitas, asignación de técnicos, base de clientes, pagos, postventa y automatizaciones.

## **3.2 Catálogo de servicios**

* Calefacción: reparación PEX, lavado de red, cambio de manifold, lavado de radiadores, puesta en marcha, cambio de radiadores, termostatos, electroválvulas, válvulas y detentores.  
* Calefont: diagnóstico, mantención, reparación, encendido, temperatura, presión, códigos de error y componentes.  
* Calderas: diagnóstico, mantención, reparación, presión, calefacción, agua sanitaria, códigos de error, limpieza y puesta en marcha.

Cada servicio debe incluir nombre, descripción breve, problemas que resuelve, recomendaciones, botón de contacto y opción de agendamiento.

## **3.3 Agendamiento**

* Calendario con bloques de una hora.  
* Disponibilidad por técnico.  
* Asignación de varios técnicos.  
* Prevención de reservas dobles.  
* Bloqueo manual de horarios.  
* Confirmación por WhatsApp y correo.  
* Reprogramación y cancelación.  
* Recordatorios automáticos.  
* Registro del servicio en la ficha del cliente.  
* Integración con Google Calendar.

## **3.4 Base de clientes**

* Ficha única por cliente.  
* Historial de contactos y visitas.  
* Equipos, direcciones y antecedentes técnicos.  
* Fotografías y documentos.  
* Presupuestos, pagos, garantías y postventa.  
* Estados y notas internas.  
* Búsqueda y exportación.

## **3.5 Pagos**

* Pago con tarjeta de débito y crédito.  
* Registro de transferencia.  
* Registro manual de efectivo.  
* Vinculación del pago con cliente y agendamiento.  
* Confirmación y comprobante.  
* Estado pendiente, pagado, anulado o reembolsado.  
* Panel de revisión de pagos.

## **3.6 Botón y protocolo de emergencia**

* Botón de llamada de emergencia visible en la página.  
* Mensaje de seguridad antes de realizar la llamada.  
* Registro de la solicitud cuando sea posible.  
* Aviso inmediato al responsable de Lumat.  
* Definición clara de horarios y alcance del servicio de emergencia.

## **3.7 Postventa y automatizaciones**

* Ingreso y seguimiento de reclamos o garantías.  
* Estados de postventa.  
* Avisos de nuevas solicitudes, reservas, cancelaciones, pagos y emergencias.  
* Recordatorios de visita.  
* Solicitud de evaluación después del servicio.  
* Resumen diario o semanal para administración.

## **3.8 Entregables del Milestone 3**

* Catálogo completo de servicios.  
* Agenda integrada con Google Calendar.  
* Asignación de técnicos.  
* Confirmaciones y recordatorios.  
* Base de clientes consolidada.  
* Integración de pagos.  
* Módulo de postventa.  
* Automatizaciones y notificaciones.  
* Panel administrativo ampliado.  
* Pruebas, manuales y capacitación.

## **3.9 Criterios de aceptación**

* El cliente puede seleccionar un servicio y solicitar o reservar una visita.  
* La reserva se refleja correctamente en el calendario del técnico.  
* No existen dobles reservas para un mismo técnico.  
* El cliente recibe confirmaciones y recordatorios.  
* Los pagos quedan asociados al cliente y al servicio.  
* La postventa puede registrarse y seguirse.  
* Los datos pueden exportarse y respaldarse.

# **4\. Propiedad, continuidad y seguridad**

La propuesta técnica debe responder expresamente los siguientes puntos:

* El dominio, número de WhatsApp, cuentas de Meta, Google, correo, IA y servidor deben quedar a nombre o bajo control de Lumat.  
* Lumat debe tener acceso administrativo a todas las plataformas.  
* La base de datos y los archivos de clientes son propiedad de Lumat.  
* Debe existir un procedimiento de exportación y respaldo completo.  
* Debe indicarse si se entrega el código fuente y documentación técnica.  
* Debe informarse si otro programador puede continuar el proyecto.  
* Debe explicarse qué ocurre si se deja de pagar el servidor o una licencia.  
* Debe indicarse el costo y procedimiento de migración.  
* Deben existir respaldos automáticos, control de acceso y recuperación ante fallas.  
* Debe describirse la forma de proteger datos personales y conversaciones.

# **5\. Formato solicitado para la propuesta económica**

| Campo | Información requerida |
| :---- | :---- |
| **Milestone** | Nombre y número de la etapa. |
| **Alcance** | Funciones y módulos incluidos. |
| **Exclusiones** | Elementos no considerados. |
| **Entregables** | Productos y accesos que se entregarán. |
| **Plazo** | Días o semanas de ejecución. |
| **Costo inicial** | Desarrollo, configuración e implementación. |
| **Costo mensual** | Servidor, soporte, licencias, IA y WhatsApp. |
| **Costo variable** | Mensajes, conversaciones, almacenamiento o transacciones. |
| **Garantía** | Periodo para corregir errores sin costo. |
| **Soporte** | Horario, canal y tiempos de respuesta. |
| **Propiedad** | Código, datos, cuentas y accesos. |
| **Dependencias** | Servicios de terceros necesarios. |

# **6\. Orden de implementación solicitado**

11. Milestone 1: Bot IA de atención al cliente.  
12. Milestone 2: Página web Lumat.  
13. Milestone 3: Servicios, agendamiento e integraciones.

# **7\. Solicitud final al programador**

Se solicita entregar una propuesta técnica y económica separada por los tres milestones descritos. El Milestone 1 deberá presentarse con el mayor nivel de precisión, ya que corresponde a la primera etapa que Lumat desea implementar.

La propuesta deberá diferenciar claramente el costo de desarrollo, implementación, licencias, servidor, inteligencia artificial, WhatsApp, soporte, mantención y consumo variable. También deberá indicar las exclusiones y los riesgos técnicos relevantes.