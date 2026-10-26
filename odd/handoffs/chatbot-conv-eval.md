# Handoff — evaluador conversacional del chatbot (`chatbot-conv-eval`)

Escrito el 2026-10-26 al cerrar la sesión, **con el baseline todavía sin correr**. La fuente de verdad es
`odd/tasks/chatbot-conv-eval.md` (S1–S9, T1–T8, L1–**L15**): leelo hasta `## Log` antes de tocar nada.
Este archivo es el mapa para arrancar en una sesión nueva.

## Dónde

| | |
|---|---|
| Worktree | `/home/stefan/repos/lumat-agent-odd-chatbot-conv-eval` |
| Branch de trabajo | `odd/conv-eval-baseline` (sobre `main` `ce1042f7` + el commit del sello) |
| Base | `origin/main`, mergeado; el diff neto **solo agrega** |
| Tests | `bash scripts/test.sh full` → **exit 0** · `quick` y `shape origin/main` → **exit 0** |
| Estado del árbol | limpio · nada pendiente de commitear |

Ya en `main`: el instrumento completo (`scripts/conv_eval*.py`, corpus de 14, seed de KB), los gates, el
juez por rúbrica **con repeticiones**, `--reset`, transcripts, y la evidencia histórica en `odd/evals/`.

## Lo que hay que saber antes de correr nada

1. **La clave del bot NO está en la base de test.** Vive en el entorno del contenedor del harness
   (`lumat-harness-api-1`, variable `DEEPSEEK_API_KEY`). La base de test no tiene `panel_secrets`. Se pasa
   como variable de entorno; `Settings.deepseek_api_key` es el fallback.
2. **La clave del juez es otra**: `~/.gentle-shell/agent/auth.json`, proveedor `opencode-go`. Esa ya está.
3. **`CHAT_MODEL` importa.** El default del código es `deepseek-chat`; el harness corre
   `deepseek-flash`. Sin fijarlo, medís un bot distinto del de producción (el sello ya lo registra).
4. **`pytest` vacía `kb_documents`.** Después de cualquier suite hay que **re-sembrar** antes de correr el
   evaluador; si no, el juez ve la KB vacía y `grounding` se va al piso.
5. **Un `--run-tag` puede pisar evidencia.** Antes de elegir uno, mirar `odd/evals/`. `baseline-2` choca
   con `conv-eval-baseline-2.md`, que está commiteado y citado en L8/L9. Usar `citable-N`.

## Cómo correr una corrida citable

```bash
cd /home/stefan/repos/lumat-agent-odd-chatbot-conv-eval
eval "$(bash infra/test-db.sh env)"                 # base de test derivada (5893 en este worktree)
KEY=$(docker inspect lumat-harness-api-1 --format '{{range .Config.Env}}{{println .}}{{end}}' \
      | sed -n 's/^DEEPSEEK_API_KEY=//p')           # nunca imprimirla
uv run python scripts/seed_kb_docs.py --apply       # OBLIGATORIO tras cualquier pytest
DEEPSEEK_API_KEY="$KEY" CHAT_PROVIDER=deepseek CHAT_MODEL=deepseek-flash \
  uv run python scripts/conv_eval.py --live --reset --quiet --run-tag "citable-1"
```

- Una suite por worktree: las corridas y `pytest` comparten base y se bloquean en el `TRUNCATE`.
- Después de la corrida: **commitear el `.md` y la transcripción, nunca el JSON** (`odd/evals/*.json` está
  ignorado). Verificar que el reporte diga `árbol sucio: no`, el corpus/KB esperados y
  `deepseek / deepseek-flash`.

## Lo que está bloqueando el baseline

**Defecto #9: el cliente simulado no reintenta.** El 2026-10-26 devolvió prosa en vez del JSON que se le
pide y `_parse_json` reventó, matando el escenario:

```
✗ simple-horario-sabado: la corrida falló: no JSON object in verdict: 'me llamo carlos, …'
```

Reproducido dos veces con nombres distintos. El juez ya tiene su reintento (`fb5220fe`); el simulador no.
Y como **un escenario que falla aborta la corrida entera** (`exit 2`, sin reporte) mientras un veredicto
faltante solo se registra como "no medido", un hipo del simulador tira los 14 escenarios.

