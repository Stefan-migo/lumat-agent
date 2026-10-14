"""Validation ping for candidate DeepSeek API keys."""

import httpx

DEEPSEEK_MODELS_URL = "https://api.deepseek.com/models"


class InvalidApiKeyError(Exception):
    """The provider rejected the candidate key as unauthorized."""


class KeyValidationUnavailableError(Exception):
    """The provider could not validate the candidate key."""


def validate_deepseek_key(key: str) -> str:
    """Return ``valid`` or ``no_balance`` after a bounded provider ping."""
    try:
        response = httpx.get(
            DEEPSEEK_MODELS_URL,
            headers={"Authorization": f"Bearer {key}"},
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        raise KeyValidationUnavailableError from exc

    if response.status_code == 200:
        return "valid"
    if response.status_code == 402:
        return "no_balance"
    if response.status_code == 401:
        raise InvalidApiKeyError
    raise KeyValidationUnavailableError
