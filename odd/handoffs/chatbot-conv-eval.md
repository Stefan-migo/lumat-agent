# Handoff — evaluador conversacional del chatbot (`chatbot-conv-eval`)

Escrito el 2026-10-23, **después de limpiar la evidencia y antes de abrir los PRs**. La fuente de
verdad es `odd/tasks/chatbot-conv-eval.md` (S1–S9, T1–T7, L1–L11): leelo hasta `## Log` antes de tocar
nada. Este archivo es el mapa para arrancar en una sesión nueva.

## Dónde

| | |
|---|---|
| Worktree | `/home/stefan/repos/lumat-agent-odd-chatbot-conv-eval` |
| Branch | `odd/chatbot-conv-eval`, ya reescrita y limpia de JSON |
| Backup de la historia anterior | `backup/pre-evals-cleanup` = `62b154e2` (rama con los JSON dentro) |
| Base | `origin/main` `497875af`, mergeada en `c3782d0f`; el diff neto **solo agrega** |
| Tests | `bash scripts/test.sh full` → **exit 0** (sin fallos; 10m51s) · `bash scripts/test.sh shape origin/main` → **exit 0** |
| Estado del árbol | limpio · **nada pusheado, ningún PR abierto** |

## Qué está construido

| Archivo | Qué hace |
|---|---|
| `scripts/conv_eval.py` | Schema y validador del corpus, 9 gates deterministas (G1–G9), scoring con cap por gate, runner scripted/`--live`, reporte JSON+MD con sello y diff, transcripts legibles, `--reset` con guarda |
| `scripts/conv_eval_corpus.yaml` | 14 escenarios: 5 simple, 4 complejo, 5 supercomplejo |
| `scripts/conv_eval_judge.py` | Juez por rúbrica 0–4 en 6 dimensiones (deepseek-v4.1-flash vía opencode-go) + cliente simulado |
| `scripts/seed_kb_docs.py` | Carga `docs/kb` como KB de cliente y es el preflight obligatorio |
| `tests/unit/test_conv_eval.py` (91) · `test_conv_eval_judge.py` (24) · `test_seed_kb_docs.py` (4) | Contrato model-free: schema, gates, scoring, reporte, sello, reset, transporte, credenciales |

Sin cambios en `app/` (non-goal explícito). El informe se escribe en `odd/evals/`.

## Cómo correrlo

```bash
cd /home/stefan/repos/lumat-agent-odd-chatbot-conv-eval
eval "$(bash infra/test-db.sh env)"                 # base de test derivada (5893 en este worktree)
export DEEPSEEK_API_KEY=...                        # el bot bajo prueba necesita su clave
# una vez por stack:
DATABASE_URL="$TEST_ADMIN_DB_URL" APP_DB_PASSWORD=app bash db/migrate.sh
uv run python scripts/seed_kb_docs.py --apply
# corrida:
uv run python scripts/conv_eval.py --validate-only                    # corpus, sin DB ni modelo
uv run python scripts/conv_eval.py --no-judge --run-tag t1            # gates, gratis
uv run python scripts/conv_eval.py --reset --run-tag t1               # estado limpio + juez
```

- **Una suite por worktree**: las corridas de `conv_eval.py` y `pytest` comparten la base de test y se
  bloquean en el `TRUNCATE`. Serializalas.
- Verificación: `bash scripts/test.sh quick` por cambio; `full` al cerrar, antes del PR y después de
  mergear main (política de `AGENTS.md` → "Test tiers").

## Lo que ya está medido (y lo que no vale)

- **Piso de ruido**: dos corridas idénticas limpias → **5/14 y 6/14**; **1 escenario de 14** cambia
  (`complejo-agendar-calefont`, tres gates juntos). Causa: el clasificador/extractor es LLM. Una
  diferencia de 1 escenario **no** autoriza decir "mejoró". Para comparar versiones: N=3 por versión.
- Corrida `--live` (cliente simulado): 8/14, peor dimensión `conversational` 1,50.
- **Ninguna corrida commiteada es citable como baseline.** `baseline-2`, `live-baseline-2`, `clean-1` y
  `clean-2` llevan `dirty: sí` por el defecto #7 (el sello contaba los reportes de la corrida
  anterior), ya arreglado en `4e1446ae`. Los `.md` se dejan con su sello original: reescribirlo sería
  falsificar el reporte. **El primer run limpio posterior a ese arreglo es el primer baseline citable.**
