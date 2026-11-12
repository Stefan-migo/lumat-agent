from app.chat.assistant.tools.registry import TOOL_REGISTRY
from scripts.probe_assistant_tools import ARGUMENT_FIXTURES, SKIP_REASONS


def test_artifact_pdf_accepts_a_probe_fixture_case():
    fixture = {
        "filename": "probe.pdf",
        "title": "Probe report",
        "sections": [{"heading": "Probe", "body": "probe"}],
    }
    TOOL_REGISTRY["artifact.pdf"].args_model.model_validate(fixture)


def test_project_file_write_tools_have_real_probe_fixtures():
    assert ARGUMENT_FIXTURES["project_file.save"] == {"filename": "probe.md", "content": "probe"}
    assert ARGUMENT_FIXTURES["project_file.update"] == {"file_id": 1, "content": "probe updated"}


def test_every_registered_tool_has_a_valid_fixture_or_named_skip_reason():
    registered = set(TOOL_REGISTRY)
    covered = set(ARGUMENT_FIXTURES) | set(SKIP_REASONS)

    assert covered == registered
    assert not (set(ARGUMENT_FIXTURES) & set(SKIP_REASONS))
    assert all(reason.strip() for reason in SKIP_REASONS.values())
    for name, arguments in ARGUMENT_FIXTURES.items():
        TOOL_REGISTRY[name].args_model.model_validate(arguments)
