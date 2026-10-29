"""Classify recorded provider calls when the post-turn capture node is in play."""
from app.chat.assistant.memory_capture import _CAPTURE_PROMPT
from app.services.prompts import load

CAPTURE_SYSTEM = load(_CAPTURE_PROMPT)


def planner_only(calls):
    """Drop the post-turn memory-capture call; it is not a planner step."""
    return [call for call in calls if (call.get("messages") or [{}])[0].get("content") != CAPTURE_SYSTEM]
