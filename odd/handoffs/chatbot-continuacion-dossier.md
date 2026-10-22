# HANDOFF — chatbot: continuar desde el dossier de decisiones

**Fecha:** 2026-10-22 · **main:** `0a0de247` (`v2026.10.6`) · **Producción:** `v2026.10.6` desplegado y verificado · **Worktree:** uno solo, sin ODD activos.

## 0. Regla de entrada (leer antes que nada)

- **El único insumo es el reporte de la sesión**, no este doc solo:
  `.rapsodia-code/sessions/ready-for-odd/2026-10-22-chatbot-decision-dossier/report.md`
- **Los 44 handoffs untracked de `odd/handoffs/` NO son backlog.** Varios están cumplidos.
- **No re-litigar:** `D1–D11` de la sesión `2026-10-21-chatbot-config-brain`, `min_sim=0.50`, los cinco invariantes de `D8`, ni `S17`.
- Antes de tocar código: leer `report.md` → `session.md` → este doc.

## 1. Estado verificado

- `main` = **`0a0de247`** = merge del PR #658, tag anotado **`v2026.10.6`**. Tracked limpio; 49 untracked (handoffs viejos + 2 PDFs de `docs/`).
- Suite por CI (`test` + `panel`) **verde** en `0a0de247`. Local: 2727 passed / 3 failed **ambientales** (`media/` de root).
- **Producción** = VPS Hostinger `179.199.148.175`, `/opt/lumat`, compose project `lumat` (`infra/docker-compose.yml` + `.prod.yml`), corriendo `v2026.10.6`. Antes estaba tres releases atrás.
- **Harness local vivo**: `lumat-harness-api-1` (8001) / `lumat-harness-db-1` (5433), con **4 documentos `customer` globales** y `tarifa.precios`. Está mejor sembrado que producción.
- **Production KB sigue con cero documentos `customer`** hasta que el owner suba los 4 de `docs/kb`.

## 2. Artefactos canónicos

