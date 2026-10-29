import pytest

from app.services import tukulpan


def test_user_memory_entity_uses_authenticated_owner_axis():
    assert tukulpan.user_memory_entity(7) == "user:7"


def test_visibility_target_maps_user_axis_for_positive_owner():
    assert tukulpan.visibility_target(
        "user", thread_id=42, proyecto="acme", owner_id=7
    ) == ("user", "user:7")


@pytest.mark.parametrize("owner_id", [None, 0, "7"])
def test_visibility_target_requires_positive_integer_owner(owner_id):
    with pytest.raises(ValueError, match="owner_id"):
        tukulpan.visibility_target(
            "user", thread_id=42, proyecto="acme", owner_id=owner_id
        )


def test_visibility_target_keeps_existing_axes_compatible():
    assert tukulpan.visibility_target("thread", thread_id=42, proyecto="acme") == (
        "panel", "thread:42"
    )
    assert tukulpan.visibility_target("global", thread_id=42, proyecto="acme") == (
        tukulpan.AGENT_SCOPE, "agent:acme"
    )
