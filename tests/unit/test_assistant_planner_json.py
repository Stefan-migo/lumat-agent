"""Tolerant reader for planner JSON, pinned to the two payloads that lost a real turn."""

import json

import pytest

from app.chat.assistant.planner_json import load_planner_payload


def test_reads_plain_object_unchanged():
    payload = '{"kind":"respond","arguments":{},"summary":"Done","requires_approval":false}'

    assert load_planner_payload(payload) == {
        "kind": "respond",
        "arguments": {},
        "summary": "Done",
        "requires_approval": False,
    }


def test_escapes_raw_newline_inside_a_string():
    """Thread 79: a prose answer carried real newlines inside a JSON string."""
    payload = '{"kind":"respond","arguments":{},"summary":"Line one\n\nLine two","requires_approval":false}'

    assert load_planner_payload(payload)["summary"] == "Line one\n\nLine two"


def test_escapes_every_forbidden_control_character_inside_a_string():
    payload = '{"kind":"respond","arguments":{},"summary":"a\tb\rc\u0001d","requires_approval":false}'

    assert load_planner_payload(payload)["summary"] == "a\tb\rc\x01d"


def test_leaves_control_whitespace_outside_a_string_alone():
    payload = '{\n\t"kind": "respond",\n\t"arguments": {},\n\t"summary": "Done"\n}'

    assert load_planner_payload(payload)["summary"] == "Done"


def test_reads_first_object_when_prose_follows():
    """Thread 80: a valid object followed by an unescaped prose paragraph."""
    payload = '{"kind":"respond","arguments":{},"summary":"Done"}\n\nSí, estamos en una sesión de planificación.'

    assert load_planner_payload(payload)["summary"] == "Done"


def test_reads_first_object_when_a_second_object_follows():
    payload = '{"kind":"respond","arguments":{},"summary":"First"}\n{"kind":"respond","arguments":{},"summary":"Second"}'

    assert load_planner_payload(payload)["summary"] == "First"


def test_reads_object_inside_a_json_code_fence():
    payload = '```json\n{"kind":"respond","arguments":{},"summary":"Fenced"}\n```'

    assert load_planner_payload(payload)["summary"] == "Fenced"


def test_keeps_braces_and_escaped_quotes_inside_strings():
    payload = '{"kind":"respond","arguments":{},"summary":"a } b \\" c { d"}'

    assert load_planner_payload(payload)["summary"] == 'a } b " c { d'


def test_unreadable_answer_raises_json_decode_error():
    with pytest.raises(json.JSONDecodeError):
        load_planner_payload("not json")
