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
