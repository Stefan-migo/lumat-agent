"""Deterministic verification gate for observable assistant effects."""

import json
from collections.abc import Callable, Iterable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.services import llm

EFFECT_TOOLS: frozenset[str] = frozenset(
    {
        "memory.update",
        "memory.delete",
        "automation.create_rule",
        "project.create",
        "project.rename",
        "project.archive",
        "project.merge",
    }
)


def verification_required(
    *, dispatched_tools: Iterable[str], explicit: bool = False, handoff: bool = False
) -> tuple[bool, str]:
    """Return whether verification is required and a stable reason code.

    Precedence is effect-tool, then explicit request, then handoff, then not-required.
    Only dispatched tool identifiers and trusted boolean signals are considered.
    """
    if EFFECT_TOOLS.intersection(dispatched_tools):
        return True, "effect-tool"
    if explicit:
        return True, "explicit"
    if handoff:
        return True, "handoff"
    return False, "not-required"


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["confirmed", "failed", "unverifiable"]
    reason: str = Field(max_length=240)


def build_verifier_messages(criterion: str, steps: list[dict], evidence: list[dict]) -> list[dict]:
    """Build a fresh, deliberately context-free verifier request."""
    # ponytail: whitelist only fields needed to judge the effect; never serialize ambient state.
    payload = {
        "criterion": criterion,
        "steps": [{"tool": item.get("tool"), "arguments": item.get("arguments", {}),
                   "result": item.get("result")} for item in steps],
        "evidence": evidence,
    }
    return [
        {"role": "system", "content": (
            'Independently judge the criterion using only supplied evidence. Return JSON exactly: '
            '{"status":"confirmed|failed|unverifiable","reason":"short explanation"}. '
            "You may request at most two read-only tools from the supplied tool catalog."
        )},
        {"role": "user", "content": json.dumps(payload, sort_keys=True, separators=(",", ":"))},
    ]


def _client_text(completion) -> str:
    try:
        return str(completion.choices[0].message.content or "")
    except (AttributeError, IndexError, TypeError):
        return ""


def run_verification(
    *, criterion: str | None, steps: list[dict], evidence: list[dict], client=None,
    tool_executor: Callable | None = None,
) -> VerificationResult:
    if not isinstance(criterion, str) or not criterion.strip():
        return VerificationResult(status="unverifiable", reason="no-observable-criterion")

    from app.chat.assistant.tools.registry import TOOL_REGISTRY, get_tool

    # Delegation's read-only boundary is the tool registry classification plus an explicit
    # whitelist. Memory tools are excluded because this isolated API has no trusted thread scope.
    allowed = frozenset(
        name for name, definition in TOOL_REGISTRY.items()
        if definition.read_only and not name.startswith("memory.")
    )
    if client is None:
        from app.chat.assistant.nodes import _assistant_client
        client = _assistant_client()
    messages = build_verifier_messages(criterion.strip(), steps, evidence)
    tools = [
        {"type": "function", "function": {"name": name, "parameters": definition.schema()}}
        for name, definition in TOOL_REGISTRY.items() if name in allowed
    ]
    try:
        completion = client.chat.completions.create(
            model=getattr(llm.get_settings(), "assistant_chat_model", llm.CHAT_MODEL),
            messages=messages, temperature=0, tools=tools, tool_choice="auto",
        )
        message = completion.choices[0].message
        calls = list(getattr(message, "tool_calls", None) or [])
        if len(calls) > 2:
            return VerificationResult(status="failed", reason="read-only-step-limit-exceeded")
        if calls:
            if tool_executor is None:
                return VerificationResult(status="unverifiable", reason="tool-executor-unavailable")
            parsed_calls = []
            for call in calls:
                name = call.function.name
                if name not in allowed or not get_tool(name).read_only:
                    return VerificationResult(status="failed", reason="read-only-tool-refused")
                try:
                    arguments = json.loads(call.function.arguments or "{}")
                except (TypeError, ValueError):
                    return VerificationResult(status="unverifiable", reason="malformed-tool-call")
                parsed_calls.append((call, name, arguments))
            messages.append({
                "role": "assistant",
                "tool_calls": [
                    {"id": call.id, "type": "function", "function": {
                        "name": name, "arguments": json.dumps(arguments, separators=(",", ":"))
                    }} for call, name, arguments in parsed_calls
                ],
            })
            for call, name, arguments in parsed_calls:
                try:
                    result = tool_executor(name, arguments)
                except Exception:
                    return VerificationResult(status="unverifiable", reason="read-only-tool-failed")
                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "content": json.dumps(result, default=str, sort_keys=True)})
            completion = client.chat.completions.create(
                model=getattr(llm.get_settings(), "assistant_chat_model", llm.CHAT_MODEL),
                messages=messages, temperature=0, tools=tools, tool_choice="none",
            )
        try:
            data = json.loads(_client_text(completion))
            result = VerificationResult.model_validate(data)
            return result.model_copy(update={"reason": result.reason[:240]})
        except Exception:
            return VerificationResult(status="unverifiable", reason="malformed-verifier-response")
    except Exception:
        return VerificationResult(status="unverifiable", reason="malformed-verifier-response")
