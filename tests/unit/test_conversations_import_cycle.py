import subprocess
import sys


def test_conversations_service_imports_before_panel_api_and_first_tool_call_succeeds():
    script = """
import app.services.conversations as conversations
import app.panel.api.routes.conversations
from unittest.mock import patch
from app.chat.assistant.tools.registry import execute_tool

with patch.object(conversations, "list_conversations", return_value=[]):
    result = execute_tool(object(), "conversations.list", {}, role="admin")
assert result["status"] == "completed", result
print("COLD_CONVERSATIONS_TOOL_OK")
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "COLD_CONVERSATIONS_TOOL_OK" in completed.stdout
