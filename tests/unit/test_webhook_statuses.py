"""Unit tests for Meta delivery callback handling (statuses)."""

from app.webhook.ingest import _delivery_error


def test_delivery_error_formats_meta_nested_error_details():
    error, code = _delivery_error({
        "errors": [{
            "code": 131053,
            "title": "Media upload error",
            "error_data": {"details": "Audio could not be processed"},
        }]
    })

    assert error == "131053: Media upload error — Audio could not be processed"
    assert code == "131053"


def test_delivery_error_uses_fallback_without_errors():
    error, code = _delivery_error({})

    assert error == "Meta no informó el motivo"
    assert code is None


def test_delivery_error_caps_reason_at_2000_characters():
    error, _ = _delivery_error({
        "errors": [{"code": 1, "message": "x" * 3000}]
    })

    assert len(error) == 2000


def test_delivery_error_prefers_error_data_details_over_the_repeated_message():
    """Measured on 131053: title and message both read "Media upload error".

    The detail is the only field that names the cause, so preferring `message`
    left every audio failure with a code and no reason.
    """
    error, code = _delivery_error({
        "errors": [{
            "code": 131053,
            "title": "Media upload error",
            "message": "Media upload error",
            "error_data": {
                "details": (
                    "Audio file uploaded with mimetype as audio/ogg, however on "
                    "processing it is of type application/octet-stream."
                )
            },
        }]
    })

    assert error == (
        "131053: Media upload error — Audio file uploaded with mimetype as "
        "audio/ogg, however on processing it is of type application/octet-stream."
    )
    assert code == "131053"
