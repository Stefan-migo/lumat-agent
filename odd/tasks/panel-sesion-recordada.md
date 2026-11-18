# Panel session that survives the PWA

The panel session is a signed cookie with `max_age=12h` (`app/main.py:99-105`). It slides while the
operator works and expires after twelve idle hours, which is exactly the reported "al día siguiente me
pide loguearme otra vez". A PWA that is closed most of the day lives outside that window by design.

The fix is a per-device remember token the operator can revoke, not a longer cookie: a lost phone must
be cut off without deactivating the account.

## Specs

- **S1** The session must hold across the PWA being closed for "un rato o un día": reopening the app
  must not ask for credentials while that device's access is still authorized.
- **S2** Access must be revocable per device. Owner's choice, verbatim: "Token 'recordarme' por
  dispositivo (revocable)".
- **S3** Revoking a device cuts its access immediately, even if its cookie is still valid.
- **S4** Presenting a token that was already rotated (the signature of a copied cookie) revokes every
  session of that user and records the event in the audit log.
- **S5** Silent re-authentication must not bypass account state: a deactivated or locked user still
  loses access, because the user row is re-read on every request.
- **S6** The remember cookie is `HttpOnly` and `SameSite=Lax`, and it never authorizes a cross-site
  write.
- **S7** Push delivery must not depend on the panel session. Verified in this session:
  `push_subscriptions` (`user_id`, `p256dh`, `auth`, `active`) is read by `app/services/push.py`, which
  never looks at the session cookie. The reported fear ("no me llegue una notificación por no estar
  logueado") is therefore not the mechanism; what a remember token restores is the app's ability to
  re-register a subscription that the OS dropped.

## Design

- **Migration `069_panel_sessions.sql`**: `panel_sessions(id, user_id FK users ON DELETE CASCADE,
  token_hash text unique, user_agent, created_at, last_used_at, expires_at, revoked_at,
  replaced_by_hash)` plus a partial index on `(user_id)` where `revoked_at IS NULL`.
- **Token**: 32 random bytes, URL-safe; only `sha256(token)` is stored. Absolute 90-day life; rotation
  is what makes it slide.
- **Restore path**: only when the signed session has no `user_id` — the exact branch that would
  redirect to login. The deps resolve the remember cookie, rotate it, write the session keys, and the
  response persists both cookies. Never on a request that already has a session.
- **Reuse**: hashing the presented token finds a row with `revoked_at` set → every session of that user
  is revoked, the cookies are cleared, and `auth.session_reuse` is audited.
- **Endpoints**: `POST /panel/api/logout` revokes the current device; `GET /panel/api/sessions`;
  `POST /panel/api/sessions/{id}/revoke`; `POST /panel/api/sessions/revoke-all`.
- **Not doing**: `maximum-scale`, `Secure` on the cookie (the API sits behind the TLS-terminating
  nginx and the existing session cookie is `https_only=False` — parity, documented), device nicknames,
  and any push change.

## Tasks

| ID | Spec | Route | Commit |
| --- | --- | --- | --- |
| T1 | S1, S2, S4 | backend · migration 069, `PanelSession` model, `panel_sessions` service | 1 |
| T2 | S1, S3, S5, S6 | backend · silent restore in the panel deps and the realtime handshake | 1 |
| T3 | S2, S3 | backend · login/logout cookies and the device endpoints | 1 |
| T4 | S1-S6 | tests · unit, DB and API red-first | 1 |
| T5 | S2 | panel · devices section, web tests, DESIGN_SYSTEM entry | 2 |

## Log

### L1 — user request (verbatim)

Ok, necesito que revises otras cosas que son un poco más generales, pero las voy a necesitar arreglar.
Una de ellas es que Lumat debe sostener la sesión. O sea, sobre todo cuando está trabajando en PWA en
versión móvil, la sesión se sale cuando pasa un rato o un día sin entrar a la aplicación. Ya no estoy
logueado, me pide loguearme nuevamente. Y esto es peligroso o puede llegar a suceder que no me llegue
una notificación por estar, por no estar logueado

### L2 — diagnosis in this session

- `app/main.py:99-105`: `SessionMiddleware(..., max_age=12 * 60 * 60, same_site="lax", https_only=False)`.
  Starlette re-signs the cookie on every response, so the window slides with activity and expires after
  twelve idle hours.
- `app/panel/deps.py:50-70` and `app/panel/api/deps.py:32-40`: both resolve `request.session["user_id"]`
  and nothing else, so once the cookie is gone there is no silent path back.
- `app/panel/api/routes/auth.py:119-122` writes the session keys; `:154` clears them on logout. No
  persistent credential exists today.
- Push: `app/models.py:994-1005` and `app/services/push.py:14-42` deliver from stored subscriptions and
  deactivate one only when the endpoint answers 404/410. No session dependency.

### L3 — owner decision

"Token \"recordarme\" por dispositivo (revocable)" over a 30-day cookie, because a lost phone must be
revocable without deactivating the account.

### L4 — slices and evidence

- **Slice 1** `8f389bbc2`: migration `069`, `PanelSession`, `panel_sessions` service, unit tests.
- **Slice 2** `93c20192e`: shared restore, login/logout cookies, device endpoints, DB and functional tests.
- **Slice 3**: the panel section (`PanelSessions`) and the `### Configuración` amendment.

Review of the delegated backend found two defects, both fixed before the slice commit:

1. **A WebSocket handshake spent the token.** FastAPI solves a WebSocket route's dependencies with
   `response=None` (`fastapi/routing.py:783-790`), so restoring there rotated the credential and had no
   way to deliver the replacement. The browser kept a revoked token, and the next HTTP request read it
   as a copied cookie and revoked every session of the user. A non-HTTP connection now borrows the
   credential read-only; `test_a_websocket_handshake_never_consumes_the_remember_token` pins it.
2. `logout` read the cookie name from a string literal instead of the shared constant.

Gates observed: `scripts/test.sh quick` green; `scripts/test.sh db` over the new unit, integration and
functional files plus `test_h4_chat.py` → 33 passed (the existing login behaviour is preserved).

Note for the next session: `AGENTS.md` says both "a missing or stale graph is a blocker, build it
FIRST" and "the refresh runs ONCE per session, when the session closes". Two delegated writers read the
first rule, could not write under `graphify-out/` (it is outside their edit surfaces), and stopped.
The parent owns that refresh; say so in the brief.

### L5 — the full suite's verdict

`bash scripts/test.sh full` failed four tests that every focused run had passed:

- `tests/integration/test_migrations.py` — `schema_migrations` and `EXPECTED_TABLES` are exact
  inventories, so `069_panel_sessions` and `panel_sessions` belong in them. The tests were right.
- `tests/functional/test_auth.py::test_json_session_role_and_tampered_cookie_are_enforced` — it replaced
  the signed cookie with garbage and expected 401, while the client still held a remembered device, which
  is a credential. The forged-cookie assertion now runs with the remember cookie removed, so it still
  proves a forged cookie is never trusted; a second test proves the device restores and rotates despite it.
- `tests/integration/test_assistant_artifacts.py::test_artifact_pdf_saves_and_publishes_idempotently` passed
  in isolation and again on the closure run: a flake, not a regression.

### L6 — closure

- `bash scripts/test.sh full` on the final tree: exit 0, no failures (the PDF artifact test that flaked in the
  earlier run passed again).
- Native review `review-e5c07ca7c2c293e3`, risk tier **high** (`hot_path: auth`), four lenses: **approved**,
  authority acknowledged and burned. Five non-blocking advisories, recorded here as follow-ups rather than
  corrections, since the native statement forbids reopening this candidate for them:
  - `R1-001` (risk, `app/panel/deps.py:61-70`): the remember cookie is `secure=False` for parity with the
    session cookie, but it lives ninety days instead of twelve hours. The honest fix is to derive
    `secure` from the request (`X-Forwarded-Proto`) rather than from the middleware's posture.
  - `R2-001` (readability, `app/panel/deps.py:62-75`): `restore_panel_user` carries both the
    session-present reuse check and the restore path in one body.
  - `R2-002` (readability, `app/services/panel_sessions.py:31-37`): `issue` and `rotate` build the same row.
  - `R3-001` (reliability, `app/panel/deps.py:65-70`): a lost `Set-Cookie` on rotation makes the next request
    present a revoked token and clear the session. Conservative by design; worth revisiting.
  - `R4-001` (resilience, `app/panel/deps.py:70-76`): the restore path is not wrapped, so a database error
    there becomes a 500 instead of an unauthenticated answer.
