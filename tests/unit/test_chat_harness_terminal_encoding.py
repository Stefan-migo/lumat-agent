"""The manual harness must survive a terminal that hands it mangled bytes.

The api container ships no locale, so Python can decode typed input with the
POSIX charset and ``surrogateescape``: a typed ``ñ`` arrives as two lone
surrogates (``\\udcc3\\udcb1``). psycopg cannot encode a surrogate, so a single
bad character killed the whole session with a 20-line SQLAlchemy traceback —
observed twice, typing "ñuñoino 568" into a live conversation.

``_fix_encoding`` rebuilds the bytes the terminal actually sent and decodes them
as UTF-8, degrading to U+FFFD when those bytes are genuinely invalid, so the
worst case is one ugly turn instead of a dead harness.
"""

import sys
from pathlib import Path

# `scripts/` is not a package; the integration suite imports it the same way.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from chat_harness import _fix_encoding  # noqa: E402


def test_surrogates_from_a_posix_charset_are_recovered_as_utf8():
    mangled = "Ñuñoa 568".encode("utf-8").decode("ascii", "surrogateescape")

    assert "\udcc3" in mangled
    assert _fix_encoding(mangled) == "Ñuñoa 568"


def test_plain_ascii_is_untouched():
    assert _fix_encoding("hola, buenas") == "hola, buenas"


def test_invalid_bytes_degrade_to_replacement_instead_of_raising():
    mangled = b"\xff".decode("ascii", "surrogateescape")

    fixed = _fix_encoding(mangled)

    assert fixed == "\ufffd"
    fixed.encode("utf-8")  # what psycopg does; a lone surrogate raises here
