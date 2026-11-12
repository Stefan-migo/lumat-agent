# Escenarios objetivo derivados del corpus real

Estos casos pertenecen a la hoja de ruta, no al corpus de regresión: el bot actual no puede cumplirlos de forma fiable. Criterio de salida: no promover un caso al corpus hasta que la capacidad descrita exista y pueda verificarse por su interfaz observable.

## D1 — Recuperar ficha e historial persistente del caso

**Evidencia:** el cliente vuelve sobre un trabajo anterior y espera continuidad; hoy el historial de conversación no equivale a una ficha de caso recuperable.

**Objetivo:** identificar el caso, propiedad y equipo relacionados antes de responder, y distinguir hechos guardados de inferencias.

**Criterio de salida:** un test de conversación posterior recupera sólo hechos persistidos pertinentes, cita el trabajo previo correctamente y no inventa historial en ausencia de coincidencia.

## D5 — Vincular postventa con el servicio anterior

**Evidencia:** La clienta reporta una falla al día siguiente de la mantención; se envía un video cuyo contenido no puede probarse con este corpus de texto.

**Objetivo:** vincular la postventa a la visita previa sin afirmar diagnóstico a partir del video.

**Criterio de salida:** con una visita previa identificable, el bot la reconoce y ofrece seguimiento; sin vínculo confirmado, declara la limitación y solicita revisión humana.

## D6 — Registrar promesas y pendientes

**Evidencia:** el caso de una clienta incluye un informe prometido que quedó pendiente; otros casos vuelven a pedir cotizaciones ya prometidas.

**Objetivo:** convertir cada compromiso en un pendiente con responsable y estado.

**Criterio de salida:** un compromiso aceptado se registra, aparece en la consulta de pendientes y se cierra sólo al registrar su cumplimiento; el bot nunca dice que se envió si no hay evidencia.

## D7 — Reconocer quién autoriza

**Evidencia:** Los casos de los arrendatarios incluyen; la decisión de gastos corresponde al propietario. La conversación no ofrece una señal estructurada confiable del rol.

**Objetivo:** conservar el rol declarado y distinguir quién usa el equipo de quién autoriza un gasto.

**Criterio de salida:** en un caso con rol y propietario identificados, el bot no confirma precio, rebaja ni trabajo como autorizado por un arrendatario; solicita autorización al decisor y nunca infiere el rol.

## D4 — Entender adjuntos (visión y transcripción)

**Evidencia:** Antonieta envía un video y otros clientes usan audio o imágenes. El texto exportado sólo marca adjuntos omitidos; sus contenidos no pueden reconstruirse ni inventarse.

**Objetivo:** procesar imagen/audio cuando el canal y el modelo lo soporten, manteniendo separado lo observado de lo inferido.

**Criterio de salida:** con un adjunto de prueba rotulado, describir sólo elementos visibles/audibles relevantes, pedir aclaración si no basta y nunca afirmar que interpretó contenido no disponible.

## D10 — Rescatar un hilo inactivo

**Evidencia:** hay clientes que reabren hilos tras largos intervalos y esperan continuidad; el contexto conversacional limitado no garantiza recuperar el último pendiente.

**Objetivo:** identificar inactividad, recuperar los pendientes pertinentes y confirmar el contexto antes de actuar.

**Criterio de salida:** en un hilo retomado tras un intervalo definido, el bot presenta el pendiente recuperado sin tratar al cliente como nuevo ni asumir que sigue vigente; cuando no hay registro, pregunta.

## Límites de los escenarios medibles hoy

- La interacción de Catalina sobre «agripado» mide pedir aclaración, no clasificar técnicamente el término.
- El caso de la arrendataria sólo puede exigir no afirmar autorización no declarada; la identificación persistente del rol y el contacto con el propietario quedan pendientes de D7.
- El adjunto de Antonieta se representa como omitido; no se exige reconocer el trabajo previo ni interpretar su video.
- El caso de «dato + pregunta» requiere responder la pregunta explícita, pero no una memoria persistente más allá del contexto que el turno actual tenga disponible.
