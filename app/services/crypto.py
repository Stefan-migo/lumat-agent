"""Application encryption for credentials stored in the database."""

import base64
import binascii
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings


def _key() -> bytes:
    encoded = get_settings().settings_encryption_key
    if not encoded:
        raise RuntimeError("SETTINGS_ENCRYPTION_KEY is required to encrypt panel secrets")
    try:
        key = base64.b64decode(encoded.encode("ascii"), altchars=b"-_", validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise RuntimeError("SETTINGS_ENCRYPTION_KEY must be URL-safe base64 for 32 bytes") from exc
    if len(key) != 32:
        raise RuntimeError("SETTINGS_ENCRYPTION_KEY must decode to exactly 32 bytes")
    return key


def encrypt(plaintext: str) -> tuple[bytes, bytes]:
    nonce = os.urandom(12)
    return AESGCM(_key()).encrypt(nonce, plaintext.encode("utf-8"), None), nonce


def decrypt(ciphertext: bytes, nonce: bytes) -> str:
    return AESGCM(_key()).decrypt(nonce, ciphertext, None).decode("utf-8")
