# Arreglos de turno — D2 y D8

Dos defectos de `odd/analysis/lumatdata/03-defectos-y-mejoras.md` que el propio análisis
clasifica juntos: «D2, D3 y D8 son arreglos de turno y se pueden hacer sin esa base». D3 ya se
arregló en Fase 1. Ninguno necesita migración.

## Specs

**S1 · D2 — una pregunta adosada a un dato no se pierde.**
«Causa: `app/chat/nodes/orchestrate.py:137-156`. Se considera pregunta sólo si `"?" in text and not
state.extracted`, o si nombra un término de horario/cobertura (el arreglo T4)». «La conjunción es el
error: si el turno trae extracción, se trata como respuesta y la pregunta desaparece. La extracción
**ya se aplicó** antes de decidir, así que nada se pierde por contestar la pregunta». «Arreglo
acotado: sumar forma interrogativa explícita (`¿…?`, «cuánto», «cuándo», «pueden», «se puede») a la
condición, sin tocar el clasificador».

Evidencia medida: **303 de 2.157** mensajes del cliente (14%) son «dato + pregunta» en el mismo
turno. Ejemplos reales del corpus: «es factible que pases tipo 14 horas?» (Carla), «Consulta. No hay
cómo importar el repuesto que falta…?» (Carlos Díaz), «A las 14 puede ser?» (Catalina).

**S2 · D8 — el paso «esto requiere cotización», con captura de antecedentes.**
«No es un bug del tarifario: es la ausencia del paso «esto requiere cotización» con captura de
antecedentes, que es lo que el humano hacía en un turno». La demanda real está dominada por trabajos
**fuera** de tarifario: «encimera nueva (Sol), quemador de cocina agripado (Catalina), cambio de
caldera (Paulina), bypass y diseño (Juan Pereira), conversión GLP→GN (Carlos), filtración (Sol),
filtro de 120.000 (Nancy), mano de obra de termostato (Guila)».

**S3 · Lo que no se toca.**
El clasificador (`agent/personas/classify.md`) y su contrato quedan intactos: «sin tocar el
clasificador». El tarifario publicado sigue respondiendo los cuatro servicios que ya reconoce. La
cortesía no se lee como reclamo (D3, `7603ecd1`) y el orden de las puertas no cambia: urgencia >
presupuesto > derivación > LLM.

## Decisiones de diseño

- **D1 · D8 no inventa un precio ni un flujo nuevo.** El trabajo fuera de tarifario no tiene cifra publicada, así que la respuesta lo dice y pide los antecedentes en el mismo mensaje —los datos del equipo y qué necesita—, que es lo que el humano hacía en un turno. La captura de esos antecedentes ocurre por el flujo que ya existe (`capture`), no por un mecanismo paralelo.
- **D2 · El paso se reconoce por frase, no por modelo.** La tabla de frases sale de la demanda medida en el corpus: cambio e instalación de caldera, encimera, quemador de cocina, bypass, diseño de red, conversión GLP→GN, filtración, filtro y termostato. Un trabajo que no está en la tabla y no aparece en la KB conserva el camino actual.
- **D3 · El orden no cambia.** Un servicio con precio publicado sigue respondiendo desde el tarifario; el paso de cotización sólo ocupa el lugar del «no tengo ese dato».

## Tasks

| ID | Specs | Route | Commit |
|---|---|---|---|
| T1 | S1 | `_is_question` en `app/chat/nodes/orchestrate.py`: la forma interrogativa explícita basta aunque haya extracción | `fix(chat):` |
| T2 | S2 | `respond`: un trabajo fuera de tarifario ofrece presupuestar con los antecedentes, en vez de «no tengo ese dato» | `feat(chat):` |

## Log

**L1 — pedido del owner (verbatim).**

```
ok quiero terminar todos los D antes de volver a deployar
```

**L2 — el paso de cotización estaba inalcanzable.** El primer intento lo colgó de la rama de KB
miss de `respond`, y la sonda sobre el grafo real mostró por qué no sirve: «cuanto cuesta cambiar la
caldera» lo clasifica como `caldera`, `_dispatch` lo manda a `capture`, y el cliente lee «Entiendo, es
un problema con tu caldera. Cuéntame qué pasa con el equipo…». `respond` nunca corre, así que la rama
nueva era código muerto para los ocho trabajos que D8 mide. Corregido con una bandera de ruteo
(`quote_question`) en `_dispatch`, en el mismo lugar donde el arreglo T4 puso la suya: preguntar el
precio de un trabajo sin tarifa es una pregunta, no una falla nueva que diagnosticar. Va antes de
`CAPTURE_INTENTS` y después de `mid_capture`, para no romper la agenda a mitad de captura.

**L3 — la verificación de ese ruteo es de punta a punta.** El writer no pudo observarla porque el
clasificador determinista respondía antes; la sonda y la prueba de grafo que quedó en
`tests/integration/test_quote_required.py` sí: el mismo turno, por el grafo, contesta la cotización y
no pide diagnóstico.

**L4 — gate de cierre del corte 1.** `scripts/test.sh shape origin/main` → sin superficies nuevas (exit 0).
`scripts/test.sh full` con `FASTEMBED_CACHE_PATH` exportado → **exit 0**, una corrida completa sin una
sola línea `FAILED` ni `ERROR`. La nota del addendum de tests aplica igual: `-qq` suprime la línea de
conteo, así que la señal es el código de salida y la ausencia de fallas, no un número en el log.
