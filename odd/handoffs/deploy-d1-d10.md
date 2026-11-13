# Deploy de los diez D — runbook

Preparado el 2026-11-13 sobre `main` = `b92f5d3a`. **No ejecutado.** Este documento es el plan; el
deploy lo decide y lo corre el owner.

## Qué entra

Diez defectos del análisis del corpus, más los stickers del panel, más un arreglo de imagen que
destapó esta misma preparación.

| PR | Qué |
|---|---|
| #806 | D1 ficha del caso, D5 linaje de casos, D7 quién decide el gasto |
| #807 | D2 pregunta adosada a un dato, D8 paso de cotización |
| #808 | D9 clasificador multi-tema y rescate de `unknown` |
| #809 | D6 compromisos con vencimiento |
| #810 | D4 transcripción local de audios nuevos |
| #811 | Stickers en el hilo del panel |
| #812 | D10 detección de hilos apagados y compromisos vencidos |
| #813 | `infra/Dockerfile.api`: `ffmpeg` + `libgomp1` (ver abajo) |

## Hallazgo que bloquea el deploy si no entra

`infra/Dockerfile.api` **no instalaba `ffmpeg`**, y el código lo necesita desde antes de este
release:

- `app/services/audio_format.py:38,98` usa `ffprobe`/`ffmpeg` para normalizar el audio que sube un
  operador. En la imagen desplegada eso lanza `AudioNormalizationError`.
- `app/services/transcription.py` usa `ffprobe` para medir la duración antes de transcribir. Sin el
  binario, **cada audio entrante fallaría, se contaría como intento y se retiraría a los tres** — el
  mismo modo de falla silencioso que la verificación independiente bloqueó, mudado de lugar.

Los tests no lo vieron porque CI instala `ffmpeg` (`.github/workflows/tests.yml:95`) y la imagen no.
El arreglo agrega `ffmpeg` (trae `ffprobe`) y `libgomp1` (ctranslate2 lo necesita para cargar
`libgomp.so.1`).

## Antes de empezar

```bash
cd /opt/lumat && sudo -u deploy git fetch origin main
sudo -u deploy git log --oneline -1        # debe ser el merge del PR de deploy-prep
bash scripts/test.sh shape origin/main      # informativo: qué superficies toca el release
```

- [ ] `main` local del VPS en el commit a desplegar.
- [ ] Un dump reciente de la base (el deploy de este release toca cuatro migraciones).
- [ ] Egress a `huggingface.co` disponible: la primera transcripción baja el modelo (~500 MB, ver
      más abajo).

## Versión y tag

`pyproject.toml` está en `2026.11.7`. Este release es **`2026.11.8`**.

El árbol a desplegar es `b92f5d3a`: diez defectos, stickers y el arreglo de imagen.

```bash
cd /opt/lumat
sudo -u deploy git checkout main
# editar pyproject.toml: [project] version = "2026.11.8"
sudo -u deploy git add pyproject.toml
sudo -u deploy git commit -m "release: 2026.11.8"
sudo -u deploy git push origin main
sudo -u deploy git tag -a v2026.11.8 -m "Release v2026.11.8"
sudo -u deploy git push origin v2026.11.8
```

## Deploy

```bash
cd /opt/lumat
sudo -u deploy git fetch origin main && sudo -u deploy git checkout v2026.11.8
GIT_SHA="$(sudo -u deploy git rev-parse --short HEAD)"
sudo -u deploy env GIT_SHA="$GIT_SHA" docker compose --project-name lumat -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml config >/tmp/lumat-compose-config.yml
sudo -u deploy docker build -f infra/nginx/Dockerfile -t lumat-nginx:prod .
sudo -u deploy env GIT_SHA="$GIT_SHA" docker compose --project-name lumat -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml up -d --build
sudo -u deploy docker compose --project-name lumat -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml exec -T nginx nginx -t
```

El `--build` ahora compila una imagen más grande: `ffmpeg` arrastra códecs. Esperá varios minutos y
mirá el espacio en disco antes (`df -h /`), porque el build anterior queda como imagen huérfana hasta
que se pode.

## Migraciones — cuatro de una vez

`db/migrate.sh` corre automáticamente dentro del contenedor del api antes de uvicorn. Re-ejecutarlo
para probar idempotencia y ver el resultado:

```bash
sudo -u deploy docker compose --project-name lumat -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml exec -T api sh -c \
  'DATABASE_URL=postgresql://lumat:$POSTGRES_PASSWORD@db:5432/lumat db/migrate.sh'
```

Las cuatro —`064_conversation_turn_count`, `065_case_ficha`, `066_commitments`,
`067_message_transcript`— se aplican **solas** al arrancar el contenedor, antes de uvicorn, así que la
corrida explícita de arriba las va a mostrar como `skip ... (already applied)` y terminar en
`migrations up to date`. Eso es lo esperado: prueba idempotencia, no aplicación. Para confirmar que
aplicaron, mirá `schema_migrations` (el bloque de abajo). Las cuatro son **aditivas**: crean columnas,
una tabla y un índice; no reescriben ni borran una sola fila.

