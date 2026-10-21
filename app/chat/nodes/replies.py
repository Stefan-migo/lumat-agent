"""S8: deterministic reply texts resolved from settings (`reply.texts`).

Booking, appointment management, handoff and the capture steps answer with fixed
wording: no model, no prompt, no cost gate. The defaults live in
`app/services/settings.py`; this module renders the configured text, filling the
slots that text declares and nothing else, so a text that drops `{{fecha}}` is
not handed a value it will never use.
"""

from __future__ import annotations

from app.services import prompts


def render_reply(texts: dict[str, str], key: str, **values: str) -> str:
    """Render one configured reply, filling only the slots its text declares."""
    text = texts[key]
    return prompts.render_text(
        text, **{slot: values[slot] for slot in prompts.placeholders(text)}
    )