Orden de trabajo para la próxima sesión:

1. Reintento del simulador (mismo patrón que el del juez) + tests, y decidir si un escenario fallido debe
   abortar la corrida o registrarse como no medido.
2. Correr `citable-1`, `citable-2`, `citable-3` y commitear la evidencia.
3. Decidir qué hacer con `escalation` (ver abajo).
4. Recién entonces comparar contra el worktree de mejoras, N=3 por versión.

## Lo que ya está medido (y lo que no vale)

- **Piso de ruido del bot: 1 escenario de 14.** Dos corridas idénticas → 5/14 y 6/14. Una diferencia de
  1 escenario no autoriza decir "mejoró".
- **Varianza del juez: 8 de 18 celdas se mueven entre llamadas idénticas**, hasta 3 puntos, y el
  `hard_fail` oscila (L14). Por eso el juez repite 3 veces: mediana como puntaje, spread como
  incertidumbre, `hard_fail` por mayoría.
- **Calibración S9 (con el juez agregado): 11/18 exactas.** `grounding` coincide, `policy` del caso de
  reclamo quedó en 1/1 (el juez viejo decía 4) y la escalación dejó de negar un `handoff` registrado.
- **Abierto: `escalation`.** Caso complejo con **spread 4** —el juez no decide entre 0 y 4— y caso super
  estable pero 2 puntos abajo del owner. El veredicto del owner: correr el baseline igual, citándolo por
  los gates (deterministas) y llevando el ± en las dimensiones.
- **Ninguna corrida commiteada es citable**: todas las históricas sellaron `dirty: sí` (defecto del sello,
  arreglado en #673) y además el corpus y la rúbrica cambiaron después.

## Los nueve defectos ya corregidos (no los re-busques)

1. Veredicto truncado del juez abortaba la corrida → un reintento; si falla, "sin veredicto", nunca puntaje.
2. `kb_miss` blando: producción no registra evento si el bot responde la oferta sin escalar → G9 lee el
   texto configurado. (Hueco de fondo en `app/`: follow-up.)
3. La evidencia citada del juez se tiraba del reporte → viaja con cada fila.
4. Corrida larga sin visibilidad → progreso por escenario con `flush`.
5. Reusar `--run-tag` apila corridas → el runner rechaza un tag con clientes (`exit 2`).
6. `--reset` fallaba por permisos y FKs → conexión admin, 24 tablas, sin `CASCADE`.
7. El sello contaba los reportes de la corrida anterior como edición del árbol → excluye `odd/evals/`.
8. El cliente simulado no tenía turnos (`max_turns` = `len(turns)`) → `SIMULATED_TURNS = 3` con techo
   declarado opcional.
9. **El cliente simulado no reintenta** cuando devuelve prosa en vez de JSON → **pendiente**.

## Gotchas que costaron tiempo

- Un `| grep` sobre la salida de una corrida **se come el stderr**: un fallo de `--reset` pareció un job
  colgado. Loguear sin filtrar y grepear al final.
- Jobs largos con `setsid` y log en `/tmp`; un crash del wrapper no mata la corrida.
- `logger.exception` del cerebro imprime tracebacks que **no** matan la corrida (Meta 401 → SMTP ausente).
- La base de test de este worktree está en **5893**; el rol `app` no puede truncar, el admin sí.
- Un `git commit` que abre editor y queda en background deja `index.lock` huérfano. Usar `GIT_EDITOR=true`
  y verificar con `ps` antes de borrarlo.
- `git reset --hard` está bloqueado por el guardrail. Para reescribir historia: rama nueva +
  `git filter-branch --index-filter`.
- **No usar `pkill -f` con un patrón que aparezca en tu propia línea de comando**: se mata el shell solo.
- `main` avanza mucho: un PR queda `BEHIND` enseguida. Con `strict: true`, mergear `origin/main` en la rama
  y volver a esperar CI. Si tras retargetear queda `BLOCKED` con todos los checks verdes, es caché de
  mergeabilidad: cambiar la base y volverla a poner fuerza el recálculo.