| Artefacto | Dónde |
|---|---|
| Cola unificada, matriz H01–H12, unidades deduplicadas, mapa de archivos | `.rapsodia-code/sessions/ready-for-odd/2026-10-22-chatbot-decision-dossier/report.md` |
| Decisiones con rationale y alternativas | misma carpeta, `session.md` |
| Índice canónico del hilo | Engram `chatbot/thread-index` (#6748) |
| Reporte de cierre + resumen de sesión | Engram `cortex-session/2026-10-22-chatbot-decision-dossier` (#6766) / (#6767) |
| Auditoría de producción y gap de versiones | Engram `deployment/prod-state-audit-2026-10-22` (#6753), `deployment/prod-vs-main-gap` (#6758) |
| Harness y modo local-first | Engram `deployment/local-testing-harness` (#6754), `chatbot/working-mode-local-first` (#6761) |
| Release desplegado | Engram `deployment/release-2026.10.6` (#6760) |

## 3. Primer paso concreto

1. **Worktree ODD**: `../lumat-agent-odd-chatbot-backlog`, branch `odd/chatbot-backlog`.
2. Crear **`odd/tasks/chatbot-backlog.md`** desde `report.md` (tabla de slices + unidades deduplicadas + mapa de archivos). Al crearlo, mover la sesión de `ready-for-odd/` a `archived/`.
3. **S1 (saludos)** primero: no depende de ninguna decisión y ya tiene RED medido.

> El task doc va en la branch y llega a `main` por PR. No commitear los handoffs untracked.

## 4. La cola

| Slice | Alcance | RED ya medido |
|---|---|---|
| **S1 · Saludos** | `is_greeting_only` por variantes (puntuación, relleno) + despedidas. Un saludo **nunca** suma `unknown_intent`. | "Hola buenas tardes" → `intent=unknown` en `main`, medido en harness. 11 de 18 unknowns de producción son saludos. |
| **S2 · Entrada** | Detector único de pedido humano (D5): petición + rol, guarda de negación, token suelto sólo si es el mensaje entero, roles ampliados. Errores técnicos fuera del contador. Conteo consecutivo. Mensajes de plataforma de Meta no se clasifican. | Tabla de detectores medida; `_record_unknown_intent` cuenta todo; un mensaje de plataforma generó `unknown_intent` en prod. |
| **S3 · Desenlace** | Salida 3 al segundo fallo y oferta en `kb_miss` (D17, D18), contador que resetea al entender. Dos textos configurables expuestos en **tres** lugares del panel. | Transcripciones: la conversación muere en el fallo 2 y en el `kb_miss`. |
| **S4 · Instrumentación** | `kb_fidelity` usa la recuperación real (`global_only` + fallback); un resultado por turno en `state`, consumido por `respond`. | `_retrieved_chunks:316` ≠ `respond.retrieve_chunks`; doble retrieval por turno. |
| **S5 · KB de cliente** | Owner sube los 4 documentos `customer` globales; **re-medir** el desglose de handoffs. | Cero documentos `customer` en producción. |

Orden no negociable: hay archivos compartidos (`respond.py` en S3 y S4; `ingest.py` en S2 y S3).

## 5. Decisiones cerradas

- **D12** Métrica norte: conversaciones resueltas sin humano sobre atendibles. Piso de merge: **cero daño**. Costo no es restricción, se reporta.
- **D13 / D17** Salida 3 con **copy configurado, sin LLM**. Secuencia: fallo 1 reformular · fallo 2 ofrecer dos caminos · fallo 3 derivar. Contador resetea al entender. Texto en el panel.
- **D18** El **`kb_miss` también ofrece los dos caminos**. Cierra U1.
- **D15** El handoff se recupera solo: mensaje nuevo + 24 h sin actividad humana → `bot`.
- **D16** Desplegar antes de arreglar (hecho).
- **D14** Harness en `deepseek-flash` a propósito.
- **D5** Detector único determinista de pedido humano.
- **D6** cerrada por medición: consecutivo vs acumulado mueve 1 de 6 conversaciones.

## 6. Decisiones pendientes (por unidad, con evidencia)

H03 aspecto · H05 precio sin chunk · H09 suficiencia · H10 contexto · H11 ráfagas · H12 entrega transaccional + Engram #6640 · H07 corrección en captura · H08 agenda · U4 CM-4 · S10 `redaccion` · S11 señal de visita · S14 reformulación · 4 derivaciones sin lector.

**Negocio/legal (parked, depende del cliente):** IVA de los 4 precios, exigibilidad del 15%, matriz de garantías, documentos SEC.

## 7. Evidencia medida (no re-medir a mano)

- Producción vieja (`v2026.10.5`): 18 de 21 conversaciones derivadas — `unknown_intent_twice` 7 · `persona` 4 · `kb_miss` 4 · `booking_unavailable` 3 · `tool_not_whitelisted` 1. **No es baseline.**
- 18 `unknown_intent`: saludos 11, test 2, despedida 1, estado 1, numéricos 2, mensaje de plataforma 1.
- Los 4 `handoff:persona` **no** son H02: vienen del LLM sin el downgrade `is_explicit_human_request`, ausente en `v2026.10.5`.
- Detectores: el gate deriva "¿cuánto cuesta **por persona**?"; `is_explicit_human_request` deriva *"**No** quiero hablar con una persona"*; ambos pierden "quiero hablar con el **encargado**".
- Código nuevo: retrieval responde $80.000 con relleno conversacional; el saludo sigue en `unknown`.

## 8. Qué NO hacer

- **No testear en producción.** Local-first: harness, y producción sólo con algo concreto ya validado.
- **No usar el webhook del harness (8001)** para probar: ese path ejecuta `deliver_outbound` y el token de Meta es real. Usar `scripts/chat_harness.py`.
- **No tocar retrieval** (H03/H05/H09, `min_sim`, chunking) antes de S4 y de la re-medida.
- **No reabrir el LLM sin evidencia** (D13 descartó que redacte la negativa).
- **No deployar** un cambio que altere clasificación o generación sin una pasada con `deepseek-chat`.
- **No usar `--admin`**; todo a `main` por PR con `test` + `panel` verdes.

## 9. Cómo se verifica

```bash
# harness (mismo main que producción, no envía)
docker compose -p lumat-harness \
  -f infra/docker-compose.yml -f infra/docker-compose.harness.yml \
  exec api uv run python scripts/chat_harness.py --phone +56900000001

# suite completa (la fuente de verdad del CI)
uv run pytest tests/
cd web && npm test && npm run build
```

Cada slice cierra con `Risk:` explícito y commit convencional sin atribución de IA.
