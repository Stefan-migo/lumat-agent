# Análisis propio del corpus real de conversaciones

Fecha: 2026-11-12 · Estado: read-only. Insumo de `03-defectos-y-mejoras.md` y `04-corpus-desde-casos-reales.md`.

---

## 1. Inventario y método

| Dato | Valor |
|---|---|
| Carpetas entregadas | 36 |
| Conversaciones únicas | **34** (`Hugo Ochoa …(1)` y `Jorge orihuela …(1)` son duplicados byte a byte) |
| Clientes distintos | **32** |
| Mensajes | **4.600** (2.667 del dueño, 2.049 del cliente, 34 de sistema) |
| Rango temporal | nov-2025 → nov-2026 |
| Formatos | `.txt` (crudo) y `.md` (exportado); ambos con el mismo contenido |

Método: parseo determinista (emisor, timestamp, tipo, latencia), extracción de las puertas deterministas del bot directamente desde el código, y lectura completa de las 34 conversaciones con citas y número de línea.

**Advertencia estructural:** en todo el corpus el único emisor propio es `Tú`, que es Maximiliano Escanilla, el dueño (se identifica en `Camila Covián…:5` y `Hugo Ochoa…:11`). **No hay un solo mensaje del bot.** Esto es el estándar humano y la distribución de entrada; no es un registro de fallas del bot.

---

## 2. Lo que el corpus es y no es

**Es:**
- la distribución real de entrada: cómo escribe un cliente chileno, con faltas de ortografía, audios, videos, stickers y mensajes partidos en tres líneas;
- el estándar de oro de comportamiento: qué hizo, qué prometió y qué olvidó el mejor vendedor de la empresa;
- la evidencia de qué fricción cuesta plata.

**No es:**
- un log del bot (no contiene ni una respuesta del asistente);
- una base de políticas (los precios cambian por temporada);
- un catálogo de "casos" independientes: es un tejido de relaciones comerciales.

---

## 3. Los ocho patrones que ordenan el corpus

### P1 · La unidad real es la **red cliente-propiedad-tercero**, no el mensaje

- **Sol** maneja tres propiedades (Los Litres 1400 casa 56, su casa en Parque Sur, depto Fray Montalva 102), dos RUT (persona natural y APU Inversiones SPA) y ocho meses de obra continua en 710 mensajes.
- **Mónica Dawabe** aparece en **tres** conversaciones distintas: la propia (495 mensajes, casa + empresa textil) y las de sus dos arrendatarios, **Diego Prado** y **Guila Sosman**.
- **Sonia Bahamondez** administra dos departamentos de dos dueños distintos, con dos arrendatarios distintos, desde Alemania.
- **Jorge Orihuela** tiene tres equipos de aire acondicionado; **Sol** tiene caldera, dos calefont, radiadores, losa radiante, encimera y campana.

Esto justifica el objeto `Property` del documento del dueño y **no** justifica los 19 objetos: lo que hace falta es saber a qué propiedad y a qué equipo pertenece un mensaje, y quién decide. Nada más.

### P2 · Lo que se rompe no es el trabajo técnico: es el seguimiento comercial

El servicio técnico sale bien y el cliente lo dice: «10/10» (Nerys), «el agua de duchas está impecable» (Javier), «hoy me duché con agua caliente» (Francisco). Lo que se cae es la promesa:

| Cliente | Promesa | Desenlace |
|---|---|---|
| Sonia Bahamondez | cotización pedida 4 veces | 25 días; el cliente cierra la relación: «me dejaste la embarrada» |
| Paolo Ganderini | cotización eléctrica | pedida de nuevo **5 meses después** |
| Gonzalo Bettancourt | cotización de gasfitería | 29 días y tres reclamos |
| Nerys de la Rosa | cotización de repuesto | 6 días |
| María Jesús Ríos | repuestos ANWO | 68 días, calefacción apagada |
| Sol | cotización de encimera | pedida cuatro veces |
| Guila Sosman | informe de la caldera | nunca llega |
| Hugo Ochoa | cotización de piezas | nunca llega; el cliente pregunta a los 14 días |

**58 mensajes del dueño contienen una promesa.** El patrón dominante no es «no supe qué hacer»: es «lo dejé pendiente».

### P3 · El cliente llega con vocabulario impreciso y el humano traduce

- Lukas: «el dispositivo azul que está afuera, debajo de la caldera».
- Catalina: «un quemador de la cocina agripado» → el humano pregunta «¿a qué se refiere con agripado?».
- Mónica: «Radiador baño 800x500» → «no te entiendo».
- Carla: un audio sin texto.

Aquí un bot **puede ser mejor que el humano**: hacer una pregunta aclaratoria cuesta cero y el humano muchas veces no la hizo, respondió de memoria.

### P4 · El tercero manda

Metrogas, ANWO, la corredora, el dueño de la casa, el conserje, el maestro de la bodega, el seguro: **36 mensajes** mencionan un tercero. Juan Pereira es el caso puro: Lumat traduce y coordina entre Metrogas (Cecilia) y ANWO, y el cliente pregunta «¿el retiro quién lo coordinará, ANWO o Metrogas?».