- `conv-eval-baseline.*` (la corrida contaminada de L8) **fue borrado**: era evidencia inválida.

## Los siete defectos ya encontrados y corregidos (no los re-busques)

1. Un veredicto truncado del juez abortaba la corrida → un reintento; si falla, escenario "sin
   veredicto", nunca como puntaje.
2. `kb_miss` blando: producción **no registra evento** cuando el bot responde la oferta de
   `kb_miss_offer` sin escalar. G9 lee el texto configurado. (Hueco de fondo en `app/`: follow-up.)
3. La evidencia citada del juez se tiraba del reporte → ahora viaja con cada fila.
4. Corrida larga sin visibilidad → progreso por escenario con `flush`.
5. Reusar `--run-tag` apila corridas → el runner rechaza un tag con clientes existentes (`exit 2`).
6. `--reset` fallaba por permisos y FKs → va por conexión **admin**, 24 tablas explícitas, sin
   `CASCADE`; KB, tarifario, catálogo y técnicos sobreviven.
7. **El sello medía los reportes, no el código**: `git_state()` corría `git status --porcelain` sobre
   todo el repo, así que los reportes que dejaba la corrida anterior marcaban `dirty: sí` la
   siguiente — y con los `.md` commiteados habría sido permanente. Ahora el sello excluye el
   directorio de reporte (`4e1446ae`).

Transporte del juez: el gateway opencode-go exige header `x-opencode-session` estable + user-agent
propio; sin eso devuelve `400 MissingSessionID`.

## Decisiones tomadas (ya no están abiertas)

1. **Corte del PR**: tres PRs encadenados, medidos en L10 — 2.577 / 965 / 3.185 líneas autoradas. Los
   tres pasan la guía de ~400 líneas y se entregan con `size:exception`: un pase honesto de corte no
   encontró una división más fina que no separe un script de sus tests.
2. **Qué se commitea de `odd/evals/`**: el `.md` sí (reporte + transcripción), el JSON no
   (`odd/evals/*.json` quedó en `.gitignore`), y `conv-eval-baseline.*` borrado.

## Trabajo pendiente, en orden

1. **Abrir los tres PRs encadenados.** Nada está pusheado: el push y la apertura son decisión del
   owner. Las ramas de corte se arman desde la historia lineal existente, sin commits nuevos.
2. **Darle espacio al cliente simulado**: hoy `max_turns` cae en `len(turns)`, así que hay **4 turnos
   simulables en 14 escenarios**. Sin eso no se puede afirmar que el evaluador "maneja todos los
   escenarios" ni que el simulador actúa como cliente. Revisar también que no escriba como el bot.
3. **Calibración S9**: el owner puntúa a mano las 3 conversaciones de `odd/evals/calibracion-s9.md`
   (con el puntaje del juez plegado). Si discrepa sistemáticamente, se ajusta la rúbrica.
4. **Recién entonces**: correr el evaluador contra el worktree de mejoras
   (`../lumat-agent-odd-chatbot-experiencia`), N=3 por versión por el piso de ruido.

## Gotchas que costaron tiempo

- Un `| grep` sobre la salida de una corrida **se come el stderr**: un fallo de `--reset` pareció un job
  colgado. Loguear sin filtrar y grepear al final.
- Los jobs largos van con `setsid` y log en `/tmp`: un crash del wrapper no mata la corrida.
- `logger.exception` del cerebro imprime tracebacks que **no** matan la corrida (notificación de
  emergencia: Meta 401 → SMTP rechazado). No confundirlos con un fallo.
- La base de test de este worktree está en **5893**; el rol `app` no puede truncar, el admin sí.
- Un `git commit` que abre editor y queda en background deja `index.lock` huérfano en
  `.git/worktrees/<worktree>/index.lock`. Usar `GIT_EDITOR=true`; verificar con `ps` antes de borrarlo.
- `git reset --hard` está bloqueado por el guardrail del harness. Para reescribir historia: rama nueva
  + `git filter-branch --index-filter`, nunca reset destructivo.
