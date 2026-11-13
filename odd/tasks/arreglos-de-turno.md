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
