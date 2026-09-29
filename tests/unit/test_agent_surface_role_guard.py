from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.models import UserRole
from app.panel.api.deps import AGENT_SURFACE_ROLES, require_agent_surface_json


@pytest.mark.parametrize("role", list(UserRole))
def test_agent_surface_guard_allows_every_panel_role(role):
    user = SimpleNamespace(role=role)
    assert require_agent_surface_json(user) is user


def test_agent_surface_guard_denies_roles_outside_declared_set():
    with pytest.raises(HTTPException) as error:
        require_agent_surface_json(SimpleNamespace(role=SimpleNamespace(value="future-role")))
    assert error.value.status_code == 403


def test_agent_surface_roles_cover_every_current_panel_role():
    assert AGENT_SURFACE_ROLES == {role.value for role in UserRole}
