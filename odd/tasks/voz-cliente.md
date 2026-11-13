# Voz del cliente — D4 (sólo audio)

Defecto D4 de `odd/analysis/lumatdata/03-defectos-y-mejoras.md`, **acotado por decisión del owner**:
transcripción de audio con modelo abierto local, sólo para audios nuevos, sin backfill del registro
histórico. Ni visión ni video en este corte.

## Specs

**S1 · D4 — una nota de voz deja de sacar al bot de la conversación.**
«Causa: `MEDIA_EVIDENCE_TYPES` (image, video, audio, document, sticker) dispara handoff
(`handoff_gate.py:42-44`). No hay transcripción de audio en ninguna parte de `app/`». «Evidencia: **194
de 2.049** mensajes del cliente (9,5%) son adjuntos; 107 notas de voz, 50 videos, 18 stickers. **27 de
34** conversaciones reales tocan una puerta que saca al bot de la conversación».

**S2 · Sólo audios nuevos, y sólo audio.**
Decisión del owner: «solo para nuevo audios. no es necesario trabscribir todos los audios del registro
de whatsapp». El histórico del corpus no se toca. Imagen, video y sticker siguen derivando como hoy:
la visión queda fuera de este corte.

**S3 · Modelo abierto, local, sin proveedor.**
Decisión del owner: «me parece bien implementar un whisper para la transcripcion de audios. seria mejor
aun con un modelo abierto que corra localmente». `faster-whisper` (Whisper sobre CTranslate2), CPU,
int8. Sin API key, sin costo por mensaje.

**S4 · La transcripción no puede frenar al cliente.**
Corre fuera del camino del webhook: un audio largo no puede retrasar la respuesta. El modelo se carga
de forma perezosa y los tests nunca lo cargan.

## Decisiones de diseño

- **D1 · El transcript es un dato del mensaje, no un reemplazo del texto.** Columna nueva
  `messages.transcript`; el texto original del mensaje no se reescribe nunca.
- **D2 · Seam inyectable.** La carga del modelo se hace una sola vez y es reemplazable, igual que
  `kb._embedder`, porque una suite que intente bajar un modelo se cuelga — ya nos pasó con fastembed.
- **D3 · Bandera apagada por defecto.** `transcription.enabled = false`: el deploy decide cuándo
  encenderla. Con la bandera apagada, el barrido no hace nada y no hay cambio de comportamiento.
- **D4 · Ventana acotada en el tiempo, no backfill.** El barrido sólo toma audios con menos de
  `transcription.window_days` días (por defecto 7), así el registro histórico no se transcribe por
  accidente y a la vez un worker caído un día se recupera.
- **D5 · Un audio con transcript ya no es evidencia que deriva.** Mientras el audio no tenga
  transcript, el comportamiento de hoy se mantiene intacto.

## Tasks

| ID | Specs | Route | Commit |
|---|---|---|---|
| T1 | S1, S2, D1 | Migración `067_message_transcript.sql` (`messages.transcript`, `transcript_at`, `transcript_attempts`) + modelo | `feat(db):` propio (item 1) |
| T2 | S3, S4, D2, D3 | `app/services/transcription.py`: modelo perezoso, seam, ajustes, `transcribe_message` | `feat(voice):` |
| T3 | S4, D4 | Barrido `app/ops/transcribe.py` sobre el patrón «buscar filas, actuar, registrar» | `feat(voice):` |
| T4 | S1, D5 | `handoff_gate`: un audio con transcript no deriva; su transcript es el texto del turno | `feat(voice):` |

## Log

**L1 — pedido del owner (verbatim).**

```
ok estoy de acuerdo con todo. excepto D4. me parece bien implementar un whisper para la transcripcin
de audios. seria mejor aun con un modelo abierto que corra localmente. pero solo para nuevo audios. no
es necesario trabscribir todos los audios del registro de whatsapp.
```
