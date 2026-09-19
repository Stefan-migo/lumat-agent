from app.chat.assistant.markup import ToolCallMarkupSanitizer, strip_tool_call_markup


def marker(payload, bars="\uff5c"):
    return f"<{bars}{payload}{bars}>"


def test_real_double_bar_tool_calls_block_is_stripped():
    bar = "\uff5c" * 2
    text = (
        "before "
        f"<{bar}tool_calls{bar}>"
        f'<{bar}invoke name="memory.read"{bar}>'
        f'<{bar}parameter name="q" string="true"{bar}>SECRETO'
        f"</{bar}parameter{bar}>"
        f"</{bar}invoke{bar}>"
        f"</{bar}tool_calls{bar}>"
        " after"
    )

    assert strip_tool_call_markup(text) == "before  after"


def test_strips_tool_calls_wrapper_with_multiline_parameters():
    bar = "\uff5c"
    text = (
        "Before "
        + marker("tool_calls", bar)
        + marker('invoke name="customers.search"', bar)
        + marker('parameter name="query" string="true"', bar)
        + "Ana\nGarcía"
        + f"</{bar}parameter{bar}>"
        + f"</{bar}invoke{bar}>"
        + f"</{bar}tool_calls{bar}>"
        + " after"
    )

    cleaned = strip_tool_call_markup(text)
    assert "Ana" not in cleaned
    assert "García" not in cleaned
    assert "tool_calls" not in cleaned


def test_strips_function_call_variants_and_ascii_markers():
    bar = "|"
    text = (
        marker("function_calls", bar)
        + marker('invoke name="one"', bar)
        + marker('parameter name="q" string="false"', bar)
        + "hidden"
        + f"</{bar}parameter{bar}>"
        + f"</{bar}invoke{bar}>"
        + f"</{bar}function_calls{bar}>"
        + "visible"
        + marker("tool_use_error", bar)
    )

    assert strip_tool_call_markup(text) == "visible"


def test_strips_bare_invoke_without_leading_delimiter_and_leftover_markers():
    bar = "\uff5c"
    text = (
        f'prefix <invoke name="customers.search"{bar}>'
        f'<parameter name="query" string="false"{bar}>Ana</{bar}parameter{bar}>'
        f'</{bar}invoke{bar}> suffix <{bar}tool_calls{bar}>'
    )

    assert strip_tool_call_markup(text) == "prefix  suffix "


def test_leaves_ordinary_text_untouched():
    text = "The pipe | and <ordinary> text are not tool calls."

    assert strip_tool_call_markup(text) == text


def test_lone_less_than_is_untouched():
    text = "ordinary < text"

    assert strip_tool_call_markup(text) == text


def test_unterminated_wrapper_strips_body_to_end():
    bar = "\uff5c"
    text = (
        "Before "
        f"<{bar}tool_calls{bar}>"
        f'<{bar}invoke name="x"{bar}>'
        f'<{bar}parameter name="q" string="true"{bar}>LEAKED BODY'
    )

    assert strip_tool_call_markup(text) == "Before "


def test_unterminated_bare_invoke_strips_body_to_end():
    bar = "\uff5c"
    text = (
        "Before "
        f'<{bar}invoke name="x"{bar}>'
        f'<{bar}parameter name="q" string="true"{bar}>LEAKED2'
    )

    assert strip_tool_call_markup(text) == "Before "


def test_streaming_sanitizer_holds_partial_markup_until_complete():
    bar = "\uff5c" * 2
    sanitizer = ToolCallMarkupSanitizer()
    chunks = [
        "Answer ",
        f"<{bar}tool_calls{bar}>",
        f'<{bar}invoke name="customers.search"{bar}>',
        f'<{bar}parameter name="query" string="true"{bar}>Ana\n',
        "García",
        f"</{bar}parameter{bar}></{bar}invoke{bar}>",
        f"</{bar}tool_calls{bar}> done",
    ]

    emitted = [sanitizer.feed(chunk) for chunk in chunks]
    emitted.append(sanitizer.flush())

    output = "".join(emitted)
    assert "SECRETO" not in output
    assert "tool_calls" not in output
    assert "invoke" not in output


def test_streaming_sanitizer_strips_bare_invoke_block():
    bar = "\uff5c"
    sanitizer = ToolCallMarkupSanitizer()

    emitted = [
        sanitizer.feed(f'prefix <{bar}invoke name="customers.search"{bar}>'),
        sanitizer.feed("hidden body"),
        sanitizer.feed(f"</{bar}invoke{bar}> suffix"),
        sanitizer.flush(),
    ]

    assert "".join(emitted) == "prefix  suffix"


def test_streaming_wrapper_close_split_preserves_later_text():
    bar = "\uff5c"
    sanitizer = ToolCallMarkupSanitizer()
    chunks = [
        f"<{bar}tool_calls{bar}>",
        f'<{bar}invoke name="x"{bar}>',
        "body",
        f"</{bar}invoke></{bar}tool_ca",
        "lls>",
        " AFTER",
    ]

    output = "".join(sanitizer.feed(chunk) for chunk in chunks) + sanitizer.flush()

    assert output == " AFTER"


def test_streaming_invoke_close_split_preserves_later_text():
    bar = "\uff5c"
    sanitizer = ToolCallMarkupSanitizer()
    chunks = [
        f'<{bar}invoke name="x"{bar}>',
        "body",
        f"</{bar}inv",
        "oke>",
        " AFTER",
    ]

    output = "".join(sanitizer.feed(chunk) for chunk in chunks) + sanitizer.flush()

    assert output == " AFTER"
