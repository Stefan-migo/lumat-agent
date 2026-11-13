# Fase 0 — Descubrimiento y verificación: integración 2Workers × Lumat

> **Tipo:** entregable comercial independiente
> **Duración:** 3 días de trabajo
> **Valor:** CLP 950.000, pagado por adelantado
> **Documento hermano:** [roadmap.md](roadmap.md)

---

## 1. Objetivo

Determinar, con evidencia y no con supuestos, qué puede y qué no puede hacer la API de 2Workers en
la cuenta real de Lumat, y a partir de eso fijar el alcance y el presupuesto firme de la integración.

Hoy la documentación pública de 2Workers tiene contradicciones y huecos que cambian el costo del
proyecto entre 6 y 10 días de trabajo. F0 los resuelve antes de firmar, no después.

---

## 2. Por qué existe F0

La API pública de 2Workers (que es la de Auvo) documenta recursos, pero no documenta las cinco cosas
que deciden el diseño:

| Pregunta abierta | Qué pasa si la respuesta es la peor | Costo |
|---|---|---|
| ¿Rechaza dos tareas a la misma hora para el mismo técnico? | Si las acepta, Lumat debe construir su propia guarda de conflicto | +2 días |
| ¿Geocodifica direcciones chilenas, o hay que mandar coordenadas? | Si no, hay que integrar geocoding y normalizar direcciones | +3-4 días |
| ¿Qué zona horaria asume `taskDate`? | El cambio de hora de septiembre mueve visitas una hora | +1-2 días |
| ¿Hay duración por tarea, o solo por tipo? | Hay que mapear y migrar el catálogo de servicios | +1 día |
| ¿Los webhooks tienen firma y reintentos? | Hay que construir idempotencia y control de origen | +2 días |

Ninguna de esas respuestas está en el blueprint. Todas se consiguen en 3 días de trabajo real contra
la cuenta.

Además, el documento público omite recursos que el sitio de Auvo sí menciona (`/services`,
`/invoices`, `/receivables`, `/routes`). Si están habilitados en el plan contratado, el alcance
puede crecer de forma útil; si no están, se cierra la puerta con evidencia.

---

## 3. Requisitos del cliente

Sin los puntos 1 y 2 no se puede iniciar.

1. **Credenciales de un usuario administrador dedicado a la integración** (`apiKey` y `apiToken`,
   desde *Menu > Integración*). Separado del usuario personal del dueño. Se entregan por canal
   seguro, nunca por WhatsApp ni correo.
2. **Autorización para crear y borrar un cliente, un usuario y una tarea de prueba** en la cuenta.
3. **Acceso de lectura al plan contratado**, para saber qué módulos están habilitados.
4. **Tres horas del contacto que decide** (dos llamadas: apertura y cierre).
5. **Confirmación de la zona horaria de la cuenta** y del horario de atención de Lumat.

---

## 4. Actividades

### Día 1 — Conexión y lectura

- Autenticación: `POST /login`, medir vigencia real del token y comportamiento al renovarlo.
- Confirmar URL base (`api.2workers.me/v2` frente a `api.auvo.com.br/v2`).
- **Medir latencia desde el VPS de Lumat.** Si cada request tarda cerca de un segundo, cambia el
  diseño del chatbot.
- `GET /tasks` por rango de fechas: máximo real de `pageSize`, comportamiento al excederlo,
  respuesta ante límite de llamadas.
- Verificar el formato exacto de `paramFilter`: el documento es inconsistente (`taskID` en un
  lugar, `taskId` en otro; `externalId` múltiple separado por coma) y de `selectfields`.
- Leer los catálogos reales: `/users`, `/teams`, `/taskTypes`, `/customers`, `/customerGroups`,
  `/segments`.
- Verificar existencia de `/services`, `/invoices`, `/receivables`, `/routes`.

### Día 2 — Las cinco pruebas que definen el presupuesto

1. **Solapamiento.** Crear dos tareas con el mismo `idUserTo` y `taskDate`. Determinar si la API
   rechaza, acepta en silencio, o acepta con advertencia.
2. **Coordenadas.** Crear una tarea sin `latitude`/`longitude` con una dirección chilena real.
   Determinar si 2Workers geocodifica, si falla, o si los campos son efectivamente obligatorios
   pese a lo que dice el texto del documento.
