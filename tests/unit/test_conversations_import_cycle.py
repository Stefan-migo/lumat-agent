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


def test_importing_the_panel_package_does_not_load_route_modules():
    """S3: the package init must not assemble the router on a plain import.

    Every service that imported a panel serializer at module level used to drag all
    20 route modules behind it, which is what turned two serializer imports into
    production import cycles.
    """
    script = """
import sys
import app.panel.api
loaded = sorted(name for name in sys.modules if name.startswith("app.panel.api.routes"))
assert not loaded, loaded
print("PANEL_INIT_STAYS_LIGHT")
"""
    completed = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=False)

    assert completed.returncode == 0, completed.stderr
    assert "PANEL_INIT_STAYS_LIGHT" in completed.stdout


def test_dashboard_service_imports_before_panel_api_and_first_tool_call_succeeds():
    """S3: the same cold-import defect the conversation service had, second occurrence."""
    script = """
import app.services.dashboard as dashboard
from app.chat.assistant.tools.registry import execute_tool
from app.db import SessionLocal

session = SessionLocal()
try:
    result = execute_tool(session, "dashboard.summary", {"window_days": 1}, role="admin")
finally:
    session.close()
assert result["status"] == "completed", result
print("COLD_DASHBOARD_TOOL_OK")
"""
    completed = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=False)

    assert completed.returncode == 0, completed.stderr
    assert "COLD_DASHBOARD_TOOL_OK" in completed.stdout
