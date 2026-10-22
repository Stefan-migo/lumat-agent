# HANDOFF — ODD del modelo de configuración del chatbot

**Estado:** la rapso session cerró con handoff (`ready-for-odd`). No se creó todavía el task doc de ODD.

## Fuente de verdad

- `.rapsodia-code/sessions/ready-for-odd/2026-10-21-chatbot-config-brain/report.md`
- `.rapsodia-code/sessions/ready-for-odd/2026-10-21-chatbot-config-brain/session.md`
- Engram: topic `cortex-session/2026-10-21-chatbot-config-brain` (reporte) y `cortex-session/2026-10-21-chatbot-config-brain/decision/*` (decisiones).
- **No re-litigar** D1–D11 del `session.md`.

## Trabajo ya hecho (branch `odd/chatbot-kb`, sin PR)

| Commit | Qué |
|---|---|
| `82913132` | Contrato de reconciliación V4 ↔ repo |
| `9b7435fd` | 5 documentos de KB comercial |
| `365f3cbf` | Persona de Max + espejo `FALLBACKS` |
| `e6f91d5b` | Suite T01–T12 |
| `ea601bf2` | Tests de contrato de KB y persona |
| `415fe1ea` | Fix de conducta (captura, `persona`, voseo, keyword) |

## Próximo paso (arranque)

```bash
rapso worktree create chatbot-config-model
```

Después: crear `odd/tasks/chatbot-config-model.md` desde `report.md`, y mover la sesión de `ready-for-odd/` a `archived/` (ready-for-odd es inbox).

## Slices, en orden de dependencia

| Slice | Alcance |
|---|---|
| **F1 · Capa 1** | `tarifa.precios` con temporadas en settings; resolver por fecha `America/Santiago`; inyectar `<tarifario>` con solo precios vigentes; `coverage.communes`; duraciones y horarios; sacar `lumat-precios.md` de la KB de cliente |
| **F2 · Capa 2** | Copy a settings: los 6 mensajes + `greeting_short` (API + UI), preguntas de captura, textos de agenda/cancelación/derivación. **Extiende** `odd/tasks/chatbot-message-catalog.md` y reutiliza `chatbot-first-turn-greeting.md` y `ss5-tone-and-messages.md` |
| **F3 · Capa 3** | Objeto de conducta con opciones cerradas: orden de campos, `redaccion: llm|plantilla`, `max_preguntas_por_mensaje`, reglas de derivación; validación al guardar |
| **F4 · Conducta** | Una pregunta por mensaje, no duplicar respuesta por turno, responder preguntas durante la captura, cobertura fuera de las 7 comunas |
| **F5 · Capa 4** | Persona y protocolo de emergencia editables con versión, diff y restaurar |
| **F6 · Panel UI** | Rediseño visual, último |

## Invariantes (no configurables)

1. Gate de emergencia antes del LLM.
2. Límites de costo.
3. Consentimiento antes de reservar.
4. No inventar + `<user_input>` como dato (anti-inyección).
5. Takeover humano: el bot calla.

## Restricciones técnicas verificadas

- Strict TDD ON (`openspec/config.yaml:28,38`). Runner: `uv run pytest tests/`.
- `agent/*.md` está byte-acoplado a `prompts.FALLBACKS`; el test `tests/unit/test_prompts.py:162` falla si se desincronizan.
- Test DB por worktree: `cp ../lumat-agent/infra/.env infra/.env` y `eval "$(bash infra/test-db.sh env)"`.
- La suite depende del orden: correr `tests/unit`, `tests/integration` y `tests/functional` en invocaciones separadas.
- Pre-merge: traer `origin/main` y esperar los checks `test` + `panel`.
- No hay auto-merge.

## Harness (para probar conducta real)

```bash
docker compose -p lumat-harness -f infra/docker-compose.yml -f infra/docker-compose.harness.yml up -d
docker compose -p lumat-harness -f infra/docker-compose.yml -f infra/docker-compose.harness.yml exec -T api bash db/seed.sh
cd web && VITE_API_TARGET=http://localhost:8001 npm run dev
```

Panel en `:5173/panel/app/`, API en `:8001`, DB en `:5433`. Subir los `docs/kb/*.md` con visibilidad **cliente** (el default es `internal` y el bot no los ve). Harness: `exec api uv run python scripts/chat_harness.py --phone +56900000001`; cada teléfono es un cliente distinto.

## Pendientes (ninguno bloquea)

- Implementación: redacción default de cada pregunta, reglas de derivación activas, si el saludo se personaliza con el nombre, si `lumat-precios.md` se conserva como documento `internal`.
- De Lumat: IVA de los 4 precios, exigibilidad del 15%, matriz de garantías, documentos SEC emitibles.
