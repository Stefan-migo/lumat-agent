# Guía para configurar WhatsApp de LumatAgent

> **Para:** Maxi, Lumat
> **De:** Desarrollo LumatAgent

Esta guía explica qué debe preparar Lumat en Meta y qué información debe compartir
con Stefan/desarrollo. La configuración se hace primero con el número de prueba de
Meta. El número real se incorpora después de confirmar sus condiciones y el impacto
de desvincularlo de WhatsApp.

## Antes de comenzar

- Use una cuenta personal de Facebook con permisos administrativos sobre el negocio.
- Tenga disponibles los datos legales de Lumat y un teléfono o correo al que pueda
  acceder durante las verificaciones de Meta.
- No comparta contraseñas, tokens ni secretos por WhatsApp o correo electrónico. Para
  esos datos, acuerde con Stefan un canal seguro de transferencia o una sesión guiada.
- Si ya existe una estructura de negocio en Meta, no cree otra sin confirmarlo:
  primero hay que identificar el Meta Business Portfolio existente.

## Recorrido rápido

1. Crear o confirmar el Meta Business Portfolio de Lumat.
2. Crear o confirmar el acceso a Meta for Developers.
3. Crear una aplicación de tipo **Business**.
4. Agregar y configurar **WhatsApp Business Platform**.
5. Validar el webhook y el envío con el número de prueba.
6. Preparar el número real dedicado, si se confirma que puede migrarse.
7. Generar los identificadores y credenciales, y entregarlos por un canal seguro.
8. Configurar el webhook junto con Stefan/desarrollo.

## 1. Crear o confirmar el Meta Business Portfolio

Meta puede mostrar el nombre conocido **Business Manager** para esta estructura. La
denominación actual es **Meta Business Portfolio**.

