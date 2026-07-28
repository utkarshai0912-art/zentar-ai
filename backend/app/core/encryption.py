"""
Zentar Intelligence — Encryption Service

Encrypts and decrypts secrets at rest using Fernet symmetric encryption.
All secrets are encrypted before being stored in the database and
decrypted only when needed.
"""

import base64
import hashlib
import logging
from typing import Optional

from cryptography.fernet import Fernet

from app.core.config import get_settings

logger = logging.getLogger("zentar.core.encryption")


class EncryptionService:
    """Encrypts/decrypts sensitive data using Fernet (symmetric AES-128-CBC)."""

    def __init__(self, key: Optional[str] = None):
        self._fernet: Optional[Fernet] = None
        key = key or get_settings().ENCRYPTION_KEY
        self._init_fernet(key)

    def _init_fernet(self, key: str):
        """Derive a valid Fernet key from the config key."""
        try:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except (ValueError, TypeError):
            encoded = base64.urlsafe_b64encode(
                hashlib.sha256(key.encode() if isinstance(key, str) else key).digest()
            )
            self._fernet = Fernet(encoded)

    def encrypt(self, value: str) -> str:
        """Encrypt a plaintext string. Returns a base64-encoded ciphertext."""
        if not value:
            return ""
        result = self._fernet.encrypt(value.encode())
        return result.decode()

    def decrypt(self, encrypted: str) -> str:
        """Decrypt a previously encrypted value. Returns the original plaintext."""
        if not encrypted:
            return ""
        result = self._fernet.decrypt(encrypted.encode())
        return result.decode()

    def mask(self, value: str, visible_chars: int = 4) -> str:
        """Mask a sensitive value for display, showing only last N chars."""
        if not value or len(value) <= visible_chars:
            return value
        return "*" * (len(value) - visible_chars) + value[-visible_chars:]


encryption_service = EncryptionService()