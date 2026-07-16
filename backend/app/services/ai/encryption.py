from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings


class AIEncryptionError(RuntimeError):
    pass


def encrypt_api_key(api_key: str, settings: Settings) -> str:
    """Encrypt a provider API key using material derived from APP_SECRET_KEY."""

    if not api_key.strip():
        raise AIEncryptionError("API key is required")
    try:
        return (
            fernet_for_settings(settings)
            .encrypt(api_key.encode("utf-8"))
            .decode("utf-8")
        )
    except Exception as exc:
        raise AIEncryptionError("Unable to encrypt API key") from exc


def decrypt_api_key(encrypted_api_key: str, settings: Settings) -> str:
    """Decrypt a provider API key or fail without returning secret material."""

    try:
        return (
            fernet_for_settings(settings)
            .decrypt(encrypted_api_key.encode("utf-8"))
            .decode("utf-8")
        )
    except InvalidToken as exc:
        raise AIEncryptionError("Stored API key cannot be decrypted") from exc
    except Exception as exc:
        raise AIEncryptionError("Unable to decrypt API key") from exc


def fernet_for_settings(settings: Settings) -> Fernet:
    secret = settings.app_secret_key.strip()
    if len(secret) < 8:
        raise AIEncryptionError("APP_SECRET_KEY is required for API key encryption")
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))