El bot no tiene dónde guardar eso. La consecuencia práctica no es que deba coordinarlo: es que debe **nombrarlo** y no contradecirlo.

### P5 · El tráfico dominante es mantención y cotización, no emergencia

Conteo de menciones en los 2.049 mensajes del cliente: dinero **161**, repuestos **113**, documentos **65**, roles **48**, terceros **36**, seguridad **34** (en 8 conversaciones), garantía **19**.

El ciclo de mantención anual aparece en al menos diez conversaciones (Nancy, Héctor, Catalina, Sandra, Gonzalo, Hugo, Claudio, Sol, Francisco, Lukas) y el ciclo se repite porque **el cliente no recuerda cuándo le toca**: Nancy cree que es cada 6 meses, Héctor recibe el aviso seis meses después, Lukas deja marzo agendado.

En cambio la emergencia real es escasa pero grave: olor a gas al final de Pabla, error EA + olor en Paula, calefont declarado inseguro en Guila.

**Desalineación estratégica:** el bot está mejor armado para la emergencia (puerta determinista + protocolo + derivación) que para el ciclo de mantención, que es el 80% del volumen.

### P6 · El adjunto es diagnóstico, no adorno

**194 de 2.049** mensajes del cliente (9,5%) son adjuntos: 107 notas de voz, 50 videos, 18 stickers. Se concentran: Antonieta 26%, Mónica 15%, Javier 7%, Francisco 7%.

El humano diagnosticaba desde el video: «Esos son errores de que sigue tapada la caldera» (Antonieta), y Claudio manda el video del E25/E26 y se resuelve por chat. El bot no ve ni oye: deriva (D4).

### P7 · El precio y el alcance son la fricción comercial número uno

- Pabla detecta **un error de aritmética** en la cotización: «¿160.000 en total? O ¿320?», y el dueño reconoce «en vez de poner total puse mano de obra».
- Héctor corrige un cobro: «pero ¿no era 60.000?» (se habían dicho 80.000).
- Diego Prado compara con el año anterior: «el año pasado fueron 110».
- Sol: «nos pareció muy alto», y luego «finalmente está desmereciendo nuestro trabajo».
- Sonia pide el presupuesto «exacto» descontando partidas que no se harán.

Tres de estas se evitan con dos datos que Lumat ya tiene o podría tener: el tarifario vigente y el precio del año anterior para ese cliente.

### P8 · El silencio cierra la conversación, no el cliente

**22 de 34** conversaciones terminan con un mensaje del cliente. Los casos terminales:

- **Sonia**: ruptura explícita, el arrendatario contrató a otro gasfiter.
- **Sol**: ocho meses, y el último mensaje es un saludo sin respuesta.
- **María Jesús**: 68 días sin repuestos, con la calefacción apagada y un «me preocupa que esto quede pendiente».
- **Carla**: tres reprogramaciones en tres días por el sueño de los niños; la conversación muere.
- **Kathy**: 14 llamadas perdidas y una frase.

Ninguno de estos clientes dijo «no me interesa». Se fueron por cansancio.

---

## 4. Tipología de desenlace del corpus

| Desenlace | Casos | Qué lo decide |
|---|---|---|
| **Resuelto y cobrado** | Héctor, Sandra, Camila, Francisco, Juan Pereira, Lukas, Nancy (final), Claudio (final) | una visita con hora firme y un precio dicho antes |
| **Resuelto, con deuda documental** | Antonieta, Catalina (cierre), Marcelo, Gonzalo (parcial) | el trabajo se hizo, el informe o la cotización quedó |
| **Pendiente por repuesto** | María Jesús, Lukas (3 meses), Pabla, Sol, Jorge | stock ANWO/Junkers, sin fecha creíble |
| **Pendiente por cotización** | Paolo, Sonia, Gonzalo, Paulina, Mónica | la cotización pedida y no enviada |
| **Perdido por fricción** | Sonia, Sol, Carla | proceso, no precio |
| **Invisible** | María Eliana, Kathy, Paula (stand-by) | el export no muestra el cierre |

La columna de la derecha es la conclusión operativa: **lo que decide el desenlace es la firmeza de la hora y la existencia del precio escrito.** No es un problema de diagnóstico.

---

## 5. Qué significa para el bot

1. El bot no necesita un motor de 19 objetos: necesita **ficha de propiedad/equipo**, **registro de compromisos** y **rol del que decide** (P1, P2, P4).
2. Su mayor ventaja competitiva es la que el humano no ejerció: **preguntar una vez** en lugar de responder de memoria (P3).
3. Su mayor riesgo medido no es inventar: es **derivar de más** (adjuntos y cortesía, D3/D4) y **olvidar a los 6 mensajes** (D1).
4. El ciclo de mantención es el volumen; la emergencia es la excepción grave. El corpus pide equilibrar ahí (P5).
5. Su métrica de éxito no es la calidad de la respuesta: es **cuántas promesas quedan sin dueño** (P2, P8).

---

## 6. Mapa de conversaciones

Detalle por conversación con citas y líneas en `05-mapa-conversaciones.md`.
