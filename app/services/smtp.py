"""SMTP connection settings and credential storage shared by the email senders.

The connection settings are ordinary KV settings (`notify.smtp_*`); the password
is an encrypted `panel_secrets` row, following the same pattern as
`app/services/model_secrets.py` (keyed upsert + audit + masked status, and the
plaintext never leaves this module except through `get_smtp_password`).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import PanelSecret
from app.services import crypto
from app.services.audit import record_audit
from app.services.settings import (
    DEFAULT_SMTP_FROM,
    DEFAULT_SMTP_HOST,
    DEFAULT_SMTP_PORT,
    DEFAULT_SMTP_TLS,
    DEFAULT_SMTP_USER,
    get_setting,
)

SMTP_PASSWORD_KEY = "smtp_password"
TLS_MODES = ("none", "starttls", "ssl")


@dataclass(frozen=True)
class SmtpConfig:
    host: str
    port: int
    from_address: str
    user: str
    password: str | None
    tls: str


def _port(session: Session) -> int:
    """A stored port outside 1..65535 (or non-numeric) falls back to the default."""
    try:
        port = int(get_setting(session, "notify.smtp_port", default=DEFAULT_SMTP_PORT))
    except (TypeError, ValueError):
        return DEFAULT_SMTP_PORT
    return port if 1 <= port <= 65535 else DEFAULT_SMTP_PORT


def _tls(session: Session) -> str:
    mode = get_setting(session, "notify.smtp_tls", default=DEFAULT_SMTP_TLS)
    return mode if mode in TLS_MODES else DEFAULT_SMTP_TLS


def _mask(value: str) -> str:
    return "…" + value[-4:] if len(value) >= 4 else "…"


def load_smtp_config(session: Session) -> SmtpConfig:
    """Resolve the full SMTP configuration for one send."""
    return SmtpConfig(
        host=get_setting(session, "notify.smtp_host", default=DEFAULT_SMTP_HOST),
        port=_port(session),
        from_address=get_setting(session, "notify.smtp_from", default=DEFAULT_SMTP_FROM),
        user=get_setting(session, "notify.smtp_user", default=DEFAULT_SMTP_USER) or "",
        password=get_smtp_password(session),
        tls=_tls(session),
    )


def get_smtp_password(session: Session) -> str | None:
    row = session.scalar(select(PanelSecret).where(PanelSecret.key == SMTP_PASSWORD_KEY))
    return crypto.decrypt(row.ciphertext, row.nonce) if row else None


def smtp_password_status(session: Session) -> dict[str, bool | str]:
    """Panel-facing status: whether a password is stored, and its masked tail."""
    password = get_smtp_password(session)
    if password:
        return {"configured": True, "masked": _mask(password)}
    return {"configured": False, "masked": ""}


def set_smtp_password(
    session: Session,
    password: str,
    actor: str,
    *,
    updated_by: int | None = None,
) -> None:
    ciphertext, nonce = crypto.encrypt(password)
    session.execute(
        insert(PanelSecret)
        .values(key=SMTP_PASSWORD_KEY, ciphertext=ciphertext, nonce=nonce, updated_by=updated_by)
        .on_conflict_do_update(
            index_elements=[PanelSecret.key],
            set_={
                "ciphertext": ciphertext,
                "nonce": nonce,
                "updated_by": updated_by,
                "updated_at": func.now(),
            },
        )
    )
    record_audit(
        session,
        actor=actor,
        action="smtp_password.set",
        entity="panel_secret",
        entity_id=SMTP_PASSWORD_KEY,
        after={"source": "panel"},
    )


def clear_smtp_password(session: Session, actor: str) -> None:
    session.execute(delete(PanelSecret).where(PanelSecret.key == SMTP_PASSWORD_KEY))
    record_audit(
        session,
        actor=actor,
        action="smtp_password.clear",
        entity="panel_secret",
        entity_id=SMTP_PASSWORD_KEY,
        after={"source": "none"},
    )
