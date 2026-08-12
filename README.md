# LumatAgent

AI WhatsApp assistant for Lumat (gasfitería, Chile).

Hito 1 — Setup + WhatsApp operativo: a secure server plus a WhatsApp bot operating
with real Lumat customers (webhook ingestion, conversation engine, customer records,
expert KB, emergency detection, human handoff, admin panel).

Project status: in construction (SDD change `hito-1-setup-whatsapp`). Batch 0
delivers the repo scaffold, the FastAPI app factory with environment-only config,
and the webhook verify handshake + HMAC signature gate.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)

## Quickstart

```bash
uv sync                       # install dependencies + dev tools into .venv
uv run pytest                 # run the test suites
```

All secrets come from environment variables only (design SH-2 — never commit them):

```bash
export APP_SECRET=your-webhook-secret          # Meta webhook HMAC secret
export VERIFY_TOKEN=your-verify-token          # GET handshake token (hub.verify_token)
export DATABASE_URL=postgresql://app:app@localhost:5432/app
export OPENAI_API_KEY=sk-...                   # chat + embeddings (used from T3.x)
export META_ACCESS_TOKEN=...                   # Meta Cloud API token (used from T3.x)
export META_PHONE_NUMBER_ID=...                # WhatsApp Business phone number id
```

A missing required variable fails the boot with a clear error (fail fast, never
half-configured).

```bash
uv run uvicorn app.main:app --port 8000
```

## Prove it — Batch 0 (webhook verify + signature)

With the server running on `127.0.0.1:8000`:

```bash
# Health check -> {"status":"ok","version":"0.1.0"}
curl http://127.0.0.1:8000/health

# GET verify handshake: correct token -> 200 with the exact challenge
curl "http://127.0.0.1:8000/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=challenge-123"
# -> challenge-123

# GET with wrong token -> 403
curl -o /dev/null -w "%{http_code}\n" \
  "http://127.0.0.1:8000/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=WRONG&hub.challenge=x"
# -> 403

# POST with valid HMAC-SHA256 signature -> 200
BODY='{"object":"whatsapp_business_account","entry":[]}'
SIG="sha256=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$APP_SECRET" | awk '{print $2}')"
curl -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8000/webhook/whatsapp \
  -H "Content-Type: application/json" -H "X-Hub-Signature-256: $SIG" -d "$BODY"
# -> 200

# POST with a bad signature -> 403 (payload dropped)
curl -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8000/webhook/whatsapp \
  -H "X-Hub-Signature-256: sha256=$(printf 'x%.0s' {1..64})" -d "$BODY"
# -> 403
```

The signature is computed over the exact raw request body (never a re-parsed
payload). Requests with a missing, malformed, or wrong signature are rejected
with 403 and dropped before any processing (spec WH-2). Accepted POSTs return
200 immediately; payload persistence arrives with the messages table (T2.2).
