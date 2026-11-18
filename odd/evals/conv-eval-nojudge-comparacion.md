# Comparación sin juez — `nojudge-main` contra `nojudge-antes`

Para qué sirve
--------------
El baseline antes/después se midió con dos instrumentos distintos: el árbol «antes» corrió con el
harness de su momento y el «después» con uno que, entre medio, empezó a registrar el estado por turno y
a no contar como falta el silencio de una conversación derivada. Comparar esos números mezcla dos
cosas: lo que cambió el bot y lo que cambió la regla.

Esta corrida aísla las dos. Mismo `scripts/conv_eval.py` y mismo `scripts/chat_harness.py` en los dos
árboles, **sin juez**: sólo los gates deterministas, que no dependen de ningún modelo.

| | Árbol | Sello | Escenarios | Pasan |
|---|---|---|---|---|
| después | `main` | `69d9a12b7` | 42 | **35** |
| antes | `odd/baseline-antes` | `be5266f8b` | 42 | **33** |

Comandos, idénticos salvo el `--run-tag`:

```
.venv/bin/python scripts/conv_eval.py --no-judge --run-tag nojudge-main
.venv/bin/python scripts/conv_eval.py --no-judge --run-tag nojudge-antes
```

Cambiaron de estado cuatro escenarios
-------------------------------------
Ninguno por el instrumento. El borde humano no movió un solo escenario en gates: los cuatro cambios
vienen del trabajo de dirección mergeado antes, y uno de ellos es una **regresión**.

| Escenario | Antes | Ahora | Atribución |
|---|---|---|---|
| `real-cortesia-no-es-reclamo` | G1, G4 ✗ | ✓ | **Mejora.** Una cortesía («te molesto con…») se leía como reclamo y derivaba a un humano. Ya no. Es el trabajo de disparadores de reclamo, no el borde. |
| `real-maria-jesus-evaluacion-caldera` | G6 ✗ | ✓ | **Mejora.** La respuesta ya contiene el ancla de evaluación. Camino `respond`. |
| `simple-cobertura-comuna` | G6 ✗ | ✓ | **Mejora.** La respuesta ya nombra al asesor/coordinación. Camino `respond`. |
| `simple-dia-especifico` | ✓ | G6 ✗ | **Regresión, y no es de la feature de emergencia.** Ver abajo. |

### La regresión

Turno 2 del cliente: «me llamo paula, paula@mail.com, **calle siempre viva 123, ñuñoa**».

- **Antes:** el bot guardaba la dirección y pasaba a pedir el consentimiento; el turno 3 llegaba a la
  oferta de agenda.
- **Ahora:** el bot responde «¿Cuál es tu dirección?» y en el turno 3 vuelve a pedirla («¿Cuál es tu
  dirección o… el pin de WhatsApp?»). Nunca llega a la oferta, y la conversación se queda en `bot`.

La dirección se da completa y con comuna; el bot la descarta. El escenario queda en `bot` de punta a
punta, así que el borde humano no participa: el cambio está en la validación de dirección que entró con
el trabajo de dirección (`app/services/address_validation.py` y su llamada desde `capture`). Esconde
dos cosas: la dirección no se acepta, y la conversación no avanza ni deriva — se queda preguntando.

Los siete que fallan gates en `main`
------------------------------------
Sin juez, la lista de fallos es mucho más corta que los 16 que reportó el baseline: los otros eran
hard fails del juez sobre el contenido, que ningún gate puede ver.

| Escenario | Gate | Qué pasó |
|---|---|---|
| `complejo-dos-temas` | G1, G10 | Quedó en `bot` esperando `human`, y no registró la derivación por «persona» |
| `complejo-no-quiere-email` | G1, G10 | Igual: esperaba `human` y una derivación (`booking_unavailable` o persona) |
| `real-claudio-caldera-valvula` | G4 | Registró `unknown_intent`, que el escenario prohíbe |
| `real-dato-mas-pregunta` | G4 | Registró `unknown_intent`, prohibido |
| `real-mantencion-caldera` | G6 | Ninguna respuesta menciona la mantención ni la caldera |
| `real-precio-mantencion-ciclo` | G2 | Clasificó `consulta` donde se esperaba un intent de valores/precio |
| `simple-dia-especifico` | G6 | La regresión de arriba: nunca llega a hablar de horario ni visita |

Conclusión
----------
1. El instrumento nuevo **no contamina** la comparación por gates: cero escenarios cambiaron por el
   borde humano. Los números de gates del baseline siguen siendo comparables.
2. La feature de emergencia movió lo que tenía que mover (los dos escenarios de emergencia, medidos
   aparte con juez) y nada más.
3. El problema real que apareció no es de esa feature: una dirección completa se rechaza y la captura
   entra en bucle. Es el próximo arreglo, y es de una línea de trabajo distinta.
4. Los gates no alcanzan para juzgar el corpus: 7 de 16 fallos son mecánicos y 9 son de contenido. El
   titular completo necesita una corrida con juez, y eso se decide cuando los grupos de contenido estén
   cerrados.
