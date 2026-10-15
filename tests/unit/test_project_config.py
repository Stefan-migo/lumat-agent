import pytest
from pydantic import ValidationError

from app.services.project_config import ProjectConfig

OPT_IN_TOOLS = {
    "web.search",
    "web.fetch",
    "automation.create_rule",
    "project.create",
    "project.rename",
    "project.archive",
    "project.merge",
}


def test_empty_project_config_uses_defaults():
    config = ProjectConfig.model_validate({})

    assert config.instructions == ""
    assert set(config.tool_policy.opt_in_enabled) == OPT_IN_TOOLS
    assert config.skills == []


def test_unknown_tool_name_is_rejected():
    with pytest.raises(ValidationError, match="unknown.tool"):
        ProjectConfig.model_validate({"tool_policy": {"opt_in_enabled": ["unknown.tool"]}})


@pytest.mark.parametrize("skill", [
    {"name": " ", "description": "Description", "body": "Body"},
    {"name": "name", "description": "  ", "body": "Body"},
    {"name": "name", "description": "Description", "body": "\n"},
])
def test_blank_project_skill_fields_are_rejected(skill):
    with pytest.raises(ValidationError):
        ProjectConfig.model_validate({"skills": [skill]})


def test_duplicate_project_skill_names_are_rejected():
    skill = {"name": "same", "description": "Description", "body": "Body"}

    with pytest.raises(ValidationError, match="Duplicate project skill name"):
        ProjectConfig.model_validate({"skills": [skill, skill]})