1. Ingrese a [Meta Business](https://business.facebook.com/).
2. Revise si Lumat ya tiene un portfolio de negocio. Busque el nombre legal y la
   información comercial de la empresa.
3. Si ya existe, confirme quién tiene acceso de administrador y continúe con ese
   portfolio.
4. Si no existe, cree uno para Lumat desde el panel de configuración del negocio.
5. Complete la información solicitada por Meta y, cuando el panel lo permita, inicie
   la verificación del negocio.

La verificación puede ser necesaria para la operación estable y para determinadas
funciones, como las plantillas. El estado debe revisarse en el panel de Meta; no
asumimos una fecha de aprobación.

## 2. Crear la cuenta de Meta for Developers

1. Ingrese a [Meta for Developers](https://developers.facebook.com/).
2. Inicie sesión con la cuenta que administra el portfolio de Lumat.
3. Si Meta solicita registrarse como desarrollador, complete el registro y acepte los
   términos que correspondan.
4. Confirme que la cuenta de desarrollador puede trabajar con el portfolio de Lumat.

Si Maxi ya tiene una cuenta de desarrollador, no es necesario crear otra. Solo hay que
confirmar que tiene acceso al portfolio correcto.

## 3. Crear la aplicación de tipo Business

1. En Meta for Developers, abra **My Apps** y seleccione **Create App**.
2. Elija el tipo de aplicación **Business**.
3. Asigne un nombre reconocible para LumatAgent y vincule la aplicación al portfolio
   de Lumat cuando Meta lo solicite.
4. Finalice la creación y abra el **App Dashboard**.
5. Guarde para referencia el **App ID** y confirme que la aplicación quedó asociada al
   portfolio correcto.

No envíe todavía secretos ni tokens. En este punto solo necesitamos confirmar que la
aplicación existe y que el acceso administrativo es correcto.

## 4. Agregar WhatsApp Business Platform

En el **App Dashboard** de la aplicación:

1. Seleccione **Add Product**.
2. Agregue **WhatsApp** y abra la sección de configuración o **API Setup**.
3. Confirme o cree la **WhatsApp Business Account (WABA)** asociada al portfolio de
   Lumat.
4. Revise que la empresa, la WABA y la aplicación pertenezcan al mismo portfolio.
5. Identifique el **Phone Number ID** que muestre Meta para el número configurado.

La WABA es la cuenta de WhatsApp Business que contiene los números y la configuración
de la plataforma. No la confunda con el número de teléfono ni con el App ID.

## 5. Validar con el número de prueba de Meta

El número de prueba que aparece en **WhatsApp > API Setup** pertenece a Meta. No es el
número real de Lumat y no requiere migrar el número que usa actualmente el negocio.

1. En **WhatsApp > API Setup**, seleccione el número de prueba que ofrece Meta.
2. Agregue como destinatario de prueba el teléfono autorizado para las pruebas. Use
   los límites que indique el panel.
3. Envíe un mensaje de prueba desde ese teléfono y confirme que la aplicación puede
   responder.
4. Registre el **Phone Number ID** del número de prueba y manténgalo identificado como
   `test`, separado del número real.
5. Coordine con Stefan/desarrollo la prueba de recepción, respuesta y webhook.

El número de prueba sirve para validar la integración inicial. No debe presentarse a
los clientes como el número comercial de Lumat.

## 6. Preparar el número real dedicado

Antes de registrarlo, confirmen con Stefan que el número cumple estas condiciones:

- Es un número dedicado para LumatAgent y Lumat puede controlar la SIM o el método de
  verificación por SMS o llamada.
- Está disponible para recibir el código de registro y definir el PIN de verificación
  en dos pasos.
- No se encuentra activo en la aplicación de WhatsApp ni en WhatsApp Business.
- Lumat acepta que el registro en WhatsApp Business Platform puede requerir
  desvincular o migrar la cuenta existente.

Un número usado en WhatsApp o WhatsApp Business puede no poder registrarse directamente
en la Cloud API. **No borren ni migren la cuenta antes de confirmarlo con
Stefan/desarrollo.** Primero hay que revisar qué conversaciones, dispositivos,
automatizaciones o usos actuales dependen de ese número y acordar el momento de la
migración.

Cuando se autorice el cambio:

1. Confirme el número en formato internacional y su titularidad operativa.
2. Coordine la desvinculación o migración de la cuenta existente.
3. Registre el número real desde **WhatsApp > API Setup**.
4. Complete la verificación por SMS o llamada y configure el PIN de dos pasos.
5. Confirme que Meta muestra el número real dentro de la WABA correcta.
6. Entregue a desarrollo el nuevo `META_PHONE_NUMBER_ID`, nunca el del número de
   prueba por error.

## 7. Generar y entregar identificadores y credenciales

### Datos que deben identificarse

Para referencia y coordinación, registren en el panel de Meta:

- **App ID** de la aplicación.
- **Business ID** del Meta Business Portfolio.
- **WABA ID** de la WhatsApp Business Account.
- **Phone Number ID** del número que se vaya a usar en cada entorno.

### Credenciales que debe recibir desarrollo

El servidor utiliza estos nombres de variables, definidos también en
`infra/.env.example`:

| Variable | Qué representa | Cómo se obtiene o define |
|---|---|---|
| `META_ACCESS_TOKEN` | Token de acceso de larga duración para enviar mensajes | Se genera desde la configuración de usuarios del sistema y permisos de la aplicación, siguiendo el flujo que muestre Meta |
| `META_PHONE_NUMBER_ID` | Identificador del número conectado a la API | **WhatsApp > API Setup** |
| `APP_SECRET` | Secreto de la aplicación para validar la firma del webhook | **App settings > Basic** |
| `VERIFY_TOKEN` | Valor acordado para el handshake del webhook | Lo define Stefan/desarrollo y debe coincidir con el valor configurado en Meta |

El PIN de dos pasos sirve para el registro y la administración del número. No es una
variable del servidor ni debe incluirse en un correo o mensaje. Si hace falta durante
una operación guiada, introdúzcalo directamente en Meta o compártalo solo mediante el
canal seguro acordado.

Para generar el token, Stefan/desarrollo indicará el usuario del sistema y los permisos
que correspondan al flujo de la aplicación. No invente permisos ni copie un token de
otra aplicación.

## 8. Configurar el webhook con Stefan/desarrollo

No es necesario que Maxi configure el servidor ni escriba código. La configuración se
coordina en una sesión conjunta:

1. Desarrollo confirma el endpoint HTTPS público y el valor de `VERIFY_TOKEN`.
2. En **WhatsApp > Configuration**, se registra la URL del callback y el token de
   verificación.
3. Se verifica el handshake y se suscribe la aplicación al campo `messages`.
4. Desarrollo instala los secretos en el entorno del servidor, nunca en el repositorio.
5. Se prueba la recepción de mensajes, la firma, la respuesta y los reintentos.
6. Se deja constancia de si la prueba corresponde al número `test` o al número real.

El runbook técnico de despliegue, secretos, validación y operación está en
[`docs/ops.md`](ops.md). Esta guía no lo duplica.

## 9. Checklist de información para entregar

### Meta y WhatsApp

- [ ] Nombre legal del negocio y portfolio de Meta que se utilizará.
- [ ] Nombre y correo de la cuenta administradora de Meta, compartidos solo para
      confirmar permisos, no como contraseña.
- [ ] Estado de la verificación del negocio.
- [ ] App ID.
- [ ] Business ID.
- [ ] WABA ID.
- [ ] Phone Number ID del número de prueba.
- [ ] Phone Number ID del número real, cuando se apruebe su migración.
- [ ] Confirmación explícita de que el número real está dedicado y puede desvincularse
      de WhatsApp o WhatsApp Business, si corresponde.
- [ ] `META_ACCESS_TOKEN`, `APP_SECRET` y `VERIFY_TOKEN`, entregados únicamente por el
      canal seguro acordado con Stefan/desarrollo.
- [ ] Estado de la verificación del número real y del PIN de dos pasos, sin enviar el
      PIN por WhatsApp o correo.
- [ ] Dominio o subdominio que Lumat autoriza para el webhook, si corresponde.

### Información del negocio

- [ ] Catálogo y descripción de servicios.
- [ ] Tarifas y precios vigentes, o instrucciones sobre qué informar y qué derivar.
- [ ] Comunas o zonas de cobertura.
- [ ] Garantías y condiciones de los trabajos.
- [ ] Procedimientos habituales, plazos y datos que debe solicitar el bot.
- [ ] Preguntas frecuentes.
- [ ] Protocolos para gas, incendio, fugas y otras emergencias.
- [ ] Horarios de atención y contactos de emergencia.
- [ ] Persona responsable de revisar las derivaciones a un humano.
- [ ] Nombre, presentación y tono del asistente.
- [ ] Mensajes estándar de saludo, despedida y fuera de horario.
- [ ] Logo para el panel, si desean incorporarlo.

Si algún documento todavía no existe, podemos realizar una sesión de captura de
conocimiento con una persona que conozca la operación de Lumat.

## Próximo paso

Coordinar una sesión con Maxi y Stefan para confirmar el portfolio, revisar la
aplicación y validar primero el número de prueba. El número real se agenda únicamente
después de revisar la desvinculación o migración necesaria.
