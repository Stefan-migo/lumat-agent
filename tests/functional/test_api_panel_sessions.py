"""Unauthenticated device-session endpoints retain JSON 401 auth semantics."""

import pytest


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/panel/api/sessions"),
        ("post", "/panel/api/sessions/1/revoke"),
        ("post", "/panel/api/sessions/revoke-all"),
    ],
)
def test_device_session_endpoints_require_json_auth_without_redirect(client, method, path):
    response = getattr(client, method)(path, follow_redirects=False)

    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}
    assert response.headers["content-type"].startswith("application/json")
    assert "location" not in response.headers
