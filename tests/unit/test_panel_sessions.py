from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from app.models import PanelSession
from app.services import panel_sessions


def test_issue_stores_only_a_hash_of_the_raw_token(monkeypatch):
    session = Mock()
    monkeypatch.setattr(panel_sessions.secrets, "token_urlsafe", lambda size: "raw-token")

    token = panel_sessions.issue(session, user_id=7, user_agent="phone")

    assert token == "raw-token"
    stored = session.add.call_args.args[0]
    assert isinstance(stored, PanelSession)
    assert stored.token_hash == panel_sessions.hash_token(token)
    assert stored.token_hash != token
    assert stored.user_id == 7
    assert stored.user_agent == "phone"


def test_resolve_rejects_expired_revoked_and_unknown_tokens():
    session = Mock()
    active = PanelSession(id=1, user_id=7, token_hash=panel_sessions.hash_token("active"), expires_at=datetime.now(timezone.utc) + timedelta(days=1))
    expired = PanelSession(id=2, user_id=7, token_hash=panel_sessions.hash_token("expired"), expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    revoked = PanelSession(id=3, user_id=7, token_hash=panel_sessions.hash_token("revoked"), expires_at=datetime.now(timezone.utc) + timedelta(days=1), revoked_at=datetime.now(timezone.utc))
    session.scalars.return_value.all.return_value = [active, expired, revoked]

    assert panel_sessions.resolve(session, "active") is active
    assert panel_sessions.resolve(session, "expired") is None
    assert panel_sessions.resolve(session, "revoked") is None
    assert panel_sessions.resolve(session, "unknown") is None


def test_rotate_revokes_old_row_and_sets_replacement_hash(monkeypatch):
    session = Mock()
    old = PanelSession(id=1, user_id=7, token_hash="old-hash", expires_at=datetime.now(timezone.utc) + timedelta(days=1))
    monkeypatch.setattr(panel_sessions.secrets, "token_urlsafe", lambda size: "new-token")

    token = panel_sessions.rotate(session, old)

    assert token == "new-token"
    assert old.revoked_at is not None
    assert old.replaced_by_hash == panel_sessions.hash_token(token)
    assert old.last_used_at is not None
    assert any(isinstance(call.args[0], PanelSession) and call.args[0].token_hash == old.replaced_by_hash for call in session.add.call_args_list)


def test_find_revoked_finds_a_previously_rotated_token():
    session = Mock()
    old = PanelSession(id=1, user_id=7, token_hash=panel_sessions.hash_token("old"), expires_at=datetime.now(timezone.utc) + timedelta(days=1), revoked_at=datetime.now(timezone.utc))
    session.scalars.return_value.all.return_value = [old]

    assert panel_sessions.find_revoked(session, "old") is old


def test_revoke_all_keeps_exactly_the_requested_row():
    session = Mock()
    panel_sessions.revoke_all(session, user_id=7, keep_id=12)

    statement = session.execute.call_args.args[0]
    assert "id !=" in str(statement)
    assert "user_id" in str(statement)
