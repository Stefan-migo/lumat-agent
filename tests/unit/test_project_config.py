import pytest
from pydantic import ValidationError

from app.services.project_config import ProjectConfig


def test_empty_project_config_uses_defaults():
    config = ProjectConfig.model_validate({})

    assert config.instructions == ""
    assert config.tool_policy.opt_in_enabled == []


def test_unknown_tool_name_is_rejected():
    with pytest.raises(ValidationError, match="unknown.tool"):
        ProjectConfig.model_validate({"tool_policy": {"opt_in_enabled": ["unknown.tool"]}})