Verificación del esquema, después:

```bash
sudo -u deploy docker compose --project-name lumat -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml exec -T db psql -U lumat -d lumat -tAc \
  "select version from schema_migrations order by version desc limit 4;"
# esperado: 067_message_transcript, 066_commitments, 065_case_ficha, 064_conversation_turn_count
```

## Seed

```bash
sudo -u deploy docker compose --project-name lumat -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml exec -T api db/seed.sh
```

Idempotente, primer seed gana. Los ajustes nuevos (`transcription.*`, `followup.idle_*`) no necesitan
seed: tienen default en código.

## Crons nuevos

Dos, ambos documentados en `docs/ops.md`:

```bash
( crontab -l 2>/dev/null; echo '*/5 * * * * /usr/bin/docker exec lumat-api-1 python -m app.ops.transcribe >> /home/deploy/lumat-transcribe.log 2>&1' ) | crontab -
( crontab -l 2>/dev/null; echo '*/5 * * * * /usr/bin/docker exec lumat-api-1 python -m app.ops.followup >> /home/deploy/lumat-followup.log 2>&1' ) | crontab -
crontab -l
```

Con las banderas apagadas (el default) ninguno de los dos le escribe a un cliente, pero **no hacen lo
mismo**:

- `transcribe` es un no-op completo: imprime `Transcription disabled; processed 0 audio message(s)` y
  no toca la base.
- `followup` **sí escribe**: registra los eventos `idle_thread` y `commitment_overdue` en
  `conversation_events`. Un contador distinto de cero en `lumat-followup.log` no es un mensaje
  enviado, es el detector trabajando.

## Smoke obligatorio

```bash
curl -fsS https://agente.lumat.cl/health
curl -fsS "https://agente.lumat.cl/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=<VERIFY_TOKEN>&hub.challenge=123"
sudo -u deploy /opt/lumat/infra/monitor.sh && echo monitor=OK
```

`/health` debe devolver `{"status":"ok","version":"2026.11.8","commit":"<sha>"}`.

Y las dos comprobaciones que sólo existen por este release:

```bash
# ffprobe y OpenMP presentes EN LA IMAGEN
sudo -u deploy docker compose --project-name lumat -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml exec -T api sh -c 'ffprobe -version | head -1; python -c "import ctranslate2, faster_whisper; print(\"whisper ok\")"'
# esquema al día y la tabla nueva existiendo
sudo -u deploy docker compose --project-name lumat -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml exec -T db psql -U lumat -d lumat -tAc \
  "select count(*) from commitments;"
```

## Panel — checklist §2.1.2

Además del checklist completo, dos cosas de este release:

- [ ] Un hilo con **sticker** entrante lo muestra como sticker, sin burbuja y sin enlace de descarga.
- [ ] Un hilo con **nota de voz** sigue mostrando el reproductor (sin cambios) y, con la bandera
      apagada, el bot sigue derivando como antes.

## Encender después, en este orden

**Transcripción.** Baja el modelo la primera vez y consume RAM de forma permanente.

1. `transcription.enabled = true` (panel, sección de ajustes).
2. Esperar el primer barrido: baja ~500 MB a `embed-cache` (`/home/appuser/.cache/huggingface`, el
   único camino escribible de la imagen). Puede tardar varios minutos; el barrido siguiente ya es
   rápido.
3. Verificar: `docker compose exec api du -sh /home/appuser/.cache`, y `lumat-transcribe.log` con
   `Processed N audio message(s)` con N > 0.
4. Enviar una nota de voz de prueba desde un teléfono y confirmar que el bot la contesta por su
   contenido.

**Seguimiento.** Cuesta por mensaje y exige plantilla aprobada por Meta.

1. Hacer aprobar la plantilla en Meta.
2. `followup.idle_template_name = "<nombre aprobado>"`.
3. `followup.idle_enabled = true`.
4. Mirar `lumat-followup.log` y los eventos `idle_thread` / `commitment_overdue` antes de encender:
   te dicen cuántos hilos y cuántos compromisos hay.

## Rollback

El código vuelve con `git checkout v2026.11.7` y `up -d --build`. **Las migraciones no se revierten**:
son aditivas, así que el esquema queda por delante del código y el código viejo las ignora. El
`-- Rollback:` de cada archivo existe para el caso contrario (revertir esquema con el código nuevo).

Si el build falla por espacio, `docker image prune -f` antes de reintentar.

## Después

Agregar la fila del release a la tabla de §2.9 con: tag, commit, fecha, operador, resultados de smoke,
rollback disponible e incidentes. Y anotar si las dos banderas quedaron apagadas o encendidas.
