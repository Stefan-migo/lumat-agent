# LumatAgent

AI WhatsApp assistant for Lumat (gasfitería, Chile).

Hito 1 — Setup + WhatsApp operativo: a secure server plus a WhatsApp bot operating
with real Lumat customers (webhook ingestion, conversation engine, customer records,
expert KB, emergency detection, human handoff, admin panel).

## Status

Feature work for `hito-1-setup-whatsapp` is complete. Its two remaining tasks are
operational and blocked on the client, not on code:

- **T2.1** — Meta Cloud API onboarding (WABA, Phone Number ID, permanent token,
  utility template `emergency_alert`) waits on client credentials.
- **T7.3** — go-live on the dedicated prepago number waits on T2.1.

Later milestones are verified PASS and archived under `openspec/changes/archive/`:
`hito-2-complete` (human inbox), `hito-3-scheduling-notifications`, and
`hito-4-automations-chat-pwa`, alongside the panel and UI changes.

- Deploy, hardening, and runbooks: `docs/ops.md`, `docs/hardening.md`
- Test suite and spec-to-test traceability: `tests/README.md`
- Live specs and change history: `openspec/`
- Panel design authority: `web/DESIGN_SYSTEM.md`

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)

## Quickstart

```bash
uv sync                       # install dependencies + dev tools into .venv
uv run pytest                 # run the test suites — needs the pgvector test DB
                              # and DEEPSEEK_API_KEY; see tests/README.md
```

All secrets come from environment variables only (design SH-2 — never commit them).
These six are required at boot:

```bash
export APP_SECRET=your-webhook-secret          # Meta webhook HMAC secret
export VERIFY_TOKEN=your-verify-token          # GET handshake token (hub.verify_token)
export DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/lumat
export META_ACCESS_TOKEN=...                   # Meta Cloud API permanent token
export META_PHONE_NUMBER_ID=...                # WhatsApp Business phone number id
export PANEL_SESSION_SECRET=...                # signs the panel session cookie
```

The active chat provider's key is required at first use: `DEEPSEEK_API_KEY` for the
default `CHAT_PROVIDER=deepseek`, or `OPENROUTER_API_KEY` for `openrouter`
(enforced in `llm.openai_client()`). The complete local/Compose set — Postgres
credentials, assistant providers, embeddings, SMTP — is documented in
`infra/.env.example`.

A missing required variable fails the boot with a clear error (fail fast, never
half-configured).

```bash
uv run uvicorn app.main:app --port 8000
```

## Prove it — webhook verify + signature

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
with 403 and dropped before any processing (spec WH-2). Accepted POSTs are
persisted as a `received` row and processed by a background task after the 200
(specs WH-3 and WH-4).