3. **Zona horaria.** Crear una tarea, leerla de vuelta, y probar el borde del cambio de hora
   chileno (primer domingo de septiembre). Determinar si almacena hora local sin zona, hora UTC, o
   la del servidor.
4. **Duración.** Leer `/taskTypes` y confirmar que `standardTime` es el único control de duración.
   Evaluar si conviene un tipo de tarea por servicio de Lumat o un tipo genérico.
5. **Webhooks.** Registrar un webhook real contra un endpoint temporal, disparar una acción, y
   capturar: payload completo, headers, presencia de firma, política de reintentos, timeout, y si
   distingue creación de modificación.

También en este día: probar `PUT /customers/` como upsert por `externalId` con un cliente real, y
verificar cómo normaliza teléfonos chilenos.

### Día 3 — Decisiones y redacción

- **Cierre de decisiones de negocio** con el contacto de Lumat:

  1. ¿Los técnicos se crean en 2Workers o en el panel?
  2. ¿Quién manda el WhatsApp al cliente en check-in, check-out y reprogramación?
  3. ¿Se migra el histórico de clientes? ¿Cuántos son?
  4. ¿Qué pasa con las visitas ya agendadas el día del corte?
  5. ¿El supervisor entra a 2Workers o solo al panel?
  6. ¿Quién administra los feriados chilenos?

- Redacción del informe y de la matriz de capacidades.

---

## 5. Entregables

1. **Informe de alcance y viabilidad** (8-12 páginas):

   - Matriz de capacidades verificadas: cada requisito con ✅ o ❌, y la evidencia pegada
     (request y response reales, no capturas de pantalla).
   - Las cinco pruebas del día 2 resueltas, cada una con su delta de días si la respuesta es
     adversa.
   - Arquitectura final: qué dato manda cada sistema, en un diagrama de una página.
   - Alcance confirmado y exclusiones explícitas.
   - Presupuesto firme por fase.
   - Plan de corte.
   - Anexo con la colección de requests ejecutados, re-ejecutable.

2. **Acta de decisiones** firmada por el cliente, con las seis respuestas del día 3.

3. **Registro de credenciales** entregadas por canal seguro, con la fecha de entrega y el
   responsable de custodia.

---

## 6. Criterios de aceptación

F0 se considera entregada cuando:

- el cliente recibe el informe y el acta de decisiones;
- las seis decisiones de negocio están respondidas y firmadas;
- las credenciales quedan registradas en el canal acordado.

**Cláusula de supuestos.** Si algún requisito no se pudo verificar por falta de acceso, por una
limitación del plan contratado, o porque el cliente no respondió a tiempo, queda declarado en el
informe como **"no verificado"**. En ese caso, el presupuesto asociado queda expresado como rango y
no como cifra firme.

---

## 7. Qué no incluye F0

- Código de producción, migraciones o cambios en el panel de Lumat.
- Configuración de la cuenta de 2Workers de Lumat (usuarios, equipos, tipos de tarea).
- Integración con WhatsApp o cambios en las plantillas de mensajes.
- Migración de datos.
- Soporte posterior al informe.

Si durante F0 se escribe algún script para consultar la API, es descartable: se entrega como anexo
del informe y no forma parte del producto.

---

## 8. Valor

F0 cuesta CLP 950.000 y su función es doble:

1. **Elimina el riesgo de cotizar a ciegas.** Convierte un rango de 6 a 10 días de incertidumbre en
   una cifra firme, y evita que ese delta aparezca a mitad del proyecto como un sobrecosto.
2. **Se entrega valor aunque no se continúe.** El informe describe la propia plataforma del cliente:
   qué puede y qué no puede hacer 2Workers, y cuánto cuesta cada camino. Es un documento que Lumat
   conserva y puede usar con cualquier otro proveedor.

En términos de decisión: por menos del 8% del proyecto total, se sabe exactamente qué se está
comprando antes de firmarlo.

---

## 9. Próximo paso

Confirmar credenciales y agendar las dos llamadas. El trabajo comienza cuando ambos requisitos están
cumplidos, y el informe se entrega 3 días hábiles después.
